"""
Transaction Management Integration Tests

Tests for advanced transaction handling including savepoints, isolation, and concurrency.
V3.2.2 - Database Integration Testing
"""

import pytest
import uuid
import asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    InvoiceDB,
    PurchaseOrderDB,
    VendorDB,
)
from src.models.invoice import InvoiceStatus
from src.models.purchase_order import POStatus


# =============================================================================
# Savepoint Tests
# =============================================================================

class TestSavepoints:
    """Tests for transaction savepoint handling."""
    
    @pytest.mark.asyncio
    async def test_nested_transaction_with_savepoint(self, test_db_session: AsyncSession):
        """Test nested transactions using savepoints."""
        vendor_id = f"V-SAVE-{uuid.uuid4().hex[:8]}"
        
        # Start main transaction
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Savepoint Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.flush()
        
        # Create savepoint
        async with test_db_session.begin_nested():
            # Add another record in nested transaction
            vendor2 = VendorDB(
                vendor_id=f"{vendor_id}-nested",
                vendor_name="Nested Vendor",
                onboarded_date=date.today(),
            )
            test_db_session.add(vendor2)
            # This will automatically commit the savepoint
        
        await test_db_session.commit()
        
        # Verify both vendors exist
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id.like(f"{vendor_id}%"))
        )
        vendors = result.scalars().all()
        assert len(vendors) == 2
    
    @pytest.mark.asyncio
    async def test_savepoint_rollback(self, test_db_session: AsyncSession):
        """Test that savepoint rollback doesn't affect main transaction."""
        vendor_id = f"V-SAVEROLL-{uuid.uuid4().hex[:8]}"
        
        # Create vendor in main transaction
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Main Transaction Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.flush()
        
        # Try nested transaction that will fail
        try:
            async with test_db_session.begin_nested():
                # Create duplicate vendor (should fail)
                vendor_dup = VendorDB(
                    vendor_id=vendor_id,  # Duplicate
                    vendor_name="Duplicate",
                    onboarded_date=date.today(),
                )
                test_db_session.add(vendor_dup)
                await test_db_session.flush()
        except IntegrityError:
            pass  # Expected - savepoint rolls back automatically
        
        # Main transaction should still work
        await test_db_session.commit()
        
        # Verify original vendor exists
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        fetched = result.scalar_one()
        assert fetched.vendor_name == "Main Transaction Vendor"


# =============================================================================
# Bulk Operation Tests
# =============================================================================

class TestBulkOperations:
    """Tests for bulk database operations."""
    
    @pytest.mark.asyncio
    async def test_bulk_insert(self, test_db_session: AsyncSession):
        """Test inserting many records efficiently."""
        base_id = uuid.uuid4().hex[:6]
        
        # Create 100 invoices
        invoices = [
            InvoiceDB(
                document_id=f"DOC-BULK-{base_id}-{i:03d}",
                invoice_number=f"INV-BULK-{base_id}-{i:03d}",
                file_name=f"bulk_{i}.pdf",
                file_hash=f"bulk_hash_{base_id}_{i}",
                status=InvoiceStatus.INGESTED,
            )
            for i in range(100)
        ]
        
        test_db_session.add_all(invoices)
        await test_db_session.commit()
        
        # Verify all were created
        result = await test_db_session.execute(
            select(InvoiceDB).where(
                InvoiceDB.document_id.like(f"DOC-BULK-{base_id}%")
            )
        )
        fetched = result.scalars().all()
        assert len(fetched) == 100
    
    @pytest.mark.asyncio
    async def test_bulk_update(self, test_db_session: AsyncSession):
        """Test updating many records efficiently using ORM bulk update."""
        base_id = uuid.uuid4().hex[:6]
        
        # Create invoices
        for i in range(10):
            invoice = InvoiceDB(
                document_id=f"DOC-BULKUP-{base_id}-{i}",
                invoice_number=f"INV-BULKUP-{base_id}-{i}",
                file_name=f"bulkup_{i}.pdf",
                file_hash=f"bulkup_hash_{base_id}_{i}",
                status=InvoiceStatus.INGESTED,
            )
            test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Fetch all invoices to update
        result = await test_db_session.execute(
            select(InvoiceDB).where(
                InvoiceDB.document_id.like(f"DOC-BULKUP-{base_id}%")
            )
        )
        invoices = result.scalars().all()
        
        # Bulk update using ORM
        for inv in invoices:
            inv.status = InvoiceStatus.EXTRACTED
        await test_db_session.commit()
        
        # Verify all were updated
        result = await test_db_session.execute(
            select(InvoiceDB).where(
                InvoiceDB.document_id.like(f"DOC-BULKUP-{base_id}%")
            )
        )
        invoices = result.scalars().all()
        assert len(invoices) == 10
        for inv in invoices:
            assert inv.status == InvoiceStatus.EXTRACTED
    
    @pytest.mark.asyncio
    async def test_bulk_delete(self, test_db_session: AsyncSession):
        """Test deleting many records efficiently."""
        base_id = uuid.uuid4().hex[:6]
        
        # Create invoices
        for i in range(10):
            invoice = InvoiceDB(
                document_id=f"DOC-BULKDEL-{base_id}-{i}",
                invoice_number=f"INV-BULKDEL-{base_id}-{i}",
                file_name=f"bulkdel_{i}.pdf",
                file_hash=f"bulkdel_hash_{base_id}_{i}",
                status=InvoiceStatus.INGESTED,
            )
            test_db_session.add(invoice)
        await test_db_session.commit()
        
        # Bulk delete using SQL
        await test_db_session.execute(
            text("DELETE FROM invoices WHERE document_id LIKE :pattern"),
            {"pattern": f"DOC-BULKDEL-{base_id}%"}
        )
        await test_db_session.commit()
        
        # Verify all were deleted
        result = await test_db_session.execute(
            select(InvoiceDB).where(
                InvoiceDB.document_id.like(f"DOC-BULKDEL-{base_id}%")
            )
        )
        invoices = result.scalars().all()
        assert len(invoices) == 0


