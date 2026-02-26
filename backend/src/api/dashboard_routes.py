"""
SmartAP Dashboard API Routes

Provides endpoints for dashboard functionality with real database queries.
These endpoints serve the frontend dashboard with actual data from PostgreSQL.
Includes Redis caching for performance optimization.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, String
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from ..db.database import get_session
from ..db.models import InvoiceDB, VendorDB, PurchaseOrderDB, MatchingResultDB, RiskAssessmentDB
from ..models.invoice import InvoiceStatus
from ..models.purchase_order import POStatus
from ..models.vendor import VendorStatus
from ..cache import (
    cached,
    get_cache_service,
    CacheTTL,
    CachePrefix,
    default_invalidator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


# ============================================================================
# Response Models
# ============================================================================

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    limit: int
    pages: int


# ============================================================================
# Helper Functions
# ============================================================================

def invoice_to_dict(invoice: InvoiceDB, risk_assessment: Optional["RiskAssessmentDB"] = None) -> dict:
    """Convert InvoiceDB to dictionary for API response."""
    invoice_data = invoice.invoice_data or {}
    amount = float(invoice_data.get("total", 0))

    # Build risk fields from the latest risk assessment (if available)
    risk_score = 0.0
    risk_level = "low"
    risk_flags: list = []
    risk_assessment_data: Optional[dict] = None
    if risk_assessment:
        risk_score = float(risk_assessment.risk_score or 0)
        risk_level = risk_assessment.risk_level or "low"
        raw_flags = risk_assessment.risk_flags or []
        if isinstance(raw_flags, list):
            risk_flags = raw_flags
        # Build full risk assessment breakdown
        risk_assessment_data = {
            "assessment_id": risk_assessment.assessment_id,
            "risk_score": risk_score,
            "risk_level": str(risk_level).upper() if isinstance(risk_level, str) else risk_level.value.upper() if hasattr(risk_level, 'value') else str(risk_level).upper(),
            "duplicate_risk_score": float(risk_assessment.duplicate_risk_score or 0),
            "vendor_risk_score": float(risk_assessment.vendor_risk_score or 0),
            "price_risk_score": float(risk_assessment.price_risk_score or 0),
            "amount_risk_score": float(risk_assessment.amount_risk_score or 0),
            "matching_risk_score": float(risk_assessment.matching_risk_score or 0),
            "pattern_risk_score": float(risk_assessment.pattern_risk_score or 0),
            "risk_flags": risk_flags,
            "critical_flags": risk_assessment.critical_flags or 0,
            "high_flags": risk_assessment.high_flags or 0,
            "duplicate_info": risk_assessment.duplicate_info,
            "vendor_risk_info": risk_assessment.vendor_risk_info,
            "price_anomaly_info": risk_assessment.price_anomaly_info,
            "recommended_action": risk_assessment.recommended_action.value if hasattr(risk_assessment.recommended_action, 'value') else str(risk_assessment.recommended_action),
            "action_reason": risk_assessment.action_reason,
            "requires_manual_review": risk_assessment.requires_manual_review,
            "assessed_at": risk_assessment.assessed_at.isoformat() if risk_assessment.assessed_at else None,
            "assessed_by": risk_assessment.assessed_by,
            "assessment_version": risk_assessment.assessment_version,
        }

    return {
        "id": invoice.document_id,
        "invoice_number": invoice.invoice_number,
        "vendor_name": invoice_data.get("vendor_name", "Unknown"),
        "vendor_id": invoice_data.get("vendor_id"),
        "amount": amount,
        "total_amount": amount,  # Alias for frontend compatibility
        "currency": invoice_data.get("currency", "USD"),
        "invoice_date": invoice_data.get("invoice_date"),
        "due_date": invoice_data.get("due_date"),
        "status": invoice.status.value if invoice.status else "pending",
        "confidence_score": invoice.extraction_confidence,
        "has_risk_flags": invoice.requires_review or len(risk_flags) > 0,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "risk_assessment": risk_assessment_data,
        "po_number": invoice_data.get("po_number"),
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
    }


def vendor_to_dict(vendor: VendorDB, live_stats: Optional[dict] = None) -> dict:
    """Convert VendorDB to dictionary for API response.
    
    Args:
        vendor: The vendor database object.
        live_stats: Optional dict with keys computed from actual invoice data:
            - total_invoices, total_amount, last_invoice_date
    """
    risk_profile = vendor.risk_profile or {}

    # risk_score is stored on a 0-1 scale in seed data; convert to 0-100
    raw_score = risk_profile.get("risk_score", 0)
    risk_score = round(raw_score * 100) if 0 < raw_score <= 1.0 else round(raw_score)

    # Determine risk level based on 0-100 score
    if risk_score >= 75:
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Read aggregate stats from the risk_profile (seeded with realistic data)
    total_invoices = risk_profile.get("total_invoices_processed", 0)
    total_amount = risk_profile.get("total_amount_paid", 0.0)
    avg_invoice_amount = risk_profile.get("average_invoice_amount", 0.0)
    last_payment = risk_profile.get("last_payment_date")

    # Payment reliability is 0-1 in seed data; convert to percentage
    payment_reliability = risk_profile.get("payment_reliability_score", 1.0)
    on_time_rate = round(payment_reliability * 100, 1) if payment_reliability <= 1.0 else payment_reliability

    # Fraud / pricing derived from risk_profile
    fraud_flags = risk_profile.get("active_fraud_flags", 0)
    price_stability = risk_profile.get("price_stability_score", 1.0)
    price_variance_rate = round((1.0 - price_stability) * 100, 1) if price_stability <= 1.0 else 0.0

    # Overlay with live stats computed from actual invoice tables (if provided)
    stats = live_stats or {}
    if stats.get("total_invoices"):
        total_invoices = stats["total_invoices"]
    if stats.get("total_amount"):
        total_amount = stats["total_amount"]
    if stats.get("last_invoice_date"):
        last_payment = stats["last_invoice_date"]

    return {
        "id": vendor.vendor_id,
        "vendor_code": vendor.vendor_id,
        "name": vendor.vendor_name,
        "email": vendor.email,
        "phone": vendor.phone,
        "address": vendor.address_line1,
        "city": vendor.city,
        "state": vendor.state,
        "country": vendor.country,
        "tax_id": vendor.tax_id,
        "status": vendor.status.value if vendor.status else "active",
        "active": vendor.status == VendorStatus.ACTIVE if vendor.status else True,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "total_invoices": total_invoices,
        "total_amount": round(total_amount, 2),
        "avg_invoice_amount": round(avg_invoice_amount, 2),
        "on_time_payment_rate": on_time_rate,
        "duplicate_attempts": fraud_flags,
        "price_variance_rate": price_variance_rate,
        "created_date": vendor.created_at.isoformat() if vendor.created_at else None,
        "last_invoice_date": str(last_payment) if last_payment else None,
        "notes": vendor.notes,
    }


async def _get_vendor_name(vendor_id: str, session: AsyncSession) -> Optional[str]:
    """Resolve vendor_id (e.g. 'V001') to vendor_name for matching against invoice_data."""
    result = await session.execute(
        select(VendorDB.vendor_name).where(VendorDB.vendor_id == vendor_id)
    )
    return result.scalar_one_or_none()


def _invoice_belongs_to_vendor(inv: InvoiceDB, vendor_id: str, vendor_name: Optional[str]) -> bool:
    """Check if an invoice belongs to a vendor by vendor_id or vendor_name."""
    if not inv.invoice_data:
        return False
    data = inv.invoice_data
    # Match by vendor_id in invoice_data (if populated)
    if data.get("vendor_id") == vendor_id:
        return True
    # Match by vendor_name in invoice_data
    if vendor_name and data.get("vendor_name") and data["vendor_name"].strip().lower() == vendor_name.strip().lower():
        return True
    return False


def po_to_dict(po: PurchaseOrderDB) -> dict:
    """Convert PurchaseOrderDB to dictionary for API response."""
    # Count unique matched invoices
    matched_invoices = set()
    matched_amount = 0.0
    if po.matching_results:
        for mr in po.matching_results:
            if mr.matched and mr.invoice_id:
                matched_invoices.add(mr.invoice_id)
        # Sum amounts from matched invoices (would need invoice data)
        matched_amount = float(po.total_amount) * len(matched_invoices) if matched_invoices else 0
    
    # Build line_items array
    line_items = []
    if po.line_items:
        for item in po.line_items:
            line_items.append({
                "id": item.id,
                "line_number": item.line_number,
                "description": item.description,
                "quantity": float(item.quantity) if item.quantity else 0,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "total_amount": float(item.amount) if item.amount else 0,
                "sku": item.sku,
                "unit": item.unit,
                "received_quantity": float(item.received_quantity) if item.received_quantity else 0,
                "matched_quantity": 0,  # TODO: Calculate from matching
            })
    
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "vendor_name": po.vendor.vendor_name if po.vendor else "Unknown",
        "vendor_id": po.vendor_id,
        "amount": float(po.total_amount) if po.total_amount else 0,
        "total_amount": float(po.total_amount) if po.total_amount else 0,
        "matched_amount": matched_amount,
        "currency": po.currency,
        "status": po.status.value if po.status else "open",
        "order_date": po.created_date.isoformat() if po.created_date else None,
        "created_date": po.created_date.isoformat() if po.created_date else None,
        "expected_date": po.expected_delivery.isoformat() if po.expected_delivery else None,
        "expected_delivery_date": po.expected_delivery.isoformat() if po.expected_delivery else None,
        "received_amount": matched_amount,
        "matched_invoices_count": len(matched_invoices),
        "items_count": len(po.line_items) if po.line_items else 0,
        "line_items": line_items,
        "created_at": po.created_at.isoformat() if po.created_at else None,
        "created_by": po.created_by or "System",
        "last_updated": po.updated_at.isoformat() if po.updated_at else None,
        "notes": po.notes,
    }


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.get("/invoices", summary="List invoices with pagination")
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    vendor_name: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List invoices with pagination and filtering."""
    try:
        query = select(InvoiceDB)
        count_query = select(func.count(InvoiceDB.id))
        
        if status:
            try:
                status_enum = InvoiceStatus(status)
                query = query.where(InvoiceDB.status == status_enum)
                count_query = count_query.where(InvoiceDB.status == status_enum)
            except ValueError:
                pass
        
        if vendor_name:
            query = query.where(InvoiceDB.invoice_data["vendor_name"].astext.ilike(f"%{vendor_name}%"))
            count_query = count_query.where(InvoiceDB.invoice_data["vendor_name"].astext.ilike(f"%{vendor_name}%"))
        
        if search:
            search_filter = or_(
                InvoiceDB.invoice_number.ilike(f"%{search}%"),
                InvoiceDB.invoice_data["vendor_name"].astext.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        offset = (page - 1) * limit
        query = query.order_by(desc(InvoiceDB.created_at)).offset(offset).limit(limit)
        
        result = await session.execute(query)
        invoices = result.scalars().all()
        
        # Batch-load latest risk assessment for each invoice
        doc_ids = [inv.document_id for inv in invoices]
        risk_map: dict[str, RiskAssessmentDB] = {}
        if doc_ids:
            # Subquery to get the max assessed_at per invoice
            from sqlalchemy import tuple_
            latest_sub = (
                select(
                    RiskAssessmentDB.invoice_id,
                    func.max(RiskAssessmentDB.assessed_at).label("max_at"),
                )
                .where(RiskAssessmentDB.invoice_id.in_(doc_ids))
                .group_by(RiskAssessmentDB.invoice_id)
                .subquery()
            )
            risk_q = (
                select(RiskAssessmentDB)
                .join(
                    latest_sub,
                    and_(
                        RiskAssessmentDB.invoice_id == latest_sub.c.invoice_id,
                        RiskAssessmentDB.assessed_at == latest_sub.c.max_at,
                    ),
                )
            )
            risk_result = await session.execute(risk_q)
            for ra in risk_result.scalars().all():
                risk_map[ra.invoice_id] = ra

        items = [invoice_to_dict(inv, risk_map.get(inv.document_id)) for inv in invoices]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error listing invoices: {e}")
        return {"items": [], "total": 0, "page": page, "limit": limit, "pages": 0}


@router.get("/invoices/{invoice_id}", summary="Get invoice by ID")
async def get_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Get a single invoice by ID, including latest risk assessment."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    # Fetch latest risk assessment for this invoice
    risk_result = await session.execute(
        select(RiskAssessmentDB)
        .where(RiskAssessmentDB.invoice_id == invoice_id)
        .order_by(desc(RiskAssessmentDB.assessed_at))
        .limit(1)
    )
    risk_assessment = risk_result.scalar_one_or_none()

    return invoice_to_dict(invoice, risk_assessment=risk_assessment)


@router.put("/invoices/{invoice_id}", summary="Update invoice")
async def update_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Update an invoice."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    invoice.updated_at = datetime.utcnow()
    await session.commit()

    # Invalidate dashboard and analytics caches
    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()

    return invoice_to_dict(invoice)


@router.delete("/invoices/{invoice_id}", summary="Delete invoice")
async def delete_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Delete an invoice and invalidate caches."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    await session.delete(invoice)
    await session.commit()

    # Invalidate dashboard and analytics caches
    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()

    return {"success": True, "message": f"Invoice {invoice_id} deleted"}


@router.post("/invoices/{invoice_id}/approve", summary="Approve invoice")
async def approve_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Approve an invoice and invalidate relevant caches."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    invoice.status = InvoiceStatus.APPROVED
    invoice.updated_at = datetime.utcnow()
    await session.commit()
    
    # Invalidate dashboard and analytics caches
    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()
    
    return invoice_to_dict(invoice)


@router.post("/invoices/{invoice_id}/reject", summary="Reject invoice")
async def reject_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Reject an invoice and invalidate relevant caches."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    invoice.status = InvoiceStatus.REJECTED
    invoice.updated_at = datetime.utcnow()
    await session.commit()
    
    # Invalidate dashboard and analytics caches
    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()
    
    return invoice_to_dict(invoice)


# ============================================================================
# Vendor Endpoints
# ============================================================================

@router.get("/vendors", summary="List vendors with pagination")
async def list_vendors(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List vendors with pagination and filtering."""
    try:
        query = select(VendorDB)
        count_query = select(func.count(VendorDB.id))
        
        if status:
            try:
                status_enum = VendorStatus(status)
                query = query.where(VendorDB.status == status_enum)
                count_query = count_query.where(VendorDB.status == status_enum)
            except ValueError:
                pass
        
        if search:
            search_filter = or_(
                VendorDB.vendor_name.ilike(f"%{search}%"),
                VendorDB.email.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        offset = (page - 1) * limit
        query = query.order_by(VendorDB.vendor_name).offset(offset).limit(limit)
        
        result = await session.execute(query)
        vendors = result.scalars().all()

        # Compute live invoice stats per vendor via PO → MatchingResult → Invoice
        vendor_ids = [v.vendor_id for v in vendors]
        live_stats_map: dict[str, dict] = {}
        if vendor_ids:
            stats_query = (
                select(
                    PurchaseOrderDB.vendor_id,
                    func.count(InvoiceDB.id).label("cnt"),
                    func.coalesce(func.sum(InvoiceDB.extraction_confidence), 0),  # placeholder col
                    func.max(InvoiceDB.created_at).label("last_date"),
                )
                .select_from(MatchingResultDB)
                .join(PurchaseOrderDB, PurchaseOrderDB.id == MatchingResultDB.po_id)
                .join(InvoiceDB, InvoiceDB.document_id == MatchingResultDB.invoice_id)
                .where(PurchaseOrderDB.vendor_id.in_(vendor_ids))
                .group_by(PurchaseOrderDB.vendor_id)
            )
            stats_result = await session.execute(stats_query)
            for row in stats_result.fetchall():
                vid, cnt, _, last_dt = row
                live_stats_map[vid] = {
                    "total_invoices": cnt,
                    "last_invoice_date": last_dt.strftime("%Y-%m-%d") if last_dt else None,
                }

            # Compute total amount per vendor from invoice_data JSON
            # This requires iterating since total_amount lives in a JSON column
            amt_query = (
                select(
                    PurchaseOrderDB.vendor_id,
                    InvoiceDB.invoice_data,
                )
                .select_from(MatchingResultDB)
                .join(PurchaseOrderDB, PurchaseOrderDB.id == MatchingResultDB.po_id)
                .join(InvoiceDB, InvoiceDB.document_id == MatchingResultDB.invoice_id)
                .where(PurchaseOrderDB.vendor_id.in_(vendor_ids))
            )
            amt_result = await session.execute(amt_query)
            vendor_amounts: dict[str, float] = {}
            for row in amt_result.fetchall():
                vid = row[0]
                inv_data = row[1] or {}
                amount = float(inv_data.get("total_amount", 0) or 0)
                vendor_amounts[vid] = vendor_amounts.get(vid, 0.0) + amount
            for vid, total_amt in vendor_amounts.items():
                if vid in live_stats_map:
                    live_stats_map[vid]["total_amount"] = round(total_amt, 2)

        items = [vendor_to_dict(v, live_stats_map.get(v.vendor_id)) for v in vendors]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error listing vendors: {e}")
        return {"items": [], "total": 0, "page": page, "limit": limit, "pages": 0}


@router.get("/vendors/{vendor_id}", summary="Get vendor by ID")
async def get_vendor(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get a single vendor by ID."""
    result = await session.execute(
        select(VendorDB).where(VendorDB.vendor_id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")

    # Compute live invoice stats for this single vendor
    live_stats: dict = {}
    stats_q = (
        select(
            func.count(InvoiceDB.id).label("cnt"),
            func.max(InvoiceDB.created_at).label("last_date"),
        )
        .select_from(MatchingResultDB)
        .join(PurchaseOrderDB, PurchaseOrderDB.id == MatchingResultDB.po_id)
        .join(InvoiceDB, InvoiceDB.document_id == MatchingResultDB.invoice_id)
        .where(PurchaseOrderDB.vendor_id == vendor_id)
    )
    sr = await session.execute(stats_q)
    row = sr.first()
    if row and row[0]:
        live_stats["total_invoices"] = row[0]
        live_stats["last_invoice_date"] = row[1].strftime("%Y-%m-%d") if row[1] else None

    # Sum amounts from invoice_data JSON
    amt_q = (
        select(InvoiceDB.invoice_data)
        .select_from(MatchingResultDB)
        .join(PurchaseOrderDB, PurchaseOrderDB.id == MatchingResultDB.po_id)
        .join(InvoiceDB, InvoiceDB.document_id == MatchingResultDB.invoice_id)
        .where(PurchaseOrderDB.vendor_id == vendor_id)
    )
    amt_r = await session.execute(amt_q)
    total_amt = sum(float((r[0] or {}).get("total_amount", 0) or 0) for r in amt_r.fetchall())
    if total_amt > 0:
        live_stats["total_amount"] = round(total_amt, 2)

    return vendor_to_dict(vendor, live_stats)


class VendorCreateRequest(BaseModel):
    """Request body for creating a vendor."""
    vendor_id: str
    vendor_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "US"
    tax_id: Optional[str] = None
    status: str = "active"


@router.post("/vendors", summary="Create vendor")
async def create_vendor(request: VendorCreateRequest, session: AsyncSession = Depends(get_session)):
    """Create a new vendor."""
    # Check if vendor_id already exists
    existing = await session.execute(
        select(VendorDB).where(VendorDB.vendor_id == request.vendor_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Vendor {request.vendor_id} already exists")
    
    # Create vendor
    vendor = VendorDB(
        vendor_id=request.vendor_id,
        vendor_name=request.vendor_name,
        email=request.email,
        phone=request.phone,
        address_line1=request.address_line1,
        city=request.city,
        state=request.state,
        country=request.country,
        tax_id=request.tax_id,
        status=VendorStatus.ACTIVE if request.status == "active" else VendorStatus.INACTIVE,
        onboarded_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()

    return vendor_to_dict(vendor)


@router.put("/vendors/{vendor_id}", summary="Update vendor")
async def update_vendor(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Update a vendor."""
    result = await session.execute(
        select(VendorDB).where(VendorDB.vendor_id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    vendor.updated_at = datetime.utcnow()
    await session.commit()

    await default_invalidator.invalidate_dashboard()

    return vendor_to_dict(vendor)


@router.post("/vendors/{vendor_id}/activate", summary="Activate vendor")
async def activate_vendor(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Activate a vendor."""
    result = await session.execute(
        select(VendorDB).where(VendorDB.vendor_id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    vendor.status = VendorStatus.ACTIVE
    vendor.updated_at = datetime.utcnow()
    await session.commit()

    await default_invalidator.invalidate_dashboard()

    return vendor_to_dict(vendor)


@router.post("/vendors/{vendor_id}/deactivate", summary="Deactivate vendor")
async def deactivate_vendor(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Deactivate a vendor."""
    result = await session.execute(
        select(VendorDB).where(VendorDB.vendor_id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    vendor.status = VendorStatus.INACTIVE
    vendor.updated_at = datetime.utcnow()
    await session.commit()

    await default_invalidator.invalidate_dashboard()

    return vendor_to_dict(vendor)


@router.get("/vendors/{vendor_id}/invoices", summary="Get vendor invoices")
async def get_vendor_invoices(vendor_id: str, page: int = 1, limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Get invoices for a specific vendor."""
    vendor_name = await _get_vendor_name(vendor_id, session)
    
    # Get all invoices and filter in Python (SQLite doesn't support .astext)
    result = await session.execute(
        select(InvoiceDB).order_by(desc(InvoiceDB.created_at))
    )
    all_invoices = result.scalars().all()
    
    # Filter by vendor_id or vendor_name in Python
    vendor_invoices = [
        inv for inv in all_invoices
        if _invoice_belongs_to_vendor(inv, vendor_id, vendor_name)
    ]
    
    total = len(vendor_invoices)
    offset = (page - 1) * limit
    paginated = vendor_invoices[offset:offset + limit]
    
    return {
        "data": [invoice_to_dict(inv) for inv in paginated],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/vendors/{vendor_id}/risk-events", summary="Get vendor risk events")
async def get_vendor_risk_events(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get risk events for a vendor."""
    vendor_name = await _get_vendor_name(vendor_id, session)
    
    # Get all risk assessments with their invoices - filter in Python for SQLite compatibility
    result = await session.execute(
        select(RiskAssessmentDB, InvoiceDB)
        .join(InvoiceDB, RiskAssessmentDB.invoice_id == InvoiceDB.document_id)
        .order_by(desc(RiskAssessmentDB.assessed_at))
    )
    rows = result.all()
    
    events = []
    event_id = 1
    for assessment, invoice in rows:
        # Filter by vendor_id or vendor_name in Python
        if _invoice_belongs_to_vendor(invoice, vendor_id, vendor_name):
            if assessment.risk_flags:
                for flag in assessment.risk_flags:
                    events.append({
                        "id": event_id,
                        "event_type": flag.get("type", "unknown"),
                        "severity": flag.get("severity", "low"),
                        "description": flag.get("description", flag.get("type", "Risk flag detected")),
                        "date": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
                        "resolved": flag.get("resolved", False),
                        "resolved_date": flag.get("resolved_date", None),
                    })
                    event_id += 1
    return events[:20]


@router.get("/vendors/{vendor_id}/risk-history", summary="Get vendor risk history")
async def get_vendor_risk_history(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get risk score history for a vendor."""
    vendor_name = await _get_vendor_name(vendor_id, session)
    
    # Get all risk assessments with their invoices - filter in Python for SQLite compatibility
    result = await session.execute(
        select(RiskAssessmentDB, InvoiceDB)
        .join(InvoiceDB, RiskAssessmentDB.invoice_id == InvoiceDB.document_id)
        .order_by(desc(RiskAssessmentDB.assessed_at))
    )
    rows = result.all()
    
    # Filter by vendor_id or vendor_name in Python
    vendor_assessments = [
        assessment for assessment, invoice in rows
        if _invoice_belongs_to_vendor(invoice, vendor_id, vendor_name)
    ][:12]
    
    return [
        {"date": a.assessed_at.isoformat() if a.assessed_at else None, "risk_score": a.risk_score}
        for a in vendor_assessments
    ]


@router.get("/vendors/{vendor_id}/performance", summary="Get vendor performance")
async def get_vendor_performance(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get performance metrics for a vendor."""
    vendor_name = await _get_vendor_name(vendor_id, session)
    
    # Get all invoices and filter in Python for SQLite compatibility
    result = await session.execute(select(InvoiceDB))
    all_invoices = result.scalars().all()
    
    vendor_invoices = [
        inv for inv in all_invoices
        if _invoice_belongs_to_vendor(inv, vendor_id, vendor_name)
    ]
    total_invoices = len(vendor_invoices)
    approved = len([inv for inv in vendor_invoices if inv.status == InvoiceStatus.APPROVED])
    
    po_count = await session.execute(
        select(func.count(PurchaseOrderDB.id)).where(PurchaseOrderDB.vendor_id == vendor_id)
    )
    total_orders = po_count.scalar() or 0
    
    return {
        "duplicate_attempts": 0,
        "price_variance_rate": 0.0,
        "rejection_rate": round((1 - approved / total_invoices) * 100, 1) if total_invoices > 0 else 0.0,
        "avg_processing_time": 0.0,
        "avg_days_to_pay": 0.0,
        "on_time_delivery_rate": round(approved / total_invoices, 2) if total_invoices > 0 else 0,
        "total_orders": total_orders,
        "total_value": 0,
    }


@router.get("/vendors/{vendor_id}/purchase-orders", summary="Get vendor purchase orders")
async def get_vendor_purchase_orders(vendor_id: str, page: int = 1, limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Get purchase orders for a specific vendor."""
    count_result = await session.execute(
        select(func.count(PurchaseOrderDB.id)).where(PurchaseOrderDB.vendor_id == vendor_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * limit
    result = await session.execute(
        select(PurchaseOrderDB)
        .options(
            selectinload(PurchaseOrderDB.vendor),
            selectinload(PurchaseOrderDB.line_items),
            selectinload(PurchaseOrderDB.matching_results),
        )
        .where(PurchaseOrderDB.vendor_id == vendor_id)
        .order_by(desc(PurchaseOrderDB.created_at))
        .offset(offset)
        .limit(limit)
    )
    pos = result.scalars().all()

    return {
        "data": [po_to_dict(po) for po in pos],
        "total": total,
        "page": page,
        "limit": limit,
    }


# ============================================================================
# Purchase Order Endpoints
# ============================================================================

@router.get("/purchase-orders", summary="List purchase orders")
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List purchase orders with pagination."""
    try:
        query = select(PurchaseOrderDB).options(
            selectinload(PurchaseOrderDB.vendor),
            selectinload(PurchaseOrderDB.line_items),
            selectinload(PurchaseOrderDB.matching_results),
        )
        count_query = select(func.count(PurchaseOrderDB.id))
        
        if status:
            try:
                status_enum = POStatus(status)
                query = query.where(PurchaseOrderDB.status == status_enum)
                count_query = count_query.where(PurchaseOrderDB.status == status_enum)
            except ValueError:
                pass
        
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        offset = (page - 1) * limit
        query = query.order_by(desc(PurchaseOrderDB.created_at)).offset(offset).limit(limit)
        
        result = await session.execute(query)
        pos = result.scalars().all()
        
        items = [po_to_dict(po) for po in pos]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error listing purchase orders: {e}")
        return {"items": [], "total": 0, "page": page, "limit": limit, "pages": 0}


@router.get("/purchase-orders/{po_id}", summary="Get purchase order by ID")
async def get_purchase_order(po_id: str, session: AsyncSession = Depends(get_session)):
    """Get a single purchase order by ID."""
    result = await session.execute(
        select(PurchaseOrderDB)
        .where(PurchaseOrderDB.po_number == po_id)
        .options(
            selectinload(PurchaseOrderDB.vendor),
            selectinload(PurchaseOrderDB.line_items),
            selectinload(PurchaseOrderDB.matching_results),
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    return po_to_dict(po)


@router.get(
    "/purchase-orders/{po_id}/pdf",
    summary="Get purchase order as PDF",
    description="Generate a printable PDF representation of a purchase order.",
    responses={
        200: {"description": "PDF file returned", "content": {"application/pdf": {}}},
        404: {"description": "Purchase order not found"},
    },
)
async def get_purchase_order_pdf(po_id: str, session: AsyncSession = Depends(get_session)):
    """Generate a PO PDF on the fly for human review workflows."""
    from io import BytesIO
    from fastapi.responses import StreamingResponse

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
    except Exception as e:
        logger.error(f"reportlab not available for PO PDF generation: {e}")
        raise HTTPException(status_code=500, detail="PDF generation is not available")

    result = await session.execute(
        select(PurchaseOrderDB)
        .where(PurchaseOrderDB.po_number == po_id)
        .options(
            selectinload(PurchaseOrderDB.vendor),
            selectinload(PurchaseOrderDB.line_items),
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")

    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"Purchase Order {po.po_number}")

    elements = []
    elements.append(Paragraph(f"Purchase Order {po.po_number}", styles["Title"]))
    elements.append(Spacer(1, 12))

    header_rows = [
        ["PO Number", po.po_number],
        ["Vendor", (po.vendor.vendor_name if po.vendor else "N/A")],
        ["Status", (po.status.value if po.status else "N/A")],
        ["Currency", (po.currency or "USD")],
        ["Total Amount", f"{float(po.total_amount or 0):,.2f}"],
        ["Order Date", (po.created_date.isoformat() if po.created_date else "N/A")],
        ["Expected Delivery", (po.expected_delivery.isoformat() if po.expected_delivery else "N/A")],
    ]

    header_table = Table(header_rows, colWidths=[140, 380])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(header_table)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Line Items", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    line_items = list(po.line_items or [])
    if not line_items:
        elements.append(Paragraph("No line items.", styles["Normal"]))
    else:
        line_rows = [["Line", "Description", "Qty", "Unit Price", "Total"]]
        for li in line_items:
            line_total = getattr(li, "amount", None)
            if line_total is None:
                line_total = float(li.quantity or 0) * float(li.unit_price or 0)
            line_rows.append(
                [
                    str(li.line_number or ""),
                    (li.description or ""),
                    f"{float(li.quantity or 0):g}",
                    f"{float(li.unit_price or 0):,.2f}",
                    f"{float(line_total or 0):,.2f}",
                ]
            )

        lines_table = Table(line_rows, colWidths=[40, 260, 60, 80, 80])
        lines_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(lines_table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"PO-{po.po_number}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"{filename}\"",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.head(
    "/purchase-orders/{po_id}/pdf",
    include_in_schema=False,
)
async def head_purchase_order_pdf(po_id: str, session: AsyncSession = Depends(get_session)):
    """Return headers for the PO PDF without a body."""
    from fastapi import Response

    result = await session.execute(select(PurchaseOrderDB.po_number).where(PurchaseOrderDB.po_number == po_id))
    exists = result.scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")

    return Response(
        status_code=200,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": f"inline; filename=\"PO-{po_id}.pdf\"",
            "Cache-Control": "public, max-age=3600",
        },
    )


class POCreateRequest(BaseModel):
    """Request body for creating a purchase order."""
    po_number: str
    vendor_id: str
    total_amount: float
    currency: str = "USD"
    status: str = "open"
    order_date: Optional[str] = None
    expected_date: Optional[str] = None


@router.post("/purchase-orders", summary="Create purchase order")
async def create_purchase_order(request: POCreateRequest, session: AsyncSession = Depends(get_session)):
    """Create a new purchase order."""
    from ..models.purchase_order import POStatus
    from decimal import Decimal
    
    # Check if PO number already exists
    existing_result = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == request.po_number)
    )
    if existing_result.scalars().first():
        raise HTTPException(status_code=400, detail=f"PO {request.po_number} already exists")
    
    # Verify vendor exists
    vendor_result = await session.execute(
        select(VendorDB).where(VendorDB.vendor_id == request.vendor_id)
    )
    if not vendor_result.scalars().first():
        raise HTTPException(status_code=400, detail=f"Vendor {request.vendor_id} not found")
    
    # Parse dates
    order_date = datetime.strptime(request.order_date, "%Y-%m-%d").date() if request.order_date else datetime.utcnow().date()
    expected_date = datetime.strptime(request.expected_date, "%Y-%m-%d").date() if request.expected_date else (datetime.utcnow() + timedelta(days=30)).date()
    
    # Parse status
    status_map = {
        "open": POStatus.OPEN,
        "partial": POStatus.PARTIALLY_RECEIVED,
        "partially_received": POStatus.PARTIALLY_RECEIVED,
        "closed": POStatus.CLOSED,
        "cancelled": POStatus.CANCELLED
    }
    po_status = status_map.get(request.status.lower(), POStatus.OPEN)
    
    # Create PO
    po = PurchaseOrderDB(
        po_number=request.po_number,
        vendor_id=request.vendor_id,
        total_amount=Decimal(str(request.total_amount)),
        subtotal=Decimal(str(request.total_amount * 0.9)),  # Assume 10% tax
        tax=Decimal(str(request.total_amount * 0.1)),
        currency=request.currency,
        status=po_status,
        created_date=order_date,
        expected_delivery=expected_date,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(po)
    await session.flush()  # Get the po.id
    
    # Add default line item (required for matching)
    from ..db.models import POLineItemDB
    line_item = POLineItemDB(
        po_id=po.id,
        line_number=1,
        description="General items",
        quantity=1.0,
        unit_price=Decimal(str(request.total_amount)),
        amount=Decimal(str(request.total_amount)),
        unit="ea",
    )
    session.add(line_item)
    
    await session.commit()

    # Re-load with relationships to avoid lazy-loading in async context
    po_result = await session.execute(
        select(PurchaseOrderDB)
        .where(PurchaseOrderDB.id == po.id)
        .options(
            selectinload(PurchaseOrderDB.vendor),
            selectinload(PurchaseOrderDB.line_items),
        )
    )
    po_loaded = po_result.scalar_one()

    await default_invalidator.invalidate_dashboard()

    return po_to_dict(po_loaded)


@router.put("/purchase-orders/{po_id}", summary="Update purchase order")
async def update_purchase_order(po_id: str, session: AsyncSession = Depends(get_session)):
    """Update a purchase order."""
    result = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    po.updated_at = datetime.utcnow()
    await session.commit()

    await default_invalidator.invalidate_dashboard()

    return po_to_dict(po)


@router.post("/purchase-orders/{po_id}/close", summary="Close purchase order")
async def close_purchase_order(po_id: str, session: AsyncSession = Depends(get_session)):
    """Close a purchase order."""
    result = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    po.status = POStatus.CLOSED
    po.updated_at = datetime.utcnow()
    await session.commit()

    await default_invalidator.invalidate_dashboard()

    return po_to_dict(po)


@router.post("/purchase-orders/{po_id}/cancel", summary="Cancel purchase order")
async def cancel_purchase_order(po_id: str, session: AsyncSession = Depends(get_session)):
    """Cancel a purchase order."""
    result = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    po.status = POStatus.CANCELLED
    po.updated_at = datetime.utcnow()
    await session.commit()

    await default_invalidator.invalidate_dashboard()

    return po_to_dict(po)


@router.post("/purchase-orders/import", summary="Import POs from ERP")
async def import_purchase_orders(session: AsyncSession = Depends(get_session)):
    """Import purchase orders from ERP system."""
    return {"success": True, "imported_count": 0, "message": "ERP import not configured"}


@router.get("/purchase-orders/{po_id}/invoices", summary="Get PO invoices")
async def get_po_invoices(po_id: str, session: AsyncSession = Depends(get_session)):
    """Get invoices matched to a purchase order."""
    # First get the PO by po_number to get its id
    po_result = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po_id)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        return {"items": [], "total": 0}
    
    # Get invoices with matching_results data
    result = await session.execute(
        select(InvoiceDB, MatchingResultDB)
        .join(MatchingResultDB, MatchingResultDB.invoice_id == InvoiceDB.document_id)
        .where(MatchingResultDB.po_id == po.id)
        .where(MatchingResultDB.matched == True)
    )
    rows = result.all()
    
    items = []
    for inv, mr in rows:
        inv_dict = invoice_to_dict(inv)
        # Add matching-specific fields expected by frontend
        inv_dict["matched_amount"] = float(inv_dict.get("total_amount", 0))
        inv_dict["matched_date"] = mr.matched_at.isoformat() if mr.matched_at else None
        inv_dict["match_score"] = mr.match_score
        # Include invoice line items from the stored invoice_data JSON
        raw_items = (inv.invoice_data or {}).get("line_items", [])
        inv_dict["line_items"] = [
            {
                "line_number": idx + 1,
                "description": li.get("description", ""),
                "quantity": float(li.get("quantity", 0)),
                "unit_price": float(li.get("unit_price", 0)),
                "amount": float(li.get("amount", 0)),
                "sku": li.get("sku"),
            }
            for idx, li in enumerate(raw_items)
        ]
        items.append(inv_dict)
    
    return {
        "items": items,
        "total": len(items),
    }


@router.get("/purchase-orders/{po_id}/matching-history", summary="Get PO matching history")
async def get_po_matching_history(po_id: str, session: AsyncSession = Depends(get_session)):
    """Get matching history for a purchase order."""
    # Get PO first
    po_result = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po_id)
    )
    po = po_result.scalar_one_or_none()
    if not po:
        return {"items": []}
    
    # Get matching results with invoice data
    result = await session.execute(
        select(MatchingResultDB, InvoiceDB)
        .join(InvoiceDB, MatchingResultDB.invoice_id == InvoiceDB.document_id)
        .where(MatchingResultDB.po_id == po.id)
        .order_by(desc(MatchingResultDB.matched_at))
    )
    rows = result.all()
    
    items = []
    for m, inv in rows:
        invoice_data = inv.invoice_data or {}
        items.append({
            "id": m.id,
            "invoice_id": m.invoice_id,
            "invoice_number": inv.invoice_number,
            "matched_amount": float(invoice_data.get("total", 0)),
            "matched_date": m.matched_at.isoformat() if m.matched_at else None,
            "matched_by": m.matched_by or "System",
            "line_items_matched": 0,  # TODO: Calculate from line item matching
            "match_score": m.match_score,
            "status": "matched" if m.matched else "unmatched",
        })
    
    return {"items": items}


# ============================================================================
# Approval Endpoints
# ============================================================================

@router.get("/approvals/queue", summary="Get approval queue")
async def get_approval_queue(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get invoices pending approval."""
    try:
        query = select(InvoiceDB).where(
            InvoiceDB.status.in_(
                [
                    InvoiceStatus.PENDING_APPROVAL,
                    InvoiceStatus.RISK_REVIEW,
                ]
            )
        )
        count_query = select(func.count(InvoiceDB.id)).where(
            InvoiceDB.status.in_(
                [
                    InvoiceStatus.PENDING_APPROVAL,
                    InvoiceStatus.RISK_REVIEW,
                ]
            )
        )
        
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        offset = (page - 1) * limit
        query = query.order_by(desc(InvoiceDB.created_at)).offset(offset).limit(limit)
        
        result = await session.execute(query)
        invoices = result.scalars().all()
        
        items = []
        for inv in invoices:
            item = invoice_to_dict(inv)
            item["approval_level"] = "level1"
            item["required_approver"] = "manager"
            item["days_pending"] = (datetime.utcnow() - inv.created_at).days if inv.created_at else 0
            item["priority"] = "high" if inv.requires_review else "medium"
            items.append(item)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error getting approval queue: {e}")
        return {"items": [], "total": 0, "page": page, "limit": limit, "pages": 0}


@router.get("/approvals/{invoice_id}/workflow", summary="Get approval workflow")
async def get_approval_workflow(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Get workflow status for an invoice."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    status = invoice.status.value if invoice.status else "pending"
    
    # Determine step statuses based on invoice status
    extraction_status = "COMPLETED" if status not in ["pending", "ingested"] else "PENDING"
    matching_status = "COMPLETED" if status in ["matched", "approved", "ready_for_payment"] else "PENDING"
    approval_status = "COMPLETED" if status in ["approved", "ready_for_payment"] else "PENDING"
    
    return {
        "invoice_id": invoice_id,
        "current_step": 1 if extraction_status == "PENDING" else (2 if matching_status == "PENDING" else (3 if approval_status == "PENDING" else 4)),
        "steps": [
            {
                "role": "Document Submission",
                "status": "COMPLETED",
                "completed_at": invoice.created_at.isoformat() if invoice.created_at else None,
                "user_name": "System",
            },
            {
                "role": "OCR Extraction",
                "status": extraction_status,
                "completed_at": invoice.updated_at.isoformat() if extraction_status == "COMPLETED" and invoice.updated_at else None,
                "user_name": "AI Engine",
            },
            {
                "role": "PO Matching",
                "status": matching_status,
                "user_name": None,
            },
            {
                "role": "Manager Approval",
                "status": approval_status,
                "user_name": None,
            },
        ],
    }


@router.get("/approvals/{invoice_id}/history", summary="Get approval history")
async def get_approval_history(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Get approval history for an invoice."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    return {
        "items": [
            {"action": "created", "timestamp": invoice.created_at.isoformat() if invoice.created_at else None, "user": "system"},
            {"action": invoice.status.value if invoice.status else "pending", "timestamp": invoice.updated_at.isoformat() if invoice.updated_at else None, "user": "system"},
        ]
    }


@router.post("/approvals/{invoice_id}/action", summary="Take approval action")
async def take_approval_action(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Take an action on an invoice approval."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()

    return invoice_to_dict(invoice)


@router.post("/approvals/bulk-approve", summary="Bulk approve invoices")
async def bulk_approve(session: AsyncSession = Depends(get_session)):
    """Approve multiple invoices at once."""
    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()
    return {"success": True, "approved_count": 0, "message": "No invoice IDs provided"}


@router.post("/approvals/bulk-reject", summary="Bulk reject invoices")
async def bulk_reject(session: AsyncSession = Depends(get_session)):
    """Reject multiple invoices at once."""
    await default_invalidator.invalidate_dashboard()
    await default_invalidator.invalidate_analytics()
    return {"success": True, "rejected_count": 0, "message": "No invoice IDs provided"}


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/metrics", summary="Get dashboard metrics")
async def get_metrics(startDate: Optional[str] = None, endDate: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    """Get overall dashboard metrics with caching."""
    cache = await get_cache_service()
    cache_key = f"{startDate or 'all'}:{endDate or 'all'}"
    cached_result = await cache.get(CachePrefix.DASHBOARD, "metrics", cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for dashboard metrics")
        return cached_result

    try:
        total_invoices_r = await session.execute(select(func.count(InvoiceDB.id)))
        total_count = total_invoices_r.scalar() or 0

        pending_statuses = ['INGESTED', 'EXTRACTED', 'MATCHED', 'RISK_REVIEW', 'PENDING_APPROVAL']
        pending_invoices_r = await session.execute(
            select(func.count(InvoiceDB.id)).where(
                func.cast(InvoiceDB.status, String).in_(pending_statuses)
            )
        )

        high_risk_r = await session.execute(
            select(func.count(InvoiceDB.id)).where(InvoiceDB.requires_review == True)
        )

        # STP rate: invoices that did NOT require manual review
        auto_processed_r = await session.execute(
            select(func.count(InvoiceDB.id)).where(InvoiceDB.requires_review == False)
        )
        auto_count = auto_processed_r.scalar() or 0
        stp_rate = round((auto_count / total_count * 100), 1) if total_count > 0 else 0.0

        # Average processing time in seconds from extraction_time_ms
        avg_time_r = await session.execute(select(func.avg(InvoiceDB.extraction_time_ms)))
        avg_ms = avg_time_r.scalar() or 0
        avg_processing_secs = round(avg_ms / 1000, 1) if avg_ms else 0.0

        # Total value: sum of totals from invoice_data JSON
        all_invoices_r = await session.execute(select(InvoiceDB.invoice_data))
        total_value = 0.0
        for row in all_invoices_r.scalars().all():
            if row and isinstance(row, dict):
                try:
                    total_value += float(row.get('total', 0) or 0)
                except (ValueError, TypeError):
                    pass

        result = {
            "total_invoices": total_count,
            "pending_invoices": pending_invoices_r.scalar() or 0,
            "high_risk_invoices": high_risk_r.scalar() or 0,
            "processing_rate": stp_rate,
            "avg_processing_time": avg_processing_secs,
            "total_value": round(total_value, 2),
        }

        await cache.set(
            CachePrefix.DASHBOARD, "metrics", cache_key,
            value=result,
            ttl=CacheTTL.DASHBOARD_METRICS,
        )

        return result
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"total_invoices": 0, "pending_invoices": 0, "high_risk_invoices": 0, "processing_rate": 0, "avg_processing_time": 0, "total_value": 0}


@router.get("/analytics/invoice-volume", summary="Get invoice volume over time")
async def get_invoice_volume(days: int = Query(30, ge=1, le=365), session: AsyncSession = Depends(get_session)):
    """Get invoice volume trends — returns flat array of {date, count, value}."""
    cache = await get_cache_service()
    cached_result = await cache.get(CachePrefix.ANALYTICS, "invoice_volume", str(days))
    if cached_result is not None:
        return cached_result

    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(InvoiceDB)
            .where(InvoiceDB.created_at >= start_date)
            .order_by(InvoiceDB.created_at)
        )
        invoices = result.scalars().all()

        # Group by date
        from collections import defaultdict
        daily: dict = defaultdict(lambda: {"count": 0, "value": 0.0})
        for inv in invoices:
            day = str(inv.created_at.date()) if inv.created_at else "unknown"
            daily[day]["count"] += 1
            if inv.invoice_data and isinstance(inv.invoice_data, dict):
                try:
                    daily[day]["value"] += float(inv.invoice_data.get("total", 0) or 0)
                except (ValueError, TypeError):
                    pass

        response = [
            {"date": date, "count": info["count"], "value": round(info["value"], 2)}
            for date, info in sorted(daily.items())
        ]

        await cache.set(
            CachePrefix.ANALYTICS, "invoice_volume", str(days),
            value=response,
            ttl=CacheTTL.ANALYTICS,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting invoice volume: {e}")
        return []


@router.get("/analytics/status-distribution", summary="Get status distribution")
async def get_status_distribution(session: AsyncSession = Depends(get_session)):
    """Get invoice status distribution — returns flat array of {status, count, percentage}."""
    cache = await get_cache_service()
    cached_result = await cache.get(CachePrefix.ANALYTICS, "status_distribution")
    if cached_result is not None:
        return cached_result

    try:
        result = await session.execute(
            select(
                func.cast(InvoiceDB.status, String).label("status"),
                func.count(InvoiceDB.id).label("count")
            ).group_by(InvoiceDB.status)
        )
        data = result.all()
        total = sum(row.count for row in data) or 1
        response = [
            {
                "status": row.status or "unknown",
                "count": row.count,
                "percentage": round(row.count / total * 100, 1),
            }
            for row in data
        ]

        await cache.set(
            CachePrefix.ANALYTICS, "status_distribution",
            value=response,
            ttl=CacheTTL.ANALYTICS,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting status distribution: {e}")
        return []


@router.get("/analytics/processing-time", summary="Get processing time metrics")
async def get_processing_time(days: int = Query(30, ge=1, le=365), session: AsyncSession = Depends(get_session)):
    """Get processing time trends — returns flat array of {date, avgTime, minTime, maxTime} (in seconds)."""
    cache = await get_cache_service()
    cache_key = f"processing_time:{days}"
    cached_result = await cache.get(CachePrefix.ANALYTICS, cache_key)
    if cached_result is not None:
        return cached_result

    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(
                func.date(InvoiceDB.created_at).label("date"),
                func.avg(InvoiceDB.extraction_time_ms).label("avg_ms"),
                func.min(InvoiceDB.extraction_time_ms).label("min_ms"),
                func.max(InvoiceDB.extraction_time_ms).label("max_ms"),
            )
            .where(InvoiceDB.created_at >= start_date)
            .group_by(func.date(InvoiceDB.created_at))
            .order_by(func.date(InvoiceDB.created_at))
        )
        data = result.all()
        response = [
            {
                "date": str(row.date),
                "avgTime": round((row.avg_ms or 0) / 1000, 2),
                "minTime": round((row.min_ms or 0) / 1000, 2),
                "maxTime": round((row.max_ms or 0) / 1000, 2),
            }
            for row in data
        ]

        await cache.set(
            CachePrefix.ANALYTICS, cache_key,
            value=response,
            ttl=CacheTTL.ANALYTICS,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting processing time: {e}")
        return []


@router.get("/analytics/risk-distribution", summary="Get risk score distribution")
async def get_risk_distribution(session: AsyncSession = Depends(get_session)):
    """Get risk score distribution — returns flat array of {riskLevel, count, percentage}."""
    cache = await get_cache_service()
    cached_result = await cache.get(CachePrefix.ANALYTICS, "risk_distribution")
    if cached_result is not None:
        return cached_result

    try:
        result = await session.execute(
            select(
                func.cast(RiskAssessmentDB.risk_level, String).label("risk_level"),
                func.count(RiskAssessmentDB.id).label("count")
            ).group_by(RiskAssessmentDB.risk_level)
        )
        data = result.all()
        total = sum(row.count for row in data) or 1
        response = [
            {
                "riskLevel": row.risk_level or "unknown",
                "count": row.count,
                "percentage": round(row.count / total * 100, 1),
            }
            for row in data
        ]

        await cache.set(
            CachePrefix.ANALYTICS, "risk_distribution",
            value=response,
            ttl=CacheTTL.ANALYTICS,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting risk distribution: {e}")
        return []


@router.get("/analytics/top-vendors", summary="Get top vendors")
async def get_top_vendors(limit: int = Query(10, ge=1, le=50), session: AsyncSession = Depends(get_session)):
    """Get top vendors by invoice count — returns flat array of {vendorName, invoiceCount, totalAmount}."""
    cache = await get_cache_service()
    cache_key = f"top_vendors:{limit}"
    cached_result = await cache.get(CachePrefix.ANALYTICS, cache_key)
    if cached_result is not None:
        return cached_result

    try:
        # Pull all invoices and aggregate by vendor_name from invoice_data JSON
        result = await session.execute(select(InvoiceDB.invoice_data))
        from collections import defaultdict
        vendor_stats: dict = defaultdict(lambda: {"count": 0, "total": 0.0})
        for row in result.scalars().all():
            if row and isinstance(row, dict):
                vname = row.get("vendor_name") or "Unknown"
                vendor_stats[vname]["count"] += 1
                try:
                    vendor_stats[vname]["total"] += float(row.get("total", 0) or 0)
                except (ValueError, TypeError):
                    pass

        # Sort by invoice count descending, take top N
        sorted_vendors = sorted(vendor_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:limit]
        response = [
            {
                "vendorName": name,
                "invoiceCount": stats["count"],
                "totalAmount": round(stats["total"], 2),
            }
            for name, stats in sorted_vendors
        ]

        await cache.set(
            CachePrefix.ANALYTICS, cache_key,
            value=response,
            ttl=CacheTTL.ANALYTICS,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting top vendors: {e}")
        return []


@router.get("/analytics/stp-rate", summary="Get straight-through processing rate")
async def get_stp_rate(weeks: int = Query(12, ge=1, le=52), session: AsyncSession = Depends(get_session)):
    """Get STP rate as weekly time-series — returns flat array of {week, rate, processed, touchless}."""
    cache = await get_cache_service()
    cache_key = f"stp_rate:{weeks}"
    cached_result = await cache.get(CachePrefix.ANALYTICS, cache_key)
    if cached_result is not None:
        return cached_result

    try:
        start_date = datetime.utcnow() - timedelta(weeks=weeks)
        result = await session.execute(
            select(InvoiceDB.created_at, InvoiceDB.requires_review)
            .where(InvoiceDB.created_at >= start_date)
            .order_by(InvoiceDB.created_at)
        )
        rows = result.all()

        from collections import defaultdict
        weekly: dict = defaultdict(lambda: {"processed": 0, "touchless": 0})
        for row in rows:
            if row.created_at:
                # ISO week label: "2025-W03"
                iso = row.created_at.isocalendar()
                week_label = f"{iso[0]}-W{iso[1]:02d}"
                weekly[week_label]["processed"] += 1
                if not row.requires_review:
                    weekly[week_label]["touchless"] += 1

        response = []
        for wk in sorted(weekly.keys()):
            info = weekly[wk]
            rate = round(info["touchless"] / info["processed"] * 100, 1) if info["processed"] > 0 else 0.0
            response.append({
                "week": wk,
                "rate": rate,
                "processed": info["processed"],
                "touchless": info["touchless"],
            })

        await cache.set(
            CachePrefix.ANALYTICS, cache_key,
            value=response,
            ttl=CacheTTL.ANALYTICS,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting STP rate: {e}")
        return []


@router.get("/analytics/recent-activity", summary="Get recent activity")
async def get_recent_activity(limit: int = Query(20, ge=1, le=100), session: AsyncSession = Depends(get_session)):
    """Get recent activity feed — returns flat array of {id, type, invoiceNumber, description, user, timestamp, status}."""
    cache = await get_cache_service()
    cache_key = f"recent_activity:{limit}"
    cached_result = await cache.get(CachePrefix.DASHBOARD, cache_key)
    if cached_result is not None:
        return cached_result

    try:
        result = await session.execute(select(InvoiceDB).order_by(desc(InvoiceDB.updated_at)).limit(limit))
        invoices = result.scalars().all()

        def _activity_type(status_val: str) -> str:
            s = status_val.upper() if status_val else ""
            if s in ("INGESTED",):
                return "upload"
            elif s in ("APPROVED", "PENDING_APPROVAL"):
                return "approval"
            elif s in ("RISK_REVIEW",):
                return "risk"
            elif s in ("READY_FOR_PAYMENT",):
                return "payment"
            return "upload"

        def _description(inv) -> str:
            status_val = inv.status.value if inv.status else "updated"
            return f"Invoice {inv.invoice_number or inv.document_id} — {status_val.replace('_', ' ').title()}"

        response = []
        for inv in invoices:
            status_val = inv.status.value if inv.status else "updated"
            response.append({
                "id": inv.document_id,
                "type": _activity_type(status_val),
                "invoiceNumber": inv.invoice_number or inv.document_id,
                "description": _description(inv),
                "user": "System",
                "timestamp": inv.updated_at.isoformat() if inv.updated_at else datetime.utcnow().isoformat(),
                "status": status_val,
            })

        await cache.set(
            CachePrefix.DASHBOARD, cache_key,
            value=response,
            ttl=30,
        )

        return response
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return []


# ============================================================================
# ERP Integration Endpoints (Stubs - would connect to real ERP systems)
# ============================================================================

@router.get("/erp/connections", summary="List ERP connections")
async def list_erp_connections(session: AsyncSession = Depends(get_session)):
    """List configured ERP connections."""
    return {"items": [], "total": 0}


@router.get("/erp/sync-status", summary="Get ERP sync status")
async def get_erp_sync_status(session: AsyncSession = Depends(get_session)):
    """Get ERP synchronization status."""
    return {"last_sync": None, "status": "not_configured", "vendors_synced": 0, "pos_synced": 0}
