"""
SmartAP API Routes (Simplified for Docker startup)

FastAPI endpoints for invoice processing.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..models import InvoiceExtractionResult, InvoiceStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["invoices"])


@router.post(
    "/invoices/upload",
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
) -> JSONResponse:
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
    
    # Return placeholder response - actual extraction to be implemented
    document_id = str(uuid.uuid4())
    return JSONResponse({
        "document_id": document_id,
        "status": "uploaded",
        "message": "Invoice uploaded successfully. Extraction pending."
    })


@router.get(
    "/invoices/{document_id}",
    summary="Retrieve invoice by ID",
    description="Get extracted invoice data by document ID",
    responses={
        200: {"description": "Invoice found"},
        404: {"description": "Invoice not found"}
    }
)
async def get_invoice(document_id: str) -> JSONResponse:
    """Get invoice extraction results by document ID."""
    # Placeholder - to be implemented with database
    return JSONResponse({
        "document_id": document_id,
        "status": "pending",
        "message": "Database integration pending"
    })


@router.post(
    "/invoices/{document_id}/match",
    summary="Match invoice to purchase order",
    description="Intelligently match an invoice to the most appropriate purchase order.",
    responses={
        200: {"description": "Matching completed"},
        404: {"description": "Invoice not found"}
    }
)
async def match_invoice_to_po(document_id: str) -> JSONResponse:
    """Match invoice to purchase order."""
    return JSONResponse({
        "document_id": document_id,
        "status": "pending",
        "message": "Matching service pending"
    })


@router.post(
    "/invoices/{document_id}/assess-risk",
    summary="Assess invoice risk and detect fraud",
    description="Comprehensive risk assessment for invoice processing.",
    responses={
        200: {"description": "Risk assessment completed"},
        404: {"description": "Invoice not found"}
    }
)
async def assess_invoice_risk(document_id: str) -> JSONResponse:
    """Assess risk for an invoice."""
    return JSONResponse({
        "document_id": document_id,
        "status": "pending",
        "message": "Risk assessment service pending"
    })


@router.post(
    "/invoices/{document_id}/process",
    summary="Process invoice with full orchestration",
    description="Complete end-to-end invoice processing workflow.",
    responses={
        200: {"description": "Processing completed"},
        500: {"description": "Processing failed"}
    }
)
async def process_invoice(document_id: str) -> JSONResponse:
    """Process an invoice through the complete workflow."""
    return JSONResponse({
        "document_id": document_id,
        "status": "pending",
        "message": "Orchestration service pending"
    })


@router.get(
    "/invoices/{document_id}/status",
    summary="Get invoice processing status",
    description="Check the current processing status of an invoice.",
    responses={
        200: {"description": "Status retrieved"},
        404: {"description": "Invoice not found"}
    }
)
async def get_processing_status(document_id: str) -> JSONResponse:
    """Get current processing status and progress for an invoice."""
    return JSONResponse({
        "document_id": document_id,
        "status": "pending",
        "message": "Status service pending"
    })


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


@router.get(
    "/health/detailed",
    tags=["health"],
    summary="Detailed health check",
    description="Check health of all system components including database, cache, and services",
)
async def detailed_health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Comprehensive health check for all components."""
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "service": "smartap-api",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {},
    }
    
    issues = []
    
    # Check database
    try:
        from ..db.database import async_session_maker
        from sqlalchemy import text
        
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        health_status["components"]["database"] = {"status": "healthy", "type": "postgresql"}
    except Exception as e:
        health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        issues.append("database")
    
    # Check Redis cache
    try:
        import redis.asyncio as redis
        
        r = redis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.close()
        health_status["components"]["cache"] = {"status": "healthy", "type": "redis"}
    except Exception as e:
        health_status["components"]["cache"] = {"status": "unhealthy", "error": str(e)}
        issues.append("cache")
    
    # Check AI service
    if settings.ai_provider == "github" and settings.github_token:
        health_status["components"]["ai"] = {
            "status": "configured",
            "provider": "github_models",
            "model": settings.model_id,
        }
    elif settings.ai_provider == "openai" and settings.openai_api_key:
        health_status["components"]["ai"] = {
            "status": "configured",
            "provider": "openai",
            "model": settings.model_id,
        }
    else:
        health_status["components"]["ai"] = {
            "status": "not_configured",
            "message": "No AI credentials provided",
        }
    
    # Check OCR service
    if settings.foxit_api_key:
        health_status["components"]["ocr"] = {"status": "configured", "provider": "foxit"}
    else:
        health_status["components"]["ocr"] = {"status": "fallback", "provider": "pytesseract_or_none"}
    
    # Check upload directory
    upload_path = Path(settings.upload_dir)
    if upload_path.exists() and os.access(upload_path, os.W_OK):
        health_status["components"]["storage"] = {"status": "healthy", "path": str(upload_path)}
    else:
        health_status["components"]["storage"] = {"status": "unhealthy", "error": "Upload directory not writable"}
        issues.append("storage")
    
    # Overall status
    if issues:
        health_status["status"] = "degraded"
        health_status["issues"] = issues
    
    return health_status


@router.get(
    "/health/full",
    tags=["health"],
    summary="Full health check",
    description="Comprehensive health check including ERP, eSign, circuit breakers, and all components",
)
async def full_health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Full health check with all component statuses including integrations."""
    try:
        from ..utils.monitoring import get_health_checker
        checker = get_health_checker(settings)
        return await checker.get_full_health_report()
    except ImportError:
        # Fallback if monitoring module not available
        return await detailed_health_check(settings)


@router.get(
    "/metrics",
    tags=["health"],
    summary="Application metrics",
    description="Get application performance metrics including request stats and service call metrics",
)
async def get_metrics(
    minutes: int = 60,
) -> dict:
    """Get application metrics for the specified time window."""
    try:
        from ..utils.monitoring import get_metrics_collector
        collector = get_metrics_collector()
        return collector.get_summary(minutes=minutes)
    except ImportError:
        return {
            "error": "Metrics collector not available",
            "message": "Install monitoring module for metrics",
        }


@router.get(
    "/metrics/endpoints",
    tags=["health"],
    summary="Endpoint metrics",
    description="Get detailed metrics for each endpoint",
)
async def get_endpoint_metrics() -> dict:
    """Get detailed per-endpoint metrics."""
    try:
        from ..utils.monitoring import get_metrics_collector
        collector = get_metrics_collector()
        return {
            "endpoints": collector.get_endpoint_stats(),
        }
    except ImportError:
        return {
            "error": "Metrics collector not available",
        }


@router.get(
    "/metrics/circuit-breakers",
    tags=["health"],
    summary="Circuit breaker status",
    description="Get status of all circuit breakers for external service integrations",
)
async def get_circuit_breaker_status() -> dict:
    """Get current state of all circuit breakers."""
    try:
        from ..utils.circuit_breaker import CircuitBreaker
        states = CircuitBreaker.get_all_states()
        
        if not states:
            return {
                "status": "no_breakers",
                "message": "No circuit breakers registered yet",
                "breakers": {},
            }
        
        open_count = sum(1 for s in states.values() if s.value == "open")
        
        return {
            "status": "degraded" if open_count > 0 else "healthy",
            "open_count": open_count,
            "breakers": {name: state.value for name, state in states.items()},
        }
    except ImportError:
        return {
            "error": "Circuit breaker module not available",
        }
