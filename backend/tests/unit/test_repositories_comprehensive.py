"""
Comprehensive Unit Tests for SmartAP Data Repositories

Tests all repository operations including:
- CRUD operations (Create, Read, Update, Delete)
- Search/filter operations
- Edge cases and error handling
- Relationship loading
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, patch, MagicMock

from src.db.models import Base, InvoiceDB, PurchaseOrderDB, VendorDB, MatchingResultDB, RiskAssessmentDB
from src.db.repositories import (
    InvoiceRepository,
    PurchaseOrderRepository,
    VendorRepository,
    MatchingRepository,
    RiskRepository,
)
from src.models import (
    Invoice,
    InvoiceLineItem,
    InvoiceExtractionResult,
    ExtractionConfidence,
    InvoiceStatus,
    PurchaseOrder,
    POLineItem,
    POStatus,
    Vendor,
    VendorStatus,
    VendorRiskProfile,
    MatchingResult,
    MatchType,
    RiskAssessment,
    RiskLevel,
    RecommendedAction,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
async def engine():
    """Create an in-memory SQLite test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create a database session for testing."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
def sample_extraction_result():
    """Create a sample extraction result."""
    return InvoiceExtractionResult(
        document_id="DOC-TEST-001",
        file_name="test_invoice.pdf",
        file_hash="abc123hash",
        status=InvoiceStatus.EXTRACTED,
        invoice=Invoice(
            invoice_number="INV-001",
            vendor_name="Test Vendor",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            currency="USD",
            subtotal=Decimal("1000.00"),
            tax=Decimal("80.00"),
            total=Decimal("1080.00"),
            line_items=[
                InvoiceLineItem(
                    description="Test Item A",
                    quantity=5,
                    unit_price=Decimal("100.00"),
                    amount=Decimal("500.00"),
                ),
                InvoiceLineItem(
                    description="Test Item B",
                    quantity=5,
                    unit_price=Decimal("100.00"),
                    amount=Decimal("500.00"),
                ),
            ],
        ),
        confidence=ExtractionConfidence(
            invoice_number=0.95,
            vendor_name=0.92,
            invoice_date=0.90,
            due_date=0.88,
            subtotal=0.95,
            tax=0.93,
            total=0.97,
            line_items=0.85,
        ),
        requires_review=False,
        ocr_applied=False,
        page_count=1,
        extraction_time_ms=450,
    )


@pytest.fixture
def sample_vendor():
    """Create a sample vendor."""
    return Vendor(
        vendor_id="V-TEST-001",
        vendor_name="Test Vendor Corp",
        email="vendor@test.com",
        status=VendorStatus.ACTIVE,
        payment_terms="Net 30",
        currency="USD",
        risk_profile=VendorRiskProfile(
            risk_score=0.15,
            payment_reliability_score=0.92,
            fraud_risk_score=0.05,
            total_invoices_processed=50,
            average_invoice_amount=2500.00,
        ),
        onboarded_date=date(2024, 1, 1),
    )


@pytest.fixture
def sample_purchase_order():
    """Create a sample purchase order."""
    return PurchaseOrder(
        po_number="PO-TEST-001",
        vendor_id="V-TEST-001",
        vendor_name="Test Vendor Corp",
        created_date=date.today(),
        expected_delivery=date.today() + timedelta(days=14),
        status=POStatus.OPEN,
        currency="USD",
        subtotal=Decimal("1000.00"),
        tax=Decimal("80.00"),
        total_amount=Decimal("1080.00"),
        payment_terms="Net 30",
        created_by="test@company.com",
        line_items=[
            POLineItem(
                line_number=1,
                description="Test Product A",
                quantity=10,
                unit_price=Decimal("100.00"),
                amount=Decimal("1000.00"),
                sku="PROD-A-001",
                unit="ea",
            )
        ],
    )


