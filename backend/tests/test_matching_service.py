"""
Unit Tests for PO Matching Agent and Services

Tests matching logic, scoring algorithms, and discrepancy detection.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models import (
    Invoice,
    InvoiceLineItem,
    PurchaseOrder,
    POLineItem,
    POStatus,
    Vendor,
    VendorStatus,
    VendorRiskProfile,
)
from src.services.matching_service import MatchingService
from src.services.discrepancy_detector import DiscrepancyDetector


class TestMatchingService:
    """Tests for MatchingService scoring algorithms."""
    
    def test_vendor_exact_match(self):
        """Test exact vendor name match."""
        score = MatchingService.calculate_vendor_match_score(
            "Acme Corporation",
            "V001",
            "Acme Corporation"
        )
        assert score == 1.0
    
    def test_vendor_fuzzy_match(self):
        """Test fuzzy vendor name match."""
        score = MatchingService.calculate_vendor_match_score(
            "Acme Corp",
            "V001",
            "Acme Corporation"
        )
        assert score > 0.80  # Should be high fuzzy match
    
    def test_vendor_partial_match(self):
        """Test partial vendor name match."""
        score = MatchingService.calculate_vendor_match_score(
            "Acme Office Supplies",
            "V001",
            "Acme Corporation"
        )
        assert 0.50 < score < 0.90  # Partial match
    
    def test_vendor_no_match(self):
        """Test vendor name no match."""
        score = MatchingService.calculate_vendor_match_score(
            "Different Vendor Inc",
            "V001",
            "Acme Corporation"
        )
        assert score < 0.50  # Poor match
    
    def test_amount_exact_match(self):
        """Test exact amount match."""
        score = MatchingService.calculate_amount_match_score(1000.00, 1000.00)
        assert score == 1.0
    
    def test_amount_within_tolerance(self):
        """Test amount within 5% tolerance."""
        score = MatchingService.calculate_amount_match_score(1025.00, 1000.00)
        assert score >= 0.85  # Within tolerance
    
    def test_amount_beyond_tolerance(self):
        """Test amount beyond tolerance."""
        score = MatchingService.calculate_amount_match_score(1200.00, 1000.00)
        assert score < 0.85  # Beyond 5% tolerance
    
    def test_date_match_within_window(self):
        """Test date match within tolerance window."""
        po_date = datetime(2026, 1, 1)
        invoice_date = datetime(2026, 1, 15)
        score = MatchingService.calculate_date_match_score(invoice_date, po_date)
        assert score >= 0.90  # Within acceptable window
    
    def test_date_invoice_before_po(self):
        """Test invoice dated before PO (suspicious)."""
        po_date = datetime(2026, 1, 15)
        invoice_date = datetime(2026, 1, 10)
        score = MatchingService.calculate_date_match_score(invoice_date, po_date)
        assert score < 1.0  # Penalty for being before PO
    
    def test_line_items_exact_match(self):
        """Test exact line item matching."""
        invoice_items = [
            InvoiceLineItem(
                line_number=1,
                description="Printer Paper - 10 reams",
                quantity=10,
                unit_price=45.00,
                amount=450.00
            )
        ]
        
        po_items = [
            POLineItem(
                line_number=1,
                description="Printer Paper - 10 reams",
                quantity=10,
                unit_price=45.00,
                amount=450.00,
                sku="PP-100"
            )
        ]
        
        matches, score = MatchingService.match_line_items(invoice_items, po_items)
        
        assert len(matches) == 1
        assert score >= 0.95  # High match
        assert matches[0].matched is True
    
    def test_line_items_fuzzy_match(self):
        """Test fuzzy line item matching."""
        invoice_items = [
            InvoiceLineItem(
                line_number=1,
                description="Printer Paper 10pk",
                quantity=10,
                unit_price=45.00,
                amount=450.00
            )
        ]
        
        po_items = [
            POLineItem(
                line_number=1,
                description="Printer Paper - 10 reams",
                quantity=10,
                unit_price=45.00,
                amount=450.00,
                sku="PP-100"
            )
        ]
        
        matches, score = MatchingService.match_line_items(invoice_items, po_items)
        
        assert len(matches) == 1
        assert 0.70 < score < 0.95  # Good fuzzy match
    
    def test_line_items_unmatched(self):
        """Test unmatched line items."""
        invoice_items = [
            InvoiceLineItem(
                line_number=1,
                description="Extra Item Not in PO",
                quantity=5,
                unit_price=100.00,
                amount=500.00
            )
        ]
        
        po_items = [
            POLineItem(
                line_number=1,
                description="Different Item",
                quantity=10,
                unit_price=50.00,
                amount=500.00,
                sku="XX-999"
            )
        ]
        
        matches, score = MatchingService.match_line_items(invoice_items, po_items)
        
        assert score < 0.70  # Poor match
    
    def test_overall_score_calculation(self):
        """Test weighted overall score calculation."""
        score = MatchingService.calculate_overall_match_score(
            vendor_score=1.0,
            amount_score=0.95,
            date_score=0.90,
            line_items_score=0.92
        )
        
        # Weighted: 0.30*1.0 + 0.30*0.95 + 0.30*0.92 + 0.10*0.90
        expected = 0.30 + 0.285 + 0.276 + 0.09
        assert abs(score - expected) < 0.01


class TestDiscrepancyDetector:
    """Tests for DiscrepancyDetector."""
    
    def test_vendor_mismatch_detection(self):
        """Test vendor name mismatch detection."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Acme Corp",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            line_items=[]
        )
        
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
            line_items=[]
        )
        
        discrepancies = DiscrepancyDetector.detect_vendor_discrepancy(
            invoice, po, "Acme Corporation", 0.85
        )
        
        assert len(discrepancies) == 1
        assert discrepancies[0].type == "vendor_mismatch"
    
    def test_amount_discrepancy_detection(self):
        """Test amount discrepancy detection."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Acme Corp",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1200.00,  # $120 over
            line_items=[]
        )
        
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
            line_items=[]
        )
        
        discrepancies = DiscrepancyDetector.detect_amount_discrepancy(
            invoice, po, 0.85
        )
        
        assert len(discrepancies) == 1
        assert discrepancies[0].type == "amount_mismatch"
        assert "OVER" in discrepancies[0].difference
    
    def test_date_discrepancy_invoice_before_po(self):
        """Test invoice dated before PO."""
        po_date = datetime(2026, 1, 15)
        invoice_date = datetime(2026, 1, 10)
        
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Acme Corp",
            invoice_date=invoice_date,
            due_date=invoice_date + timedelta(days=30),
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            line_items=[]
        )
        
        po = PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            created_date=po_date,
            expected_delivery=po_date + timedelta(days=30),
            status=POStatus.OPEN,
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            payment_terms="Net 30",
            created_by="test@company.com",
            line_items=[]
        )
        
        discrepancies = DiscrepancyDetector.detect_date_discrepancy(
            invoice, po, 0.80
        )
        
        assert len(discrepancies) == 1
        assert discrepancies[0].type == "date_mismatch"
        assert "before PO" in discrepancies[0].description
    
    def test_currency_mismatch_detection(self):
        """Test currency mismatch detection."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Acme Corp",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            currency="EUR",  # Different currency
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            line_items=[]
        )
        
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
            line_items=[]
        )
        
        discrepancies = DiscrepancyDetector.detect_currency_discrepancy(invoice, po)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].type == "currency_mismatch"
        assert discrepancies[0].severity == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
