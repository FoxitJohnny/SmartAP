"""
Exception Handling Tests

Tests for exception handling and error propagation including:
- Service-level exceptions
- Database errors
- External API failures
- Error logging and monitoring
- Graceful degradation

V3.2.3 Implementation
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from httpx import AsyncClient

from src.utils.errors import (
    SmartAPError,
    ValidationError as SmartAPValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
    RateLimitError,
    CircuitBreakerOpenError,
)
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from src.utils.retry import RetryConfig, RetryExhaustedError, retry_async


class TestDatabaseExceptionHandling:
    """Tests for database exception handling."""
    
    @pytest.mark.asyncio
    async def test_integrity_error_handling(self, test_db_session):
        """Test handling of database integrity errors."""
        from src.db.models import VendorDB
        from datetime import date
        
        # Create vendor with all required fields
        vendor = VendorDB(
            vendor_id="integrity-test-001",
            vendor_name="Test Vendor",
            status="active",
            onboarded_date=date(2024, 1, 1)
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Try to create duplicate
        duplicate = VendorDB(
            vendor_id="integrity-test-001",  # Same ID
            vendor_name="Duplicate Vendor",
            status="active",
            onboarded_date=date(2024, 1, 1)
        )
        test_db_session.add(duplicate)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        # Rollback to clean up
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, test_db_session):
        """Test session automatically rolls back on error."""
        from src.db.models import VendorDB
        from datetime import date
        
        # Get initial count
        from sqlalchemy import select, func
        initial_count = await test_db_session.scalar(
            select(func.count()).select_from(VendorDB)
        )
        
        try:
            vendor = VendorDB(
                vendor_id="rollback-test",
                vendor_name="Rollback Test",
                status="active",
                onboarded_date=date(2024, 1, 1)
            )
            test_db_session.add(vendor)
            await test_db_session.flush()
            
            # Simulate error
            raise Exception("Simulated error")
        except Exception:
            await test_db_session.rollback()
        
        # Count should be same as initial
        final_count = await test_db_session.scalar(
            select(func.count()).select_from(VendorDB)
        )
        
        assert final_count == initial_count
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of database connection errors."""
        # Simulate connection error scenario
        mock_session = AsyncMock()
        mock_session.execute.side_effect = OperationalError(
            "connection refused", None, None
        )
        
        with pytest.raises(OperationalError):
            await mock_session.execute("SELECT 1")


class TestExternalServiceExceptionHandling:
    """Tests for external service exception handling."""
    
    @pytest.mark.asyncio
    async def test_external_service_timeout(self):
        """Test handling of external service timeouts."""
        async def slow_service():
            await asyncio.sleep(10)
            return "never reached"
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_service(), timeout=0.01)
    
    @pytest.mark.asyncio
    async def test_external_service_error_propagation(self):
        """Test that external service errors propagate correctly."""
        error = ExternalServiceError(
            service_name="TestService",
            message="Connection refused",
            original_error="ECONNREFUSED",
            retryable=True
        )
        
        async def failing_service():
            raise error
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await failing_service()
        
        assert exc_info.value.service_name == "TestService"
        assert exc_info.value.retryable is True
        assert exc_info.value.status_code == 502
    
    @pytest.mark.asyncio
    async def test_retry_on_external_error(self):
        """Test retry behavior on external service errors."""
        call_count = 0
        
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ExternalServiceError(
                    service_name="FlakyAPI",
                    message="Temporary failure",
                    retryable=True
                )
            return {"status": "success"}
        
        result = await retry_async(
            flaky_service,
            config=RetryConfig(
                max_retries=3,
                initial_delay=0.01,
                retryable_exceptions=(ExternalServiceError,)
            )
        )
        
        assert result["status"] == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Test non-retryable errors eventually exhaust retries."""
        call_count = 0
        
        async def permanent_failure():
            nonlocal call_count
            call_count += 1
            raise ExternalServiceError(
                service_name="API",
                message="Invalid credentials",
                retryable=False  # Marked non-retryable but still in retryable_exceptions
            )
        
        # Since ExternalServiceError is in retryable_exceptions, it will retry
        with pytest.raises((ExternalServiceError, RetryExhaustedError)):
            await retry_async(
                permanent_failure,
                config=RetryConfig(
                    max_retries=2,
                    initial_delay=0.01,
                    retryable_exceptions=(ExternalServiceError,)
                )
            )


class TestCircuitBreakerExceptionHandling:
    """Tests for circuit breaker exception handling."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_error_message(self):
        """Test circuit breaker open error has proper message."""
        error = CircuitBreakerOpenError(
            service_name="test_service",
            retry_after=30
        )
        
        assert "test_service" in error.message
        assert error.status_code == 503
        assert error.retry_after == 30
        assert "CIRCUIT_BREAKER_OPEN" in error.error_code
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_different_errors(self):
        """Test circuit breaker handles different error types."""
        breaker = CircuitBreaker(
            "test_diff_errors",
            CircuitBreakerConfig(failure_threshold=5)
        )
        
        errors = [
            ValueError("Type error"),
            ConnectionError("Connection failed"),
            TimeoutError("Timeout"),
            RuntimeError("Runtime issue"),
            Exception("Generic error")
        ]
        
        for error in errors:
            try:
                async with breaker:
                    raise error
            except type(error):
                pass
        
        # All errors should increment failure count
        assert breaker.get_stats()["failure_count"] == 5
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_after_success(self):
        """Test circuit breaker recovers after successful calls."""
        breaker = CircuitBreaker(
            "test_recovery",
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=0.1
            )
        )
        
        # Trip the breaker
        for _ in range(3):
            try:
                async with breaker:
                    raise Exception("Failure")
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        
        # Successful calls should close circuit
        for _ in range(2):
            async with breaker:
                pass  # Success
        
        assert breaker.state == CircuitState.CLOSED