# =============================================================================
# Session State Tests
# =============================================================================

class TestSessionState:
    """Tests for session state management."""
    
    @pytest.mark.asyncio
    async def test_session_dirty_tracking(self, test_db_session: AsyncSession):
        """Test that session tracks dirty (modified) objects."""
        vendor_id = f"V-DIRTY-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Dirty Track Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Modify the vendor
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        vendor.vendor_name = "Modified Name"
        
        # Session should track the change
        assert vendor in test_db_session.dirty
        
        await test_db_session.commit()
        assert vendor not in test_db_session.dirty
    
    @pytest.mark.asyncio
    async def test_session_new_tracking(self, test_db_session: AsyncSession):
        """Test that session tracks new (unsaved) objects."""
        vendor = VendorDB(
            vendor_id=f"V-NEW-{uuid.uuid4().hex[:8]}",
            vendor_name="New Track Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        
        # Session should track as new
        assert vendor in test_db_session.new
        
        await test_db_session.commit()
        assert vendor not in test_db_session.new
    
    @pytest.mark.asyncio
    async def test_session_deleted_tracking(self, test_db_session: AsyncSession):
        """Test that session tracks deleted objects."""
        vendor_id = f"V-DELETED-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Delete Track Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Delete the vendor
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        await test_db_session.delete(vendor)
        
        # Session should track as deleted
        assert vendor in test_db_session.deleted
        
        await test_db_session.commit()
        assert vendor not in test_db_session.deleted
    
    @pytest.mark.asyncio
    async def test_expunge_object(self, test_db_session: AsyncSession):
        """Test removing object from session without deleting."""
        vendor_id = f"V-EXPUNGE-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Expunge Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Expunge from session
        test_db_session.expunge(vendor)
        
        # Vendor should not be in session
        assert vendor not in test_db_session
        
        # But should still exist in DB
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        fetched = result.scalar_one()
        assert fetched.vendor_name == "Expunge Test"


# =============================================================================
# Refresh and Expire Tests
# =============================================================================

class TestRefreshExpire:
    """Tests for refreshing and expiring objects."""
    
    @pytest.mark.asyncio
    async def test_refresh_object(self, test_db_session: AsyncSession):
        """Test refreshing object from database."""
        vendor_id = f"V-REFRESH-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Refresh Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Modify in memory
        vendor.vendor_name = "Modified in Memory"
        
        # Refresh from DB - should revert
        await test_db_session.refresh(vendor)
        assert vendor.vendor_name == "Refresh Test"
    
    @pytest.mark.asyncio
    async def test_expire_object(self, test_db_session: AsyncSession):
        """Test expiring object attributes."""
        vendor_id = f"V-EXPIRE-{uuid.uuid4().hex[:8]}"
        
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Expire Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Expire the object - this marks all attributes as stale
        test_db_session.expire(vendor)
        
        # Use refresh to properly reload from DB in async context
        await test_db_session.refresh(vendor)
        
        # Verify the attribute value is correct after refresh
        assert vendor.vendor_name == "Expire Test"


# =============================================================================
# Complex Transaction Tests
# =============================================================================

class TestComplexTransactions:
    """Tests for complex multi-step transactions."""
    
    @pytest.mark.asyncio
    async def test_multi_entity_transaction(self, test_db_session: AsyncSession):
        """Test transaction spanning multiple entity types."""
        base_id = uuid.uuid4().hex[:6]
        vendor_id = f"V-MULTI-{base_id}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Multi Entity Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        
        # Create PO for vendor
        po = PurchaseOrderDB(
            po_number=f"PO-MULTI-{base_id}",
            vendor_id=vendor_id,
            created_date=date.today(),
            status=POStatus.OPEN,
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )
        test_db_session.add(po)
        
        # Create invoice
        invoice = InvoiceDB(
            document_id=f"DOC-MULTI-{base_id}",
            invoice_number=f"INV-MULTI-{base_id}",
            file_name="multi_entity.pdf",
            file_hash=f"multi_hash_{base_id}",
            status=InvoiceStatus.INGESTED,
            invoice_data={"vendor_id": vendor_id, "po_number": po.po_number},
        )
        test_db_session.add(invoice)
        
        # Single commit for all
        await test_db_session.commit()
        
        # Verify all entities exist
        v_result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        assert v_result.scalar_one() is not None
        
        po_result = await test_db_session.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po.po_number)
        )
        assert po_result.scalar_one() is not None
        
        inv_result = await test_db_session.execute(
            select(InvoiceDB).where(InvoiceDB.document_id == invoice.document_id)
        )
        assert inv_result.scalar_one() is not None
    
    @pytest.mark.asyncio
    async def test_transaction_with_conditional_logic(self, test_db_session: AsyncSession):
        """Test transaction with conditional updates."""
        base_id = uuid.uuid4().hex[:6]
        vendor_id = f"V-COND-{base_id}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Conditional Test Vendor",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Create POs and conditionally update status
        for i in range(5):
            po = PurchaseOrderDB(
                po_number=f"PO-COND-{base_id}-{i}",
                vendor_id=vendor_id,
                created_date=date.today(),
                status=POStatus.OPEN,
                subtotal=Decimal("100.00") * (i + 1),
                total_amount=Decimal("100.00") * (i + 1),
            )
            test_db_session.add(po)
        
        await test_db_session.commit()
        
        # Update POs based on amount
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(
                PurchaseOrderDB.vendor_id == vendor_id
            )
        )
        pos = result.scalars().all()
        
        for po in pos:
            # High value POs get special status
            if po.total_amount > Decimal("300.00"):
                po.notes = "High Value Order"
        
        await test_db_session.commit()
        
        # Verify conditional updates
        result = await test_db_session.execute(
            select(PurchaseOrderDB).where(
                PurchaseOrderDB.vendor_id == vendor_id,
                PurchaseOrderDB.notes == "High Value Order"
            )
        )
        high_value_pos = result.scalars().all()
        assert len(high_value_pos) == 2  # POs with amounts 400 and 500


