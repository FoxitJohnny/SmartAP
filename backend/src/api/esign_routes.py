"""
eSign API Routes
Phase 4.2: Electronic Signature Endpoints

FastAPI routes for managing eSign requests and webhooks.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from ..db.session import get_session
from ..services.esign_service import ESignService, ESignStatus, get_required_signers
from ..models.esign import ESignRequest, ESignSigner, ESignAuditLog, ESignWebhook, SignerStatus
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/esign", tags=["esign"])


def get_esign_service() -> ESignService:
    """Dependency to get eSign service instance"""
    settings = get_settings()
    return ESignService(
        api_key=settings.foxit_esign_api_key,
        api_secret=settings.foxit_esign_api_secret,
        base_url=settings.foxit_esign_base_url,
        webhook_secret=settings.foxit_esign_webhook_secret,
        callback_url=settings.foxit_esign_callback_url,
    )


@router.post("/requests")
async def create_esign_request(
    invoice_id: str,
    signers: List[dict],
    session: AsyncSession = Depends(get_session),
    esign_service: ESignService = Depends(get_esign_service),
):
    """
    Create a new eSign request for an invoice.
    
    Args:
        invoice_id: Invoice document ID
        signers: List of signers with name, email, role
    
    Returns:
        Created eSign request details
    """
    try:
        # Get invoice details (placeholder - replace with actual DB query)
        invoice_number = f"INV-{invoice_id[:8]}"
        invoice_amount = 15000.00  # Placeholder
        vendor_name = "Acme Corp"  # Placeholder
        document_path = f"./uploads/{invoice_id}.pdf"  # Placeholder
        
        # Create Foxit eSign request
        foxit_result = await esign_service.create_signing_request(
            invoice_id=invoice_id,
            document_path=document_path,
            signers=signers,
            invoice_amount=invoice_amount,
            invoice_number=invoice_number,
            vendor_name=vendor_name,
        )
        
        # Save to database
        request_id = str(uuid.uuid4())
        db_request = ESignRequest(
            id=request_id,
            foxit_request_id=foxit_result["request_id"],
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            invoice_amount=invoice_amount,
            vendor_name=vendor_name,
            status=ESignStatus.PENDING,
            original_document_path=document_path,
            created_at=datetime.utcnow(),
            expires_at=datetime.fromisoformat(foxit_result["expires_at"]),
            title=f"Invoice Approval - {invoice_number}",
            message=f"Please review and sign invoice from {vendor_name}",
        )
        session.add(db_request)
        
        # Save signers
        for idx, signer in enumerate(signers):
            db_signer = ESignSigner(
                id=str(uuid.uuid4()),
                request_id=request_id,
                name=signer["name"],
                email=signer["email"],
                role=signer["role"],
                order=idx + 1,
                status=SignerStatus.PENDING,
                signer_url=foxit_result["signer_urls"][idx] if idx < len(foxit_result["signer_urls"]) else None,
            )
            session.add(db_signer)
        
        # Create audit log
        audit_log = ESignAuditLog(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type="request_created",
            event_timestamp=datetime.utcnow(),
            event_data={
                "invoice_id": invoice_id,
                "invoice_amount": invoice_amount,
                "signer_count": len(signers),
            },
        )
        session.add(audit_log)
        
        await session.commit()
        
        logger.info(f"Created eSign request {request_id} for invoice {invoice_id}")
        
        return {
            "request_id": request_id,
            "foxit_request_id": foxit_result["request_id"],
            "status": ESignStatus.PENDING,
            "signers": [
                {
                    "name": s["name"],
                    "email": s["email"],
                    "role": s["role"],
                    "order": idx + 1,
                }
                for idx, s in enumerate(signers)
            ],
            "expires_at": foxit_result["expires_at"],
        }
        
    except Exception as e:
        logger.error(f"Failed to create eSign request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requests/{request_id}")
async def get_esign_request(
    request_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get eSign request details and current status.
    
    Args:
        request_id: eSign request ID
    
    Returns:
        Request details with signers and status
    """
    try:
        # Query database (placeholder - implement actual query)
        return {
            "request_id": request_id,
            "status": ESignStatus.PENDING,
            "invoice_number": "INV-12345",
            "invoice_amount": 15000.00,
            "vendor_name": "Acme Corp",
            "signers": [],
            "created_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get eSign request: {str(e)}")
        raise HTTPException(status_code=404, detail="Request not found")


