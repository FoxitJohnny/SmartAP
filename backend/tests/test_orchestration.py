"""
Tests for invoice processing orchestration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.orchestration import InvoiceProcessingOrchestrator, WorkflowState, ProcessingDecision, WorkflowStatus
from src.db.models import InvoiceDB, PurchaseOrderDB, VendorDB, POLineItemDB
from src.models import MatchingResult, RiskAssessment, RiskLevel, RiskFlag, DuplicateInfo
from src.models.matching import MatchType, DiscrepancyType, DiscrepancySeverity, Discrepancy
from src.models.risk import RecommendedAction, RiskFlagType


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_invoice():
    """Create mock invoice."""
    from src.models.invoice import InvoiceStatus
    return InvoiceDB(
        id=1,
        document_id="DOC-001",
        invoice_number="INV-12345",
        file_name="invoice.pdf",
        file_hash="abc123",
        status=InvoiceStatus.EXTRACTED,
        extraction_confidence=0.95,
        requires_review=False,
        ocr_applied=False,
        page_count=1,
        invoice_data={
            "invoice_number": "INV-12345",
            "invoice_date": "2026-01-05",
            "due_date": "2026-02-05",
            "total": 1000.00,
            "currency": "USD",
            "vendor_name": "Tech Supplies Inc",
            "po_number": "PO-001",
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_po():
    """Create mock purchase order."""
    from src.models.purchase_order import POStatus
    from datetime import date
    return PurchaseOrderDB(
        id=1,
        po_number="PO-001",
        vendor_id="V001",
        created_date=date(2026, 1, 1),
        expected_delivery=date(2026, 2, 1),
        subtotal=Decimal("900.00"),
        tax=Decimal("100.00"),
        total_amount=Decimal("1000.00"),
        currency="USD",
        status=POStatus.OPEN,
        payment_terms="Net 30",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_vendor():
    """Create mock vendor."""
    from src.models.vendor import VendorStatus
    from datetime import date
    return VendorDB(
        id=1,
        vendor_id="V001",
        vendor_name="Tech Supplies Inc",
        status=VendorStatus.ACTIVE,
        onboarded_date=date(2025, 1, 1),
        payment_terms="Net 30",
        currency="USD",
        risk_profile={
            "risk_score": 0.1,
            "on_time_payment_rate": 0.95,
            "total_invoices_processed": 50,
        },
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
class TestInvoiceProcessingOrchestrator:
    """Test invoice processing orchestration."""
    
    async def test_successful_processing_auto_approved(
        self,
        mock_db_session,
        mock_invoice,
        mock_po,
        mock_vendor,
    ):
        """Test successful processing with auto-approval."""
        # Setup mocks - patch at orchestrator.py where repositories are instantiated
        with patch("src.orchestration.orchestrator.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.orchestrator.PurchaseOrderRepository") as mock_po_repo_cls, \
             patch("src.orchestration.orchestrator.VendorRepository") as mock_vendor_repo_cls, \
             patch("src.orchestration.orchestrator.MatchingRepository") as mock_matching_repo_cls, \
             patch("src.orchestration.orchestrator.RiskRepository") as mock_risk_repo_cls, \
             patch("src.orchestration.workflow_nodes.POMatchingAgent") as mock_matching_agent_cls, \
             patch("src.orchestration.workflow_nodes.RiskDetectionAgent") as mock_risk_agent_cls:
            
            # Configure invoice repository
            mock_invoice_repo = AsyncMock()
            mock_invoice_repo.get_by_document_id = AsyncMock(return_value=mock_invoice)
            mock_invoice_repo_cls.return_value = mock_invoice_repo
            
            # Configure vendor repository
            mock_vendor_repo = AsyncMock()
            mock_vendor_repo.get_by_name = AsyncMock(return_value=mock_vendor)
            mock_vendor_repo_cls.return_value = mock_vendor_repo
            
            # Configure matching agent
            mock_matching_agent = AsyncMock()
            mock_matching_result = MatchingResult(
                matching_id="MATCH-001",
                invoice_id="DOC-001",
                po_id="PO-001",
                po_number="PO-001",
                match_type=MatchType.EXACT,
                match_score=0.96,
                matched=True,
                discrepancies=[],
                requires_approval=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # Configure risk agent
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                assessment_id="RISK-001",
                invoice_id="DOC-001",
                risk_level=RiskLevel.LOW,
                risk_score=0.15,
                risk_flags=[],
                duplicate_info=None,
                vendor_risk_info=None,
                price_anomalies=[],
                recommended_action=RecommendedAction.AUTO_APPROVE,
                action_reason="Low risk, high match score",
                requires_manual_review=False,
                assessed_at=datetime.utcnow(),
            )
            mock_risk_agent.assess_risk = AsyncMock(return_value=mock_risk_result)
            mock_risk_agent_cls.return_value = mock_risk_agent
            
            # Create orchestrator
            orchestrator = InvoiceProcessingOrchestrator(mock_db_session)
            
            # Process invoice
            final_state = await orchestrator.process_invoice("DOC-001", "V001")
            
            # Assertions
            assert final_state["status"] == WorkflowStatus.COMPLETED
            assert final_state["decision"] == ProcessingDecision.AUTO_APPROVED
            assert final_state["extraction_completed"] is True
            assert final_state["matching_completed"] is True
            assert final_state["risk_completed"] is True
            assert final_state["requires_manual_review"] is False
            assert final_state["match_score"] == 0.96
            assert final_state["risk_level"] == RiskLevel.LOW
            assert len(final_state["errors"]) == 0
    
    async def test_processing_with_discrepancies_requires_review(
        self,
        mock_db_session,
        mock_invoice,
        mock_po,
        mock_vendor,
    ):
        """Test processing with discrepancies requiring review."""
        with patch("src.orchestration.orchestrator.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.orchestrator.VendorRepository") as mock_vendor_repo_cls, \
             patch("src.orchestration.orchestrator.PurchaseOrderRepository") as mock_po_repo_cls, \
             patch("src.orchestration.orchestrator.MatchingRepository") as mock_matching_repo_cls, \
             patch("src.orchestration.orchestrator.RiskRepository") as mock_risk_repo_cls, \
             patch("src.orchestration.workflow_nodes.POMatchingAgent") as mock_matching_agent_cls, \
             patch("src.orchestration.workflow_nodes.RiskDetectionAgent") as mock_risk_agent_cls:
            
            # Setup repositories
            mock_invoice_repo = AsyncMock()
            mock_invoice_repo.get_by_document_id = AsyncMock(return_value=mock_invoice)
            mock_invoice_repo_cls.return_value = mock_invoice_repo
            
            mock_vendor_repo = AsyncMock()
            mock_vendor_repo.get_by_name = AsyncMock(return_value=mock_vendor)
            mock_vendor_repo_cls.return_value = mock_vendor_repo
            
            # Matching with critical discrepancy
            mock_matching_agent = AsyncMock()
            mock_matching_result = MatchingResult(
                matching_id="MATCH-001",
                invoice_id="DOC-001",
                po_id="PO-001",
                po_number="PO-001",
                match_type=MatchType.FUZZY,
                match_score=0.88,
                matched=True,
                discrepancies=[
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.AMOUNT_TOLERANCE_EXCEEDED,
                        severity=DiscrepancySeverity.CRITICAL,
                        invoice_value="1200.00",
                        po_value="1000.00",
                        difference="200.00",
                        description="Amount exceeds PO by 20%",
                    )
                ],
                requires_approval=True,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # Low risk assessment
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                assessment_id="RISK-001",
                invoice_id="DOC-001",
                risk_level=RiskLevel.LOW,
                risk_score=0.20,
                risk_flags=[],
                duplicate_info=None,
                vendor_risk_info=None,
                price_anomalies=[],
                recommended_action=RecommendedAction.REVIEW,
                action_reason="Amount discrepancy",
                requires_manual_review=True,
                assessed_at=datetime.utcnow(),
            )
            mock_risk_agent.assess_risk = AsyncMock(return_value=mock_risk_result)
            mock_risk_agent_cls.return_value = mock_risk_agent
            
            # Process
            orchestrator = InvoiceProcessingOrchestrator(mock_db_session)
            final_state = await orchestrator.process_invoice("DOC-001", "V001")
            
            # Assertions
            assert final_state["status"] == WorkflowStatus.COMPLETED
            assert final_state["decision"] == ProcessingDecision.REQUIRES_REVIEW
            assert final_state["requires_manual_review"] is True
            assert len(final_state["discrepancies"]) == 1
            assert "Review discrepancies" in final_state["recommended_actions"]
    
    async def test_processing_with_duplicate_rejected(
        self,
        mock_db_session,
        mock_invoice,
        mock_vendor,
    ):
        """Test processing with duplicate detection resulting in rejection."""
        with patch("src.orchestration.orchestrator.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.orchestrator.VendorRepository") as mock_vendor_repo_cls, \
             patch("src.orchestration.orchestrator.PurchaseOrderRepository") as mock_po_repo_cls, \
             patch("src.orchestration.orchestrator.MatchingRepository") as mock_matching_repo_cls, \
             patch("src.orchestration.orchestrator.RiskRepository") as mock_risk_repo_cls, \
             patch("src.orchestration.workflow_nodes.POMatchingAgent") as mock_matching_agent_cls, \
             patch("src.orchestration.workflow_nodes.RiskDetectionAgent") as mock_risk_agent_cls:
            
            # Setup repositories
            mock_invoice_repo = AsyncMock()
            mock_invoice_repo.get_by_document_id = AsyncMock(return_value=mock_invoice)
            mock_invoice_repo_cls.return_value = mock_invoice_repo
            
            mock_vendor_repo = AsyncMock()
            mock_vendor_repo.get_by_name = AsyncMock(return_value=mock_vendor)
            mock_vendor_repo_cls.return_value = mock_vendor_repo
            
            # Good matching
            mock_matching_agent = AsyncMock()
            mock_matching_result = MatchingResult(
                matching_id="MATCH-001",
                invoice_id="DOC-001",
                po_id="PO-001",
                po_number="PO-001",
                match_type=MatchType.EXACT,
                match_score=0.95,
                matched=True,
                discrepancies=[],
                requires_approval=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # Duplicate detected
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                assessment_id="RISK-001",
                invoice_id="DOC-001",
                risk_level=RiskLevel.CRITICAL,
                risk_score=0.90,
                risk_flags=[
                    RiskFlag(
                        flag_type=RiskFlagType.DUPLICATE_NEAR,
                        severity="critical",
                        description="Exact duplicate found (invoice number match)",
                        confidence=1.0,
                    )
                ],
                duplicate_info=DuplicateInfo(
                    is_duplicate=True,
                    duplicate_type=RiskFlagType.DUPLICATE_NEAR,
                    similarity_score=1.0,
                    duplicate_invoice_id="DOC-000",
                ),
                vendor_risk_info=None,
                price_anomalies=[],
                recommended_action=RecommendedAction.REJECT,
                action_reason="Duplicate invoice",
                requires_manual_review=True,
                assessed_at=datetime.utcnow(),
            )
            mock_risk_agent.assess_risk = AsyncMock(return_value=mock_risk_result)
            mock_risk_agent_cls.return_value = mock_risk_agent
            
            # Process
            orchestrator = InvoiceProcessingOrchestrator(mock_db_session)
            final_state = await orchestrator.process_invoice("DOC-001", "V001")
            
            # Assertions
            assert final_state["status"] == WorkflowStatus.COMPLETED
            assert final_state["decision"] == ProcessingDecision.REJECTED
            assert final_state["is_duplicate"] is True
            assert "Duplicate invoice detected" in final_state["decision_reason"]
            assert final_state["requires_manual_review"] is True
    
    async def test_processing_with_high_risk_requires_investigation(
        self,
        mock_db_session,
        mock_invoice,
        mock_vendor,
    ):
        """Test processing with high risk requiring investigation."""
        with patch("src.orchestration.orchestrator.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.orchestrator.VendorRepository") as mock_vendor_repo_cls, \
             patch("src.orchestration.orchestrator.PurchaseOrderRepository") as mock_po_repo_cls, \
             patch("src.orchestration.orchestrator.MatchingRepository") as mock_matching_repo_cls, \
             patch("src.orchestration.orchestrator.RiskRepository") as mock_risk_repo_cls, \
             patch("src.orchestration.workflow_nodes.POMatchingAgent") as mock_matching_agent_cls, \
             patch("src.orchestration.workflow_nodes.RiskDetectionAgent") as mock_risk_agent_cls:
            
            # Setup repositories
            mock_invoice_repo = AsyncMock()
            mock_invoice_repo.get_by_document_id = AsyncMock(return_value=mock_invoice)
            mock_invoice_repo_cls.return_value = mock_invoice_repo
            
            mock_vendor_repo = AsyncMock()
            mock_vendor_repo.get_by_name = AsyncMock(return_value=mock_vendor)
            mock_vendor_repo_cls.return_value = mock_vendor_repo
            
            # Good matching
            mock_matching_agent = AsyncMock()
            mock_matching_result = MatchingResult(
                matching_id="MATCH-001",
                invoice_id="DOC-001",
                po_id="PO-001",
                po_number="PO-001",
                match_type=MatchType.EXACT,
                match_score=0.92,
                matched=True,
                discrepancies=[],
                requires_approval=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # High risk with multiple flags
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                assessment_id="RISK-001",
                invoice_id="DOC-001",
                risk_level=RiskLevel.HIGH,
                risk_score=0.65,
                risk_flags=[
                    RiskFlag(
                        flag_type=RiskFlagType.VENDOR_NEW,
                        severity="high",
                        description="Vendor has poor payment history",
                        confidence=0.80,
                    ),
                    RiskFlag(
                        flag_type=RiskFlagType.PRICE_ANOMALY,
                        severity="high",
                        description="Price 35% above historical average",
                        confidence=0.85,
                    ),
                ],
                duplicate_info=None,
                vendor_risk_info=None,
                price_anomalies=[],
                recommended_action=RecommendedAction.INVESTIGATE,
                action_reason="Multiple high risk factors",
                requires_manual_review=True,
                assessed_at=datetime.utcnow(),
            )
            mock_risk_agent.assess_risk = AsyncMock(return_value=mock_risk_result)
            mock_risk_agent_cls.return_value = mock_risk_agent
            
            # Process
            orchestrator = InvoiceProcessingOrchestrator(mock_db_session)
            final_state = await orchestrator.process_invoice("DOC-001", "V001")
            
            # Assertions
            assert final_state["status"] == WorkflowStatus.COMPLETED
            assert final_state["decision"] == ProcessingDecision.REQUIRES_INVESTIGATION
            assert final_state["risk_level"] == RiskLevel.HIGH
            assert len(final_state["risk_flags"]) == 2
            assert "Investigate risk factors" in final_state["recommended_actions"]
    
    async def test_processing_extraction_not_completed(
        self,
        mock_db_session,
    ):
        """Test processing when extraction is not completed."""
        with patch("src.orchestration.orchestrator.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.orchestrator.VendorRepository") as mock_vendor_repo_cls, \
             patch("src.orchestration.orchestrator.PurchaseOrderRepository") as mock_po_repo_cls, \
             patch("src.orchestration.orchestrator.MatchingRepository") as mock_matching_repo_cls, \
             patch("src.orchestration.orchestrator.RiskRepository") as mock_risk_repo_cls:
            from src.models.invoice import InvoiceStatus
            
            # Invoice with incomplete extraction
            incomplete_invoice = InvoiceDB(
                id=1,
                document_id="DOC-002",
                invoice_number="INV-PENDING",
                file_name="invoice.pdf",
                file_hash="xyz789",
                status=InvoiceStatus.INGESTED,
                extraction_confidence=0.0,
                requires_review=False,
                ocr_applied=False,
                page_count=1,
                created_at=datetime.utcnow(),
            )
            
            mock_invoice_repo = AsyncMock()
            mock_invoice_repo.get_by_document_id = AsyncMock(return_value=incomplete_invoice)
            mock_invoice_repo_cls.return_value = mock_invoice_repo
            
            # Process
            orchestrator = InvoiceProcessingOrchestrator(mock_db_session)
            final_state = await orchestrator.process_invoice("DOC-002")
            
            # Assertions
            assert final_state["status"] == WorkflowStatus.FAILED
            assert final_state["extraction_completed"] is False
            assert "extraction not completed" in final_state["extraction_error"].lower()
            assert len(final_state["errors"]) > 0
