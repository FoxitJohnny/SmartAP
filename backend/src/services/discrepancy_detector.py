"""
Discrepancy Detection Service

Identifies and categorizes discrepancies between invoices and POs.
"""

from typing import List
from datetime import datetime

from ..models import (
    Invoice,
    PurchaseOrder,
    LineItemMatch,
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity,
)


class DiscrepancyDetector:
    """Service for detecting discrepancies between invoices and POs."""
    
    # Thresholds
    AMOUNT_CRITICAL_THRESHOLD = 0.10  # 10% difference
    AMOUNT_MAJOR_THRESHOLD = 0.05     # 5% difference
    
    @staticmethod
    def detect_vendor_discrepancy(
        invoice: Invoice,
        po: PurchaseOrder,
        vendor_name_from_db: str,
        vendor_match_score: float
    ) -> List[Discrepancy]:
        """Detect vendor name discrepancies."""
        discrepancies = []
        
        if vendor_match_score < 0.95:
            # Determine severity based on score
            if vendor_match_score < 0.70:
                severity = DiscrepancySeverity.MAJOR
            else:
                severity = DiscrepancySeverity.MINOR
            
            discrepancies.append(Discrepancy(
                type=DiscrepancyType.VENDOR_MISMATCH,
                severity=severity,
                description=f"Vendor name mismatch: Invoice '{invoice.vendor_name}' vs PO '{vendor_name_from_db}'",
                invoice_value=invoice.vendor_name,
                po_value=vendor_name_from_db,
                difference=f"Match score: {vendor_match_score:.2%}",
            ))
        
        return discrepancies
    
    @staticmethod
    def detect_amount_discrepancy(
        invoice: Invoice,
        po: PurchaseOrder,
        amount_match_score: float
    ) -> List[Discrepancy]:
        """Detect amount discrepancies."""
        discrepancies = []
        
        difference = invoice.total_amount - po.total_amount
        if po.total_amount > 0:
            percentage_diff = abs(difference) / po.total_amount
        else:
            percentage_diff = 1.0
        
        if percentage_diff > 0.01:  # More than 1% difference
            # Determine severity
            if percentage_diff >= DiscrepancyDetector.AMOUNT_CRITICAL_THRESHOLD:
                severity = DiscrepancySeverity.CRITICAL
            elif percentage_diff >= DiscrepancyDetector.AMOUNT_MAJOR_THRESHOLD:
                severity = DiscrepancySeverity.MAJOR
            else:
                severity = DiscrepancySeverity.MINOR
            
            direction = "over" if difference > 0 else "under"
            
            discrepancies.append(Discrepancy(
                type=DiscrepancyType.AMOUNT_MISMATCH,
                severity=severity,
                description=f"Invoice amount is {direction} PO by ${abs(difference):.2f} ({percentage_diff:.1%})",
                invoice_value=f"${invoice.total_amount:.2f}",
                po_value=f"${po.total_amount:.2f}",
                difference=f"{direction.upper()}: ${abs(difference):.2f}",
            ))
        
        return discrepancies
    
    @staticmethod
    def detect_date_discrepancy(
        invoice: Invoice,
        po: PurchaseOrder,
        date_match_score: float
    ) -> List[Discrepancy]:
        """Detect date-related discrepancies."""
        discrepancies = []
        
        # Invoice date before PO date
        if invoice.invoice_date < po.created_date:
            days_before = (po.created_date - invoice.invoice_date).days
            severity = DiscrepancySeverity.MAJOR if days_before > 7 else DiscrepancySeverity.MINOR
            
            discrepancies.append(Discrepancy(
                type=DiscrepancyType.DATE_MISMATCH,
                severity=severity,
                description=f"Invoice dated {days_before} days before PO creation",
                invoice_value=invoice.invoice_date.strftime("%Y-%m-%d"),
                po_value=po.created_date.strftime("%Y-%m-%d"),
                difference=f"{days_before} days before PO",
            ))
        
        # Invoice dated way after expected delivery
        if po.expected_delivery and invoice.invoice_date > po.expected_delivery:
            days_after = (invoice.invoice_date - po.expected_delivery).days
            if days_after > 30:
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.DATE_MISMATCH,
                    severity=DiscrepancySeverity.MINOR,
                    description=f"Invoice dated {days_after} days after expected delivery",
                    invoice_value=invoice.invoice_date.strftime("%Y-%m-%d"),
                    po_value=po.expected_delivery.strftime("%Y-%m-%d"),
                    difference=f"{days_after} days late",
                ))
        
        return discrepancies
    
    @staticmethod
    def detect_line_item_discrepancies(
        invoice: Invoice,
        po: PurchaseOrder,
        line_matches: List[LineItemMatch],
        line_items_score: float
    ) -> List[Discrepancy]:
        """Detect line item discrepancies."""
        discrepancies = []
        
        # Unmatched invoice items
        matched_inv_lines = {m.invoice_line_number for m in line_matches}
        unmatched_inv_items = [
            item for item in invoice.line_items
            if item.line_number not in matched_inv_lines
        ]
        
        if unmatched_inv_items:
            total_unmatched = sum(item.amount for item in unmatched_inv_items)
            severity = DiscrepancySeverity.CRITICAL if total_unmatched > 1000 else DiscrepancySeverity.MAJOR
            
            discrepancies.append(Discrepancy(
                type=DiscrepancyType.LINE_ITEM_MISMATCH,
                severity=severity,
                description=f"{len(unmatched_inv_items)} invoice line item(s) not found in PO (${total_unmatched:.2f})",
                invoice_value=f"{len(unmatched_inv_items)} unmatched items",
                po_value="N/A",
                difference=f"${total_unmatched:.2f} unmatched",
            ))
        
        # Quantity mismatches
        for match in line_matches:
            if match.quantity_matched != match.quantity_expected:
                diff = match.quantity_matched - match.quantity_expected
                severity = DiscrepancySeverity.MAJOR if abs(diff) > match.quantity_expected * 0.1 else DiscrepancySeverity.MINOR
                
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.QUANTITY_MISMATCH,
                    severity=severity,
                    description=f"Line {match.invoice_line_number}: Quantity mismatch",
                    invoice_value=f"{match.quantity_matched}",
                    po_value=f"{match.quantity_expected}",
                    difference=f"{'Over' if diff > 0 else 'Under'} by {abs(diff)}",
                ))
        
        # Poor description matches
        for match in line_matches:
            if match.description_match_score < 0.80:
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.LINE_ITEM_MISMATCH,
                    severity=DiscrepancySeverity.MINOR,
                    description=f"Line {match.invoice_line_number}: Description mismatch (score: {match.description_match_score:.1%})",
                    invoice_value="See invoice",
                    po_value="See PO",
                    difference=f"Match score: {match.description_match_score:.1%}",
                ))
        
        return discrepancies
    
    @staticmethod
    def detect_payment_terms_discrepancy(
        invoice: Invoice,
        po: PurchaseOrder
    ) -> List[Discrepancy]:
        """Detect payment terms discrepancies."""
        discrepancies = []
        
        if invoice.payment_terms and po.payment_terms:
            if invoice.payment_terms.strip().lower() != po.payment_terms.strip().lower():
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.TERMS_MISMATCH,
                    severity=DiscrepancySeverity.MINOR,
                    description="Payment terms differ between invoice and PO",
                    invoice_value=invoice.payment_terms,
                    po_value=po.payment_terms,
                    difference="Terms mismatch",
                ))
        
        return discrepancies
    
    @staticmethod
    def detect_currency_discrepancy(
        invoice: Invoice,
        po: PurchaseOrder
    ) -> List[Discrepancy]:
        """Detect currency discrepancies."""
        discrepancies = []
        
        if invoice.currency.upper() != po.currency.upper():
            discrepancies.append(Discrepancy(
                type=DiscrepancyType.CURRENCY_MISMATCH,
                severity=DiscrepancySeverity.CRITICAL,
                description="Currency mismatch between invoice and PO",
                invoice_value=invoice.currency,
                po_value=po.currency,
                difference="Different currencies",
            ))
        
        return discrepancies
    
    @staticmethod
    def detect_all_discrepancies(
        invoice: Invoice,
        po: PurchaseOrder,
        vendor_name_from_db: str,
        vendor_match_score: float,
        amount_match_score: float,
        date_match_score: float,
        line_matches: List[LineItemMatch],
        line_items_score: float
    ) -> List[Discrepancy]:
        """Detect all discrepancies between invoice and PO."""
        all_discrepancies = []
        
        # Vendor
        all_discrepancies.extend(
            DiscrepancyDetector.detect_vendor_discrepancy(
                invoice, po, vendor_name_from_db, vendor_match_score
            )
        )
        
        # Amount
        all_discrepancies.extend(
            DiscrepancyDetector.detect_amount_discrepancy(
                invoice, po, amount_match_score
            )
        )
        
        # Date
        all_discrepancies.extend(
            DiscrepancyDetector.detect_date_discrepancy(
                invoice, po, date_match_score
            )
        )
        
        # Line items
        all_discrepancies.extend(
            DiscrepancyDetector.detect_line_item_discrepancies(
                invoice, po, line_matches, line_items_score
            )
        )
        
        # Payment terms
        all_discrepancies.extend(
            DiscrepancyDetector.detect_payment_terms_discrepancy(invoice, po)
        )
        
        # Currency
        all_discrepancies.extend(
            DiscrepancyDetector.detect_currency_discrepancy(invoice, po)
        )
        
        return all_discrepancies
