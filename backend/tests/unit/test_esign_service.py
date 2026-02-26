"""
Unit Tests for ESignService (Foxit eSign Integration)

Tests for electronic signature request creation, verification, and webhook handling.
"""

import pytest
import hashlib
import hmac
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
import httpx

from src.services.esign_service import ESignService, ESignStatus, SignerRole


class TestESignServiceInit:
    """Tests for ESignService initialization."""
    
    def test_init_sets_properties(self):
        """Test that initialization sets all properties correctly."""
        service = ESignService(
            api_key="test-api-key",
            api_secret="test-api-secret",
            base_url="https://api.foxit.com/v1",
            webhook_secret="webhook-secret",
            callback_url="https://myapp.com/webhooks/esign",
        )
        
        assert service.api_key == "test-api-key"
        assert service.api_secret == "test-api-secret"
        assert service.base_url == "https://api.foxit.com/v1"
        assert service.webhook_secret == "webhook-secret"
        assert service.callback_url == "https://myapp.com/webhooks/esign"
    
    def test_init_strips_trailing_slash(self):
        """Test that base_url trailing slash is stripped."""
        service = ESignService(
            api_key="key",
            api_secret="secret",
            base_url="https://api.foxit.com/v1/",
            webhook_secret="webhook",
            callback_url="https://app.com/callback",
        )
        
        assert service.base_url == "https://api.foxit.com/v1"


class TestAuthSignature:
    """Tests for HMAC authentication signature generation."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return ESignService(
            api_key="test-api-key",
            api_secret="test-secret-key",
            base_url="https://api.foxit.com",
            webhook_secret="webhook-secret",
            callback_url="https://app.com/callback",
        )
    
    def test_generate_auth_signature_no_body(self, service):
        """Test signature generation without request body."""
        timestamp = "2026-01-15T10:00:00"
        
        signature = service._generate_auth_signature(timestamp)
        
        # Verify signature is hex-encoded HMAC-SHA256
        assert len(signature) == 64  # SHA256 hex = 64 chars
        assert all(c in '0123456789abcdef' for c in signature)
    
    def test_generate_auth_signature_with_body(self, service):
        """Test signature generation with request body."""
        timestamp = "2026-01-15T10:00:00"
        body = '{"test": "data"}'
        
        signature = service._generate_auth_signature(timestamp, body)
        
        # Verify expected signature
        expected_message = f"{timestamp}{body}".encode('utf-8')
        expected_signature = hmac.new(
            "test-secret-key".encode('utf-8'),
            expected_message,
            hashlib.sha256
        ).hexdigest()
        
        assert signature == expected_signature
    
    def test_generate_auth_signature_different_inputs_different_output(self, service):
        """Test that different inputs produce different signatures."""
        sig1 = service._generate_auth_signature("2026-01-15T10:00:00")
        sig2 = service._generate_auth_signature("2026-01-15T11:00:00")
        sig3 = service._generate_auth_signature("2026-01-15T10:00:00", "body")
        
        assert sig1 != sig2
        assert sig1 != sig3
        assert sig2 != sig3


class TestWebhookVerification:
    """Tests for webhook signature verification."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ESignService(
            api_key="key",
            api_secret="secret",
            base_url="https://api.foxit.com",
            webhook_secret="my-webhook-secret",
            callback_url="https://app.com/callback",
        )
    
    def test_verify_webhook_signature_valid(self, service):
        """Test valid webhook signature verification."""
        payload = '{"event": "signed", "request_id": "123"}'
        
        # Generate valid signature
        expected_signature = hmac.new(
            "my-webhook-secret".encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        assert service.verify_webhook_signature(payload, expected_signature) is True
    
    def test_verify_webhook_signature_invalid(self, service):
        """Test invalid webhook signature rejection."""
        payload = '{"event": "signed", "request_id": "123"}'
        invalid_signature = "invalid_signature_value_here"
        
        assert service.verify_webhook_signature(payload, invalid_signature) is False
    
    def test_verify_webhook_signature_tampered_payload(self, service):
        """Test that tampered payload fails verification."""
        original_payload = '{"event": "signed", "request_id": "123"}'
        tampered_payload = '{"event": "signed", "request_id": "456"}'  # Changed ID
        
        # Signature for original payload
        signature = hmac.new(
            "my-webhook-secret".encode('utf-8'),
            original_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Should fail with tampered payload
        assert service.verify_webhook_signature(tampered_payload, signature) is False


class TestCreateSigningRequest:
    """Tests for create_signing_request method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked client."""
        svc = ESignService(
            api_key="test-api-key",
            api_secret="test-secret",
            base_url="https://api.foxit.com",
            webhook_secret="webhook-secret",
            callback_url="https://app.com/callback",
        )
        svc.client = AsyncMock()
        return svc
    
    @pytest.mark.asyncio
    async def test_create_signing_request_success(self, service, tmp_path):
        """Test successful signing request creation."""
        # Create temporary PDF
        pdf_path = tmp_path / "test_invoice.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test content")
        
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "request_id": "ESIGN-REQ-001",
            "signer_urls": [
                {"email": "manager@company.com", "url": "https://esign.foxit.com/sign/abc123"},
            ],
            "expires_at": "2026-01-22T10:00:00Z",
        }
        mock_response.raise_for_status = Mock()
        service.client.post = AsyncMock(return_value=mock_response)
        
        # Call method
        result = await service.create_signing_request(
            invoice_id="INV-001",
            document_path=str(pdf_path),
            signers=[
                {"name": "John Manager", "email": "manager@company.com", "role": "manager"},
            ],
            invoice_amount=50000.00,
            invoice_number="INV-2026-001",
            vendor_name="Acme Corp",
        )
        
        # Verify response
        assert result["request_id"] == "ESIGN-REQ-001"
        assert result["status"] == ESignStatus.PENDING
        assert len(result["signer_urls"]) == 1
    
    @pytest.mark.asyncio
    async def test_create_signing_request_includes_metadata(self, service, tmp_path):
        """Test that request includes invoice metadata."""
        pdf_path = tmp_path / "invoice.pdf"
        pdf_path.write_bytes(b"%PDF")
        
        mock_response = Mock()
        mock_response.json.return_value = {"request_id": "REQ-002", "signer_urls": []}
        mock_response.raise_for_status = Mock()
        service.client.post = AsyncMock(return_value=mock_response)
        
        await service.create_signing_request(
            invoice_id="INV-002",
            document_path=str(pdf_path),
            signers=[{"name": "CFO", "email": "cfo@company.com"}],
            invoice_amount=100000.00,
            invoice_number="INV-2026-002",
            vendor_name="Test Vendor",
        )
        
        # Verify API call
        call_args = service.client.post.call_args
        payload = call_args.kwargs.get("json", call_args[1].get("json"))
        
        assert payload["metadata"]["invoice_id"] == "INV-002"
        assert payload["metadata"]["invoice_amount"] == 100000.00
        assert payload["metadata"]["vendor_name"] == "Test Vendor"
    
    @pytest.mark.asyncio
    async def test_create_signing_request_http_error(self, service, tmp_path):
        """Test handling of HTTP error response."""
        pdf_path = tmp_path / "invoice.pdf"
        pdf_path.write_bytes(b"%PDF")
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Bad Request",
                request=Mock(),
                response=Mock(text="Invalid document format"),
            )
        )
        service.client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(httpx.HTTPStatusError):
            await service.create_signing_request(
                invoice_id="INV-003",
                document_path=str(pdf_path),
                signers=[{"name": "Manager", "email": "mgr@company.com"}],
                invoice_amount=25000.00,
                invoice_number="INV-2026-003",
                vendor_name="Vendor",
            )
    
    @pytest.mark.asyncio
    async def test_create_signing_request_file_not_found(self, service):
        """Test handling of missing document file."""
        with pytest.raises(FileNotFoundError):
            await service.create_signing_request(
                invoice_id="INV-004",
                document_path="/nonexistent/path/invoice.pdf",
                signers=[{"name": "Manager", "email": "mgr@company.com"}],
                invoice_amount=10000.00,
                invoice_number="INV-2026-004",
                vendor_name="Vendor",
            )