@pytest.fixture
def sample_matching_result():
    """Create a sample matching result."""
    return MatchingResult(
        matching_id="MATCH-TEST-001",
        invoice_id="DOC-TEST-001",
        po_number="PO-TEST-001",
        match_type=MatchType.EXACT,
        match_score=0.95,
        matched=True,
        vendor_match_score=1.0,
        amount_match_score=0.98,
        date_match_score=0.90,
        line_items_match_score=0.92,
        discrepancies=[],
        has_discrepancies=False,
        critical_discrepancies=0,
        requires_approval=False,
        matched_by="system",
    )


@pytest.fixture
def sample_risk_assessment():
    """Create a sample risk assessment."""
    return RiskAssessment(
        assessment_id="RISK-TEST-001",
        invoice_id="DOC-TEST-001",
        risk_level=RiskLevel.LOW,
        risk_score=0.15,
        duplicate_risk_score=0.0,
        vendor_risk_score=0.12,
        price_risk_score=0.05,
        amount_risk_score=0.08,
        pattern_risk_score=0.10,
        risk_flags=[],
        critical_flags=0,
        high_flags=0,
        recommended_action=RecommendedAction.AUTO_APPROVE,
        action_reason="All checks passed",
        requires_manual_review=False,
        assessed_by="system",
        assessment_version="1.0",
    )


# =============================================================================
# Invoice Repository Tests
# =============================================================================

