# SmartAP API Routes
# Use simplified routes for now to avoid complex import issues
from .routes_simple import router

# TODO: Re-enable these when agents are properly configured
# from .esign_routes import router as esign_router
# from .erp_routes import router as erp_router

# Include eSign routes
# router.include_router(esign_router, prefix="/esign", tags=["esign"])

# Include ERP routes
# router.include_router(erp_router, prefix="/erp", tags=["ERP Integration"])

__all__ = ["router"]
