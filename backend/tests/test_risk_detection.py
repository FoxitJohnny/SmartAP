"""
Unit Tests for Risk Detection Services

Tests duplicate detection, vendor risk analysis, and price anomaly detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from src.models import (
    Invoice,
    InvoiceLineItem,
    Vendor,
    VendorStatus,
    VendorRiskProfile,
    RiskLevel,
)
from src.services.duplicate_detector import DuplicateDetector
from src.services.vendor_risk_analyzer import VendorRiskAnalyzer
from src.services.price_anomaly_detector import PriceAnomalyDetector


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""
    
    @pytest.fixture
    def invoice_repo_mock(self):
        """Mock invoice repository."""
        return AsyncMock()
    
    @pytest.fixture
    def detector(self, invoice_repo_mock):
        """Create detector instance."""
        return DuplicateDetector(invoice_repo_mock)
    
    @pytest.fixture
    def sample_invoice(self):
        """Sample invoice for testing."""
        return Invoice(
            invoice_number="INV-2025-001",
            vendor_name="Test Vendor Inc",
            invoice_date=datetime(2025, 1, 15),
            due_date=datetime(2025, 2, 14),
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,
            line_items=[]
        )
    
    @pytest.mark.asyncio
    async def test_no_duplicates(self, detector, sample_invoice, invoice_repo_mock):
        """Test when no duplicates exist."""
        invoice_repo_mock.search_by_vendor.return_value = []
        
        is_duplicate, duplicate_info = await detector.detect_duplicates(sample_invoice)
        
        assert is_duplicate is False
        assert duplicate_info is None
    
    @pytest.mark.asyncio
    async def test_invoice_number_duplicate(self, detector, sample_invoice, invoice_repo_mock):
        """Test duplicate invoice number detection."""
        # Mock existing invoice with same invoice number
        existing_mock = Mock()
        existing_mock.document_id = "DOC-001"
        existing_mock.invoice_data = {
            "invoice_number": "INV-2025-001",
            "invoice_date": "2025-01-10T00:00:00",
            "total_amount": 1080.00,
        }
        
        invoice_repo_mock.search_by_vendor.return_value = [existing_mock]
        
        is_duplicate, duplicate_info = await detector.detect_duplicates(sample_invoice)
        
        assert is_duplicate is True
        assert duplicate_info is not None
        assert duplicate_info.match_type == "exact_invoice_number"
        assert duplicate_info.confidence_score == 1.0
    
    @pytest.mark.asyncio
    async def test_fuzzy_amount_duplicate(self, detector, sample_invoice, invoice_repo_mock):
        """Test fuzzy duplicate detection by amount and date."""
        # Mock existing invoice with similar amount and close date
        existing_mock = Mock()
        existing_mock.document_id = "DOC-002"
        existing_mock.invoice_data = {
            "invoice_number": "INV-2025-099",  # Different number
            "invoice_date": "2025-01-12T00:00:00",  # Within 30 days
            "total_amount": 1090.00,  # Within 2% tolerance
        }
        
        invoice_repo_mock.search_by_vendor.return_value = [existing_mock]
        
        is_duplicate, duplicate_info = await detector.detect_duplicates(sample_invoice)
        
        assert is_duplicate is True
        assert duplicate_info is not None
        assert duplicate_info.match_type == "fuzzy_amount_date"
        assert duplicate_info.confidence_score >= 0.75


class TestVendorRiskAnalyzer:
    """Tests for VendorRiskAnalyzer."""
    
    @pytest.fixture
    def vendor_repo_mock(self):
        """Mock vendor repository."""
        return AsyncMock()
    
    @pytest.fixture
    def analyzer(self, vendor_repo_mock):
        """Create analyzer instance."""
        return VendorRiskAnalyzer(vendor_repo_mock)
    
    @pytest.mark.asyncio
    async def test_low_risk_vendor(self, analyzer, vendor_repo_mock):
        """Test low-risk vendor assessment."""
        # Mock low-risk vendor
        vendor_mock = Mock()
        vendor_mock.vendor_id = "V001"
        vendor_mock.vendor_name = "Trusted Vendor"
        vendor_mock.status = VendorStatus.ACTIVE
        vendor_mock.onboarded_date = datetime.now() - timedelta(days=365)
        vendor_mock.risk_profile = VendorRiskProfile(
            risk_score=0.10,
            on_time_payment_rate=0.98,
            invoice_count=200,
            avg_invoice_amount=1000.00,
            max_invoice_amount=5000.00,
            has_fraud_history=False,
            last_payment_date=datetime.now() - timedelta(days=5),
            days_since_last_payment=5,
        )
        
        vendor_repo_mock.get_by_id.return_value = vendor_mock
        
        risk_score, risk_info = await analyzer.analyze_vendor_risk("V001")
        
        assert risk_score < 0.25
        assert risk_info is not None
        assert risk_info.vendor_id == "V001"
        assert risk_info.has_fraud_flags is False
    
    @pytest.mark.asyncio
    async def test_high_risk_vendor(self, analyzer, vendor_repo_mock):
        """Test high-risk vendor assessment."""
        # Mock high-risk vendor
        vendor_mock = Mock()
        vendor_mock.vendor_id = "V999"
        vendor_mock.vendor_name = "Risky Vendor"
        vendor_mock.status = VendorStatus.SUSPENDED
        vendor_mock.onboarded_date = datetime.now() - timedelta(days=90)
        vendor_mock.risk_profile = VendorRiskProfile(
            risk_score=0.80,
            on_time_payment_rate=0.60,
            invoice_count=10,
            avg_invoice_amount=500.00,
            max_invoice_amount=2000.00,
            has_fraud_history=True,
            last_payment_date=datetime.now() - timedelta(days=200),
            days_since_last_payment=200,
            fraud_flag_count=3,
        )
        
        vendor_repo_mock.get_by_id.return_value = vendor_mock
        
        risk_score, risk_info = await analyzer.analyze_vendor_risk("V999")
        
        assert risk_score >= 0.50
        assert risk_info is not None
        assert risk_info.has_fraud_flags is True
        assert risk_info.fraud_flag_count == 3
    
    @pytest.mark.asyncio
    async def test_unknown_vendor(self, analyzer, vendor_repo_mock):
        """Test unknown vendor (not in database)."""
        vendor_repo_mock.get_by_id.return_value = None
        
        risk_score, risk_info = await analyzer.analyze_vendor_risk("V-UNKNOWN")
        
        assert risk_score >= 0.80  # High risk for unknown
        assert risk_info is not None
        assert risk_info.vendor_name == "Unknown"
    
    def test_risk_level_conversion(self, analyzer):
        """Test risk score to risk level conversion."""
        assert analyzer.get_risk_level(0.10) == RiskLevel.LOW
        assert analyzer.get_risk_level(0.35) == RiskLevel.MEDIUM
        assert analyzer.get_risk_level(0.60) == RiskLevel.HIGH
        assert analyzer.get_risk_level(0.90) == RiskLevel.CRITICAL


class TestPriceAnomalyDetector:
    """Tests for PriceAnomalyDetector."""
    
    @pytest.fixture
    def invoice_repo_mock(self):
        """Mock invoice repository."""
        return AsyncMock()
    
    @pytest.fixture
    def detector(self, invoice_repo_mock):
        """Create detector instance."""
        return PriceAnomalyDetector(invoice_repo_mock)
    
    @pytest.fixture
    def sample_invoice(self):
        """Sample invoice for testing."""
        return Invoice(
            invoice_number="INV-2025-001",
            vendor_name="Test Vendor",
            invoice_date=datetime(2025, 1, 15),
            due_date=datetime(2025, 2, 14),
            currency="USD",
            subtotal=5000.00,
            tax=400.00,
            total_amount=5400.00,  # Significantly higher than average
            line_items=[]
        )
    
    @pytest.mark.asyncio
    async def test_no_anomaly_insufficient_history(self, detector, sample_invoice, invoice_repo_mock):
        """Test no anomaly when insufficient historical data."""
        invoice_repo_mock.search_by_vendor.return_value = []
        
        risk_score, anomaly_info = await detector.detect_price_anomalies(
            sample_invoice,
            "Test Vendor"
        )
        
        assert risk_score == 0.0
        assert anomaly_info is None
    
    @pytest.mark.asyncio
    async def test_price_anomaly_detected(self, detector, sample_invoice, invoice_repo_mock):
        """Test price anomaly detection."""
        # Mock historical invoices with lower amounts
        historical_mocks = []
        for i in range(10):
            mock_inv = Mock()
            mock_inv.invoice_data = {
                "total_amount": 1000.00 + (i * 50),  # $1000-1450
                "invoice_date": (datetime.now() - timedelta(days=30*i)).isoformat(),
            }
            historical_mocks.append(mock_inv)
        
        invoice_repo_mock.search_by_vendor.return_value = historical_mocks
        
        risk_score, anomaly_info = await detector.detect_price_anomalies(
            sample_invoice,
            "Test Vendor"
        )
        
        # $5400 is much higher than $1000-1450 average
        assert risk_score > 0.0
        assert anomaly_info is not None
        assert anomaly_info.is_anomaly is True
        assert anomaly_info.current_amount == 5400.00
        assert anomaly_info.average_amount < 1500.00
    
    @pytest.mark.asyncio
    async def test_no_anomaly_within_range(self, detector, invoice_repo_mock):
        """Test no anomaly when within normal range."""
        normal_invoice = Invoice(
            invoice_number="INV-2025-002",
            vendor_name="Test Vendor",
            invoice_date=datetime(2025, 1, 15),
            due_date=datetime(2025, 2, 14),
            currency="USD",
            subtotal=1000.00,
            tax=80.00,
            total_amount=1080.00,  # Within normal range
            line_items=[]
        )
        
        # Mock historical invoices with similar amounts
        historical_mocks = []
        for i in range(10):
            mock_inv = Mock()
            mock_inv.invoice_data = {
                "total_amount": 1000.00 + (i * 20),  # $1000-1180
                "invoice_date": (datetime.now() - timedelta(days=30*i)).isoformat(),
            }
            historical_mocks.append(mock_inv)
        
        invoice_repo_mock.search_by_vendor.return_value = historical_mocks
        
        risk_score, anomaly_info = await detector.detect_price_anomalies(
            normal_invoice,
            "Test Vendor"
        )
        
        assert risk_score == 0.0
        assert anomaly_info is None
    
    def test_amount_risk_very_high(self, detector):
        """Test amount risk for very high amounts."""
        risk = detector.calculate_amount_risk(250000.00, 0, 100000.00)
        assert risk > 0.30  # Should flag as risky
    
    def test_amount_risk_normal(self, detector):
        """Test amount risk for normal amounts."""
        risk = detector.calculate_amount_risk(50000.00, 0, 100000.00)
        assert risk == 0.0  # Within normal range


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
