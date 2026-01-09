"""
Extraction Agent Wrapper

This module provides backward compatibility for the orchestration layer
by re-exporting the InvoiceExtractionAgent from services.

The actual implementation is in services/extraction_agent.py.
This wrapper ensures the orchestration layer can import correctly.
"""

from ..services.extraction_agent import InvoiceExtractionAgent


class ExtractionAgent(InvoiceExtractionAgent):
    """
    Wrapper class for orchestration workflow compatibility.
    
    Inherits all functionality from InvoiceExtractionAgent.
    This alias allows the orchestration layer to import using
    the expected module path: `from ..agents.extraction_agent import ExtractionAgent`
    """
    pass


__all__ = ["ExtractionAgent", "InvoiceExtractionAgent"]
