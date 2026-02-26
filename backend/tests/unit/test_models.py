"""
Unit Tests for SmartAP Pydantic Models

Comprehensive tests for all Pydantic models covering:
- Field validation
- Default values
- Required vs optional fields
- Computed properties
- Serialization/deserialization
- Edge cases
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pydantic import ValidationError

# Invoice models
from src.models.invoice import (
    Invoice,
    InvoiceLineItem,
    InvoiceExtractionResult,
    ExtractionConfidence,
    InvoiceStatus,
)

# Purchase Order models
from src.models.purchase_order import (
    PurchaseOrder,
    POLineItem,
    POStatus,
)

# Vendor models
from src.models.vendor import (
    Vendor,
    VendorRiskProfile,
    VendorStatus,
    PaymentRecord,
    FraudFlag,
    FraudFlagType,
)

# Matching models
from src.models.matching import (
    MatchingResult,
    MatchType,
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity,
    LineItemMatch,
)

# Risk models
from src.models.risk import (
    RiskAssessment,
    RiskLevel,
    RiskFlag,
    RiskFlagType,
    RecommendedAction,
    DuplicateInfo,
    VendorRiskInfo,
    PriceAnomalyInfo,
)


# =============================================================================
# Invoice Model Tests
# =============================================================================

class TestInvoiceStatus:
    """Tests for InvoiceStatus enum."""
    
    def test_all_statuses_exist(self):
        """Test all expected statuses are defined."""
        expected = [
            "INGESTED", "EXTRACTED", "MATCHED", "RISK_REVIEW",
            "APPROVED", "READY_FOR_PAYMENT", "ARCHIVED", "FAILED"
        ]
        for status in expected:
            assert hasattr(InvoiceStatus, status)
    
    def test_status_values(self):
        """Test status string values."""
        assert InvoiceStatus.INGESTED.value == "ingested"
        assert InvoiceStatus.EXTRACTED.value == "extracted"
        assert InvoiceStatus.APPROVED.value == "approved"


class TestExtractionConfidence:
    """Tests for ExtractionConfidence model."""
    
    def test_default_values(self):
        """Test all fields default to 0.0."""
        conf = ExtractionConfidence()
        assert conf.invoice_number == 0.0
        assert conf.vendor_name == 0.0
        assert conf.total == 0.0
    
    def test_overall_calculation(self):
        """Test overall confidence calculation."""
        conf = ExtractionConfidence(
            invoice_number=0.9,
            vendor_name=0.85,
            invoice_date=0.95,
            total=0.92,
            line_items=0.88
        )
        # Overall is average of: invoice_number, vendor_name, invoice_date, total, line_items
        expected = (0.9 + 0.85 + 0.95 + 0.92 + 0.88) / 5
        assert abs(conf.overall - expected) < 0.001
    
    def test_validation_rejects_values_over_one(self):
        """Test validation rejects confidence > 1.0."""
        with pytest.raises(ValidationError):
            ExtractionConfidence(invoice_number=1.5)
    
    def test_validation_rejects_negative_values(self):
        """Test validation rejects negative confidence."""
        with pytest.raises(ValidationError):
            ExtractionConfidence(vendor_name=-0.1)


class TestInvoiceLineItem:
    """Tests for InvoiceLineItem model."""
    
    def test_minimal_creation(self):
        """Test creation with only required field."""
        item = InvoiceLineItem(description="Test Item")
        assert item.description == "Test Item"
        assert item.quantity is None
        assert item.unit_price is None
    
    def test_full_creation(self):
        """Test creation with all fields."""
        item = InvoiceLineItem(
            description="Widget",
            quantity=10.0,
            unit_price=Decimal("25.99"),
            amount=Decimal("259.90"),
            sku="WGT-001",
            unit="ea"
        )
        assert item.quantity == 10.0
        assert item.unit_price == Decimal("25.99")
        assert item.sku == "WGT-001"
    
    def test_serialization(self):
        """Test JSON serialization."""
        item = InvoiceLineItem(
            description="Test",
            amount=Decimal("100.00")
        )
        data = item.model_dump(mode="json")
        assert data["description"] == "Test"
        assert data["amount"] == "100.00"


class TestInvoice:
    """Tests for Invoice model."""
    
    def test_minimal_creation(self):
        """Test creation with only required fields."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Test Vendor",
            total=Decimal("1000.00")
        )
        assert invoice.invoice_number == "INV-001"
        assert invoice.currency == "USD"  # Default
        assert invoice.line_items == []  # Default
    
    def test_full_creation(self):
        """Test creation with all fields."""
        invoice = Invoice(
            invoice_number="INV-002",
            vendor_name="Acme Corp",
            vendor_address="123 Main St",
            vendor_tax_id="12-3456789",
            invoice_date=date(2026, 1, 15),
            due_date=date(2026, 2, 15),
            currency="EUR",
            subtotal=Decimal("850.00"),
            tax=Decimal("150.00"),
            total=Decimal("1000.00"),
            line_items=[
                InvoiceLineItem(description="Item 1", amount=Decimal("500.00")),
                InvoiceLineItem(description="Item 2", amount=Decimal("350.00"))
            ],
            payment_terms="Net 30",
            po_number="PO-001"
        )
        assert invoice.currency == "EUR"
        assert len(invoice.line_items) == 2
        assert invoice.po_number == "PO-001"
    
    def test_missing_required_field(self):
        """Test validation error on missing required field."""
        with pytest.raises(ValidationError):
            Invoice(
                invoice_number="INV-001"
                # Missing: vendor_name, total
            )


