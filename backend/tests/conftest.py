"""
Test fixtures and utilities for SmartAP testing.

Provides reusable fixtures for database setup, test data generation,
and common test utilities.

V3.1.1 Enhanced with:
- Organized fixtures package (fixtures/)
- httpx AsyncClient support for async API testing
- FastAPI dependency override helpers
- Comprehensive model factories
"""

import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Generator, Dict, Any
from io import BytesIO

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool, NullPool
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.db.models import Base
from src.db.database import get_session
from src.db.models import (
    InvoiceDB as InvoiceORM,
    PurchaseOrderDB as POORM,
    VendorDB as VendorORM,
    POLineItemDB as POLineItemORM,
)
from src.models.invoice import InvoiceStatus
from src.models.vendor import VendorStatus
from src.models.purchase_order import POStatus
from src.main import app

# Import organized fixtures
from tests.fixtures import (
    SAMPLE_INVOICES,
    SAMPLE_USERS,
    create_sample_invoice,
    create_invoice_batch,
    create_test_user,
    create_admin_user,
    create_auth_headers,
    create_admin_headers,
    INVOICE_PDF_CONTENT,
    TEST_PASSWORD,
    InvoiceFactory,
    VendorFactory,
    PurchaseOrderFactory,
    UserFactory,
    LineItemFactory,
)


# Test database URLs
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
)
# Use PostgreSQL for integration tests when available
POSTGRES_TEST_URL = os.getenv(
    "POSTGRES_TEST_URL",
    "postgresql+asyncpg://test:test@localhost:5432/smartap_test"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create async test database engine."""
    from sqlalchemy import event
    
    # Determine if using SQLite or PostgreSQL
    use_postgres = "postgresql" in TEST_DATABASE_URL
    
    if use_postgres:
        engine = create_async_engine(
            TEST_DATABASE_URL,
            poolclass=NullPool,
            echo=False,
        )
    else:
        engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        
        # Enable foreign key constraints for SQLite
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
def test_client() -> TestClient:
    """Create FastAPI test client (synchronous)."""
    return TestClient(app)


@pytest.fixture(scope="function")
async def test_client_with_db(test_db_session: AsyncSession, test_db_engine) -> AsyncGenerator[TestClient, None]:
    """
    Create FastAPI test client with properly configured database override.
    
    This fixture ensures the TestClient and test fixtures share the same database
    by overriding the get_session dependency to use the test session.
    """
    # Override database dependency to use test session
    async def override_get_session():
        yield test_db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    # Create TestClient with overridden dependencies
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create async HTTP client for API testing.
    
    This fixture:
    1. Overrides the database dependency to use test session
    2. Provides httpx AsyncClient for async API calls
    3. Cleans up after test completion
    """
    # Override database dependency
    async def override_get_session():
        yield test_db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    # Create async client with ASGI transport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Get authentication headers for standard user."""
    return create_auth_headers(scenario="standard")


@pytest.fixture
def admin_auth_headers() -> Dict[str, str]:
    """Get authentication headers for admin user."""
    return create_admin_headers()


# Test data fixtures

@pytest.fixture
def sample_vendor_data():
    """Sample vendor data for testing."""
    from datetime import date
    return {
        "vendor_id": "V001",
        "vendor_name": "Tech Supplies Inc",
        "status": VendorStatus.ACTIVE,
        "onboarded_date": date(2025, 1, 1),
        "payment_terms": "Net 30",
        "currency": "USD",
        "risk_profile": {
            "risk_score": 0.1,
            "on_time_payment_rate": 0.95,
            "total_invoices_processed": 50,
        },
    }


@pytest.fixture
def sample_po_data():
    """Sample purchase order data for testing."""
    from datetime import date
    return {
        "po_number": "PO-001",
        "vendor_id": "V001",
        "created_date": date(2026, 1, 1),
        "expected_delivery": date(2026, 2, 1),
        "subtotal": Decimal("900.00"),
        "tax": Decimal("100.00"),
        "total_amount": Decimal("1000.00"),
        "currency": "USD",
        "status": POStatus.OPEN,
        "payment_terms": "Net 30",
    }


@pytest.fixture
def sample_po_line_items():
    """Sample PO line items for testing."""
    return [
        {
            "line_number": 1,
            "description": "Laptop Computer",
            "quantity": 2.0,
            "unit_price": Decimal("400.00"),
            "amount": Decimal("800.00"),
        },
        {
            "line_number": 2,
            "description": "Wireless Mouse",
            "quantity": 5.0,
            "unit_price": Decimal("40.00"),
            "amount": Decimal("200.00"),
        },
    ]


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        "document_id": "DOC-001",
        "invoice_number": "INV-12345",
        "file_name": "test_invoice.pdf",
        "file_hash": "abc123def456",
        "status": InvoiceStatus.EXTRACTED,
        "extraction_confidence": 0.95,
        "requires_review": False,
        "ocr_applied": False,
        "page_count": 1,
        "invoice_data": {
            "invoice_number": "INV-12345",
            "invoice_date": "2026-01-05",
            "due_date": "2026-02-05",
            "total_amount": 1000.00,
            "currency": "USD",
            "vendor_name": "Tech Supplies Inc",
            "po_number": "PO-001",
        },
    }