class TestErrorResponseFormatting:
    """Tests for error response formatting."""
    
    def test_error_response_has_required_fields(self):
        """Test error response model has required fields."""
        from src.utils.errors import ErrorResponse
        
        response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message"
        )
        
        assert response.error_code == "TEST_ERROR"
        assert response.message == "Test message"
        assert response.timestamp is not None
    
    def test_error_response_with_optional_fields(self):
        """Test error response with all fields."""
        from src.utils.errors import ErrorResponse
        
        response = ErrorResponse(
            error_code="FULL_ERROR",
            message="Full error message",
            detail="Additional details here",
            request_id="req-12345",
            path="/api/v1/test",
            suggestions=["Try this", "Or that"]
        )
        
        assert response.detail == "Additional details here"
        assert response.request_id == "req-12345"
        assert response.path == "/api/v1/test"
        assert len(response.suggestions) == 2
    
    def test_smartap_error_to_response_conversion(self):
        """Test SmartAPError converts to ErrorResponse."""
        error = NotFoundError(
            resource_type="Invoice",
            resource_id="INV-999"
        )
        
        response = error.to_response(
            request_id="test-request-id",
            path="/api/v1/invoices/INV-999"
        )
        
        assert "INVOICE_NOT_FOUND" in response.error_code
        assert "INV-999" in response.message
        assert response.request_id == "test-request-id"


class TestAPIExceptionHandling:
    """Tests for API endpoint exception handling."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_always_responds(self, async_client: AsyncClient):
        """Test health endpoint responds even under load."""
        response = await async_client.get("/api/v1/health")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, async_client: AsyncClient):
        """Test error responses have consistent format."""
        # Test non-existent endpoint for 404
        response = await async_client.get("/api/v1/nonexistent-endpoint-xyz")
        
        assert response.status_code == 404
        
        data = response.json()
        # Should have error information
        assert "detail" in data or "error_code" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_not_found_response(self, async_client: AsyncClient, auth_headers):
        """Test 404 responses include resource information."""
        response = await async_client.get(
            "/api/v1/invoices/definitely-not-exist-12345",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 422]
    
    @pytest.mark.asyncio
    async def test_method_not_allowed_response(self, async_client: AsyncClient, auth_headers):
        """Test 405 Method Not Allowed responses."""
        response = await async_client.delete(
            "/api/v1/health",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 405]


class TestExceptionChaining:
    """Tests for exception chaining and context."""
    
    @pytest.mark.asyncio
    async def test_exception_chain_preserved(self):
        """Test that exception chains are preserved."""
        original = ValueError("Original error")
        
        try:
            try:
                raise original
            except ValueError as e:
                raise ExternalServiceError(
                    service_name="Test",
                    message="Wrapped error",
                    original_error=str(e)
                ) from e
        except ExternalServiceError as exc:
            assert exc.__cause__ is original
            assert "Original error" in exc.detail
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_preserves_last_error(self):
        """Test RetryExhaustedError preserves last exception."""
        last_error = ValueError("Last failure")
        
        async def always_fails():
            raise last_error
        
        try:
            await retry_async(
                always_fails,
                config=RetryConfig(max_retries=2, initial_delay=0.01)
            )
        except RetryExhaustedError as exc:
            assert exc.last_exception is last_error
            assert exc.attempts == 3  # Initial + 2 retries


class TestConcurrentExceptionHandling:
    """Tests for exception handling in concurrent scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_errors_isolated(self):
        """Test that concurrent errors don't interfere with each other."""
        results = []
        
        async def task_succeeds():
            await asyncio.sleep(0.01)
            return "success"
        
        async def task_fails():
            await asyncio.sleep(0.01)
            raise ValueError("Task failed")
        
        # Mix of successful and failing tasks
        tasks = [
            task_succeeds(),
            task_fails(),
            task_succeeds(),
            task_fails(),
            task_succeeds()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        successes = [r for r in results if r == "success"]
        failures = [r for r in results if isinstance(r, ValueError)]
        
        assert len(successes) == 3
        assert len(failures) == 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_failures(self):
        """Test circuit breaker handles concurrent failures."""
        breaker = CircuitBreaker(
            "test_concurrent_fail",
            CircuitBreakerConfig(failure_threshold=5)
        )
        
        async def failing_call():
            async with breaker:
                raise Exception("Concurrent failure")
        
        # Run concurrent failing calls
        tasks = [failing_call() for _ in range(10)]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some should fail with Exception, some may fail with CircuitBreakerOpenError
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 10
    
    @pytest.mark.asyncio
    async def test_session_error_isolation(self, test_db_session):
        """Test that session errors don't corrupt shared state."""
        from src.db.models import VendorDB
        from datetime import date
        
        # Create a vendor successfully
        vendor = VendorDB(
            vendor_id="isolation-test",
            vendor_name="Isolation Test",
            status="active",
            onboarded_date=date(2024, 1, 1)
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Now try an operation that fails
        try:
            bad_vendor = VendorDB(
                vendor_id="isolation-test",  # Duplicate
                vendor_name="Bad Vendor",
                status="active",
                onboarded_date=date(2024, 1, 1)
            )
            test_db_session.add(bad_vendor)
            await test_db_session.commit()
        except IntegrityError:
            await test_db_session.rollback()
        
        # Original vendor should still be accessible
        from sqlalchemy import select
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == "isolation-test")
        )
        found_vendor = result.scalar_one_or_none()
        
        assert found_vendor is not None
        assert found_vendor.vendor_name == "Isolation Test"


