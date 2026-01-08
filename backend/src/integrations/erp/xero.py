"""
Xero Connector
Integration with Xero Accounting API
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


class XeroConnector(ERPConnector):
    """
    Xero Accounting API Connector
    
    Implements bidirectional sync with Xero using OAuth 2.0
    API Documentation: https://developer.xero.com/documentation/api/accounting/overview
    """
    
    API_BASE_URL = "https://api.xero.com/api.xro/2.0"
    AUTH_URL = "https://login.xero.com/identity/connect/authorize"
    TOKEN_URL = "https://identity.xero.com/connect/token"
    CONNECTIONS_URL = "https://api.xero.com/connections"
    
    # Rate limits: 60 requests/minute, 5000 requests/day
    MAX_REQUESTS_PER_MINUTE = 60
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize Xero connector
        
        Required config:
            client_id: OAuth 2.0 client ID
            client_secret: OAuth 2.0 client secret
            tenant_id: Xero tenant (organization) ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
        """
        super().__init__(connection_config)
        
        self.client_id = connection_config.get("client_id")
        self.client_secret = connection_config.get("client_secret")
        self.tenant_id = connection_config.get("tenant_id")
        self.access_token = connection_config.get("access_token")
        self.refresh_token = connection_config.get("refresh_token")
        self.token_expires_at = connection_config.get("token_expires_at")
        
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.request_count = 0
        self.request_window_start = datetime.utcnow()
        
    @property
    def system_type(self) -> ERPSystem:
        return ERPSystem.XERO
        
    async def authenticate(self) -> bool:
        """Authenticate with Xero"""
        try:
            if self._token_needs_refresh():
                await self._refresh_access_token()
                
            result = await self.test_connection()
            self.is_authenticated = result.get("success", False)
            return self.is_authenticated
            
        except Exception as e:
            logger.error(f"Xero authentication failed: {e}")
            self.is_authenticated = False
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test Xero connection by querying organization info"""
        try:
            url = f"{self.API_BASE_URL}/Organisation"
            headers = self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            organisations = data.get("Organisations", [])
            
            if organisations:
                org = organisations[0]
                return {
                    "success": True,
                    "organisation_name": org.get("Name"),
                    "country_code": org.get("CountryCode"),
                    "base_currency": org.get("BaseCurrency"),
                    "connected_at": datetime.utcnow().isoformat()
                }
            else:
                return {"success": False, "error": "No organisation found"}
                
        except Exception as e:
            logger.error(f"Xero connection test failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def import_vendors(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import suppliers from Xero (Contacts with ContactType=Supplier)
        """
        result = SyncResult(
            entity_type=ERPEntity.VENDOR,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            self._log_sync_start(ERPEntity.VENDOR)
            
            url = f"{self.API_BASE_URL}/Contacts"
            params = {"where": 'IsSupplier==true'}
            
            if since:
                params["where"] += f' AND UpdatedDateUTC >= DateTime({since.year},{since.month},{since.day})'
                
            if limit:
                params["page"] = 1
                params["pageSize"] = min(limit, 100)
                
            vendors_data = await self._make_request("GET", url, params=params)
            contacts = vendors_data.get("Contacts", [])
            
            vendors = []
            for contact_data in contacts:
                try:
                    vendor = self._parse_vendor(contact_data)
                    vendors.append(vendor)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(f"Failed to parse contact {contact_data.get('ContactID')}: {e}")
                    
            result.total_count = len(contacts)
            result.data = [v.to_dict() for v in vendors]
            result.status = SyncStatus.COMPLETED if result.error_count == 0 else SyncStatus.PARTIAL
            result.completed_at = datetime.utcnow()
            
            self._log_sync_complete(result)
            return result
            
        except Exception as e:
            logger.error(f"Xero vendor import failed: {e}")
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
        """Import purchase orders from Xero"""
        result = SyncResult(
            entity_type=ERPEntity.PURCHASE_ORDER,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            self._log_sync_start(ERPEntity.PURCHASE_ORDER)
            
            url = f"{self.API_BASE_URL}/PurchaseOrders"
            params = {}
            
            where_clauses = []
            if since:
                where_clauses.append(f'UpdatedDateUTC >= DateTime({since.year},{since.month},{since.day})')
            if status_filter:
                status_map = {"open": "SUBMITTED", "closed": "BILLED"}
                xero_status = status_map.get(status_filter.lower(), status_filter.upper())
                where_clauses.append(f'Status=="{xero_status}"')
                
            if where_clauses:
                params["where"] = " AND ".join(where_clauses)
                
            if limit:
                params["page"] = 1
                params["pageSize"] = min(limit, 100)
                
            pos_data = await self._make_request("GET", url, params=params)
            purchase_orders_data = pos_data.get("PurchaseOrders", [])
            
            purchase_orders = []
            for po_data in purchase_orders_data:
                try:
                    po = self._parse_purchase_order(po_data)
                    purchase_orders.append(po)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(f"Failed to parse PO {po_data.get('PurchaseOrderID')}: {e}")
                    
            result.total_count = len(purchase_orders_data)
            result.data = [po.to_dict() for po in purchase_orders]
            result.status = SyncStatus.COMPLETED if result.error_count == 0 else SyncStatus.PARTIAL
            result.completed_at = datetime.utcnow()
            
            self._log_sync_complete(result)
            return result
            
        except Exception as e:
            logger.error(f"Xero PO import failed: {e}")
            result.status = SyncStatus.FAILED
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            return result
            
    async def export_invoice(self, invoice: ERPInvoice) -> Dict[str, Any]:
        """
        Export invoice to Xero as a Bill
        
        Xero API: Create Bill (Invoice with Type=ACCPAY)
        """
        try:
            url = f"{self.API_BASE_URL}/Invoices"
            
            # Build Bill payload
            bill_data = {
                "Type": "ACCPAY",  # Accounts Payable
                "Contact": {
                    "ContactID": invoice.vendor_id
                },
                "Date": invoice.invoice_date.strftime("%Y-%m-%d"),
                "DueDate": invoice.due_date.strftime("%Y-%m-%d"),
                "InvoiceNumber": invoice.invoice_number,
                "Reference": invoice.po_number or "",
                "Status": "AUTHORISED",
                "LineItems": []
            }
            
            # Add line items
            for line in invoice.line_items:
                line_item = {
                    "Description": line.get("description", ""),
                    "Quantity": line.get("quantity", 1),
                    "UnitAmount": line.get("unit_price", 0),
                    "AccountCode": line.get("account_code", "200"),  # Default expense account
                    "TaxType": line.get("tax_code", "NONE")
                }
                bill_data["LineItems"].append(line_item)
                
            # Create bill
            response_data = await self._make_request("POST", url, json_data={"Invoices": [bill_data]})
            
            invoices = response_data.get("Invoices", [])
            if invoices:
                created_bill = invoices[0]
                logger.info(f"Exported invoice {invoice.invoice_number} to Xero Bill ID {created_bill.get('InvoiceID')}")
                
                return {
                    "success": True,
                    "external_id": created_bill.get("InvoiceID"),
                    "external_number": created_bill.get("InvoiceNumber"),
                    "exported_at": datetime.utcnow().isoformat()
                }
            else:
                return {"success": False, "error": "No invoice created"}
                
        except Exception as e:
            logger.error(f"Xero invoice export failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def sync_payment_status(self, external_invoice_id: str) -> Dict[str, Any]:
        """Sync payment status from Xero"""
        try:
            url = f"{self.API_BASE_URL}/Invoices/{external_invoice_id}"
            
            response_data = await self._make_request("GET", url)
            invoices = response_data.get("Invoices", [])
            
            if not invoices:
                return {"success": False, "error": "Invoice not found"}
                
            invoice = invoices[0]
            
            status = invoice.get("Status", "")
            amount_due = float(invoice.get("AmountDue", 0))
            total_amount = float(invoice.get("Total", 0))
            amount_paid = float(invoice.get("AmountPaid", 0))
            
            is_paid = status == "PAID" or amount_due == 0
            
            # Get payments
            payments = []
            for payment in invoice.get("Payments", []):
                payments.append({
                    "payment_id": payment.get("PaymentID"),
                    "payment_date": payment.get("Date"),
                    "amount": payment.get("Amount"),
                    "reference": payment.get("Reference")
                })
                
            return {
                "success": True,
                "is_paid": is_paid,
                "status": status,
                "balance": amount_due,
                "total_amount": total_amount,
                "amount_paid": amount_paid,
                "payments": payments,
                "synced_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Xero payment sync failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get chart of accounts from Xero"""
        try:
            url = f"{self.API_BASE_URL}/Accounts"
            response_data = await self._make_request("GET", url)
            
            accounts_data = response_data.get("Accounts", [])
            accounts = []
            
            for account in accounts_data:
                if account.get("Status") == "ACTIVE":
                    accounts.append({
                        "id": account.get("AccountID"),
                        "code": account.get("Code"),
                        "name": account.get("Name"),
                        "type": account.get("Type"),
                        "class": account.get("Class"),
                        "tax_type": account.get("TaxType")
                    })
                    
            return accounts
            
        except Exception as e:
            logger.error(f"Xero accounts query failed: {e}")
            return []
            
    async def get_tax_codes(self) -> List[Dict[str, Any]]:
        """Get tax rates from Xero"""
        try:
            url = f"{self.API_BASE_URL}/TaxRates"
            response_data = await self._make_request("GET", url)
            
            tax_rates_data = response_data.get("TaxRates", [])
            tax_codes = []
            
            for tax_rate in tax_rates_data:
                if tax_rate.get("Status") == "ACTIVE":
                    tax_codes.append({
                        "name": tax_rate.get("Name"),
                        "rate": tax_rate.get("EffectiveRate"),
                        "type": tax_rate.get("TaxType"),
                        "can_apply_to_expenses": tax_rate.get("CanApplyToExpenses", False)
                    })
                    
            return tax_codes
            
        except Exception as e:
            logger.error(f"Xero tax rates query failed: {e}")
            return []
            
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Xero API with rate limiting"""
        await self._check_rate_limit()
        
        headers = self._get_headers()
        
        response = await self.http_client.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        
        return response.json()
        
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
            
            expires_in = token_data.get("expires_in", 1800)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("Xero access token refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh Xero token: {e}")
            raise
            
    def _token_needs_refresh(self) -> bool:
        """Check if access token needs refresh"""
        if not self.token_expires_at:
            return True
            
        buffer = timedelta(minutes=5)
        return datetime.utcnow() >= (self.token_expires_at - buffer)
        
    async def _check_rate_limit(self):
        """Check and enforce rate limits"""
        import asyncio
        
        now = datetime.utcnow()
        
        if (now - self.request_window_start).total_seconds() >= 60:
            self.request_count = 0
            self.request_window_start = now
            
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
            "Xero-tenant-id": self.tenant_id,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    def _parse_vendor(self, contact_data: Dict[str, Any]) -> ERPVendor:
        """Parse Xero Contact to ERPVendor"""
        addresses = contact_data.get("Addresses", [])
        postal_address = next((addr for addr in addresses if addr.get("AddressType") == "POBOX"), {})
        
        phones = contact_data.get("Phones", [])
        phone = next((p.get("PhoneNumber") for p in phones if p.get("PhoneType") == "DEFAULT"), None)
        
        return ERPVendor(
            external_id=contact_data.get("ContactID"),
            name=contact_data.get("Name", ""),
            email=contact_data.get("EmailAddress"),
            phone=phone,
            address={
                "line1": postal_address.get("AddressLine1", ""),
                "line2": postal_address.get("AddressLine2", ""),
                "city": postal_address.get("City", ""),
                "state": postal_address.get("Region", ""),
                "postal_code": postal_address.get("PostalCode", ""),
                "country": postal_address.get("Country", "")
            },
            tax_id=contact_data.get("TaxNumber"),
            account_number=contact_data.get("AccountNumber"),
            is_active=contact_data.get("ContactStatus") == "ACTIVE",
            metadata={
                "contact_number": contact_data.get("ContactNumber"),
                "accounts_payable_balance": contact_data.get("Balances", {}).get("AccountsPayable", {}).get("Outstanding")
            }
        )
        
    def _parse_purchase_order(self, po_data: Dict[str, Any]) -> ERPPurchaseOrder:
        """Parse Xero PurchaseOrder to ERPPurchaseOrder"""
        contact = po_data.get("Contact", {})
        
        line_items = []
        for line in po_data.get("LineItems", []):
            line_items.append({
                "description": line.get("Description", ""),
                "quantity": line.get("Quantity", 1),
                "unit_price": line.get("UnitAmount", 0),
                "amount": line.get("LineAmount", 0),
                "account_code": line.get("AccountCode"),
                "tax_type": line.get("TaxType")
            })
            
        return ERPPurchaseOrder(
            external_id=po_data.get("PurchaseOrderID"),
            po_number=po_data.get("PurchaseOrderNumber", ""),
            vendor_id=contact.get("ContactID", ""),
            vendor_name=contact.get("Name", ""),
            total_amount=float(po_data.get("Total", 0)),
            currency=po_data.get("CurrencyCode", "USD"),
            status=po_data.get("Status", "").lower(),
            created_date=datetime.fromisoformat(po_data["Date"].replace("Z", "+00:00")) if po_data.get("Date") else None,
            expected_date=datetime.fromisoformat(po_data["DeliveryDate"].replace("Z", "+00:00")) if po_data.get("DeliveryDate") else None,
            line_items=line_items,
            metadata={
                "reference": po_data.get("Reference"),
                "delivery_address": po_data.get("DeliveryAddress"),
                "attention_to": po_data.get("AttentionTo")
            }
        )
        
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
        await super().close()