class TestInvoiceExtractionResult:
    """Tests for InvoiceExtractionResult model."""
    
    def test_minimal_creation(self):
        """Test creation with required fields."""
        result = InvoiceExtractionResult(
            document_id="DOC-001",
            file_name="invoice.pdf",
            file_hash="abc123"
        )
        assert result.status == InvoiceStatus.EXTRACTED  # Default
        assert result.invoice is None  # Default
        assert result.requires_review is False  # Default
    
    def test_with_invoice(self):
        """Test creation with embedded invoice."""
        result = InvoiceExtractionResult(
            document_id="DOC-002",
            file_name="invoice.pdf",
            file_hash="def456",
            invoice=Invoice(
                invoice_number="INV-001",
                vendor_name="Test Vendor",
                total=Decimal("500.00")
            ),
            confidence=ExtractionConfidence(
                invoice_number=0.95,
                vendor_name=0.90,
                total=0.98
            )
        )
        assert result.invoice.invoice_number == "INV-001"
        assert result.confidence.invoice_number == 0.95
    
    def test_timestamps_default(self):
        """Test timestamps default to current time."""
        result = InvoiceExtractionResult(
            document_id="DOC-003",
            file_name="test.pdf",
            file_hash="xyz789"
        )
        assert result.created_at is not None
        assert result.updated_at is not None


# =============================================================================
# Purchase Order Model Tests
# =============================================================================

class TestPOStatus:
    """Tests for POStatus enum."""
    
    def test_all_statuses_exist(self):
        """Test all expected statuses are defined."""
        assert POStatus.OPEN.value == "open"
        assert POStatus.PARTIALLY_RECEIVED.value == "partially_received"
        assert POStatus.CLOSED.value == "closed"
        assert POStatus.CANCELLED.value == "cancelled"


class TestPOLineItem:
    """Tests for POLineItem model."""
    
    def test_creation(self):
        """Test creation with required fields."""
        item = POLineItem(
            line_number=1,
            description="Test Product",
            quantity=5,
            unit_price=Decimal("100.00"),
            amount=Decimal("500.00")
        )
        assert item.line_number == 1
        assert item.received_quantity == 0.0  # Default
    
    def test_validation_quantity_positive(self):
        """Test quantity must be positive."""
        with pytest.raises(ValidationError):
            POLineItem(
                line_number=1,
                description="Test",
                quantity=0,  # Must be > 0
                unit_price=Decimal("10.00"),
                amount=Decimal("0.00")
            )
    
    def test_validation_price_non_negative(self):
        """Test unit_price must be >= 0."""
        with pytest.raises(ValidationError):
            POLineItem(
                line_number=1,
                description="Test",
                quantity=1,
                unit_price=Decimal("-10.00"),  # Invalid
                amount=Decimal("10.00")
            )


