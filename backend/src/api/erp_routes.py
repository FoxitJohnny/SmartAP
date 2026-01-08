"""
ERP Integration API Routes

Provides REST API endpoints for managing ERP connections, triggering sync operations,
viewing sync logs, and managing field mappings.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..database import get_db
from ..models.erp import (
    ERPConnection,
    ERPSyncLog,
    ERPFieldMapping,
    ERPVendorMapping,
    ERPInvoiceMapping,
    ERPSystemType,
    ERPConnectionStatus,
    SyncStatus,
    ERPEntityType,
)
from ..integrations.erp.base import ERPConnector, SyncResult
from ..integrations.erp.quickbooks import QuickBooksConnector
from ..integrations.erp.xero import XeroConnector
from ..integrations.erp.sap import SAPConnector
from ..auth import get_current_user
from ..models.users import User

router = APIRouter(prefix="/erp", tags=["ERP Integration"])


# Pydantic schemas for request/response validation
from pydantic import BaseModel, Field


class ERPConnectionCreate(BaseModel):
    """Schema for creating ERP connection"""
    name: str = Field(..., min_length=1, max_length=255)
    system_type: ERPSystemType
    credentials: Dict[str, Any]
    tenant_id: Optional[str] = None
    company_db: Optional[str] = None
    api_url: Optional[str] = None
    auto_sync_enabled: bool = True
    sync_interval_minutes: int = Field(default=60, ge=5, le=1440)


class ERPConnectionUpdate(BaseModel):
    """Schema for updating ERP connection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    credentials: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None
    company_db: Optional[str] = None
    api_url: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)


class ERPConnectionResponse(BaseModel):
    """Schema for ERP connection response"""
    id: UUID
    name: str
    system_type: ERPSystemType
    status: ERPConnectionStatus
    tenant_id: Optional[str]
    company_db: Optional[str]
    api_url: Optional[str]
    last_connected_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    connection_error: Optional[str]
    auto_sync_enabled: bool
    sync_interval_minutes: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    """Schema for triggering sync operation"""
    since: Optional[datetime] = None
    status_filter: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)


class SyncResponse(BaseModel):
    """Schema for sync operation response"""
    sync_log_id: UUID
    status: SyncStatus
    started_at: datetime


class ERPSyncLogResponse(BaseModel):
    """Schema for sync log response"""
    id: UUID
    connection_id: UUID
    entity_type: ERPEntityType
    sync_direction: str
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    total_count: int
    success_count: int
    error_count: int
    errors: Optional[List[str]]
    error_message: Optional[str]
    sync_params: Optional[Dict[str, Any]]
    triggered_by: str

    class Config:
        from_attributes = True


class ERPFieldMappingCreate(BaseModel):
    """Schema for creating field mapping"""
    entity_type: ERPEntityType
    smartap_field: str
    erp_field: str
    transformation_rule: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = False
    validation_regex: Optional[str] = None
    description: Optional[str] = None


class ERPFieldMappingUpdate(BaseModel):
    """Schema for updating field mapping"""
    smartap_field: Optional[str] = None
    erp_field: Optional[str] = None
    transformation_rule: Optional[str] = None
    default_value: Optional[str] = None
    is_required: Optional[bool] = None
    validation_regex: Optional[str] = None
    description: Optional[str] = None


class ERPFieldMappingResponse(BaseModel):
    """Schema for field mapping response"""
    id: UUID
    connection_id: UUID
    entity_type: ERPEntityType
    smartap_field: str
    erp_field: str
    transformation_rule: Optional[str]
    default_value: Optional[str]
    is_required: bool
    validation_regex: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceExportRequest(BaseModel):
    """Schema for exporting invoice to ERP"""
    connection_id: UUID


class InvoiceExportResponse(BaseModel):
    """Schema for invoice export response"""
    success: bool
    external_id: Optional[str]
    external_number: Optional[str]
    exported_at: datetime
    error_message: Optional[str] = None


