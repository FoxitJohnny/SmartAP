"""
Example Plugin: Custom ERP Connector

This agent demonstrates how to create a custom ERP integration
for pushing approved invoices to your company's ERP system.
"""

import time
from typing import Dict, Any, Optional
import httpx

from src.plugins import BaseAgent, AgentContext, AgentResult, AgentStatus


class CustomERPConnector(BaseAgent):
    """
    Custom ERP connector for pushing invoices to company ERP.
    
    This example shows how to:
    1. Create a custom integration agent
    2. Connect to external ERP APIs
    3. Transform invoice data to ERP format
    4. Handle API errors and retries
    
    Usage:
        >>> from plugins.custom_erp import CustomERPConnector
        >>> from src.plugins import AgentContext, register_agent
        >>> 
        >>> # Register the agent
        >>> connector = CustomERPConnector(
        ...     api_url="https://erp.mycompany.com/api",
        ...     api_key="your_api_key"
        ... )
        >>> register_agent(connector)
        >>> 
        >>> # Use to push invoice
        >>> context = AgentContext(
        ...     invoice_id="123",
        ...     pdf_bytes=pdf_data,
        ...     extracted_data=invoice_data
        ... )
        >>> result = await connector.process(context)
        >>> print(result.data["erp_invoice_id"])
    """
    
    def __init__(
        self,
        api_url: str = "https://erp.example.com/api",
        api_key: str = "",
        timeout: int = 30,
        max_retries: int = 3
    ):
        super().__init__(
            name="custom_erp_connector",
            version="1.0.0",
            description="Push approved invoices to company ERP system",
            dependencies=[]  # Can depend on other agents if needed
        )
        
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method - push invoice to ERP.
        """
        start_time = time.time()
        
        try:
            # Validate we have invoice data
            if not context.extracted_data:
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    data={},
                    confidence=0.0,
                    errors=["No invoice data available to push to ERP"]
                )
            
            # Transform invoice data to ERP format
            erp_payload = self._transform_to_erp_format(context.extracted_data)
            
            # Push to ERP with retries
            erp_response = await self._push_to_erp(erp_payload)
            
            result = AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data={
                    "erp_invoice_id": erp_response.get("id"),
                    "erp_status": erp_response.get("status"),
                    "erp_url": erp_response.get("url"),
                    "sync_timestamp": time.time()
                },
                confidence=1.0,  # API call either succeeds or fails
                execution_time_ms=(time.time() - start_time) * 1000,
                agent_version=self.version
            )
            
            return result
        
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[f"ERP sync failed: {str(e)}"],
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _transform_to_erp_format(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SmartAP invoice format to ERP-specific format.
        
        Different ERPs have different data models. This method maps
        SmartAP's standardized format to your ERP's expected structure.
        """
        # Example transformation (customize for your ERP)
        erp_invoice = {
            "invoice_number": invoice_data.get("invoice_number"),
            "vendor_id": invoice_data.get("vendor", {}).get("id"),
            "vendor_name": invoice_data.get("vendor", {}).get("name"),
            "invoice_date": invoice_data.get("invoice_date"),
            "due_date": invoice_data.get("due_date"),
            "currency_code": invoice_data.get("currency", "USD"),
            "total_amount": invoice_data.get("total_amount"),
            "tax_amount": invoice_data.get("tax_amount"),
            "subtotal": invoice_data.get("subtotal"),
            "payment_terms": invoice_data.get("payment_terms"),
            "purchase_order_number": invoice_data.get("po_number"),
            "line_items": self._transform_line_items(
                invoice_data.get("line_items", [])
            ),
            "notes": invoice_data.get("notes", ""),
            "status": "PENDING_APPROVAL"
        }
        
        return erp_invoice
    
    def _transform_line_items(self, line_items: list) -> list:
        """Transform line items to ERP format"""
        erp_items = []
        for item in line_items:
            erp_items.append({
                "description": item.get("description"),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0.0),
                "line_total": item.get("total", 0.0),
                "sku": item.get("sku"),
                "account_code": item.get("account_code", "5000"),  # Default GL code
            })
        return erp_items
    
    async def _push_to_erp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push invoice to ERP with retry logic.
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_url}/invoices",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    # Server error, retry
                    await self._wait_before_retry(attempt)
                    continue
                else:
                    # Client error, don't retry
                    raise
            
            except httpx.RequestError as e:
                last_error = e
                # Network error, retry
                await self._wait_before_retry(attempt)
                continue
        
        # All retries exhausted
        raise Exception(f"Failed to push to ERP after {self.max_retries} attempts: {last_error}")
    
    async def _wait_before_retry(self, attempt: int):
        """Exponential backoff before retry"""
        import asyncio
        wait_time = 2 ** attempt  # 1s, 2s, 4s, etc.
        await asyncio.sleep(wait_time)


class QuickBooksConnector(BaseAgent):
    """
    QuickBooks Online integration connector.
    
    Example of a real-world ERP connector using OAuth2.
    """
    
    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        realm_id: str = "",
        access_token: str = "",
        refresh_token: str = ""
    ):
        super().__init__(
            name="quickbooks_connector",
            version="1.0.0",
            description="Sync invoices to QuickBooks Online"
        )
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.realm_id = realm_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.base_url = "https://quickbooks.api.intuit.com/v3"
    
    async def process(self, context: AgentContext) -> AgentResult:
        """Push invoice to QuickBooks"""
        try:
            # Transform to QuickBooks format
            qb_invoice = self._to_quickbooks_format(context.extracted_data)
            
            # Create invoice in QuickBooks
            qb_response = await self._create_invoice(qb_invoice)
            
            return AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data={
                    "quickbooks_invoice_id": qb_response.get("Invoice", {}).get("Id"),
                    "doc_number": qb_response.get("Invoice", {}).get("DocNumber"),
                    "sync_time": qb_response.get("time")
                },
                confidence=1.0
            )
        
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
    
    def _to_quickbooks_format(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform to QuickBooks API format"""
        # QuickBooks Invoice object structure
        # See: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/invoice
        
        line_items = []
        for item in invoice_data.get("line_items", []):
            line_items.append({
                "Amount": item.get("total"),
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "Qty": item.get("quantity", 1),
                    "UnitPrice": item.get("unit_price"),
                },
                "Description": item.get("description")
            })
        
        qb_invoice = {
            "Line": line_items,
            "CustomerRef": {
                "value": "1"  # Would look up customer ID
            },
            "DueDate": invoice_data.get("due_date"),
            "TxnDate": invoice_data.get("invoice_date"),
            "DocNumber": invoice_data.get("invoice_number"),
            "PrivateNote": f"Imported from SmartAP - PO: {invoice_data.get('po_number', 'N/A')}"
        }
        
        return qb_invoice
    
    async def _create_invoice(self, qb_invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice in QuickBooks via API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/company/{self.realm_id}/invoice",
                json=qb_invoice,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def _refresh_access_token(self):
        """Refresh OAuth2 access token"""
        # Implementation of token refresh
        # See QuickBooks OAuth2 documentation
        pass