class TestCheckSigningStatus:
    """Tests for check_signing_status method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked client."""
        svc = ESignService(
            api_key="key",
            api_secret="secret",
            base_url="https://api.foxit.com",
            webhook_secret="webhook",
            callback_url="https://app.com/callback",
        )
        svc.client = AsyncMock()
        return svc
    
    @pytest.mark.asyncio
    async def test_check_status_pending(self, service):
        """Test checking pending status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "pending",
            "signers": [
                {"email": "mgr@company.com", "status": "pending"},
            ],
        }
        mock_response.raise_for_status = Mock()
        service.client.get = AsyncMock(return_value=mock_response)
        
        result = await service.check_signing_status("REQ-001")
        
        assert result["status"] == ESignStatus.PENDING
        assert len(result["signers"]) == 1
    
    @pytest.mark.asyncio
    async def test_check_status_completed(self, service):
        """Test checking completed status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "completed",
            "signers": [
                {"email": "mgr@company.com", "status": "signed"},
                {"email": "cfo@company.com", "status": "signed"},
            ],
            "completed_at": "2026-01-15T14:00:00Z",
            "signed_document_url": "https://esign.foxit.com/docs/signed123.pdf",
        }
        mock_response.raise_for_status = Mock()
        service.client.get = AsyncMock(return_value=mock_response)
        
        result = await service.check_signing_status("REQ-002")
        
        assert result["status"] == ESignStatus.FULLY_SIGNED
        assert result["completed_at"] == "2026-01-15T14:00:00Z"
        assert "signed_document_url" in result
    
    @pytest.mark.asyncio
    async def test_check_status_partially_signed(self, service):
        """Test checking partially signed status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "in_progress",
            "signers": [
                {"email": "mgr@company.com", "status": "signed"},
                {"email": "cfo@company.com", "status": "pending"},
            ],
        }
        mock_response.raise_for_status = Mock()
        service.client.get = AsyncMock(return_value=mock_response)
        
        result = await service.check_signing_status("REQ-003")
        
        assert result["status"] == ESignStatus.PARTIALLY_SIGNED
    
    @pytest.mark.asyncio
    async def test_check_status_rejected(self, service):
        """Test checking rejected status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "declined",
            "signers": [
                {"email": "cfo@company.com", "status": "declined", "reason": "Amount discrepancy"},
            ],
        }
        mock_response.raise_for_status = Mock()
        service.client.get = AsyncMock(return_value=mock_response)
        
        result = await service.check_signing_status("REQ-004")
        
        assert result["status"] == ESignStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_check_status_expired(self, service):
        """Test checking expired status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "expired",
            "signers": [],
        }
        mock_response.raise_for_status = Mock()
        service.client.get = AsyncMock(return_value=mock_response)
        
        result = await service.check_signing_status("REQ-005")
        
        assert result["status"] == ESignStatus.EXPIRED


class TestCancelSigningRequest:
    """Tests for cancel_signing_request method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked client."""
        svc = ESignService(
            api_key="key",
            api_secret="secret",
            base_url="https://api.foxit.com",
            webhook_secret="webhook",
            callback_url="https://app.com/callback",
        )
        svc.client = AsyncMock()
        return svc
    
    @pytest.mark.asyncio
    async def test_cancel_request_success(self, service):
        """Test successful cancellation."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        service.client.post = AsyncMock(return_value=mock_response)
        
        result = await service.cancel_signing_request("REQ-001", reason="Invoice voided")
        
        assert result is True
        service.client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_request_includes_reason(self, service):
        """Test that cancellation includes reason."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        service.client.post = AsyncMock(return_value=mock_response)
        
        await service.cancel_signing_request("REQ-002", reason="Duplicate request")
        
        call_args = service.client.post.call_args
        payload = call_args.kwargs.get("json", call_args[1].get("json"))
        
        assert payload["reason"] == "Duplicate request"


class TestSendReminder:
    """Tests for send_reminder method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked client."""
        svc = ESignService(
            api_key="key",
            api_secret="secret",
            base_url="https://api.foxit.com",
            webhook_secret="webhook",
            callback_url="https://app.com/callback",
        )
        svc.client = AsyncMock()
        return svc
    
    @pytest.mark.asyncio
    async def test_send_reminder_success(self, service):
        """Test successful reminder sending."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        service.client.post = AsyncMock(return_value=mock_response)
        
        result = await service.send_reminder("REQ-001", "cfo@company.com")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_reminder_to_correct_signer(self, service):
        """Test that reminder is sent to correct email."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        service.client.post = AsyncMock(return_value=mock_response)
        
        await service.send_reminder("REQ-002", "approver@company.com")
        
        call_args = service.client.post.call_args
        payload = call_args.kwargs.get("json", call_args[1].get("json"))
        
        assert payload["signer_email"] == "approver@company.com"


class TestDownloadSignedDocument:
    """Tests for download_signed_document method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked client."""
        svc = ESignService(
            api_key="key",
            api_secret="secret",
            base_url="https://api.foxit.com",
            webhook_secret="webhook",
            callback_url="https://app.com/callback",
        )
        svc.client = AsyncMock()
        return svc
    
    @pytest.mark.asyncio
    async def test_download_signed_document_success(self, service, tmp_path):
        """Test successful document download."""
        output_path = tmp_path / "signed_invoice.pdf"
        
        mock_response = Mock()
        mock_response.content = b"%PDF-1.4 signed document content"
        mock_response.raise_for_status = Mock()
        service.client.get = AsyncMock(return_value=mock_response)
        
        result = await service.download_signed_document("REQ-001", str(output_path))
        
        assert result == str(output_path)
        assert output_path.exists()
        assert output_path.read_bytes() == b"%PDF-1.4 signed document content"
    
    @pytest.mark.asyncio
    async def test_download_http_error(self, service, tmp_path):
        """Test handling of HTTP error during download."""
        output_path = tmp_path / "signed_invoice.pdf"
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=Mock(),
                response=Mock(text="Document not found"),
            )
        )
        service.client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(httpx.HTTPStatusError):
            await service.download_signed_document("REQ-INVALID", str(output_path))


class TestESignEnums:
    """Tests for ESign enums."""
    
    def test_esign_status_values(self):
        """Test ESignStatus enum values."""
        assert ESignStatus.PENDING == "pending_signature"
        assert ESignStatus.PARTIALLY_SIGNED == "partially_signed"
        assert ESignStatus.FULLY_SIGNED == "fully_signed"
        assert ESignStatus.REJECTED == "rejected"
        assert ESignStatus.EXPIRED == "expired"
        assert ESignStatus.CANCELLED == "cancelled"
    
    def test_signer_role_values(self):
        """Test SignerRole enum values."""
        assert SignerRole.MANAGER == "manager"
        assert SignerRole.SENIOR_MANAGER == "senior_manager"
        assert SignerRole.CFO == "cfo"
        assert SignerRole.CONTROLLER == "controller"
