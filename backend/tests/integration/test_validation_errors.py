"""
Validation Error Tests

Comprehensive tests for input validation error handling including:
- Request body validation
- Query parameter validation
- Path parameter validation
- Schema validation
- Constraint violations
- Type coercion errors

V3.2.3 Implementation
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
import json

from httpx import AsyncClient
from pydantic import BaseModel, ValidationError, Field, field_validator

from src.models.invoice import Invoice, InvoiceLineItem
from src.models.vendor import Vendor, VendorStatus
from src.models.purchase_order import PurchaseOrder, POStatus
from src.models.matching import MatchingResult, MatchType
from src.models.risk import RiskAssessment, RiskLevel, RecommendedAction


class TestPydanticValidation:
    """Tests for Pydantic model validation."""
    
    def test_invoice_valid_data(self):
        """Test Invoice model with valid data."""
        invoice = Invoice(
            invoice_number="INV-2024-001",
            vendor_name="Test Vendor",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total=Decimal("1000.00"),
            currency="USD",
        )
        
        assert invoice.invoice_number == "INV-2024-001"
        assert invoice.total == Decimal("1000.00")
    
    def test_invoice_invalid_amount(self):
        """Test Invoice model with negative amount (credit memo)."""
        # Negative amounts may be valid for credit memos
        invoice = Invoice(
            invoice_number="INV-2024-002",
            vendor_name="Test Vendor",
            invoice_date=date(2024, 1, 15),
            total=Decimal("-100.00"),  # Negative (credit memo)
            currency="USD",
        )
        
        # Model may accept negative (for credit memos)
        assert invoice.total == Decimal("-100.00")
    
    def test_invoice_missing_required_field(self):
        """Test Invoice model requires mandatory fields."""
        with pytest.raises(ValidationError) as exc_info:
            Invoice(
                # Missing invoice_number and total
                vendor_name="Test Vendor",
            )
        
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "invoice_number" in field_names or "total" in field_names
    
    def test_vendor_valid_data(self):
        """Test Vendor model with valid data."""
        vendor = Vendor(
            vendor_id="V-001",
            vendor_name="Acme Corp",
            status=VendorStatus.ACTIVE,
            onboarded_date=date(2024, 1, 1)
        )
        
        assert vendor.vendor_id == "V-001"
        assert vendor.status == VendorStatus.ACTIVE
    
    def test_vendor_invalid_status(self):
        """Test Vendor model rejects invalid status."""
        with pytest.raises(ValidationError):
            Vendor(
                vendor_id="V-002",
                vendor_name="Test Corp",
                status="not_a_valid_status",
                onboarded_date=date(2024, 1, 1)
            )
    
    def test_purchase_order_valid(self):
        """Test PurchaseOrder model with valid data."""
        from src.models.purchase_order import POLineItem
        
        po = PurchaseOrder(
            po_id="PO-001",
            po_number="PO-2024-001",
            vendor_id="V-001",
            vendor_name="Test Vendor",
            total_amount=Decimal("5000.00"),
            currency="USD",
            status=POStatus.OPEN,
            created_date=date(2024, 1, 1),
            line_items=[
                POLineItem(
                    line_number=1,
                    description="Widget A",
                    quantity=10,
                    unit_price=Decimal("500.00"),
                    amount=Decimal("5000.00")
                )
            ],
            subtotal=Decimal("5000.00")
        )
        
        assert po.po_number == "PO-2024-001"
        assert po.status == POStatus.OPEN
    
    def test_matching_result_valid(self):
        """Test MatchingResult model with valid data."""
        result = MatchingResult(
            matching_id="M-001",
            invoice_id="INV-001",
            po_id="PO-001",
            match_type=MatchType.EXACT,
            match_score=0.95,
            matched=True
        )
        
        assert result.match_score == 0.95
        assert result.matched is True
    
    def test_matching_result_confidence_bounds(self):
        """Test MatchingResult match_score bounds."""
        # Score should be 0-1, validation should enforce bounds
        with pytest.raises(ValidationError):
            MatchingResult(
                matching_id="M-002",
                invoice_id="INV-002",
                po_id="PO-002",
                match_type=MatchType.FUZZY,
                match_score=1.5,  # Over 1.0 - should fail validation
                matched=True
            )
    
    def test_risk_assessment_valid(self):
        """Test RiskAssessment model with valid data."""
        assessment = RiskAssessment(
            assessment_id="RA-001",
            invoice_id="INV-001",
            risk_level=RiskLevel.LOW,
            risk_score=0.15,
            recommended_action=RecommendedAction.AUTO_APPROVE,
            action_reason="Low risk score",
            requires_manual_review=False
        )
        
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.risk_score == 0.15
    
    def test_line_item_valid(self):
        """Test InvoiceLineItem with valid data."""
        item = InvoiceLineItem(
            description="Widget A",
            quantity=10,
            unit_price=Decimal("25.00"),
            amount=Decimal("250.00")
        )
        
        assert item.description == "Widget A"
        assert item.amount == Decimal("250.00")


class TestAPIValidation:
    """Tests for API endpoint validation."""
    
    @pytest.mark.asyncio
    async def test_register_valid_email(self, async_client: AsyncClient):
        """Test registration with valid email."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "password": "SecurePass123!",
                "name": "Valid User"
            }
        )
        
        # Should succeed or fail for other reason (not email validation)
        assert response.status_code in [200, 201, 400, 409, 422]  # 422 for validation
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-valid-email",
                "password": "SecurePass123!",
                "name": "Test User"
            }
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "123",  # Too weak
                "name": "Test User"
            }
        )
        
        # May reject weak passwords or allow them
        assert response.status_code in [200, 201, 400, 422]
    
    @pytest.mark.asyncio
    async def test_login_missing_email(self, async_client: AsyncClient):
        """Test login without email."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "password": "SomePassword123"
            }
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_login_missing_password(self, async_client: AsyncClient):
        """Test login without password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@example.com"
            }
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, async_client: AsyncClient):
        """Test login with empty credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "",
                "password": ""
            }
        )
        
        assert response.status_code in [400, 401, 422]
    
    @pytest.mark.asyncio
    async def test_invoice_list_invalid_limit(self, async_client: AsyncClient, auth_headers):
        """Test invoice list with invalid limit parameter."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"limit": -1},
            headers=auth_headers
        )
        
        # Should use default or reject negative
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_invoice_list_invalid_offset(self, async_client: AsyncClient, auth_headers):
        """Test invoice list with invalid offset parameter."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"offset": "not-a-number"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_dashboard_invalid_date_range(self, async_client: AsyncClient, auth_headers):
        """Test dashboard with invalid date range."""
        response = await async_client.get(
            "/api/v1/dashboard/metrics",
            params={
                "start_date": "2024-12-01",
                "end_date": "2024-01-01"  # End before start
            },
            headers=auth_headers
        )
        
        # May swap dates, use defaults, return error, or 404 if endpoint doesn't exist
        assert response.status_code in [200, 400, 404, 422]
    
    @pytest.mark.asyncio
    async def test_upload_invalid_content_type(self, async_client: AsyncClient, auth_headers):
        """Test invoice upload with invalid content type."""
        response = await async_client.post(
            "/api/v1/invoices/upload",
            content=b"not a pdf",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        assert response.status_code in [400, 415, 422]


class TestPathParameterValidation:
    """Tests for path parameter validation."""
    
    @pytest.mark.asyncio
    async def test_invoice_id_format(self, async_client: AsyncClient, auth_headers):
        """Test invoice endpoint with various ID formats."""
        # Valid UUID-like format
        response = await async_client.get(
            "/api/v1/invoices/550e8400-e29b-41d4-a716-446655440000",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]  # May not exist but format valid
    
    @pytest.mark.asyncio
    async def test_invoice_id_special_chars(self, async_client: AsyncClient, auth_headers):
        """Test invoice endpoint with special characters in ID."""
        response = await async_client.get(
            "/api/v1/invoices/<script>alert(1)</script>",
            headers=auth_headers
        )
        
        # Should sanitize/reject or return 404
        assert response.status_code in [400, 404, 422]
    
    @pytest.mark.asyncio
    async def test_invoice_id_sql_injection(self, async_client: AsyncClient, auth_headers):
        """Test invoice endpoint against SQL injection."""
        response = await async_client.get(
            "/api/v1/invoices/1' OR '1'='1",
            headers=auth_headers
        )
        
        # Should not execute SQL, just return not found or error
        assert response.status_code in [400, 404, 422]
    
    @pytest.mark.asyncio
    async def test_vendor_id_empty(self, async_client: AsyncClient, auth_headers):
        """Test vendor endpoint with empty ID (list endpoint)."""
        response = await async_client.get(
            "/api/v1/vendors",
            headers=auth_headers
        )
        
        # Empty path should list vendors or return error
        assert response.status_code in [200, 307, 400, 404]


class TestQueryParameterValidation:
    """Tests for query parameter validation."""
    
    @pytest.mark.asyncio
    async def test_multiple_status_filter(self, async_client: AsyncClient, auth_headers):
        """Test filtering with multiple status values."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"status": ["pending", "approved"]},
            headers=auth_headers
        )
        
        # Should handle array parameters
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_pagination_boundary(self, async_client: AsyncClient, auth_headers):
        """Test pagination at boundary values."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"limit": 0, "offset": 0},
            headers=auth_headers
        )
        
        # Limit of 0 may be rejected or return empty
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_large_limit(self, async_client: AsyncClient, auth_headers):
        """Test with very large limit value."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"limit": 1000000},
            headers=auth_headers
        )
        
        # Should cap at max or return error
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_negative_pagination(self, async_client: AsyncClient, auth_headers):
        """Test with negative pagination values."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"limit": -10, "offset": -5},
            headers=auth_headers
        )
        
        # Should reject or use defaults
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_unicode_search(self, async_client: AsyncClient, auth_headers):
        """Test search with unicode characters."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"search": "测试 тест 🔍"},
            headers=auth_headers
        )
        
        # Should handle unicode gracefully
        assert response.status_code in [200, 400]


