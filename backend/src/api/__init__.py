# SmartAP API Routes
"""
API route aggregation with graceful fallbacks.

Attempts to load full routes, eSign, and ERP routes.
Falls back to simple routes if imports fail.
"""

import logging

logger = logging.getLogger(__name__)

# Core routers (always available)
from .routes_simple import router as routes_simple
from .dashboard_routes import router as dashboard_router
from ..auth import router as auth_router

# Track which routers are available
HAS_FULL_ROUTES = False
HAS_ESIGN = False
HAS_ERP = False
HAS_APPROVALS = False

# Full routes with agent integration
try:
    from .routes import router as full_router
    HAS_FULL_ROUTES = True
    logger.info("Full API routes loaded successfully")
except ImportError as e:
    logger.warning(f"Full routes not available: {e}")
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

# Use full router if available, otherwise fall back to simple
router = full_router if HAS_FULL_ROUTES else routes_simple

__all__ = [
    "router",
    "routes_simple",
    "dashboard_router",
    "auth_router",
    "full_router",
    "esign_router",
    "erp_router",
    "approval_router",
    "HAS_FULL_ROUTES",
    "HAS_ESIGN",
    "HAS_ERP",
    "HAS_APPROVALS",
]
