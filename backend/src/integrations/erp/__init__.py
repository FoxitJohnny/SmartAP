"""
SmartAP ERP Integrations Package
Bidirectional connectors for popular ERP systems
"""

from .base import (
    ERPConnector,
    ERPSystem,
    ERPVendor,
    ERPPurchaseOrder,
    ERPInvoice,
    ERPEntity,
    SyncResult,
    SyncStatus,
)
from .quickbooks import QuickBooksConnector
from .xero import XeroConnector
from .sap import SAPConnector
from .netsuite import NetSuiteConnector

__all__ = [
    # Base classes
    "ERPConnector",
    "ERPSystem",
    "ERPVendor",
    "ERPPurchaseOrder",
    "ERPInvoice",
    "ERPEntity",
    "SyncResult",
    "SyncStatus",
    # Connectors
    "QuickBooksConnector",
    "XeroConnector",
    "SAPConnector",
    "NetSuiteConnector",
]