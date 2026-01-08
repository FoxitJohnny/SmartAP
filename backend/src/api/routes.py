"""
SmartAP API Routes

FastAPI endpoints for invoice processing.
"""

import os
import uuid
import logging
import aiofiles
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..models import InvoiceExtractionResult, InvoiceStatus, MatchingResult, RiskAssessment
from ..services import InvoiceExtractionAgent
from ..agents import POMatchingAgent, RiskDetectionAgent
from ..db import get_session, InvoiceRepository, PurchaseOrderRepository, VendorRepository, MatchingRepository, RiskRepository
from ..db.models import InvoiceDB
from ..orchestration import InvoiceProcessingOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["invoices"])


def get_extraction_agent(settings: Annotated[Settings, Depends(get_settings)]) -> InvoiceExtractionAgent:
    """Dependency to get extraction agent instance."""
    return InvoiceExtractionAgent(settings)


@router.post(
    "/invoices/upload",
    response_model=InvoiceExtractionResult,
    summary="Upload and extract invoice data",
    description="Upload a PDF invoice and extract structured data using AI.",
    responses={
        200: {"description": "Invoice extracted successfully"},
        400: {"description": "Invalid file type or size"},
        500: {"description": "Extraction failed"}
    }
)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="PDF invoice file (max 10MB)")],
    settings: Annotated[Settings, Depends(get_settings)],
    agent: Annotated[InvoiceExtractionAgent, Depends(get_extraction_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvoiceExtractionResult:
    """Upload and process an invoice PDF with AI extraction."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Validate file size
    max_size = settings.max_file_size_mb * 1024 * 1024
    content = await file.read()
    
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed ({settings.max_file_size_mb}MB)"
        )
    
    # Ensure upload directory exists
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file temporarily
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"
    
    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        # Extract invoice data
        result = await agent.extract(file_path, file.filename)
        
        # Save to database
        invoice_repo = InvoiceRepository(session)
        await invoice_repo.create(result)
        await session.commit()
        
        return result
        
    finally:
        # Clean up temporary file
        if file_path.exists():
            os.remove(file_path)


@router.get(
    "/invoices/{document_id}",
    response_model=InvoiceExtractionResult,
    summary="Retrieve invoice by ID",
    description="Get extracted invoice data by document ID",
    responses={
        200: {"description": "Invoice found"},
        404: {"description": "Invoice not found"}
    }
)
async def get_invoice(
    document_id: str,
    session: Annotated[AsyncSession, Depends(get_session)]
) -> InvoiceExtractionResult:
    """Get invoice extraction results by document ID."""
    invoice_repo = InvoiceRepository(session)
    invoice_db = await invoice_repo.get_by_id(document_id)
    
    if not invoice_db:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {document_id} not found"
        )
    
    # Convert DB model to response model
    return InvoiceExtractionResult(
        document_id=invoice_db.id,
        invoice_data=invoice_db.extracted_data or {},
        extraction_metadata={
            "confidence_scores": invoice_db.confidence_scores or {},
            "extraction_completed": invoice_db.extraction_completed or False,
        }
    )


@router.post(
    "/invoices/{document_id}/match",
    response_model=MatchingResult,
    summary="Match invoice to purchase order",
    description="Intelligently match an invoice to the most appropriate purchase order.",
    responses={
        200: {"description": "Matching completed"},
        400: {"description": "Invoice not extracted yet"},
        404: {"description": "Invoice not found"}
    }
)
async def match_invoice_to_po(
    document_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    use_ai: bool = True,
) -> MatchingResult:
    """Match invoice to purchase order with optional AI assistance."""
    # Get invoice from database
    invoice_repo = InvoiceRepository(session)
    invoice_db = await invoice_repo.get_by_id(document_id)
    
    if not invoice_db:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {document_id} not found"
        )
    
    # Check if invoice has extracted data
    if not invoice_db.invoice_data or invoice_db.status != InvoiceStatus.EXTRACTED:
        raise HTTPException(
            status_code=400,
            detail=f"Invoice {document_id} has not been successfully extracted"
        )
    
    # Convert to Pydantic model
    from ..models import Invoice
    invoice = Invoice.model_validate(invoice_db.invoice_data)
    
    # Initialize matching agent
    po_repo = PurchaseOrderRepository(session)
    vendor_repo = VendorRepository(session)
    matching_agent = POMatchingAgent(po_repo, vendor_repo)
    
    try:
        if use_ai:
            await matching_agent.initialize()
        
        # Perform matching
        result = await matching_agent.match_invoice(invoice, use_ai=use_ai)
        
        # Save matching result to database
        matching_repo = MatchingRepository(session)
        await matching_repo.save_result(document_id, result)
        await session.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Matching failed for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")


@router.post(
    "/invoices/{document_id}/assess-risk",
    response_model=RiskAssessment,
    summary="Assess invoice risk and detect fraud",
    description="Comprehensive risk assessment for invoice processing.",
    responses={
        200: {"description": "Risk assessment completed"},
        400: {"description": "Invoice not extracted yet"},
        404: {"description": "Invoice not found"}
    }
)
async def assess_invoice_risk(
    document_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    vendor_id: str = None,
) -> RiskAssessment:
    """Assess risk for an invoice."""
    # Get invoice from database
    invoice_repo = InvoiceRepository(session)
    invoice_db = await invoice_repo.get_by_id(document_id)
    
    if not invoice_db:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {document_id} not found"
        )
    
    # Check if invoice has extracted data
    if not invoice_db.invoice_data:
        raise HTTPException(
            status_code=400,
            detail=f"Invoice {document_id} has no extracted data"
        )
    
    # Initialize risk detection agent
    risk_repo = RiskRepository(session)
    vendor_repo = VendorRepository(session)
    risk_agent = RiskDetectionAgent(risk_repo, vendor_repo)
    
    try:
        await risk_agent.initialize()
        
        # Convert to Pydantic model
        from ..models import Invoice
        invoice = Invoice.model_validate(invoice_db.invoice_data)
        
        # Perform risk assessment
        result = await risk_agent.assess_risk(invoice, vendor_id=vendor_id)
        
        # Save risk result to database
        await risk_repo.save_assessment(document_id, result)
        await session.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Risk assessment failed for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")


@router.post(
    "/invoices/{document_id}/process",
    summary="Process invoice with full orchestration",
    description="Complete end-to-end invoice processing workflow.",
    responses={
        200: {"description": "Processing completed"},
        404: {"description": "Invoice not found"},
        500: {"description": "Processing failed"}
    }
)
async def process_invoice(
    document_id: str,
    vendor_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Process an invoice through the complete workflow."""
    try:
        # Create orchestrator
        orchestrator = InvoiceProcessingOrchestrator(session)
        
        # Process invoice through workflow
        final_state = await orchestrator.process_invoice(
            document_id=document_id,
            vendor_id=vendor_id,
        )
        
        # Build comprehensive response
        response_data = {
            "document_id": final_state["document_id"],
            "status": final_state["status"],
            "decision": final_state.get("decision"),
            "decision_reason": final_state.get("decision_reason", ""),
            "requires_manual_review": final_state.get("requires_manual_review", True),
            "recommended_actions": final_state.get("recommended_actions", []),
            "extraction": {
                "completed": final_state.get("extraction_completed", False),
                "confidence": final_state.get("extraction_confidence"),
                "invoice_data": final_state.get("invoice_data"),
                "error": final_state.get("extraction_error"),
            },
            "matching": {
                "completed": final_state.get("matching_completed", False),
                "match_score": final_state.get("match_score"),
                "match_type": final_state.get("match_type"),
                "matched_po_number": final_state.get("matched_po_number"),
                "discrepancies": final_state.get("discrepancies", []),
                "error": final_state.get("matching_error"),
            },
            "risk": {
                "completed": final_state.get("risk_completed", False),
                "risk_level": final_state.get("risk_level"),
                "risk_score": final_state.get("risk_score"),
                "is_duplicate": final_state.get("is_duplicate", False),
                "risk_flags": final_state.get("risk_flags", []),
                "error": final_state.get("risk_error"),
            },
            "metadata": {
                "processing_time_ms": final_state.get("processing_time_ms"),
                "ai_calls_made": final_state.get("ai_calls_made", 0),
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Processing failed for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get(
    "/invoices/{document_id}/status",
    summary="Get invoice processing status",
    description="Check the current processing status of an invoice.",
    responses={
        200: {"description": "Status retrieved"},
        404: {"description": "Invoice not found"},
        500: {"description": "Failed to retrieve status"}
    }
)
async def get_processing_status(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Get current processing status and progress for an invoice."""
    try:
        # Get invoice from database
        result = await session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == document_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        return JSONResponse({
            "document_id": document_id,
            "status": str(invoice.status) if invoice.status else "uploaded",
            "extraction_completed": invoice.extraction_completed or False,
            "matching_completed": False,
            "risk_completed": False,
            "decision": None,
            "processing_time_ms": None
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/invoices/{document_id}/reprocess",
    summary="Reprocess a failed or rejected invoice",
    description="Retry processing for invoices that failed or were rejected.",
    responses={
        200: {"description": "Reprocessing completed"},
        404: {"description": "Invoice not found"},
        500: {"description": "Reprocessing failed"}
    }
)
async def reprocess_invoice(
    document_id: str,
    vendor_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Reprocess invoice (clears previous results and re-runs workflow)."""
    try:
        # Get invoice from database
        result = await session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == document_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Reset invoice status
        invoice.status = InvoiceStatus.UPLOADED
        await session.commit()
        
        return JSONResponse({
            "document_id": document_id,
            "status": "uploaded",
            "message": "Invoice reset for reprocessing"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reprocess: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    tags=["health"],
    summary="API health check",
    description="Check if the API is running and healthy",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "smartap-api",
                        "version": "0.1.0"
                    }
                }
            }
        }
    }
)
async def health_check() -> dict:
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": "smartap-api",
        "version": "0.1.0",
    }

