# SmartAP Services
from .ocr_service import OCRService

# Optional: InvoiceExtractionAgent requires agent_framework
try:
    from .extraction_agent import InvoiceExtractionAgent
    HAS_EXTRACTION_AGENT = True
except ImportError:
    InvoiceExtractionAgent = None
    HAS_EXTRACTION_AGENT = False

__all__ = [
    "OCRService",
    "InvoiceExtractionAgent",
    "HAS_EXTRACTION_AGENT",
]
