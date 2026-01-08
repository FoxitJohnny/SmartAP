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
        invoice = await invoice_repo.get_by_document_id(sample_invoice.document_id)
        assert invoice is not None
        assert invoice.extraction_status == "completed"
        
        # Step 2: Match to PO
        matching_agent = POMatchingAgent(
            invoice_repository=invoice_repo,
            po_repository=po_repo,
            matching_repository=matching_repo,
        )
        
        matching_result = await matching_agent.match_invoice_to_po(
            document_id=sample_invoice.document_id,
            use_ai=False,  # Use algorithmic only for deterministic tests
        )
        
        # Assertions
        assert matching_result is not None
        assert matching_result.match_score >= 0.90  # High match expected
        assert matching_result.match_type in ["exact", "fuzzy"]
        assert matching_result.po_number == sample_po.po_number
        
        # Verify matching result saved to database
        saved_matching = await matching_repo.get_by_document_id(sample_invoice.document_id)
        assert saved_matching is not None
        assert saved_matching.match_score == matching_result.match_score
        
        # Step 3: Assess risk
        risk_agent = RiskDetectionAgent(
            invoice_repository=invoice_repo,
            vendor_repository=vendor_repo,
            risk_repository=risk_repo,
        )
        
        risk_assessment = await risk_agent.assess_risk(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Assertions
        assert risk_assessment is not None
        assert risk_assessment.risk_level in ["low", "medium"]  # Should be low risk
        assert risk_assessment.duplicate_info is not None
        assert risk_assessment.duplicate_info.is_duplicate is False
        
        # Verify risk assessment saved to database
        saved_risk = await risk_repo.get_by_document_id(sample_invoice.document_id)
        assert saved_risk is not None
        assert saved_risk.risk_level == risk_assessment.risk_level
    
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
        
        # Match to PO
        invoice_repo = InvoiceRepository(test_db_session)
        po_repo = PurchaseOrderRepository(test_db_session)
        matching_repo = MatchingRepository(test_db_session)
        
        matching_agent = POMatchingAgent(
            invoice_repository=invoice_repo,
            po_repository=po_repo,
            matching_repository=matching_repo,
        )
        
        matching_result = await matching_agent.match_invoice_to_po(
            document_id="DOC-002",
            use_ai=False,
        )
        
        # Assertions
        assert matching_result.match_score < 0.95  # Lower score due to discrepancy
        assert len(matching_result.discrepancies) > 0
        
        # Check for amount discrepancy
        amount_discrepancies = [
            d for d in matching_result.discrepancies
            if d.discrepancy_type == "amount_mismatch"
        ]
        assert len(amount_discrepancies) > 0
        assert amount_discrepancies[0].severity in ["major", "critical"]
    
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
            risk_level="high",
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
        
        # Assess risk
        invoice_repo = InvoiceRepository(test_db_session)
        vendor_repo = VendorRepository(test_db_session)
        risk_repo = RiskRepository(test_db_session)
        
        risk_agent = RiskDetectionAgent(
            invoice_repository=invoice_repo,
            vendor_repository=vendor_repo,
            risk_repository=risk_repo,
        )
        
        risk_assessment = await risk_agent.assess_risk(
            document_id="DOC-999",
            vendor_id="V999",
        )
        
        # Assertions
        assert risk_assessment.risk_level in ["high", "critical"]
        assert risk_assessment.vendor_info is not None
        
        # Check for vendor risk flags
        vendor_flags = [
            f for f in risk_assessment.risk_flags
            if f.flag_type == "VENDOR_RISK"
        ]
        assert len(vendor_flags) > 0


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
        assert final_state["status"] == "completed"
        assert final_state["extraction_completed"] is True
        assert final_state["matching_completed"] is True
        assert final_state["risk_completed"] is True
        
        # Check decision
        assert final_state["decision"] in ["auto_approved", "requires_review"]
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
        
        # Assertions
        assert final_state["status"] == "completed"
        assert final_state["is_duplicate"] is True
        assert final_state["decision"] == "rejected"
        assert "duplicate" in final_state["decision_reason"].lower()
    
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
        
        # Assertions
        assert final_state["status"] == "completed"
        
        # Matching should fail or return low score
        if final_state["matching_completed"]:
            assert final_state["match_score"] < 0.70 or final_state["match_type"] == "none"
        
        # Should require review
        assert final_state["decision"] in ["requires_review", "requires_investigation"]
        assert final_state["requires_manual_review"] is True
    
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
            extraction_status="failed",  # Failed extraction
        )
        
        await data_builder.commit()
        
        # Process invoice
        orchestrator = InvoiceProcessingOrchestrator(test_db_session)
        final_state = await orchestrator.process_invoice(
            document_id="DOC-FAILED",
        )
        
        # Assertions
        assert final_state["status"] == "failed"
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
        assert final_state["status"] == "failed"
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
        assert status_before["extraction_status"] == "completed"
        assert status_before["matching_completed"] is False
        assert status_before["risk_completed"] is False
        
        # Process invoice
        await orchestrator.process_invoice(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Get status after processing
        status_after = await orchestrator.get_processing_status(
            sample_invoice.document_id
        )
        
        assert status_after["matching_completed"] is True
        assert status_after["risk_completed"] is True
        assert status_after["match_score"] is not None
        assert status_after["risk_level"] is not None
    
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
        
        assert first_result["status"] == "completed"
        first_decision = first_result["decision"]
        
        # Reprocess
        second_result = await orchestrator.reprocess_invoice(
            document_id=sample_invoice.document_id,
            vendor_id=sample_vendor.vendor_id,
        )
        
        # Should complete successfully
        assert second_result["status"] == "completed"
        # Decision should be consistent (same data)
        assert second_result["decision"] == first_decision


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