# Dependency: Get ERP connector instance based on connection
def get_erp_connector(
    connection: ERPConnection,
    db: Session = Depends(get_db)
) -> ERPConnector:
    """Factory function to create appropriate ERP connector instance"""
    
    credentials = connection.credentials or {}
    
    if connection.system_type == ERPSystemType.QUICKBOOKS:
        return QuickBooksConnector(
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            realm_id=credentials.get("realm_id"),
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            token_expires_at=credentials.get("token_expires_at")
        )
    
    elif connection.system_type == ERPSystemType.XERO:
        return XeroConnector(
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            tenant_id=connection.tenant_id or credentials.get("tenant_id"),
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            token_expires_at=credentials.get("token_expires_at")
        )
    
    elif connection.system_type == ERPSystemType.SAP:
        return SAPConnector(
            service_layer_url=connection.api_url or credentials.get("service_layer_url"),
            company_db=connection.company_db or credentials.get("company_db"),
            username=credentials.get("username"),
            password=credentials.get("password")
        )
    
    elif connection.system_type == ERPSystemType.NETSUITE:
        from ..integrations.erp.netsuite import NetSuiteConnector
        return NetSuiteConnector(
            account_id=credentials.get("account_id"),
            consumer_key=credentials.get("consumer_key"),
            consumer_secret=credentials.get("consumer_secret"),
            token_id=credentials.get("token_id"),
            token_secret=credentials.get("token_secret"),
            restlet_url=connection.api_url or credentials.get("restlet_url"),
            realm=credentials.get("realm")
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported ERP system type: {connection.system_type}"
        )


# ==================== Connection Management ====================

