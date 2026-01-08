"""
Performance and load tests for SmartAP API.

Tests system performance under various load conditions:
- Response time benchmarks
- Throughput testing
- Concurrent request handling
- Resource usage monitoring
"""

import pytest
import time
import asyncio
from decimal import Decimal
from typing import List, Dict

from fastapi.testclient import TestClient
from src.main import app
from src.db.database import get_session


@pytest.mark.performance
@pytest.mark.asyncio
class TestResponseTimes:
    """Test response time benchmarks for each endpoint."""
    
    @pytest.fixture
    def override_db_session(self, test_db_session):
        """Override get_session dependency."""
        async def _get_test_session():
            yield test_db_session
        
        app.dependency_overrides[get_session] = _get_test_session
        yield
        app.dependency_overrides.clear()
    
    async def test_matching_performance(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Benchmark PO matching performance."""
        # Setup data
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        await data_builder.create_invoice(
            document_id="DOC-PERF-MATCH",
            invoice_number="INV-PERF-MATCH",
            vendor_name="Test Vendor",
            po_number="PO-001",
        )
        await data_builder.commit()
        
        # Warm-up request
        test_client.post(
            "/api/v1/invoices/DOC-PERF-MATCH/match",
            params={"use_ai": False},
        )
        
        # Benchmark
        times = []
        for _ in range(10):
            start = time.time()
            response = test_client.post(
                "/api/v1/invoices/DOC-PERF-MATCH/match",
                params={"use_ai": False},
            )
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nPO Matching Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        
        # Assertions
        assert avg_time < 2000, f"Average matching time {avg_time:.0f}ms exceeds 2s"
        assert max_time < 5000, f"Max matching time {max_time:.0f}ms exceeds 5s"
    
    async def test_risk_assessment_performance(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Benchmark risk assessment performance."""
        # Setup data
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_invoice(
            document_id="DOC-PERF-RISK",
            invoice_number="INV-PERF-RISK",
            vendor_name="Test Vendor",
        )
        await data_builder.commit()
        
        # Benchmark
        times = []
        for _ in range(10):
            start = time.time()
            response = test_client.post(
                "/api/v1/invoices/DOC-PERF-RISK/assess-risk",
                params={"vendor_id": "V001"},
            )
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        
        print(f"\nRisk Assessment Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        
        assert avg_time < 1500, f"Average risk assessment {avg_time:.0f}ms exceeds 1.5s"
    
    async def test_orchestration_performance(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Benchmark complete orchestration performance."""
        # Setup data
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        await data_builder.create_invoice(
            document_id="DOC-PERF-ORCH",
            invoice_number="INV-PERF-ORCH",
            vendor_name="Test Vendor",
            po_number="PO-001",
        )
        await data_builder.commit()
        
        # Benchmark
        times = []
        for _ in range(5):  # Fewer iterations for complete workflow
            start = time.time()
            response = test_client.post(
                "/api/v1/invoices/DOC-PERF-ORCH/process",
                params={"vendor_id": "V001"},
            )
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        
        print(f"\nOrchestration Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        
        assert avg_time < 8000, f"Average orchestration {avg_time:.0f}ms exceeds 8s"


@pytest.mark.load
@pytest.mark.asyncio
class TestConcurrentLoad:
    """Test system under concurrent load."""
    
    @pytest.fixture
    def override_db_session(self, test_db_session):
        """Override get_session dependency."""
        async def _get_test_session():
            yield test_db_session
        
        app.dependency_overrides[get_session] = _get_test_session
        yield
        app.dependency_overrides.clear()
    
    async def test_concurrent_matching_requests(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Test concurrent PO matching requests."""
        # Setup data for multiple invoices
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        
        document_ids = []
        for i in range(20):
            invoice = await data_builder.create_invoice(
                document_id=f"DOC-LOAD-{i}",
                invoice_number=f"INV-LOAD-{i}",
                vendor_name="Test Vendor",
                po_number="PO-001",
            )
            document_ids.append(invoice.document_id)
        
        await data_builder.commit()
        
        # Concurrent requests
        import concurrent.futures
        
        def make_request(doc_id):
            start = time.time()
            response = test_client.post(
                f"/api/v1/invoices/{doc_id}/match",
                params={"use_ai": False},
            )
            end = time.time()
            return {
                "doc_id": doc_id,
                "status_code": response.status_code,
                "time_ms": (end - start) * 1000,
            }
        
        start_all = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, document_ids))
        
        end_all = time.time()
        total_time = (end_all - start_all) * 1000
        
        # Analyze results
        successful = [r for r in results if r["status_code"] == 200]
        failed = [r for r in results if r["status_code"] != 200]
        
        avg_response_time = sum(r["time_ms"] for r in successful) / len(successful) if successful else 0
        throughput = len(successful) / (total_time / 1000)  # requests per second
        
        print(f"\nConcurrent Load Test (20 requests, 10 workers):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Successful: {len(successful)}/{len(results)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Avg response time: {avg_response_time:.2f}ms")
        print(f"  Throughput: {throughput:.2f} req/s")
        
        # Assertions
        assert len(successful) >= 18, f"Too many failures: {len(failed)}/20"
        assert avg_response_time < 3000, f"Avg response {avg_response_time:.0f}ms too high"
    
    async def test_concurrent_orchestration_load(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Test concurrent orchestration requests."""
        # Setup data
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        
        document_ids = []
        for i in range(10):  # Fewer for full workflow
            invoice = await data_builder.create_invoice(
                document_id=f"DOC-ORCH-LOAD-{i}",
                invoice_number=f"INV-ORCH-LOAD-{i}",
                vendor_name="Test Vendor",
                po_number="PO-001",
            )
            document_ids.append(invoice.document_id)
        
        await data_builder.commit()
        
        # Concurrent orchestration
        import concurrent.futures
        
        def process_invoice(doc_id):
            start = time.time()
            response = test_client.post(
                f"/api/v1/invoices/{doc_id}/process",
                params={"vendor_id": "V001"},
            )
            end = time.time()
            return {
                "doc_id": doc_id,
                "status_code": response.status_code,
                "time_ms": (end - start) * 1000,
                "decision": response.json().get("decision") if response.status_code == 200 else None,
            }
        
        start_all = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_invoice, document_ids))
        
        end_all = time.time()
        total_time = (end_all - start_all) * 1000
        
        # Analyze results
        successful = [r for r in results if r["status_code"] == 200]
        
        print(f"\nConcurrent Orchestration Load (10 requests, 5 workers):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Successful: {len(successful)}/10")
        
        if successful:
            avg_time = sum(r["time_ms"] for r in successful) / len(successful)
            print(f"  Avg processing time: {avg_time:.2f}ms")
            
            decisions = {}
            for r in successful:
                decision = r.get("decision", "unknown")
                decisions[decision] = decisions.get(decision, 0) + 1
            print(f"  Decisions: {decisions}")
        
        # Assertions
        assert len(successful) >= 8, f"Too many failures: {10 - len(successful)}/10"


@pytest.mark.stress
@pytest.mark.asyncio
class TestStressScenarios:
    """Stress tests for system limits."""
    
    @pytest.fixture
    def override_db_session(self, test_db_session):
        """Override get_session dependency."""
        async def _get_test_session():
            yield test_db_session
        
        app.dependency_overrides[get_session] = _get_test_session
        yield
        app.dependency_overrides.clear()
    
    async def test_many_line_items_performance(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Test performance with many line items."""
        # Create PO with many line items
        await data_builder.create_vendor(vendor_id="V001")
        po = await data_builder.create_po(
            po_number="PO-MANY-ITEMS",
            vendor_id="V001",
            amount=Decimal("10000.00"),
        )
        
        # Add 50 line items
        from src.db.models import POLineItem as POLineItemORM
        for i in range(50):
            line_item = POLineItemORM(
                po_id=po.id,
                line_number=i + 1,
                description=f"Item {i + 1}",
                quantity=10,
                unit_price=Decimal("20.00"),
                total=Decimal("200.00"),
            )
            test_db_session.add(line_item)
        
        await data_builder.create_invoice(
            document_id="DOC-MANY-ITEMS",
            invoice_number="INV-MANY-ITEMS",
            vendor_name="Test Vendor",
            po_number="PO-MANY-ITEMS",
            amount=Decimal("10000.00"),
        )
        
        await data_builder.commit()
        
        # Test matching with many line items
        start = time.time()
        response = test_client.post(
            "/api/v1/invoices/DOC-MANY-ITEMS/match",
            params={"use_ai": False},
        )
        end = time.time()
        
        processing_time = (end - start) * 1000
        
        print(f"\nMany Line Items Performance (50 items):")
        print(f"  Processing time: {processing_time:.2f}ms")
        
        assert response.status_code == 200
        assert processing_time < 5000, f"Processing {processing_time:.0f}ms too slow"
    
    async def test_rapid_sequential_requests(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Test rapid sequential requests to same resource."""
        # Setup data
        await data_builder.create_invoice(
            document_id="DOC-RAPID",
            invoice_number="INV-RAPID",
        )
        await data_builder.commit()
        
        # Make rapid sequential status checks
        times = []
        for i in range(100):
            start = time.time()
            response = test_client.get("/api/v1/invoices/DOC-RAPID/status")
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"\nRapid Sequential Requests (100 status checks):")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  Max time: {max_time:.2f}ms")
        
        assert avg_time < 100, f"Average {avg_time:.0f}ms too slow"
        assert max_time < 500, f"Max time {max_time:.0f}ms too slow"


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestPerformanceRegression:
    """Baseline performance tests for regression detection."""
    
    @pytest.fixture
    def override_db_session(self, test_db_session):
        """Override get_session dependency."""
        async def _get_test_session():
            yield test_db_session
        
        app.dependency_overrides[get_session] = _get_test_session
        yield
        app.dependency_overrides.clear()
    
    async def test_baseline_full_workflow(
        self,
        test_client: TestClient,
        test_db_session,
        data_builder,
        override_db_session,
    ):
        """Baseline benchmark for complete workflow."""
        # Setup
        await data_builder.create_vendor(vendor_id="V001")
        await data_builder.create_po(po_number="PO-001", vendor_id="V001")
        await data_builder.create_invoice(
            document_id="DOC-BASELINE",
            invoice_number="INV-BASELINE",
            vendor_name="Test Vendor",
            po_number="PO-001",
        )
        await data_builder.commit()
        
        # Run workflow
        start = time.time()
        response = test_client.post(
            "/api/v1/invoices/DOC-BASELINE/process",
            params={"vendor_id": "V001"},
        )
        end = time.time()
        
        total_time = (end - start) * 1000
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"\n=== BASELINE PERFORMANCE METRICS ===")
        print(f"Total API time: {total_time:.2f}ms")
        print(f"Processing time (reported): {data['metadata']['processing_time_ms']}ms")
        print(f"AI calls: {data['metadata']['ai_calls_made']}")
        print(f"Decision: {data['decision']}")
        print(f"Extraction completed: {data['extraction']['completed']}")
        print(f"Matching completed: {data['matching']['completed']}")
        print(f"Risk completed: {data['risk']['completed']}")
        print("====================================")
        
        # Store baseline for comparison (in real project, save to file)
        baseline = {
            "total_time_ms": total_time,
            "processing_time_ms": data["metadata"]["processing_time_ms"],
            "ai_calls": data["metadata"]["ai_calls_made"],
        }
        
        # Baseline assertions (these are targets, not hard limits)
        assert total_time < 10000, "Baseline: Total time should be under 10s"
