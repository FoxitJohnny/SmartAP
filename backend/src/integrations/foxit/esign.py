"""
Foxit eSign API Integration

Provides integration with Foxit eSign API for digital signature workflows.
Supports document signing, approval workflows, and signature status tracking.

Foxit eSign API Documentation:
https://developers.foxit.com/esign/
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class SignatureStatus(str, Enum):
    """Signature request status"""
    DRAFT = "draft"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SignerRole(str, Enum):
    """Signer role in approval chain"""
    SIGNER = "signer"
    APPROVER = "approver"
    CC = "cc"  # Carbon copy (receive only)
    REVIEWER = "reviewer"


class FoxitESignConnector:
    """
    Foxit eSign API connector for digital signature workflows.
    
    Supports:
    - Document upload and signing
    - Multi-party signature workflows
    - Approval chains
    - Status tracking
    - Webhook notifications
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.esign.foxit.com/v1",
        webhook_url: Optional[str] = None
    ):
        """
        Initialize Foxit eSign connector.
        
        Args:
            api_key: Foxit eSign API key
            api_secret: Foxit eSign API secret
            base_url: API base URL (default: production)
            webhook_url: Webhook URL for status updates
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.webhook_url = webhook_url
        
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                'X-API-Key': api_key,
                'X-API-Secret': api_secret,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        logger.info("Foxit eSign connector initialized")
    
    async def upload_document(
        self,
        file_path: str,
        document_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload document to Foxit eSign for signing.
        
        Args:
            file_path: Path to PDF file
            document_name: Display name for document
            metadata: Optional document metadata
            
        Returns:
            Dictionary with document_id and upload details
        """
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (document_name, f, 'application/pdf')
                }
                
                data = {
                    'name': document_name,
                    'metadata': metadata or {}
                }
                
                # Remove content-type header for multipart
                headers = dict(self.client.headers)
                del headers['Content-Type']
                
                response = await self.client.post(
                    f"{self.base_url}/documents",
                    files=files,
                    data=data,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Document uploaded: {result.get('document_id')}")
                
                return {
                    'document_id': result.get('document_id'),
                    'document_name': document_name,
                    'file_size': result.get('file_size'),
                    'page_count': result.get('page_count'),
                    'uploaded_at': datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Failed to upload document: {str(e)}")
            raise
    
    async def create_signature_request(
        self,
        document_id: str,
        signers: List[Dict[str, Any]],
        subject: str,
        message: Optional[str] = None,
        expires_in_days: int = 30,
        reminder_frequency: int = 3,
        require_all_signers: bool = True
    ) -> Dict[str, Any]:
        """
        Create signature request for document.
        
        Args:
            document_id: Document ID from upload
            signers: List of signer details [{email, name, role, order}]
            subject: Email subject for signature request
            message: Custom message to signers
            expires_in_days: Days until request expires
            reminder_frequency: Days between reminder emails
            require_all_signers: Whether all signers must sign
            
        Returns:
            Dictionary with signature_request_id and status
        """
        try:
            # Format signers
            formatted_signers = []
            for i, signer in enumerate(signers):
                formatted_signers.append({
                    'email': signer['email'],
                    'name': signer.get('name', signer['email']),
                    'role': signer.get('role', SignerRole.SIGNER),
                    'order': signer.get('order', i + 1),
                    'signature_type': signer.get('signature_type', 'electronic'),
                    'fields': signer.get('fields', [])  # Signature field positions
                })
            
            request_data = {
                'document_id': document_id,
                'subject': subject,
                'message': message or f"Please review and sign: {subject}",
                'signers': formatted_signers,
                'expires_at': (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat(),
                'reminder_frequency_days': reminder_frequency,
                'require_all_signers': require_all_signers,
                'webhook_url': self.webhook_url
            }
            
            response = await self.client.post(
                f"{self.base_url}/signature_requests",
                json=request_data
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Signature request created: {result.get('signature_request_id')}")
            
            return {
                'signature_request_id': result.get('signature_request_id'),
                'status': SignatureStatus.SENT,
                'document_id': document_id,
                'signers': formatted_signers,
                'expires_at': request_data['expires_at'],
                'created_at': datetime.utcnow().isoformat(),
                'signing_url': result.get('signing_url'),
                'signer_urls': result.get('signer_urls', {})  # Map of email -> signing URL
            }
        
        except Exception as e:
            logger.error(f"Failed to create signature request: {str(e)}")
            raise
    
    async def get_signature_status(
        self,
        signature_request_id: str
    ) -> Dict[str, Any]:
        """
        Get status of signature request.
        
        Args:
            signature_request_id: Signature request ID
            
        Returns:
            Dictionary with status and signer details
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/signature_requests/{signature_request_id}"
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse signer status
            signers_status = []
            for signer in result.get('signers', []):
                signers_status.append({
                    'email': signer['email'],
                    'name': signer['name'],
                    'role': signer['role'],
                    'status': signer['status'],  # pending, signed, declined
                    'signed_at': signer.get('signed_at'),
                    'ip_address': signer.get('ip_address'),
                    'user_agent': signer.get('user_agent')
                })
            
            return {
                'signature_request_id': signature_request_id,
                'status': result.get('status'),
                'document_id': result.get('document_id'),
                'signers': signers_status,
                'completed_at': result.get('completed_at'),
                'signed_document_url': result.get('signed_document_url'),
                'audit_trail_url': result.get('audit_trail_url')
            }
        
        except Exception as e:
            logger.error(f"Failed to get signature status: {str(e)}")
            raise
    
    async def download_signed_document(
        self,
        signature_request_id: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Download signed document after completion.
        
        Args:
            signature_request_id: Signature request ID
            output_path: Path to save signed PDF
            
        Returns:
            Dictionary with file details
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/signature_requests/{signature_request_id}/download"
            )
            
            response.raise_for_status()
            
            # Save signed document
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Signed document downloaded: {output_path}")
            
            return {
                'signature_request_id': signature_request_id,
                'file_path': output_path,
                'file_size': len(response.content),
                'downloaded_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to download signed document: {str(e)}")
            raise
    
    async def download_audit_trail(
        self,
        signature_request_id: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Download audit trail PDF for signature request.
        
        Args:
            signature_request_id: Signature request ID
            output_path: Path to save audit trail PDF
            
        Returns:
            Dictionary with file details
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/signature_requests/{signature_request_id}/audit_trail"
            )
            
            response.raise_for_status()
            
            # Save audit trail
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Audit trail downloaded: {output_path}")
            
            return {
                'signature_request_id': signature_request_id,
                'file_path': output_path,
                'file_size': len(response.content),
                'downloaded_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to download audit trail: {str(e)}")
            raise
    
    async def cancel_signature_request(
        self,
        signature_request_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel pending signature request.
        
        Args:
            signature_request_id: Signature request ID
            reason: Optional cancellation reason
            
        Returns:
            Dictionary with cancellation details
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/signature_requests/{signature_request_id}/cancel",
                json={'reason': reason or 'Cancelled by system'}
            )
            
            response.raise_for_status()
            
            logger.info(f"Signature request cancelled: {signature_request_id}")
            
            return {
                'signature_request_id': signature_request_id,
                'status': SignatureStatus.CANCELLED,
                'cancelled_at': datetime.utcnow().isoformat(),
                'reason': reason
            }
        
        except Exception as e:
            logger.error(f"Failed to cancel signature request: {str(e)}")
            raise
    
    async def send_reminder(
        self,
        signature_request_id: str,
        signer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send reminder to pending signers.
        
        Args:
            signature_request_id: Signature request ID
            signer_email: Optional specific signer email (sends to all pending if None)
            
        Returns:
            Dictionary with reminder details
        """
        try:
            data = {}
            if signer_email:
                data['signer_email'] = signer_email
            
            response = await self.client.post(
                f"{self.base_url}/signature_requests/{signature_request_id}/remind",
                json=data
            )
            
            response.raise_for_status()
            
            logger.info(f"Reminder sent for signature request: {signature_request_id}")
            
            return {
                'signature_request_id': signature_request_id,
                'reminded_at': datetime.utcnow().isoformat(),
                'signer_email': signer_email
            }
        
        except Exception as e:
            logger.error(f"Failed to send reminder: {str(e)}")
            raise
    
    async def create_approval_workflow(
        self,
        document_id: str,
        approvers: List[Dict[str, Any]],
        approval_threshold: int,
        subject: str,
        sequential: bool = True
    ) -> Dict[str, Any]:
        """
        Create multi-level approval workflow.
        
        Args:
            document_id: Document ID from upload
            approvers: List of approver details [{email, name, order, level}]
            approval_threshold: Amount requiring approval (for context)
            subject: Approval request subject
            sequential: Whether approvers must approve in order
            
        Returns:
            Dictionary with workflow details
        """
        try:
            # Format approvers with APPROVER role
            formatted_approvers = []
            for approver in approvers:
                formatted_approvers.append({
                    'email': approver['email'],
                    'name': approver.get('name', approver['email']),
                    'role': SignerRole.APPROVER,
                    'order': approver.get('order', approver.get('level', 1)),
                    'level': approver.get('level', 1),
                    'fields': [{
                        'type': 'signature',
                        'page': 1,
                        'required': True
                    }]
                })
            
            workflow_data = {
                'document_id': document_id,
                'subject': f"Approval Required: {subject} (${approval_threshold/100:,.2f})",
                'message': f"Please review and approve this invoice for ${approval_threshold/100:,.2f}",
                'approvers': formatted_approvers,
                'workflow_type': 'sequential' if sequential else 'parallel',
                'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat(),
                'webhook_url': self.webhook_url
            }
            
            response = await self.client.post(
                f"{self.base_url}/approval_workflows",
                json=workflow_data
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Approval workflow created: {result.get('workflow_id')}")
            
            return {
                'workflow_id': result.get('workflow_id'),
                'signature_request_id': result.get('signature_request_id'),
                'status': SignatureStatus.SENT,
                'document_id': document_id,
                'approvers': formatted_approvers,
                'approval_threshold': approval_threshold,
                'sequential': sequential,
                'created_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to create approval workflow: {str(e)}")
            raise
    
    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
        logger.info("Foxit eSign connector closed")
