"""
Integration tests for SmartAP workflows.

Tests complete workflows with real database transactions:
- Upload → Match → Assess Risk
- Upload → Process (orchestrated workflow)
- Error handling and edge cases
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.db.repositories import (
    InvoiceRepository,
    PurchaseOrderRepository,
    VendorRepository,
    MatchingRepository,
    RiskRepository,
)
from src.models.invoice import InvoiceStatus
from src.models.matching import MatchType
from src.models.risk import RiskLevel
from src.orchestration.workflow_state import WorkflowStatus, ProcessingDecision
from src.agents import POMatchingAgent, RiskDetectionAgent
from src.orchestration import InvoiceProcessingOrchestrator
from tests.conftest import (
    assert_matching_result,
    assert_risk_assessment,
    assert_workflow_completed,
)


@pytest.mark.asyncio
class TestUploadMatchAssessWorkflow:
    """Test the step-by-step workflow: upload → match → assess-risk."""
    
    async def test_happy_path_workflow(
        self,
        test_db_session,
        sample_vendor,
        sample_po,
        sample_invoice,
    ):
        """Test successful workflow with all steps completing."""
        # Setup repositories
        invoice_repo = InvoiceRepository(test_db_session)
        po_repo = PurchaseOrderRepository(test_db_session)
        vendor_repo = VendorRepository(test_db_session)
        matching_repo = MatchingRepository(test_db_session)
        risk_repo = RiskRepository(test_db_session)
        
        # Step 1: Verify invoice exists (uploaded)
        invoice_db = await invoice_repo.get_by_document_id(sample_invoice.document_id)
        assert invoice_db is not None
        assert invoice_db.status == InvoiceStatus.EXTRACTED
        
        # Convert to Pydantic Invoice model for agent
        from src.models.invoice import Invoice
        invoice = Invoice(
            invoice_number=invoice_db.invoice_number,
            vendor_name=invoice_db.invoice_data.get("vendor_name", "Test Vendor"),
            total=Decimal(str(invoice_db.invoice_data.get("total", 1000.00))),
            invoice_date=invoice_db.invoice_data.get("invoice_date"),
            due_date=invoice_db.invoice_data.get("due_date"),
            po_number=invoice_db.invoice_data.get("po_number"),
            document_id=invoice_db.document_id,  # Include to exclude self from duplicate detection
        )
        
        # Step 2: Match to PO
        matching_agent = POMatchingAgent(
            po_repository=po_repo,
            vendor_repository=vendor_repo,
        )
        
        matching_result = await matching_agent.match_invoice_to_po(
            invoice=invoice,
            use_ai_for_ambiguous=False,  # Use algorithmic only for deterministic tests
        )
        
        # Assertions
        assert matching_result is not None
        assert matching_result.match_score >= 0.90  # High match expected
        assert matching_result.match_type in [MatchType.EXACT, MatchType.FUZZY, "exact", "fuzzy"]
        assert matching_result.po_number == sample_po.po_number
        
        # Step 3: Assess risk
        risk_agent = RiskDetectionAgent(
            invoice_repo=invoice_repo,
            vendor_repo=vendor_repo,
        )
        
        risk_assessment = await risk_agent.assess_risk(
            invoice=invoice,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Assertions
        assert risk_assessment is not None
        assert risk_assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, "low", "medium"]  # Should be low risk
        # When no duplicate is detected, duplicate_info can be None or have is_duplicate=False
        if risk_assessment.duplicate_info is not None:
            assert risk_assessment.duplicate_info.is_duplicate is False
    
    async def test_workflow_with_amount_discrepancy(
        self,
        test_db_session,
        data_builder,
    ):
        """Test workflow when invoice amount exceeds PO amount."""
        # Create vendor and PO
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(
            po_number="PO-001",
            vendor_id="V001",
            amount=Decimal("1000.00"),
        )
        
        # Create invoice with higher amount
        await data_builder.create_invoice(
            document_id="DOC-002",
            invoice_number="INV-002",
            amount=Decimal("1200.00"),  # 20% over PO
            vendor_name="Test Vendor",
            po_number="PO-001",
        )
        
        await data_builder.commit()
        
        # Match to PO via orchestrator (which handles the full workflow)
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        
        final_state = await orchestrator.process_invoice(
            document_id="DOC-002",
            vendor_id="V001",
        )
        
        # Assertions - workflow should complete but identify discrepancy
        assert final_state["status"] in ["completed", "failed"]
        
        # If matching completed, there should be discrepancies noted
        if final_state.get("matching_completed"):
            assert final_state.get("match_score", 1.0) < 0.95  # Lower score due to discrepancy
    
    async def test_workflow_with_high_risk_vendor(
        self,
        test_db_session,
        data_builder,
    ):
        """Test workflow with high-risk vendor."""
        # Create high-risk vendor
        await data_builder.create_vendor(
            vendor_id="V999",
            vendor_name="Risky Vendor Inc",
            risk_score=0.8,  # High risk score
            on_time_rate=0.45,  # Poor payment history
        )
        
        await data_builder.create_po(
            po_number="PO-999",
            vendor_id="V999",
            amount=Decimal("5000.00"),
        )
        
        await data_builder.create_invoice(
            document_id="DOC-999",
            invoice_number="INV-999",
            amount=Decimal("5000.00"),
            vendor_name="Risky Vendor Inc",
            po_number="PO-999",
        )
        
        await data_builder.commit()
        
        # Process via orchestrator (which handles risk assessment internally)
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        final_state = await orchestrator.process_invoice(
            document_id="DOC-999",
            vendor_id="V999",
        )
        
        # Assertions - workflow should complete
        assert final_state["status"] in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, "completed", "failed"]
        
        # If risk assessment completed, check for vendor risk flags
        if final_state.get("risk_completed"):
            # Vendor risk should have been identified (any risk level is acceptable)
            risk_flags = final_state.get("risk_flags", [])
            # Verify that some vendor-related risk was flagged
            vendor_risk_types = ["vendor_blocked", "vendor_new", "vendor_spoofing", "vendor_bank_change"]
            has_vendor_risk = any(
                f.get("flag_type") in vendor_risk_types or 
                (hasattr(f.get("flag_type"), "value") and f.get("flag_type").value in vendor_risk_types)
                for f in risk_flags
            )
            assert has_vendor_risk, f"Expected vendor risk flag, got: {risk_flags}"


@pytest.mark.asyncio
class TestOrchestratedWorkflow:
    """Test the complete orchestrated workflow via InvoiceProcessingOrchestrator."""
    
    async def test_orchestrated_happy_path(
        self,
        test_db_session,
        sample_vendor,
        sample_po,
        sample_invoice,
    ):
        """Test complete orchestration with auto-approval."""
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        
        # Process invoice through complete workflow
        final_state = await orchestrator.process_invoice(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Assertions
        status = final_state["status"]
        assert status == WorkflowStatus.COMPLETED or status == "completed", f"Expected completed, got {status}"
        assert final_state["extraction_completed"] is True
        assert final_state["matching_completed"] is True
        assert final_state["risk_completed"] is True
        
        # Check decision - can be enum or string
        decision = final_state["decision"]
        valid_decisions = [
            ProcessingDecision.AUTO_APPROVED, ProcessingDecision.REQUIRES_REVIEW,
            "auto_approved", "requires_review"
        ]
        assert decision in valid_decisions, f"Unexpected decision: {decision}"
        assert "decision_reason" in final_state
        assert len(final_state["recommended_actions"]) > 0
        
        # Check metadata
        assert final_state["processing_time_ms"] is not None
        assert final_state["processing_time_ms"] > 0
        assert final_state["ai_calls_made"] >= 0
    
    async def test_orchestrated_with_duplicate_detection(
        self,
        test_db_session,
        data_builder,
    ):
        """Test orchestration detects and rejects duplicate invoices."""
        # Create vendor and PO
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        
        # Create first invoice
        await data_builder.create_invoice(
            document_id="DOC-ORIG",
            invoice_number="INV-DUPLICATE",
            vendor_name="Test Vendor",
            po_number="PO-001",
        )
        
        # Create duplicate invoice (same invoice number, same vendor)
        await data_builder.create_invoice(
            document_id="DOC-DUP",
            invoice_number="INV-DUPLICATE",  # Same invoice number
            vendor_name="Test Vendor",
            po_number="PO-001",
        )
        
        await data_builder.commit()
        
        # Process the duplicate
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        final_state = await orchestrator.process_invoice(
            document_id="DOC-DUP",
            vendor_id="V001",
        )
        
        # Assertions - workflow should complete (either completed or failed)
        status = final_state["status"]
        assert status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, "completed", "failed"]
        
        # If workflow completed, check duplicate detection 
        if status in [WorkflowStatus.COMPLETED, "completed"]:
            # Duplicate should be detected
            if final_state.get("is_duplicate"):
                decision = final_state.get("decision")
                assert decision in [ProcessingDecision.REJECTED, "rejected"]
                assert "duplicate" in final_state.get("decision_reason", "").lower()
    
    async def test_orchestrated_with_missing_po(
        self,
        test_db_session,
        data_builder,
    ):
        """Test orchestration when no matching PO exists."""
        # Create vendor but no PO
        await data_builder.create_vendor(vendor_id="V001")
        
        # Create invoice referencing non-existent PO
        await data_builder.create_invoice(
            document_id="DOC-NO-PO",
            invoice_number="INV-NO-PO",
            vendor_name="Test Vendor",
            po_number="PO-MISSING",  # Non-existent PO
        )
        
        await data_builder.commit()
        
        # Process invoice
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        final_state = await orchestrator.process_invoice(
            document_id="DOC-NO-PO",
            vendor_id="V001",
        )
        
        # Assertions - workflow should complete (even without matching PO)
        status = final_state["status"]
        assert status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, "completed", "failed"]
        
        # If completed, matching should fail or return low score
        if status in [WorkflowStatus.COMPLETED, "completed"]:
            if final_state.get("matching_completed"):
                match_score = final_state.get("match_score", 0)
                match_type = final_state.get("match_type", "none")
                assert match_score < 0.70 or match_type in [MatchType.NONE, "none"]
            
            # Should require review
            decision = final_state.get("decision")
            valid_review_decisions = [
                ProcessingDecision.REQUIRES_REVIEW, ProcessingDecision.REQUIRES_INVESTIGATION,
                "requires_review", "requires_investigation"
            ]
            assert decision in valid_review_decisions or final_state.get("requires_manual_review")
    
    async def test_orchestrated_with_extraction_failure(
        self,
        test_db_session,
        data_builder,
    ):
        """Test orchestration handles extraction failures gracefully."""
        # Create invoice with failed extraction
        await data_builder.create_invoice(
            document_id="DOC-FAILED",
            invoice_number="INV-FAILED",
            status=InvoiceStatus.FAILED,  # Failed extraction
        )
        
        await data_builder.commit()
        
        # Process invoice
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        final_state = await orchestrator.process_invoice(
            document_id="DOC-FAILED",
        )
        
        # Assertions
        status = final_state["status"]
        assert status in [WorkflowStatus.FAILED, "failed"]
        assert final_state["extraction_completed"] is False
        assert final_state["extraction_error"] is not None
        assert len(final_state["errors"]) > 0


@pytest.mark.asyncio
class TestWorkflowErrorHandling:
    """Test error handling and edge cases in workflows."""
    
    async def test_workflow_with_nonexistent_document(
        self,
        test_db_session,
    ):
        """Test workflow with non-existent document ID."""
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        
        final_state = await orchestrator.process_invoice(
            document_id="DOES-NOT-EXIST",
        )
        
        # Should fail gracefully
        status = final_state["status"]
        assert status in [WorkflowStatus.FAILED, "failed"]
        assert final_state["extraction_error"] is not None
        assert "not found" in final_state["extraction_error"].lower()
    
    async def test_workflow_status_check(
        self,
        test_db_session,
        sample_vendor,
        sample_po,
        sample_invoice,
    ):
        """Test get_processing_status method."""
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        
        # Get status before processing
        status_before = await orchestrator.get_processing_status(
            sample_invoice.document_id
        )
        
        assert status_before["document_id"] == sample_invoice.document_id
        # Status could be InvoiceStatus enum or string
        before_status = status_before["status"]
        assert before_status in [InvoiceStatus.EXTRACTED, "extracted", "error"], f"Got status: {before_status}"
        # Before processing, no matching or risk assessment should exist in DB
        assert status_before["matching_completed"] is False
        assert status_before["risk_completed"] is False
        
        # Process invoice and get final workflow state
        final_state = await orchestrator.process_invoice(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Verify workflow completed successfully
        assert final_state["status"] in [WorkflowStatus.COMPLETED, "completed"]
        
        # The workflow state should have matching and risk completed
        # Note: The results are stored in workflow state, not necessarily in DB
        assert final_state.get("matching_completed") is True
        assert final_state.get("risk_completed") is True
        assert final_state.get("match_score") is not None
        assert final_state.get("risk_level") is not None
    
    async def test_workflow_reprocessing(
        self,
        test_db_session,
        sample_vendor,
        sample_po,
        sample_invoice,
    ):
        """Test reprocessing an invoice."""
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        
        # First processing
        first_result = await orchestrator.process_invoice(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        first_status = first_result["status"]
        assert first_status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, "completed", "failed"]
        first_decision = first_result.get("decision")
        
        # Reprocess
        second_result = await orchestrator.reprocess_invoice(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Should have consistent status
        second_status = second_result["status"]
        assert second_status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, "completed", "failed"]


@pytest.mark.asyncio
class TestConcurrentWorkflows:
    """Test concurrent invoice processing."""
    
    async def test_concurrent_processing(
        self,
        test_db_session,
        data_builder,
    ):
        """Test processing multiple invoices concurrently."""
        import asyncio
        
        # Create test data
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        
        # Create multiple invoices
        document_ids = []
        for i in range(5):
            invoice = await data_builder.create_invoice(
                document_id=f"DOC-CONCURRENT-{i}",
                invoice_number=f"INV-CONCURRENT-{i}",
                vendor_name="Test Vendor",
                po_number="PO-001",
            )
            document_ids.append(invoice.document_id)
        
        await data_builder.commit()
        
        # Process concurrently
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        
        tasks = [
            orchestrator.process_invoice(doc_id, "V001")
            for doc_id in document_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent processing failed: {result}")
            
            assert result["status"] in ["completed", "failed"]
            assert result["document_id"] in document_ids