class TestPurchaseOrder:
    """Tests for PurchaseOrder model."""
    
    @pytest.fixture
    def sample_line_item(self):
        """Create a sample line item."""
        return POLineItem(
            line_number=1,
            description="Widget",
            quantity=10,
            unit_price=Decimal("50.00"),
            amount=Decimal("500.00")
        )
    
    def test_minimal_creation(self, sample_line_item):
        """Test creation with required fields."""
        po = PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            vendor_name="Test Vendor",
            created_date=date(2026, 1, 1),
            line_items=[sample_line_item],
            subtotal=Decimal("500.00"),
            total_amount=Decimal("540.00")
        )
        assert po.status == POStatus.OPEN  # Default
        assert po.currency == "USD"  # Default
    
    def test_line_items_required(self):
        """Test at least one line item is required."""
        with pytest.raises(ValidationError):
            PurchaseOrder(
                po_number="PO-001",
                vendor_id="V001",
                vendor_name="Test",
                created_date=date.today(),
                line_items=[],  # min_length=1
                subtotal=Decimal("0"),
                total_amount=Decimal("0")
            )
    
    def test_is_fully_received_property(self, sample_line_item):
        """Test is_fully_received computed property."""
        po = PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            vendor_name="Test",
            created_date=date.today(),
            line_items=[sample_line_item],
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00")
        )
        assert po.is_fully_received is False
        
        # Now set received_quantity to match ordered quantity
        po.line_items[0].received_quantity = 10
        assert po.is_fully_received is True
    
    def test_is_partially_received_property(self):
        """Test is_partially_received computed property."""
        item = POLineItem(
            line_number=1,
            description="Widget",
            quantity=10,
            unit_price=Decimal("50.00"),
            amount=Decimal("500.00"),
            received_quantity=5  # Partially received
        )
        po = PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            vendor_name="Test",
            created_date=date.today(),
            line_items=[item],
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00")
        )
        assert po.is_partially_received is True
    
    def test_received_percentage_property(self):
        """Test received_percentage computed property."""
        item = POLineItem(
            line_number=1,
            description="Widget",
            quantity=10,
            unit_price=Decimal("50.00"),
            amount=Decimal("500.00"),
            received_quantity=2
        )
        po = PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            vendor_name="Test",
            created_date=date.today(),
            line_items=[item],
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00")
        )
        assert po.received_percentage == 20.0


# =============================================================================
# Vendor Model Tests
# =============================================================================

class TestVendorStatus:
    """Tests for VendorStatus enum."""
    
    def test_all_statuses(self):
        """Test all vendor statuses."""
        assert VendorStatus.ACTIVE.value == "active"
        assert VendorStatus.INACTIVE.value == "inactive"
        assert VendorStatus.SUSPENDED.value == "suspended"
        assert VendorStatus.BLOCKED.value == "blocked"


class TestFraudFlagType:
    """Tests for FraudFlagType enum."""
    
    def test_fraud_flag_types(self):
        """Test fraud flag type values."""
        assert FraudFlagType.DUPLICATE_INVOICE.value == "duplicate_invoice"
        assert FraudFlagType.BANK_ACCOUNT_CHANGE.value == "bank_account_change"
        assert FraudFlagType.PRICE_ANOMALY.value == "price_anomaly"


