"""
SmartAP Invoice Extraction Agent

AI-powered invoice data extraction using Microsoft Agent Framework.
"""

import json
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pathlib import Path

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI

from ..config import Settings
from ..models import (
    Invoice,
    InvoiceLineItem,
    InvoiceExtractionResult,
    ExtractionConfidence,
    InvoiceStatus,
)
from .ocr_service import OCRService, OCRResult


# System prompt for invoice extraction
EXTRACTION_SYSTEM_PROMPT = """You are an expert invoice data extraction agent. Your task is to extract structured data from invoice text.

IMPORTANT RULES:
1. Extract ONLY information that is explicitly present in the text
2. Use null for any field that is not clearly present
3. For amounts, extract the exact numbers without currency symbols
4. For dates, use ISO format (YYYY-MM-DD)
5. Be conservative - if unsure, mark confidence as low

OUTPUT FORMAT:
You must respond with valid JSON only, no additional text. Use this exact schema:
{
  "invoice_number": "string",
  "vendor_name": "string",
  "vendor_address": "string or null",
  "vendor_tax_id": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "currency": "USD/EUR/GBP/etc",
  "subtotal": number or null,
  "tax": number or null,
  "total": number,
  "line_items": [
    {
      "description": "string",
      "quantity": number or null,
      "unit_price": number or null,
      "amount": number or null,
      "sku": "string or null"
    }
  ],
  "po_number": "string or null",
  "payment_terms": "string or null",
  "confidence": {
    "invoice_number": 0.0-1.0,
    "vendor_name": 0.0-1.0,
    "invoice_date": 0.0-1.0,
    "total": 0.0-1.0,
    "line_items": 0.0-1.0
  }
}

CONFIDENCE SCORING:
- 1.0: Field is clearly visible and unambiguous
- 0.8-0.9: Field is present but has minor ambiguity
- 0.5-0.7: Field is partially visible or inferred
- 0.0-0.4: Field is guessed or very uncertain
"""


