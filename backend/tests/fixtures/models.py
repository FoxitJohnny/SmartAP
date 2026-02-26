"""
Model Factories for Test Data Generation

Provides factory classes for creating test instances of all SmartAP models.
Uses factory pattern for flexible, composable test data creation.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import uuid4
import random
import string

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


def random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def random_decimal(min_val: float = 100.0, max_val: float = 10000.0) -> Decimal:
    """Generate a random decimal amount."""
    return Decimal(str(round(random.uniform(min_val, max_val), 2)))


class InvoiceFactory:
    """Factory for creating Invoice and InvoiceExtractionResult test data."""
    
    _counter = 0
    
    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"INV-{cls._counter:05d}"
    
    @classmethod
    def create(
        cls,
        invoice_number: Optional[str] = None,
        vendor_name: str = "Test Vendor Inc.",
        total: Optional[Decimal] = None,
        currency: str = "USD",
        invoice_date: Optional[date] = None,
        due_date: Optional[date] = None,
        po_number: Optional[str] = None,
        line_items: Optional[List[InvoiceLineItem]] = None,
        **kwargs,
    ) -> Invoice:
        """
        Create a test Invoice instance.
        
        Args:
            invoice_number: Invoice number (auto-generated if not provided)
            vendor_name: Name of the vendor
            total: Total invoice amount
            currency: Currency code
            invoice_date: Date of invoice
            due_date: Payment due date
            po_number: Associated PO number
            line_items: List of line items
            **kwargs: Additional Invoice attributes
        
        Returns:
            Invoice instance
        """
        today = date.today()
        
        if line_items is None:
            line_items = [LineItemFactory.create_invoice_line()]
        
        subtotal = sum(item.amount or Decimal("0") for item in line_items)
        tax = subtotal * Decimal("0.08")  # 8% tax
        
        return Invoice(
            invoice_number=invoice_number or cls._next_id(),
            vendor_name=vendor_name,
            invoice_date=invoice_date or today,
            due_date=due_date or (today + timedelta(days=30)),
            currency=currency,
            subtotal=subtotal,
            tax=tax,
            total=total or (subtotal + tax),
            po_number=po_number,
            line_items=line_items,
            **kwargs,
        )
    
    @classmethod
    def create_extraction_result(
        cls,
        document_id: Optional[str] = None,
        status: InvoiceStatus = InvoiceStatus.EXTRACTED,
        confidence: float = 0.95,
        requires_review: bool = False,
        invoice: Optional[Invoice] = None,
        **kwargs,
    ) -> InvoiceExtractionResult:
        """
        Create a test InvoiceExtractionResult.
        
        Args:
            document_id: Unique document ID
            status: Extraction status
            confidence: Overall confidence score
            requires_review: Whether manual review is needed
            invoice: Associated Invoice (created if not provided)
            **kwargs: Additional attributes
        
        Returns:
            InvoiceExtractionResult instance
        """
        doc_id = document_id or f"DOC-{uuid4().hex[:8].upper()}"
        
        return InvoiceExtractionResult(
            document_id=doc_id,
            file_name=f"{doc_id}.pdf",
            file_hash=f"sha256:{uuid4().hex}",
            status=status,
            invoice=invoice or cls.create(),
            confidence=ExtractionConfidence(
                overall=confidence,
                invoice_number=confidence,
                vendor_name=confidence,
                amounts=confidence,
                dates=confidence,
                line_items=confidence,
            ),
            requires_review=requires_review,
            ocr_applied=False,
            page_count=1,
            extraction_time_ms=random.randint(200, 800),
            **kwargs,
        )
    
    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[Invoice]:
        """Create multiple invoices."""
        return [cls.create(**kwargs) for _ in range(count)]


class VendorFactory:
    """Factory for creating Vendor test data."""
    
    _counter = 0
    _vendor_names = [
        "Acme Corporation",
        "Tech Solutions Ltd",
        "Global Supplies Inc",
        "Premier Services",
        "Quality Products Co",
        "Innovative Systems",
        "Reliable Partners",
        "Express Logistics",
    ]
    
    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"V{cls._counter:04d}"
    
    @classmethod
    def create(
        cls,
        vendor_id: Optional[str] = None,
        vendor_name: Optional[str] = None,
        status: VendorStatus = VendorStatus.ACTIVE,
        risk_score: float = 0.15,
        on_time_rate: float = 0.95,
        **kwargs,
    ) -> Vendor:
        """
        Create a test Vendor instance.
        
        Args:
            vendor_id: Vendor ID (auto-generated if not provided)
            vendor_name: Vendor name
            status: Vendor status
            risk_score: Risk assessment score (0-1)
            on_time_rate: On-time payment rate (0-1)
            **kwargs: Additional Vendor attributes
        
        Returns:
            Vendor instance
        """
        name = vendor_name or random.choice(cls._vendor_names)
        
        return Vendor(
            vendor_id=vendor_id or cls._next_id(),
            vendor_name=name,
            email=f"contact@{name.lower().replace(' ', '')}.com",
            status=status,
            payment_terms="Net 30",
            currency="USD",
            risk_profile=VendorRiskProfile(
                risk_score=risk_score,
                on_time_payment_rate=on_time_rate,
                invoice_count=random.randint(10, 200),
                avg_invoice_amount=random.uniform(500, 5000),
                max_invoice_amount=random.uniform(5000, 50000),
                has_fraud_history=risk_score > 0.7,
            ),
            onboarded_date=datetime.now() - timedelta(days=random.randint(30, 365)),
            **kwargs,
        )
    
    @classmethod
    def create_high_risk(cls, **kwargs) -> Vendor:
        """Create a high-risk vendor for testing."""
        return cls.create(
            risk_score=0.85,
            on_time_rate=0.60,
            status=VendorStatus.UNDER_REVIEW,
            **kwargs,
        )
    
    @classmethod
    def create_new_vendor(cls, **kwargs) -> Vendor:
        """Create a new vendor with limited history."""
        return cls.create(
            risk_score=0.50,  # Medium risk due to unknown history
            on_time_rate=0.0,  # No payment history
            status=VendorStatus.PENDING,
            **kwargs,
        )
    
    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[Vendor]:
        """Create multiple vendors."""
        return [cls.create(**kwargs) for _ in range(count)]


class PurchaseOrderFactory:
    """Factory for creating PurchaseOrder test data."""
    
    _counter = 0
    
    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"PO-{cls._counter:05d}"
    
    @classmethod
    def create(
        cls,
        po_number: Optional[str] = None,
        vendor_id: str = "V0001",
        total_amount: Optional[Decimal] = None,
        status: POStatus = POStatus.OPEN,
        line_items: Optional[List[POLineItem]] = None,
        **kwargs,
    ) -> PurchaseOrder:
        """
        Create a test PurchaseOrder instance.
        
        Args:
            po_number: PO number (auto-generated if not provided)
            vendor_id: Associated vendor ID
            total_amount: Total PO amount
            status: PO status
            line_items: List of PO line items
            **kwargs: Additional PurchaseOrder attributes
        
        Returns:
            PurchaseOrder instance
        """
        now = datetime.now()
        
        if line_items is None:
            line_items = [LineItemFactory.create_po_line()]
        
        calculated_total = sum(item.total for item in line_items)
        
        return PurchaseOrder(
            po_number=po_number or cls._next_id(),
            vendor_id=vendor_id,
            po_date=now - timedelta(days=random.randint(1, 30)),
            expected_delivery=now + timedelta(days=random.randint(7, 60)),
            total_amount=float(total_amount or calculated_total),
            currency="USD",
            status=status,
            payment_terms="Net 30",
            line_items=line_items,
            **kwargs,
        )
    
    @classmethod
    def create_with_vendor(cls, vendor: Vendor, **kwargs) -> PurchaseOrder:
        """Create a PO linked to a specific vendor."""
        return cls.create(vendor_id=vendor.vendor_id, **kwargs)
    
    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[PurchaseOrder]:
        """Create multiple POs."""
        return [cls.create(**kwargs) for _ in range(count)]


class LineItemFactory:
    """Factory for creating line item test data."""
    
    _invoice_items = [
        ("Office Supplies", Decimal("25.00")),
        ("Laptop Computer", Decimal("1200.00")),
        ("Software License", Decimal("499.99")),
        ("Consulting Services", Decimal("150.00")),
        ("Network Equipment", Decimal("850.00")),
        ("Printer Paper", Decimal("45.00")),
        ("External Monitor", Decimal("350.00")),
        ("Wireless Mouse", Decimal("29.99")),
    ]
    
    @classmethod
    def create_invoice_line(
        cls,
        description: Optional[str] = None,
        quantity: float = 1.0,
        unit_price: Optional[Decimal] = None,
        **kwargs,
    ) -> InvoiceLineItem:
        """Create a test InvoiceLineItem."""
        desc, default_price = random.choice(cls._invoice_items)
        price = unit_price or default_price
        
        return InvoiceLineItem(
            description=description or desc,
            quantity=quantity,
            unit_price=price,
            amount=price * Decimal(str(quantity)),
            **kwargs,
        )
    
    @classmethod
    def create_po_line(
        cls,
        line_number: int = 1,
        description: Optional[str] = None,
        quantity: int = 1,
        unit_price: Optional[Decimal] = None,
        **kwargs,
    ) -> POLineItem:
        """Create a test POLineItem."""
        desc, default_price = random.choice(cls._invoice_items)
        price = unit_price or default_price
        
        return POLineItem(
            line_number=line_number,
            description=description or desc,
            quantity=quantity,
            unit_price=price,
            total=price * Decimal(str(quantity)),
            **kwargs,
        )
    
    @classmethod
    def create_invoice_lines(cls, count: int = 3) -> List[InvoiceLineItem]:
        """Create multiple invoice line items."""
        return [cls.create_invoice_line(line_number=i+1) for i in range(count)]
    
    @classmethod
    def create_po_lines(cls, count: int = 3) -> List[POLineItem]:
        """Create multiple PO line items."""
        return [cls.create_po_line(line_number=i+1) for i in range(count)]


class UserFactory:
    """Factory for creating User test data."""
    
    _counter = 0
    
    @classmethod
    def _next_id(cls) -> int:
        cls._counter += 1
        return cls._counter
    
    @classmethod
    def create(
        cls,
        email: Optional[str] = None,
        name: str = "Test User",
        role: str = "user",
        is_active: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create test user data dictionary.
        
        Returns a dict since User model varies by auth implementation.
        """
        user_id = cls._next_id()
        
        return {
            "id": user_id,
            "email": email or f"user{user_id}@test.com",
            "name": name,
            "role": role,
            "is_active": is_active,
            "created_at": datetime.now(),
            **kwargs,
        }
    
    @classmethod
    def create_admin(cls, **kwargs) -> Dict[str, Any]:
        """Create an admin user."""
        return cls.create(
            name="Admin User",
            role="admin",
            **kwargs,
        )
    
    @classmethod
    def create_reviewer(cls, **kwargs) -> Dict[str, Any]:
        """Create a reviewer user."""
        return cls.create(
            name="Reviewer User",
            role="reviewer",
            **kwargs,
        )