class TestPaymentRecord:
    """Tests for PaymentRecord model."""
    
    def test_creation(self):
        """Test payment record creation."""
        record = PaymentRecord(
            payment_id="PAY-001",
            invoice_number="INV-001",
            amount=Decimal("5000.00"),
            payment_date=date(2026, 1, 15),
            days_to_pay=28
        )
        assert record.currency == "USD"  # Default
        assert record.amount == Decimal("5000.00")
    
    def test_validation_amount_positive(self):
        """Test amount must be positive."""
        with pytest.raises(ValidationError):
            PaymentRecord(
                payment_id="PAY-001",
                invoice_number="INV-001",
                amount=Decimal("0.00"),  # Must be > 0
                payment_date=date.today(),
                days_to_pay=0
            )


class TestFraudFlag:
    """Tests for FraudFlag model."""
    
    def test_creation(self):
        """Test fraud flag creation."""
        flag = FraudFlag(
            flag_id="FLAG-001",
            flag_type=FraudFlagType.PRICE_ANOMALY,
            severity="medium",
            description="Price 50% above average"
        )
        assert flag.resolved is False  # Default
        assert flag.flagged_date is not None


class TestVendorRiskProfile:
    """Tests for VendorRiskProfile model."""
    
    def test_default_values(self):
        """Test default values."""
        profile = VendorRiskProfile()
        assert profile.risk_score == 0.0
        assert profile.payment_reliability_score == 1.0
        assert profile.fraud_risk_score == 0.0
        assert profile.total_invoices_processed == 0
    
    def test_validation_score_range(self):
        """Test score validation (0-1)."""
        with pytest.raises(ValidationError):
            VendorRiskProfile(risk_score=1.5)  # > 1.0


class TestVendor:
    """Tests for Vendor model."""
    
    def test_minimal_creation(self):
        """Test creation with required fields."""
        vendor = Vendor(
            vendor_id="V001",
            vendor_name="Test Vendor Inc",
            onboarded_date=date(2025, 1, 1)
        )
        assert vendor.status == VendorStatus.ACTIVE  # Default
        assert vendor.payment_terms == "Net 30"  # Default
        assert vendor.country == "US"  # Default
    
    def test_is_active_property(self):
        """Test is_active computed property."""
        vendor = Vendor(
            vendor_id="V001",
            vendor_name="Test",
            onboarded_date=date.today()
        )
        assert vendor.is_active is True
        
        vendor.status = VendorStatus.BLOCKED
        assert vendor.is_active is False
    
    def test_email_validation(self):
        """Test email validation."""
        vendor = Vendor(
            vendor_id="V001",
            vendor_name="Test",
            email="valid@email.com",
            onboarded_date=date.today()
        )
        assert vendor.email == "valid@email.com"
        
        with pytest.raises(ValidationError):
            Vendor(
                vendor_id="V001",
                vendor_name="Test",
                email="invalid-email",  # Not a valid email
                onboarded_date=date.today()
            )


# =============================================================================
# Matching Model Tests
# =============================================================================

class TestMatchType:
    """Tests for MatchType enum."""
    
    def test_all_types(self):
        """Test all match types."""
        assert MatchType.EXACT.value == "exact"
        assert MatchType.FUZZY.value == "fuzzy"
        assert MatchType.LINE_ITEM.value == "line_item"
        assert MatchType.MANUAL.value == "manual"
        assert MatchType.NO_MATCH.value == "no_match"


class TestDiscrepancy:
    """Tests for Discrepancy model."""
    
    def test_creation(self):
        """Test discrepancy creation."""
        disc = Discrepancy(
            discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
            severity=DiscrepancySeverity.MEDIUM,
            description="Price differs from PO"
        )
        assert disc.requires_approval is False  # Default
    
    def test_with_values(self):
        """Test discrepancy with comparison values."""
        disc = Discrepancy(
            discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
            severity=DiscrepancySeverity.HIGH,
            description="Quantity mismatch",
            line_number=1,
            invoice_value="15",
            po_value="10",
            difference="5",
            difference_percentage=50.0,
            requires_approval=True
        )
        assert disc.difference_percentage == 50.0
        assert disc.requires_approval is True