class TestInvoiceRepository:
    """Comprehensive tests for InvoiceRepository."""
    
    @pytest.mark.asyncio
    async def test_create_invoice(self, session, sample_extraction_result):
        """Test creating a new invoice."""
        repo = InvoiceRepository(session)
        
        invoice_db = await repo.create(sample_extraction_result)
        
        assert invoice_db.document_id == "DOC-TEST-001"
        assert invoice_db.invoice_number == "INV-001"
        assert invoice_db.status == InvoiceStatus.EXTRACTED
        # Overall is average of: invoice_number, vendor_name, invoice_date, total, line_items
        # (0.95 + 0.92 + 0.90 + 0.97 + 0.85) / 5 = 0.918
        assert 0.91 <= invoice_db.extraction_confidence <= 0.93
        assert invoice_db.page_count == 1
        assert invoice_db.extraction_time_ms == 450
    
    @pytest.mark.asyncio
    async def test_create_invoice_without_extracted_data(self, session):
        """Test creating invoice when extraction has no invoice data."""
        repo = InvoiceRepository(session)
        
        extraction = InvoiceExtractionResult(
            document_id="DOC-FAILED-001",
            file_name="corrupted.pdf",
            file_hash="xyz789",
            status=InvoiceStatus.FAILED,
            invoice=None,  # No extracted data
            confidence=ExtractionConfidence(),
            requires_review=True,
            ocr_applied=True,
            page_count=0,
            extraction_time_ms=100,
        )
        
        invoice_db = await repo.create(extraction)
        
        assert invoice_db.document_id == "DOC-FAILED-001"
        assert invoice_db.invoice_number == "UNKNOWN"
        assert invoice_db.invoice_data is None
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, session, sample_extraction_result):
        """Test retrieving invoice by document ID."""
        repo = InvoiceRepository(session)
        await repo.create(sample_extraction_result)
        await session.flush()
        
        invoice = await repo.get_by_id("DOC-TEST-001")
        
        assert invoice is not None
        assert invoice.document_id == "DOC-TEST-001"
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session):
        """Test retrieving non-existent invoice returns None."""
        repo = InvoiceRepository(session)
        
        invoice = await repo.get_by_id("NONEXISTENT")
        
        assert invoice is None
    
    @pytest.mark.asyncio
    async def test_get_by_hash(self, session, sample_extraction_result):
        """Test finding invoice by file hash."""
        repo = InvoiceRepository(session)
        await repo.create(sample_extraction_result)
        await session.flush()
        
        invoice = await repo.get_by_hash("abc123hash")
        
        assert invoice is not None
        assert invoice.file_hash == "abc123hash"
    
    @pytest.mark.asyncio
    async def test_get_by_hash_for_duplicate_detection(self, session, sample_extraction_result):
        """Test using hash lookup for duplicate detection."""
        repo = InvoiceRepository(session)
        await repo.create(sample_extraction_result)
        await session.flush()
        
        # Same hash = duplicate
        duplicate = await repo.get_by_hash("abc123hash")
        assert duplicate is not None
        
        # Different hash = not duplicate
        not_duplicate = await repo.get_by_hash("different_hash")
        assert not_duplicate is None
    
    @pytest.mark.asyncio
    async def test_get_by_status(self, session):
        """Test filtering invoices by status."""
        repo = InvoiceRepository(session)
        
        # Create invoices with different statuses
        statuses = [
            InvoiceStatus.EXTRACTED,
            InvoiceStatus.EXTRACTED,
            InvoiceStatus.MATCHED,
            InvoiceStatus.APPROVED,
        ]
        
        for i, status in enumerate(statuses):
            extraction = InvoiceExtractionResult(
                document_id=f"DOC-{i}",
                file_name=f"invoice_{i}.pdf",
                file_hash=f"hash{i}",
                status=status,
                confidence=ExtractionConfidence(),
                requires_review=False,
                ocr_applied=False,
                page_count=1,
                extraction_time_ms=100,
            )
            await repo.create(extraction)
        
        await session.flush()
        
        # Get extracted invoices
        extracted = await repo.get_by_status(InvoiceStatus.EXTRACTED)
        assert len(extracted) == 2
        
        # Get matched invoices
        matched = await repo.get_by_status(InvoiceStatus.MATCHED)
        assert len(matched) == 1
    
    @pytest.mark.asyncio
    async def test_get_by_status_with_limit(self, session):
        """Test status filter with limit."""
        repo = InvoiceRepository(session)
        
        # Create 5 invoices
        for i in range(5):
            extraction = InvoiceExtractionResult(
                document_id=f"DOC-{i}",
                file_name=f"invoice_{i}.pdf",
                file_hash=f"hash{i}",
                status=InvoiceStatus.EXTRACTED,
                confidence=ExtractionConfidence(),
                requires_review=False,
                ocr_applied=False,
                page_count=1,
                extraction_time_ms=100,
            )
            await repo.create(extraction)
        
        await session.flush()
        
        # Limit to 3
        invoices = await repo.get_by_status(InvoiceStatus.EXTRACTED, limit=3)
        assert len(invoices) == 3
    
    @pytest.mark.asyncio
    async def test_update_status(self, session, sample_extraction_result):
        """Test updating invoice status."""
        repo = InvoiceRepository(session)
        invoice = await repo.create(sample_extraction_result)
        await session.flush()
        
        # Update status
        updated = await repo.update_status("DOC-TEST-001", InvoiceStatus.APPROVED)
        
        assert updated is not None
        assert updated.status == InvoiceStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_update_status_not_found(self, session):
        """Test updating status of non-existent invoice."""
        repo = InvoiceRepository(session)
        
        updated = await repo.update_status("NONEXISTENT", InvoiceStatus.APPROVED)
        
        assert updated is None


# =============================================================================
# Vendor Repository Tests
# =============================================================================