class MatchingResultFactory:
    """Factory for creating MatchingResult test data."""
    
    @classmethod
    def create(
        cls,
        match_score: float = 0.95,
        match_type: MatchType = MatchType.EXACT,
        matched_po_number: Optional[str] = None,
        discrepancies: Optional[List[Dict]] = None,
        **kwargs,
    ) -> MatchingResult:
        """Create a test MatchingResult."""
        return MatchingResult(
            match_score=match_score,
            match_type=match_type,
            matched_po_number=matched_po_number or f"PO-{random_string(5)}",
            discrepancies=discrepancies or [],
            line_item_matches=[],
            confidence=match_score,
            **kwargs,
        )
    
    @classmethod
    def create_no_match(cls) -> MatchingResult:
        """Create a result indicating no match found."""
        return cls.create(
            match_score=0.0,
            match_type=MatchType.NONE,
            matched_po_number=None,
            discrepancies=[{"type": "no_match", "message": "No matching PO found"}],
        )
    
    @classmethod
    def create_fuzzy_match(cls, discrepancies: List[Dict] = None) -> MatchingResult:
        """Create a fuzzy match result."""
        return cls.create(
            match_score=0.75,
            match_type=MatchType.FUZZY,
            discrepancies=discrepancies or [
                {"type": "amount_mismatch", "expected": 1000.00, "actual": 1050.00}
            ],
        )


