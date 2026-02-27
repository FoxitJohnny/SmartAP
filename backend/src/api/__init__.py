# SmartAP API Routes
"""
API route aggregation with graceful fallbacks.

Attempts to load full routes, eSign, and ERP routes.
Falls back to simple routes if imports fail.
"""

import logging
import traceback

logger = logging.getLogger(__name__)

# Core routers (always available)
from .routes_simple import router as routes_simple
from .dashboard_routes import router as dashboard_router
from .settings_routes import router as settings_router
from .processing_routes import router as processing_router
from ..auth import router as auth_router

# Track which routers are available
HAS_FULL_ROUTES = False
HAS_ESIGN = False
HAS_ERP = False
HAS_APPROVALS = False
ROUTES_IMPORT_ERROR = None  # Stores the error if full routes fail to load

# Full routes with agent integration
try:
    from .routes import router as full_router
    HAS_FULL_ROUTES = True
    print("[OK] Full API routes loaded successfully (AI extraction, matching, risk assessment enabled)")
    logger.info("Full API routes loaded successfully")
except Exception as e:
    ROUTES_IMPORT_ERROR = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
    print(f"[ERROR] *** FULL ROUTES FAILED TO LOAD — running in DEGRADED mode (stub routes only) ***")
    print(f"[ERROR] Import error: {type(e).__name__}: {e}")
    print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
    print(f"[ERROR] Invoice upload will NOT process with AI. Fix the import error above.")
    logger.error(f"Full routes not available: {e}", exc_info=True)
    full_router = None

# eSign routes
try:
    from .esign_routes import router as esign_router
    HAS_ESIGN = True
    logger.info("eSign routes loaded successfully")
except ImportError as e:
    logger.warning(f"eSign routes not available: {e}")
    esign_router = None

# ERP routes
try:
    from .erp_routes import router as erp_router
    HAS_ERP = True
    logger.info("ERP routes loaded successfully")
except ImportError as e:
    logger.warning(f"ERP routes not available: {e}")
    erp_router = None

# Approval routes
try:
    from .approval_routes import router as approval_router
    HAS_APPROVALS = True
    logger.info("Approval routes loaded successfully")
except ImportError as e:
    logger.warning(f"Approval routes not available: {e}")
    approval_router = None

# Admin routes
try:
    from .admin_routes import router as admin_router
    HAS_ADMIN = True
    logger.info("Admin routes loaded successfully")
except ImportError as e:
    logger.warning(f"Admin routes not available: {e}")
    admin_router = None

# Use full router if available, otherwise fall back to simple
router = full_router if HAS_FULL_ROUTES else routes_simple

if not HAS_FULL_ROUTES:
    print("[WARN] *** Using STUB routes — invoice upload will NOT use AI processing ***")
    print("[WARN] Check the import errors above and ensure all dependencies are installed (pip install -r requirements.txt --pre)")

__all__ = [
    "router",
    "routes_simple",
    "dashboard_router",
    "settings_router",
    "processing_router",
    "auth_router",
    "full_router",
    "esign_router",
    "erp_router",
    "approval_router",
    "admin_router",
    "HAS_FULL_ROUTES",
    "HAS_ESIGN",
    "HAS_ERP",
    "HAS_APPROVALS",
    "HAS_ADMIN",
    "ROUTES_IMPORT_ERROR",
]
