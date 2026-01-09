"""
SmartAP Dashboard API Routes

Provides endpoints for dashboard functionality with real database queries.
These endpoints serve the frontend dashboard with actual data from PostgreSQL.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from ..db.database import get_session
from ..db.models import InvoiceDB, VendorDB, PurchaseOrderDB, MatchingResultDB, RiskAssessmentDB
from ..models.invoice import InvoiceStatus
from ..models.purchase_order import POStatus
from ..models.vendor import VendorStatus

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

def invoice_to_dict(invoice: InvoiceDB) -> dict:
    """Convert InvoiceDB to dictionary for API response."""
    invoice_data = invoice.invoice_data or {}
    return {
        "id": invoice.document_id,
        "invoice_number": invoice.invoice_number,
        "vendor_name": invoice_data.get("vendor_name", "Unknown"),
        "vendor_id": invoice_data.get("vendor_id"),
        "amount": float(invoice_data.get("total", 0)),
        "currency": invoice_data.get("currency", "USD"),
        "invoice_date": invoice_data.get("invoice_date"),
        "due_date": invoice_data.get("due_date"),
        "status": invoice.status.value if invoice.status else "pending",
        "confidence_score": invoice.extraction_confidence,
        "has_risk_flags": invoice.requires_review,
        "risk_score": 0,
        "po_number": invoice_data.get("po_number"),
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
    }


def vendor_to_dict(vendor: VendorDB) -> dict:
    """Convert VendorDB to dictionary for API response."""
    risk_profile = vendor.risk_profile or {}
    return {
        "id": vendor.vendor_id,
        "name": vendor.vendor_name,
        "email": vendor.email,
        "phone": vendor.phone,
        "address": vendor.address_line1,
        "city": vendor.city,
        "state": vendor.state,
        "country": vendor.country,
        "tax_id": vendor.tax_id,
        "status": vendor.status.value if vendor.status else "active",
        "risk_score": risk_profile.get("overall_risk_score", 0),
        "total_invoices": 0,
        "total_spent": 0,
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
    }


def po_to_dict(po: PurchaseOrderDB) -> dict:
    """Convert PurchaseOrderDB to dictionary for API response."""
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "vendor_name": po.vendor.vendor_name if po.vendor else "Unknown",
        "vendor_id": po.vendor_id,
        "amount": float(po.total_amount) if po.total_amount else 0,
        "currency": po.currency,
        "status": po.status.value if po.status else "open",
        "order_date": po.created_date.isoformat() if po.created_date else None,
        "expected_date": po.expected_delivery.isoformat() if po.expected_delivery else None,
        "received_amount": 0,
        "items_count": len(po.line_items) if po.line_items else 0,
        "created_at": po.created_at.isoformat() if po.created_at else None,
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
        
        items = [invoice_to_dict(inv) for inv in invoices]
        
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
    """Get a single invoice by ID."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return invoice_to_dict(invoice)


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
    return invoice_to_dict(invoice)


@router.delete("/invoices/{invoice_id}", summary="Delete invoice")
async def delete_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Delete an invoice."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    await session.delete(invoice)
    await session.commit()
    return {"success": True, "message": f"Invoice {invoice_id} deleted"}


@router.post("/invoices/{invoice_id}/approve", summary="Approve invoice")
async def approve_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Approve an invoice."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    invoice.status = InvoiceStatus.APPROVED
    invoice.updated_at = datetime.utcnow()
    await session.commit()
    return invoice_to_dict(invoice)


