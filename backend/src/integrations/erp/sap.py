"""
SAP Business One / S/4HANA Connector
Integration with SAP Service Layer API
"""

import httpx
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

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


class SAPConnector(ERPConnector):
    """
    SAP Business One / S/4HANA Connector
    
    Implements bidirectional sync with SAP using Service Layer API
    API Documentation: https://help.sap.com/doc/0d2533ad95474d6b9828fbb2806ba6e0/
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize SAP connector
        
        Required config:
            service_layer_url: SAP Service Layer URL
            company_db: Company database name
            username: SAP username
            password: SAP password
        """
        super().__init__(connection_config)
        
        self.service_layer_url = connection_config.get("service_layer_url")
        self.company_db = connection_config.get("company_db")
        self.username = connection_config.get("username")
        self.password = connection_config.get("password")
        
        self.api_base_url = f"{self.service_layer_url}/b1s/v1"
        self.session_id = None
        self.session_timeout = None
        
        self.http_client = httpx.AsyncClient(
            timeout=60.0,
            verify=connection_config.get("verify_ssl", True)
        )
        
    @property
    def system_type(self) -> ERPSystem:
        return ERPSystem.SAP
        
    async def authenticate(self) -> bool:
        """Authenticate with SAP Service Layer"""
        try:
            url = f"{self.service_layer_url}/b1s/v1/Login"
            
            login_data = {
                "CompanyDB": self.company_db,
                "UserName": self.username,
                "Password": self.password
            }
            
            response = await self.http_client.post(url, json=login_data)
            response.raise_for_status()
            
            # SAP returns session ID in cookies
            self.session_id = response.cookies.get("B1SESSION")
            
            if self.session_id:
                self.is_authenticated = True
                logger.info(f"SAP authentication successful for company {self.company_db}")
                return True
            else:
                self.is_authenticated = False
                return False
                
        except Exception as e:
            logger.error(f"SAP authentication failed: {e}")
            self.is_authenticated = False
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test SAP connection by querying company info"""
        try:
            url = f"{self.api_base_url}/CompanyService_GetCompanyInfo"
            headers = self._get_headers()
            
            response = await self.http_client.get(url, headers=headers, cookies=self._get_cookies())
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "success": True,
                "company_name": data.get("CompanyName"),
                "database": self.company_db,
                "connected_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SAP connection test failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def import_vendors(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> SyncResult:
        """
        Import business partners (suppliers) from SAP
        
        SAP API: Query BusinessPartners with CardType='S' (Supplier)
        """
        result = SyncResult(
            entity_type=ERPEntity.VENDOR,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            self._log_sync_start(ERPEntity.VENDOR)
            
            # Build OData filter
            filter_parts = ["CardType eq 'S'"]  # Supplier type
            
            if since:
                since_str = since.strftime("%Y-%m-%d")
                filter_parts.append(f"UpdateDate ge '{since_str}'")
                
            filter_query = " and ".join(filter_parts)
            
            url = f"{self.api_base_url}/BusinessPartners"
            params = {"$filter": filter_query}
            
            if limit:
                params["$top"] = limit
                
            vendors_data = await self._make_request("GET", url, params=params)
            business_partners = vendors_data.get("value", [])
            
            vendors = []
            for bp_data in business_partners:
                try:
                    vendor = self._parse_vendor(bp_data)
                    vendors.append(vendor)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(f"Failed to parse BP {bp_data.get('CardCode')}: {e}")
                    
            result.total_count = len(business_partners)
            result.data = [v.to_dict() for v in vendors]
            result.status = SyncStatus.COMPLETED if result.error_count == 0 else SyncStatus.PARTIAL
            result.completed_at = datetime.utcnow()
            
            self._log_sync_complete(result)
            return result
            
        except Exception as e:
            logger.error(f"SAP vendor import failed: {e}")
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
        Import purchase orders from SAP
        
        SAP API: Query PurchaseOrders
        """
        result = SyncResult(
            entity_type=ERPEntity.PURCHASE_ORDER,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            self._log_sync_start(ERPEntity.PURCHASE_ORDER)
            
            filter_parts = []
            
            if since:
                since_str = since.strftime("%Y-%m-%d")
                filter_parts.append(f"DocumentDate ge '{since_str}'")
                
            if status_filter:
                # SAP uses DocumentStatus: O=Open, C=Closed
                status_map = {"open": "O", "closed": "C"}
                sap_status = status_map.get(status_filter.lower(), "O")
                filter_parts.append(f"DocumentStatus eq '{sap_status}'")
                
            url = f"{self.api_base_url}/PurchaseOrders"
            params = {}
            
            if filter_parts:
                params["$filter"] = " and ".join(filter_parts)
                
            if limit:
                params["$top"] = limit
                
            pos_data = await self._make_request("GET", url, params=params)
            purchase_orders_data = pos_data.get("value", [])
            
            purchase_orders = []
            for po_data in purchase_orders_data:
                try:
                    po = self._parse_purchase_order(po_data)
                    purchase_orders.append(po)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(f"Failed to parse PO {po_data.get('DocNum')}: {e}")
                    
            result.total_count = len(purchase_orders_data)
            result.data = [po.to_dict() for po in purchase_orders]
            result.status = SyncStatus.COMPLETED if result.error_count == 0 else SyncStatus.PARTIAL
            result.completed_at = datetime.utcnow()
            
            self._log_sync_complete(result)
            return result
            
        except Exception as e:
            logger.error(f"SAP PO import failed: {e}")
            result.status = SyncStatus.FAILED
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            return result
            
    async def export_invoice(self, invoice: ERPInvoice) -> Dict[str, Any]:
        """
        Export invoice to SAP as Purchase Invoice
        
        SAP API: Create PurchaseInvoices
        """
        try:
            url = f"{self.api_base_url}/PurchaseInvoices"
            
            # Build Purchase Invoice payload
            invoice_data = {
                "CardCode": invoice.vendor_id,
                "DocDate": invoice.invoice_date.strftime("%Y-%m-%d"),
                "DocDueDate": invoice.due_date.strftime("%Y-%m-%d"),
                "NumAtCard": invoice.invoice_number,  # Vendor invoice number
                "Comments": invoice.notes or "",
                "DocumentLines": []
            }
            
            # Add document lines
            for idx, line in enumerate(invoice.line_items):
                doc_line = {
                    "LineNum": idx,
                    "ItemDescription": line.get("description", ""),
                    "Quantity": line.get("quantity", 1),
                    "UnitPrice": line.get("unit_price", 0),
                    "AccountCode": line.get("gl_account", ""),
                }
                
                # Add tax code if present
                if line.get("tax_code"):
                    doc_line["TaxCode"] = line.get("tax_code")
                    
                # Add purchase order reference if present
                if invoice.po_number and line.get("po_line_num"):
                    doc_line["BaseType"] = 22  # Purchase Order
                    doc_line["BaseEntry"] = line.get("po_doc_entry")
                    doc_line["BaseLine"] = line.get("po_line_num")
                    
                invoice_data["DocumentLines"].append(doc_line)
                
            # Create purchase invoice
            response_data = await self._make_request("POST", url, json_data=invoice_data)
            
            doc_entry = response_data.get("DocEntry")
            doc_num = response_data.get("DocNum")
            
            logger.info(f"Exported invoice {invoice.invoice_number} to SAP DocEntry {doc_entry}")
            
            return {
                "success": True,
                "external_id": str(doc_entry),
                "external_number": str(doc_num),
                "exported_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SAP invoice export failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def sync_payment_status(self, external_invoice_id: str) -> Dict[str, Any]:
        """
        Sync payment status from SAP
        
        Query PurchaseInvoices and related IncomingPayments
        """
        try:
            url = f"{self.api_base_url}/PurchaseInvoices({external_invoice_id})"
            
            response_data = await self._make_request("GET", url)
            
            doc_total = float(response_data.get("DocTotal", 0))
            paid_to_date = float(response_data.get("PaidToDate", 0))
            doc_status = response_data.get("DocumentStatus", "O")
            
            is_paid = doc_status == "C" or paid_to_date >= doc_total
            balance = doc_total - paid_to_date
            
            # Query incoming payments
            payments_filter = f"DocumentLines/any(line: line.DocEntry eq {external_invoice_id} and line.InvType eq 18)"
            payments_url = f"{self.api_base_url}/IncomingPayments"
            payments_data = await self._make_request(
                "GET",
                payments_url,
                params={"$filter": payments_filter}
            )
            
            payments = []
            for payment in payments_data.get("value", []):
                payments.append({
                    "payment_id": payment.get("DocEntry"),
                    "payment_date": payment.get("DocDate"),
                    "amount": payment.get("CashSum", 0),
                    "reference": payment.get("Remarks")
                })
                
            return {
                "success": True,
                "is_paid": is_paid,
                "balance": balance,
                "total_amount": doc_total,
                "amount_paid": paid_to_date,
                "payments": payments,
                "synced_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SAP payment sync failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get chart of accounts from SAP"""
        try:
            url = f"{self.api_base_url}/ChartOfAccounts"
            params = {"$top": 1000}
            
            response_data = await self._make_request("GET", url, params=params)
            accounts_data = response_data.get("value", [])
            
            accounts = []
            for account in accounts_data:
                if account.get("ActiveAccount") == "Y":
                    accounts.append({
                        "code": account.get("Code"),
                        "name": account.get("Name"),
                        "type": account.get("AccountType"),
                        "level": account.get("AccountLevel"),
                        "currency": account.get("CurrencyCode")
                    })
                    
            return accounts
            
        except Exception as e:
            logger.error(f"SAP accounts query failed: {e}")
            return []
            
    async def get_tax_codes(self) -> List[Dict[str, Any]]:
        """Get tax codes from SAP"""
        try:
            url = f"{self.api_base_url}/SalesTaxCodes"
            params = {"$top": 1000}
            
            response_data = await self._make_request("GET", url, params=params)
            tax_codes_data = response_data.get("value", [])
            
            tax_codes = []
            for tax_code in tax_codes_data:
                if tax_code.get("Inactive") == "N":
                    tax_codes.append({
                        "code": tax_code.get("Code"),
                        "name": tax_code.get("Name"),
                        "rate": tax_code.get("Rate", 0)
                    })
                    
            return tax_codes
            
        except Exception as e:
            logger.error(f"SAP tax codes query failed: {e}")
            return []
            
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to SAP Service Layer API"""
        headers = self._get_headers()
        cookies = self._get_cookies()
        
        response = await self.http_client.request(
            method,
            url,
            headers=headers,
            cookies=cookies,
            params=params,
            json=json_data
        )
        
        # Check if session expired (401) and reauthenticate
        if response.status_code == 401:
            logger.warning("SAP session expired, reauthenticating...")
            await self.authenticate()
            
            # Retry request with new session
            cookies = self._get_cookies()
            response = await self.http_client.request(
                method,
                url,
                headers=headers,
                cookies=cookies,
                params=params,
                json=json_data
            )
            
        response.raise_for_status()
        return response.json()
        
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
    def _get_cookies(self) -> Dict[str, str]:
        """Get session cookies"""
        return {"B1SESSION": self.session_id} if self.session_id else {}
        
    def _parse_vendor(self, bp_data: Dict[str, Any]) -> ERPVendor:
        """Parse SAP BusinessPartner to ERPVendor"""
        addresses = bp_data.get("BPAddresses", [])
        address = addresses[0] if addresses else {}
        
        return ERPVendor(
            external_id=bp_data.get("CardCode"),
            name=bp_data.get("CardName", ""),
            email=bp_data.get("EmailAddress"),
            phone=bp_data.get("Phone1"),
            address={
                "line1": address.get("Street", ""),
                "line2": address.get("Block", ""),
                "city": address.get("City", ""),
                "state": address.get("State", ""),
                "postal_code": address.get("ZipCode", ""),
                "country": address.get("Country", "")
            },
            tax_id=bp_data.get("FederalTaxID"),
            payment_terms=bp_data.get("PayTermsGrpCode"),
            is_active=bp_data.get("Valid") == "Y",
            metadata={
                "group_code": bp_data.get("GroupCode"),
                "currency": bp_data.get("Currency"),
                "balance": bp_data.get("CurrentAccountBalance")
            }
        )
        
    def _parse_purchase_order(self, po_data: Dict[str, Any]) -> ERPPurchaseOrder:
        """Parse SAP PurchaseOrder to ERPPurchaseOrder"""
        line_items = []
        for line in po_data.get("DocumentLines", []):
            line_items.append({
                "line_num": line.get("LineNum"),
                "description": line.get("ItemDescription", ""),
                "quantity": line.get("Quantity", 1),
                "unit_price": line.get("UnitPrice", 0),
                "amount": line.get("LineTotal", 0),
                "item_code": line.get("ItemCode"),
                "account_code": line.get("AccountCode")
            })
            
        return ERPPurchaseOrder(
            external_id=str(po_data.get("DocEntry")),
            po_number=str(po_data.get("DocNum", "")),
            vendor_id=po_data.get("CardCode", ""),
            vendor_name=po_data.get("CardName", ""),
            total_amount=float(po_data.get("DocTotal", 0)),
            currency=po_data.get("DocCurrency", "USD"),
            status="open" if po_data.get("DocumentStatus") == "O" else "closed",
            created_date=datetime.fromisoformat(po_data["DocDate"]) if po_data.get("DocDate") else None,
            expected_date=datetime.fromisoformat(po_data["DocDueDate"]) if po_data.get("DocDueDate") else None,
            line_items=line_items,
            metadata={
                "comments": po_data.get("Comments"),
                "reference": po_data.get("NumAtCard")
            }
        )
        
    async def close(self):
        """Logout from SAP and close HTTP client"""
        if self.session_id:
            try:
                url = f"{self.service_layer_url}/b1s/v1/Logout"
                await self.http_client.post(url, cookies=self._get_cookies())
                logger.info("SAP session closed")
            except Exception as e:
                logger.error(f"Failed to logout from SAP: {e}")
                
        await self.http_client.aclose()
        await super().close()
