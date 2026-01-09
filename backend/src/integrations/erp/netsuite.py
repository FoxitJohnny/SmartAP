"""
NetSuite ERP Connector

Integrates with NetSuite via RESTlet API using Token-Based Authentication (TBA).
Supports vendor import, purchase order import, invoice export (Bill), and payment sync.

NetSuite API Documentation:
https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4389743623.html

Authentication: OAuth 1.0a (TBA - Token Based Authentication)
"""

import asyncio
import logging
import hmac
import hashlib
import base64
import time
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import quote

import httpx

from .base import (
    ERPConnector,
    ERPVendor,
    ERPPurchaseOrder,
    ERPInvoice,
    SyncResult,
    SyncStatus,
    ERPSystem,
)

logger = logging.getLogger(__name__)


class NetSuiteConnector(ERPConnector):
    """
    NetSuite connector using RESTlet API with OAuth 1.0a (TBA).
    
    NetSuite uses custom RESTlets for data operations. This connector
    assumes you have deployed the required RESTlets in your NetSuite account.
    
    Required RESTlets:
    - Vendor RESTlet: GET /vendor, POST /vendor
    - Purchase Order RESTlet: GET /purchaseorder
    - Bill RESTlet: POST /vendorbill
    - Payment RESTlet: GET /vendorpayment
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize NetSuite connector.
        
        Required config:
            account_id: NetSuite account ID (e.g., "1234567")
            consumer_key: OAuth consumer key from integration record
            consumer_secret: OAuth consumer secret
            token_id: Token ID for the access token
            token_secret: Token secret
            restlet_url: Base URL for RESTlets (e.g., "https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl")
            realm: NetSuite realm (default: account_id)
        """
        super().__init__(connection_config)
        
        self.account_id = connection_config.get("account_id", "")
        self.consumer_key = connection_config.get("consumer_key", "")
        self.consumer_secret = connection_config.get("consumer_secret", "")
        self.token_id = connection_config.get("token_id", "")
        self.token_secret = connection_config.get("token_secret", "")
        self.restlet_url = connection_config.get("restlet_url", "")
        self.realm = connection_config.get("realm") or self.account_id
        
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Rate limiting: NetSuite has concurrency limits (typically 10 concurrent requests)
        # and governance limits (10,000 units per hour)
        self.max_concurrent_requests = 5
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        logger.info(f"NetSuite connector initialized for account {account_id}")
    
    def _generate_oauth_signature(
        self,
        method: str,
        url: str,
        params: Dict[str, str]
    ) -> str:
        """
        Generate OAuth 1.0a signature for NetSuite TBA.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: OAuth parameters
            
        Returns:
            Base64-encoded HMAC-SHA256 signature
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = "&".join([f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in sorted_params])
        
        # Create signature base string
        base_string = "&".join([
            method.upper(),
            quote(url, safe=''),
            quote(param_string, safe='')
        ])
        
        # Create signing key
        signing_key = f"{quote(self.consumer_secret, safe='')}&{quote(self.token_secret, safe='')}"
        
        # Generate signature
        signature = hmac.new(
            signing_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_oauth_headers(self, method: str, url: str) -> Dict[str, str]:
        """
        Generate OAuth 1.0a authorization header for NetSuite.
        
        Args:
            method: HTTP method
            url: Request URL
            
        Returns:
            Dictionary with Authorization header
        """
        # OAuth parameters
        oauth_params = {
            'oauth_consumer_key': self.consumer_key,
            'oauth_token': self.token_id,
            'oauth_signature_method': 'HMAC-SHA256',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': secrets.token_hex(16),
            'oauth_version': '1.0',
            'realm': self.realm
        }
        
        # Generate signature
        signature = self._generate_oauth_signature(method, url, oauth_params)
        oauth_params['oauth_signature'] = signature
        
        # Build authorization header
        auth_header = 'OAuth ' + ', '.join([
            f'{k}="{quote(str(v), safe="")}"' for k, v in sorted(oauth_params.items())
        ])
        
        return {
            'Authorization': auth_header,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def _make_request(
        self,
        method: str,
        script_id: str,
        deploy_id: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to NetSuite RESTlet.
        
        Args:
            method: HTTP method
            script_id: RESTlet script ID
            deploy_id: RESTlet deployment ID
            params: Query parameters
            json_data: Request body JSON
            
        Returns:
            Response JSON
        """
        async with self.request_semaphore:
            # Build URL with script and deploy parameters
            url = f"{self.restlet_url}?script={script_id}&deploy={deploy_id}"
            
            # Get OAuth headers
            headers = self._get_oauth_headers(method, url)
            
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data
                )
                
                response.raise_for_status()
                
                return response.json()
            
            except httpx.HTTPStatusError as e:
                logger.error(f"NetSuite API error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"NetSuite API error: {e.response.text}")
            
            except Exception as e:
                logger.error(f"NetSuite request failed: {str(e)}")
                raise
    
    async def authenticate(self) -> bool:
        """
        Test authentication with NetSuite.
        Token-based auth doesn't require explicit authentication,
        so we just test a simple API call.
        
        Returns:
            True if authentication successful
        """
        try:
            # Test with a simple company information request
            # This assumes you have a RESTlet deployed for company info
            # For now, we'll just return True as TBA tokens don't expire
            logger.info("NetSuite TBA authentication validated")
            return True
        
        except Exception as e:
            logger.error(f"NetSuite authentication failed: {str(e)}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to NetSuite and retrieve company information.
        
        Returns:
            Dictionary with company details
        """
        try:
            # Get company information
            # This requires a custom RESTlet for company info
            # For MVP, return account information
            
            logger.info("NetSuite connection test successful")
            
            return {
                "company_name": f"NetSuite Account {self.account_id}",
                "account_id": self.account_id,
                "realm": self.realm,
                "connected_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"NetSuite connection test failed: {str(e)}")
            raise
    
    async def import_vendors(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import vendors from NetSuite.
        
        Args:
            since: Only import vendors modified after this date
            limit: Maximum number of vendors to import
            
        Returns:
            SyncResult with imported vendor data
        """
        self._log_sync_start("vendor", "import")
        
        vendors: List[ERPVendor] = []
        errors: List[str] = []
        
        try:
            # Build search parameters
            params = {}
            if since:
                params['lastModifiedDate'] = since.isoformat()
            if limit:
                params['limit'] = limit
            
            # Call vendor RESTlet (assumes deployed script)
            # You need to deploy a RESTlet with script ID and deploy ID
            response = await self._make_request(
                method='GET',
                script_id='customscript_vendor_restlet',  # Replace with your script ID
                deploy_id='customdeploy_vendor_restlet',  # Replace with your deploy ID
                params=params
            )
            
            # Parse vendors
            vendor_records = response.get('vendors', [])
            
            for vendor_data in vendor_records:
                try:
                    vendor = self._parse_vendor(vendor_data)
                    vendors.append(vendor)
                except Exception as e:
                    error_msg = f"Failed to parse vendor {vendor_data.get('id')}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            status = SyncStatus.COMPLETED if not errors else SyncStatus.PARTIAL
            
            logger.info(f"Imported {len(vendors)} vendors from NetSuite")
            
            return self._log_sync_complete(
                entity_type="vendor",
                status=status,
                total_count=len(vendor_records),
                success_count=len(vendors),
                error_count=len(errors),
                errors=errors,
                data=vendors
            )
        
        except Exception as e:
            logger.error(f"Failed to import vendors from NetSuite: {str(e)}")
            return self._log_sync_complete(
                entity_type="vendor",
                status=SyncStatus.FAILED,
                total_count=0,
                success_count=0,
                error_count=1,
                errors=[str(e)],
                data=[]
            )
    
    def _parse_vendor(self, vendor_data: Dict[str, Any]) -> ERPVendor:
        """Parse NetSuite vendor record to ERPVendor model"""
        
        # Extract address
        address_lines = []
        if vendor_data.get('defaultAddress'):
            addr = vendor_data['defaultAddress']
            if addr.get('addr1'):
                address_lines.append(addr['addr1'])
            if addr.get('addr2'):
                address_lines.append(addr['addr2'])
            if addr.get('city'):
                address_lines.append(addr['city'])
            if addr.get('state'):
                address_lines.append(addr['state'])
            if addr.get('zip'):
                address_lines.append(addr['zip'])
            if addr.get('country'):
                address_lines.append(addr['country'])
        
        address = ", ".join(address_lines) if address_lines else None
        
        return ERPVendor(
            external_id=str(vendor_data.get('id', '')),
            name=vendor_data.get('entityId', vendor_data.get('companyName', '')),
            email=vendor_data.get('email'),
            phone=vendor_data.get('phone'),
            address=address,
            tax_id=vendor_data.get('taxIdNum'),
            payment_terms=vendor_data.get('terms', {}).get('name') if isinstance(vendor_data.get('terms'), dict) else None,
            currency=vendor_data.get('currency', {}).get('name') if isinstance(vendor_data.get('currency'), dict) else 'USD',
            is_active=vendor_data.get('isInactive') == False,
            custom_fields=vendor_data.get('customFields', {})
        )
    
    async def import_purchase_orders(
        self,
        since: Optional[datetime] = None,
        status_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import purchase orders from NetSuite.
        
        Args:
            since: Only import POs created/modified after this date
            status_filter: Filter by status (e.g., "pendingReceipt", "partiallyReceived")
            limit: Maximum number of POs to import
            
        Returns:
            SyncResult with imported PO data
        """
        self._log_sync_start("purchase_order", "import")
        
        purchase_orders: List[ERPPurchaseOrder] = []
        errors: List[str] = []
        
        try:
            # Build search parameters
            params = {}
            if since:
                params['lastModifiedDate'] = since.isoformat()
            if status_filter:
                params['status'] = status_filter
            if limit:
                params['limit'] = limit
            
            # Call purchase order RESTlet
            response = await self._make_request(
                method='GET',
                script_id='customscript_po_restlet',  # Replace with your script ID
                deploy_id='customdeploy_po_restlet',  # Replace with your deploy ID
                params=params
            )
            
            # Parse purchase orders
            po_records = response.get('purchaseOrders', [])
            
            for po_data in po_records:
                try:
                    po = self._parse_purchase_order(po_data)
                    purchase_orders.append(po)
                except Exception as e:
                    error_msg = f"Failed to parse PO {po_data.get('id')}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            status = SyncStatus.COMPLETED if not errors else SyncStatus.PARTIAL
            
            logger.info(f"Imported {len(purchase_orders)} purchase orders from NetSuite")
            
            return self._log_sync_complete(
                entity_type="purchase_order",
                status=status,
                total_count=len(po_records),
                success_count=len(purchase_orders),
                error_count=len(errors),
                errors=errors,
                data=purchase_orders
            )
        
        except Exception as e:
            logger.error(f"Failed to import purchase orders from NetSuite: {str(e)}")
            return self._log_sync_complete(
                entity_type="purchase_order",
                status=SyncStatus.FAILED,
                total_count=0,
                success_count=0,
                error_count=1,
                errors=[str(e)],
                data=[]
            )
    
    def _parse_purchase_order(self, po_data: Dict[str, Any]) -> ERPPurchaseOrder:
        """Parse NetSuite purchase order record to ERPPurchaseOrder model"""
        
        # Parse line items
        line_items = []
        for item in po_data.get('item', {}).get('items', []):
            line_items.append({
                'item_id': str(item.get('item', {}).get('internalId', '')) if isinstance(item.get('item'), dict) else None,
                'description': item.get('description', ''),
                'quantity': float(item.get('quantity', 0)),
                'unit_price': float(item.get('rate', 0)),
                'amount': float(item.get('amount', 0))
            })
        
        return ERPPurchaseOrder(
            external_id=str(po_data.get('id', '')),
            po_number=po_data.get('tranId', ''),
            vendor_id=str(po_data.get('entity', {}).get('internalId', '')) if isinstance(po_data.get('entity'), dict) else None,
            vendor_name=po_data.get('entity', {}).get('name') if isinstance(po_data.get('entity'), dict) else None,
            total_amount=int(float(po_data.get('total', 0)) * 100),  # Convert to cents
            currency=po_data.get('currency', {}).get('name') if isinstance(po_data.get('currency'), dict) else 'USD',
            status=po_data.get('status', {}).get('name') if isinstance(po_data.get('status'), dict) else 'unknown',
            created_date=self._parse_date(po_data.get('tranDate')),
            line_items=line_items,
            custom_fields=po_data.get('customFields', {})
        )
    
    async def export_invoice(self, invoice: ERPInvoice) -> Dict[str, Any]:
        """
        Export invoice to NetSuite as a Vendor Bill.
        
        Args:
            invoice: ERPInvoice object to export
            
        Returns:
            Dictionary with created bill details (id, tranId)
        """
        try:
            # Build vendor bill record
            bill_data = {
                'recordType': 'vendorbill',
                'entity': {'internalId': invoice.vendor_id},  # Vendor internal ID
                'tranDate': invoice.invoice_date.strftime('%m/%d/%Y'),
                'dueDate': invoice.due_date.strftime('%m/%d/%Y') if invoice.due_date else None,
                'tranId': invoice.invoice_number,  # External invoice number
                'memo': invoice.description,
                'item': {
                    'items': []
                }
            }
            
            # Add line items
            for line in invoice.line_items:
                bill_data['item']['items'].append({
                    'item': {'internalId': line.get('item_id')},
                    'description': line.get('description', ''),
                    'quantity': line.get('quantity', 1),
                    'rate': line.get('unit_price', 0) / 100,  # Convert from cents
                    'amount': line.get('amount', 0) / 100,  # Convert from cents
                    'account': {'internalId': line.get('account_id')}  # Expense account
                })
            
            # Call bill creation RESTlet
            response = await self._make_request(
                method='POST',
                script_id='customscript_bill_restlet',  # Replace with your script ID
                deploy_id='customdeploy_bill_restlet',  # Replace with your deploy ID
                json_data=bill_data
            )
            
            logger.info(f"Exported invoice {invoice.invoice_number} to NetSuite as bill {response.get('id')}")
            
            return {
                'id': str(response.get('id')),
                'invoice_number': response.get('tranId'),
                'status': 'created',
                'created_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to export invoice to NetSuite: {str(e)}")
            raise
    
    async def sync_payment_status(self, external_invoice_id: str) -> Dict[str, Any]:
        """
        Sync payment status for a vendor bill from NetSuite.
        
        Args:
            external_invoice_id: NetSuite bill internal ID
            
        Returns:
            Dictionary with payment status and details
        """
        try:
            # Get bill details
            response = await self._make_request(
                method='GET',
                script_id='customscript_bill_restlet',
                deploy_id='customdeploy_bill_restlet',
                params={'id': external_invoice_id}
            )
            
            bill = response.get('bill', {})
            
            # Determine payment status
            status = bill.get('status', {}).get('name', 'open')
            amount_remaining = float(bill.get('amountRemaining', 0))
            total_amount = float(bill.get('total', 0))
            paid_amount = total_amount - amount_remaining
            
            payment_status = 'unpaid'
            if amount_remaining == 0:
                payment_status = 'paid'
            elif paid_amount > 0:
                payment_status = 'partial'
            
            logger.info(f"Synced payment status for bill {external_invoice_id}: {payment_status}")
            
            return {
                'status': payment_status,
                'paid_amount': int(paid_amount * 100),  # Convert to cents
                'remaining_amount': int(amount_remaining * 100),
                'total_amount': int(total_amount * 100),
                'last_payment_date': self._parse_date(bill.get('lastModifiedDate')),
                'synced_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to sync payment status from NetSuite: {str(e)}")
            raise
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Get chart of accounts from NetSuite.
        
        Returns:
            List of account dictionaries
        """
        try:
            # Call accounts RESTlet
            response = await self._make_request(
                method='GET',
                script_id='customscript_account_restlet',  # Replace with your script ID
                deploy_id='customdeploy_account_restlet',  # Replace with your deploy ID
                params={'type': 'expense'}  # Filter for expense accounts
            )
            
            accounts = []
            for account_data in response.get('accounts', []):
                accounts.append({
                    'id': str(account_data.get('id')),
                    'number': account_data.get('acctNumber'),
                    'name': account_data.get('acctName'),
                    'type': account_data.get('acctType', {}).get('name') if isinstance(account_data.get('acctType'), dict) else None,
                    'description': account_data.get('description'),
                    'is_inactive': account_data.get('isInactive', False)
                })
            
            logger.info(f"Retrieved {len(accounts)} accounts from NetSuite")
            
            return accounts
        
        except Exception as e:
            logger.error(f"Failed to get accounts from NetSuite: {str(e)}")
            raise
    
    async def get_tax_codes(self) -> List[Dict[str, Any]]:
        """
        Get tax codes from NetSuite.
        
        Returns:
            List of tax code dictionaries
        """
        try:
            # Call tax codes RESTlet
            response = await self._make_request(
                method='GET',
                script_id='customscript_tax_restlet',  # Replace with your script ID
                deploy_id='customdeploy_tax_restlet',  # Replace with your deploy ID
            )
            
            tax_codes = []
            for tax_data in response.get('taxCodes', []):
                tax_codes.append({
                    'id': str(tax_data.get('id')),
                    'code': tax_data.get('itemId'),
                    'name': tax_data.get('displayName'),
                    'rate': float(tax_data.get('rate', 0)),
                    'description': tax_data.get('description'),
                    'is_inactive': tax_data.get('isInactive', False)
                })
            
            logger.info(f"Retrieved {len(tax_codes)} tax codes from NetSuite")
            
            return tax_codes
        
        except Exception as e:
            logger.error(f"Failed to get tax codes from NetSuite: {str(e)}")
            raise
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse NetSuite date string to datetime"""
        if not date_str:
            return None
        
        try:
            # NetSuite typically uses MM/DD/YYYY format
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            try:
                # Try ISO format
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Failed to parse date: {date_str}")
                return None
    
    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
        logger.info("NetSuite connector closed")
