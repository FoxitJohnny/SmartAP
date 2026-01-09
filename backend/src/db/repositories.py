"""
SmartAP Data Access Layer - Repositories

Repositories for database operations on all entities.
"""

from typing import Optional, List
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from .models import (
    InvoiceDB,
    PurchaseOrderDB,
    POLineItemDB,
    VendorDB,
    PaymentRecordDB,
    FraudFlagDB,
    MatchingResultDB,
    RiskAssessmentDB,
)
from ..models import (
    Invoice,
    InvoiceExtractionResult,
    InvoiceStatus,
    PurchaseOrder,
    POStatus,
    Vendor,
    VendorStatus,
    MatchingResult,
    RiskAssessment,
)


class InvoiceRepository:
    """Repository for Invoice operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, extraction_result: InvoiceExtractionResult) -> InvoiceDB:
        """Create a new invoice record."""
        invoice_db = InvoiceDB(
            document_id=extraction_result.document_id,
            invoice_number=extraction_result.invoice.invoice_number if extraction_result.invoice else "UNKNOWN",
            file_name=extraction_result.file_name,
            file_hash=extraction_result.file_hash,
            status=extraction_result.status,
            invoice_data=extraction_result.invoice.model_dump() if extraction_result.invoice else None,
            extraction_confidence=extraction_result.confidence.overall,
            requires_review=extraction_result.requires_review,
            ocr_applied=extraction_result.ocr_applied,
            page_count=extraction_result.page_count,
            extraction_time_ms=extraction_result.extraction_time_ms,
        )
        
        self.session.add(invoice_db)
        await self.session.flush()
        return invoice_db
    
    async def get_by_id(self, document_id: str) -> Optional[InvoiceDB]:
        """Get invoice by document ID."""
        result = await self.session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, file_hash: str) -> Optional[InvoiceDB]:
        """Get invoice by file hash (for duplicate detection)."""
        result = await self.session.execute(
            select(InvoiceDB).where(InvoiceDB.file_hash == file_hash)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: InvoiceStatus, limit: int = 100) -> List[InvoiceDB]:
        """Get invoices by status."""
        result = await self.session.execute(
            select(InvoiceDB)
            .where(InvoiceDB.status == status)
            .order_by(desc(InvoiceDB.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_status(self, document_id: str, status: InvoiceStatus) -> Optional[InvoiceDB]:
        """Update invoice status."""
        invoice = await self.get_by_id(document_id)
        if invoice:
            invoice.status = status
            invoice.updated_at = datetime.utcnow()
            await self.session.flush()
        return invoice
    
    async def search_by_vendor(self, vendor_name: str, limit: int = 50) -> List[InvoiceDB]:
        """Search invoices by vendor name."""
        result = await self.session.execute(
            select(InvoiceDB)
            .where(InvoiceDB.invoice_data["vendor_name"].astext.ilike(f"%{vendor_name}%"))
            .order_by(desc(InvoiceDB.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


class PurchaseOrderRepository:
    """Repository for Purchase Order operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, po: PurchaseOrder) -> PurchaseOrderDB:
        """Create a new purchase order."""
        po_db = PurchaseOrderDB(
            po_number=po.po_number,
            vendor_id=po.vendor_id,
            created_date=po.created_date,
            expected_delivery=po.expected_delivery,
            status=po.status,
            currency=po.currency,
            subtotal=po.subtotal,
            tax=po.tax,
            total_amount=po.total_amount,
            payment_terms=po.payment_terms,
            notes=po.notes,
            created_by=po.created_by,
        )
        
        self.session.add(po_db)
        await self.session.flush()
        
        # Add line items
        for item in po.line_items:
            line_item_db = POLineItemDB(
                po_id=po_db.id,
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=item.amount,
                sku=item.sku,
                unit=item.unit,
                received_quantity=item.received_quantity,
            )
            self.session.add(line_item_db)
        
        await self.session.flush()
        return po_db
    
    async def get_by_po_number(self, po_number: str) -> Optional[PurchaseOrderDB]:
        """Get PO by PO number with line items."""
        result = await self.session.execute(
            select(PurchaseOrderDB)
            .where(PurchaseOrderDB.po_number == po_number)
            .options(selectinload(PurchaseOrderDB.line_items))
        )
        return result.scalar_one_or_none()
    
    async def get_by_vendor(self, vendor_id: str, status: Optional[POStatus] = None) -> List[PurchaseOrderDB]:
        """Get POs by vendor, optionally filtered by status."""
        query = select(PurchaseOrderDB).where(PurchaseOrderDB.vendor_id == vendor_id)
        
        if status:
            query = query.where(PurchaseOrderDB.status == status)
        
        query = query.options(selectinload(PurchaseOrderDB.line_items)).order_by(desc(PurchaseOrderDB.created_date))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def find_candidates(
        self,
        vendor_id: str,
        amount_min: float,
        amount_max: float,
        status: POStatus = POStatus.OPEN
    ) -> List[PurchaseOrderDB]:
        """Find candidate POs for matching based on vendor and amount range."""
        result = await self.session.execute(
            select(PurchaseOrderDB)
            .where(
                and_(
                    PurchaseOrderDB.vendor_id == vendor_id,
                    PurchaseOrderDB.status == status,
                    PurchaseOrderDB.total_amount >= amount_min,
                    PurchaseOrderDB.total_amount <= amount_max,
                )
            )
            .options(selectinload(PurchaseOrderDB.line_items))
            .order_by(PurchaseOrderDB.created_date)
        )
        return list(result.scalars().all())
    
    async def update_status(self, po_number: str, status: POStatus) -> Optional[PurchaseOrderDB]:
        """Update PO status."""
        po = await self.get_by_po_number(po_number)
        if po:
            po.status = status
            po.updated_at = datetime.utcnow()
            await self.session.flush()
        return po


