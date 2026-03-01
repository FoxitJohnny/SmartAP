# SmartAP Sample Invoice Dataset

This directory contains **50 synthetic invoices** whose PO numbers, vendor
names, and line items are aligned with the deterministic seed data in
`src/db/seed_data.py`. This ensures 3-way matching produces meaningful
results during demonstrations.

## Quick Reference — Clean Invoices

| # | Invoice | PO | Vendor | Scenario |
|---|---------|-----|--------|----------|
| 01 | INV-2025-1001 | PO-2025-001 | V001 Acme Office Supplies | **Exact match** (happy path) |
| 02 | INV-2025-1002 | PO-2025-002 | V002 TechGear Solutions | Exact match |
| 03 | INV-2025-1003 | PO-2025-003 | V003 QuickPrint Services | Exact match |
| 04 | INV-2025-1004 | PO-2025-004 | V004 Global Logistics | Exact match |
| 05 | INV-2025-1005 | PO-2025-009 | V001 Acme Office Supplies | Exact match |
| 06 | INV-2025-1006 | PO-2025-010 | V008 FastShip Express | Exact match |
| 07 | INV-2025-1007 | PO-2025-005 | V006 Premium IT Services | Partial delivery (10/20 licences) |
| 08 | INV-2025-1008 | PO-2025-006 | V001 Acme Office Supplies | Partial delivery (4/10 chairs) |
| 09 | INV-2025-1009 | PO-2025-001 | V001 Acme Office Supplies | Price variance +5 % |
| 10 | INV-2025-1010 | PO-2025-002 | V002 TechGear Solutions | Quantity mismatch (12 vs 10 monitors) |
| 11 | INV-2025-1011 | PO-2025-004 | V004 Global Logistics | Overbilled +10 % |
| 12 | INV-2025-1012 | PO-2025-005 | V006 Premium IT Services | Remaining partial |
| 13 | INV-2025-1013 | — | V001 Acme Office Supplies | Missing PO |
| 14 | INV-2025-1014 | — | V007 Metro Facility Services | Missing PO |
| 15 | INV-2025-1015 | — | V010 Enterprise Solutions Group | Missing PO |
| 16 | INV-2025-1016 | PO-2025-007 | V003 QuickPrint Services | Against **closed** PO |
| 17 | INV-2025-1017 | PO-2025-008 | V007 Metro Facility Services | Against **closed** PO |
| 18 | INV-2025-1018 | PO-2024-099 | V002 TechGear Solutions | Against **closed** PO |
| 19 | INV-2025-1019 | PO-2025-001 | V001 Acme Office Supplies | Partial shipment (3/6 items) |
| 20 | INV-2025-1020 | PO-2025-002 | V002 TechGear Solutions | 5 % discount applied |

## Directory Structure

```
sample-data/invoices/
├── clean/           20 well-formatted invoices + ground-truth JSON
├── messy/           15 simulated poor-quality scans + JSON
└── edge-cases/      15 special cases + JSON
    ├── multipage_*  5 multi-page invoices (25-40 line items)
    ├── duplicate_*  3 duplicates of clean invoices
    ├── price_spike_* 3 invoices with 200-400 % price increases
    └── missing_po_* 4 invoices with no PO reference
```

## Regenerating

```bash
cd backend
python scripts/generate_sample_data.py
```

The generator uses `random.seed(42)` for deterministic output.

## Ground Truth JSON Format

Each PDF has a sibling `.json` file with extracted fields for validation.

## License

All company names, addresses, and tax IDs are fictional.
