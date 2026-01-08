"""
Duplicate Invoice Detector

Detects duplicate invoices using multiple strategies.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from ..models import Invoice, DuplicateInfo
from ..db.repositories import InvoiceRepository


class DuplicateDetector:
    """Service for detecting duplicate invoices."""
    
    # Thresholds
    EXACT_DUPLICATE_DAYS = 90  # Look back 90 days for exact duplicates
    FUZZY_DUPLICATE_DAYS = 30  # Look back 30 days for fuzzy duplicates
    AMOUNT_TOLERANCE = 0.02    # 2% tolerance for amount matching
    
    def __init__(self, invoice_repo: InvoiceRepository):
        self.invoice_repo = invoice_repo
    
    async def detect_duplicates(
        self,
        invoice: Invoice
    ) -> Tuple[bool, Optional[DuplicateInfo]]:
        """
        Detect if an invoice is a duplicate.
        
        Checks:
        1. File hash (exact file duplicate)
        2. Invoice number + vendor
        3. Amount + vendor + date range (fuzzy)
        
        Returns:
            Tuple of (is_duplicate, duplicate_info)
        """
        # Check 1: Exact file hash match
        hash_duplicate = await self._check_hash_duplicate(invoice)
        if hash_duplicate:
            return True, hash_duplicate
        
        # Check 2: Invoice number + vendor match
        invoice_num_duplicate = await self._check_invoice_number_duplicate(invoice)
        if invoice_num_duplicate:
            return True, invoice_num_duplicate
        
        # Check 3: Fuzzy match (amount + vendor + date proximity)
        fuzzy_duplicate = await self._check_fuzzy_duplicate(invoice)
        if fuzzy_duplicate:
            return True, fuzzy_duplicate
        
        return False, None
    
    async def _check_hash_duplicate(
        self,
        invoice: Invoice
    ) -> Optional[DuplicateInfo]:
        """Check for exact file hash duplicate."""
        # Note: file_hash would need to be passed from the upload
        # This is a placeholder for the logic
        # In practice, we'd need to modify Invoice model or pass file_hash separately
        return None
    
    async def _check_invoice_number_duplicate(
        self,
        invoice: Invoice
    ) -> Optional[DuplicateInfo]:
        """Check for duplicate invoice number from same vendor."""
        # Search for invoices with same invoice number
        existing_invoices = await self.invoice_repo.search_by_vendor(
            invoice.vendor_name,
            limit=100
        )
        
        for existing in existing_invoices:
            # Skip if no invoice data
            if not existing.invoice_data:
                continue
            
            existing_inv_num = existing.invoice_data.get("invoice_number", "")
            
            # Exact invoice number match from same vendor
            if existing_inv_num == invoice.invoice_number:
                # Check date proximity (within 90 days)
                existing_date_str = existing.invoice_data.get("invoice_date")
                if existing_date_str:
                    try:
                        existing_date = datetime.fromisoformat(existing_date_str.replace("Z", "+00:00"))
                        days_diff = abs((invoice.invoice_date - existing_date).days)
                        
                        if days_diff <= self.EXACT_DUPLICATE_DAYS:
                            return DuplicateInfo(
                                is_duplicate=True,
                                duplicate_invoice_id=existing.document_id,
                                duplicate_invoice_number=existing_inv_num,
                                match_type="exact_invoice_number",
                                confidence_score=1.0,
                                days_apart=days_diff,
                            )
                    except (ValueError, AttributeError):
                        pass
        
        return None
    
    async def _check_fuzzy_duplicate(
        self,
        invoice: Invoice
    ) -> Optional[DuplicateInfo]:
        """Check for fuzzy duplicate (same amount, vendor, close date)."""
        # Search for invoices from same vendor
        existing_invoices = await self.invoice_repo.search_by_vendor(
            invoice.vendor_name,
            limit=100
        )
        
        for existing in existing_invoices:
            if not existing.invoice_data:
                continue
            
            # Check amount match (within tolerance)
            existing_amount = existing.invoice_data.get("total_amount", 0)
            if existing_amount == 0:
                continue
            
            amount_diff = abs(invoice.total_amount - existing_amount) / existing_amount
            
            if amount_diff <= self.AMOUNT_TOLERANCE:
                # Check date proximity (within 30 days)
                existing_date_str = existing.invoice_data.get("invoice_date")
                if existing_date_str:
                    try:
                        existing_date = datetime.fromisoformat(existing_date_str.replace("Z", "+00:00"))
                        days_diff = abs((invoice.invoice_date - existing_date).days)
                        
                        if days_diff <= self.FUZZY_DUPLICATE_DAYS:
                            # Calculate confidence based on amount match and date proximity
                            amount_score = 1.0 - (amount_diff / self.AMOUNT_TOLERANCE)
                            date_score = 1.0 - (days_diff / self.FUZZY_DUPLICATE_DAYS)
                            confidence = (amount_score * 0.6) + (date_score * 0.4)
                            
                            # Only flag if confidence is high enough
                            if confidence >= 0.75:
                                existing_inv_num = existing.invoice_data.get("invoice_number", "Unknown")
                                
                                return DuplicateInfo(
                                    is_duplicate=True,
                                    duplicate_invoice_id=existing.document_id,
                                    duplicate_invoice_number=existing_inv_num,
                                    match_type="fuzzy_amount_date",
                                    confidence_score=confidence,
                                    days_apart=days_diff,
                                    amount_difference=abs(invoice.total_amount - existing_amount),
                                )
                    except (ValueError, AttributeError):
                        pass
        
        return None
    
    async def get_duplicate_risk_score(
        self,
        invoice: Invoice
    ) -> float:
        """
        Calculate duplicate risk score (0.0 = no risk, 1.0 = definite duplicate).
        """
        is_duplicate, duplicate_info = await self.detect_duplicates(invoice)
        
        if is_duplicate and duplicate_info:
            return duplicate_info.confidence_score
        
        return 0.0
