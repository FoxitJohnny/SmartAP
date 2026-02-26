"""
SmartAP Data Access Layer - Repositories

Repositories for database operations on all entities.
Optimized with eager loading, caching, and batch operations.
"""

from typing import Any, Dict, Optional, List, Sequence, Tuple
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime
import logging

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
from ..utils.query_optimizer import (
    QueryCache,
    QueryAnalyzer,
    BatchLoader,
    generate_cache_key,
    get_default_cache,
    get_default_analyzer,
)

logger = logging.getLogger(__name__)


# Pagination helper
class PaginatedResult(Sequence):
    """Container for paginated query results."""
    
    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        self.has_next = page < self.total_pages
        self.has_prev = page > 1
    
    def __getitem__(self, index):
        return self.items[index]
    
    def __len__(self):
        return len(self.items)
    
    def __iter__(self):
        return iter(self.items)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class InvoiceRepository:
    """Repository for Invoice operations with query optimization."""
    
    def __init__(self, session: AsyncSession, cache: Optional[QueryCache] = None):
        self.session = session
        self.cache = cache or get_default_cache()
        self.analyzer = get_default_analyzer()
    
    async def create(self, extraction_result: InvoiceExtractionResult) -> InvoiceDB:
        """Create a new invoice record."""
        invoice_db = InvoiceDB(
            document_id=extraction_result.document_id,
            invoice_number=extraction_result.invoice.invoice_number if extraction_result.invoice else "UNKNOWN",
            file_name=extraction_result.file_name,
            file_hash=extraction_result.file_hash,
            status=extraction_result.status,
            invoice_data=extraction_result.invoice.model_dump(mode="json") if extraction_result.invoice else None,
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
        """Get invoice by document ID with eager loading."""
        cache_key = f"invoice:{document_id}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("invoice_get_by_id"):
            result = await self.session.execute(
                select(InvoiceDB)
                .where(InvoiceDB.document_id == document_id)
                .options(
                    selectinload(InvoiceDB.matching_results),
                    selectinload(InvoiceDB.risk_assessments),
                )
            )
            invoice = result.scalar_one_or_none()
        
        if invoice:
            await self.cache.set(cache_key, invoice, ttl=60)
        
        return invoice
    
    async def get_by_document_id(self, document_id: str) -> Optional[InvoiceDB]:
        """Alias for get_by_id - Get invoice by document ID."""
        return await self.get_by_id(document_id)
    
    async def get_by_hash(self, file_hash: str) -> Optional[InvoiceDB]:
        """Get invoice by file hash (for duplicate detection)."""
        result = await self.session.execute(
            select(InvoiceDB).where(InvoiceDB.file_hash == file_hash)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: InvoiceStatus, limit: int = 100) -> List[InvoiceDB]:
        """Get invoices by status using optimized index."""
        cache_key = f"invoices:status:{status}:limit:{limit}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("invoice_get_by_status"):
            # Uses ix_invoices_status_created_at index
            result = await self.session.execute(
                select(InvoiceDB)
                .where(InvoiceDB.status == status)
                .order_by(desc(InvoiceDB.created_at))
                .limit(limit)
            )
            invoices = list(result.scalars().all())
        
        await self.cache.set(cache_key, invoices, ttl=30)
        return invoices
    
    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[InvoiceStatus] = None,
        vendor_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResult:
        """Get paginated invoices with optional filters.
        
        Uses composite indexes for optimal performance.
        """
        cache_key = generate_cache_key(
            "invoices:paginated",
            page=page,
            page_size=page_size,
            status=status,
            vendor_id=vendor_id,
            search=search,
        )
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("invoice_get_paginated"):
            # Build query with filters
            query = select(InvoiceDB)
            count_query = select(func.count(InvoiceDB.id))
            
            conditions = []
            if status:
                conditions.append(InvoiceDB.status == status)
            if vendor_id:
                conditions.append(InvoiceDB.vendor_id == vendor_id)
            if search:
                conditions.append(
                    or_(
                        InvoiceDB.invoice_number.ilike(f"%{search}%"),
                        InvoiceDB.invoice_data["vendor_name"].astext.ilike(f"%{search}%"),
                    )
                )
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Get total count
            total_result = await self.session.execute(count_query)
            total = total_result.scalar() or 0
            
            # Get page items with optimized ordering
            offset = (page - 1) * page_size
            query = (
                query
                .order_by(desc(InvoiceDB.created_at))
                .offset(offset)
                .limit(page_size)
            )
            
            result = await self.session.execute(query)
            items = list(result.scalars().all())
        
        paginated = PaginatedResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
        
        await self.cache.set(cache_key, paginated, ttl=30)
        return paginated
    
    async def get_by_vendor_batch(
        self,
        vendor_ids: List[str],
        status: Optional[InvoiceStatus] = None,
    ) -> Dict[str, List[InvoiceDB]]:
        """Batch load invoices for multiple vendors.
        
        Prevents N+1 queries when loading invoices for multiple vendors.
        Uses ix_invoices_vendor_id_status index.
        """
        async with self.analyzer.track("invoice_get_by_vendor_batch"):
            query = (
                select(InvoiceDB)
                .where(InvoiceDB.vendor_id.in_(vendor_ids))
            )
            
            if status:
                query = query.where(InvoiceDB.status == status)
            
            query = query.order_by(desc(InvoiceDB.created_at))
            
            result = await self.session.execute(query)
            invoices = result.scalars().all()
        
        # Group by vendor_id
        grouped: Dict[str, List[InvoiceDB]] = {vid: [] for vid in vendor_ids}
        for invoice in invoices:
            if invoice.vendor_id in grouped:
                grouped[invoice.vendor_id].append(invoice)
        
        return grouped
    
    async def invalidate_cache(self, document_id: str) -> None:
        """Invalidate cache entries for an invoice."""
        await self.cache.delete(f"invoice:{document_id}")
        await self.cache.invalidate_pattern("invoices:")
    
    async def update_status(self, document_id: str, status: InvoiceStatus) -> Optional[InvoiceDB]:
        """Update invoice status and invalidate cache."""
        invoice = await self.get_by_id(document_id)
        if invoice:
            invoice.status = status
            invoice.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.invalidate_cache(document_id)
        return invoice
    
    async def search_by_vendor(self, vendor_name: str, limit: int = 100) -> List[InvoiceDB]:
        """Search invoices by vendor name."""
        from sqlalchemy import cast, String
        # Use cast for SQLite compatibility (astext is PostgreSQL-specific)
        result = await self.session.execute(
            select(InvoiceDB)
            .where(
                cast(InvoiceDB.invoice_data["vendor_name"], String).ilike(f"%{vendor_name}%")
            )
            .order_by(desc(InvoiceDB.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


class PurchaseOrderRepository:
    """Repository for Purchase Order operations with query optimization."""
    
    def __init__(self, session: AsyncSession, cache: Optional[QueryCache] = None):
        self.session = session
        self.cache = cache or get_default_cache()
        self.analyzer = get_default_analyzer()
    
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
        """Get PO by PO number with line items (eager loaded)."""
        cache_key = f"po:{po_number}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("po_get_by_number"):
            result = await self.session.execute(
                select(PurchaseOrderDB)
                .where(PurchaseOrderDB.po_number == po_number)
                .options(
                    selectinload(PurchaseOrderDB.line_items),
                    joinedload(PurchaseOrderDB.vendor),
                )
            )
            po = result.scalar_one_or_none()
        
        if po:
            await self.cache.set(cache_key, po, ttl=120)
        
        return po
    
    async def get_by_vendor(self, vendor_id: str, status: Optional[POStatus] = None) -> List[PurchaseOrderDB]:
        """Get POs by vendor, optionally filtered by status.
        
        Uses ix_purchase_orders_vendor_id_status index.
        """
        cache_key = f"pos:vendor:{vendor_id}:status:{status}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("po_get_by_vendor"):
            query = select(PurchaseOrderDB).where(PurchaseOrderDB.vendor_id == vendor_id)
            
            if status:
                query = query.where(PurchaseOrderDB.status == status)
            
            query = (
                query
                .options(selectinload(PurchaseOrderDB.line_items))
                .order_by(desc(PurchaseOrderDB.created_date))
            )
            
            result = await self.session.execute(query)
            pos = list(result.scalars().all())
        
        await self.cache.set(cache_key, pos, ttl=60)
        return pos
    
    async def find_candidates(
        self,
        vendor_id: str,
        amount_min: float,
        amount_max: float,
        status: POStatus = POStatus.OPEN
    ) -> List[PurchaseOrderDB]:
        """Find candidate POs for matching based on vendor and amount range.
        
        Optimized with vendor_id + status composite index.
        """
        async with self.analyzer.track("po_find_candidates"):
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
        """Update PO status and invalidate cache."""
        po = await self.get_by_po_number(po_number)
        if po:
            po.status = status
            po.updated_at = datetime.utcnow()
            await self.session.flush()
            # Invalidate cache
            await self.cache.delete(f"po:{po_number}")
            await self.cache.invalidate_pattern(f"pos:vendor:{po.vendor_id}")
        return po


class VendorRepository:
    """Repository for Vendor operations with query optimization."""
    
    def __init__(self, session: AsyncSession, cache: Optional[QueryCache] = None):
        self.session = session
        self.cache = cache or get_default_cache()
        self.analyzer = get_default_analyzer()
    
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
        """Get vendor by ID with related data (eager loaded)."""
        cache_key = f"vendor:{vendor_id}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("vendor_get_by_id"):
            result = await self.session.execute(
                select(VendorDB)
                .where(VendorDB.vendor_id == vendor_id)
                .options(
                    selectinload(VendorDB.payment_history),
                    selectinload(VendorDB.fraud_flags)
                )
            )
            vendor = result.scalar_one_or_none()
        
        if vendor:
            await self.cache.set(cache_key, vendor, ttl=300)  # 5 min cache for vendors
        
        return vendor
    
    async def get_by_ids_batch(self, vendor_ids: List[str]) -> Dict[str, VendorDB]:
        """Batch load vendors by IDs.
        
        Prevents N+1 queries when loading multiple vendors.
        """
        # Check cache for each vendor
        result: Dict[str, VendorDB] = {}
        uncached_ids: List[str] = []
        
        for vid in vendor_ids:
            cached = await self.cache.get(f"vendor:{vid}")
            if cached:
                result[vid] = cached
            else:
                uncached_ids.append(vid)
        
        if uncached_ids:
            async with self.analyzer.track("vendor_get_by_ids_batch"):
                query_result = await self.session.execute(
                    select(VendorDB)
                    .where(VendorDB.vendor_id.in_(uncached_ids))
                    .options(
                        selectinload(VendorDB.payment_history),
                        selectinload(VendorDB.fraud_flags)
                    )
                )
                vendors = query_result.scalars().all()
            
            for vendor in vendors:
                result[vendor.vendor_id] = vendor
                await self.cache.set(f"vendor:{vendor.vendor_id}", vendor, ttl=300)
        
        return result
    
    async def search_by_name(self, name: str) -> List[VendorDB]:
        """Search vendors by name using optimized index.
        
        Uses ix_vendors_name_lower index for case-insensitive search.
        """
        async with self.analyzer.track("vendor_search_by_name"):
            result = await self.session.execute(
                select(VendorDB)
                .where(func.lower(VendorDB.vendor_name).like(f"%{name.lower()}%"))
                .order_by(VendorDB.vendor_name)
            )
            return list(result.scalars().all())
    
    async def get_all_active(self) -> List[VendorDB]:
        """Get all active vendors using optimized index.
        
        Uses ix_vendors_status index.
        """
        cache_key = "vendors:active"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("vendor_get_all_active"):
            result = await self.session.execute(
                select(VendorDB)
                .where(VendorDB.status == VendorStatus.ACTIVE)
                .order_by(VendorDB.vendor_name)
            )
            vendors = list(result.scalars().all())
        
        await self.cache.set(cache_key, vendors, ttl=300)
        return vendors
    
    async def update_risk_profile(self, vendor_id: str, risk_profile: dict) -> Optional[VendorDB]:
        """Update vendor risk profile and invalidate cache."""
        vendor = await self.get_by_id(vendor_id)
        if vendor:
            vendor.risk_profile = risk_profile
            vendor.updated_at = datetime.utcnow()
            await self.session.flush()
            # Invalidate cache
            await self.cache.delete(f"vendor:{vendor_id}")
            await self.cache.invalidate_pattern("vendors:")
        return vendor


class MatchingRepository:
    """Repository for Matching Result operations with query optimization."""
    
    def __init__(self, session: AsyncSession, cache: Optional[QueryCache] = None):
        self.session = session
        self.cache = cache or get_default_cache()
        self.analyzer = get_default_analyzer()
    
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
            ai_evaluation=getattr(matching_result, "ai_evaluation", None),
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
        """Get latest matching result for an invoice with eager loading."""
        cache_key = f"matching:invoice:{invoice_id}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("matching_get_by_invoice"):
            result = await self.session.execute(
                select(MatchingResultDB)
                .where(MatchingResultDB.invoice_id == invoice_id)
                .options(
                    joinedload(MatchingResultDB.purchase_order),
                )
                .order_by(desc(MatchingResultDB.matched_at))
            )
            matching = result.scalars().first()
        
        if matching:
            await self.cache.set(cache_key, matching, ttl=60)
        
        return matching
    
    async def get_by_document_id(self, document_id: str) -> Optional[MatchingResultDB]:
        """Alias for get_by_invoice_id for consistency with other repositories."""
        return await self.get_by_invoice_id(document_id)
    
    async def get_unmatched(self, limit: int = 100) -> List[MatchingResultDB]:
        """Get unmatched results using optimized index.
        
        Uses ix_matching_results_matched index.
        """
        async with self.analyzer.track("matching_get_unmatched"):
            result = await self.session.execute(
                select(MatchingResultDB)
                .where(MatchingResultDB.matched == False)
                .order_by(desc(MatchingResultDB.matched_at))
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def get_by_confidence_range(
        self,
        min_score: float,
        max_score: float,
        limit: int = 100,
    ) -> List[MatchingResultDB]:
        """Get matching results by confidence score range.
        
        Uses ix_matching_results_confidence_score index.
        """
        async with self.analyzer.track("matching_get_by_confidence"):
            result = await self.session.execute(
                select(MatchingResultDB)
                .where(
                    and_(
                        MatchingResultDB.confidence_score >= min_score,
                        MatchingResultDB.confidence_score <= max_score,
                    )
                )
                .order_by(desc(MatchingResultDB.confidence_score))
                .limit(limit)
            )
            return list(result.scalars().all())

    async def delete_by_invoice_id(self, invoice_id: str) -> int:
        """Delete all matching results for an invoice.
        
        Returns the number of deleted records.
        """
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(MatchingResultDB).where(MatchingResultDB.invoice_id == invoice_id)
        )
        # Clear cache
        cache_key = f"matching:invoice:{invoice_id}"
        await self.cache.delete(cache_key)
        return result.rowcount


class RiskRepository:
    """Repository for Risk Assessment operations with query optimization."""
    
    def __init__(self, session: AsyncSession, cache: Optional[QueryCache] = None):
        self.session = session
        self.cache = cache or get_default_cache()
        self.analyzer = get_default_analyzer()
    
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
            matching_risk_score=risk_assessment.matching_risk_score,
            pattern_risk_score=risk_assessment.pattern_risk_score,
            risk_flags=[f.model_dump(mode="json") for f in risk_assessment.risk_flags],
            critical_flags=risk_assessment.critical_flags,
            high_flags=risk_assessment.high_flags,
            duplicate_info=risk_assessment.duplicate_info.model_dump(mode="json") if risk_assessment.duplicate_info else None,
            vendor_risk_info=risk_assessment.vendor_risk_info.model_dump(mode="json") if risk_assessment.vendor_risk_info else None,
            price_anomaly_info=risk_assessment.price_anomaly_info.model_dump(mode="json") if risk_assessment.price_anomaly_info else None,
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
        cache_key = f"risk:invoice:{invoice_id}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("risk_get_by_invoice"):
            result = await self.session.execute(
                select(RiskAssessmentDB)
                .where(RiskAssessmentDB.invoice_id == invoice_id)
                .order_by(desc(RiskAssessmentDB.assessed_at))
            )
            assessment = result.scalars().first()
        
        if assessment:
            await self.cache.set(cache_key, assessment, ttl=60)
        
        return assessment
    
    async def get_by_document_id(self, document_id: str) -> Optional[RiskAssessmentDB]:
        """Alias for get_by_invoice_id for consistency with other repositories."""
        return await self.get_by_invoice_id(document_id)
    
    async def get_high_risk_invoices(self, limit: int = 50) -> List[RiskAssessmentDB]:
        """Get high and critical risk assessments using optimized index.
        
        Uses ix_risk_assessments_risk_level index.
        """
        cache_key = f"risk:high_risk:limit:{limit}"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("risk_get_high_risk"):
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
            assessments = list(result.scalars().all())
        
        await self.cache.set(cache_key, assessments, ttl=30)
        return assessments
    
    async def get_by_risk_level(
        self,
        risk_level: str,
        limit: int = 100,
    ) -> List[RiskAssessmentDB]:
        """Get assessments by specific risk level.
        
        Uses ix_risk_assessments_risk_level index.
        """
        async with self.analyzer.track("risk_get_by_level"):
            result = await self.session.execute(
                select(RiskAssessmentDB)
                .where(RiskAssessmentDB.risk_level == risk_level)
                .order_by(desc(RiskAssessmentDB.assessed_at))
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get risk assessment statistics for dashboard.
        
        Aggregates counts by risk level efficiently.
        """
        cache_key = "risk:statistics"
        
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.analyzer.track("risk_get_statistics"):
            result = await self.session.execute(
                select(
                    RiskAssessmentDB.risk_level,
                    func.count(RiskAssessmentDB.id).label("count"),
                )
                .group_by(RiskAssessmentDB.risk_level)
            )
            rows = result.all()
        
        stats = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
            "total": 0,
        }
        
        for row in rows:
            level, count = row
            if level in stats:
                stats[level] = count
            stats["total"] += count
        
        await self.cache.set(cache_key, stats, ttl=60)
        return stats
