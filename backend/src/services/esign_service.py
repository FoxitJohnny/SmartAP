"""
Foxit eSign Integration Service
Phase 4.2: Electronic Signature for High-Value Invoices

Integrates with Foxit eSign API for threshold-based invoice approvals.
"""

import hashlib
import hmac
import httpx
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ESignStatus(str, Enum):
    """Electronic signature request status"""
    PENDING = "pending_signature"
    PARTIALLY_SIGNED = "partially_signed"
    FULLY_SIGNED = "fully_signed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignerRole(str, Enum):
    """Signer roles for approval workflow"""
    MANAGER = "manager"
    SENIOR_MANAGER = "senior_manager"
    CFO = "cfo"
    CONTROLLER = "controller"


class ESignService:
    """
    Service for managing electronic signatures via Foxit eSign API.
    
    Features:
    - Create signature requests for invoices
    - Track signing status
    - Handle webhook callbacks
    - Download signed documents
    - Manage approval workflows
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str,
        webhook_secret: str,
        callback_url: str,
    ):
        """
        Initialize eSign service.
        
        Args:
            api_key: Foxit eSign API key
            api_secret: Foxit eSign API secret
            base_url: Foxit eSign API base URL
            webhook_secret: Secret for webhook signature verification
            callback_url: URL for webhook callbacks
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.webhook_secret = webhook_secret
        self.callback_url = callback_url
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
            }
        )
    
    def _generate_auth_signature(self, timestamp: str, body: str = "") -> str:
        """
        Generate HMAC-SHA256 signature for API authentication.
        
        Args:
            timestamp: ISO timestamp
            body: Request body (for POST/PUT requests)
            
        Returns:
            Hex-encoded signature
        """
        message = f"{timestamp}{body}".encode('utf-8')
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from Foxit eSign.
        
        Args:
            payload: Webhook payload (raw string)
            signature: Signature from X-Signature header
            
        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    async def create_signing_request(
        self,
        invoice_id: str,
        document_path: str,
        signers: List[Dict[str, Any]],
        invoice_amount: float,
        invoice_number: str,
        vendor_name: str,
        expiration_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Create a new eSign request for an invoice.
        
        Args:
            invoice_id: Internal invoice ID
            document_path: Path to the PDF document
            signers: List of signer dictionaries with name, email, role
            invoice_amount: Invoice amount for display
            invoice_number: Invoice number
            vendor_name: Vendor name
            expiration_days: Days until request expires
            
        Returns:
            Dictionary with request_id, status, signer_urls
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Prepare document
            with open(document_path, 'rb') as f:
                document_content = f.read()
            
            # Build request payload
            payload = {
                "document": {
                    "name": f"Invoice_{invoice_number}_{vendor_name}.pdf",
                    "content": document_content.hex(),  # Hex-encoded binary
                },
                "signers": [
                    {
                        "name": signer["name"],
                        "email": signer["email"],
                        "role": signer.get("role", "signer"),
                        "order": idx + 1,  # Sequential signing
                    }
                    for idx, signer in enumerate(signers)
                ],
                "metadata": {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "invoice_amount": invoice_amount,
                    "vendor_name": vendor_name,
                },
                "settings": {
                    "expiration_days": expiration_days,
                    "reminder_enabled": True,
                    "reminder_days": [3, 1],  # Remind 3 days and 1 day before expiration
                    "sequential_signing": True,
                    "callback_url": self.callback_url,
                },
                "title": f"Invoice Approval - {invoice_number}",
                "message": f"Please review and sign the invoice from {vendor_name} for ${invoice_amount:,.2f}",
            }
            
            # Add authentication
            signature = self._generate_auth_signature(timestamp, str(payload))
            headers = {
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            }
            
            # Send request
            response = await self.client.post(
                "/signature-requests",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(
                f"Created eSign request for invoice {invoice_id}: {result.get('request_id')}"
            )
            
            return {
                "request_id": result["request_id"],
                "status": ESignStatus.PENDING,
                "signer_urls": result.get("signer_urls", []),
                "expires_at": result.get("expires_at"),
                "created_at": datetime.utcnow().isoformat(),
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create eSign request: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating eSign request: {str(e)}")
            raise
    
    async def check_signing_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check the current status of a signing request.
        
        Args:
            request_id: Foxit eSign request ID
            
        Returns:
            Dictionary with status, signers, completion info
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            signature = self._generate_auth_signature(timestamp)
            
            headers = {
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            }
            
            response = await self.client.get(
                f"/signature-requests/{request_id}",
                headers=headers,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Map status
            status_map = {
                "pending": ESignStatus.PENDING,
                "in_progress": ESignStatus.PARTIALLY_SIGNED,
                "completed": ESignStatus.FULLY_SIGNED,
                "declined": ESignStatus.REJECTED,
                "expired": ESignStatus.EXPIRED,
                "cancelled": ESignStatus.CANCELLED,
            }
            
            status = status_map.get(data["status"], ESignStatus.PENDING)
            
            return {
                "request_id": request_id,
                "status": status,
                "signers": data.get("signers", []),
                "completed_at": data.get("completed_at"),
                "signed_document_url": data.get("signed_document_url"),
                "metadata": data.get("metadata", {}),
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to check status for {request_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error checking signing status: {str(e)}")
            raise
    
    async def download_signed_document(
        self,
        request_id: str,
        output_path: str,
    ) -> str:
        """
        Download the signed document.
        
        Args:
            request_id: Foxit eSign request ID
            output_path: Path to save the signed document
            
        Returns:
            Path to the saved document
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            signature = self._generate_auth_signature(timestamp)
            
            headers = {
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            }
            
            response = await self.client.get(
                f"/signature-requests/{request_id}/download",
                headers=headers,
            )
            response.raise_for_status()
            
            # Save document
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded signed document for {request_id} to {output_path}")
            
            return output_path
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to download signed document: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error downloading signed document: {str(e)}")
            raise
    
    async def cancel_signing_request(self, request_id: str, reason: str = "") -> bool:
        """
        Cancel a pending signing request.
        
        Args:
            request_id: Foxit eSign request ID
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            payload = {"reason": reason}
            signature = self._generate_auth_signature(timestamp, str(payload))
            
            headers = {
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            }
            
            response = await self.client.post(
                f"/signature-requests/{request_id}/cancel",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            
            logger.info(f"Cancelled eSign request {request_id}: {reason}")
            
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel request {request_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error cancelling signing request: {str(e)}")
            raise
    
    async def send_reminder(self, request_id: str, signer_email: str) -> bool:
        """
        Send a reminder to a specific signer.
        
        Args:
            request_id: Foxit eSign request ID
            signer_email: Email of the signer to remind
            
        Returns:
            True if reminder sent successfully
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            payload = {"signer_email": signer_email}
            signature = self._generate_auth_signature(timestamp, str(payload))
            
            headers = {
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            }
            
            response = await self.client.post(
                f"/signature-requests/{request_id}/remind",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            
            logger.info(f"Sent reminder for {request_id} to {signer_email}")
            
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send reminder: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
            raise
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook callback from Foxit eSign.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Processed event data
        """
        try:
            event_type = payload.get("event")
            request_id = payload.get("request_id")
            
            logger.info(f"Received eSign webhook: {event_type} for {request_id}")
            
            # Map event types
            event_handlers = {
                "signature_request.signed": self._handle_signed_event,
                "signature_request.declined": self._handle_declined_event,
                "signature_request.completed": self._handle_completed_event,
                "signature_request.expired": self._handle_expired_event,
            }
            
            handler = event_handlers.get(event_type)
            if handler:
                return await handler(payload)
            
            logger.warning(f"Unhandled webhook event type: {event_type}")
            return {"processed": False, "reason": "Unknown event type"}
            
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            raise
    
    async def _handle_signed_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle individual signer completion"""
        return {
            "event": "signed",
            "request_id": payload["request_id"],
            "signer": payload.get("signer"),
            "signed_at": payload.get("signed_at"),
        }
    
    async def _handle_declined_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle signature decline"""
        return {
            "event": "declined",
            "request_id": payload["request_id"],
            "signer": payload.get("signer"),
            "reason": payload.get("reason"),
            "declined_at": payload.get("declined_at"),
        }
    
    async def _handle_completed_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fully signed document"""
        return {
            "event": "completed",
            "request_id": payload["request_id"],
            "completed_at": payload.get("completed_at"),
            "signed_document_url": payload.get("signed_document_url"),
        }
    
    async def _handle_expired_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle expired signature request"""
        return {
            "event": "expired",
            "request_id": payload["request_id"],
            "expired_at": payload.get("expired_at"),
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


def get_required_signers(invoice_amount: float) -> List[SignerRole]:
    """
    Determine required signers based on invoice amount thresholds.
    
    Threshold Rules:
    - < $5,000: Manager approval (no eSign)
    - $5,000 - $25,000: Senior Manager eSign
    - $25,000 - $100,000: CFO eSign
    - > $100,000: CFO + Controller eSign
    
    Args:
        invoice_amount: Invoice total amount
        
    Returns:
        List of required signer roles
    """
    if invoice_amount < 5000:
        return []  # No eSign required, standard approval
    elif invoice_amount < 25000:
        return [SignerRole.SENIOR_MANAGER]
    elif invoice_amount < 100000:
        return [SignerRole.CFO]
    else:
        return [SignerRole.CFO, SignerRole.CONTROLLER]


def calculate_expiration_date(days: int = 7) -> datetime:
    """
    Calculate expiration date for signature request.
    
    Args:
        days: Number of days until expiration
        
    Returns:
        Expiration datetime
    """
    return datetime.utcnow() + timedelta(days=days)