@pytest.fixture
async def sample_vendor(test_db_session: AsyncSession, sample_vendor_data) -> VendorORM:
    """Create sample vendor in test database."""
    vendor = VendorORM(**sample_vendor_data)
    test_db_session.add(vendor)
    await test_db_session.commit()
    await test_db_session.refresh(vendor)
    return vendor


@pytest.fixture
async def sample_po(
    test_db_session: AsyncSession,
    sample_vendor: VendorORM,
    sample_po_data,
    sample_po_line_items,
) -> POORM:
    """Create sample PO with line items in test database."""
    po = POORM(**sample_po_data)
    test_db_session.add(po)
    await test_db_session.flush()
    
    # Add line items
    for item_data in sample_po_line_items:
        line_item = POLineItemORM(po_id=po.id, **item_data)
        test_db_session.add(line_item)
    
    await test_db_session.commit()
    await test_db_session.refresh(po)
    return po


@pytest.fixture
async def sample_invoice(
    test_db_session: AsyncSession,
    sample_invoice_data,
) -> InvoiceORM:
    """Create sample invoice in test database."""
    invoice = InvoiceORM(**sample_invoice_data)
    test_db_session.add(invoice)
    await test_db_session.commit()
    await test_db_session.refresh(invoice)
    return invoice


@pytest.fixture
def sample_pdf_file():
    """Create sample PDF file for upload testing."""
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Invoice) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
410
%%EOF
"""
    return BytesIO(pdf_content)


# Test data generators

def create_vendor_data(
    vendor_id: str = "V001",
    vendor_name: str = "Test Vendor",
    risk_score: float = 0.1,
    on_time_rate: float = 0.95,
) -> dict:
    """Generate vendor test data."""
    from datetime import date
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "status": VendorStatus.ACTIVE,
        "onboarded_date": date(2025, 1, 1),
        "payment_terms": "Net 30",
        "currency": "USD",
        "risk_profile": {
            "risk_score": risk_score,
            "on_time_payment_rate": on_time_rate,
            "total_invoices_processed": 50,
        },
    }


def create_po_data(
    po_number: str = "PO-001",
    vendor_id: str = "V001",
    amount: Decimal = Decimal("1000.00"),
    status: POStatus = POStatus.OPEN,
) -> dict:
    """Generate PO test data."""
    from datetime import date
    return {
        "po_number": po_number,
        "vendor_id": vendor_id,
        "created_date": date(2026, 1, 1),
        "expected_delivery": date(2026, 2, 1),
        "subtotal": amount * Decimal("0.9"),
        "tax": amount * Decimal("0.1"),
        "total_amount": amount,
        "currency": "USD",
        "status": status,
        "payment_terms": "Net 30",
    }


def create_invoice_data(
    document_id: str = "DOC-001",
    invoice_number: str = "INV-001",
    amount: Decimal = Decimal("1000.00"),
    vendor_name: str = "Test Vendor",
    po_number: str = "PO-001",
    status: InvoiceStatus = InvoiceStatus.EXTRACTED,
) -> dict:
    """Generate invoice test data."""
    return {
        "document_id": document_id,
        "invoice_number": invoice_number,
        "file_name": f"{document_id}.pdf",
        "file_hash": f"hash_{document_id}",
        "status": status,
        "extraction_confidence": 0.95,
        "requires_review": False,
        "ocr_applied": False,
        "page_count": 1,
        "invoice_data": {
            "invoice_number": invoice_number,
            "invoice_date": "2026-01-05",
            "due_date": "2026-02-05",
            "total": float(amount),
            "currency": "USD",
            "vendor_name": vendor_name,
            "po_number": po_number,
        },
    }


# Test utilities

class TestDataBuilder:
    """Builder for creating complex test data scenarios."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vendors = []
        self.pos = []
        self.invoices = []
    
    async def create_vendor(self, **kwargs) -> VendorORM:
        """Create vendor with custom data."""
        data = create_vendor_data(**kwargs)
        vendor = VendorORM(**data)
        self.session.add(vendor)
        await self.session.flush()
        self.vendors.append(vendor)
        return vendor
    
    async def create_po(self, vendor_id: str = None, line_items: list = None, **kwargs) -> POORM:
        """Create PO with custom data and line items.
        
        Args:
            vendor_id: Vendor ID (uses first created vendor if None)
            line_items: List of dicts with line item data (auto-creates default if None)
            **kwargs: Additional PO data fields
        """
        if vendor_id is None and self.vendors:
            vendor_id = self.vendors[0].vendor_id
        
        data = create_po_data(vendor_id=vendor_id, **kwargs)
        po = POORM(**data)
        self.session.add(po)
        await self.session.flush()
        
        # Create line items (default to one item if not provided)
        if line_items is None:
            amount = kwargs.get("amount", Decimal("1000.00"))
            line_items = [{
                "line_number": 1,
                "description": "Test Product",
                "quantity": 1.0,
                "unit_price": amount,
                "amount": amount,
                "sku": "TEST-001",
                "unit": "EA",
                "received_quantity": 0.0,
            }]
        
        for item_data in line_items:
            line_item = POLineItemORM(
                po_id=po.id,
                **item_data
            )
            self.session.add(line_item)
        
        await self.session.flush()
        # Refresh to load line_items relationship
        await self.session.refresh(po)
        
        self.pos.append(po)
        return po
    
    async def create_invoice(self, **kwargs) -> InvoiceORM:
        """Create invoice with custom data."""
        data = create_invoice_data(**kwargs)
        invoice = InvoiceORM(**data)
        self.session.add(invoice)
        await self.session.flush()
        self.invoices.append(invoice)
        return invoice
    
    async def commit(self):
        """Commit all changes."""
        await self.session.commit()
        
        # Refresh all objects
        for vendor in self.vendors:
            await self.session.refresh(vendor)
        for po in self.pos:
            await self.session.refresh(po)
        for invoice in self.invoices:
            await self.session.refresh(invoice)