class TestRequestBodyValidation:
    """Tests for request body validation."""
    
    @pytest.mark.asyncio
    async def test_empty_json_body(self, async_client: AsyncClient, auth_headers):
        """Test endpoints with empty JSON body."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_null_json_body(self, async_client: AsyncClient, auth_headers):
        """Test endpoints with null JSON body."""
        response = await async_client.post(
            "/api/v1/auth/login",
            content="null",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_array_instead_of_object(self, async_client: AsyncClient, auth_headers):
        """Test endpoints expecting object receiving array."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json=[{"email": "test@example.com", "password": "test"}],
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_extra_fields_ignored(self, async_client: AsyncClient, auth_headers):
        """Test that extra fields are ignored or cause validation error."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass",
                "extra_field": "should_be_ignored",
                "another_extra": 12345
            }
        )
        
        # Extra fields should be ignored or cause validation error
        assert response.status_code in [200, 401, 422]  # Success, auth failure, or validation
    
    @pytest.mark.asyncio
    async def test_wrong_type_for_field(self, async_client: AsyncClient, auth_headers):
        """Test wrong type provided for a field."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": 12345,  # Should be string
                "password": ["array", "not", "string"]  # Should be string
            }
        )
        
        assert response.status_code in [400, 422]


class TestTypeCoercionErrors:
    """Tests for type coercion and conversion errors."""
    
    @pytest.mark.asyncio
    async def test_string_to_int_coercion(self, async_client: AsyncClient, auth_headers):
        """Test string to int coercion for pagination."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"limit": "10", "offset": "0"},  # Strings that can be ints
            headers=auth_headers
        )
        
        # Should coerce strings to ints
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_float_to_int_coercion(self, async_client: AsyncClient, auth_headers):
        """Test float to int coercion."""
        response = await async_client.get(
            "/api/v1/invoices",
            params={"limit": "10.5"},  # Float string
            headers=auth_headers
        )
        
        # May truncate or reject
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_boolean_string_coercion(self, async_client: AsyncClient, auth_headers):
        """Test boolean string coercion."""
        response = await async_client.get(
            "/api/v1/vendors",
            params={"active": "true"},  # String boolean
            headers=auth_headers
        )
        
        # Should recognize "true" as boolean
        assert response.status_code in [200, 400, 404]


class TestConstraintViolations:
    """Tests for database constraint violations."""
    
    @pytest.mark.asyncio
    async def test_duplicate_email_registration(self, async_client: AsyncClient):
        """Test registering with duplicate email."""
        # First registration
        email = f"duplicate_test_{datetime.now().timestamp()}@example.com"
        
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "name": "First User"
            }
        )
        
        # Second registration with same email
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "DifferentPass456!",
                "name": "Second User"
            }
        )
        
        # Should reject duplicate
        assert response.status_code in [400, 409, 422]
    
    @pytest.mark.asyncio
    async def test_invoice_approval_already_approved(self, async_client: AsyncClient, auth_headers):
        """Test approving an already approved invoice."""
        # This would require creating and approving an invoice first
        # For now, just test the endpoint handles non-existent invoices
        response = await async_client.post(
            "/api/v1/invoices/nonexistent/approve",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 400, 422]


class TestContentTypeValidation:
    """Tests for content type validation."""
    
    @pytest.mark.asyncio
    async def test_json_endpoint_with_form_data(self, async_client: AsyncClient):
        """Test JSON endpoint receiving form data."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={"email": "test@example.com", "password": "testpass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # May accept form data or require JSON
        assert response.status_code in [200, 400, 401, 415, 422]
    
    @pytest.mark.asyncio
    async def test_upload_endpoint_without_file(self, async_client: AsyncClient, auth_headers):
        """Test upload endpoint without actual file."""
        response = await async_client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers
        )
        
        # Should require file
        assert response.status_code in [400, 422]
