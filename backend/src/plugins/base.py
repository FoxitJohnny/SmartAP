"""
Base Agent Interface for SmartAP Plugin System

This module defines the base interface that all custom agents must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class AgentContext:
    """
    Context passed to agents during execution.
    
    Contains all necessary information about the invoice being processed,
    database session, and any intermediate results from previous agents.
    """
    # Invoice identification
    invoice_id: str
    
    # Raw invoice data
    pdf_bytes: bytes
    pdf_path: Optional[str] = None
    
    # Extracted invoice data (from previous agents)
    extracted_data: Optional[Dict[str, Any]] = None
    
    # Vendor information
    vendor_id: Optional[str] = None
    vendor_data: Optional[Dict[str, Any]] = None
    
    # PO information (if available)
    po_number: Optional[str] = None
    po_data: Optional[Dict[str, Any]] = None
    
    # Previous agent results
    previous_results: Dict[str, Any] = None
    
    # Metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.previous_results is None:
            self.previous_results = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentResult:
    """
    Result returned by agent execution.
    
    Contains the processed data, confidence score, any errors,
    and metadata about the execution.
    """
    # Execution status
    success: bool
    status: AgentStatus
    
    # Processed data
    data: Dict[str, Any]
    
    # Confidence in the result (0.0 to 1.0)
    confidence: float
    
    # Any errors or warnings
    errors: List[str] = None
    warnings: List[str] = None
    
    # Execution metadata
    execution_time_ms: Optional[float] = None
    agent_version: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def has_errors(self) -> bool:
        """Check if result has any errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if result has any warnings"""
        return len(self.warnings) > 0


class BaseAgent(ABC):
    """
    Abstract base class for all SmartAP agents.
    
    Custom agents must inherit from this class and implement the `process` method.
    
    Example:
        >>> class MyCustomAgent(BaseAgent):
        ...     def __init__(self):
        ...         super().__init__(
        ...             name="my_custom_agent",
        ...             version="1.0.0",
        ...             description="My custom agent description"
        ...         )
        ...     
        ...     async def process(self, context: AgentContext) -> AgentResult:
        ...         # Your custom logic here
        ...         return AgentResult(
        ...             success=True,
        ...             status=AgentStatus.SUCCESS,
        ...             data={"key": "value"},
        ...             confidence=0.95
        ...         )
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        dependencies: Optional[List[str]] = None
    ):
        """
        Initialize base agent.
        
        Args:
            name: Unique identifier for this agent
            version: Semantic version (e.g., "1.0.0")
            description: Human-readable description
            dependencies: List of agent names this agent depends on
        """
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies or []
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Process the invoice and return results.
        
        This is the main method that must be implemented by all custom agents.
        
        Args:
            context: AgentContext containing invoice data and metadata
        
        Returns:
            AgentResult with processed data and execution metadata
        
        Raises:
            Exception: Any errors during processing should be caught and
                      returned in AgentResult.errors
        """
        pass
    
    async def validate_context(self, context: AgentContext) -> bool:
        """
        Validate that the context has all required data.
        
        Override this method to add custom validation logic.
        
        Args:
            context: AgentContext to validate
        
        Returns:
            True if context is valid, False otherwise
        """
        # Basic validation
        if not context.invoice_id:
            return False
        if not context.pdf_bytes and not context.pdf_path:
            return False
        return True
    
    async def pre_process(self, context: AgentContext) -> None:
        """
        Hook called before process() execution.
        
        Override this method to add setup logic (e.g., load models, connect to APIs).
        
        Args:
            context: AgentContext for the current execution
        """
        pass
    
    async def post_process(self, result: AgentResult) -> AgentResult:
        """
        Hook called after process() execution.
        
        Override this method to add cleanup or post-processing logic.
        
        Args:
            result: AgentResult from process() execution
        
        Returns:
            Modified or original AgentResult
        """
        return result
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' version='{self.version}'>"


class BaseExtractorAgent(BaseAgent):
    """
    Base class for extraction agents that extract data from invoices.
    
    Extraction agents are responsible for reading PDF content and extracting
    structured data (invoice number, vendor, amounts, line items, etc.).
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        supported_formats: Optional[List[str]] = None
    ):
        super().__init__(name, version, description)
        self.supported_formats = supported_formats or ["pdf"]
    
    @abstractmethod
    async def extract_invoice_data(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract structured data from invoice PDF.
        
        Args:
            pdf_bytes: Raw PDF file content
        
        Returns:
            Dictionary with extracted invoice data
        """
        pass


class BaseValidatorAgent(BaseAgent):
    """
    Base class for validation agents that check invoice data for correctness.
    
    Validator agents check extracted data for:
    - Data completeness
    - Format validation
    - Business rule compliance
    - Cross-field consistency
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        validation_rules: Optional[List[str]] = None
    ):
        super().__init__(name, version, description)
        self.validation_rules = validation_rules or []
    
    @abstractmethod
    async def validate_data(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate invoice data.
        
        Args:
            invoice_data: Extracted invoice data to validate
        
        Returns:
            Dictionary with validation results and any errors
        """
        pass


class BaseRiskAgent(BaseAgent):
    """
    Base class for risk assessment agents.
    
    Risk agents analyze invoices for:
    - Fraud patterns
    - Duplicate detection
    - Vendor risk
    - Price anomalies
    - Compliance violations
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        risk_threshold: float = 0.5
    ):
        super().__init__(name, version, description)
        self.risk_threshold = risk_threshold
    
    @abstractmethod
    async def assess_risk(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk for the invoice.
        
        Args:
            invoice_data: Invoice data to assess
        
        Returns:
            Dictionary with risk assessment results
        """
        pass