class VendorRepository:
    """Repository for Vendor operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, vendor: Vendor) -> VendorDB:
        """Create a new vendor."""
        vendor_db = VendorDB(
            vendor_id=vendor.vendor_id,
            vendor_name=vendor.vendor_name,
            contact_name=vendor.contact_name,
            email=vendor.email,
            phone=vendor.phone,
            address_line1=vendor.address_line1,
            city=vendor.city,
            state=vendor.state,
            postal_code=vendor.postal_code,
            country=vendor.country,
            tax_id=vendor.tax_id,
            bank_account_number=vendor.bank_account_number,
            bank_name=vendor.bank_name,
            status=vendor.status,
            payment_terms=vendor.payment_terms,
            currency=vendor.currency,
            risk_profile=vendor.risk_profile.model_dump(mode='json'),
            onboarded_date=vendor.onboarded_date,
            notes=vendor.notes,
        )
        
        self.session.add(vendor_db)
        await self.session.flush()
        return vendor_db
    
    async def get_by_id(self, vendor_id: str) -> Optional[VendorDB]:
        """Get vendor by ID."""
        result = await self.session.execute(
            select(VendorDB)
            .where(VendorDB.vendor_id == vendor_id)
            .options(
                selectinload(VendorDB.payment_history),
                selectinload(VendorDB.fraud_flags)
            )
        )
        return result.scalar_one_or_none()
    
    async def search_by_name(self, name: str) -> List[VendorDB]:
        """Search vendors by name (fuzzy)."""
        result = await self.session.execute(
            select(VendorDB)
            .where(VendorDB.vendor_name.ilike(f"%{name}%"))
            .order_by(VendorDB.vendor_name)
        )
        return list(result.scalars().all())
    
    async def get_all_active(self) -> List[VendorDB]:
        """Get all active vendors."""
        result = await self.session.execute(
            select(VendorDB)
            .where(VendorDB.status == VendorStatus.ACTIVE)
            .order_by(VendorDB.vendor_name)
        )
        return list(result.scalars().all())
    
    async def update_risk_profile(self, vendor_id: str, risk_profile: dict) -> Optional[VendorDB]:
        """Update vendor risk profile."""
        vendor = await self.get_by_id(vendor_id)
        if vendor:
            vendor.risk_profile = risk_profile
            vendor.updated_at = datetime.utcnow()
            await self.session.flush()
        return vendor


class MatchingRepository:
    """Repository for Matching Result operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, matching_result: MatchingResult) -> MatchingResultDB:
        """Create a new matching result."""
        matching_db = MatchingResultDB(
            invoice_id=matching_result.invoice_id,
            po_id=None,  # Will be set if PO exists in DB
            matching_id=matching_result.matching_id,
            match_type=matching_result.match_type,
            match_score=matching_result.match_score,
            matched=matching_result.matched,
            vendor_match_score=matching_result.vendor_match_score,
            amount_match_score=matching_result.amount_match_score,
            date_match_score=matching_result.date_match_score,
            line_items_match_score=matching_result.line_items_match_score,
            discrepancies=[d.model_dump() for d in matching_result.discrepancies],
            has_discrepancies=matching_result.has_discrepancies,
            critical_discrepancies=matching_result.critical_discrepancies,
            requires_approval=matching_result.requires_approval,
            approval_reason=matching_result.approval_reason,
            matched_by=matching_result.matched_by,
        )
        
        # Link to PO if it exists
        if matching_result.po_number:
            result = await self.session.execute(
                select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == matching_result.po_number)
            )
            po = result.scalar_one_or_none()
            if po:
                matching_db.po_id = po.id
        
        self.session.add(matching_db)
        await self.session.flush()
        return matching_db
    
    async def get_by_invoice_id(self, invoice_id: str) -> Optional[MatchingResultDB]:
        """Get latest matching result for an invoice."""
        result = await self.session.execute(
            select(MatchingResultDB)
            .where(MatchingResultDB.invoice_id == invoice_id)
            .order_by(desc(MatchingResultDB.matched_at))
        )
        return result.scalars().first()