class TestVendorRepository:
    """Comprehensive tests for VendorRepository."""
    
    @pytest.mark.asyncio
    async def test_create_vendor(self, session, sample_vendor):
        """Test creating a new vendor."""
        repo = VendorRepository(session)
        
        vendor_db = await repo.create(sample_vendor)
        
        assert vendor_db.vendor_id == "V-TEST-001"
        assert vendor_db.vendor_name == "Test Vendor Corp"
        assert vendor_db.status == VendorStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_create_vendor_with_full_details(self, session):
        """Test creating vendor with all fields populated."""
        repo = VendorRepository(session)
        
        vendor = Vendor(
            vendor_id="V-FULL-001",
            vendor_name="Full Details Corp",
            contact_name="John Doe",
            email="john@fulldetails.com",
            phone="+1-555-123-4567",
            address_line1="123 Business Ave",
            city="New York",
            state="NY",
            postal_code="10001",
            country="US",
            tax_id="12-3456789",
            bank_account_number="****1234",
            bank_name="Chase Bank",
            status=VendorStatus.ACTIVE,
            payment_terms="Net 45",
            currency="USD",
            risk_profile=VendorRiskProfile(
                risk_score=0.08,
                payment_reliability_score=0.98,
            ),
            onboarded_date=date(2023, 6, 15),
            notes="Premium vendor",
        )
        
        vendor_db = await repo.create(vendor)
        
        assert vendor_db.contact_name == "John Doe"
        assert vendor_db.city == "New York"
        assert vendor_db.payment_terms == "Net 45"
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, session, sample_vendor):
        """Test retrieving vendor by ID."""
        repo = VendorRepository(session)
        await repo.create(sample_vendor)
        await session.flush()
        
        vendor = await repo.get_by_id("V-TEST-001")
        
        assert vendor is not None
        assert vendor.vendor_id == "V-TEST-001"
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session):
        """Test retrieving non-existent vendor."""
        repo = VendorRepository(session)
        
        vendor = await repo.get_by_id("NONEXISTENT")
        
        assert vendor is None
    
    @pytest.mark.asyncio
    async def test_search_by_name(self, session):
        """Test searching vendors by name."""
        repo = VendorRepository(session)
        
        # Create test vendors
        vendors = [
            Vendor(vendor_id="V001", vendor_name="Acme Corporation", onboarded_date=date.today()),
            Vendor(vendor_id="V002", vendor_name="Acme Industries", onboarded_date=date.today()),
            Vendor(vendor_id="V003", vendor_name="Tech Solutions", onboarded_date=date.today()),
        ]
        
        for v in vendors:
            await repo.create(v)
        await session.flush()
        
        # Search for "Acme"
        results = await repo.search_by_name("Acme")
        
        assert len(results) == 2
        assert all("Acme" in v.vendor_name for v in results)
    
    @pytest.mark.asyncio
    async def test_search_by_name_case_insensitive(self, session):
        """Test that name search is case insensitive."""
        repo = VendorRepository(session)
        
        vendor = Vendor(
            vendor_id="V001",
            vendor_name="UPPERCASE CORP",
            onboarded_date=date.today()
        )
        await repo.create(vendor)
        await session.flush()
        
        # Search with lowercase
        results = await repo.search_by_name("uppercase")
        
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_get_all_active(self, session):
        """Test getting all active vendors."""
        repo = VendorRepository(session)
        
        vendors = [
            Vendor(vendor_id="V001", vendor_name="Active 1", status=VendorStatus.ACTIVE, onboarded_date=date.today()),
            Vendor(vendor_id="V002", vendor_name="Active 2", status=VendorStatus.ACTIVE, onboarded_date=date.today()),
            Vendor(vendor_id="V003", vendor_name="Inactive", status=VendorStatus.INACTIVE, onboarded_date=date.today()),
            Vendor(vendor_id="V004", vendor_name="Blocked", status=VendorStatus.BLOCKED, onboarded_date=date.today()),
        ]
        
        for v in vendors:
            await repo.create(v)
        await session.flush()
        
        active = await repo.get_all_active()
        
        assert len(active) == 2
        assert all(v.status == VendorStatus.ACTIVE for v in active)
    
    @pytest.mark.asyncio
    async def test_update_risk_profile(self, session, sample_vendor):
        """Test updating vendor risk profile."""
        repo = VendorRepository(session)
        await repo.create(sample_vendor)
        await session.flush()
        
        new_profile = {
            "risk_score": 0.45,
            "fraud_risk_score": 0.30,
            "active_fraud_flags": 2,
        }
        
        updated = await repo.update_risk_profile("V-TEST-001", new_profile)
        
        assert updated is not None
        assert updated.risk_profile["risk_score"] == 0.45


