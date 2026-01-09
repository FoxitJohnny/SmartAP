"""
Archival Service for SmartAP Invoice Management System

This service manages the complete archival lifecycle for approved invoices,
including PDF preparation, immutable storage, retention policy enforcement,
and secure retrieval with audit logging.

Key Features:
- Complete archival workflow orchestration
- Integration with PDFService for document preparation
- Immutable storage with tamper-proof sealing
- 7-year retention policy enforcement
- Access control and audit logging
- Archive integrity verification
- Automatic cleanup of expired archives

Author: SmartAP Development Team
Date: 2025
"""

import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging
from sqlalchemy.orm import Session

from ..models.approval import (
    ArchivedDocument,
    DocumentAccessLog,
    ApprovalWorkflow,
    ApprovalAction,
    ArchivalStatus
)
from ..models.invoice import Invoice
from ..db.models import InvoiceDB
from .pdf_service import PDFService

logger = logging.getLogger(__name__)


class ArchivalService:
    """
    Service for managing invoice document archival and retention.
    
    This service orchestrates the complete archival workflow:
    1. Retrieve invoice PDF from storage
    2. Gather approval workflow audit data
    3. Prepare PDF for archival (flatten, audit page, PDF/A, seal)
    4. Calculate document hash for tamper detection
    5. Store in archival location with immutable flag
    6. Create database record with retention policy
    7. Log all access attempts for compliance
    """
    
    def __init__(
        self,
        db: Session,
        archival_storage_path: str,
        retention_years: int = 7,
        enable_cloud_backup: bool = False,
        cloud_storage_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize archival service.
        
        Args:
            db: Database session
            archival_storage_path: Base path for archival storage
            retention_years: Default retention period (default: 7 years for compliance)
            enable_cloud_backup: Whether to backup to cloud storage
            cloud_storage_config: Cloud storage configuration (S3, Azure Blob, etc.)
        """
        self.db = db
        self.archival_storage_path = Path(archival_storage_path)
        self.retention_years = retention_years
        self.enable_cloud_backup = enable_cloud_backup
        self.cloud_storage_config = cloud_storage_config or {}
        self.pdf_service = PDFService()
        
        # Create archival directory if it doesn't exist
        self.archival_storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ArchivalService initialized with storage path: {self.archival_storage_path}")
    
    def archive_invoice(
        self,
        invoice_id: str,
        workflow_id: str,
        seal_config: Optional[Dict[str, Any]] = None,
        custom_retention_years: Optional[int] = None
    ) -> ArchivedDocument:
        """
        Archive an approved invoice with complete audit trail.
        
        This method performs the complete archival workflow:
        1. Retrieve invoice document from database
        2. Gather approval workflow audit data
        3. Prepare PDF for archival (5-step process)
        4. Calculate SHA256 hash for tamper detection
        5. Store in archival location
        6. Create ArchivedDocument database record
        7. Backup to cloud storage (if enabled)
        
        Args:
            invoice_id: Invoice ID to archive
            workflow_id: Approval workflow ID for audit data
            seal_config: Configuration for tamper-proof seal
            custom_retention_years: Custom retention period (overrides default)
        
        Returns:
            ArchivedDocument record
        
        Raises:
            ValueError: If invoice or workflow not found
            RuntimeError: If archival process fails
        """
        try:
            logger.info(f"Starting archival process for invoice {invoice_id}")
            
            # 1. Retrieve invoice document
            invoice_doc = self.db.query(InvoiceDocument).filter(
                InvoiceDocument.invoice_id == invoice_id
            ).first()
            
            if not invoice_doc:
                raise ValueError(f"Invoice document not found: {invoice_id}")
            
            # 2. Gather approval workflow audit data
            workflow = self.db.query(ApprovalWorkflow).filter(
                ApprovalWorkflow.id == workflow_id
            ).first()
            
            if not workflow:
                raise ValueError(f"Approval workflow not found: {workflow_id}")
            
            audit_data = self._gather_audit_data(workflow)
            
            # 3. Generate archival filename and path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archival_filename = f"invoice_{invoice_id}_{timestamp}_archived.pdf"
            archival_path = self.archival_storage_path / archival_filename
            
            # Create temporary output path for PDF preparation
            temp_output = self.archival_storage_path / f"temp_{archival_filename}"
            
            # 4. Prepare PDF for archival (5-step process)
            logger.info(f"Preparing PDF for archival: {invoice_doc.document_path}")
            
            seal_config = seal_config or {
                "certificate_path": "config/archival_cert.p12",
                "certificate_password": "archival_seal_password",
                "reason": "Document archived for compliance",
                "location": "SmartAP Archival System"
            }
            
            metadata = {
                "title": f"Archived Invoice {invoice_id}",
                "author": "SmartAP Archival System",
                "subject": "Approved Invoice - Permanent Archival",
                "keywords": f"invoice,archival,approved,{invoice_id}",
                "creator": "SmartAP v1.0",
                "producer": "Foxit PDF SDK"
            }
            
            self.pdf_service.prepare_for_archival(
                input_path=invoice_doc.document_path,
                output_path=str(temp_output),
                audit_data=audit_data,
                seal_config=seal_config,
                metadata=metadata
            )
            
            # Move to final archival location
            shutil.move(str(temp_output), str(archival_path))
            logger.info(f"PDF archived to: {archival_path}")
            
            # 5. Calculate SHA256 hash for tamper detection
            document_hash = self._calculate_file_hash(archival_path)
            logger.info(f"Document hash calculated: {document_hash}")
            
            # 6. Calculate retention expiration
            retention_years = custom_retention_years or self.retention_years
            retention_expires_at = datetime.utcnow() + timedelta(days=365 * retention_years)
            
            # 7. Create ArchivedDocument record
            archived_doc = ArchivedDocument(
                invoice_id=invoice_id,
                archived_document_path=str(archival_path),
                document_hash=document_hash,
                status=ArchivalStatus.SEALED,
                flattened=True,
                audit_page_added=True,
                pdfa_converted=True,
                tamper_sealed=True,
                seal_verification={
                    "sealed_at": datetime.utcnow().isoformat(),
                    "seal_config": seal_config,
                    "initial_hash": document_hash
                },
                retention_years=retention_years,
                retention_expires_at=retention_expires_at,
                workflow_id=workflow_id,
                audit_data=audit_data,
                access_count=0
            )
            
            self.db.add(archived_doc)
            self.db.commit()
            self.db.refresh(archived_doc)
            
            logger.info(f"ArchivedDocument record created: {archived_doc.id}")
            
            # 8. Backup to cloud storage (if enabled)
            if self.enable_cloud_backup:
                self._backup_to_cloud(archival_path, archival_filename)
            
            logger.info(f"Archival process completed successfully for invoice {invoice_id}")
            return archived_doc
            
        except Exception as e:
            logger.error(f"Archival process failed for invoice {invoice_id}: {e}")
            
            # Create failed archival record
            failed_doc = ArchivedDocument(
                invoice_id=invoice_id,
                archived_document_path=str(archival_path) if 'archival_path' in locals() else None,
                document_hash=None,
                status=ArchivalStatus.FAILED,
                audit_data={"error": str(e), "timestamp": datetime.utcnow().isoformat()},
                retention_years=retention_years,
                workflow_id=workflow_id
            )
            self.db.add(failed_doc)
            self.db.commit()
            
            raise RuntimeError(f"Failed to archive invoice {invoice_id}: {e}")
    
    def retrieve_archived_invoice(
        self,
        invoice_id: str,
        accessed_by: str,
        access_type: str = "view",
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Retrieve an archived invoice document with audit logging.
        
        Args:
            invoice_id: Invoice ID to retrieve
            accessed_by: User/system retrieving the document
            access_type: Type of access (view, download, print)
            reason: Reason for accessing archived document
            ip_address: IP address of requester
            user_agent: User agent of requester
        
        Returns:
            Path to archived document
        
        Raises:
            ValueError: If archived document not found
            PermissionError: If retention period expired and access denied
        """
        archived_doc = self.db.query(ArchivedDocument).filter(
            ArchivedDocument.invoice_id == invoice_id
        ).first()
        
        if not archived_doc:
            raise ValueError(f"Archived document not found for invoice: {invoice_id}")
        
        # Check retention expiration
        if archived_doc.is_retention_expired:
            logger.warning(f"Access denied - retention expired for invoice {invoice_id}")
            raise PermissionError(
                f"Document retention period expired. Document can only be accessed for deletion."
            )
        
        # Verify archive integrity
        is_valid, verification_details = self.verify_archive_integrity(invoice_id)
        if not is_valid:
            logger.error(f"Archive integrity check failed for invoice {invoice_id}: {verification_details}")
            raise RuntimeError(f"Archive integrity compromised: {verification_details.get('error')}")
        
        # Log access
        access_log = DocumentAccessLog(
            document_id=archived_doc.id,
            accessed_by=accessed_by,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=reason
        )
        self.db.add(access_log)
        
        # Increment access count
        archived_doc.access_count += 1
        self.db.commit()
        
        logger.info(
            f"Archived document accessed: invoice={invoice_id}, user={accessed_by}, "
            f"type={access_type}, count={archived_doc.access_count}"
        )
        
        return archived_doc.archived_document_path
    
    def verify_archive_integrity(self, invoice_id: str) -> tuple[bool, Dict[str, Any]]:
        """
        Verify the integrity of an archived document using hash comparison.
        
        Args:
            invoice_id: Invoice ID to verify
        
        Returns:
            Tuple of (is_valid, verification_details)
        """
        archived_doc = self.db.query(ArchivedDocument).filter(
            ArchivedDocument.invoice_id == invoice_id
        ).first()
        
        if not archived_doc:
            return False, {"error": "Archived document not found"}
        
        # Check if file exists
        archive_path = Path(archived_doc.archived_document_path)
        if not archive_path.exists():
            logger.error(f"Archived file not found: {archive_path}")
            return False, {
                "error": "Archived file not found on disk",
                "expected_path": str(archive_path)
            }
        
        # Calculate current hash
        current_hash = self._calculate_file_hash(archive_path)
        
        # Compare with stored hash
        is_valid = current_hash == archived_doc.document_hash
        
        verification_details = {
            "invoice_id": invoice_id,
            "archive_path": str(archive_path),
            "stored_hash": archived_doc.document_hash,
            "current_hash": current_hash,
            "is_valid": is_valid,
            "verified_at": datetime.utcnow().isoformat()
        }
        
        if not is_valid:
            logger.error(f"Archive integrity check FAILED for invoice {invoice_id}")
            verification_details["error"] = "Document hash mismatch - possible tampering detected"
        else:
            logger.info(f"Archive integrity check PASSED for invoice {invoice_id}")
        
        # Update seal verification in database
        seal_verification = archived_doc.seal_verification or {}
        seal_verification["last_verification"] = verification_details
        archived_doc.seal_verification = seal_verification
        self.db.commit()
        
        return is_valid, verification_details
    
    def check_retention_expiry(self) -> List[Dict[str, Any]]:
        """
        Check for archived documents approaching or past retention expiration.
        
        Returns:
            List of documents with retention status
        """
        current_date = datetime.utcnow()
        warning_threshold = current_date + timedelta(days=30)  # 30-day warning
        
        # Query all archived documents
        archived_docs = self.db.query(ArchivedDocument).all()
        
        retention_status = []
        
        for doc in archived_docs:
            if doc.retention_expires_at:
                days_remaining = (doc.retention_expires_at - current_date).days
                
                status_info = {
                    "invoice_id": doc.invoice_id,
                    "archived_at": doc.archived_at.isoformat(),
                    "retention_expires_at": doc.retention_expires_at.isoformat(),
                    "days_remaining": days_remaining,
                    "is_expired": doc.is_retention_expired,
                    "can_be_deleted": doc.can_be_deleted,
                    "access_count": doc.access_count
                }
                
                if doc.is_retention_expired:
                    status_info["status"] = "EXPIRED"
                    logger.warning(f"Retention EXPIRED for invoice {doc.invoice_id}")
                elif days_remaining <= 30:
                    status_info["status"] = "EXPIRING_SOON"
                    logger.info(f"Retention expiring soon for invoice {doc.invoice_id}: {days_remaining} days")
                else:
                    status_info["status"] = "ACTIVE"
                
                retention_status.append(status_info)
        
        return retention_status
    
    def delete_expired_archives(
        self,
        force: bool = False,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Delete archived documents past their retention period.
        
        Args:
            force: Force deletion even if access count is high
            dry_run: Only report what would be deleted without actual deletion
        
        Returns:
            List of deleted or deletable documents
        """
        current_date = datetime.utcnow()
        
        # Query expired documents
        expired_docs = self.db.query(ArchivedDocument).filter(
            ArchivedDocument.retention_expires_at < current_date,
            ArchivedDocument.status != ArchivalStatus.FAILED
        ).all()
        
        deletion_results = []
        
        for doc in expired_docs:
            # Check if document can be deleted
            if not force and doc.access_count > 100:
                logger.warning(
                    f"Skipping deletion of high-access document: invoice={doc.invoice_id}, "
                    f"access_count={doc.access_count}"
                )
                deletion_results.append({
                    "invoice_id": doc.invoice_id,
                    "status": "SKIPPED",
                    "reason": "High access count - requires manual review",
                    "access_count": doc.access_count
                })
                continue
            
            result = {
                "invoice_id": doc.invoice_id,
                "archived_at": doc.archived_at.isoformat(),
                "retention_expired_at": doc.retention_expires_at.isoformat(),
                "access_count": doc.access_count,
                "archive_path": doc.archived_document_path
            }
            
            if dry_run:
                result["status"] = "DRY_RUN"
                result["action"] = "Would be deleted"
                logger.info(f"DRY RUN: Would delete invoice {doc.invoice_id}")
            else:
                try:
                    # Delete physical file
                    archive_path = Path(doc.archived_document_path)
                    if archive_path.exists():
                        archive_path.unlink()
                        logger.info(f"Deleted archived file: {archive_path}")
                    
                    # Delete from cloud backup (if enabled)
                    if self.enable_cloud_backup:
                        self._delete_from_cloud(archive_path.name)
                    
                    # Delete database record
                    self.db.delete(doc)
                    self.db.commit()
                    
                    result["status"] = "DELETED"
                    result["deleted_at"] = datetime.utcnow().isoformat()
                    logger.info(f"Deleted expired archive: invoice={doc.invoice_id}")
                    
                except Exception as e:
                    result["status"] = "ERROR"
                    result["error"] = str(e)
                    logger.error(f"Failed to delete expired archive: invoice={doc.invoice_id}, error={e}")
            
            deletion_results.append(result)
        
        return deletion_results
    
    def _gather_audit_data(self, workflow: ApprovalWorkflow) -> Dict[str, Any]:
        """
        Gather complete audit data from approval workflow.
        
        Args:
            workflow: Approval workflow to extract data from
        
        Returns:
            Audit data dictionary
        """
        # Get all approval actions
        actions = self.db.query(ApprovalAction).filter(
            ApprovalAction.workflow_id == workflow.id
        ).order_by(ApprovalAction.created_at).all()
        
        audit_data = {
            "workflow_id": workflow.id,
            "invoice_id": workflow.invoice_id,
            "chain_name": workflow.chain.name if workflow.chain else "Unknown",
            "status": workflow.status.value,
            "created_at": workflow.created_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "approval_actions": [],
            "esign_required": workflow.esign_required,
            "esign_request_id": workflow.esign_request_id
        }
        
        for action in actions:
            audit_data["approval_actions"].append({
                "level_number": action.level_number,
                "approver_email": action.approver_email,
                "action": action.action.value,
                "comment": action.comment,
                "created_at": action.created_at.isoformat(),
                "ip_address": action.ip_address,
                "signature_id": action.signature_id
            })
        
        return audit_data
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Hex digest of SHA256 hash
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _backup_to_cloud(self, local_path: Path, filename: str):
        """
        Backup archived document to cloud storage.
        
        Args:
            local_path: Local file path
            filename: Target filename in cloud
        """
        # Placeholder for cloud backup implementation
        # This would integrate with AWS S3, Azure Blob Storage, etc.
        logger.info(f"Cloud backup: {filename} -> {self.cloud_storage_config.get('provider', 'unknown')}")
        
        # Example implementation for AWS S3:
        # import boto3
        # s3_client = boto3.client('s3')
        # s3_client.upload_file(
        #     str(local_path),
        #     self.cloud_storage_config['bucket'],
        #     f"archival/{filename}"
        # )
    
    def _delete_from_cloud(self, filename: str):
        """
        Delete archived document from cloud storage.
        
        Args:
            filename: Filename in cloud storage
        """
        # Placeholder for cloud deletion implementation
        logger.info(f"Cloud deletion: {filename} from {self.cloud_storage_config.get('provider', 'unknown')}")
        
        # Example implementation for AWS S3:
        # import boto3
        # s3_client = boto3.client('s3')
        # s3_client.delete_object(
        #     Bucket=self.cloud_storage_config['bucket'],
        #     Key=f"archival/{filename}"
        # )