@router.post("/requests/{request_id}/cancel")
async def cancel_esign_request(
    request_id: str,
    reason: str,
    session: AsyncSession = Depends(get_session),
    esign_service: ESignService = Depends(get_esign_service),
):
    """
    Cancel a pending eSign request.
    
    Args:
        request_id: eSign request ID
        reason: Cancellation reason
    
    Returns:
        Cancellation confirmation
    """
    try:
        # Get request from DB (placeholder)
        foxit_request_id = "foxit-12345"
        
        # Cancel in Foxit
        await esign_service.cancel_signing_request(foxit_request_id, reason)
        
        # Update database (placeholder)
        # request.status = ESignStatus.CANCELLED
        # request.cancelled_at = datetime.utcnow()
        # request.cancellation_reason = reason
        
        logger.info(f"Cancelled eSign request {request_id}: {reason}")
        
        return {
            "request_id": request_id,
            "status": ESignStatus.CANCELLED,
            "cancelled_at": datetime.utcnow().isoformat(),
            "reason": reason,
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel eSign request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/requests/{request_id}/remind")
async def send_reminder(
    request_id: str,
    signer_email: str,
    session: AsyncSession = Depends(get_session),
    esign_service: ESignService = Depends(get_esign_service),
):
    """
    Send a reminder to a specific signer.
    
    Args:
        request_id: eSign request ID
        signer_email: Email of signer to remind
    
    Returns:
        Reminder confirmation
    """
    try:
        # Get request from DB (placeholder)
        foxit_request_id = "foxit-12345"
        
        # Send reminder
        await esign_service.send_reminder(foxit_request_id, signer_email)
        
        # Update database (placeholder)
        # signer.reminder_count += 1
        # signer.last_reminder_at = datetime.utcnow()
        
        logger.info(f"Sent reminder for {request_id} to {signer_email}")
        
        return {
            "request_id": request_id,
            "signer_email": signer_email,
            "reminder_sent_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to send reminder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks")
async def handle_esign_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
    esign_service: ESignService = Depends(get_esign_service),
):
    """
    Handle webhook callbacks from Foxit eSign.
    
    This endpoint receives notifications about signature events:
    - Document signed by individual signer
    - All signatures completed
    - Signature declined/rejected
    - Request expired
    
    Args:
        request: FastAPI request object
        x_signature: Webhook signature header
    
    Returns:
        Processing confirmation
    """
    try:
        # Get raw body
        body = await request.body()
        payload_str = body.decode('utf-8')
        
        # Verify signature
        if not x_signature:
            logger.warning("Webhook received without signature")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        if not esign_service.verify_webhook_signature(payload_str, x_signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        payload = await request.json()
        
        # Save webhook to database
        webhook_id = str(uuid.uuid4())
        webhook = ESignWebhook(
            id=webhook_id,
            foxit_request_id=payload.get("request_id", ""),
            event_type=payload.get("event", "unknown"),
            received_at=datetime.utcnow(),
            payload=payload,
            signature_valid=1,
        )
        session.add(webhook)
        
        # Process webhook
        result = await esign_service.handle_webhook(payload)
        
        # Update webhook status
        webhook.processed = 1
        webhook.processed_at = datetime.utcnow()
        
        # Create audit log
        audit_log = ESignAuditLog(
            id=str(uuid.uuid4()),
            request_id=payload.get("metadata", {}).get("invoice_id", ""),
            event_type=f"webhook_{payload.get('event', 'unknown')}",
            event_timestamp=datetime.utcnow(),
            event_data=result,
        )
        session.add(audit_log)
        
        await session.commit()
        
        logger.info(f"Processed webhook: {payload.get('event')} for {payload.get('request_id')}")
        
        return {"status": "processed", "webhook_id": webhook_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        
        # Save error
        if 'webhook' in locals():
            webhook.processing_error = str(e)
            await session.commit()
        
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/thresholds")
async def get_esign_thresholds():
    """
    Get current eSign approval thresholds.
    
    Returns:
        Threshold configuration and required approvers
    """
    settings = get_settings()
    
    return {
        "thresholds": {
            "manager": 0,  # No eSign
            "senior_manager": float(settings.esign_threshold_manager),
            "cfo": float(settings.esign_threshold_senior),
            "cfo_and_controller": float(settings.esign_threshold_cfo),
        },
        "rules": [
            {
                "range": "< $5,000",
                "required_approvers": ["Manager"],
                "requires_esign": False,
            },
            {
                "range": "$5,000 - $25,000",
                "required_approvers": ["Senior Manager"],
                "requires_esign": True,
            },
            {
                "range": "$25,000 - $100,000",
                "required_approvers": ["CFO"],
                "requires_esign": True,
            },
            {
                "range": "> $100,000",
                "required_approvers": ["CFO", "Controller"],
                "requires_esign": True,
            },
        ],
    }


@router.post("/check-threshold")
async def check_esign_threshold(invoice_amount: float):
    """
    Check if eSign is required for an invoice amount.
    
    Args:
        invoice_amount: Invoice total amount
    
    Returns:
        Required signers and eSign requirement
    """
    required_roles = get_required_signers(invoice_amount)
    
    return {
        "invoice_amount": invoice_amount,
        "requires_esign": len(required_roles) > 0,
        "required_signers": [role.value for role in required_roles],
        "signer_count": len(required_roles),
    }