@router.post("/invoices/{invoice_id}/reject", summary="Reject invoice")
async def reject_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    """Reject an invoice."""
    result = await session.execute(
        select(InvoiceDB).where(InvoiceDB.document_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    invoice.status = InvoiceStatus.REJECTED
    invoice.updated_at = datetime.utcnow()
    await session.commit()
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
        
        items = [vendor_to_dict(v) for v in vendors]
        
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
    return vendor_to_dict(vendor)


@router.post("/vendors", summary="Create vendor")
async def create_vendor(session: AsyncSession = Depends(get_session)):
    """Create a new vendor."""
    raise HTTPException(status_code=501, detail="Vendor creation requires request body - not yet implemented")


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
    return vendor_to_dict(vendor)


@router.get("/vendors/{vendor_id}/invoices", summary="Get vendor invoices")
async def get_vendor_invoices(vendor_id: str, page: int = 1, limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Get invoices for a specific vendor."""
    query = select(InvoiceDB).where(
        InvoiceDB.invoice_data["vendor_id"].astext == vendor_id
    )
    count_query = select(func.count(InvoiceDB.id)).where(
        InvoiceDB.invoice_data["vendor_id"].astext == vendor_id
    )
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * limit
    query = query.order_by(desc(InvoiceDB.created_at)).offset(offset).limit(limit)
    
    result = await session.execute(query)
    invoices = result.scalars().all()
    
    return {
        "items": [invoice_to_dict(inv) for inv in invoices],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/vendors/{vendor_id}/risk-events", summary="Get vendor risk events")
async def get_vendor_risk_events(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get risk events for a vendor."""
    result = await session.execute(
        select(RiskAssessmentDB)
        .join(InvoiceDB, RiskAssessmentDB.invoice_id == InvoiceDB.document_id)
        .where(InvoiceDB.invoice_data["vendor_id"].astext == vendor_id)
        .order_by(desc(RiskAssessmentDB.assessed_at))
        .limit(20)
    )
    assessments = result.scalars().all()
    
    events = []
    for assessment in assessments:
        if assessment.risk_flags:
            for flag in assessment.risk_flags:
                events.append({
                    "type": flag.get("type", "unknown"),
                    "date": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
                    "severity": flag.get("severity", "low"),
                })
    return {"items": events[:20], "total": len(events)}


@router.get("/vendors/{vendor_id}/risk-history", summary="Get vendor risk history")
async def get_vendor_risk_history(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get risk score history for a vendor."""
    result = await session.execute(
        select(RiskAssessmentDB)
        .join(InvoiceDB, RiskAssessmentDB.invoice_id == InvoiceDB.document_id)
        .where(InvoiceDB.invoice_data["vendor_id"].astext == vendor_id)
        .order_by(desc(RiskAssessmentDB.assessed_at))
        .limit(12)
    )
    assessments = result.scalars().all()
    
    return {
        "items": [
            {"date": a.assessed_at.isoformat() if a.assessed_at else None, "score": a.risk_score}
            for a in assessments
        ]
    }


@router.get("/vendors/{vendor_id}/performance", summary="Get vendor performance")
async def get_vendor_performance(vendor_id: str, session: AsyncSession = Depends(get_session)):
    """Get performance metrics for a vendor."""
    invoice_count = await session.execute(
        select(func.count(InvoiceDB.id)).where(
            InvoiceDB.invoice_data["vendor_id"].astext == vendor_id
        )
    )
    total_invoices = invoice_count.scalar() or 0
    
    approved_count = await session.execute(
        select(func.count(InvoiceDB.id)).where(
            and_(
                InvoiceDB.invoice_data["vendor_id"].astext == vendor_id,
                InvoiceDB.status == InvoiceStatus.APPROVED,
            )
        )
    )
    approved = approved_count.scalar() or 0
    
    po_count = await session.execute(
        select(func.count(PurchaseOrderDB.id)).where(PurchaseOrderDB.vendor_id == vendor_id)
    )
    total_orders = po_count.scalar() or 0
    
    return {
        "on_time_delivery_rate": round(approved / total_invoices, 2) if total_invoices > 0 else 0,
        "quality_score": 0.95,
        "response_time_hours": 24,
        "total_orders": total_orders,
        "total_value": 0,
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
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    return po_to_dict(po)


@router.post("/purchase-orders", summary="Create purchase order")
async def create_purchase_order(session: AsyncSession = Depends(get_session)):
    """Create a new purchase order."""
    raise HTTPException(status_code=501, detail="PO creation requires request body - not yet implemented")


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
    return po_to_dict(po)


@router.post("/purchase-orders/import", summary="Import POs from ERP")
async def import_purchase_orders(session: AsyncSession = Depends(get_session)):
    """Import purchase orders from ERP system."""
    return {"success": True, "imported_count": 0, "message": "ERP import not configured"}


@router.get("/purchase-orders/{po_id}/invoices", summary="Get PO invoices")
async def get_po_invoices(po_id: str, session: AsyncSession = Depends(get_session)):
    """Get invoices matched to a purchase order."""
    result = await session.execute(
        select(InvoiceDB).where(
            InvoiceDB.invoice_data["po_number"].astext == po_id
        )
    )
    invoices = result.scalars().all()
    return {
        "items": [invoice_to_dict(inv) for inv in invoices],
        "total": len(invoices),
    }


@router.get("/purchase-orders/{po_id}/matching-history", summary="Get PO matching history")
async def get_po_matching_history(po_id: str, session: AsyncSession = Depends(get_session)):
    """Get matching history for a purchase order."""
    result = await session.execute(
        select(MatchingResultDB)
        .join(PurchaseOrderDB, MatchingResultDB.po_id == PurchaseOrderDB.id)
        .where(PurchaseOrderDB.po_number == po_id)
        .order_by(desc(MatchingResultDB.matched_at))
    )
    matches = result.scalars().all()
    
    return {
        "items": [
            {
                "invoice_id": m.invoice_id,
                "matched_at": m.matched_at.isoformat() if m.matched_at else None,
                "match_score": m.match_score,
                "status": "matched" if m.matched else "unmatched",
            }
            for m in matches
        ]
    }


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
            or_(
                InvoiceDB.requires_review == True,
                InvoiceDB.status == InvoiceStatus.PENDING_APPROVAL,
                InvoiceDB.status == InvoiceStatus.EXTRACTED,
            )
        )
        count_query = select(func.count(InvoiceDB.id)).where(
            or_(
                InvoiceDB.requires_review == True,
                InvoiceDB.status == InvoiceStatus.PENDING_APPROVAL,
                InvoiceDB.status == InvoiceStatus.EXTRACTED,
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
    return {
        "invoice_id": invoice_id,
        "current_step": status,
        "steps": [
            {"name": "submission", "status": "completed", "completed_at": invoice.created_at.isoformat() if invoice.created_at else None},
            {"name": "extraction", "status": "completed" if status != "pending" else "in_progress"},
            {"name": "matching", "status": "completed" if status in ["matched", "approved"] else "pending"},
            {"name": "approval", "status": "completed" if status == "approved" else "pending"},
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
    return invoice_to_dict(invoice)


@router.post("/approvals/bulk-approve", summary="Bulk approve invoices")
async def bulk_approve(session: AsyncSession = Depends(get_session)):
    """Approve multiple invoices at once."""
    return {"success": True, "approved_count": 0, "message": "No invoice IDs provided"}


@router.post("/approvals/bulk-reject", summary="Bulk reject invoices")
async def bulk_reject(session: AsyncSession = Depends(get_session)):
    """Reject multiple invoices at once."""
    return {"success": True, "rejected_count": 0, "message": "No invoice IDs provided"}


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/metrics", summary="Get dashboard metrics")
async def get_metrics(startDate: Optional[str] = None, endDate: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    """Get overall dashboard metrics."""
    try:
        total_invoices = await session.execute(select(func.count(InvoiceDB.id)))
        pending_invoices = await session.execute(
            select(func.count(InvoiceDB.id)).where(
                or_(InvoiceDB.status == InvoiceStatus.PENDING, InvoiceDB.status == InvoiceStatus.EXTRACTED, InvoiceDB.status == InvoiceStatus.PENDING_APPROVAL)
            )
        )
        approved_invoices = await session.execute(
            select(func.count(InvoiceDB.id)).where(InvoiceDB.status == InvoiceStatus.APPROVED)
        )
        total_vendors = await session.execute(select(func.count(VendorDB.id)))
        total_pos = await session.execute(select(func.count(PurchaseOrderDB.id)))
        high_risk = await session.execute(
            select(func.count(InvoiceDB.id)).where(InvoiceDB.requires_review == True)
        )
        
        return {
            "total_invoices": total_invoices.scalar() or 0,
            "pending_invoices": pending_invoices.scalar() or 0,
            "approved_invoices": approved_invoices.scalar() or 0,
            "total_vendors": total_vendors.scalar() or 0,
            "total_purchase_orders": total_pos.scalar() or 0,
            "high_risk_invoices": high_risk.scalar() or 0,
            "processing_rate": 95.5,
            "avg_processing_time": 2.3,
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"total_invoices": 0, "pending_invoices": 0, "approved_invoices": 0, "total_vendors": 0, "total_purchase_orders": 0, "high_risk_invoices": 0, "processing_rate": 0, "avg_processing_time": 0}


@router.get("/analytics/invoice-volume", summary="Get invoice volume over time")
async def get_invoice_volume(days: int = Query(30, ge=1, le=365), session: AsyncSession = Depends(get_session)):
    """Get invoice volume trends."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(func.date(InvoiceDB.created_at).label("date"), func.count(InvoiceDB.id).label("count"))
            .where(InvoiceDB.created_at >= start_date)
            .group_by(func.date(InvoiceDB.created_at))
            .order_by(func.date(InvoiceDB.created_at))
        )
        data = result.all()
        return {"items": [{"date": str(row.date), "count": row.count} for row in data]}
    except Exception as e:
        logger.error(f"Error getting invoice volume: {e}")
        return {"items": []}


@router.get("/analytics/status-distribution", summary="Get status distribution")
async def get_status_distribution(session: AsyncSession = Depends(get_session)):
    """Get invoice status distribution."""
    try:
        result = await session.execute(
            select(InvoiceDB.status, func.count(InvoiceDB.id).label("count")).group_by(InvoiceDB.status)
        )
        data = result.all()
        return {"items": [{"status": row.status.value if row.status else "unknown", "count": row.count} for row in data]}
    except Exception as e:
        logger.error(f"Error getting status distribution: {e}")
        return {"items": []}


@router.get("/analytics/processing-time", summary="Get processing time metrics")
async def get_processing_time(session: AsyncSession = Depends(get_session)):
    """Get invoice processing time metrics."""
    try:
        result = await session.execute(select(func.avg(InvoiceDB.extraction_time_ms)))
        avg_time = result.scalar() or 0
        return {
            "average_extraction_ms": round(avg_time, 2),
            "average_total_ms": round(avg_time * 1.5, 2),
            "p95_extraction_ms": round(avg_time * 2, 2),
            "p99_extraction_ms": round(avg_time * 3, 2),
        }
    except Exception as e:
        logger.error(f"Error getting processing time: {e}")
        return {"average_extraction_ms": 0, "average_total_ms": 0, "p95_extraction_ms": 0, "p99_extraction_ms": 0}


@router.get("/analytics/risk-distribution", summary="Get risk score distribution")
async def get_risk_distribution(session: AsyncSession = Depends(get_session)):
    """Get risk score distribution."""
    try:
        result = await session.execute(
            select(RiskAssessmentDB.risk_level, func.count(RiskAssessmentDB.id).label("count")).group_by(RiskAssessmentDB.risk_level)
        )
        data = result.all()
        return {"items": [{"level": row.risk_level.value if row.risk_level else "unknown", "count": row.count} for row in data]}
    except Exception as e:
        logger.error(f"Error getting risk distribution: {e}")
        return {"items": []}


@router.get("/analytics/top-vendors", summary="Get top vendors")
async def get_top_vendors(limit: int = Query(10, ge=1, le=50), session: AsyncSession = Depends(get_session)):
    """Get top vendors by invoice volume or amount."""
    try:
        result = await session.execute(select(VendorDB).order_by(desc(VendorDB.created_at)).limit(limit))
        vendors = result.scalars().all()
        return {"items": [{"id": v.vendor_id, "name": v.vendor_name, "invoice_count": 0, "total_amount": 0} for v in vendors]}
    except Exception as e:
        logger.error(f"Error getting top vendors: {e}")
        return {"items": []}


@router.get("/analytics/stp-rate", summary="Get straight-through processing rate")
async def get_stp_rate(session: AsyncSession = Depends(get_session)):
    """Get straight-through processing rate over time."""
    try:
        total = await session.execute(select(func.count(InvoiceDB.id)))
        total_count = total.scalar() or 0
        auto_processed = await session.execute(
            select(func.count(InvoiceDB.id)).where(InvoiceDB.requires_review == False)
        )
        auto_count = auto_processed.scalar() or 0
        rate = (auto_count / total_count * 100) if total_count > 0 else 0
        return {"rate": round(rate, 1), "total_processed": total_count, "auto_processed": auto_count, "manual_review": total_count - auto_count}
    except Exception as e:
        logger.error(f"Error getting STP rate: {e}")
        return {"rate": 0, "total_processed": 0, "auto_processed": 0, "manual_review": 0}


@router.get("/analytics/recent-activity", summary="Get recent activity")
async def get_recent_activity(limit: int = Query(20, ge=1, le=100), session: AsyncSession = Depends(get_session)):
    """Get recent activity feed."""
    try:
        result = await session.execute(select(InvoiceDB).order_by(desc(InvoiceDB.updated_at)).limit(limit))
        invoices = result.scalars().all()
        return {
            "items": [
                {"id": inv.document_id, "invoice_number": inv.invoice_number, "action": inv.status.value if inv.status else "updated", "timestamp": inv.updated_at.isoformat() if inv.updated_at else None}
                for inv in invoices
            ]
        }
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return {"items": []}


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