class InvoiceExtractionAgent:
    """
    AI Agent for extracting structured data from invoice PDFs.
    
    Uses Microsoft Agent Framework with zero-shot extraction.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the extraction agent.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.ocr_service = OCRService(
            foxit_api_key=settings.foxit_api_key,
            foxit_endpoint=settings.foxit_api_endpoint,
        )
        self._agent: Optional[ChatAgent] = None
    
    async def _get_agent(self) -> ChatAgent:
        """Get or create the ChatAgent instance."""
        if self._agent is None:
            # Configure OpenAI client based on provider
            if self.settings.ai_provider == "github":
                client = AsyncOpenAI(
                    base_url=self.settings.model_base_url,
                    api_key=self.settings.github_token,
                )
            else:
                client = AsyncOpenAI(
                    api_key=self.settings.openai_api_key,
                )
            
            chat_client = OpenAIChatClient(
                async_client=client,
                model_id=self.settings.model_id,
            )
            
            self._agent = ChatAgent(
                chat_client=chat_client,
                name="InvoiceExtractor",
                instructions=EXTRACTION_SYSTEM_PROMPT,
            )
        
        return self._agent
    
    async def extract(self, file_path: Path, file_name: str) -> InvoiceExtractionResult:
        """
        Extract invoice data from a PDF file.
        
        Args:
            file_path: Path to the uploaded PDF file
            file_name: Original filename
            
        Returns:
            InvoiceExtractionResult with extracted data and confidence scores
        """
        start_time = time.time()
        document_id = str(uuid.uuid4())
        errors: list[str] = []
        warnings: list[str] = []
        
        try:
            # Step 1: OCR / Text extraction
            ocr_result = await self.ocr_service.process_pdf(file_path)
            
            if ocr_result.is_scanned and not ocr_result.ocr_applied:
                warnings.append(
                    "Document appears to be scanned but OCR was not applied. "
                    "Configure Foxit OCR for better results."
                )
            
            if not ocr_result.text.strip():
                return InvoiceExtractionResult(
                    document_id=document_id,
                    file_name=file_name,
                    file_hash=ocr_result.file_hash,
                    status=InvoiceStatus.FAILED,
                    ocr_applied=ocr_result.ocr_applied,
                    page_count=ocr_result.page_count,
                    extraction_time_ms=int((time.time() - start_time) * 1000),
                    errors=["No text could be extracted from the document."],
                )
            
            # Step 2: AI extraction
            agent = await self._get_agent()
            extraction_prompt = f"Extract invoice data from the following text:\n\n{ocr_result.text}"
            
            response_text = ""
            async for chunk in agent.run_stream(extraction_prompt):
                if chunk.text:
                    response_text += chunk.text
            
            # Step 3: Parse AI response
            invoice, confidence = self._parse_extraction_response(response_text, errors, warnings)
            
            # Step 4: Validate extraction
            if invoice:
                self._validate_extraction(invoice, confidence, warnings)
            
            # Determine if manual review is needed
            requires_review = (
                confidence.overall < self.settings.extraction_confidence_threshold
                or len(errors) > 0
            )
            
            extraction_time = int((time.time() - start_time) * 1000)
            
            return InvoiceExtractionResult(
                document_id=document_id,
                file_name=file_name,
                file_hash=ocr_result.file_hash,
                status=InvoiceStatus.EXTRACTED if invoice else InvoiceStatus.FAILED,
                invoice=invoice,
                confidence=confidence,
                requires_review=requires_review,
                ocr_applied=ocr_result.ocr_applied,
                page_count=ocr_result.page_count,
                extraction_time_ms=extraction_time,
                errors=errors,
                warnings=warnings,
            )
            
        except Exception as e:
            extraction_time = int((time.time() - start_time) * 1000)
            return InvoiceExtractionResult(
                document_id=document_id,
                file_name=file_name,
                file_hash="",
                status=InvoiceStatus.FAILED,
                extraction_time_ms=extraction_time,
                errors=[f"Extraction failed: {str(e)}"],
            )
    
    def _parse_extraction_response(
        self,
        response_text: str,
        errors: list[str],
        warnings: list[str],
    ) -> tuple[Optional[Invoice], ExtractionConfidence]:
        """Parse the AI extraction response into structured data."""
        confidence = ExtractionConfidence()
        
        try:
            # Clean up response (remove markdown code blocks if present)
            clean_response = response_text.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            
            # Parse confidence scores
            if "confidence" in data:
                conf_data = data["confidence"]
                confidence = ExtractionConfidence(
                    invoice_number=conf_data.get("invoice_number", 0.0),
                    vendor_name=conf_data.get("vendor_name", 0.0),
                    invoice_date=conf_data.get("invoice_date", 0.0),
                    total=conf_data.get("total", 0.0),
                    line_items=conf_data.get("line_items", 0.0),
                )
            
            # Parse line items
            line_items = []
            for item_data in data.get("line_items", []):
                line_items.append(InvoiceLineItem(
                    description=item_data.get("description", ""),
                    quantity=item_data.get("quantity"),
                    unit_price=Decimal(str(item_data["unit_price"])) if item_data.get("unit_price") else None,
                    amount=Decimal(str(item_data["amount"])) if item_data.get("amount") else None,
                    sku=item_data.get("sku"),
                ))
            
            # Parse invoice
            invoice = Invoice(
                invoice_number=data.get("invoice_number", "UNKNOWN"),
                vendor_name=data.get("vendor_name", "UNKNOWN"),
                vendor_address=data.get("vendor_address"),
                vendor_tax_id=data.get("vendor_tax_id"),
                invoice_date=data.get("invoice_date"),
                due_date=data.get("due_date"),
                currency=data.get("currency", "USD"),
                subtotal=Decimal(str(data["subtotal"])) if data.get("subtotal") else None,
                tax=Decimal(str(data["tax"])) if data.get("tax") else None,
                total=Decimal(str(data.get("total", 0))),
                line_items=line_items,
                po_number=data.get("po_number"),
                payment_terms=data.get("payment_terms"),
            )
            
            return invoice, confidence
            
        except json.JSONDecodeError as e:
            errors.append(f"Failed to parse AI response as JSON: {str(e)}")
            return None, confidence
        except Exception as e:
            errors.append(f"Failed to parse extraction result: {str(e)}")
            return None, confidence
    
    def _validate_extraction(
        self,
        invoice: Invoice,
        confidence: ExtractionConfidence,
        warnings: list[str],
    ) -> None:
        """Validate extracted invoice data for consistency."""
        # Check if line items sum matches subtotal
        if invoice.line_items and invoice.subtotal:
            line_items_total = sum(
                item.amount or Decimal(0) for item in invoice.line_items
            )
            if abs(line_items_total - invoice.subtotal) > Decimal("0.01"):
                warnings.append(
                    f"Line items total ({line_items_total}) does not match "
                    f"subtotal ({invoice.subtotal})"
                )
        
        # Check if subtotal + tax = total
        if invoice.subtotal and invoice.tax:
            expected_total = invoice.subtotal + invoice.tax
            if abs(expected_total - invoice.total) > Decimal("0.01"):
                warnings.append(
                    f"Subtotal ({invoice.subtotal}) + Tax ({invoice.tax}) = "
                    f"{expected_total} does not match Total ({invoice.total})"
                )