@router.post("/connections", response_model=ERPConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_erp_connection(
    connection_data: ERPConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new ERP connection"""
    
    # Check for duplicate connection name
    existing = db.query(ERPConnection).filter(
        ERPConnection.name == connection_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection with name '{connection_data.name}' already exists"
        )
    
    # Create connection
    connection = ERPConnection(
        name=connection_data.name,
        system_type=connection_data.system_type,
        credentials=connection_data.credentials,
        tenant_id=connection_data.tenant_id,
        company_db=connection_data.company_db,
        api_url=connection_data.api_url,
        auto_sync_enabled=connection_data.auto_sync_enabled,
        sync_interval_minutes=connection_data.sync_interval_minutes,
        status=ERPConnectionStatus.PENDING,
        created_by=current_user.email
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    return connection


@router.get("/connections", response_model=List[ERPConnectionResponse])
async def list_erp_connections(
    system_type: Optional[ERPSystemType] = None,
    status: Optional[ERPConnectionStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all ERP connections with optional filters"""
    
    query = db.query(ERPConnection)
    
    if system_type:
        query = query.filter(ERPConnection.system_type == system_type)
    
    if status:
        query = query.filter(ERPConnection.status == status)
    
    connections = query.order_by(desc(ERPConnection.created_at)).all()
    
    return connections


@router.get("/connections/{connection_id}", response_model=ERPConnectionResponse)
async def get_erp_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ERP connection details"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    return connection


@router.put("/connections/{connection_id}", response_model=ERPConnectionResponse)
async def update_erp_connection(
    connection_id: UUID,
    connection_data: ERPConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update ERP connection"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    # Update fields
    update_data = connection_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connection, field, value)
    
    connection.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(connection)
    
    return connection


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_erp_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete ERP connection (cascade deletes logs and mappings)"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    db.delete(connection)
    db.commit()
    
    return None


@router.post("/connections/{connection_id}/test", response_model=Dict[str, Any])
async def test_erp_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test ERP connection and return company info"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    try:
        # Get connector instance
        connector = get_erp_connector(connection, db)
        
        # Authenticate
        auth_success = await connector.authenticate()
        if not auth_success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
        
        # Test connection
        company_info = await connector.test_connection()
        
        # Update connection status
        connection.status = ERPConnectionStatus.ACTIVE
        connection.last_connected_at = datetime.utcnow()
        connection.connection_error = None
        db.commit()
        
        return {
            "success": True,
            "company_name": company_info.get("company_name"),
            "country": company_info.get("country"),
            "connected_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        # Update connection status
        connection.status = ERPConnectionStatus.ERROR
        connection.connection_error = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


@router.post("/connections/{connection_id}/authenticate", status_code=status.HTTP_200_OK)
async def authenticate_erp_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Force re-authentication with ERP system"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    try:
        connector = get_erp_connector(connection, db)
        auth_success = await connector.authenticate()
        
        if not auth_success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
        
        connection.status = ERPConnectionStatus.ACTIVE
        connection.last_connected_at = datetime.utcnow()
        connection.connection_error = None
        db.commit()
        
        return {"success": True, "authenticated_at": datetime.utcnow().isoformat()}
    
    except Exception as e:
        connection.status = ERPConnectionStatus.ERROR
        connection.connection_error = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


# ==================== Sync Operations ====================

@router.post("/connections/{connection_id}/sync/vendors", response_model=SyncResponse)
async def sync_vendors(
    connection_id: UUID,
    sync_request: SyncRequest = SyncRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger vendor import from ERP"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    # Create sync log
    sync_log = ERPSyncLog(
        connection_id=connection_id,
        entity_type=ERPEntityType.VENDOR,
        sync_direction="import",
        status=SyncStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        sync_params={
            "since": sync_request.since.isoformat() if sync_request.since else None,
            "limit": sync_request.limit
        },
        triggered_by=current_user.email,
        total_count=0,
        success_count=0,
        error_count=0
    )
    
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)
    
    try:
        # Get connector and import vendors
        connector = get_erp_connector(connection, db)
        
        # Authenticate first
        await connector.authenticate()
        
        # Import vendors
        result = await connector.import_vendors(
            since=sync_request.since,
            limit=sync_request.limit
        )
        
        # Update sync log
        sync_log.status = result.status
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = int((sync_log.completed_at - sync_log.started_at).total_seconds())
        sync_log.total_count = result.total_count
        sync_log.success_count = result.success_count
        sync_log.error_count = result.error_count
        sync_log.errors = result.errors
        
        # Update connection last_sync_at
        connection.last_sync_at = datetime.utcnow()
        
        db.commit()
        
        return SyncResponse(
            sync_log_id=sync_log.id,
            status=sync_log.status,
            started_at=sync_log.started_at
        )
    
    except Exception as e:
        # Update sync log with failure
        sync_log.status = SyncStatus.FAILED
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = int((sync_log.completed_at - sync_log.started_at).total_seconds())
        sync_log.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vendor sync failed: {str(e)}"
        )


@router.post("/connections/{connection_id}/sync/purchase-orders", response_model=SyncResponse)
async def sync_purchase_orders(
    connection_id: UUID,
    sync_request: SyncRequest = SyncRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger purchase order import from ERP"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    # Create sync log
    sync_log = ERPSyncLog(
        connection_id=connection_id,
        entity_type=ERPEntityType.PURCHASE_ORDER,
        sync_direction="import",
        status=SyncStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        sync_params={
            "since": sync_request.since.isoformat() if sync_request.since else None,
            "status_filter": sync_request.status_filter,
            "limit": sync_request.limit
        },
        triggered_by=current_user.email,
        total_count=0,
        success_count=0,
        error_count=0
    )
    
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)
    
    try:
        connector = get_erp_connector(connection, db)
        await connector.authenticate()
        
        result = await connector.import_purchase_orders(
            since=sync_request.since,
            status_filter=sync_request.status_filter,
            limit=sync_request.limit
        )
        
        # Update sync log
        sync_log.status = result.status
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = int((sync_log.completed_at - sync_log.started_at).total_seconds())
        sync_log.total_count = result.total_count
        sync_log.success_count = result.success_count
        sync_log.error_count = result.error_count
        sync_log.errors = result.errors
        
        connection.last_sync_at = datetime.utcnow()
        
        db.commit()
        
        return SyncResponse(
            sync_log_id=sync_log.id,
            status=sync_log.status,
            started_at=sync_log.started_at
        )
    
    except Exception as e:
        sync_log.status = SyncStatus.FAILED
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = int((sync_log.completed_at - sync_log.started_at).total_seconds())
        sync_log.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Purchase order sync failed: {str(e)}"
        )


@router.post("/invoices/{invoice_id}/export", response_model=InvoiceExportResponse)
async def export_invoice_to_erp(
    invoice_id: UUID,
    export_request: InvoiceExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export approved invoice to ERP system"""
    
    # Get invoice (would need to import Invoice model)
    # invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    # For now, placeholder
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == export_request.connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {export_request.connection_id} not found"
        )
    
    try:
        connector = get_erp_connector(connection, db)
        await connector.authenticate()
        
        # Create ERPInvoice object from SmartAP invoice
        # This would map invoice fields to ERPInvoice model
        # For now, placeholder
        from ..integrations.erp.base import ERPInvoice
        
        erp_invoice = ERPInvoice(
            invoice_number=f"INV-{invoice_id}",
            vendor_id="vendor_external_id",
            invoice_date=datetime.utcnow(),
            due_date=datetime.utcnow(),
            total_amount=100000,  # cents
            line_items=[],
            currency="USD"
        )
        
        # Export to ERP
        result = await connector.export_invoice(erp_invoice)
        
        # Create invoice mapping
        invoice_mapping = ERPInvoiceMapping(
            connection_id=connection.id,
            smartap_invoice_id=invoice_id,
            erp_invoice_id=result.get("id"),
            erp_invoice_number=result.get("invoice_number"),
            exported_at=datetime.utcnow(),
            exported_by=current_user.email,
            payment_status="unpaid"
        )
        
        db.add(invoice_mapping)
        db.commit()
        
        return InvoiceExportResponse(
            success=True,
            external_id=result.get("id"),
            external_number=result.get("invoice_number"),
            exported_at=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice export failed: {str(e)}"
        )


@router.post("/invoices/{invoice_id}/sync-payment", status_code=status.HTTP_200_OK)
async def sync_invoice_payment_status(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync payment status from ERP for exported invoice"""
    
    # Get invoice mapping
    invoice_mapping = db.query(ERPInvoiceMapping).filter(
        ERPInvoiceMapping.smartap_invoice_id == invoice_id
    ).first()
    
    if not invoice_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} has not been exported to ERP"
        )
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == invoice_mapping.connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    try:
        connector = get_erp_connector(connection, db)
        await connector.authenticate()
        
        # Sync payment status
        payment_info = await connector.sync_payment_status(invoice_mapping.erp_invoice_id)
        
        # Update mapping
        invoice_mapping.payment_status = payment_info.get("status", "unpaid")
        invoice_mapping.payment_amount = payment_info.get("paid_amount", 0)
        invoice_mapping.payment_synced_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "payment_status": invoice_mapping.payment_status,
            "payment_amount": invoice_mapping.payment_amount,
            "synced_at": invoice_mapping.payment_synced_at.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment sync failed: {str(e)}"
        )


