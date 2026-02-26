"""
Price Anomaly Detector

Detects unusual pricing patterns and anomalies.
"""

from typing import List, Optional, Tuple
from statistics import mean, stdev
from decimal import Decimal

from ..models import Invoice, InvoiceLineItem, PriceAnomalyInfo
from ..db.repositories import InvoiceRepository


class PriceAnomalyDetector:
    """Service for detecting price anomalies."""
    
    # Thresholds
    STANDARD_DEVIATIONS_THRESHOLD = 2.0  # Price must be 2 std devs from mean
    MIN_HISTORICAL_INVOICES = 2          # Need at least 2 invoices for comparison
    SIGNIFICANT_AMOUNT_THRESHOLD = 1000.00  # Only flag if amount is significant
    
    # Price change thresholds
    MINOR_INCREASE = 0.15   # 15% increase
    MAJOR_INCREASE = 0.30   # 30% increase
    CRITICAL_INCREASE = 0.50  # 50% increase
    
    def __init__(self, invoice_repo: InvoiceRepository, settings: dict | None = None):
        self.invoice_repo = invoice_repo
        if settings:
            self.STANDARD_DEVIATIONS_THRESHOLD = settings.get("price_std_dev_threshold", self.STANDARD_DEVIATIONS_THRESHOLD)
            self.MIN_HISTORICAL_INVOICES = settings.get("price_min_historical_invoices", self.MIN_HISTORICAL_INVOICES)
            self.SIGNIFICANT_AMOUNT_THRESHOLD = settings.get("price_significant_amount", self.SIGNIFICANT_AMOUNT_THRESHOLD)
            self.MINOR_INCREASE = settings.get("price_minor_increase", self.MINOR_INCREASE)
            self.MAJOR_INCREASE = settings.get("price_major_increase", self.MAJOR_INCREASE)
            self.CRITICAL_INCREASE = settings.get("price_critical_increase", self.CRITICAL_INCREASE)
    
    async def detect_price_anomalies(
        self,
        invoice: Invoice,
        vendor_name: str,
        exclude_document_id: Optional[str] = None,
    ) -> Tuple[float, Optional[PriceAnomalyInfo]]:
        """
        Detect price anomalies by comparing to historical invoices.
        
        Args:
            invoice: Invoice being assessed
            vendor_name: Vendor name for historical lookup
            exclude_document_id: If set, exclude this document from the
                historical baseline so the invoice doesn't inflate its own stats
        
        Returns:
            Tuple of (risk_score, anomaly_info)
        """
        # Get historical invoices from same vendor
        historical_invoices = await self.invoice_repo.search_by_vendor(
            vendor_name,
            limit=50
        )
        
        # Filter to only successful extractions
        # Exclude the current invoice so it doesn't bias its own baseline
        def _get_total(data: dict) -> float:
            """Extract total from invoice_data, trying 'total' then 'total_amount'."""
            raw = data.get("total", data.get("total_amount", 0))
            try:
                return float(raw)
            except (TypeError, ValueError):
                return 0.0

        valid_invoices = [
            inv for inv in historical_invoices
            if inv.invoice_data and _get_total(inv.invoice_data) > 0
            and (not exclude_document_id or inv.document_id != exclude_document_id)
        ]
        
        # Need minimum historical data
        if len(valid_invoices) < self.MIN_HISTORICAL_INVOICES:
            return 0.0, None
        
        # Extract historical amounts
        historical_amounts = [_get_total(inv.invoice_data) for inv in valid_invoices]
        
        # Calculate statistics
        avg_amount = mean(historical_amounts)
        
        if len(historical_amounts) > 1:
            std_dev = stdev(historical_amounts)
        else:
            std_dev = 0.0
        
        # Calculate how many standard deviations away
        if std_dev > 0:
            z_score = (float(invoice.total) - avg_amount) / std_dev
        else:
            z_score = 0.0
        
        # Check if this is an anomaly
        # Primary: z-score based (reliable with larger samples)
        is_anomaly = abs(z_score) >= self.STANDARD_DEVIATIONS_THRESHOLD
        
        # Fallback: percentage-based for small sample sizes where stdev is unreliable
        current_total = float(invoice.total)
        if not is_anomaly and avg_amount > 0 and len(historical_amounts) < 5:
            pct_from_mean = abs(current_total - avg_amount) / avg_amount
            if pct_from_mean >= self.MAJOR_INCREASE:
                is_anomaly = True
        
        if is_anomaly and current_total >= self.SIGNIFICANT_AMOUNT_THRESHOLD:
            # Calculate percentage difference
            pct_diff = (current_total - avg_amount) / avg_amount
            
            # Determine severity
            if abs(pct_diff) >= self.CRITICAL_INCREASE:
                risk_score = 1.0
            elif abs(pct_diff) >= self.MAJOR_INCREASE:
                risk_score = 0.70
            elif abs(pct_diff) >= self.MINOR_INCREASE:
                risk_score = 0.40
            else:
                risk_score = 0.20
            
            anomaly_info = PriceAnomalyInfo(
                item_description="Invoice Total",
                current_price=Decimal(str(invoice.total)),
                historical_average=Decimal(str(avg_amount)),
                historical_std_dev=Decimal(str(std_dev)),
                price_z_score=z_score,
                is_anomaly=True,
                deviation_percentage=pct_diff * 100,
            )
            
            return risk_score, anomaly_info
        
        return 0.0, None
    
    async def detect_line_item_anomalies(
        self,
        line_items: List[InvoiceLineItem],
        vendor_name: str
    ) -> List[dict]:
        """
        Detect anomalies in individual line items.
        
        Returns:
            List of anomaly details for each suspicious line item
        """
        anomalies = []
        
        for item in line_items:
            # Check for unusual unit price (very high or very low)
            if item.unit_price and item.quantity:
                # Unreasonably high unit price
                if item.unit_price > 10000:
                    anomalies.append({
                        "line_number": item.line_number,
                        "description": item.description,
                        "issue": "Very high unit price",
                        "unit_price": item.unit_price,
                        "risk": "high"
                    })
                
                # Unreasonably low unit price (potential error)
                elif item.unit_price < 0.01 and item.amount > 100:
                    anomalies.append({
                        "line_number": item.line_number,
                        "description": item.description,
                        "issue": "Suspiciously low unit price",
                        "unit_price": item.unit_price,
                        "risk": "medium"
                    })
                
                # Check for quantity anomalies
                if item.quantity > 10000:
                    anomalies.append({
                        "line_number": item.line_number,
                        "description": item.description,
                        "issue": "Very high quantity",
                        "quantity": item.quantity,
                        "risk": "medium"
                    })
        
        return anomalies
    
    def calculate_amount_risk(
        self,
        invoice_amount: float,
        typical_range_min: float = 0,
        typical_range_max: float = 100000
    ) -> float:
        """
        Calculate risk based on invoice amount.
        
        Very high or very low amounts relative to typical range.
        """
        # Amount way above typical range
        if invoice_amount > typical_range_max * 2:
            excess = (invoice_amount - typical_range_max) / typical_range_max
            return min(1.0, 0.30 + (excess * 0.20))
        
        # Amount below typical but not suspicious
        elif invoice_amount < typical_range_min * 0.5:
            return 0.10
        
        # Normal range
        return 0.0
