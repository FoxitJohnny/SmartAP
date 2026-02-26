"""
Unit Tests for Risk Detection Services

Tests for DuplicateDetector, VendorRiskAnalyzer, and PriceAnomalyDetector.
Note: These are unit tests that mock external dependencies.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from src.services.duplicate_detector import DuplicateDetector
from src.services.vendor_risk_analyzer import VendorRiskAnalyzer
from src.services.price_anomaly_detector import PriceAnomalyDetector


# =============================================================================
# Duplicate Detector Tests
# =============================================================================

class TestDuplicateDetector:
    """Tests for DuplicateDetector service."""
    
    @pytest.fixture
    def invoice_repo_mock(self):
        """Mock invoice repository."""
        return AsyncMock()
    
    @pytest.fixture
    def detector(self, invoice_repo_mock):
        """Create detector instance."""
        return DuplicateDetector(invoice_repo_mock)
    
    def test_detector_initialization(self, detector, invoice_repo_mock):
        """Test detector initializes with repository."""
        assert detector.invoice_repo == invoice_repo_mock
    
    def test_threshold_constants(self):
        """Test threshold constants are defined."""
        assert DuplicateDetector.EXACT_DUPLICATE_DAYS == 90
        assert DuplicateDetector.FUZZY_DUPLICATE_DAYS == 30
        assert DuplicateDetector.AMOUNT_TOLERANCE == 0.02
    
    @pytest.mark.asyncio
    async def test_no_duplicates_empty_history(self, detector, invoice_repo_mock):
        """Test when no historical invoices exist."""
        invoice_repo_mock.search_by_vendor.return_value = []
        
        # Create mock invoice
        invoice = Mock()
        invoice.vendor_name = "Test Vendor"
        invoice.invoice_number = "INV-001"
        invoice.invoice_date = date(2026, 1, 15)
        invoice.total = Decimal("1000.00")
        
        is_duplicate, duplicate_info = await detector.detect_duplicates(invoice)
        
        assert is_duplicate is False
        assert duplicate_info is None
    
    @pytest.mark.asyncio
    async def test_skip_invoices_without_data(self, detector, invoice_repo_mock):
        """Test that invoices without data are skipped."""
        existing_mock = Mock()
        existing_mock.invoice_data = None  # No data
        
        invoice_repo_mock.search_by_vendor.return_value = [existing_mock]
        
        invoice = Mock()
        invoice.vendor_name = "Test Vendor"
        invoice.invoice_number = "INV-001"
        invoice.invoice_date = date(2026, 1, 15)
        invoice.total = Decimal("1000.00")
        
        is_duplicate, duplicate_info = await detector.detect_duplicates(invoice)
        
        assert is_duplicate is False
        assert duplicate_info is None


# =============================================================================
# Vendor Risk Analyzer Tests
# =============================================================================

class TestVendorRiskAnalyzer:
    """Tests for VendorRiskAnalyzer service."""
    
    @pytest.fixture
    def vendor_repo_mock(self):
        """Mock vendor repository."""
        return AsyncMock()
    
    @pytest.fixture
    def analyzer(self, vendor_repo_mock):
        """Create analyzer instance."""
        return VendorRiskAnalyzer(vendor_repo_mock)
    
    def test_analyzer_initialization(self, analyzer, vendor_repo_mock):
        """Test analyzer initializes with repository."""
        assert analyzer.vendor_repo == vendor_repo_mock
    
    def test_risk_threshold_constants(self):
        """Test risk threshold constants are defined."""
        assert hasattr(VendorRiskAnalyzer, 'LOW_RISK_THRESHOLD')
        assert hasattr(VendorRiskAnalyzer, 'MEDIUM_RISK_THRESHOLD')
        assert hasattr(VendorRiskAnalyzer, 'HIGH_RISK_THRESHOLD')
    
    @pytest.mark.asyncio
    async def test_unknown_vendor_returns_result(self, analyzer, vendor_repo_mock):
        """Test that unknown vendor returns a valid result."""
        vendor_repo_mock.get_by_id.return_value = None
        
        risk_score, risk_info = await analyzer.analyze_vendor_risk("UNKNOWN-001")
        
        # Unknown vendor should have some risk score
        assert risk_score >= 0.0
        assert risk_score <= 1.0
        assert risk_info is not None


# =============================================================================
# Price Anomaly Detector Tests
# =============================================================================

class TestPriceAnomalyDetector:
    """Tests for PriceAnomalyDetector service."""
    
    @pytest.fixture
    def invoice_repo_mock(self):
        """Mock invoice repository."""
        return AsyncMock()
    
    @pytest.fixture
    def detector(self, invoice_repo_mock):
        """Create detector instance."""
        return PriceAnomalyDetector(invoice_repo_mock)
    
    def test_detector_initialization(self, detector, invoice_repo_mock):
        """Test detector initializes with repository."""
        assert detector.invoice_repo == invoice_repo_mock
    
    def test_anomaly_threshold_constants(self):
        """Test anomaly detector constants are defined."""
        assert hasattr(PriceAnomalyDetector, 'STANDARD_DEVIATIONS_THRESHOLD')
        assert hasattr(PriceAnomalyDetector, 'MIN_HISTORICAL_INVOICES')
        assert hasattr(PriceAnomalyDetector, 'SIGNIFICANT_AMOUNT_THRESHOLD')
    
    def _create_historical_mock(self, amount):
        """Helper to create historical invoice mock."""
        mock = Mock()
        mock.invoice_data = {"total_amount": amount}
        return mock
    
    @pytest.mark.asyncio
    async def test_no_anomaly_insufficient_history(self, detector, invoice_repo_mock):
        """Test no anomaly when insufficient historical data."""
        # Only 2 historical invoices (need 3)
        invoice_repo_mock.search_by_vendor.return_value = [
            self._create_historical_mock(4500.00),
            self._create_historical_mock(5500.00),
        ]
        
        invoice = Mock()
        invoice.total = Decimal("5000.00")
        
        risk_score, anomaly_info = await detector.detect_price_anomalies(
            invoice, "Test Vendor"
        )
        
        assert risk_score == 0.0
        assert anomaly_info is None
    
    @pytest.mark.asyncio
    async def test_handles_empty_history(self, detector, invoice_repo_mock):
        """Test handling of empty historical data."""
        invoice_repo_mock.search_by_vendor.return_value = []
        
        invoice = Mock()
        invoice.total = Decimal("5000.00")
        
        risk_score, anomaly_info = await detector.detect_price_anomalies(
            invoice, "Test Vendor"
        )
        
        assert risk_score == 0.0
        assert anomaly_info is None


# =============================================================================
# Risk Score Threshold Tests  
# =============================================================================

class TestRiskThresholds:
    """Tests for risk threshold constants."""
    
    def test_duplicate_detector_thresholds_reasonable(self):
        """Verify duplicate detector thresholds are reasonable."""
        assert DuplicateDetector.EXACT_DUPLICATE_DAYS > 0
        assert DuplicateDetector.FUZZY_DUPLICATE_DAYS > 0
        assert 0 < DuplicateDetector.AMOUNT_TOLERANCE < 1
    
    def test_vendor_risk_thresholds_ordered(self):
        """Verify vendor risk thresholds are properly ordered."""
        low = VendorRiskAnalyzer.LOW_RISK_THRESHOLD
        medium = VendorRiskAnalyzer.MEDIUM_RISK_THRESHOLD
        high = VendorRiskAnalyzer.HIGH_RISK_THRESHOLD
        
        assert low < medium < high
        assert all(0 <= t <= 1 for t in [low, medium, high])
    
    def test_price_anomaly_thresholds_reasonable(self):
        """Verify price anomaly thresholds are reasonable."""
        assert PriceAnomalyDetector.STANDARD_DEVIATIONS_THRESHOLD > 0
        assert PriceAnomalyDetector.MIN_HISTORICAL_INVOICES >= 1
        assert PriceAnomalyDetector.SIGNIFICANT_AMOUNT_THRESHOLD > 0