# ==================== Sync Logs ====================

@router.get("/sync-logs", response_model=List[ERPSyncLogResponse])
async def list_sync_logs(
    connection_id: Optional[UUID] = None,
    entity_type: Optional[ERPEntityType] = None,
    status: Optional[SyncStatus] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List sync logs with filters"""
    
    query = db.query(ERPSyncLog)
    
    if connection_id:
        query = query.filter(ERPSyncLog.connection_id == connection_id)
    
    if entity_type:
        query = query.filter(ERPSyncLog.entity_type == entity_type)
    
    if status:
        query = query.filter(ERPSyncLog.status == status)
    
    logs = query.order_by(desc(ERPSyncLog.started_at)).limit(limit).offset(offset).all()
    
    return logs


@router.get("/sync-logs/{log_id}", response_model=ERPSyncLogResponse)
async def get_sync_log(
    log_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed sync log"""
    
    log = db.query(ERPSyncLog).filter(ERPSyncLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync log {log_id} not found"
        )
    
    return log


# ==================== Field Mappings ====================

@router.get("/connections/{connection_id}/field-mappings", response_model=List[ERPFieldMappingResponse])
async def list_field_mappings(
    connection_id: UUID,
    entity_type: Optional[ERPEntityType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List field mappings for connection"""
    
    query = db.query(ERPFieldMapping).filter(
        ERPFieldMapping.connection_id == connection_id
    )
    
    if entity_type:
        query = query.filter(ERPFieldMapping.entity_type == entity_type)
    
    mappings = query.order_by(ERPFieldMapping.entity_type, ERPFieldMapping.smartap_field).all()
    
    return mappings


@router.post("/connections/{connection_id}/field-mappings", response_model=ERPFieldMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_field_mapping(
    connection_id: UUID,
    mapping_data: ERPFieldMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create field mapping rule"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    # Check for duplicate mapping
    existing = db.query(ERPFieldMapping).filter(
        and_(
            ERPFieldMapping.connection_id == connection_id,
            ERPFieldMapping.entity_type == mapping_data.entity_type,
            ERPFieldMapping.smartap_field == mapping_data.smartap_field
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field mapping for {mapping_data.entity_type}.{mapping_data.smartap_field} already exists"
        )
    
    mapping = ERPFieldMapping(
        connection_id=connection_id,
        entity_type=mapping_data.entity_type,
        smartap_field=mapping_data.smartap_field,
        erp_field=mapping_data.erp_field,
        transformation_rule=mapping_data.transformation_rule,
        default_value=mapping_data.default_value,
        is_required=mapping_data.is_required,
        validation_regex=mapping_data.validation_regex,
        description=mapping_data.description
    )
    
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    
    return mapping


@router.put("/field-mappings/{mapping_id}", response_model=ERPFieldMappingResponse)
async def update_field_mapping(
    mapping_id: UUID,
    mapping_data: ERPFieldMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update field mapping"""
    
    mapping = db.query(ERPFieldMapping).filter(
        ERPFieldMapping.id == mapping_id
    ).first()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping {mapping_id} not found"
        )
    
    update_data = mapping_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mapping, field, value)
    
    mapping.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(mapping)
    
    return mapping


@router.delete("/field-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_mapping(
    mapping_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete field mapping"""
    
    mapping = db.query(ERPFieldMapping).filter(
        ERPFieldMapping.id == mapping_id
    ).first()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping {mapping_id} not found"
        )
    
    db.delete(mapping)
    db.commit()
    
    return None


# ==================== Accounts & Tax Codes ====================

@router.get("/connections/{connection_id}/accounts", response_model=List[Dict[str, Any]])
async def get_accounts(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chart of accounts from ERP"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    try:
        connector = get_erp_connector(connection, db)
        await connector.authenticate()
        
        accounts = await connector.get_accounts()
        
        return accounts
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch accounts: {str(e)}"
        )


@router.get("/connections/{connection_id}/tax-codes", response_model=List[Dict[str, Any]])
async def get_tax_codes(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tax codes from ERP"""
    
    connection = db.query(ERPConnection).filter(
        ERPConnection.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    try:
        connector = get_erp_connector(connection, db)
        await connector.authenticate()
        
        tax_codes = await connector.get_tax_codes()
        
        return tax_codes
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tax codes: {str(e)}"
        )