class TestLineItemMatch:
    """Tests for LineItemMatch model."""
    
    def test_creation(self):
        """Test line item match creation."""
        match = LineItemMatch(
            invoice_line_number=1,
            po_line_number=1,
            match_score=0.95,
            description_similarity=0.92,
            matched=True
        )
        assert match.discrepancies == []  # Default
    
    def test_unmatched_line(self):
        """Test unmatched line item."""
        match = LineItemMatch(
            invoice_line_number=2,
            po_line_number=None,  # Not matched to any PO line
            match_score=0.0,
            description_similarity=0.0,
            matched=False,
            discrepancies=[
                Discrepancy(
                    discrepancy_type=DiscrepancyType.EXTRA_LINE_ITEM,
                    severity=DiscrepancySeverity.HIGH,
                    description="Invoice contains extra line item"
                )
            ]
        )
        assert not match.matched
        assert len(match.discrepancies) == 1


class TestMatchingResult:
    """Tests for MatchingResult model."""
    
    def test_minimal_creation(self):
        """Test creation with required fields."""
        result = MatchingResult(
            matching_id="MATCH-001",
            invoice_id="INV-001",
            match_type=MatchType.NO_MATCH,
            match_score=0.0,
            matched=False
        )
        assert result.po_number is None
        assert result.discrepancies == []
    
    def test_exact_match(self):
        """Test exact match result."""
        result = MatchingResult(
            matching_id="MATCH-002",
            invoice_id="INV-002",
            po_number="PO-001",
            match_type=MatchType.EXACT,
            match_score=0.98,
            matched=True,
            vendor_match_score=1.0,
            amount_match_score=0.99,
            date_match_score=0.95,
            line_items_match_score=0.98
        )
        assert result.is_high_confidence_match is True
        assert result.is_acceptable_match is True
    
    def test_is_high_confidence_match_property(self):
        """Test is_high_confidence_match threshold."""
        # Below threshold
        result = MatchingResult(
            matching_id="MATCH-003",
            invoice_id="INV-003",
            match_type=MatchType.FUZZY,
            match_score=0.85,
            matched=True
        )
        assert result.is_high_confidence_match is False
        
        # Above threshold
        result.match_score = 0.91
        assert result.is_high_confidence_match is True
    
    def test_is_acceptable_match_with_critical_discrepancies(self):
        """Test acceptable match fails with critical discrepancies."""
        result = MatchingResult(
            matching_id="MATCH-004",
            invoice_id="INV-004",
            match_type=MatchType.FUZZY,
            match_score=0.90,
            matched=True,
            critical_discrepancies=1  # Has critical issue
        )
        assert result.is_acceptable_match is False
    
    def test_discrepancy_summary_property(self):
        """Test discrepancy_summary computed property."""
        result = MatchingResult(
            matching_id="MATCH-005",
            invoice_id="INV-005",
            match_type=MatchType.FUZZY,
            match_score=0.80,
            matched=True,
            discrepancies=[
                Discrepancy(
                    discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                    severity=DiscrepancySeverity.LOW,
                    description="Minor price difference"
                ),
                Discrepancy(
                    discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                    severity=DiscrepancySeverity.MEDIUM,
                    description="Quantity differs"
                ),
                Discrepancy(
                    discrepancy_type=DiscrepancyType.AMOUNT_TOLERANCE_EXCEEDED,
                    severity=DiscrepancySeverity.HIGH,
                    description="Amount exceeds tolerance"
                )
            ]
        )
        summary = result.discrepancy_summary
        assert summary["low"] == 1
        assert summary["medium"] == 1
        assert summary["high"] == 1
        assert summary["critical"] == 0


# =============================================================================
# Risk Model Tests
# =============================================================================

