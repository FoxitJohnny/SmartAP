"""
ERP Sync Scheduler Service

Background service for scheduled ERP synchronization operations.
Uses APScheduler to run periodic sync jobs for vendors, purchase orders, and payment status.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..db.database import SessionLocal, get_sync_session
from ..models.erp import (
    ERPConnection,
    ERPSyncLog,
    ERPVendorMapping,
    ERPInvoiceMapping,
    ERPConnectionStatus,
    SyncStatus,
    ERPEntityType,
)
from ..db.models import VendorDB as Vendor
from ..integrations.erp.base import ERPConnector, ERPVendor, ERPPurchaseOrder, SyncResult
from ..integrations.erp.quickbooks import QuickBooksConnector
from ..integrations.erp.xero import XeroConnector
from ..integrations.erp.sap import SAPConnector
from ..integrations.erp.netsuite import NetSuiteConnector

logger = logging.getLogger(__name__)


class ERPSyncService:
    """
    Manages scheduled and manual ERP synchronization operations.
    
    Responsibilities:
    - Periodic import of vendors and purchase orders from ERP
    - Export of approved invoices to ERP
    - Payment status synchronization
    - Conflict resolution between SmartAP and ERP data
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def start(self):
        """Start the scheduler with configured jobs"""
        if self._is_running:
            logger.warning("ERP sync service is already running")
            return
        
        # Schedule periodic sync jobs
        self._setup_jobs()
        
        self.scheduler.start()
        self._is_running = True
        logger.info("ERP sync service started successfully")
    
    def stop(self):
        """Stop the scheduler"""
        if not self._is_running:
            return
        
        self.scheduler.shutdown(wait=True)
        self._is_running = False
        logger.info("ERP sync service stopped")
    
    def _setup_jobs(self):
        """Configure scheduled sync jobs"""
        
        # Sync vendors every 60 minutes
        self.scheduler.add_job(
            self.sync_all_vendors,
            trigger=IntervalTrigger(minutes=60),
            id="sync_vendors_job",
            name="Sync Vendors from All Active ERPs",
            replace_existing=True,
            max_instances=1
        )
        
        # Sync purchase orders every 30 minutes
        self.scheduler.add_job(
            self.sync_all_purchase_orders,
            trigger=IntervalTrigger(minutes=30),
            id="sync_purchase_orders_job",
            name="Sync Purchase Orders from All Active ERPs",
            replace_existing=True,
            max_instances=1
        )
        
        # Sync payment status every 15 minutes
        self.scheduler.add_job(
            self.sync_all_payment_statuses,
            trigger=IntervalTrigger(minutes=15),
            id="sync_payment_statuses_job",
            name="Sync Payment Statuses for Exported Invoices",
            replace_existing=True,
            max_instances=1
        )
        
        logger.info("Scheduled 3 ERP sync jobs: vendors (60min), purchase orders (30min), payments (15min)")
    
    
    def _get_connector(self, connection: ERPConnection) -> ERPConnector:
        """Factory function to create appropriate ERP connector"""
        
        credentials = connection.credentials or {}
        
        # Build connection config dict that connectors expect
        config = {
            **credentials,
            "tenant_id": connection.tenant_id,
            "company_db": connection.company_db,
            "api_url": connection.api_url,
        }
        
        if connection.system_type.value == "quickbooks":
            return QuickBooksConnector(config)
        
        elif connection.system_type.value == "xero":
            return XeroConnector(config)
        
        elif connection.system_type.value == "sap":
            return SAPConnector(config)
        
        elif connection.system_type.value == "netsuite":
            return NetSuiteConnector(config)
        
        else:
            raise ValueError(f"Unsupported ERP system: {connection.system_type}")
    
    async def sync_all_vendors(self):
        """Sync vendors from all active ERP connections"""
        logger.info("Starting scheduled vendor sync for all active connections")
        
        db = SessionLocal()
        try:
            # Get all active connections with auto_sync enabled
            connections = db.query(ERPConnection).filter(
                ERPConnection.status == ERPConnectionStatus.ACTIVE,
                ERPConnection.auto_sync_enabled == True
            ).all()
            
            logger.info(f"Found {len(connections)} active connections for vendor sync")
            
            for connection in connections:
                try:
                    await self.sync_connection_vendors(connection.id, db)
                except Exception as e:
                    logger.error(f"Failed to sync vendors for connection {connection.name}: {str(e)}")
                    continue
        
        finally:
            db.close()
    
    async def sync_connection_vendors(
        self,
        connection_id: UUID,
        db: Session,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> ERPSyncLog:
        """Sync vendors from a specific ERP connection"""
        
        connection = db.query(ERPConnection).filter(
            ERPConnection.id == connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Use last_sync_at if since not provided
        if since is None and connection.last_sync_at:
            since = connection.last_sync_at
        
        # Create sync log
        sync_log = ERPSyncLog(
            connection_id=connection_id,
            entity_type=ERPEntityType.VENDOR,
            sync_direction="import",
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            sync_params={
                "since": since.isoformat() if since else None,
                "limit": limit
            },
            triggered_by="system",
            total_count=0,
            success_count=0,
            error_count=0
        )
        
        db.add(sync_log)
        db.commit()
        db.refresh(sync_log)
        
        try:
            # Get connector and authenticate
            connector = self._get_connector(connection)
            await connector.authenticate()
            
            # Import vendors
            result = await connector.import_vendors(since=since, limit=limit)
            
            # Process vendors and create/update in SmartAP
            for vendor_data in result.data:
                await self._process_vendor(connection, vendor_data, db)
            
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
            
            logger.info(
                f"Vendor sync completed for {connection.name}: "
                f"{result.success_count}/{result.total_count} successful"
            )
            
            return sync_log
        
        except Exception as e:
            logger.error(f"Vendor sync failed for {connection.name}: {str(e)}")
            
            # Update sync log with failure
            sync_log.status = SyncStatus.FAILED
            sync_log.completed_at = datetime.utcnow()
            sync_log.duration_seconds = int((sync_log.completed_at - sync_log.started_at).total_seconds())
            sync_log.error_message = str(e)
            
            # Update connection status
            connection.status = ERPConnectionStatus.ERROR
            connection.connection_error = str(e)
            
            db.commit()
            
            raise
    
    async def _process_vendor(
        self,
        connection: ERPConnection,
        vendor_data: ERPVendor,
        db: Session
    ):
        """Process vendor from ERP and create/update in SmartAP"""
        
        # Check if vendor mapping exists
        mapping = db.query(ERPVendorMapping).filter(
            ERPVendorMapping.connection_id == connection.id,
            ERPVendorMapping.erp_vendor_id == vendor_data.external_id
        ).first()
        
        if mapping:
            # Update existing vendor
            vendor = db.query(Vendor).filter(Vendor.id == mapping.smartap_vendor_id).first()
            
            if vendor:
                # Update vendor fields (use newest data)
                vendor.name = vendor_data.name
                vendor.email = vendor_data.email
                vendor.phone = vendor_data.phone
                vendor.address = vendor_data.address
                vendor.tax_id = vendor_data.tax_id
                vendor.payment_terms = vendor_data.payment_terms
                vendor.updated_at = datetime.utcnow()
                
                # Update mapping
                mapping.erp_vendor_name = vendor_data.name
                mapping.last_synced_at = datetime.utcnow()
                mapping.sync_count += 1
                
                logger.debug(f"Updated existing vendor: {vendor.name}")
        else:
            # Create new vendor
            vendor = Vendor(
                name=vendor_data.name,
                email=vendor_data.email,
                phone=vendor_data.phone,
                address=vendor_data.address,
                tax_id=vendor_data.tax_id,
                payment_terms=vendor_data.payment_terms,
                status="active"
            )
            
            db.add(vendor)
            db.flush()  # Get vendor ID
            
            # Create mapping
            mapping = ERPVendorMapping(
                connection_id=connection.id,
                smartap_vendor_id=vendor.id,
                erp_vendor_id=vendor_data.external_id,
                erp_vendor_name=vendor_data.name,
                first_synced_at=datetime.utcnow(),
                last_synced_at=datetime.utcnow(),
                sync_count=1,
                is_active=True
            )
            
            db.add(mapping)
            
            logger.debug(f"Created new vendor: {vendor.name}")
        
        db.commit()
    
    async def sync_all_purchase_orders(self):
        """Sync purchase orders from all active ERP connections"""
        logger.info("Starting scheduled purchase order sync for all active connections")
        
        db = SessionLocal()
        try:
            connections = db.query(ERPConnection).filter(
                ERPConnection.status == ERPConnectionStatus.ACTIVE,
                ERPConnection.auto_sync_enabled == True
            ).all()
            
            logger.info(f"Found {len(connections)} active connections for PO sync")
            
            for connection in connections:
                try:
                    await self.sync_connection_purchase_orders(connection.id, db)
                except Exception as e:
                    logger.error(f"Failed to sync purchase orders for connection {connection.name}: {str(e)}")
                    continue
        
        finally:
            db.close()
    
    async def sync_connection_purchase_orders(
        self,
        connection_id: UUID,
        db: Session,
        since: Optional[datetime] = None,
        status_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> ERPSyncLog:
        """Sync purchase orders from a specific ERP connection"""
        
        connection = db.query(ERPConnection).filter(
            ERPConnection.id == connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Use last_sync_at if since not provided
        if since is None and connection.last_sync_at:
            since = connection.last_sync_at
        
        # Create sync log
        sync_log = ERPSyncLog(
            connection_id=connection_id,
            entity_type=ERPEntityType.PURCHASE_ORDER,
            sync_direction="import",
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            sync_params={
                "since": since.isoformat() if since else None,
                "status_filter": status_filter,
                "limit": limit
            },
            triggered_by="system",
            total_count=0,
            success_count=0,
            error_count=0
        )
        
        db.add(sync_log)
        db.commit()
        db.refresh(sync_log)
        
        try:
            connector = self._get_connector(connection)
            await connector.authenticate()
            
            result = await connector.import_purchase_orders(
                since=since,
                status_filter=status_filter,
                limit=limit
            )
            
            # Process purchase orders
            # (Would create/update PurchaseOrder model - placeholder for now)
            for po_data in result.data:
                logger.debug(f"Processing PO: {po_data.po_number}")
            
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
            
            logger.info(
                f"Purchase order sync completed for {connection.name}: "
                f"{result.success_count}/{result.total_count} successful"
            )
            
            return sync_log
        
        except Exception as e:
            logger.error(f"Purchase order sync failed for {connection.name}: {str(e)}")
            
            sync_log.status = SyncStatus.FAILED
            sync_log.completed_at = datetime.utcnow()
            sync_log.duration_seconds = int((sync_log.completed_at - sync_log.started_at).total_seconds())
            sync_log.error_message = str(e)
            
            connection.status = ERPConnectionStatus.ERROR
            connection.connection_error = str(e)
            
            db.commit()
            
            raise
    
    async def sync_all_payment_statuses(self):
        """Sync payment status for all exported invoices"""
        logger.info("Starting scheduled payment status sync for all exported invoices")
        
        db = SessionLocal()
        try:
            # Get all invoice mappings that need payment sync
            # (invoices exported in last 90 days and not fully paid)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            invoice_mappings = db.query(ERPInvoiceMapping).filter(
                ERPInvoiceMapping.exported_at >= cutoff_date,
                ERPInvoiceMapping.payment_status != "paid"
            ).all()
            
            logger.info(f"Found {len(invoice_mappings)} invoices to sync payment status")
            
            # Group by connection for efficiency
            by_connection: Dict[UUID, List[ERPInvoiceMapping]] = {}
            for mapping in invoice_mappings:
                if mapping.connection_id not in by_connection:
                    by_connection[mapping.connection_id] = []
                by_connection[mapping.connection_id].append(mapping)
            
            for connection_id, mappings in by_connection.items():
                try:
                    await self.sync_connection_payment_statuses(connection_id, mappings, db)
                except Exception as e:
                    logger.error(f"Failed to sync payment statuses for connection {connection_id}: {str(e)}")
                    continue
        
        finally:
            db.close()
    
    async def sync_connection_payment_statuses(
        self,
        connection_id: UUID,
        invoice_mappings: List[ERPInvoiceMapping],
        db: Session
    ):
        """Sync payment statuses for invoices from a specific connection"""
        
        connection = db.query(ERPConnection).filter(
            ERPConnection.id == connection_id
        ).first()
        
        if not connection or connection.status != ERPConnectionStatus.ACTIVE:
            logger.warning(f"Connection {connection_id} not active, skipping payment sync")
            return
        
        try:
            connector = self._get_connector(connection)
            await connector.authenticate()
            
            success_count = 0
            error_count = 0
            
            for mapping in invoice_mappings:
                try:
                    # Sync payment status from ERP
                    payment_info = await connector.sync_payment_status(mapping.erp_invoice_id)
                    
                    # Update mapping
                    mapping.payment_status = payment_info.get("status", "unpaid")
                    mapping.payment_amount = payment_info.get("paid_amount", 0)
                    mapping.payment_synced_at = datetime.utcnow()
                    
                    success_count += 1
                    
                    logger.debug(
                        f"Updated payment status for invoice {mapping.erp_invoice_number}: "
                        f"{mapping.payment_status}"
                    )
                
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Failed to sync payment for invoice {mapping.erp_invoice_number}: {str(e)}"
                    )
            
            db.commit()
            
            logger.info(
                f"Payment sync completed for {connection.name}: "
                f"{success_count} successful, {error_count} failed"
            )
        
        except Exception as e:
            logger.error(f"Payment sync failed for connection {connection.name}: {str(e)}")
            raise
    
    async def export_invoice(
        self,
        invoice_id: UUID,
        connection_id: UUID,
        db: Session,
        exported_by: str
    ) -> Dict[str, Any]:
        """Export invoice to ERP system"""
        
        # Get invoice (would need Invoice model)
        # invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        connection = db.query(ERPConnection).filter(
            ERPConnection.id == connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        try:
            connector = self._get_connector(connection)
            await connector.authenticate()
            
            # Create ERPInvoice from SmartAP invoice
            # (Placeholder - would map actual invoice fields)
            from ..integrations.erp.base import ERPInvoice
            
            erp_invoice = ERPInvoice(
                invoice_number=f"INV-{invoice_id}",
                vendor_id="vendor_external_id",
                invoice_date=datetime.utcnow(),
                due_date=datetime.utcnow(),
                total_amount=100000,
                line_items=[],
                currency="USD"
            )
            
            # Export to ERP
            result = await connector.export_invoice(erp_invoice)
            
            # Create invoice mapping
            mapping = ERPInvoiceMapping(
                connection_id=connection_id,
                smartap_invoice_id=invoice_id,
                erp_invoice_id=result.get("id"),
                erp_invoice_number=result.get("invoice_number"),
                exported_at=datetime.utcnow(),
                exported_by=exported_by,
                payment_status="unpaid"
            )
            
            db.add(mapping)
            db.commit()
            
            logger.info(f"Exported invoice {invoice_id} to {connection.name} as {result.get('invoice_number')}")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to export invoice {invoice_id} to {connection.name}: {str(e)}")
            raise
    
    def trigger_manual_sync(
        self,
        connection_id: UUID,
        entity_type: ERPEntityType,
        **kwargs
    ):
        """Trigger manual sync operation outside of scheduled jobs"""
        
        db = SessionLocal()
        try:
            if entity_type == ERPEntityType.VENDOR:
                return asyncio.create_task(
                    self.sync_connection_vendors(connection_id, db, **kwargs)
                )
            elif entity_type == ERPEntityType.PURCHASE_ORDER:
                return asyncio.create_task(
                    self.sync_connection_purchase_orders(connection_id, db, **kwargs)
                )
            else:
                raise ValueError(f"Unsupported entity type for manual sync: {entity_type}")
        
        finally:
            pass  # Don't close db here, let the task handle it


# Global service instance
erp_sync_service = ERPSyncService()


def start_erp_sync_service():
    """Start the ERP sync service (called from main.py)"""
    erp_sync_service.start()


def stop_erp_sync_service():
    """Stop the ERP sync service"""
    erp_sync_service.stop()