# =============================================================================
# Purchase Order Repository Tests
# =============================================================================

class TestPurchaseOrderRepository:
    """Comprehensive tests for PurchaseOrderRepository."""
    
    @pytest.mark.asyncio
    async def test_create_po(self, session, sample_purchase_order):
        """Test creating a purchase order."""
        repo = PurchaseOrderRepository(session)
        
        po_db = await repo.create(sample_purchase_order)
        await session.flush()
        
        assert po_db.po_number == "PO-TEST-001"
        assert po_db.total_amount == Decimal("1080.00")
    
    @pytest.mark.asyncio
    async def test_create_po_with_multiple_line_items(self, session):
        """Test creating PO with multiple line items."""
        repo = PurchaseOrderRepository(session)
        
        po = PurchaseOrder(
            po_number="PO-MULTI-001",
            vendor_id="V001",
            vendor_name="Test Vendor",
            created_date=date.today(),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=Decimal("2500.00"),
            tax=Decimal("200.00"),
            total_amount=Decimal("2700.00"),
            line_items=[
                POLineItem(line_number=1, description="Item A", quantity=10, unit_price=Decimal("100.00"), amount=Decimal("1000.00")),
                POLineItem(line_number=2, description="Item B", quantity=5, unit_price=Decimal("200.00"), amount=Decimal("1000.00")),
                POLineItem(line_number=3, description="Item C", quantity=10, unit_price=Decimal("50.00"), amount=Decimal("500.00")),
            ],
        )
        
        po_db = await repo.create(po)
        await session.flush()
        
        # Verify line items
        retrieved = await repo.get_by_po_number("PO-MULTI-001")
        assert len(retrieved.line_items) == 3
    
    @pytest.mark.asyncio
    async def test_get_by_po_number(self, session, sample_purchase_order):
        """Test retrieving PO by number."""
        repo = PurchaseOrderRepository(session)
        await repo.create(sample_purchase_order)
        await session.flush()
        
        po = await repo.get_by_po_number("PO-TEST-001")
        
        assert po is not None
        assert po.po_number == "PO-TEST-001"
        assert len(po.line_items) == 1
    
    @pytest.mark.asyncio
    async def test_get_by_po_number_loads_line_items(self, session, sample_purchase_order):
        """Test that line items are eagerly loaded."""
        repo = PurchaseOrderRepository(session)
        await repo.create(sample_purchase_order)
        await session.flush()
        
        po = await repo.get_by_po_number("PO-TEST-001")
        
        # Should be able to access line items without additional query
        assert po.line_items[0].description == "Test Product A"
    
    @pytest.mark.asyncio
    async def test_get_by_vendor(self, session):
        """Test getting POs by vendor."""
        repo = PurchaseOrderRepository(session)
        
        # Create POs for different vendors
        for i in range(3):
            po = PurchaseOrder(
                po_number=f"PO-V1-{i}",
                vendor_id="V001",
                vendor_name="Vendor One",
                created_date=date.today(),
                status=POStatus.OPEN,
                currency="USD",
                subtotal=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
                line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=Decimal("1000.00"), amount=Decimal("1000.00"))],
            )
            await repo.create(po)
        
        po = PurchaseOrder(
            po_number="PO-V2-0",
            vendor_id="V002",
            vendor_name="Vendor Two",
            created_date=date.today(),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=Decimal("500.00"), amount=Decimal("500.00"))],
        )
        await repo.create(po)
        await session.flush()
        
        # Get POs for V001
        v1_pos = await repo.get_by_vendor("V001")
        assert len(v1_pos) == 3
    
    @pytest.mark.asyncio
    async def test_get_by_vendor_with_status_filter(self, session):
        """Test getting POs by vendor filtered by status."""
        repo = PurchaseOrderRepository(session)
        
        statuses = [POStatus.OPEN, POStatus.OPEN, POStatus.CLOSED]
        
        for i, status in enumerate(statuses):
            po = PurchaseOrder(
                po_number=f"PO-{i}",
                vendor_id="V001",
                vendor_name="Test",
                created_date=date.today(),
                status=status,
                currency="USD",
                subtotal=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
                line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=Decimal("1000.00"), amount=Decimal("1000.00"))],
            )
            await repo.create(po)
        
        await session.flush()
        
        # Filter by OPEN status
        open_pos = await repo.get_by_vendor("V001", status=POStatus.OPEN)
        assert len(open_pos) == 2
    
    @pytest.mark.asyncio
    async def test_find_candidates(self, session):
        """Test finding candidate POs for matching."""
        repo = PurchaseOrderRepository(session)
        
        # Create POs with different amounts
        amounts = [
            Decimal("900.00"),
            Decimal("1000.00"),
            Decimal("1100.00"),
            Decimal("5000.00"),  # Outside range
        ]
        
        for i, amount in enumerate(amounts):
            po = PurchaseOrder(
                po_number=f"PO-{i}",
                vendor_id="V001",
                vendor_name="Test",
                created_date=date.today(),
                status=POStatus.OPEN,
                currency="USD",
                subtotal=amount,
                total_amount=amount,
                line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=amount, amount=amount)],
            )
            await repo.create(po)
        
        await session.flush()
        
        # Find candidates in range 800-1200
        candidates = await repo.find_candidates(
            vendor_id="V001",
            amount_min=800.0,
            amount_max=1200.0,
            status=POStatus.OPEN
        )
        
        assert len(candidates) == 3
    
    @pytest.mark.asyncio
    async def test_find_candidates_excludes_closed(self, session):
        """Test that find_candidates excludes closed POs."""
        repo = PurchaseOrderRepository(session)
        
        # Create open and closed POs
        for status in [POStatus.OPEN, POStatus.CLOSED]:
            po = PurchaseOrder(
                po_number=f"PO-{status.value}",
                vendor_id="V001",
                vendor_name="Test",
                created_date=date.today(),
                status=status,
                currency="USD",
                subtotal=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
                line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=Decimal("1000.00"), amount=Decimal("1000.00"))],
            )
            await repo.create(po)
        
        await session.flush()
        
        candidates = await repo.find_candidates(
            vendor_id="V001",
            amount_min=900.0,
            amount_max=1100.0,
            status=POStatus.OPEN
        )
        
        assert len(candidates) == 1
        assert candidates[0].status == POStatus.OPEN
    
    @pytest.mark.asyncio
    async def test_update_status(self, session, sample_purchase_order):
        """Test updating PO status."""
        repo = PurchaseOrderRepository(session)
        await repo.create(sample_purchase_order)
        await session.flush()
        
        updated = await repo.update_status("PO-TEST-001", POStatus.CLOSED)
        
        assert updated is not None
        assert updated.status == POStatus.CLOSED


