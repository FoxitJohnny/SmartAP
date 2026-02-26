"""
SmartAP Test Fixtures Package

Provides organized test fixtures for database, models, invoices, and users.
Import fixtures from this package in conftest.py or individual tests.
"""

from .database import (
    TestDatabaseManager,
    override_get_session,
    create_test_tables,
    drop_test_tables,
)
from .models import (
    InvoiceFactory,
    VendorFactory,
    PurchaseOrderFactory,
    UserFactory,
    LineItemFactory,
)
from .invoices import (
    SAMPLE_INVOICES,
    create_sample_invoice,
    create_invoice_batch,
    create_invoice_with_line_items,
    INVOICE_PDF_CONTENT,
)
from .users import (
    SAMPLE_USERS,
    create_test_user,
    create_admin_user,
    create_auth_headers,
    create_admin_headers,
    create_reviewer_headers,
    create_approver_headers,
    TEST_PASSWORD,
)

__all__ = [
    # Database
    "TestDatabaseManager",
    "override_get_session",
    "create_test_tables",
    "drop_test_tables",
    # Model factories
    "InvoiceFactory",
    "VendorFactory",
    "PurchaseOrderFactory",
    "UserFactory",
    "LineItemFactory",
    # Invoice fixtures
    "SAMPLE_INVOICES",
    "create_sample_invoice",
    "create_invoice_batch",
    "create_invoice_with_line_items",
    "INVOICE_PDF_CONTENT",
    # User fixtures
    "SAMPLE_USERS",
    "create_test_user",
    "create_admin_user",
    "create_auth_headers",
    "create_admin_headers",
    "create_reviewer_headers",
    "create_approver_headers",
    "TEST_PASSWORD",
]