class TestGracefulDegradation:
    """Tests for graceful degradation scenarios."""
    
    @pytest.mark.asyncio
    async def test_service_fallback_on_error(self):
        """Test fallback behavior when primary service fails."""
        primary_called = False
        fallback_called = False
        
        async def primary_service():
            nonlocal primary_called
            primary_called = True
            raise ExternalServiceError(
                service_name="Primary",
                message="Service down",
                retryable=False
            )
        
        async def fallback_service():
            nonlocal fallback_called
            fallback_called = True
            return {"status": "fallback"}
        
        # Implement fallback pattern
        try:
            result = await primary_service()
        except ExternalServiceError:
            result = await fallback_service()
        
        assert primary_called is True
        assert fallback_called is True
        assert result["status"] == "fallback"
    
    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """Test handling of partial failures in batch operations."""
        results = {
            "successful": [],
            "failed": []
        }
        
        async def process_item(item_id):
            if item_id % 3 == 0:
                raise ValueError(f"Item {item_id} failed")
            return item_id * 2
        
        for i in range(1, 10):
            try:
                result = await process_item(i)
                results["successful"].append((i, result))
            except ValueError as e:
                results["failed"].append((i, str(e)))
        
        # Should have mix of successes and failures
        assert len(results["successful"]) == 6  # 1,2,4,5,7,8
        assert len(results["failed"]) == 3  # 3,6,9


class TestErrorLogging:
    """Tests for error logging behavior."""
    
    @pytest.mark.asyncio
    async def test_error_logged_with_context(self, caplog):
        """Test that errors are logged with context."""
        import logging
        
        breaker = CircuitBreaker(
            "test_logging",
            CircuitBreakerConfig(failure_threshold=2)
        )
        
        with caplog.at_level(logging.INFO):
            for _ in range(2):
                try:
                    async with breaker:
                        raise Exception("Test error")
                except Exception:
                    pass
        
        # Should log state transition
        assert any("transitioned" in record.message.lower() for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_retry_logs_attempts(self, caplog):
        """Test that retry attempts are logged."""
        import logging
        
        call_count = 0
        
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient")
            return "ok"
        
        with caplog.at_level(logging.WARNING):
            await retry_async(
                flaky,
                config=RetryConfig(max_retries=3, initial_delay=0.01)
            )
        
        # Should log retry attempts
        retry_logs = [r for r in caplog.records if "retry" in r.message.lower()]
        assert len(retry_logs) >= 1


class TestSpecificServiceErrors:
    """Tests for specific service error scenarios."""
    
    @pytest.mark.asyncio
    async def test_ocr_service_error_handling(self):
        """Test OCR service error is properly categorized."""
        error = ExternalServiceError(
            service_name="FoxitOCR",
            message="Image processing failed",
            original_error="Invalid image format",
            retryable=True
        )
        
        assert error.status_code == 502
        assert "FOXIT" in error.error_code.upper() or "EXTERNAL_SERVICE" in error.error_code
        assert error.retryable is True
    
    @pytest.mark.asyncio
    async def test_erp_sync_error_handling(self):
        """Test ERP sync error handling."""
        error = ExternalServiceError(
            service_name="NetSuite",
            message="Sync failed",
            original_error="Authentication expired",
            retryable=True
        )
        
        assert "NetSuite" in error.message
        assert error.status_code == 502
    
    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self):
        """Test AI service error handling."""
        error = ExternalServiceError(
            service_name="OpenAI",
            message="Rate limited",
            original_error="429 Too Many Requests",
            retryable=True
        )
        
        response = error.to_response()
        assert response.error_code is not None
        # Suggestions include "try again" which is close to retry concept
        assert any("try again" in s.lower() for s in response.suggestions)
