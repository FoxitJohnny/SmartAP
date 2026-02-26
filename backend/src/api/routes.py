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
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..models import (
    InvoiceExtractionResult,
    InvoiceStatus,
    MatchingResult,
    RiskAssessment,
    MatchingSettings,
)
from ..services import InvoiceExtractionAgent
from ..agents import POMatchingAgent, RiskDetectionAgent
from ..db import get_session, InvoiceRepository, PurchaseOrderRepository, VendorRepository, MatchingRepository, RiskRepository
from ..db.models import InvoiceDB, MatchingResultDB, RiskAssessmentDB, MatchingSettingsDB, RiskSettingsDB
from .settings_routes import DEFAULT_MATCHING_SETTINGS, DEFAULT_RISK_SETTINGS
from ..orchestration import InvoiceProcessingOrchestrator
from ..services.processing_event_service import ProcessingEventService
from ..cache import default_invalidator

event_service = ProcessingEventService()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["invoices"])


def get_extraction_agent(settings: Annotated[Settings, Depends(get_settings)]) -> InvoiceExtractionAgent:
    """Dependency to get extraction agent instance."""
    return InvoiceExtractionAgent(settings)


async def _get_active_matching_settings(session: AsyncSession) -> MatchingSettings:
    """Get active matching settings, creating defaults if needed."""
    result = await session.execute(
        select(MatchingSettingsDB).where(MatchingSettingsDB.is_active == True)
    )
    settings_db = result.scalars().first()

    if not settings_db:
        settings_db = MatchingSettingsDB(name="active", is_active=True, **DEFAULT_MATCHING_SETTINGS)
        session.add(settings_db)
        await session.flush()

    return MatchingSettings(
        id=settings_db.id,
        name=settings_db.name,
        vendor_fuzzy_threshold=settings_db.vendor_fuzzy_threshold,
        vendor_match_weight=settings_db.vendor_match_weight,
        amount_tolerance_percent=settings_db.amount_tolerance_percent,
        amount_match_tolerance=getattr(settings_db, "amount_match_tolerance", 0.05),
        amount_match_weight=settings_db.amount_match_weight,
        date_tolerance_days=settings_db.date_tolerance_days,
        date_match_weight=settings_db.date_match_weight,
        line_items_match_weight=settings_db.line_items_match_weight,
        line_item_description_threshold=settings_db.line_item_description_threshold,
        line_item_amount_tolerance=settings_db.line_item_amount_tolerance,
        exact_match_threshold=settings_db.exact_match_threshold,
        good_match_threshold=getattr(settings_db, "good_match_threshold", 0.85),
        acceptable_match_threshold=settings_db.acceptable_match_threshold,
        review_threshold=settings_db.review_threshold,
        use_ai_for_ambiguous=settings_db.use_ai_for_ambiguous,
        ai_confidence_threshold=settings_db.ai_confidence_threshold,
        max_amount_discrepancy_for_auto_approve=settings_db.max_amount_discrepancy_for_auto_approve,
        critical_discrepancy_blocks_approval=settings_db.critical_discrepancy_blocks_approval,
        is_active=settings_db.is_active,
        created_at=settings_db.created_at,
        updated_at=settings_db.updated_at,
        updated_by=settings_db.updated_by,
    )


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
    
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )
    
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed ({settings.max_file_size_mb}MB)"
        )
    
    # Ensure upload directory exists
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file with document_id as filename for later retrieval
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"
    
    try:
        await event_service.emit(
            entity_type="invoice",
            entity_id=file_id,
            stage="upload",
            status="started",
            message="Invoice upload started",
            details={
                "original_filename": file.filename,
                "bytes": len(content),
            },
        )

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        await event_service.emit(
            entity_type="invoice",
            entity_id=file_id,
            stage="upload",
            status="succeeded",
            message="Invoice PDF saved",
            details={"path": str(file_path)},
        )
        
        # Extract invoice data
        await event_service.emit(
            entity_type="invoice",
            entity_id=file_id,
            stage="extract",
            status="started",
            message="Invoice extraction started",
        )
        result = await agent.extract(file_path, file.filename)

        await event_service.emit(
            entity_type="invoice",
            entity_id=file_id,
            stage="extract",
            status="succeeded",
            message="Invoice extraction completed",
            details={
                "status": str(getattr(result.status, "value", result.status)),
                "requires_review": bool(getattr(result, "requires_review", False)),
                "extraction_time_ms": getattr(result, "extraction_time_ms", None),
            },
        )
        
        # Update result with file id and API path for serving
        result.document_id = file_id
        result.file_path = f"/api/v1/invoices/{file_id}/pdf"
        
        # Save to database
        invoice_repo = InvoiceRepository(session)
        await invoice_repo.create(result)
        await session.commit()

        await event_service.emit(
            entity_type="invoice",
            entity_id=file_id,
            stage="persist",
            status="succeeded",
            message="Invoice persisted to database",
        )
        
        # Auto-run matching and risk assessment after extraction
        try:
            # Get matching settings
            matching_settings = await _get_active_matching_settings(session)
            
            # Create repositories
            po_repo = PurchaseOrderRepository(session)
            vendor_repo = VendorRepository(session)
            matching_repo = MatchingRepository(session)
            risk_repo = RiskRepository(session)
            
            # Run PO matching if we have invoice data
            matching_result = None  # Initialize for risk assessment
            if result.invoice:
                await event_service.emit(
                    entity_type="invoice",
                    entity_id=file_id,
                    stage="match",
                    status="started",
                    message="PO matching started",
                )
                
                try:
                    matching_agent = POMatchingAgent(
                        po_repository=po_repo,
                        vendor_repository=vendor_repo,
                        matching_settings=matching_settings,
                    )
                    matching_result = await matching_agent.match_invoice_to_po(
                        invoice=result.invoice,
                        use_ai_for_ambiguous=matching_settings.use_ai_for_ambiguous if matching_settings else True,
                    )
                    
                    # Update invoice_id to use document_id for DB foreign key
                    matching_result.invoice_id = file_id
                    
                    # Delete any existing matching results for this invoice (handles re-uploads)
                    await matching_repo.delete_by_invoice_id(file_id)
                    
                    # Save matching result
                    await matching_repo.create(matching_result)
                    
                    # Update invoice status based on matching result
                    invoice_db = await invoice_repo.get_by_id(file_id)
                    if invoice_db:
                        if matching_result.matched and not matching_result.requires_approval:
                            invoice_db.status = InvoiceStatus.MATCHED
                        elif matching_result.requires_approval:
                            invoice_db.status = InvoiceStatus.PENDING_APPROVAL
                    
                    await session.commit()
                    
                    await event_service.emit(
                        entity_type="invoice",
                        entity_id=file_id,
                        stage="match",
                        status="succeeded",
                        message="PO matching completed",
                        details={
                            "match_score": float(matching_result.match_score),
                            "match_type": str(matching_result.match_type),
                            "po_number": matching_result.po_number,
                            "matched": bool(matching_result.matched),
                        },
                    )
                except Exception as match_error:
                    logger.warning(f"Matching failed for {file_id}: {match_error}")
                    await event_service.emit(
                        entity_type="invoice",
                        entity_id=file_id,
                        stage="match",
                        status="failed",
                        level="WARNING",
                        message=f"PO matching failed: {str(match_error)}",
                    )
                
                # Run risk assessment
                await event_service.emit(
                    entity_type="invoice",
                    entity_id=file_id,
                    stage="risk",
                    status="started",
                    message="Risk assessment started",
                )
                
                try:
                    # Load risk settings from DB (or use defaults)
                    risk_settings_result = await session.execute(
                        select(RiskSettingsDB).where(RiskSettingsDB.is_active == True)
                    )
                    risk_settings_row = risk_settings_result.scalars().first()
                    if risk_settings_row:
                        risk_cfg = {
                            col: getattr(risk_settings_row, col)
                            for col in DEFAULT_RISK_SETTINGS
                            if hasattr(risk_settings_row, col)
                        }
                    else:
                        risk_cfg = dict(DEFAULT_RISK_SETTINGS)

                    risk_agent = RiskDetectionAgent(
                        invoice_repo=invoice_repo,
                        vendor_repo=vendor_repo,
                        settings=risk_cfg,
                    )

                    # Resolve vendor_id from extracted vendor name
                    resolved_vendor_id = None
                    if result.invoice.vendor_name:
                        try:
                            vendors = await vendor_repo.search_by_name(result.invoice.vendor_name)
                            if vendors:
                                # Prefer exact case-insensitive match
                                for v in vendors:
                                    if v.vendor_name.strip().lower() == result.invoice.vendor_name.strip().lower():
                                        resolved_vendor_id = v.vendor_id
                                        break
                                if not resolved_vendor_id:
                                    resolved_vendor_id = vendors[0].vendor_id
                        except Exception:
                            pass

                    # Set document_id on invoice so duplicate detector can exclude self
                    result.invoice.document_id = file_id

                    risk_assessment = await risk_agent.assess_risk(
                        invoice=result.invoice,
                        vendor_id=resolved_vendor_id,
                        matching_result=matching_result,
                    )
                    
                    # Update invoice_id to use document_id for DB foreign key
                    risk_assessment.invoice_id = file_id
                    
                    # Save risk assessment
                    await risk_repo.create(risk_assessment)

                    # Update invoice status based on risk level
                    risk_level_str = str(risk_assessment.risk_level).lower()
                    if risk_level_str in ("high", "critical"):
                        invoice_db = await invoice_repo.get_by_id(file_id)
                        if invoice_db:
                            invoice_db.status = InvoiceStatus.RISK_REVIEW
                            invoice_db.requires_review = True
                    elif risk_level_str == "medium":
                        invoice_db = await invoice_repo.get_by_id(file_id)
                        if invoice_db and invoice_db.status != InvoiceStatus.PENDING_APPROVAL:
                            invoice_db.status = InvoiceStatus.PENDING_APPROVAL

                    await session.commit()
                    
                    await event_service.emit(
                        entity_type="invoice",
                        entity_id=file_id,
                        stage="risk",
                        status="succeeded",
                        message="Risk assessment completed",
                        details={
                            "risk_level": str(risk_assessment.risk_level),
                            "risk_score": float(risk_assessment.risk_score),
                            "is_duplicate": bool(risk_assessment.duplicate_info is not None),
                        },
                    )
                except Exception as risk_error:
                    logger.warning(f"Risk assessment failed for {file_id}: {risk_error}")
                    await event_service.emit(
                        entity_type="invoice",
                        entity_id=file_id,
                        stage="risk",
                        status="failed",
                        level="WARNING",
                        message=f"Risk assessment failed: {str(risk_error)}",
                    )
        except Exception as post_process_error:
            # Log but don't fail the upload - extraction was successful
            logger.warning(f"Post-processing (matching/risk) failed for {file_id}: {post_process_error}")

        # Invalidate dashboard/analytics caches so new data shows immediately
        try:
            await default_invalidator.invalidate_dashboard()
            await default_invalidator.invalidate_analytics()
        except Exception:
            pass

        return result
        
    except Exception as e:
        await event_service.emit_error(
            entity_type="invoice",
            entity_id=file_id,
            stage="upload",
            message="Invoice upload/extraction failed",
            error=e,
        )
        # Clean up file on error
        if file_path.exists():
            os.remove(file_path)
        raise


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
    # Build Invoice object from invoice_data if available
    invoice_obj = None
    if invoice_db.invoice_data:
        from ..models import Invoice
        try:
            invoice_obj = Invoice(**invoice_db.invoice_data)
        except Exception:
            pass  # Invoice data may not be complete
    
    # Fetch latest risk assessment
    risk_assessment_data = None
    try:
        risk_result = await session.execute(
            select(RiskAssessmentDB)
            .where(RiskAssessmentDB.invoice_id == document_id)
            .order_by(desc(RiskAssessmentDB.assessed_at))
            .limit(1)
        )
        risk_db = risk_result.scalar_one_or_none()
        if risk_db:
            risk_level_str = risk_db.risk_level.value if hasattr(risk_db.risk_level, 'value') else str(risk_db.risk_level)
            risk_assessment_data = {
                "assessment_id": risk_db.assessment_id,
                "risk_score": float(risk_db.risk_score or 0),
                "risk_level": risk_level_str.upper() if isinstance(risk_level_str, str) else risk_level_str,
                "duplicate_risk_score": float(risk_db.duplicate_risk_score or 0),
                "vendor_risk_score": float(risk_db.vendor_risk_score or 0),
                "price_risk_score": float(risk_db.price_risk_score or 0),
                "amount_risk_score": float(risk_db.amount_risk_score or 0),
                "matching_risk_score": float(risk_db.matching_risk_score or 0),
                "pattern_risk_score": float(risk_db.pattern_risk_score or 0),
                "risk_flags": risk_db.risk_flags or [],
                "critical_flags": risk_db.critical_flags or 0,
                "high_flags": risk_db.high_flags or 0,
                "duplicate_info": risk_db.duplicate_info,
                "vendor_risk_info": risk_db.vendor_risk_info,
                "price_anomaly_info": risk_db.price_anomaly_info,
                "recommended_action": risk_db.recommended_action.value if hasattr(risk_db.recommended_action, 'value') else str(risk_db.recommended_action),
                "action_reason": risk_db.action_reason,
                "requires_manual_review": risk_db.requires_manual_review,
                "assessed_at": risk_db.assessed_at.isoformat() if risk_db.assessed_at else None,
                "assessed_by": risk_db.assessed_by,
                "assessment_version": risk_db.assessment_version,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch risk assessment for {document_id}: {e}")
    
    return InvoiceExtractionResult(
        document_id=invoice_db.document_id,
        file_name=invoice_db.file_name,
        file_hash=invoice_db.file_hash,
        file_path=f"/api/v1/invoices/{invoice_db.document_id}/pdf",
        status=invoice_db.status,
        invoice=invoice_obj,
        requires_review=invoice_db.requires_review,
        ocr_applied=invoice_db.ocr_applied,
        page_count=invoice_db.page_count,
        extraction_time_ms=invoice_db.extraction_time_ms,
        created_at=invoice_db.created_at,
        updated_at=invoice_db.updated_at,
        risk_assessment=risk_assessment_data,
    )


@router.get(
    "/invoices/{document_id}/pdf",
    summary="Get invoice PDF file",
    description="Get the original PDF file for an invoice",
    responses={
        200: {"description": "PDF file returned", "content": {"application/pdf": {}}},
        404: {"description": "Invoice or PDF not found"}
    }
)
async def get_invoice_pdf(
    document_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)]
):
    """Get the original PDF file for an invoice."""
    from fastapi.responses import FileResponse
    
    # Verify invoice exists
    invoice_repo = InvoiceRepository(session)
    invoice_db = await invoice_repo.get_by_id(document_id)
    
    if not invoice_db:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {document_id} not found"
        )
    
    # Find the PDF file
    upload_dir = Path(settings.upload_dir)
    pdf_path = upload_dir / f"{document_id}.pdf"
    
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF file for invoice {document_id} not found"
        )
    
    # Don't use filename parameter as it forces Content-Disposition: attachment
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"{invoice_db.file_name or f'{document_id}.pdf'}\"",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.head(
    "/invoices/{document_id}/pdf",
    include_in_schema=False,
)
async def head_invoice_pdf(
    document_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Return headers for the invoice PDF without a body."""
    from fastapi import Response

    invoice_repo = InvoiceRepository(session)
    invoice_db = await invoice_repo.get_by_id(document_id)

    if not invoice_db:
        raise HTTPException(status_code=404, detail=f"Invoice {document_id} not found")

    upload_dir = Path(settings.upload_dir)
    pdf_path = upload_dir / f"{document_id}.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF file for invoice {document_id} not found",
        )

    return Response(
        status_code=200,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": f"inline; filename=\"{invoice_db.file_name or f'{document_id}.pdf'}\"",
            "Cache-Control": "public, max-age=3600",
        },
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
    await event_service.emit(
        entity_type="invoice",
        entity_id=document_id,
        stage="match",
        status="started",
        message="PO matching started",
        details={"use_ai": bool(use_ai)},
    )
    # Get invoice from database
    invoice_repo = InvoiceRepository(session)
    invoice_db = await invoice_repo.get_by_id(document_id)
    
    if not invoice_db:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {document_id} not found"
        )
    
    # Check if invoice has extracted data
    # Allow re-running matching when the invoice is already pending approval.
    if not invoice_db.invoice_data or invoice_db.status not in (
        InvoiceStatus.EXTRACTED,
        InvoiceStatus.PENDING_APPROVAL,
    ):
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
    matching_settings = await _get_active_matching_settings(session)
    matching_agent = POMatchingAgent(po_repo, vendor_repo, matching_settings=matching_settings)
    
    try:
        effective_use_ai = bool(use_ai) and bool(matching_settings.use_ai_for_ambiguous)

        if effective_use_ai:
            await matching_agent.initialize()
        
        # Perform matching
        result = await matching_agent.match_invoice_to_po(invoice, use_ai_for_ambiguous=effective_use_ai)
        
        # Update invoice_id to use document_id for DB foreign key
        result.invoice_id = document_id
        
        # Save matching result to database
        matching_repo = MatchingRepository(session)
        await matching_repo.create(result)
        
        # Update invoice status based on matching result
        if result.matched:
            invoice_db.status = InvoiceStatus.MATCHED
        elif result.requires_approval:
            invoice_db.status = InvoiceStatus.PENDING_APPROVAL
        
        await session.commit()

        await event_service.emit(
            entity_type="invoice",
            entity_id=document_id,
            stage="match",
            status="succeeded",
            message="PO matching completed",
            details={
                "matched": bool(result.matched),
                "match_type": str(result.match_type),
                "match_score": float(result.match_score),
                "po_number": result.po_number,
                "requires_approval": bool(result.requires_approval),
            },
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Matching failed for {document_id}: {str(e)}")
        await event_service.emit_error(
            entity_type="invoice",
            entity_id=document_id,
            stage="match",
            message="PO matching failed",
            error=e,
        )
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")


@router.get(
    "/invoices/{document_id}/matching-result",
    response_model=MatchingResult,
    summary="Get latest PO matching result",
    description="Returns the most recent stored matching result (including any AI evaluation payload).",
    responses={
        200: {"description": "Latest matching result"},
        404: {"description": "No matching result found"},
    },
)
async def get_latest_matching_result(
    document_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchingResult:
    matching_repo = MatchingRepository(session)
    matching_db = await matching_repo.get_by_invoice_id(document_id)
    if not matching_db:
        raise HTTPException(status_code=404, detail=f"No matching result found for invoice {document_id}")

    po_number = matching_db.purchase_order.po_number if matching_db.purchase_order else None
    po_id = str(matching_db.purchase_order.id) if matching_db.purchase_order else None

    return MatchingResult(
        matching_id=matching_db.matching_id,
        invoice_id=matching_db.invoice_id,
        po_id=po_id,
        po_number=po_number,
        match_type=matching_db.match_type,
        match_score=matching_db.match_score,
        matched=matching_db.matched,
        vendor_match_score=matching_db.vendor_match_score,
        amount_match_score=matching_db.amount_match_score,
        date_match_score=matching_db.date_match_score,
        line_items_match_score=matching_db.line_items_match_score,
        line_item_matches=[],
        discrepancies=matching_db.discrepancies or [],
        has_discrepancies=matching_db.has_discrepancies,
        critical_discrepancies=matching_db.critical_discrepancies,
        requires_approval=matching_db.requires_approval,
        approval_reason=matching_db.approval_reason,
        candidate_pos=[],
        matching_algorithm="fuzzy_matching_v1",
        matched_at=matching_db.matched_at,
        matched_by=matching_db.matched_by,
        ai_evaluation=getattr(matching_db, "ai_evaluation", None),
    )


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
    await event_service.emit(
        entity_type="invoice",
        entity_id=document_id,
        stage="risk",
        status="started",
        message="Risk assessment started",
        details={"vendor_id": vendor_id},
    )
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
    invoice_repo = InvoiceRepository(session)
    risk_repo = RiskRepository(session)
    vendor_repo = VendorRepository(session)

    # Load risk settings from DB (or use defaults)
    risk_settings_result = await session.execute(
        select(RiskSettingsDB).where(RiskSettingsDB.is_active == True)
    )
    risk_settings_row = risk_settings_result.scalars().first()
    if risk_settings_row:
        risk_cfg = {
            col: getattr(risk_settings_row, col)
            for col in DEFAULT_RISK_SETTINGS
            if hasattr(risk_settings_row, col)
        }
    else:
        risk_cfg = dict(DEFAULT_RISK_SETTINGS)

    risk_agent = RiskDetectionAgent(invoice_repo, vendor_repo, settings=risk_cfg)
    
    try:
        # Convert to Pydantic model
        from ..models import Invoice
        invoice = Invoice.model_validate(invoice_db.invoice_data)
        
        # Perform risk assessment
        result = await risk_agent.assess_risk(invoice, vendor_id=vendor_id)
        
        # Update invoice_id to use document_id for DB foreign key
        result.invoice_id = document_id
        
        # Save risk result to database
        await risk_repo.create(result)
        await session.commit()

        await event_service.emit(
            entity_type="invoice",
            entity_id=document_id,
            stage="risk",
            status="succeeded",
            message="Risk assessment completed",
            details={
                "risk_level": str(result.risk_level),
                "risk_score": float(result.risk_score),
                "requires_manual_review": bool(result.requires_manual_review),
            },
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Risk assessment failed for {document_id}: {str(e)}")
        await event_service.emit_error(
            entity_type="invoice",
            entity_id=document_id,
            stage="risk",
            message="Risk assessment failed",
            error=e,
        )
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
    await event_service.emit(
        entity_type="invoice",
        entity_id=document_id,
        stage="orchestrate",
        status="started",
        message="Orchestrated processing started",
        details={"vendor_id": vendor_id},
    )
    completed_successfully = False
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
        
        completed_successfully = True
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Processing failed for {document_id}: {str(e)}")
        await event_service.emit_error(
            entity_type="invoice",
            entity_id=document_id,
            stage="orchestrate",
            message="Orchestrated processing failed",
            error=e,
        )
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    finally:
        # Best-effort completion marker (even if nodes logged their own events)
        await event_service.emit(
            entity_type="invoice",
            entity_id=document_id,
            stage="orchestrate",
            status="succeeded" if completed_successfully else "failed",
            message=(
                "Orchestrated processing finished" if completed_successfully else "Orchestrated processing ended with error"
            ),
        )


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
        
        # Determine extraction completion based on status
        # Extraction is complete if status is beyond INGESTED
        extraction_completed = invoice.status in (
            InvoiceStatus.EXTRACTED, InvoiceStatus.MATCHED, 
            InvoiceStatus.RISK_REVIEW, InvoiceStatus.APPROVED,
            InvoiceStatus.READY_FOR_PAYMENT, InvoiceStatus.ARCHIVED
        ) if invoice.status else False
        
        # Check for matching result
        matching_result = await session.execute(
            select(MatchingResultDB).where(MatchingResultDB.invoice_id == document_id)
        )
        matching_completed = matching_result.scalar_one_or_none() is not None
        
        # Check for risk assessment
        risk_result = await session.execute(
            select(RiskAssessmentDB).where(RiskAssessmentDB.invoice_id == document_id)
        )
        risk_completed = risk_result.scalar_one_or_none() is not None
        
        return JSONResponse({
            "document_id": document_id,
            "status": str(invoice.status.value) if invoice.status else "uploaded",
            "extraction_completed": extraction_completed,
            "matching_completed": matching_completed,
            "risk_completed": risk_completed,
            "decision": None,
            "processing_time_ms": invoice.extraction_time_ms
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
        invoice.status = InvoiceStatus.INGESTED
        await session.commit()
        
        return JSONResponse({
            "document_id": document_id,
            "status": "ingested",
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

