"""
Price Anomaly Detector

Detects unusual pricing patterns and anomalies.
"""

from typing import List, Optional, Tuple
from statistics import mean, stdev

from ..models import Invoice, InvoiceLineItem, PriceAnomalyInfo
from ..db.repositories import InvoiceRepository


class PriceAnomalyDetector:
    """Service for detecting price anomalies."""
    
    # Thresholds
    STANDARD_DEVIATIONS_THRESHOLD = 2.0  # Price must be 2 std devs from mean
    MIN_HISTORICAL_INVOICES = 3          # Need at least 3 invoices for comparison
    SIGNIFICANT_AMOUNT_THRESHOLD = 1000.00  # Only flag if amount is significant
    
    # Price change thresholds
    MINOR_INCREASE = 0.15   # 15% increase
    MAJOR_INCREASE = 0.30   # 30% increase
    CRITICAL_INCREASE = 0.50  # 50% increase
    
    def __init__(self, invoice_repo: InvoiceRepository):
        self.invoice_repo = invoice_repo
    
    async def detect_price_anomalies(
        self,
        invoice: Invoice,
        vendor_name: str
    ) -> Tuple[float, Optional[PriceAnomalyInfo]]:
        """
        Detect price anomalies by comparing to historical invoices.
        
        Returns:
            Tuple of (risk_score, anomaly_info)
        """
        # Get historical invoices from same vendor
        historical_invoices = await self.invoice_repo.search_by_vendor(
            vendor_name,
            limit=50
        )
        
        # Filter to only successful extractions
        valid_invoices = [
            inv for inv in historical_invoices
            if inv.invoice_data and inv.invoice_data.get("total_amount", 0) > 0
        ]
        
        # Need minimum historical data
        if len(valid_invoices) < self.MIN_HISTORICAL_INVOICES:
            return 0.0, None
        
        # Extract historical amounts
        historical_amounts = [
            float(inv.invoice_data.get("total_amount", 0))
            for inv in valid_invoices
        ]
        
        # Calculate statistics
        avg_amount = mean(historical_amounts)
        
        if len(historical_amounts) > 1:
            std_dev = stdev(historical_amounts)
        else:
            std_dev = 0.0
        
        # Calculate how many standard deviations away
        if std_dev > 0:
            z_score = (invoice.total_amount - avg_amount) / std_dev
        else:
            z_score = 0.0
        
        # Check if this is an anomaly
        is_anomaly = abs(z_score) >= self.STANDARD_DEVIATIONS_THRESHOLD
        
        if is_anomaly and invoice.total_amount >= self.SIGNIFICANT_AMOUNT_THRESHOLD:
            # Calculate percentage difference
            pct_diff = (invoice.total_amount - avg_amount) / avg_amount
            
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
                is_anomaly=True,
                current_amount=invoice.total_amount,
                average_amount=avg_amount,
                std_deviation=std_dev,
                z_score=z_score,
                percentage_difference=pct_diff,
                historical_invoice_count=len(historical_amounts),
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
