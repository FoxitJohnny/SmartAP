"""
Tests for invoice processing orchestration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.orchestration import InvoiceProcessingOrchestrator, WorkflowState, ProcessingDecision, WorkflowStatus
from src.db.models import Invoice, PurchaseOrder, Vendor, POLineItem
from src.models import MatchingResult, RiskAssessment, RiskLevel, RiskFlag


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_invoice():
    """Create mock invoice."""
    return Invoice(
        id=1,
        document_id="DOC-001",
        file_path="/uploads/invoice.pdf",
        file_hash="abc123",
        extraction_status="completed",
        invoice_number="INV-12345",
        invoice_date=datetime(2026, 1, 5),
        due_date=datetime(2026, 2, 5),
        total_amount=Decimal("1000.00"),
        currency="USD",
        vendor_name="Tech Supplies Inc",
        po_number="PO-001",
        confidence_score=0.95,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_po():
    """Create mock purchase order."""
    return PurchaseOrder(
        id=1,
        po_number="PO-001",
        vendor_id="V001",
        po_date=datetime(2026, 1, 1),
        total_amount=Decimal("1000.00"),
        currency="USD",
        status="open",
        payment_terms="Net 30",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_vendor():
    """Create mock vendor."""
    return Vendor(
        id=1,
        vendor_id="V001",
        vendor_name="Tech Supplies Inc",
        risk_level="low",
        on_time_payment_rate=0.95,
        total_invoices_processed=50,
        is_active=True,
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
        # Setup mocks
        with patch("src.orchestration.workflow_nodes.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.workflow_nodes.PurchaseOrderRepository") as mock_po_repo_cls, \
             patch("src.orchestration.workflow_nodes.VendorRepository") as mock_vendor_repo_cls, \
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
                document_id="DOC-001",
                po_number="PO-001",
                match_score=0.96,
                match_type="exact",
                discrepancies=[],
                requires_approval=False,
                ai_decision_used=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # Configure risk agent
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                document_id="DOC-001",
                risk_level=RiskLevel.LOW,
                overall_risk_score=0.15,
                risk_flags=[],
                duplicate_info=None,
                vendor_info={"risk_score": 0.10, "payment_history": "excellent"},
                price_anomaly_info=None,
                recommended_action="approve",
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
        with patch("src.orchestration.workflow_nodes.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.workflow_nodes.VendorRepository") as mock_vendor_repo_cls, \
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
            from src.models import Discrepancy, DiscrepancyType, DiscrepancySeverity
            mock_matching_agent = AsyncMock()
            mock_matching_result = MatchingResult(
                document_id="DOC-001",
                po_number="PO-001",
                match_score=0.88,
                match_type="fuzzy",
                discrepancies=[
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.AMOUNT,
                        severity=DiscrepancySeverity.CRITICAL,
                        invoice_value="1200.00",
                        po_value="1000.00",
                        difference=200.00,
                        description="Amount exceeds PO by 20%",
                    )
                ],
                requires_approval=True,
                ai_decision_used=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # Low risk assessment
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                document_id="DOC-001",
                risk_level=RiskLevel.LOW,
                overall_risk_score=0.20,
                risk_flags=[],
                duplicate_info=None,
                vendor_info={"risk_score": 0.10},
                price_anomaly_info=None,
                recommended_action="review",
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
        with patch("src.orchestration.workflow_nodes.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.workflow_nodes.VendorRepository") as mock_vendor_repo_cls, \
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
                document_id="DOC-001",
                po_number="PO-001",
                match_score=0.95,
                match_type="exact",
                discrepancies=[],
                requires_approval=False,
                ai_decision_used=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # Duplicate detected
            from src.models import DuplicateInfo
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                document_id="DOC-001",
                risk_level=RiskLevel.CRITICAL,
                overall_risk_score=0.90,
                risk_flags=[
                    RiskFlag(
                        flag_type="DUPLICATE_INVOICE",
                        severity="critical",
                        description="Exact duplicate found (invoice number match)",
                        confidence_score=1.0,
                    )
                ],
                duplicate_info=DuplicateInfo(
                    is_duplicate=True,
                    match_type="invoice_number",
                    confidence_score=1.0,
                    existing_document_id="DOC-000",
                    days_apart=5,
                ),
                vendor_info=None,
                price_anomaly_info=None,
                recommended_action="reject",
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
        with patch("src.orchestration.workflow_nodes.InvoiceRepository") as mock_invoice_repo_cls, \
             patch("src.orchestration.workflow_nodes.VendorRepository") as mock_vendor_repo_cls, \
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
                document_id="DOC-001",
                po_number="PO-001",
                match_score=0.92,
                match_type="exact",
                discrepancies=[],
                requires_approval=False,
                ai_decision_used=False,
                matched_at=datetime.utcnow(),
            )
            mock_matching_agent.match_invoice_to_po = AsyncMock(return_value=mock_matching_result)
            mock_matching_agent_cls.return_value = mock_matching_agent
            
            # High risk with multiple flags
            mock_risk_agent = AsyncMock()
            mock_risk_result = RiskAssessment(
                document_id="DOC-001",
                risk_level=RiskLevel.HIGH,
                overall_risk_score=0.65,
                risk_flags=[
                    RiskFlag(
                        flag_type="VENDOR_RISK",
                        severity="high",
                        description="Vendor has poor payment history",
                        confidence_score=0.80,
                    ),
                    RiskFlag(
                        flag_type="PRICE_ANOMALY",
                        severity="high",
                        description="Price 35% above historical average",
                        confidence_score=0.85,
                    ),
                ],
                duplicate_info=None,
                vendor_info={"risk_score": 0.70, "payment_history": "poor"},
                price_anomaly_info={"z_score": 2.5, "percentage_difference": 35},
                recommended_action="investigate",
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
        with patch("src.orchestration.workflow_nodes.InvoiceRepository") as mock_invoice_repo_cls:
            
            # Invoice with incomplete extraction
            incomplete_invoice = Invoice(
                id=1,
                document_id="DOC-002",
                file_path="/uploads/invoice.pdf",
                file_hash="xyz789",
                extraction_status="pending",
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