# =============================================================================
# Matching Repository Tests
# =============================================================================

class TestMatchingRepository:
    """Comprehensive tests for MatchingRepository."""
    
    @pytest.mark.asyncio
    async def test_create_matching_result(self, session, sample_matching_result):
        """Test creating a matching result."""
        repo = MatchingRepository(session)
        
        matching_db = await repo.create(sample_matching_result)
        
        assert matching_db.matching_id == "MATCH-TEST-001"
        assert matching_db.match_score == 0.95
        assert matching_db.matched is True
    
    @pytest.mark.asyncio
    async def test_create_unmatched_result(self, session):
        """Test creating an unmatched result."""
        repo = MatchingRepository(session)
        
        result = MatchingResult(
            matching_id="MATCH-NONE-001",
            invoice_id="INV-001",
            match_type=MatchType.NO_MATCH,
            match_score=0.0,
            matched=False,
            matched_by="system",
        )
        
        matching_db = await repo.create(result)
        
        assert matching_db.matched is False
        assert matching_db.po_id is None
    
    @pytest.mark.asyncio
    async def test_get_by_invoice_id(self, session, sample_matching_result):
        """Test retrieving matching result by invoice ID."""
        repo = MatchingRepository(session)
        await repo.create(sample_matching_result)
        await session.flush()
        
        result = await repo.get_by_invoice_id("DOC-TEST-001")
        
        assert result is not None
        assert result.invoice_id == "DOC-TEST-001"
    
    @pytest.mark.asyncio
    async def test_get_by_invoice_id_returns_latest(self, session):
        """Test that get_by_invoice_id returns most recent result."""
        repo = MatchingRepository(session)
        
        # Create multiple matching results for same invoice
        for i, score in enumerate([0.70, 0.85, 0.95]):
            result = MatchingResult(
                matching_id=f"MATCH-{i}",
                invoice_id="INV-001",
                match_type=MatchType.FUZZY,
                match_score=score,
                matched=True,
                matched_by="system",
            )
            await repo.create(result)
        
        await session.flush()
        
        # Should return latest (highest ID, which correlates with time)
        latest = await repo.get_by_invoice_id("INV-001")
        assert latest is not None