class TestRiskLevel:
    """Tests for RiskLevel enum."""
    
    def test_all_levels(self):
        """Test all risk levels."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestRiskFlagType:
    """Tests for RiskFlagType enum."""
    
    def test_duplicate_types(self):
        """Test duplicate risk flag types."""
        assert RiskFlagType.DUPLICATE_EXACT.value == "duplicate_exact"
        assert RiskFlagType.DUPLICATE_NEAR.value == "duplicate_near"
        assert RiskFlagType.DUPLICATE_SIMILAR.value == "duplicate_similar"
    
    def test_vendor_types(self):
        """Test vendor risk flag types."""
        assert RiskFlagType.VENDOR_NEW.value == "vendor_new"
        assert RiskFlagType.VENDOR_BLOCKED.value == "vendor_blocked"
        assert RiskFlagType.VENDOR_BANK_CHANGE.value == "vendor_bank_change"


class TestRecommendedAction:
    """Tests for RecommendedAction enum."""
    
    def test_all_actions(self):
        """Test all recommended actions."""
        assert RecommendedAction.AUTO_APPROVE.value == "auto_approve"
        assert RecommendedAction.REVIEW.value == "review"
        assert RecommendedAction.MANAGER_APPROVAL.value == "manager_approval"
        assert RecommendedAction.INVESTIGATE.value == "investigate"
        assert RecommendedAction.REJECT.value == "reject"


class TestRiskFlag:
    """Tests for RiskFlag model."""
    
    def test_creation(self):
        """Test risk flag creation."""
        flag = RiskFlag(
            flag_type=RiskFlagType.PRICE_SPIKE,
            severity="high",
            description="Price 50% higher than average",
            confidence=0.88
        )
        assert flag.requires_action is True  # Default
    
    def test_with_evidence(self):
        """Test risk flag with evidence."""
        flag = RiskFlag(
            flag_type=RiskFlagType.DUPLICATE_NEAR,
            severity="critical",
            description="Near duplicate detected",
            confidence=0.95,
            evidence="Invoice INV-001 has same vendor and amount",
            related_invoice_id="INV-001",
            expected_value="Unique invoice",
            actual_value="Duplicate found"
        )
        assert flag.related_invoice_id == "INV-001"


class TestDuplicateInfo:
    """Tests for DuplicateInfo model."""
    
    def test_no_duplicate(self):
        """Test when no duplicate detected."""
        info = DuplicateInfo(
            is_duplicate=False,
            similarity_score=0.2
        )
        assert info.duplicate_invoice_id is None
    
    def test_with_duplicate(self):
        """Test when duplicate detected."""
        info = DuplicateInfo(
            is_duplicate=True,
            duplicate_type=RiskFlagType.DUPLICATE_EXACT,
            duplicate_invoice_id="INV-001",
            duplicate_invoice_number="INV-001",
            similarity_score=1.0,
            duplicate_processed_date=datetime.utcnow()
        )
        assert info.is_duplicate is True
        assert info.similarity_score == 1.0


class TestVendorRiskInfo:
    """Tests for VendorRiskInfo model."""
    
    def test_new_vendor(self):
        """Test new vendor risk info."""
        info = VendorRiskInfo(
            vendor_id="V001",
            vendor_name="New Vendor",
            vendor_risk_score=0.3,
            is_new_vendor=True,
            is_blocked=False
        )
        assert info.is_new_vendor is True
        assert info.total_invoices == 0  # Default
    
    def test_established_vendor(self):
        """Test established vendor with history."""
        info = VendorRiskInfo(
            vendor_id="V002",
            vendor_name="Established Vendor",
            vendor_risk_score=0.1,
            is_new_vendor=False,
            average_invoice_amount=Decimal("5000.00"),
            invoice_amount_std_dev=Decimal("500.00"),
            total_invoices=50,
            amount_z_score=1.5,
            is_amount_anomaly=False
        )
        assert info.total_invoices == 50


class TestPriceAnomalyInfo:
    """Tests for PriceAnomalyInfo model."""
    
    def test_normal_price(self):
        """Test item with normal price."""
        info = PriceAnomalyInfo(
            item_description="Widget",
            current_price=Decimal("100.00"),
            historical_average=Decimal("98.00"),
            historical_std_dev=Decimal("10.00"),
            price_z_score=0.2,
            is_anomaly=False,
            deviation_percentage=2.04
        )
        assert info.is_anomaly is False
    
    def test_anomalous_price(self):
        """Test item with anomalous price."""
        info = PriceAnomalyInfo(
            item_description="Widget",
            current_price=Decimal("200.00"),
            historical_average=Decimal("100.00"),
            historical_std_dev=Decimal("10.00"),
            price_z_score=10.0,
            is_anomaly=True,
            deviation_percentage=100.0
        )
        assert info.is_anomaly is True
        assert info.deviation_percentage == 100.0


class TestRiskAssessment:
    """Tests for RiskAssessment model."""
    
    def test_low_risk_creation(self):
        """Test low risk assessment creation."""
        assessment = RiskAssessment(
            assessment_id="RISK-001",
            invoice_id="INV-001",
            risk_level=RiskLevel.LOW,
            risk_score=0.15,
            recommended_action=RecommendedAction.AUTO_APPROVE,
            action_reason="All checks passed",
            requires_manual_review=False,
        )
        assert assessment.duplicate_risk_score == 0.0  # Default
        assert assessment.risk_flags == []
        assert assessment.critical_flags == 0
    
    def test_high_risk_with_flags(self):
        """Test high risk assessment with flags."""
        assessment = RiskAssessment(
            assessment_id="RISK-002",
            invoice_id="INV-002",
            risk_level=RiskLevel.HIGH,
            risk_score=0.75,
            duplicate_risk_score=0.0,
            vendor_risk_score=0.4,
            price_risk_score=0.8,
            risk_flags=[
                RiskFlag(
                    flag_type=RiskFlagType.PRICE_SPIKE,
                    severity="high",
                    description="Price anomaly detected",
                    confidence=0.90
                ),
                RiskFlag(
                    flag_type=RiskFlagType.VENDOR_NEW,
                    severity="medium",
                    description="First invoice from vendor",
                    confidence=1.0
                )
            ],
            critical_flags=0,
            high_flags=1,
            recommended_action=RecommendedAction.MANAGER_APPROVAL,
            action_reason="High price anomaly detected",
            requires_manual_review=True,
        )
        assert len(assessment.risk_flags) == 2
        assert assessment.high_flags == 1


# =============================================================================
# Serialization Tests
# =============================================================================

class TestModelSerialization:
    """Tests for model serialization/deserialization."""
    
    def test_invoice_round_trip(self):
        """Test Invoice serialization and deserialization."""
        original = Invoice(
            invoice_number="INV-001",
            vendor_name="Test Vendor",
            invoice_date=date(2026, 1, 15),
            total=Decimal("1500.00"),
            line_items=[
                InvoiceLineItem(
                    description="Item 1",
                    quantity=2,
                    unit_price=Decimal("750.00"),
                    amount=Decimal("1500.00")
                )
            ]
        )
        
        # Serialize
        data = original.model_dump(mode="json")
        
        # Deserialize
        restored = Invoice.model_validate(data)
        
        assert restored.invoice_number == original.invoice_number
        assert restored.invoice_date == original.invoice_date
        assert len(restored.line_items) == 1
    
    def test_purchase_order_round_trip(self):
        """Test PurchaseOrder serialization and deserialization."""
        original = PurchaseOrder(
            po_number="PO-001",
            vendor_id="V001",
            vendor_name="Test Vendor",
            created_date=date(2026, 1, 1),
            line_items=[
                POLineItem(
                    line_number=1,
                    description="Product A",
                    quantity=5,
                    unit_price=Decimal("100.00"),
                    amount=Decimal("500.00")
                )
            ],
            subtotal=Decimal("500.00"),
            total_amount=Decimal("540.00")
        )
        
        # Serialize
        data = original.model_dump(mode="json")
        
        # Deserialize
        restored = PurchaseOrder.model_validate(data)
        
        assert restored.po_number == original.po_number
        assert restored.total_amount == original.total_amount
    
    def test_matching_result_round_trip(self):
        """Test MatchingResult serialization and deserialization."""
        original = MatchingResult(
            matching_id="MATCH-001",
            invoice_id="INV-001",
            po_number="PO-001",
            match_type=MatchType.EXACT,
            match_score=0.95,
            matched=True,
            discrepancies=[
                Discrepancy(
                    discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                    severity=DiscrepancySeverity.LOW,
                    description="Minor price difference"
                )
            ]
        )
        
        # Serialize
        data = original.model_dump(mode="json")
        
        # Deserialize
        restored = MatchingResult.model_validate(data)
        
        assert restored.match_type == MatchType.EXACT
        assert len(restored.discrepancies) == 1
    
    def test_risk_assessment_round_trip(self):
        """Test RiskAssessment serialization and deserialization."""
        original = RiskAssessment(
            assessment_id="RISK-001",
            invoice_id="INV-001",
            risk_level=RiskLevel.MEDIUM,
            risk_score=0.45,
            risk_flags=[
                RiskFlag(
                    flag_type=RiskFlagType.VENDOR_NEW,
                    severity="low",
                    description="New vendor",
                    confidence=1.0
                )
            ],
            recommended_action=RecommendedAction.REVIEW,
            action_reason="New vendor requires review",
            requires_manual_review=True,
        )
        
        # Serialize
        data = original.model_dump(mode="json")
        
        # Deserialize
        restored = RiskAssessment.model_validate(data)
        
        assert restored.risk_level == RiskLevel.MEDIUM
        assert len(restored.risk_flags) == 1


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_decimal_precision(self):
        """Test Decimal handling in models."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Test",
            total=Decimal("0.01")  # Minimum meaningful amount
        )
        assert invoice.total == Decimal("0.01")
    
    def test_large_amounts(self):
        """Test large monetary amounts."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Test",
            total=Decimal("999999999.99")  # Large amount
        )
        assert invoice.total == Decimal("999999999.99")
    
    def test_empty_line_items_invoice(self):
        """Test invoice with empty line items list."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="Test",
            total=Decimal("1000.00"),
            line_items=[]
        )
        assert invoice.line_items == []
    
    def test_long_description(self):
        """Test handling of long descriptions."""
        long_desc = "A" * 1000
        item = InvoiceLineItem(description=long_desc)
        assert len(item.description) == 1000
    
    def test_special_characters_in_strings(self):
        """Test special characters in string fields."""
        invoice = Invoice(
            invoice_number="INV-2026/01-001",
            vendor_name="Test & Co., Ltd. (UK)",
            total=Decimal("100.00")
        )
        assert "&" in invoice.vendor_name
        assert "/" in invoice.invoice_number
    
    def test_unicode_in_strings(self):
        """Test unicode characters in strings."""
        invoice = Invoice(
            invoice_number="INV-001",
            vendor_name="测试供应商 日本語 émojis 🎉",
            total=Decimal("100.00")
        )
        assert "测试" in invoice.vendor_name
        assert "🎉" in invoice.vendor_name
    
    def test_confidence_boundary_values(self):
        """Test confidence at exact boundaries."""
        # Exactly 0.0
        conf = ExtractionConfidence(invoice_number=0.0)
        assert conf.invoice_number == 0.0
        
        # Exactly 1.0
        conf = ExtractionConfidence(invoice_number=1.0)
        assert conf.invoice_number == 1.0
    
    def test_zero_quantity_received(self):
        """Test PO with zero received quantity."""
        item = POLineItem(
            line_number=1,
            description="Test",
            quantity=10,
            unit_price=Decimal("100.00"),
            amount=Decimal("1000.00"),
            received_quantity=0.0
        )
        assert item.received_quantity == 0.0
