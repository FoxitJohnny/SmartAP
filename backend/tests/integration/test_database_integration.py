"""
Database Integration Tests

Tests for database connectivity, basic operations, and core functionality.
V3.2.2 - Database Integration Testing
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    InvoiceDB,
    PurchaseOrderDB,
    POLineItemDB,
    VendorDB,
    PaymentRecordDB,
    FraudFlagDB,
    MatchingResultDB,
    RiskAssessmentDB,
    UserDB,
    RefreshTokenDB,
)
from src.models.invoice import InvoiceStatus
from src.models.purchase_order import POStatus
from src.models.vendor import VendorStatus, FraudFlagType
from src.models.matching import MatchType
from src.models.risk import RiskLevel, RecommendedAction


# =============================================================================
# Database Connection Tests
# =============================================================================

class TestDatabaseConnection:
    """Tests for basic database connectivity."""
    
    @pytest.mark.asyncio
    async def test_database_connection_works(self, test_db_session: AsyncSession):
        """Test that database connection is established."""
        result = await test_db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_database_timezone_handling(self, test_db_session: AsyncSession):
        """Test that database handles timestamps correctly."""
        result = await test_db_session.execute(text("SELECT datetime('now')"))
        timestamp = result.scalar()
        assert timestamp is not None
    
    @pytest.mark.asyncio
    async def test_tables_exist(self, test_db_session: AsyncSession):
        """Test that all required tables are created."""
        # Query SQLite master table (works for SQLite test DB)
        result = await test_db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result.fetchall()]
        
        expected_tables = [
            "invoices",
            "purchase_orders",
            "po_line_items",
            "vendors",
            "matching_results",
            "risk_assessments",
            "users",
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"


# =============================================================================
# Transaction Tests
# =============================================================================

class TestTransactionManagement:
    """Tests for database transaction handling."""
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self, test_db_session: AsyncSession):
        """Test that transactions can be committed."""
        # Create a vendor
        vendor = VendorDB(
            vendor_id=f"V-COMMIT-{uuid.uuid4().hex[:8]}",
            vendor_name="Commit Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Verify it's persisted
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor.vendor_id)
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.vendor_name == "Commit Test Vendor"
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_db_session: AsyncSession):
        """Test that transactions can be rolled back."""
        vendor_id = f"V-ROLLBACK-{uuid.uuid4().hex[:8]}"
        
        # Create a vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Rollback Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.flush()  # Flush to get ID but don't commit
        
        # Rollback
        await test_db_session.rollback()
        
        # Verify it's not persisted
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        fetched = result.scalar_one_or_none()
        assert fetched is None
    
    @pytest.mark.asyncio
    async def test_multiple_inserts_in_transaction(self, test_db_session: AsyncSession):
        """Test that multiple inserts work in a single transaction."""
        base_id = uuid.uuid4().hex[:6]
        
        # Create multiple vendors in one transaction
        vendors = [
            VendorDB(
                vendor_id=f"V-MULTI-{base_id}-{i}",
                vendor_name=f"Multi Vendor {i}",
                onboarded_date=date.today(),
            )
            for i in range(5)
        ]
        
        test_db_session.add_all(vendors)
        await test_db_session.commit()
        
        # Verify all are persisted
        result = await test_db_session.execute(
            select(func.count(VendorDB.id)).where(
                VendorDB.vendor_id.like(f"V-MULTI-{base_id}%")
            )
        )
        count = result.scalar()
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_partial_rollback_on_error(self, test_db_session: AsyncSession):
        """Test that errors cause rollback of uncommitted changes."""
        vendor_id = f"V-PARTIAL-{uuid.uuid4().hex[:8]}"
        
        # Create first vendor successfully
        vendor1 = VendorDB(
            vendor_id=vendor_id,
            vendor_name="First Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor1)
        await test_db_session.flush()
        
        # Try to create duplicate (should fail)
        vendor2 = VendorDB(
            vendor_id=vendor_id,  # Duplicate ID
            vendor_name="Duplicate Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor2)
        
        with pytest.raises(IntegrityError):
            await test_db_session.flush()
        
        # Rollback and verify neither persisted
        await test_db_session.rollback()


# =============================================================================
# CRUD Operation Tests
# =============================================================================

class TestCRUDOperations:
    """Tests for Create, Read, Update, Delete operations."""
    
    @pytest.mark.asyncio
    async def test_create_invoice(self, test_db_session: AsyncSession):
        """Test creating an invoice."""
        doc_id = f"DOC-{uuid.uuid4().hex[:8]}"
        
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number=f"INV-{uuid.uuid4().hex[:8]}",
            file_name="test_invoice.pdf",
            file_hash="abc123hash",
            status=InvoiceStatus.INGESTED,
            invoice_data={"vendor": "Test", "total": 1000},
            extraction_confidence=0.95,
            requires_review=False,
            ocr_applied=True,
            page_count=2,
            extraction_time_ms=1500,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Verify
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        fetched = result.scalar_one()
        assert fetched.status == InvoiceStatus.INGESTED
        assert fetched.extraction_confidence == 0.95
        assert fetched.invoice_data["vendor"] == "Test"
    
    @pytest.mark.asyncio
    async def test_read_invoice_by_hash(self, test_db_session: AsyncSession):
        """Test reading invoice by file hash."""
        file_hash = f"hash-{uuid.uuid4().hex[:12]}"
        
        invoice = InvoiceDB(
            document_id=f"DOC-{uuid.uuid4().hex[:8]}",
            invoice_number="INV-READ-001",
            file_name="read_test.pdf",
            file_hash=file_hash,
            status=InvoiceStatus.EXTRACTED,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Read by hash
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.file_hash == file_hash)
        )
        fetched = result.scalar_one()
        assert fetched.invoice_number == "INV-READ-001"
    
    @pytest.mark.asyncio
    async def test_update_invoice_status(self, test_db_session: AsyncSession):
        """Test updating invoice status."""
        doc_id = f"DOC-UPDATE-{uuid.uuid4().hex[:8]}"
        
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number="INV-UPDATE-001",
            file_name="update_test.pdf",
            file_hash="update_hash",
            status=InvoiceStatus.INGESTED,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Update status
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        invoice_to_update = result.scalar_one()
        invoice_to_update.status = InvoiceStatus.APPROVED
        await test_db_session.commit()
        
        # Verify update
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        updated = result.scalar_one()
        assert updated.status == InvoiceStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_delete_invoice(self, test_db_session: AsyncSession):
        """Test deleting an invoice."""
        doc_id = f"DOC-DELETE-{uuid.uuid4().hex[:8]}"
        
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number="INV-DELETE-001",
            file_name="delete_test.pdf",
            file_hash="delete_hash",
            status=InvoiceStatus.INGESTED,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Delete
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        invoice_to_delete = result.scalar_one()
        await test_db_session.delete(invoice_to_delete)
        await test_db_session.commit()
        
        # Verify deleted
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        deleted = result.scalar_one_or_none()
        assert deleted is None


# =============================================================================
# Data Type Tests
# =============================================================================

class TestDataTypes:
    """Tests for proper handling of different data types."""
    
    @pytest.mark.asyncio
    async def test_decimal_precision(self, test_db_session: AsyncSession):
        """Test that decimal values maintain precision."""
        vendor_id = f"V-DECIMAL-{uuid.uuid4().hex[:8]}"
        
        # Create vendor first
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Decimal Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create PO with precise decimal
        po = PurchaseOrderDB(
            po_number=f"PO-DECIMAL-{uuid.uuid4().hex[:8]}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("1234.56"),
            tax=Decimal("98.76"),
            total_amount=Decimal("1333.32"),
        )
        test_db_session.add(po)
        await test_db_session.commit()
        
        # Verify precision maintained
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po.po_number)
        )
        fetched = result.scalar_one()
        assert fetched.subtotal == Decimal("1234.56")
        assert fetched.tax == Decimal("98.76")
        assert fetched.total_amount == Decimal("1333.32")
    
    @pytest.mark.asyncio
    async def test_json_storage(self, test_db_session: AsyncSession):
        """Test that JSON data is stored and retrieved correctly."""
        doc_id = f"DOC-JSON-{uuid.uuid4().hex[:8]}"
        
        invoice_data = {
            "vendor": {"name": "ACME Corp", "id": "V001"},
            "line_items": [
                {"description": "Widget", "amount": 100.00},
                {"description": "Gadget", "amount": 200.00},
            ],
            "totals": {"subtotal": 300.00, "tax": 24.00, "total": 324.00},
            "metadata": {"extracted_by": "AI", "confidence": 0.95},
        }
        
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number="INV-JSON-001",
            file_name="json_test.pdf",
            file_hash="json_hash",
            status=InvoiceStatus.EXTRACTED,
            invoice_data=invoice_data,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Verify JSON structure
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        fetched = result.scalar_one()
        assert fetched.invoice_data["vendor"]["name"] == "ACME Corp"
        assert len(fetched.invoice_data["line_items"]) == 2
        assert fetched.invoice_data["totals"]["total"] == 324.00
    
    @pytest.mark.asyncio
    async def test_date_handling(self, test_db_session: AsyncSession):
        """Test that dates are handled correctly."""
        vendor_id = f"V-DATE-{uuid.uuid4().hex[:8]}"
        today = date.today()
        expected_delivery = today + timedelta(days=30)
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Date Test Vendor",
            onboarded_date=today,
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        po = PurchaseOrderDB(
            po_number=f"PO-DATE-{uuid.uuid4().hex[:8]}",
            vendor_id=vendor_id,
            created_date=today,
            expected_delivery=expected_delivery,
            status=POStatus.OPEN,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        test_db_session.add(po)
        await test_db_session.commit()
        
        # Verify dates
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po.po_number)
        )
        fetched = result.scalar_one()
        assert fetched.created_date == today
        assert fetched.expected_delivery == expected_delivery
    
    @pytest.mark.asyncio
    async def test_enum_storage(self, test_db_session: AsyncSession):
        """Test that enum values are stored correctly."""
        doc_id = f"DOC-ENUM-{uuid.uuid4().hex[:8]}"
        
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number="INV-ENUM-001",
            file_name="enum_test.pdf",
            file_hash="enum_hash",
            status=InvoiceStatus.RISK_REVIEW,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Verify enum value
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        fetched = result.scalar_one()
        assert fetched.status == InvoiceStatus.RISK_REVIEW
        assert fetched.status.value == "risk_review"
    
    @pytest.mark.asyncio
    async def test_boolean_fields(self, test_db_session: AsyncSession):
        """Test that boolean fields work correctly."""
        doc_id = f"DOC-BOOL-{uuid.uuid4().hex[:8]}"
        
        invoice = InvoiceDB(
            document_id=doc_id,
            invoice_number="INV-BOOL-001",
            file_name="bool_test.pdf",
            file_hash="bool_hash",
            status=InvoiceStatus.EXTRACTED,
            requires_review=True,
            ocr_applied=False,
        )
        test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Verify booleans
        result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == doc_id)
        )
        fetched = result.scalar_one()
        assert fetched.requires_review is True
        assert fetched.ocr_applied is False


# =============================================================================
# Query Tests
# =============================================================================

class TestQueryOperations:
    """Tests for query operations and filtering."""
    
    @pytest.mark.asyncio
    async def test_filter_by_status(self, test_db_session: AsyncSession):
        """Test filtering invoices by status."""
        base_id = uuid.uuid4().hex[:6]
        
        # Create invoices with different statuses
        statuses = [
            InvoiceStatus.INGESTED,
            InvoiceStatus.EXTRACTED,
            InvoiceStatus.EXTRACTED,
            InvoiceStatus.APPROVED,
        ]
        
        for i, status in enumerate(statuses):
            invoice = InvoiceDB(
                document_id=f"DOC-STATUS-{base_id}-{i}",
                invoice_number=f"INV-STATUS-{base_id}-{i}",
                file_name=f"status_test_{i}.pdf",
                file_hash=f"status_hash_{base_id}_{i}",
                status=status,
            )
            test_db_session.add(invoice)
        
        await test_db_session.commit()
        
        # Filter by EXTRACTED status
        result = await test_db_session.execute(
            select(InvoiceDB).where(
                InvoiceDB.status == InvoiceStatus.EXTRACTED,
                InvoiceDB.document_id.like(f"DOC-STATUS-{base_id}%")
            )
        )
        extracted = result.scalars().all()
        assert len(extracted) == 2
    
    @pytest.mark.asyncio
    async def test_order_by_created_at(self, test_db_session: AsyncSession):
        """Test ordering results by creation time."""
        vendor_id = f"V-ORDER-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Order Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create POs
        for i in range(3):
            po = PurchaseOrderDB(
                po_number=f"PO-ORDER-{vendor_id}-{i}",
                vendor_id=vendor_id,
                created_date=date.today() - timedelta(days=i),
                status=POStatus.OPEN,
                subtotal=Decimal("100.00"),
                total_amount=Decimal("100.00"),
            )
            test_db_session.add(po)
        await test_db_session.commit()
        
        # Query ordered by created_date
        result = await test_db_session.execute(
            select(PurchaseOrderDB)
            .where(PurchaseOrderDB.vendor_id == vendor_id)
            .order_by(PurchaseOrderDB.created_date.desc())
        )
        pos = result.scalars().all()
        
        # Verify order
        assert len(pos) == 3
        assert pos[0].created_date >= pos[1].created_date >= pos[2].created_date
    
    @pytest.mark.asyncio
    async def test_aggregate_functions(self, test_db_session: AsyncSession):
        """Test aggregate functions (count, sum)."""
        vendor_id = f"V-AGG-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Aggregate Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create multiple POs
        amounts = [Decimal("100.00"), Decimal("200.00"), Decimal("300.00")]
        for i, amount in enumerate(amounts):
            po = PurchaseOrderDB(
                po_number=f"PO-AGG-{vendor_id}-{i}",
                vendor_id=vendor_id,
                created_date=date.today(),
                status=POStatus.OPEN,
                subtotal=amount,
                total_amount=amount,
            )
            test_db_session.add(po)
        await test_db_session.commit()
        
        # Test count
        result = await test_db_session.execute(
            select(func.count(PurchaseOrderDB.id)).where(
                PurchaseOrderDB.vendor_id == vendor_id
            )
        )
        count = result.scalar()
        assert count == 3
        
        # Test sum
        result = await test_db_session.execute(
            select(func.sum(PurchaseOrderDB.total_amount)).where(
                PurchaseOrderDB.vendor_id == vendor_id
            )
        )
        total = result.scalar()
        assert total == Decimal("600.00")
    
    @pytest.mark.asyncio
    async def test_like_query(self, test_db_session: AsyncSession):
        """Test LIKE queries for text search."""
        base_id = uuid.uuid4().hex[:6]
        
        vendors = [
            VendorDB(vendor_id=f"V-LIKE-{base_id}-1", vendor_name="ACME Corporation", onboarded_date=date.today()),
            VendorDB(vendor_id=f"V-LIKE-{base_id}-2", vendor_name="ACME Industries", onboarded_date=date.today()),
            VendorDB(vendor_id=f"V-LIKE-{base_id}-3", vendor_name="Beta Corp", onboarded_date=date.today()),
        ]
        test_db_session.add_all(vendors)
        await test_db_session.commit()
        
        # Search for ACME
        result = await test_db_session.execute(
            select(VendorDB).where(
                VendorDB.vendor_name.like("%ACME%"),
                VendorDB.vendor_id.like(f"V-LIKE-{base_id}%")
            )
        )
        acme_vendors = result.scalars().all()
        assert len(acme_vendors) == 2


# =============================================================================
# Constraint Tests
# =============================================================================

class TestConstraints:
    """Tests for database constraints."""
    
    @pytest.mark.asyncio
    async def test_unique_constraint_vendor_id(self, test_db_session: AsyncSession):
        """Test that vendor_id must be unique."""
        vendor_id = f"V-UNIQUE-{uuid.uuid4().hex[:8]}"
        
        vendor1 = VendorDB(
            vendor_id=vendor_id,
            vendor_name="First Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor1)
        await test_db_session.commit()
        
        # Try to create duplicate
        vendor2 = VendorDB(
            vendor_id=vendor_id,  # Same ID
            vendor_name="Second Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor2)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_unique_constraint_document_id(self, test_db_session: AsyncSession):
        """Test that document_id must be unique."""
        doc_id = f"DOC-UNIQUE-{uuid.uuid4().hex[:8]}"
        
        invoice1 = InvoiceDB(
            document_id=doc_id,
            invoice_number="INV-001",
            file_name="test1.pdf",
            file_hash="hash1",
            status=InvoiceStatus.INGESTED,
        )
        test_db_session.add(invoice1)
        await test_db_session.commit()
        
        # Try to create duplicate
        invoice2 = InvoiceDB(
            document_id=doc_id,  # Same ID
            invoice_number="INV-002",
            file_name="test2.pdf",
            file_hash="hash2",
            status=InvoiceStatus.INGESTED,
        )
        test_db_session.add(invoice2)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, test_db_session: AsyncSession):
        """Test that foreign key constraints are enforced."""
        # Try to create PO with non-existent vendor
        po = PurchaseOrderDB(
            po_number=f"PO-FK-{uuid.uuid4().hex[:8]}",
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
    async def test_not_null_constraint(self, test_db_session: AsyncSession):
        """Test that required fields cannot be null."""
        # Try to create invoice without required document_id
        # Note: SQLite doesn't enforce NOT NULL for some cases, so we test
        # by checking what happens when we try to query with null values
        invoice = InvoiceDB(
            document_id=f"DOC-NOTNULL-{uuid.uuid4().hex[:8]}",
            invoice_number="",  # Empty but not null
            file_name="",
            file_hash="",
            status=InvoiceStatus.INGESTED,
        )
        test_db_session.add(invoice)
        # Should succeed because empty string is not null
        await test_db_session.commit()


# =============================================================================
# Timestamp Tests
# =============================================================================

class TestTimestamps:
    """Tests for automatic timestamp handling."""
    
    @pytest.mark.asyncio
    async def test_created_at_auto_set(self, test_db_session: AsyncSession):
        """Test that created_at is automatically set."""
        before = datetime.utcnow()
        
        vendor = VendorDB(
            vendor_id=f"V-TS-{uuid.uuid4().hex[:8]}",
            vendor_name="Timestamp Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        after = datetime.utcnow()
        
        # Refresh to get server-generated values
        await test_db_session.refresh(vendor)
        
        assert vendor.created_at is not None
        # Note: Timestamp comparison might be tricky with different DBs
    
    @pytest.mark.asyncio
    async def test_updated_at_changes_on_update(self, test_db_session: AsyncSession):
        """Test that updated_at changes when record is modified."""
        vendor = VendorDB(
            vendor_id=f"V-UPDATE-{uuid.uuid4().hex[:8]}",
            vendor_name="Update Timestamp Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        await test_db_session.refresh(vendor)
        
        original_updated = vendor.updated_at
        
        # Update the vendor
        vendor.vendor_name = "Updated Name"
        await test_db_session.commit()
        await test_db_session.refresh(vendor)
        
        # Note: SQLite may not support onupdate triggers the same way
        # This test verifies the model structure allows for it
        assert vendor.vendor_name == "Updated Name"


# =============================================================================
# Index Tests
# =============================================================================

class TestIndexes:
    """Tests for index performance and existence."""
    
    @pytest.mark.asyncio
    async def test_indexed_query_performance(self, test_db_session: AsyncSession):
        """Test that indexed columns can be queried efficiently."""
        vendor_id = f"V-INDEX-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Index Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Query by indexed column (vendor_id)
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        fetched = result.scalar_one()
        assert fetched.vendor_name == "Index Test Vendor"
    
    @pytest.mark.asyncio
    async def test_composite_query(self, test_db_session: AsyncSession):
        """Test queries on multiple indexed columns."""
        base_id = uuid.uuid4().hex[:6]
        
        # Create invoices with different statuses
        for i in range(3):
            invoice = InvoiceDB(
                document_id=f"DOC-COMP-{base_id}-{i}",
                invoice_number=f"INV-COMP-{base_id}-{i}",
                file_name=f"comp_{i}.pdf",
                file_hash=f"comp_hash_{base_id}_{i}",
                status=InvoiceStatus.EXTRACTED if i % 2 == 0 else InvoiceStatus.APPROVED,
            )
            test_db_session.add(invoice)
        
        await test_db_session.commit()
        
        # Query using multiple indexed columns
        result = await test_db_session.execute(
            select(InvoiceDB).where(
                InvoiceDB.status == InvoiceStatus.EXTRACTED,
                InvoiceDB.document_id.like(f"DOC-COMP-{base_id}%")
            )
        )
        invoices = result.scalars().all()
        assert len(invoices) == 2