class RiskRepository:
    """Repository for Risk Assessment operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, risk_assessment: RiskAssessment) -> RiskAssessmentDB:
        """Create a new risk assessment."""
        risk_db = RiskAssessmentDB(
            invoice_id=risk_assessment.invoice_id,
            assessment_id=risk_assessment.assessment_id,
            risk_level=risk_assessment.risk_level,
            risk_score=risk_assessment.risk_score,
            duplicate_risk_score=risk_assessment.duplicate_risk_score,
            vendor_risk_score=risk_assessment.vendor_risk_score,
            price_risk_score=risk_assessment.price_risk_score,
            amount_risk_score=risk_assessment.amount_risk_score,
            pattern_risk_score=risk_assessment.pattern_risk_score,
            risk_flags=[f.model_dump() for f in risk_assessment.risk_flags],
            critical_flags=risk_assessment.critical_flags,
            high_flags=risk_assessment.high_flags,
            duplicate_info=risk_assessment.duplicate_info.model_dump() if risk_assessment.duplicate_info else None,
            recommended_action=risk_assessment.recommended_action,
            action_reason=risk_assessment.action_reason,
            requires_manual_review=risk_assessment.requires_manual_review,
            assessed_by=risk_assessment.assessed_by,
            assessment_version=risk_assessment.assessment_version,
        )
        
        self.session.add(risk_db)
        await self.session.flush()
        return risk_db
    
    async def get_by_invoice_id(self, invoice_id: str) -> Optional[RiskAssessmentDB]:
        """Get latest risk assessment for an invoice."""
        result = await self.session.execute(
            select(RiskAssessmentDB)
            .where(RiskAssessmentDB.invoice_id == invoice_id)
            .order_by(desc(RiskAssessmentDB.assessed_at))
        )
        return result.scalars().first()
    
    async def get_high_risk_invoices(self, limit: int = 50) -> List[RiskAssessmentDB]:
        """Get high and critical risk assessments."""
        result = await self.session.execute(
            select(RiskAssessmentDB)
            .where(
                or_(
                    RiskAssessmentDB.risk_level == "high",
                    RiskAssessmentDB.risk_level == "critical"
                )
            )
            .order_by(desc(RiskAssessmentDB.assessed_at))
            .limit(limit)
        )
        return list(result.scalars().all())
