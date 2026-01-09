# SmartAP Phase 2 Database Layer
from .database import (
    engine,
    async_session_maker,
    get_session,
    get_sync_session,
    SessionLocal,
    init_db,
)
from .models import (
    Base,
    InvoiceDB,
    PurchaseOrderDB,
    POLineItemDB,
    VendorDB,
    PaymentRecordDB,
    FraudFlagDB,
    MatchingResultDB,
    RiskAssessmentDB,
)
from .repositories import (
    InvoiceRepository,
    PurchaseOrderRepository,
    VendorRepository,
    MatchingRepository,
    RiskRepository,
)

# Alias for consistency
RiskAssessmentRepository = RiskRepository

__all__ = [
    # Database
    "engine",
    "async_session_maker",
    "get_session",
    "get_sync_session",
    "SessionLocal",
    "init_db",
    # Models
    "Base",
    "InvoiceDB",
    "PurchaseOrderDB",
    "POLineItemDB",
    "VendorDB",
    "PaymentRecordDB",
    "FraudFlagDB",
    "MatchingResultDB",
    "RiskAssessmentDB",
    # Repositories
    "InvoiceRepository",
    "PurchaseOrderRepository",
    "VendorRepository",
    "MatchingRepository",
    "RiskRepository",
    "RiskAssessmentRepository",
]
