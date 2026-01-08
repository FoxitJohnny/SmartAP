"""
Example Plugin: Custom Extraction Agent

This agent demonstrates how to create a custom extraction agent
that uses a different AI model or extraction strategy.
"""

import time
from typing import Dict, Any
import httpx

from src.plugins import BaseExtractorAgent, AgentContext, AgentResult, AgentStatus


class CustomExtractionAgent(BaseExtractorAgent):
    """
    Custom extraction agent using a different AI model.
    
    This example shows how to:
    1. Inherit from BaseExtractorAgent
    2. Implement custom extraction logic
    3. Use external APIs (e.g., different AI provider)
    4. Return structured results
    
    Usage:
        >>> from plugins.custom_extractor import CustomExtractionAgent
        >>> from src.plugins import AgentContext, register_agent
        >>> 
        >>> # Register the agent
        >>> agent = CustomExtractionAgent()
        >>> register_agent(agent)
        >>> 
        >>> # Use in pipeline
        >>> context = AgentContext(invoice_id="123", pdf_bytes=pdf_data)
        >>> result = await agent.process(context)
    """
    
    def __init__(self):
        super().__init__(
            name="custom_extractor",
            version="1.0.0",
            description="Custom extraction agent using alternative AI model",
            supported_formats=["pdf", "png", "jpg"]
        )
        
        # Configuration (loaded from environment variables)
        self.api_url = "https://api.example.com/extract"  # Your custom API
        self.api_key = "your_api_key"  # Load from env var
        self.model = "custom-model-v1"
        self.timeout = 30
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method - extracts invoice data using custom model.
        """
        start_time = time.time()
        
        try:
            # Validate context
            if not await self.validate_context(context):
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    data={},
                    confidence=0.0,
                    errors=["Invalid context: missing required fields"]
                )
            
            # Pre-process hook
            await self.pre_process(context)
            
            # Extract invoice data
            extracted_data = await self.extract_invoice_data(context.pdf_bytes)
            
            # Calculate confidence
            confidence = self._calculate_confidence(extracted_data)
            
            # Build result
            result = AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data=extracted_data,
                confidence=confidence,
                execution_time_ms=(time.time() - start_time) * 1000,
                agent_version=self.version
            )
            
            # Post-process hook
            return await self.post_process(result)
        
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)],
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def extract_invoice_data(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract structured data from invoice PDF using custom API.
        """
        # Call your custom extraction API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                files={"file": pdf_bytes},
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"model": self.model},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse response
            api_result = response.json()
        
        # Transform API response to SmartAP format
        invoice_data = {
            "invoice_number": api_result.get("invoice_id"),
            "vendor": {
                "name": api_result.get("vendor_name"),
                "address": api_result.get("vendor_address"),
                "tax_id": api_result.get("vendor_tax_id")
            },
            "customer": {
                "name": api_result.get("customer_name"),
                "address": api_result.get("customer_address")
            },
            "invoice_date": api_result.get("invoice_date"),
            "due_date": api_result.get("due_date"),
            "po_number": api_result.get("po_number"),
            "currency": api_result.get("currency", "USD"),
            "line_items": self._parse_line_items(api_result.get("line_items", [])),
            "subtotal": api_result.get("subtotal"),
            "tax_amount": api_result.get("tax"),
            "total_amount": api_result.get("total"),
            "payment_terms": api_result.get("payment_terms"),
        }
        
        return invoice_data
    
    def _parse_line_items(self, raw_items: list) -> list:
        """Parse line items from API response"""
        line_items = []
        for item in raw_items:
            line_items.append({
                "description": item.get("description"),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0.0),
                "total": item.get("total", 0.0),
                "sku": item.get("sku"),
            })
        return line_items
    
    def _calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on data completeness.
        
        Checks for presence of critical fields and returns a confidence score.
        """
        critical_fields = [
            "invoice_number",
            "vendor.name",
            "total_amount",
            "invoice_date"
        ]
        
        present = 0
        for field in critical_fields:
            if "." in field:
                # Nested field (e.g., "vendor.name")
                parts = field.split(".")
                value = extracted_data
                for part in parts:
                    value = value.get(part) if isinstance(value, dict) else None
                    if value is None:
                        break
                if value:
                    present += 1
            else:
                if extracted_data.get(field):
                    present += 1
        
        return present / len(critical_fields)
    
    async def validate_context(self, context: AgentContext) -> bool:
        """Validate that PDF bytes are available"""
        if not context.pdf_bytes:
            return False
        if len(context.pdf_bytes) == 0:
            return False
        return True


# Example 2: Simple extraction agent using local processing
class SimpleTextExtractor(BaseExtractorAgent):
    """
    Simple extraction agent that uses regex patterns for extraction.
    
    Good for standardized invoice formats where patterns are predictable.
    """
    
    def __init__(self):
        super().__init__(
            name="simple_text_extractor",
            version="1.0.0",
            description="Simple regex-based extraction for standardized formats"
        )
    
    async def process(self, context: AgentContext) -> AgentResult:
        """Extract data using regex patterns"""
        try:
            extracted_data = await self.extract_invoice_data(context.pdf_bytes)
            
            return AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data=extracted_data,
                confidence=0.85
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
    
    async def extract_invoice_data(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract data using regex patterns.
        
        In a real implementation, you would:
        1. Convert PDF to text (using PyPDF2, pdfplumber, etc.)
        2. Apply regex patterns to extract fields
        3. Validate and structure the data
        """
        import re
        # This is a simplified example
        # In production, you'd use proper PDF parsing libraries
        
        # Example patterns
        patterns = {
            "invoice_number": r"Invoice #?:\s*([A-Z0-9-]+)",
            "total_amount": r"Total:?\s*\$?([0-9,]+\.\d{2})",
            "invoice_date": r"Date:?\s*(\d{1,2}/\d{1,2}/\d{4})",
            "vendor_name": r"From:?\s*([^\n]+)",
        }
        
        # Convert PDF to text (placeholder)
        # In real implementation: text = extract_text_from_pdf(pdf_bytes)
        text = "Example invoice text..."
        
        extracted = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                extracted[field] = match.group(1)
        
        return extracted
