"""
SmartAP - Intelligent Invoice & Accounts Payable Automation Hub

Phase 1: Core Intake Engine
- PDF upload and OCR processing
- AI-powered invoice data extraction
- Confidence scoring and validation
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    # Ensure directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.processed_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.signed_dir).mkdir(parents=True, exist_ok=True)  # eSign directory
    
    print(f"🚀 SmartAP {settings.app_version} starting...")
    print(f"📁 Upload directory: {settings.upload_dir}")
    print(f"🤖 AI Provider: {settings.ai_provider}")
    print(f"🔧 Model: {settings.model_id}")
    
    # Start ERP sync scheduler if enabled
    if settings.erp_sync_enabled:
        try:
            from .services.erp_sync_service import start_erp_sync_service
            start_erp_sync_service()
            print(f"✅ ERP sync scheduler started")
        except Exception as e:
            print(f"⚠️ Failed to start ERP sync scheduler: {str(e)}")
    
    yield
    
    # Stop ERP sync scheduler on shutdown
    if settings.erp_sync_enabled:
        try:
            from .services.erp_sync_service import stop_erp_sync_service
            stop_erp_sync_service()
            print("🛑 ERP sync scheduler stopped")
        except Exception as e:
            print(f"⚠️ Failed to stop ERP sync scheduler: {str(e)}")
    
    print("👋 SmartAP shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="SmartAP API",
        description=(
            "**Intelligent Invoice & Accounts Payable Automation Hub**\n\n"
            "SmartAP provides AI-powered invoice processing with multi-agent orchestration:\n\n"
            "**Features:**\n"
            "- 📄 PDF invoice upload and extraction\n"
            "- 🎯 Intelligent PO matching with AI assistance\n"
            "- ⚠️ Risk assessment and fraud detection\n"
            "- 🔀 Multi-agent workflow orchestration\n"
            "- ✅ Automated approval decisions\n\n"
            "**Phases:**\n"
            "- Phase 1: Core Intake Engine (PDF upload, OCR, AI extraction)\n"
            "- Phase 2: Multi-Agent Reasoning System (PO matching, risk detection, orchestration)\n\n"
            "**Processing Flow:**\n"
            "1. Upload invoice PDF\n"
            "2. AI extracts structured data\n"
            "3. Match to purchase order\n"
            "4. Assess risk (duplicates, vendor, price)\n"
            "5. Make approval decision\n\n"
            "Use the `/process` endpoint for complete orchestrated workflows."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "invoices",
                "description": "Invoice processing operations including upload, matching, risk assessment, and orchestration.",
            },
            {
                "name": "esign",
                "description": "Electronic signature operations for high-value invoice approvals.",
            },
            {
                "name": "ERP Integration",
                "description": "ERP system integration for vendor sync, purchase order import, and invoice export.",
            },
            {
                "name": "health",
                "description": "Health check and system status endpoints.",
            },
        ],
    )
    
    # Configure CORS for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router)
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
