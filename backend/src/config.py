"""
SmartAP Configuration Module

Manages environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "SmartAP"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # AI Model Configuration
    # Using GitHub Models endpoint (free tier for development)
    ai_provider: str = Field(default="github", description="AI provider: 'github', 'openai', or 'azure'")
    github_token: Optional[str] = Field(default=None, description="GitHub PAT for GitHub Models")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    
    # Model settings
    model_id: str = Field(default="openai/gpt-4.1", description="Model ID for extraction")
    model_base_url: str = Field(default="https://models.github.ai/inference", description="Model API base URL")
    
    # Extraction settings
    extraction_confidence_threshold: float = Field(default=0.85, description="Minimum confidence for auto-approval")
    max_file_size_mb: int = Field(default=50, description="Maximum upload file size in MB")
    
    # Foxit API Configuration (placeholder)
    foxit_api_key: Optional[str] = Field(default=None, description="Foxit API key for OCR services")
    foxit_api_endpoint: Optional[str] = Field(default=None, description="Foxit API endpoint")
    
    # Foxit eSign Configuration (Phase 4.4)
    foxit_esign_api_key: str = Field(default="", description="Foxit eSign API key")
    foxit_esign_api_secret: str = Field(default="", description="Foxit eSign API secret")
    foxit_esign_base_url: str = Field(default="https://api.foxitsign.com/v2.0", description="Foxit eSign API base URL")
    foxit_esign_webhook_secret: str = Field(default="", description="Webhook signature verification secret")
    foxit_esign_callback_url: str = Field(default="", description="Webhook callback URL")
    
    # Approval Workflow Configuration (Phase 4.4)
    approval_level1_max: int = Field(default=100000, description="Level 1 max amount in cents ($1,000)")
    approval_level2_max: int = Field(default=500000, description="Level 2 max amount in cents ($5,000)")
    approval_esign_threshold: int = Field(default=500000, description="eSign threshold in cents ($5,000)")
    approval_timeout_hours: int = Field(default=72, description="Default approval timeout in hours")
    approval_auto_escalate: bool = Field(default=True, description="Auto-escalate on timeout")
    
    # eSign Threshold Configuration (Phase 4.2)
    esign_threshold_manager: float = Field(default=5000.0, description="Manager approval threshold")
    esign_threshold_senior: float = Field(default=25000.0, description="Senior manager approval threshold")
    esign_threshold_cfo: float = Field(default=100000.0, description="CFO approval threshold")
    
    # Archival Configuration (Phase 4.4)
    archival_storage_path: str = Field(default="./archival", description="Directory for archived documents")
    archival_retention_years: int = Field(default=7, description="Default retention period in years")
    archival_pdfa_version: str = Field(default="PDF/A-2b", description="PDF/A version for archival")
    archival_enable_cloud_backup: bool = Field(default=False, description="Enable cloud backup for archives")
    archival_cloud_provider: str = Field(default="aws", description="Cloud provider: 'aws', 'azure', 'gcp'")
    archival_cloud_bucket: Optional[str] = Field(default=None, description="Cloud storage bucket/container name")
    
    # PDF Sealing Configuration (Phase 4.4)
    pdf_seal_certificate_path: str = Field(default="config/archival_cert.p12", description="Certificate for PDF tamper seal")
    pdf_seal_certificate_password: str = Field(default="", description="Certificate password")
    pdf_seal_reason: str = Field(default="Document archived for compliance", description="Reason for sealing")
    pdf_seal_location: str = Field(default="SmartAP Archival System", description="Seal location")
    
    # eSign Storage
    signed_dir: str = Field(default="./signed", description="Directory for signed documents")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./smartap.db",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_pool_max_overflow: int = Field(default=10, description="Max overflow connections")
    database_pool_timeout: int = Field(default=30, description="Connection pool timeout in seconds")
    database_echo: bool = Field(default=False, description="Echo SQL queries (for debugging)")
    
    # Redis Cache Configuration
    redis_enabled: bool = Field(default=False, description="Enable Redis caching")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    cache_ttl_seconds: int = Field(default=3600, description="Default cache TTL in seconds")
    
    # Storage
    upload_dir: str = Field(default="./uploads", description="Directory for uploaded files")
    processed_dir: str = Field(default="./processed", description="Directory for processed files")
    
    # ERP Integration Configuration
    erp_sync_enabled: bool = Field(default=True, description="Enable ERP sync scheduler")
    erp_sync_interval_minutes: int = Field(default=60, description="Default sync interval for vendors")
    erp_po_sync_interval_minutes: int = Field(default=30, description="Sync interval for purchase orders")
    erp_payment_sync_interval_minutes: int = Field(default=15, description="Sync interval for payment status")
    erp_max_sync_retries: int = Field(default=3, description="Maximum sync retry attempts")
    erp_sync_batch_size: int = Field(default=100, description="Default batch size for sync operations")
    
    # QuickBooks Configuration
    quickbooks_client_id: Optional[str] = Field(default=None, description="QuickBooks OAuth client ID")
    quickbooks_client_secret: Optional[str] = Field(default=None, description="QuickBooks OAuth client secret")
    quickbooks_redirect_uri: Optional[str] = Field(default=None, description="QuickBooks OAuth redirect URI")
    
    # Xero Configuration
    xero_client_id: Optional[str] = Field(default=None, description="Xero OAuth client ID")
    xero_client_secret: Optional[str] = Field(default=None, description="Xero OAuth client secret")
    xero_redirect_uri: Optional[str] = Field(default=None, description="Xero OAuth redirect URI")
    
    # SAP Configuration
    sap_service_layer_url: Optional[str] = Field(default=None, description="SAP Service Layer URL")
    sap_verify_ssl: bool = Field(default=True, description="Verify SSL for SAP connections")
    
    # NetSuite Configuration
    netsuite_account_id: Optional[str] = Field(default=None, description="NetSuite account ID")
    netsuite_consumer_key: Optional[str] = Field(default=None, description="NetSuite OAuth consumer key")
    netsuite_consumer_secret: Optional[str] = Field(default=None, description="NetSuite OAuth consumer secret")
    netsuite_restlet_url: Optional[str] = Field(default=None, description="NetSuite RESTlet base URL")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    log_format: str = Field(default="json", description="Log format: json or text")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