# =============================================================================
# Data Integrity Tests
# =============================================================================

class TestDataIntegrity:
    """Tests for data integrity during transactions."""
    
    @pytest.mark.asyncio
    async def test_no_partial_updates(self, test_db_session: AsyncSession):
        """Test that partial updates don't occur on error."""
        base_id = uuid.uuid4().hex[:6]
        vendor_id = f"V-PARTIAL-{base_id}"
        
        # Create vendor
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Partial Update Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Start transaction with multiple updates
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        vendor = result.scalar_one()
        vendor.vendor_name = "Updated Name"
        
        # Try to add duplicate vendor (should fail)
        vendor_dup = VendorDB(
            vendor_id=vendor_id,  # Duplicate
            vendor_name="Duplicate",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor_dup)
        
        try:
            await test_db_session.commit()
        except IntegrityError:
            await test_db_session.rollback()
        
        # Verify original vendor wasn't updated
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        fetched = result.scalar_one()
        assert fetched.vendor_name == "Partial Update Test"  # Original name
    
    @pytest.mark.asyncio
    async def test_consistent_read_after_write(self, test_db_session: AsyncSession):
        """Test that reads see committed writes immediately."""
        vendor_id = f"V-RAW-{uuid.uuid4().hex[:8]}"
        
        # Write
        vendor = VendorDB(
            vendor_id=vendor_id,
            vendor_name="Read After Write Test",
            onboarded_date=date.today(),
        )
        test_db_session.add(vendor)
        await test_db_session.commit()
        
        # Immediate read
        result = await test_db_session.execute(
            select(VendorDB).where(VendorDB.vendor_id == vendor_id)
        )
        fetched = result.scalar_one()
        assert fetched.vendor_name == "Read After Write Test"
        
        # Update
        fetched.vendor_name = "Updated RAW"
        await test_db_session.commit()
        
        # Immediate read after update
        await test_db_session.refresh(fetched)
        assert fetched.vendor_name == "Updated RAW"
