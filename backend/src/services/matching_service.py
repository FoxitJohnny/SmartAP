"""
PO Matching Service

Calculates match scores between invoices and purchase orders.
"""

from typing import List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from fuzzywuzzy import fuzz

from ..models import (
    Invoice,
    InvoiceLineItem,
    PurchaseOrder,
    POLineItem,
    LineItemMatch,
)


class MatchingService:
    """Service for calculating match scores between invoices and POs."""
    
    # Thresholds
    EXACT_MATCH_THRESHOLD = 0.95
    GOOD_MATCH_THRESHOLD = 0.85
    ACCEPTABLE_MATCH_THRESHOLD = 0.70
    
    # Amount tolerance (percentage)
    AMOUNT_TOLERANCE = 0.05  # 5%
    
    # Date tolerance (days)
    DATE_TOLERANCE_DAYS = 30
    
    @staticmethod
    def calculate_vendor_match_score(
        invoice_vendor: str,
        po_vendor_id: str,
        vendor_name_from_db: str
    ) -> float:
        """
        Calculate vendor match score.
        
        Returns:
            1.0 for exact match, 0.0-0.99 for fuzzy match, 0.0 for no match
        """
        # Normalize strings
        inv_vendor = invoice_vendor.strip().lower()
        po_vendor = vendor_name_from_db.strip().lower()
        
        # Exact match
        if inv_vendor == po_vendor:
            return 1.0
        
        # Fuzzy match using fuzzywuzzy
        ratio = fuzz.ratio(inv_vendor, po_vendor) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(inv_vendor, po_vendor) / 100.0
        partial_ratio = fuzz.partial_ratio(inv_vendor, po_vendor) / 100.0
        
        # Use the best score
        return max(ratio, token_sort_ratio, partial_ratio)
    
    @staticmethod
    def calculate_amount_match_score(
        invoice_amount: float,
        po_amount: float,
        tolerance: float = AMOUNT_TOLERANCE
    ) -> float:
        """
        Calculate amount match score with tolerance.
        
        Returns:
            1.0 for exact match, decreases as difference increases
        """
        if po_amount == 0:
            return 0.0
        
        difference = abs(invoice_amount - po_amount)
        percentage_diff = difference / po_amount
        
        # Exact match
        if percentage_diff == 0:
            return 1.0
        
        # Within tolerance
        if percentage_diff <= tolerance:
            # Linear decrease from 1.0 to 0.85 within tolerance
            return 1.0 - (percentage_diff / tolerance) * 0.15
        
        # Beyond tolerance - exponential decay
        # At 2x tolerance (10%), score = 0.50
        # At 3x tolerance (15%), score = 0.25
        excess = percentage_diff - tolerance
        score = 0.85 * (0.5 ** (excess / tolerance))
        
        return max(0.0, score)
    
    @staticmethod
    def calculate_date_match_score(
        invoice_date: datetime,
        po_date: datetime,
        tolerance_days: int = DATE_TOLERANCE_DAYS
    ) -> float:
        """
        Calculate date match score.
        
        Returns:
            1.0 if invoice is after PO within tolerance, decreases otherwise
        """
        days_diff = (invoice_date - po_date).days
        
        # Invoice should be after or on PO date
        if 0 <= days_diff <= tolerance_days:
            # Perfect if within 7 days, decreases linearly
            if days_diff <= 7:
                return 1.0
            else:
                return 1.0 - ((days_diff - 7) / (tolerance_days - 7)) * 0.20
        
        # Invoice before PO (suspicious)
        elif days_diff < 0:
            abs_diff = abs(days_diff)
            if abs_diff <= 3:  # Grace period for date entry errors
                return 0.80
            else:
                return max(0.0, 0.80 - (abs_diff / 30) * 0.80)
        
        # Invoice way after PO
        else:
            excess_days = days_diff - tolerance_days
            return max(0.0, 0.80 - (excess_days / 60) * 0.80)
    
    @staticmethod
    def match_line_items(
        invoice_items: List[InvoiceLineItem],
        po_items: List[POLineItem],
        *,
        amount_tolerance: float = 0.10,
        min_match_score: float = 0.60,
        matched_score_threshold: float = 0.70,
    ) -> Tuple[List[LineItemMatch], float]:
        """
        Match invoice line items to PO line items.
        
        Returns:
            Tuple of (matched_items, overall_score)
            If no line items on either side, returns 1.0 (neutral score)
        """
        # Handle empty line items case - don't penalize the match
        if not invoice_items or not po_items:
            return [], 1.0  # Neutral score when no line items to compare
        
        matches: List[LineItemMatch] = []
        total_invoice_amount = float(sum(item.amount or 0 for item in invoice_items))
        matched_amount = 0.0
        
        # Try to match each invoice item to a PO item
        for inv_idx, inv_item in enumerate(invoice_items):
            best_match = None
            best_score = 0.0
            best_po_item = None
            
            # Use index+1 if line_number is None
            inv_line_num = inv_item.line_number if inv_item.line_number is not None else (inv_idx + 1)
            
            for po_item in po_items:
                # Skip if already matched to this PO line
                if any(m.po_line_number == po_item.line_number for m in matches):
                    continue
                
                # Calculate description similarity
                desc_score = fuzz.token_sort_ratio(
                    inv_item.description.lower(),
                    po_item.description.lower()
                ) / 100.0
                
                # Calculate amount similarity
                amount_score = MatchingService.calculate_amount_match_score(
                    float(inv_item.amount or 0),
                    float(po_item.amount or 0),
                    tolerance=amount_tolerance
                )
                
                # Calculate quantity match
                quantity_score = 1.0 if inv_item.quantity == po_item.quantity else 0.8
                
                # Overall item score (weighted)
                item_score = (desc_score * 0.4) + (amount_score * 0.4) + (quantity_score * 0.2)
                
                if item_score > best_score:
                    best_score = item_score
                    best_po_item = po_item
                    best_match = LineItemMatch(
                        invoice_line_number=inv_line_num,
                        po_line_number=po_item.line_number,
                        match_score=item_score,
                        description_similarity=desc_score,
                        matched=item_score >= matched_score_threshold,
                    )
            
            if best_match and best_score >= min_match_score:
                matches.append(best_match)
                matched_amount += float(inv_item.amount or 0)
        
        # Calculate overall line items score
        if total_invoice_amount > 0:
            coverage_score = matched_amount / total_invoice_amount
        else:
            coverage_score = 0.0
        
        # Average match quality
        if matches:
            avg_quality = sum(m.description_similarity for m in matches) / len(matches)
        else:
            avg_quality = 0.0
        
        # Overall score combines coverage and quality
        overall_score = (coverage_score * 0.6) + (avg_quality * 0.4)
        
        return matches, overall_score
    
    @staticmethod
    def calculate_overall_match_score(
        vendor_score: float,
        amount_score: float,
        date_score: float,
        line_items_score: float,
        *,
        vendor_weight: float = 0.30,
        amount_weight: float = 0.30,
        date_weight: float = 0.10,
        line_items_weight: float = 0.30,
    ) -> float:
        """
        Calculate weighted overall match score.
        
        Weights:
            - Vendor: 30%
            - Amount: 30%
            - Line Items: 30%
            - Date: 10%
        """
        weight_sum = vendor_weight + amount_weight + date_weight + line_items_weight
        if weight_sum <= 0:
            # Safe fallback to previous defaults
            vendor_weight, amount_weight, line_items_weight, date_weight = 0.30, 0.30, 0.30, 0.10
            weight_sum = 1.0

        return (
            vendor_score * vendor_weight +
            amount_score * amount_weight +
            line_items_score * line_items_weight +
            date_score * date_weight
        ) / weight_sum
    
    @staticmethod
    def determine_match_quality(score: float) -> str:
        """Determine match quality from score."""
        if score >= MatchingService.EXACT_MATCH_THRESHOLD:
            return "exact"
        elif score >= MatchingService.GOOD_MATCH_THRESHOLD:
            return "good"
        elif score >= MatchingService.ACCEPTABLE_MATCH_THRESHOLD:
            return "acceptable"
        else:
            return "poor"