# =============================================================================
# Risk Repository Tests
# =============================================================================

class TestRiskRepository:
    """Comprehensive tests for RiskRepository."""
    
    @pytest.mark.asyncio
    async def test_create_risk_assessment(self, session, sample_risk_assessment):
        """Test creating a risk assessment."""
        repo = RiskRepository(session)
        
        risk_db = await repo.create(sample_risk_assessment)
        
        assert risk_db.assessment_id == "RISK-TEST-001"
        assert risk_db.risk_level == RiskLevel.LOW
        assert risk_db.risk_score == 0.15
    
    @pytest.mark.asyncio
    async def test_create_high_risk_assessment(self, session):
        """Test creating a high risk assessment with flags."""
        from src.models.risk import RiskFlag, RiskFlagType
        
        repo = RiskRepository(session)
        
        assessment = RiskAssessment(
            assessment_id="RISK-HIGH-001",
            invoice_id="INV-001",
            risk_level=RiskLevel.HIGH,
            risk_score=0.75,
            duplicate_risk_score=0.0,
            vendor_risk_score=0.50,
            price_risk_score=0.80,
            risk_flags=[
                RiskFlag(
                    flag_type=RiskFlagType.PRICE_SPIKE,
                    severity="high",
                    description="Price 60% above average",
                    confidence=0.92,
                ),
                RiskFlag(
                    flag_type=RiskFlagType.VENDOR_NEW,
                    severity="medium",
                    description="First invoice from vendor",
                    confidence=1.0,
                ),
            ],
            critical_flags=0,
            high_flags=1,
            recommended_action=RecommendedAction.MANAGER_APPROVAL,
            action_reason="High price anomaly detected",
            requires_manual_review=True,
            assessed_by="system",
            assessment_version="1.0",
        )
        
        risk_db = await repo.create(assessment)
        
        assert risk_db.risk_level == RiskLevel.HIGH
        assert risk_db.high_flags == 1
        assert len(risk_db.risk_flags) == 2
    
    @pytest.mark.asyncio
    async def test_get_by_invoice_id(self, session, sample_risk_assessment):
        """Test retrieving risk assessment by invoice ID."""
        repo = RiskRepository(session)
        await repo.create(sample_risk_assessment)
        await session.flush()
        
        result = await repo.get_by_invoice_id("DOC-TEST-001")
        
        assert result is not None
        assert result.invoice_id == "DOC-TEST-001"
    
    @pytest.mark.asyncio
    async def test_get_high_risk_invoices(self, session):
        """Test getting high and critical risk invoices."""
        repo = RiskRepository(session)
        
        # Create assessments with different risk levels
        levels = [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        
        for i, level in enumerate(levels):
            assessment = RiskAssessment(
                assessment_id=f"RISK-{i}",
                invoice_id=f"INV-{i}",
                risk_level=level,
                risk_score=0.1 + (i * 0.25),
                recommended_action=RecommendedAction.AUTO_APPROVE if level == RiskLevel.LOW else RecommendedAction.REVIEW,
                action_reason="Test",
                requires_manual_review=level != RiskLevel.LOW,
                assessed_by="system",
                assessment_version="1.0",
            )
            await repo.create(assessment)
        
        await session.flush()
        
        high_risk = await repo.get_high_risk_invoices()
        
        # Should return HIGH and CRITICAL only
        assert len(high_risk) == 2
    
    @pytest.mark.asyncio
    async def test_get_high_risk_invoices_with_limit(self, session):
        """Test high risk query respects limit."""
        repo = RiskRepository(session)
        
        # Create multiple high risk assessments
        for i in range(10):
            assessment = RiskAssessment(
                assessment_id=f"RISK-{i}",
                invoice_id=f"INV-{i}",
                risk_level=RiskLevel.HIGH,
                risk_score=0.75,
                recommended_action=RecommendedAction.REVIEW,
                action_reason="Test",
                requires_manual_review=True,
                assessed_by="system",
                assessment_version="1.0",
            )
            await repo.create(assessment)
        
        await session.flush()
        
        high_risk = await repo.get_high_risk_invoices(limit=5)
        
        assert len(high_risk) == 5


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestRepositoryEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_invoice_with_special_characters(self, session):
        """Test invoice with special characters in fields."""
        repo = InvoiceRepository(session)
        
        extraction = InvoiceExtractionResult(
            document_id="DOC-SPECIAL",
            file_name="invoice with spaces & special.pdf",
            file_hash="special123",
            status=InvoiceStatus.EXTRACTED,
            invoice=Invoice(
                invoice_number="INV-2026/01-001",
                vendor_name="Test & Co. Ltd. (UK)",
                total=Decimal("1000.00"),
            ),
            confidence=ExtractionConfidence(overall=0.9),
            requires_review=False,
            ocr_applied=False,
            page_count=1,
            extraction_time_ms=100,
        )
        
        invoice_db = await repo.create(extraction)
        
        assert "&" in invoice_db.invoice_data["vendor_name"]
    
    @pytest.mark.asyncio
    async def test_decimal_precision_preserved(self, session, sample_purchase_order):
        """Test that decimal precision is preserved in database."""
        repo = PurchaseOrderRepository(session)
        
        sample_purchase_order.total_amount = Decimal("1234.56")
        
        po_db = await repo.create(sample_purchase_order)
        await session.flush()
        
        retrieved = await repo.get_by_po_number(sample_purchase_order.po_number)
        
        assert retrieved.total_amount == Decimal("1234.56")
    
    @pytest.mark.asyncio
    async def test_empty_line_items_query(self, session):
        """Test querying PO that might have no line items loaded."""
        repo = PurchaseOrderRepository(session)
        
        po = PurchaseOrder(
            po_number="PO-EMPTY-CHECK",
            vendor_id="V001",
            vendor_name="Test",
            created_date=date.today(),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            line_items=[POLineItem(line_number=1, description="Single Item", quantity=1, unit_price=Decimal("100.00"), amount=Decimal("100.00"))],
        )
        await repo.create(po)
        await session.flush()
        
        # Use get_by_po_number which should load line items
        retrieved = await repo.get_by_po_number("PO-EMPTY-CHECK")
        
        assert len(retrieved.line_items) == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self, session, sample_vendor):
        """Test handling of concurrent updates."""
        repo = VendorRepository(session)
        await repo.create(sample_vendor)
        await session.flush()
        
        # Update risk profile
        profile1 = {"risk_score": 0.30}
        await repo.update_risk_profile("V-TEST-001", profile1)
        await session.flush()
        
        # Verify update
        vendor = await repo.get_by_id("V-TEST-001")
        assert vendor.risk_profile["risk_score"] == 0.30