class RiskAssessmentFactory:
    """Factory for creating RiskAssessment test data."""
    
    @classmethod
    def create(
        cls,
        risk_level: RiskLevel = RiskLevel.LOW,
        risk_score: float = 0.15,
        risk_flags: Optional[List[str]] = None,
        **kwargs,
    ) -> RiskAssessment:
        """Create a test RiskAssessment."""
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_flags=risk_flags or [],
            vendor_risk_score=risk_score,
            amount_risk_score=0.1,
            timing_risk_score=0.1,
            pattern_risk_score=0.1,
            **kwargs,
        )
    
    @classmethod
    def create_high_risk(cls) -> RiskAssessment:
        """Create a high-risk assessment."""
        return cls.create(
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            risk_flags=[
                "new_vendor",
                "amount_exceeds_threshold",
                "rush_payment_requested",
            ],
        )
    
    @classmethod
    def create_critical_risk(cls) -> RiskAssessment:
        """Create a critical-risk assessment requiring immediate attention."""
        return cls.create(
            risk_level=RiskLevel.CRITICAL,
            risk_score=0.95,
            risk_flags=[
                "fraud_indicator_detected",
                "vendor_on_watchlist",
                "duplicate_invoice_suspected",
                "unusual_payment_terms",
            ],
        )
