"""
Unit Tests for SmartAP Data Repositories

Tests async repository operations for all entities.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.db.database import Base
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
)


@pytest.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_invoice_repository_create(session):
    """Test creating an invoice."""
    repo = InvoiceRepository(session)
    
    extraction = InvoiceExtractionResult(
        document_id="DOC001",
        file_name="test_invoice.pdf",
        file_hash="abc123",
        status=InvoiceStatus.EXTRACTED,
        invoice=Invoice(
            invoice_number="INV-001",
            vendor_name="Test Vendor",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            line_items=[
                InvoiceLineItem(
                    line_number=1,
                    description="Test Item",
                    quantity=10,
                    unit_price=100.00,
                    amount=1000.00,
                )
            ],
        ),
        confidence=ExtractionConfidence(overall=0.95),
        requires_review=False,
        ocr_applied=False,
        page_count=1,
        extraction_time_ms=500,
    )
    
    invoice_db = await repo.create(extraction)
    
    assert invoice_db.document_id == "DOC001"
    assert invoice_db.invoice_number == "INV-001"
    assert invoice_db.status == InvoiceStatus.EXTRACTED
    assert invoice_db.extraction_confidence == 0.95


@pytest.mark.asyncio
async def test_invoice_repository_get_by_hash(session):
    """Test finding duplicate invoices by hash."""
    repo = InvoiceRepository(session)
    
    extraction = InvoiceExtractionResult(
        document_id="DOC002",
        file_name="invoice.pdf",
        file_hash="hash123",
        status=InvoiceStatus.EXTRACTED,
        confidence=ExtractionConfidence(overall=0.90),
        requires_review=False,
        ocr_applied=False,
        page_count=1,
        extraction_time_ms=400,
    )
    
    await repo.create(extraction)
    await session.flush()
    
    # Search by hash
    duplicate = await repo.get_by_hash("hash123")
    
    assert duplicate is not None
    assert duplicate.file_hash == "hash123"
    assert duplicate.document_id == "DOC002"


@pytest.mark.asyncio
async def test_vendor_repository_create(session):
    """Test creating a vendor."""
    repo = VendorRepository(session)
    
    vendor = Vendor(
        vendor_id="V001",
        vendor_name="Test Vendor Inc.",
        email="test@vendor.com",
        status=VendorStatus.ACTIVE,
        payment_terms="Net 30",
        currency="USD",
        risk_profile=VendorRiskProfile(
            risk_score=0.15,
            on_time_payment_rate=0.95,
            invoice_count=100,
            avg_invoice_amount=1000.00,
            max_invoice_amount=5000.00,
            has_fraud_history=False,
        ),
        onboarded_date=datetime.now(),
    )
    
    vendor_db = await repo.create(vendor)
    
    assert vendor_db.vendor_id == "V001"
    assert vendor_db.vendor_name == "Test Vendor Inc."
    assert vendor_db.status == VendorStatus.ACTIVE
    assert vendor_db.risk_profile["risk_score"] == 0.15


@pytest.mark.asyncio
async def test_vendor_repository_search_by_name(session):
    """Test searching vendors by name."""
    repo = VendorRepository(session)
    
    # Create test vendors
    vendors = [
        Vendor(
            vendor_id="V001",
            vendor_name="Acme Corporation",
            email="acme@test.com",
            status=VendorStatus.ACTIVE,
            payment_terms="Net 30",
            currency="USD",
            risk_profile=VendorRiskProfile(risk_score=0.1, on_time_payment_rate=0.9, invoice_count=10, avg_invoice_amount=500.0, max_invoice_amount=1000.0, has_fraud_history=False),
            onboarded_date=datetime.now(),
        ),
        Vendor(
            vendor_id="V002",
            vendor_name="Tech Solutions",
            email="tech@test.com",
            status=VendorStatus.ACTIVE,
            payment_terms="Net 45",
            currency="USD",
            risk_profile=VendorRiskProfile(risk_score=0.2, on_time_payment_rate=0.85, invoice_count=5, avg_invoice_amount=1000.0, max_invoice_amount=2000.0, has_fraud_history=False),
            onboarded_date=datetime.now(),
        ),
    ]
    
    for v in vendors:
        await repo.create(v)
    
    await session.flush()
    
    # Search for "Acme"
    results = await repo.search_by_name("Acme")
    
    assert len(results) == 1
    assert results[0].vendor_name == "Acme Corporation"


@pytest.mark.asyncio
async def test_po_repository_create(session):
    """Test creating a purchase order."""
    repo = PurchaseOrderRepository(session)
    
    po = PurchaseOrder(
        po_number="PO-001",
        vendor_id="V001",
        created_date=datetime.now(),
        expected_delivery=datetime.now() + timedelta(days=30),
        status=POStatus.OPEN,
        currency="USD",
        subtotal=1000.00,
        tax=80.00,
        total_amount=1080.00,
        payment_terms="Net 30",
        created_by="test@company.com",
        line_items=[
            POLineItem(
                line_number=1,
                description="Test Product",
                quantity=10,
                unit_price=100.00,
                amount=1000.00,
                sku="TEST-001",
                unit="ea",
            )
        ],
    )
    
    po_db = await repo.create(po)
    await session.flush()
    
    assert po_db.po_number == "PO-001"
    assert po_db.total_amount == 1080.00
    assert len(po_db.line_items) == 1
    assert po_db.line_items[0].description == "Test Product"


@pytest.mark.asyncio
async def test_po_repository_find_candidates(session):
    """Test finding candidate POs for matching."""
    repo = PurchaseOrderRepository(session)
    
    # Create test POs
    pos = [
        PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            created_date=datetime.now(),
            expected_delivery=datetime.now() + timedelta(days=30),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            payment_terms="Net 30",
            created_by="test@company.com",
            line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=1000.00, amount=1000.00)],
        ),
        PurchaseOrder(
            po_number="PO-002",
            vendor_id="V001",
            created_date=datetime.now(),
            expected_delivery=datetime.now() + timedelta(days=30),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=5000.00,
            tax=400.00,
            total_amount=5400.00,
            payment_terms="Net 30",
            created_by="test@company.com",
            line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=5000.00, amount=5000.00)],
        ),
        PurchaseOrder(
            po_number="PO-003",
            vendor_id="V002",  # Different vendor
            created_date=datetime.now(),
            expected_delivery=datetime.now() + timedelta(days=30),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            payment_terms="Net 30",
            created_by="test@company.com",
            line_items=[POLineItem(line_number=1, description="Item", quantity=1, unit_price=1000.00, amount=1000.00)],
        ),
    ]
    
    for po in pos:
        await repo.create(po)
    
    await session.flush()
    
    # Find candidates for V001 with amount ~1080
    candidates = await repo.find_candidates(
        vendor_id="V001",
        amount_min=900.0,
        amount_max=1200.0,
        status=POStatus.OPEN,
    )
    
    assert len(candidates) == 1
    assert candidates[0].po_number == "PO-001"


@pytest.mark.asyncio
async def test_matching_repository_create(session):
    """Test creating a matching result."""
    repo = MatchingRepository(session)
    
    matching = MatchingResult(
        invoice_id="INV001",
        po_number="PO-001",
        matching_id="MATCH001",
        match_type=MatchType.EXACT,
        match_score=0.98,
        matched=True,
        vendor_match_score=1.0,
        amount_match_score=0.99,
        date_match_score=0.95,
        line_items_match_score=0.98,
        discrepancies=[],
        has_discrepancies=False,
        critical_discrepancies=0,
        requires_approval=False,
        matched_by="system",
    )
    
    matching_db = await repo.create(matching)
    
    assert matching_db.invoice_id == "INV001"
    assert matching_db.match_score == 0.98
    assert matching_db.matched is True


@pytest.mark.asyncio
async def test_risk_repository_create(session):
    """Test creating a risk assessment."""
    repo = RiskRepository(session)
    
    risk = RiskAssessment(
        invoice_id="INV001",
        assessment_id="RISK001",
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
        recommended_action="approve",
        action_reason="All checks passed",
        requires_manual_review=False,
        assessed_by="system",
        assessment_version="1.0",
    )
    
    risk_db = await repo.create(risk)
    
    assert risk_db.invoice_id == "INV001"
    assert risk_db.risk_level == RiskLevel.LOW
    assert risk_db.risk_score == 0.15
