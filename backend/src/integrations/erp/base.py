"""
Base ERP Connector
Abstract base class defining the interface for all ERP integrations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ERPSystem(str, Enum):
    """Supported ERP systems"""
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAP = "sap"
    SAGE = "sage"
    NETSUITE = "netsuite"
    ORACLE = "oracle"
    MICROSOFT_DYNAMICS = "dynamics"


class SyncStatus(str, Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ERPEntity(str, Enum):
    """ERP entity types for sync"""
    VENDOR = "vendor"
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    PAYMENT = "payment"
    ACCOUNT = "account"
    TAX_CODE = "tax_code"


class ERPVendor:
    """Standardized vendor data model"""
    
    def __init__(
        self,
        external_id: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[Dict[str, str]] = None,
        tax_id: Optional[str] = None,
        payment_terms: Optional[str] = None,
        account_number: Optional[str] = None,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.external_id = external_id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address or {}
        self.tax_id = tax_id
        self.payment_terms = payment_terms
        self.account_number = account_number
        self.is_active = is_active
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "external_id": self.external_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "tax_id": self.tax_id,
            "payment_terms": self.payment_terms,
            "account_number": self.account_number,
            "is_active": self.is_active,
            "metadata": self.metadata
        }


class ERPPurchaseOrder:
    """Standardized purchase order data model"""
    
    def __init__(
        self,
        external_id: str,
        po_number: str,
        vendor_id: str,
        vendor_name: str,
        total_amount: float,
        currency: str = "USD",
        status: str = "open",
        created_date: Optional[datetime] = None,
        expected_date: Optional[datetime] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.external_id = external_id
        self.po_number = po_number
        self.vendor_id = vendor_id
        self.vendor_name = vendor_name
        self.total_amount = total_amount
        self.currency = currency
        self.status = status
        self.created_date = created_date
        self.expected_date = expected_date
        self.line_items = line_items or []
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "external_id": self.external_id,
            "po_number": self.po_number,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "status": self.status,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "expected_date": self.expected_date.isoformat() if self.expected_date else None,
            "line_items": self.line_items,
            "metadata": self.metadata
        }


class ERPInvoice:
    """Standardized invoice export model"""
    
    def __init__(
        self,
        invoice_number: str,
        vendor_id: str,
        vendor_name: str,
        invoice_date: datetime,
        due_date: datetime,
        total_amount: float,
        currency: str = "USD",
        tax_amount: Optional[float] = None,
        po_number: Optional[str] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.invoice_number = invoice_number
        self.vendor_id = vendor_id
        self.vendor_name = vendor_name
        self.invoice_date = invoice_date
        self.due_date = due_date
        self.total_amount = total_amount
        self.currency = currency
        self.tax_amount = tax_amount
        self.po_number = po_number
        self.line_items = line_items or []
        self.notes = notes
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "invoice_number": self.invoice_number,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "invoice_date": self.invoice_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "total_amount": self.total_amount,
            "currency": self.currency,
            "tax_amount": self.tax_amount,
            "po_number": self.po_number,
            "line_items": self.line_items,
            "notes": self.notes,
            "metadata": self.metadata
        }


class SyncResult:
    """Result of a sync operation"""
    
    def __init__(
        self,
        entity_type: ERPEntity,
        status: SyncStatus,
        total_count: int = 0,
        success_count: int = 0,
        error_count: int = 0,
        errors: Optional[List[str]] = None,
        data: Optional[List[Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        self.entity_type = entity_type
        self.status = status
        self.total_count = total_count
        self.success_count = success_count
        self.error_count = error_count
        self.errors = errors or []
        self.data = data or []
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entity_type": self.entity_type,
            "status": self.status,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at
                else None
            )
        }


class ERPConnector(ABC):
    """
    Abstract base class for ERP system integrations
    
    All ERP connectors must implement these methods to provide
    standardized bidirectional data sync with SmartAP.
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize connector with connection configuration
        
        Args:
            connection_config: Dictionary containing credentials and settings
        """
        self.config = connection_config
        self.system_name = self.__class__.__name__
        self.is_authenticated = False
        self.last_sync: Dict[ERPEntity, Optional[datetime]] = {
            entity: None for entity in ERPEntity
        }
        
    @property
    @abstractmethod
    def system_type(self) -> ERPSystem:
        """Return the ERP system type"""
        pass
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the ERP system
        
        Returns:
            bool: True if authentication successful, False otherwise
            
        Raises:
            Exception: If authentication fails
        """
        pass
        
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to ERP system
        
        Returns:
            Dictionary with connection status and metadata
        """
        pass
        
    @abstractmethod
    async def import_vendors(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import vendors/suppliers from ERP system
        
        Args:
            since: Only import vendors modified after this date
            limit: Maximum number of vendors to import
            
        Returns:
            SyncResult with imported vendor data
        """
        pass
        
    @abstractmethod
    async def import_purchase_orders(
        self,
        since: Optional[datetime] = None,
        status_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import purchase orders from ERP system
        
        Args:
            since: Only import POs created/modified after this date
            status_filter: Filter by PO status (e.g., "open", "closed")
            limit: Maximum number of POs to import
            
        Returns:
            SyncResult with imported PO data
        """
        pass
        
    @abstractmethod
    async def export_invoice(self, invoice: ERPInvoice) -> Dict[str, Any]:
        """
        Export approved invoice to ERP system
        
        Args:
            invoice: Invoice data to export
            
        Returns:
            Dictionary with export result including external_id
            
        Raises:
            Exception: If export fails
        """
        pass
        
    @abstractmethod
    async def sync_payment_status(self, external_invoice_id: str) -> Dict[str, Any]:
        """
        Sync payment status from ERP system
        
        Args:
            external_invoice_id: ERP system's invoice ID
            
        Returns:
            Dictionary with payment status and metadata
        """
        pass
        
    @abstractmethod
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Get chart of accounts from ERP system
        
        Returns:
            List of account dictionaries
        """
        pass
        
    @abstractmethod
    async def get_tax_codes(self) -> List[Dict[str, Any]]:
        """
        Get tax codes/rates from ERP system
        
        Returns:
            List of tax code dictionaries
        """
        pass
        
    async def close(self):
        """Clean up resources and close connections"""
        logger.info(f"Closing {self.system_name} connector")
        self.is_authenticated = False
        
    def _handle_rate_limit(self, retry_after: int):
        """
        Handle API rate limiting
        
        Args:
            retry_after: Seconds to wait before retry
        """
        logger.warning(
            f"{self.system_name} rate limit reached, waiting {retry_after}s"
        )
        # Implement exponential backoff or sleep
        
    def _log_sync_start(self, entity_type: ERPEntity):
        """Log sync operation start"""
        logger.info(f"Starting {entity_type} sync from {self.system_name}")
        
    def _log_sync_complete(self, result: SyncResult):
        """Log sync operation completion"""
        logger.info(
            f"Completed {result.entity_type} sync: "
            f"{result.success_count}/{result.total_count} successful, "
            f"{result.error_count} errors"
        )
        if result.errors:
            logger.error(f"Sync errors: {result.errors}")
            
    def __repr__(self) -> str:
        return f"<{self.system_name} authenticated={self.is_authenticated}>"
