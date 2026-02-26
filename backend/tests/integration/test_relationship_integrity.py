"""
Relationship and Referential Integrity Tests

Tests for foreign key relationships, cascade operations, and data integrity.
V3.2.2 - Database Integration Testing
"""

import pytest
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import (
    InvoiceDB,
    PurchaseOrderDB,
    POLineItemDB,
    VendorDB,
    PaymentRecordDB,
    FraudFlagDB,
    MatchingResultDB,
    RiskAssessmentDB,
)
from src.models.invoice import InvoiceStatus
from src.models.purchase_order import POStatus
from src.models.vendor import FraudFlagType
from src.models.matching import MatchType
from src.models.risk import RiskLevel, RecommendedAction


# =============================================================================
# Vendor Relationships Tests
# =============================================================================

class TestVendorRelationships:
    """Tests for vendor entity relationships."""
    
    @pytest.mark.asyncio
    async def test_vendor_has_many_purchase_orders(self, test_db_session: AsyncSession):
        """Test vendor can have multiple purchase orders."""
        vendor_id = f"V-REL-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Relationship Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create multiple POs
        for i in range(3):
            po = PurchaseOrderDB(
                po_number=f"PO-REL-{vendor_id}-{i}",
                vendor_id=vendor_id,
                created_date=date.today(),
                status=POStatus.OPEN,
                subtotal=Decimal("100.00"),
                total_amount=Decimal("100.00"),
            )
            test_db_session.add(po)
        await test_db_session.commit()
        
        # Query vendor with POs
        result = await test_db_session.execute(
            select(VendorDB)
            .options(selectinload(VendorDB.purchase_orders))
            .where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        
        assert len(vendor.purchase_orders) == 3
    
    @pytest.mark.asyncio
    async def test_vendor_has_payment_history(self, test_db_session: AsyncSession):
        """Test vendor payment history relationship."""
        vendor_id = f"V-PAY-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Payment History Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create payment records
        for i in range(2):
            payment = PaymentRecordDB(
                vendor_id=vendor_id,
                payment_id=f"PAY-{vendor_id}-{i}",
                invoice_number=f"INV-{vendor_id}-{i}",
                amount=Decimal("500.00"),
                payment_date=date.today(),
                days_to_pay=30,
            )
            test_db_session.add(payment)
        await test_db_session.commit()
        
        # Query vendor with payments
        result = await test_db_session.execute(
            select(VendorDB)
            .options(selectinload(VendorDB.payment_history))
            .where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        
        assert len(vendor.payment_history) == 2
    
    @pytest.mark.asyncio
    async def test_vendor_has_fraud_flags(self, test_db_session: AsyncSession):
        """Test vendor fraud flags relationship."""
        vendor_id = f"V-FRAUD-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Fraud Flag Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create fraud flag
        fraud_flag = FraudFlagDB(
            vendor_id=vendor_id,
            flag_id=f"FLAG-{vendor_id}",
            flag_type=FraudFlagType.SUSPICIOUS_AMOUNT,
            severity="high",
            description="Suspicious amount pattern detected",
        )
        test_db_session.add(fraud_flag)
        await test_db_session.commit()
        
        # Query vendor with flags
        result = await test_db_session.execute(
            select(VendorDB)
            .options(selectinload(VendorDB.fraud_flags))
            .where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        
        assert len(vendor.fraud_flags) == 1
        assert vendor.fraud_flags[0].flag_type == FraudFlagType.SUSPICIOUS_AMOUNT


# =============================================================================
# Purchase Order Relationships Tests
# =============================================================================

class TestPurchaseOrderRelationships:
    """Tests for purchase order entity relationships."""
    
    @pytest.mark.asyncio
    async def test_po_belongs_to_vendor(self, test_db_session: AsyncSession):
        """Test PO belongs to vendor relationship."""
        vendor_id = f"V-POREL-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="PO Relationship Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create PO
        po = PurchaseOrderDB(
            po_number=f"PO-BELONGS-{vendor_id}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        test_db_session.add(po)
        await test_db_session.commit()
        
        # Query PO with vendor
        result = await test_db_session.execute(
            select(PurchaseOrderDB)
            .options(selectinload(PurchaseOrderDB.vendor))
            .where(PurchaseOrderDB.po_number == po.po_number)
        )
        po = result.scalar_one()
        
        assert po.vendor is not None
        assert po.vendor.vendor_name == "PO Relationship Vendor"
    
    @pytest.mark.asyncio
    async def test_po_has_many_line_items(self, test_db_session: AsyncSession):
        """Test PO has many line items relationship."""
        vendor_id = f"V-POLINE-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Line Item Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create PO
        po = PurchaseOrderDB(
            po_number=f"PO-LINES-{vendor_id}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("300.00"),
            total_amount=Decimal("300.00"),
        )
        test_db_session.add(po)
        await test_db_session.flush()
        
        # Create line items
        for i in range(3):
            line = POLineItemDB(
                po_id=po.id,
                line_number=i + 1,
                description=f"Line Item {i + 1}",
                quantity=float(i + 1),
                unit_price=Decimal("100.00"),
                amount=Decimal("100.00") * (i + 1),
            )
            test_db_session.add(line)
        await test_db_session.commit()
        
        # Query PO with line items
        result = await test_db_session.execute(
            select(PurchaseOrderDB)
            .options(selectinload(PurchaseOrderDB.line_items))
            .where(PurchaseOrderDB.po_number == po.po_number)
        )
        po = result.scalar_one()
        
        assert len(po.line_items) == 3
        assert po.line_items[0].description == "Line Item 1"


# =============================================================================
# Invoice Relationships Tests
# =============================================================================

class TestInvoiceRelationships:
    """Tests for invoice entity relationships."""
    
    @pytest.mark.asyncio
    async def test_invoice_has_matching_results(self, test_db_session: AsyncSession):
        """Test invoice has matching results relationship."""
        doc_id = f"DOC-MATCH-{uuid.uuid4().hex[:8]}"
        
        # Create invoice
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number=f"INV-MATCH-{uuid.uuid4().hex[:8]}",
            file_name="match_test.pdf",
            file_hash=f"match_hash_{uuid.uuid4().hex[:8]}",
            status=InvoiceStatus.MATCHED,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Create matching result
        matching = MatchingResultDB(
            invoice_id=doc_id,
            matching_id=f"MR-{doc_id}",
            match_type=MatchType.EXACT,
            match_score=0.95,
            matched=True,
            vendor_match_score=1.0,
            amount_match_score=0.95,
        )
        test_db_session.add(matching)
        await test_db_session.commit()
        
        # Query invoice with matching results
        result = await test_db_session.execute(
            select(InvoiceDB)
            .options(selectinload(InvoiceDB.matching_results))
            .where(InvoiceDB.document_id == doc_id)
        )
        invoice = result.scalar_one()
        
        assert len(invoice.matching_results) == 1
        assert invoice.matching_results[0].match_type == MatchType.EXACT
    
    @pytest.mark.asyncio
    async def test_invoice_has_risk_assessments(self, test_db_session: AsyncSession):
        """Test invoice has risk assessments relationship."""
        doc_id = f"DOC-RISK-{uuid.uuid4().hex[:8]}"
        
        # Create invoice
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number=f"INV-RISK-{uuid.uuid4().hex[:8]}",
            file_name="risk_test.pdf",
            file_hash=f"risk_hash_{uuid.uuid4().hex[:8]}",
            status=InvoiceStatus.RISK_REVIEW,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Create risk assessment
        risk = RiskAssessmentDB(
            invoice_id=doc_id,
            assessment_id=f"RA-{doc_id}",
            risk_level=RiskLevel.MEDIUM,
            risk_score=0.5,
            recommended_action=RecommendedAction.REVIEW,
            action_reason="Medium risk detected",
            requires_manual_review=True,
        )
        test_db_session.add(risk)
        await test_db_session.commit()
        
        # Query invoice with risk assessments
        result = await test_db_session.execute(
            select(InvoiceDB)
            .options(selectinload(InvoiceDB.risk_assessments))
            .where(InvoiceDB.document_id == doc_id)
        )
        invoice = result.scalar_one()
        
        assert len(invoice.risk_assessments) == 1
        assert invoice.risk_assessments[0].risk_level == RiskLevel.MEDIUM


# =============================================================================
# Cascade Delete Tests
# =============================================================================

class TestCascadeDelete:
    """Tests for cascade delete operations."""
    
    @pytest.mark.asyncio
    async def test_delete_vendor_cascades_to_pos_via_db(self, test_db_session: AsyncSession):
        """Test deleting vendor cascades to purchase orders via database FK constraint.
        
        Note: This tests database-level cascade delete (ON DELETE CASCADE in FK definition)
        rather than SQLAlchemy ORM-level cascade which requires explicit cascade config.
        We use raw SQL DELETE to bypass ORM and test DB-level cascade.
        """
        vendor_id = f"V-CASCADE-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Cascade Delete Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create POs
        po_numbers = []
        for i in range(2):
            po = PurchaseOrderDB(
                po_number=f"PO-CASCADE-{vendor_id}-{i}",
                vendor_id=vendor_id,
                created_date=date.today(),
                status=POStatus.OPEN,
                subtotal=Decimal("100.00"),
                total_amount=Decimal("100.00"),
            )
            test_db_session.add(po)
            po_numbers.append(po.po_number)
        await test_db_session.commit()
        
        # Delete vendor using raw SQL to test DB-level cascade
        from sqlalchemy import text
        await test_db_session.execute(
            text("DELETE FROM vendors WHERE vendor_id = :vid"),
            {"vid": vendor_id}
        )
        await test_db_session.commit()
        
        # Expire session to force reload
        test_db_session.expire_all()
        
        # Verify POs are deleted (cascade)
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(
                PurchaseOrderDB.po_number.in_(po_numbers)
            )
        )
        pos = result.scalars().all()
        assert len(pos) == 0
    
    @pytest.mark.asyncio
    async def test_delete_vendor_cascades_to_payments(self, test_db_session: AsyncSession):
        """Test deleting vendor cascades to payment records."""
        vendor_id = f"V-PAYCASCADE-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Payment Cascade Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create payment record
        payment = PaymentRecordDB(
            vendor_id=vendor_id,
            payment_id=f"PAY-CASCADE-{vendor_id}",
            invoice_number="INV-001",
            amount=Decimal("500.00"),
            payment_date=date.today(),
            days_to_pay=30,
        )
        test_db_session.add(payment)
        await test_db_session.commit()
        
        payment_id = payment.payment_id
        
        # Delete vendor
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        await test_db_session.delete(vendor)
        await test_db_session.commit()
        
        # Verify payment is deleted
        result = await test_db_session.execute(
            select(PaymentRecordDB).where(PaymentRecordDB.payment_id == payment_id)
        )
        payments = result.scalars().all()
        assert len(payments) == 0
    
    @pytest.mark.asyncio
    async def test_delete_po_cascades_to_line_items(self, test_db_session: AsyncSession):
        """Test deleting PO cascades to line items."""
        vendor_id = f"V-LINECASCADE-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Line Cascade Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create PO with line items
        po = PurchaseOrderDB(
            po_number=f"PO-LINECASCADE-{vendor_id}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        test_db_session.add(po)
        await test_db_session.flush()
        
        po_id = po.id
        
        # Add line items
        for i in range(3):
            line = POLineItemDB(
                po_id=po.id,
                line_number=i + 1,
                description=f"Cascade Item {i + 1}",
                quantity=1.0,
                unit_price=Decimal("100.00"),
                amount=Decimal("100.00"),
            )
            test_db_session.add(line)
        await test_db_session.commit()
        
        # Delete PO
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.id == po_id)
        )
        po = result.scalar_one()
        await test_db_session.delete(po)
        await test_db_session.commit()
        
        # Verify line items are deleted
        result = await test_db_session.execute(
            select(POLineItemDB).where(POLineItemDB.po_id == po_id)
        )
        lines = result.scalars().all()
        assert len(lines) == 0
    
    @pytest.mark.asyncio
    async def test_delete_invoice_cascades_to_matching(self, test_db_session: AsyncSession):
        """Test deleting invoice cascades to matching results."""
        doc_id = f"DOC-MATCHCASCADE-{uuid.uuid4().hex[:8]}"
        
        # Create invoice
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number=f"INV-MATCHCASCADE-{uuid.uuid4().hex[:8]}",
            file_name="cascade_match.pdf",
            file_hash=f"cascade_hash_{uuid.uuid4().hex[:8]}",
            status=InvoiceStatus.MATCHED,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Create matching result
        matching = MatchingResultDB(
            invoice_id=doc_id,
            matching_id=f"MR-CASCADE-{doc_id}",
            match_type=MatchType.EXACT,
            match_score=0.95,
            matched=True,
        )
        test_db_session.add(matching)
        await test_db_session.commit()
        
        matching_id = matching.matching_id
        
        # Delete invoice
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        invoice = result.scalar_one()
        await test_db_session.delete(invoice)
        await test_db_session.commit()
        
        # Verify matching result is deleted
        result = await test_db_session.execute(
            select(MatchingResultDB).where(MatchingResultDB.matching_id == matching_id)
        )
        matches = result.scalars().all()
        assert len(matches) == 0


# =============================================================================
# Referential Integrity Tests
# =============================================================================

class TestReferentialIntegrity:
    """Tests for referential integrity constraints."""
    
    @pytest.mark.asyncio
    async def test_cannot_create_po_without_vendor(self, test_db_session: AsyncSession):
        """Test that PO cannot be created without valid vendor."""
        po = PurchaseOrderDB(
            po_number=f"PO-NOVENDOR-{uuid.uuid4().hex[:8]}",
            vendor_id="NON_EXISTENT_VENDOR",
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        test_db_session.add(po)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_cannot_create_payment_without_vendor(self, test_db_session: AsyncSession):
        """Test that payment cannot be created without valid vendor."""
        payment = PaymentRecordDB(
            vendor_id="NON_EXISTENT_VENDOR",
            payment_id=f"PAY-NOVENDOR-{uuid.uuid4().hex[:8]}",
            invoice_number="INV-001",
            amount=Decimal("500.00"),
            payment_date=date.today(),
            days_to_pay=30,
        )
        test_db_session.add(payment)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_cannot_create_line_item_without_po(self, test_db_session: AsyncSession):
        """Test that line item cannot be created without valid PO."""
        line = POLineItemDB(
            po_id=99999,  # Non-existent PO
            line_number=1,
            description="Orphan Line Item",
            quantity=1.0,
            unit_price=Decimal("100.00"),
            amount=Decimal("100.00"),
        )
        test_db_session.add(line)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_cannot_create_matching_without_invoice(self, test_db_session: AsyncSession):
        """Test that matching result cannot be created without valid invoice."""
        matching = MatchingResultDB(
            invoice_id="NON_EXISTENT_INVOICE",
            matching_id=f"MR-NOINVOICE-{uuid.uuid4().hex[:8]}",
            match_type=MatchType.EXACT,
            match_score=0.95,
            matched=True,
        )
        test_db_session.add(matching)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_cannot_create_risk_without_invoice(self, test_db_session: AsyncSession):
        """Test that risk assessment cannot be created without valid invoice."""
        risk = RiskAssessmentDB(
            invoice_id="NON_EXISTENT_INVOICE",
            assessment_id=f"RA-NOINVOICE-{uuid.uuid4().hex[:8]}",
            risk_level=RiskLevel.LOW,
            risk_score=0.1,
            recommended_action=RecommendedAction.AUTO_APPROVE,
            action_reason="Test",
            requires_manual_review=False,
        )
        test_db_session.add(risk)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()


# =============================================================================
# Orphan Record Tests
# =============================================================================

class TestOrphanRecords:
    """Tests for handling orphan records."""
    
    @pytest.mark.asyncio
    async def test_no_orphan_line_items(self, test_db_session: AsyncSession):
        """Test that deleting PO removes all line items."""
        vendor_id = f"V-ORPHAN-{uuid.uuid4().hex[:8]}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Orphan Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create PO with line items
        po = PurchaseOrderDB(
            po_number=f"PO-ORPHAN-{vendor_id}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("200.00"),
            total_amount=Decimal("200.00"),
        )
        test_db_session.add(po)
        await test_db_session.flush()
        
        po_id = po.id
        
        for i in range(2):
            line = POLineItemDB(
                po_id=po.id,
                line_number=i + 1,
                description=f"Orphan Test Item {i + 1}",
                quantity=1.0,
                unit_price=Decimal("100.00"),
                amount=Decimal("100.00"),
            )
            test_db_session.add(line)
        await test_db_session.commit()
        
        # Delete PO
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.id == po_id)
        )
        po = result.scalar_one()
        await test_db_session.delete(po)
        await test_db_session.commit()
        
        # Verify no orphan line items
        result = await test_db_session.execute(
            select(POLineItemDB).where(POLineItemDB.po_id == po_id)
        )
        orphans = result.scalars().all()
        assert len(orphans) == 0
    
    @pytest.mark.asyncio
    async def test_no_orphan_matching_results(self, test_db_session: AsyncSession):
        """Test that deleting invoice removes all matching results."""
        doc_id = f"DOC-ORPHANMATCH-{uuid.uuid4().hex[:8]}"
        
        # Create invoice
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number=f"INV-ORPHANMATCH-{uuid.uuid4().hex[:8]}",
            file_name="orphan_match.pdf",
            file_hash=f"orphan_hash_{uuid.uuid4().hex[:8]}",
            status=InvoiceStatus.MATCHED,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Create multiple matching results
        for i in range(2):
            matching = MatchingResultDB(
                invoice_id=doc_id,
                matching_id=f"MR-ORPHAN-{doc_id}-{i}",
                match_type=MatchType.FUZZY,
                match_score=0.8 + (i * 0.05),
                matched=True,
            )
            test_db_session.add(matching)
        await test_db_session.commit()
        
        # Delete invoice
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        invoice = result.scalar_one()
        await test_db_session.delete(invoice)
        await test_db_session.commit()
        
        # Verify no orphan matching results
        result = await test_db_session.execute(
            select(MatchingResultDB).where(MatchingResultDB.invoice_id == doc_id)
        )
        orphans = result.scalars().all()
        assert len(orphans) == 0


# =============================================================================
# Complex Relationship Tests
# =============================================================================

class TestComplexRelationships:
    """Tests for complex relationship scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_invoice_lifecycle(self, test_db_session: AsyncSession):
        """Test full invoice lifecycle with all relationships."""
        base_id = uuid.uuid4().hex[:6]
        vendor_id = f"V-LIFECYCLE-{base_id}"
        doc_id = f"DOC-LIFECYCLE-{base_id}"
        
        # 1. Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Lifecycle Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        
        # 2. Create PO
        po = PurchaseOrderDB(
            po_number=f"PO-LIFECYCLE-{base_id}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )
        test_db_session.add(po)
        await test_db_session.flush()
        
        # 3. Create PO line items
        line = POLineItemDB(
            po_id=po.id,
            line_number=1,
            description="Lifecycle Item",
            quantity=10.0,
            unit_price=Decimal("100.00"),
            amount=Decimal("1000.00"),
        )
        test_db_session.add(line)
        
        # 4. Create invoice
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number=f"INV-LIFECYCLE-{base_id}",
            file_name="lifecycle.pdf",
            file_hash=f"lifecycle_hash_{base_id}",
            status=InvoiceStatus.EXTRACTED,
            invoice_data={"vendor_id": vendor_id, "po_number": po.po_number},
        )
        test_db_session.add(invoice)
        
        # 5. Create matching result
        matching = MatchingResultDB(
            invoice_id=doc_id,
            po_id=po.id,
            matching_id=f"MR-LIFECYCLE-{base_id}",
            match_type=MatchType.EXACT,
            match_score=0.98,
            matched=True,
            vendor_match_score=1.0,
            amount_match_score=0.98,
        )
        test_db_session.add(matching)
        
        # 6. Create risk assessment
        risk = RiskAssessmentDB(
            invoice_id=doc_id,
            assessment_id=f"RA-LIFECYCLE-{base_id}",
            risk_level=RiskLevel.LOW,
            risk_score=0.1,
            recommended_action=RecommendedAction.AUTO_APPROVE,
            action_reason="Low risk, high confidence match",
            requires_manual_review=False,
        )
        test_db_session.add(risk)
        
        await test_db_session.commit()
        
        # Verify all relationships
        # Query invoice with all relationships
        result = await test_db_session.execute(
            select(InvoiceDB)
            .options(
                selectinload(InvoiceDB.matching_results),
                selectinload(InvoiceDB.risk_assessments),
            )
            .where(InvoiceDB.document_id == doc_id)
        )
        invoice = result.scalar_one()
        
        assert len(invoice.matching_results) == 1
        assert len(invoice.risk_assessments) == 1
        assert invoice.matching_results[0].match_score == 0.98
        assert invoice.risk_assessments[0].risk_level == RiskLevel.LOW
        
        # Query PO with relationships
        result = await test_db_session.execute(
            select(PurchaseOrderDB)
            .options(
                selectinload(PurchaseOrderDB.vendor),
                selectinload(PurchaseOrderDB.line_items),
                selectinload(PurchaseOrderDB.matching_results),
            )
            .where(PurchaseOrderDB.po_number == po.po_number)
        )
        po = result.scalar_one()
        
        assert po.vendor.vendor_name == "Lifecycle Test Vendor"
        assert len(po.line_items) == 1
        assert len(po.matching_results) == 1