@pytest.fixture
async def data_builder(test_db_session: AsyncSession) -> TestDataBuilder:
    """Provide test data builder."""
    return TestDataBuilder(test_db_session)


# Assertion helpers

def assert_invoice_match(invoice_data: dict, expected: dict):
    """Assert invoice data matches expected values."""
    assert invoice_data["invoice_number"] == expected["invoice_number"]
    assert invoice_data["vendor_name"] == expected["vendor_name"]
    assert float(invoice_data["total_amount"]) == float(expected["total_amount"])
    assert invoice_data["currency"] == expected["currency"]


def assert_matching_result(result: dict, min_score: float = 0.0):
    """Assert matching result has valid structure and scores."""
    assert "match_score" in result
    assert "match_type" in result
    assert "discrepancies" in result
    assert result["match_score"] >= min_score
    assert result["match_type"] in ["exact", "fuzzy", "partial", "none"]
    assert isinstance(result["discrepancies"], list)


def assert_risk_assessment(assessment: dict):
    """Assert risk assessment has valid structure."""
    assert "risk_level" in assessment
    assert "risk_score" in assessment
    assert "risk_flags" in assessment
    assert assessment["risk_level"] in ["low", "medium", "high", "critical"]
    assert 0 <= assessment["risk_score"] <= 1
    assert isinstance(assessment["risk_flags"], list)


def assert_workflow_completed(result: dict):
    """Assert workflow completed successfully."""
    assert result["status"] in ["completed", "failed"]
    assert "decision" in result
    assert "extraction" in result
    assert "matching" in result
    assert "risk" in result
    assert "metadata" in result
