"""
QuickBooks Online Connector
Integration with Intuit QuickBooks Online API
"""

import httpx
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from .base import (
    ERPConnector,
    ERPSystem,
    ERPVendor,
    ERPPurchaseOrder,
    ERPInvoice,
    SyncResult,
    SyncStatus,
    ERPEntity
)

logger = logging.getLogger(__name__)


class QuickBooksConnector(ERPConnector):
    """
    QuickBooks Online API Connector
    
    Implements bidirectional sync with QuickBooks Online using OAuth 2.0
    API Documentation: https://developer.intuit.com/app/developer/qbo/docs/api/accounting
    """
    
    API_BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
    AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
    TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    
    # Rate limits: 500 requests/minute per app
    MAX_REQUESTS_PER_MINUTE = 500
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize QuickBooks connector
        
        Required config:
            client_id: OAuth 2.0 client ID
            client_secret: OAuth 2.0 client secret
            realm_id: Company ID (realm ID)
            access_token: OAuth access token
            refresh_token: OAuth refresh token
        """
        super().__init__(connection_config)
        
        self.client_id = connection_config.get("client_id")
        self.client_secret = connection_config.get("client_secret")
        self.realm_id = connection_config.get("realm_id")
        self.access_token = connection_config.get("access_token")
        self.refresh_token = connection_config.get("refresh_token")
        self.token_expires_at = connection_config.get("token_expires_at")
        
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.request_count = 0
        self.request_window_start = datetime.utcnow()
        
    @property
    def system_type(self) -> ERPSystem:
        return ERPSystem.QUICKBOOKS
        
    async def authenticate(self) -> bool:
        """
        Authenticate with QuickBooks Online
        
        Checks if access token is valid, refreshes if needed
        """
        try:
            # Check if token needs refresh
            if self._token_needs_refresh():
                await self._refresh_access_token()
                
            # Test connection
            result = await self.test_connection()
            self.is_authenticated = result.get("success", False)
            return self.is_authenticated
            
        except Exception as e:
            logger.error(f"QuickBooks authentication failed: {e}")
            self.is_authenticated = False
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test QuickBooks connection by querying company info"""
        try:
            url = f"{self.API_BASE_URL}/{self.realm_id}/companyinfo/{self.realm_id}"
            headers = self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            company_info = data.get("CompanyInfo", {})
            
            return {
                "success": True,
                "company_name": company_info.get("CompanyName"),
                "country": company_info.get("Country"),
                "fiscal_year_start": company_info.get("FiscalYearStartMonth"),
                "connected_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"QuickBooks connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def import_vendors(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import vendors from QuickBooks
        
        QuickBooks API: Query Vendor entities
        """
        result = SyncResult(
            entity_type=ERPEntity.VENDOR,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            self._log_sync_start(ERPEntity.VENDOR)
            
            # Build query
            query = "SELECT * FROM Vendor WHERE Active = true"
            if since:
                query += f" AND MetaData.LastUpdatedTime > '{since.isoformat()}'"
            if limit:
                query += f" MAXRESULTS {limit}"
            else:
                query += " MAXRESULTS 1000"
                
            # Execute query
            vendors_data = await self._execute_query(query)
            vendors = []
            
            for vendor_data in vendors_data:
                try:
                    vendor = self._parse_vendor(vendor_data)
                    vendors.append(vendor)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(f"Failed to parse vendor {vendor_data.get('Id')}: {e}")
                    
            result.total_count = len(vendors_data)
            result.data = [v.to_dict() for v in vendors]
            result.status = SyncStatus.COMPLETED if result.error_count == 0 else SyncStatus.PARTIAL
            result.completed_at = datetime.utcnow()
            
            self._log_sync_complete(result)
            return result
            
        except Exception as e:
            logger.error(f"QuickBooks vendor import failed: {e}")
            result.status = SyncStatus.FAILED
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            return result
            
    async def import_purchase_orders(
        self,
        since: Optional[datetime] = None,
        status_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import purchase orders from QuickBooks
        
        QuickBooks API: Query PurchaseOrder entities
        """
        result = SyncResult(
            entity_type=ERPEntity.PURCHASE_ORDER,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            self._log_sync_start(ERPEntity.PURCHASE_ORDER)
            
            # Build query
            query = "SELECT * FROM PurchaseOrder"
            conditions = []
            
            if since:
                conditions.append(f"MetaData.LastUpdatedTime > '{since.isoformat()}'")
            if status_filter:
                # QuickBooks doesn't have direct status field, using POStatus
                conditions.append(f"POStatus = '{status_filter}'")
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            if limit:
                query += f" MAXRESULTS {limit}"
            else:
                query += " MAXRESULTS 1000"
                
            # Execute query
            pos_data = await self._execute_query(query)
            purchase_orders = []
            
            for po_data in pos_data:
                try:
                    po = self._parse_purchase_order(po_data)
                    purchase_orders.append(po)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(f"Failed to parse PO {po_data.get('Id')}: {e}")
                    
            result.total_count = len(pos_data)
            result.data = [po.to_dict() for po in purchase_orders]
            result.status = SyncStatus.COMPLETED if result.error_count == 0 else SyncStatus.PARTIAL
            result.completed_at = datetime.utcnow()
            
            self._log_sync_complete(result)
            return result
            
        except Exception as e:
            logger.error(f"QuickBooks PO import failed: {e}")
            result.status = SyncStatus.FAILED
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            return result
            
    async def export_invoice(self, invoice: ERPInvoice) -> Dict[str, Any]:
        """
        Export invoice to QuickBooks as a Bill
        
        QuickBooks API: Create Bill entity
        """
        try:
            url = f"{self.API_BASE_URL}/{self.realm_id}/bill"
            headers = self._get_headers()
            
            # Build Bill payload
            bill_data = {
                "VendorRef": {
                    "value": invoice.vendor_id
                },
                "TxnDate": invoice.invoice_date.strftime("%Y-%m-%d"),
                "DueDate": invoice.due_date.strftime("%Y-%m-%d"),
                "DocNumber": invoice.invoice_number,
                "PrivateNote": invoice.notes or "",
                "Line": []
            }
            
            # Add line items
            for line in invoice.line_items:
                bill_line = {
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "Amount": line.get("amount", 0),
                    "Description": line.get("description", ""),
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {
                            "value": line.get("account_id", "1")  # Default expense account
                        }
                    }
                }
                
                # Add tax if present
                if invoice.tax_amount and line.get("tax_code_id"):
                    bill_line["AccountBasedExpenseLineDetail"]["TaxCodeRef"] = {
                        "value": line.get("tax_code_id")
                    }
                    
                bill_data["Line"].append(bill_line)
                
            # Create bill
            response = await self.http_client.post(
                url,
                headers=headers,
                json=bill_data
            )
            response.raise_for_status()
            
            result = response.json()
            bill = result.get("Bill", {})
            
            logger.info(f"Exported invoice {invoice.invoice_number} to QuickBooks Bill ID {bill.get('Id')}")
            
            return {
                "success": True,
                "external_id": bill.get("Id"),
                "external_number": bill.get("DocNumber"),
                "exported_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"QuickBooks invoice export failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def sync_payment_status(self, external_invoice_id: str) -> Dict[str, Any]:
        """
        Sync payment status from QuickBooks
        
        Query Bill and related BillPayment entities
        """
        try:
            # Get bill details
            url = f"{self.API_BASE_URL}/{self.realm_id}/bill/{external_invoice_id}"
            headers = self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            bill = data.get("Bill", {})
            
            balance = float(bill.get("Balance", 0))
            total_amount = float(bill.get("TotalAmt", 0))
            
            # Check if fully paid
            is_paid = balance == 0 and total_amount > 0
            
            # Query for bill payments
            query = f"SELECT * FROM BillPayment WHERE Line.LinkedTxn.TxnId = '{external_invoice_id}'"
            payments_data = await self._execute_query(query)
            
            payments = []
            for payment_data in payments_data:
                payments.append({
                    "payment_id": payment_data.get("Id"),
                    "payment_date": payment_data.get("TxnDate"),
                    "amount": payment_data.get("TotalAmt"),
                    "payment_method": payment_data.get("PayType")
                })
                
            return {
                "success": True,
                "is_paid": is_paid,
                "balance": balance,
                "total_amount": total_amount,
                "payments": payments,
                "synced_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"QuickBooks payment sync failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get chart of accounts from QuickBooks"""
        try:
            query = "SELECT * FROM Account WHERE Active = true"
            accounts_data = await self._execute_query(query)
            
            accounts = []
            for account in accounts_data:
                accounts.append({
                    "id": account.get("Id"),
                    "name": account.get("Name"),
                    "type": account.get("AccountType"),
                    "number": account.get("AcctNum"),
                    "balance": account.get("CurrentBalance"),
                    "currency": account.get("CurrencyRef", {}).get("value", "USD")
                })
                
            return accounts
            
        except Exception as e:
            logger.error(f"QuickBooks accounts query failed: {e}")
            return []
            
    async def get_tax_codes(self) -> List[Dict[str, Any]]:
        """Get tax codes from QuickBooks"""
        try:
            query = "SELECT * FROM TaxCode WHERE Active = true"
            tax_codes_data = await self._execute_query(query)
            
            tax_codes = []
            for tax_code in tax_codes_data:
                tax_codes.append({
                    "id": tax_code.get("Id"),
                    "name": tax_code.get("Name"),
                    "description": tax_code.get("Description"),
                    "taxable": tax_code.get("Taxable", False)
                })
                
            return tax_codes
            
        except Exception as e:
            logger.error(f"QuickBooks tax codes query failed: {e}")
            return []
            
    async def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute QuickBooks query
        
        Handles rate limiting and pagination
        """
        await self._check_rate_limit()
        
        url = f"{self.API_BASE_URL}/{self.realm_id}/query"
        params = {"query": query}
        headers = self._get_headers()
        
        response = await self.http_client.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        query_response = data.get("QueryResponse", {})
        
        # Get the entity name from query (e.g., "Vendor" from "SELECT * FROM Vendor")
        entity_name = query.split("FROM")[1].strip().split()[0]
        
        return query_response.get(entity_name, [])
        
    async def _refresh_access_token(self):
        """Refresh OAuth 2.0 access token"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            auth = (self.client_id, self.client_secret)
            
            response = await self.http_client.post(
                self.TOKEN_URL,
                data=data,
                auth=auth
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("QuickBooks access token refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh QuickBooks token: {e}")
            raise
            
    def _token_needs_refresh(self) -> bool:
        """Check if access token needs refresh"""
        if not self.token_expires_at:
            return True
            
        # Refresh 5 minutes before expiration
        buffer = timedelta(minutes=5)
        return datetime.utcnow() >= (self.token_expires_at - buffer)
        
    async def _check_rate_limit(self):
        """Check and enforce rate limits"""
        now = datetime.utcnow()
        
        # Reset counter if window expired
        if (now - self.request_window_start).total_seconds() >= 60:
            self.request_count = 0
            self.request_window_start = now
            
        # Wait if at limit
        if self.request_count >= self.MAX_REQUESTS_PER_MINUTE:
            wait_time = 60 - (now - self.request_window_start).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.request_window_start = datetime.utcnow()
                
        self.request_count += 1
        
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    def _parse_vendor(self, vendor_data: Dict[str, Any]) -> ERPVendor:
        """Parse QuickBooks Vendor to ERPVendor"""
        address_data = vendor_data.get("BillAddr", {})
        
        return ERPVendor(
            external_id=vendor_data.get("Id"),
            name=vendor_data.get("DisplayName", ""),
            email=vendor_data.get("PrimaryEmailAddr", {}).get("Address"),
            phone=vendor_data.get("PrimaryPhone", {}).get("FreeFormNumber"),
            address={
                "line1": address_data.get("Line1", ""),
                "line2": address_data.get("Line2", ""),
                "city": address_data.get("City", ""),
                "state": address_data.get("CountrySubDivisionCode", ""),
                "postal_code": address_data.get("PostalCode", ""),
                "country": address_data.get("Country", "")
            },
            tax_id=vendor_data.get("TaxIdentifier"),
            payment_terms=vendor_data.get("TermRef", {}).get("name"),
            account_number=vendor_data.get("AcctNum"),
            is_active=vendor_data.get("Active", True),
            metadata={
                "company_name": vendor_data.get("CompanyName"),
                "balance": vendor_data.get("Balance"),
                "currency": vendor_data.get("CurrencyRef", {}).get("value", "USD")
            }
        )
        
    def _parse_purchase_order(self, po_data: Dict[str, Any]) -> ERPPurchaseOrder:
        """Parse QuickBooks PurchaseOrder to ERPPurchaseOrder"""
        vendor_ref = po_data.get("VendorRef", {})
        
        line_items = []
        for line in po_data.get("Line", []):
            if line.get("DetailType") == "ItemBasedExpenseLineDetail":
                detail = line.get("ItemBasedExpenseLineDetail", {})
                line_items.append({
                    "description": line.get("Description", ""),
                    "quantity": detail.get("Qty", 1),
                    "unit_price": detail.get("UnitPrice", 0),
                    "amount": line.get("Amount", 0),
                    "item_id": detail.get("ItemRef", {}).get("value")
                })
                
        return ERPPurchaseOrder(
            external_id=po_data.get("Id"),
            po_number=po_data.get("DocNumber", ""),
            vendor_id=vendor_ref.get("value", ""),
            vendor_name=vendor_ref.get("name", ""),
            total_amount=float(po_data.get("TotalAmt", 0)),
            currency=po_data.get("CurrencyRef", {}).get("value", "USD"),
            status=po_data.get("POStatus", "open").lower(),
            created_date=datetime.fromisoformat(po_data.get("TxnDate")) if po_data.get("TxnDate") else None,
            expected_date=datetime.fromisoformat(po_data.get("ShipDate")) if po_data.get("ShipDate") else None,
            line_items=line_items,
            metadata={
                "po_email": po_data.get("POEmail", {}).get("Address"),
                "ship_address": po_data.get("ShipAddr", {}),
                "memo": po_data.get("Memo")
            }
        )
        
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
        await super().close()


# Import asyncio for sleep in rate limiting
import asyncio
