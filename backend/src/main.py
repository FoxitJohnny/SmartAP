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
from .api import (
    router, 
    auth_router, 
    dashboard_router, 
    esign_router,
    erp_router,
    HAS_ESIGN,
    HAS_ERP,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    # Configure structured logging
    try:
        from .middleware.logging_middleware import configure_structured_logging
        configure_structured_logging(
            log_level=settings.log_level,
            json_mode=(settings.log_format == "json"),
        )
        print(f"📝 Logging configured: level={settings.log_level}, format={settings.log_format}")
    except Exception as e:
        print(f"⚠️ Failed to configure structured logging: {str(e)}")
    
    # Ensure directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.processed_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.signed_dir).mkdir(parents=True, exist_ok=True)  # eSign directory
    
    print(f"🚀 SmartAP {settings.app_version} starting...")
    print(f"📁 Upload directory: {settings.upload_dir}")
    print(f"🤖 AI Provider: {settings.ai_provider}")
    print(f"🔧 Model: {settings.model_id}")
    
    # Initialize database tables
    try:
        from .db.database import init_db, async_session_maker
        await init_db()
        
        # Seed demo data in development mode
        if settings.debug:
            try:
                from .db.seed_data import run_seed
                from .db.models import VendorDB
                from sqlalchemy import select
                
                async with async_session_maker() as session:
                    # Check if vendors already exist
                    result = await session.execute(select(VendorDB).limit(1))
                    if not result.scalar():
                        await run_seed(session)
                    else:
                        print("📊 Database already seeded, skipping...")
            except Exception as e:
                print(f"⚠️ Seed data loading skipped: {str(e)}")
                
    except Exception as e:
        print(f"⚠️ Failed to initialize database: {str(e)}")
    
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
            {
                "name": "authentication",
                "description": "User authentication, registration, and token management.",
            },
        ],
    )
    
    # Configure CORS for frontend integration
    # In production, set CORS_ORIGINS to specific domains
    settings = get_settings()
    cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
    cors_methods = settings.cors_allow_methods.split(",")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=cors_methods,
        allow_headers=settings.cors_allow_headers.split(",") if settings.cors_allow_headers != "*" else ["*"],
    )
    
    # Add rate limiting middleware
    try:
        from .middleware import RateLimitMiddleware, RateLimitConfig
        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                burst_limit=10,
            )
        )
        print("✅ Rate limiting enabled")
    except Exception as e:
        print(f"⚠️ Rate limiting disabled: {e}")
    
    # Add request logging middleware
    try:
        from .middleware import RequestLoggingMiddleware
        app.add_middleware(RequestLoggingMiddleware, enable_metrics=True)
        print("✅ Request logging middleware enabled")
    except Exception as e:
        print(f"⚠️ Request logging middleware disabled: {e}")
    
    # Include API routes
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    
    # Include optional routers if available
    if HAS_ESIGN and esign_router:
        app.include_router(esign_router)
        print("✅ eSign routes enabled")
    
    if HAS_ERP and erp_router:
        app.include_router(erp_router)
        print("✅ ERP routes enabled")
    
    # Add global exception handlers
    _setup_exception_handlers(app)
    
    return app


def _setup_exception_handlers(app: FastAPI):
    """Configure global exception handlers for standardized error responses."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    import traceback
    
    # Import custom exceptions (with fallback if utils not available)
    try:
        from .utils.errors import (
            SmartAPError,
            ValidationError as SmartAPValidationError,
            NotFoundError,
            AuthenticationError,
            AuthorizationError,
            ExternalServiceError,
            RateLimitError,
            CircuitBreakerOpenError,
        )
        HAS_CUSTOM_ERRORS = True
    except ImportError:
        HAS_CUSTOM_ERRORS = False
    
    if HAS_CUSTOM_ERRORS:
        @app.exception_handler(SmartAPError)
        async def smartap_error_handler(request: Request, exc: SmartAPError):
            """Handle all SmartAP custom exceptions."""
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error_code": exc.error_code,
                    "message": exc.message,
                    "detail": exc.detail,
                    "suggestions": exc.suggestions,
                    "path": str(request.url.path),
                }
            )
        
        @app.exception_handler(CircuitBreakerOpenError)
        async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenError):
            """Handle circuit breaker open errors with Retry-After header."""
            return JSONResponse(
                status_code=exc.status_code,
                headers={"Retry-After": str(exc.retry_after)},
                content={
                    "error_code": exc.error_code,
                    "message": exc.message,
                    "detail": exc.detail,
                    "suggestions": exc.suggestions,
                    "path": str(request.url.path),
                }
            )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions with generic error response."""
        settings = get_settings()
        
        # Log the full error in debug mode
        if settings.debug:
            traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "detail": str(exc) if settings.debug else None,
                "path": str(request.url.path),
            }
        )


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
