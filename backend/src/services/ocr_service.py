"""
SmartAP OCR Service

Handles PDF text extraction and OCR processing.
Supports:
1. Foxit Cloud OCR API (when configured)
2. Pytesseract fallback (for local OCR)
3. pypdf for digital/text-based PDFs
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

import httpx
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class OCRPageResult:
    """Result of OCR for a single page."""
    page_number: int
    text: str
    confidence: float


@dataclass
class OCRResult:
    """Result of OCR processing."""
    text: str
    page_count: int
    is_scanned: bool
    ocr_applied: bool
    confidence: float
    file_hash: str
    pages: List[OCRPageResult] = field(default_factory=list)
    error: Optional[str] = None


class OCRService:
    """
    OCR Service for PDF text extraction.
    
    Hierarchy of processing:
    1. Try pypdf for digital PDFs (fast, no external dependencies)
    2. If no text found (scanned PDF), try Foxit Cloud OCR API
    3. Fallback to pytesseract for local OCR (if available)
    """
    
    def __init__(
        self,
        foxit_api_key: Optional[str] = None,
        foxit_endpoint: Optional[str] = None,
        use_local_ocr: bool = True
    ):
        """
        Initialize OCR service.
        
        Args:
            foxit_api_key: Foxit Cloud API key for OCR services
            foxit_endpoint: Foxit Cloud API endpoint
            use_local_ocr: Whether to use local OCR (pytesseract) as fallback
        """
        self.foxit_api_key = foxit_api_key
        self.foxit_endpoint = foxit_endpoint or "https://api.foxit.com/v1"
        self._use_foxit = bool(foxit_api_key)
        self._use_local_ocr = use_local_ocr
        
        # Check for local OCR availability
        self._pytesseract_available = False
        self._pdf2image_available = False
        
        if use_local_ocr:
            try:
                import pytesseract
                self._pytesseract_available = True
                logger.info("Pytesseract OCR is available")
            except ImportError:
                logger.debug("Pytesseract not available - install with: pip install pytesseract")
            
            try:
                import pdf2image
                self._pdf2image_available = True
                logger.info("pdf2image is available for PDF conversion")
            except ImportError:
                logger.debug("pdf2image not available - install with: pip install pdf2image")
    
    async def process_pdf(self, file_path: Path) -> OCRResult:
        """
        Process a PDF file and extract text.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            OCRResult with extracted text and metadata
        """
        file_hash = self._calculate_hash(file_path)
        
        # First, try pypdf for digital PDFs (fast)
        pypdf_result = await self._process_with_pypdf(file_path, file_hash)
        
        # If we got text, return it (digital PDF)
        if pypdf_result.text.strip() and pypdf_result.confidence > 0.5:
            logger.info(f"Extracted text from digital PDF: {file_path.name}")
            return pypdf_result
        
        # PDF appears to be scanned - needs OCR
        logger.info(f"PDF appears scanned, attempting OCR: {file_path.name}")
        
        # Try Foxit Cloud OCR first (if configured)
        if self._use_foxit:
            try:
                foxit_result = await self._process_with_foxit(file_path, file_hash)
                if foxit_result.text.strip():
                    logger.info(f"OCR completed with Foxit: {file_path.name}")
                    return foxit_result
            except Exception as e:
                logger.warning(f"Foxit OCR failed: {e}, trying fallback")
        
        # Fallback to local OCR (pytesseract)
        if self._use_local_ocr and self._pytesseract_available and self._pdf2image_available:
            try:
                local_result = await self._process_with_pytesseract(file_path, file_hash)
                if local_result.text.strip():
                    logger.info(f"OCR completed with pytesseract: {file_path.name}")
                    return local_result
            except Exception as e:
                logger.warning(f"Pytesseract OCR failed: {e}")
        
        # Return the pypdf result with is_scanned=True and low confidence
        return OCRResult(
            text=pypdf_result.text,
            page_count=pypdf_result.page_count,
            is_scanned=True,
            ocr_applied=False,
            confidence=0.0,
            file_hash=file_hash,
            error="OCR not available - document appears to be scanned but no OCR service configured"
        )
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of the file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def _process_with_foxit(self, file_path: Path, file_hash: str) -> OCRResult:
        """
        Process PDF using Foxit Cloud OCR API.
        
        Uses Foxit's document conversion/OCR API to extract text from scanned documents.
        """
        if not self.foxit_api_key:
            raise ValueError("Foxit API key not configured")
        
        # Read PDF file
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Get page count
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
        
        # Call Foxit OCR API
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {self.foxit_api_key}",
                "Content-Type": "application/octet-stream",
            }
            
            # Foxit Cloud API endpoint for OCR
            ocr_url = f"{self.foxit_endpoint}/ocr/extract"
            
            response = await client.post(
                ocr_url,
                headers=headers,
                content=pdf_bytes,
                params={
                    "outputFormat": "text",
                    "language": "eng",
                }
            )
            
            if response.status_code == 200:
                result_data = response.json()
                
                # Extract text from response
                text = result_data.get("text", "")
                confidence = result_data.get("confidence", 0.85)
                pages = []
                
                # Parse page-level results if available
                for page_data in result_data.get("pages", []):
                    pages.append(OCRPageResult(
                        page_number=page_data.get("pageNumber", 0),
                        text=page_data.get("text", ""),
                        confidence=page_data.get("confidence", confidence)
                    ))
                
                return OCRResult(
                    text=text,
                    page_count=page_count,
                    is_scanned=True,
                    ocr_applied=True,
                    confidence=confidence,
                    file_hash=file_hash,
                    pages=pages,
                )
            
            elif response.status_code == 401:
                raise ValueError("Invalid Foxit API key")
            elif response.status_code == 429:
                raise ValueError("Foxit API rate limit exceeded")
            else:
                raise ValueError(f"Foxit API error: {response.status_code} - {response.text}")
    
    async def _process_with_pytesseract(self, file_path: Path, file_hash: str) -> OCRResult:
        """
        Process PDF using pytesseract (local OCR).
        
        Requires pytesseract and pdf2image packages plus Tesseract installed on system.
        """
        import pytesseract
        from pdf2image import convert_from_path
        
        # Convert PDF to images
        images = convert_from_path(file_path, dpi=300)
        page_count = len(images)
        
        text_parts = []
        pages = []
        total_confidence = 0.0
        
        for i, image in enumerate(images):
            # Run OCR on each page
            page_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate confidence
            page_text_parts = []
            page_confidences = []
            
            for j, word in enumerate(page_data["text"]):
                if word.strip():
                    page_text_parts.append(word)
                    conf = page_data["conf"][j]
                    if conf > 0:  # -1 means no confidence
                        page_confidences.append(conf)
            
            page_text = " ".join(page_text_parts)
            page_confidence = sum(page_confidences) / len(page_confidences) / 100 if page_confidences else 0.0
            
            text_parts.append(page_text)
            pages.append(OCRPageResult(
                page_number=i + 1,
                text=page_text,
                confidence=page_confidence
            ))
            total_confidence += page_confidence
        
        full_text = "\n\n".join(text_parts)
        avg_confidence = total_confidence / page_count if page_count > 0 else 0.0
        
        return OCRResult(
            text=full_text,
            page_count=page_count,
            is_scanned=True,
            ocr_applied=True,
            confidence=avg_confidence,
            file_hash=file_hash,
            pages=pages,
        )
    
    async def _process_with_pypdf(self, file_path: Path, file_hash: str) -> OCRResult:
        """
        Process PDF using pypdf (for digital/text-based PDFs).
        
        Note: This does NOT perform OCR on scanned documents.
        """
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
        
        text_parts = []
        pages = []
        has_text = False
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
                has_text = True
            
            pages.append(OCRPageResult(
                page_number=i + 1,
                text=page_text,
                confidence=0.95 if page_text.strip() else 0.0
            ))
        
        full_text = "\n\n".join(text_parts)
        is_scanned = not has_text
        
        return OCRResult(
            text=full_text,
            page_count=page_count,
            is_scanned=is_scanned,
            ocr_applied=False,
            confidence=0.95 if has_text else 0.0,
            file_hash=file_hash,
            pages=pages,
        )
    
    async def check_duplicate(self, file_hash: str, session=None) -> Optional[str]:
        """
        Check if a document with this hash has already been processed.
        
        Args:
            file_hash: SHA-256 hash of the document
            session: Database session (optional)
            
        Returns:
            Document ID if duplicate found, None otherwise
        """
        if session is None:
            return None
        
        # Import here to avoid circular imports
        from sqlalchemy import select
        from ..db.models import InvoiceDB
        
        result = await session.execute(
            select(InvoiceDB.document_id).where(InvoiceDB.file_hash == file_hash)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Duplicate document detected: {existing}")
            return existing
        
        return None
    
    @property
    def ocr_available(self) -> bool:
        """Check if any OCR capability is available."""
        return self._use_foxit or (self._pytesseract_available and self._pdf2image_available)
    
    @property
    def ocr_provider(self) -> str:
        """Get the name of the active OCR provider."""
        if self._use_foxit:
            return "Foxit Cloud OCR"
        elif self._pytesseract_available and self._pdf2image_available:
            return "Pytesseract (local)"
        else:
            return "None (digital PDFs only)"


# Factory function for creating OCR service with settings
def get_ocr_service() -> OCRService:
    """Create OCR service instance from settings."""
    from ..config import get_settings
    settings = get_settings()
    
    return OCRService(
        foxit_api_key=settings.foxit_api_key,
        foxit_endpoint=settings.foxit_api_endpoint,
        use_local_ocr=True,
    )
