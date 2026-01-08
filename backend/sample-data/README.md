# SmartAP Sample Invoice Dataset

This directory contains 50 synthetic invoices for testing SmartAP's AI extraction capabilities.

## Dataset Composition

### Clean Invoices (20 files in `clean/`)
- **US Standard (5):** Clean formatting, USD currency, complete data
- **International (5):** EUR/GBP/JPY currencies, international formats
- **Service Invoices (5):** Hourly rates, consulting, subscriptions
- **Product Invoices (5):** Line items with quantities, SKUs, discounts
- **Quality:** Perfect formatting, high resolution, no noise
- **Purpose:** Test baseline extraction accuracy

### Messy Invoices (15 files in `messy/`)
- **Quality Issues:** Poor scans, noise, rotation, low resolution
- **Artifacts:** Simulated poor scan quality
- **Purpose:** Test robustness to real-world document quality issues
- **Expected Accuracy:** 80-90% (lower than clean invoices)

### Edge Cases (15 files in `edge-cases/`)
- **Multi-page (5):** 25-40 line items across 3-5 pages
- **Duplicates (3):** Same vendor/amount to test fraud detection
- **Price Spikes (3):** 200%+ increase from historical average
- **Missing PO (4):** No PO number to test matching logic
- **Purpose:** Test exception handling and manual review triggers

## File Structure

```
sample-data/
├── invoices/
│   ├── clean/
│   │   ├── clean_01_INV-2024-1234.pdf
│   │   ├── clean_01_INV-2024-1234.json  (ground truth)
│   │   └── ...
│   ├── messy/
│   │   ├── messy_01_BILL-2025-5678.pdf
│   │   ├── messy_01_BILL-2025-5678.json
│   │   └── ...
│   └── edge-cases/
│       ├── multipage_01_SI-2026-9012.pdf
│       ├── multipage_01_SI-2026-9012.json
│       ├── duplicate_01.pdf
│       ├── price_spike_01_INV-2025-3456.pdf
│       ├── missing_po_01_NO-2024-7890.pdf
│       └── ...
└── README.md (this file)
```

## Ground Truth JSON Format

Each PDF has a corresponding JSON file with ground truth data for validation.

## Usage

### Running Sample Data Generation
```bash
cd backend
python scripts/generate_sample_data.py
```

## Expected Metrics

| Invoice Type | Header Fields | Line Items | Total Amount | Overall |
|--------------|---------------|------------|--------------|---------|
| Clean        | >98%          | >95%       | >99%         | >97%    |
| Messy        | >85%          | >80%       | >90%         | >85%    |
| Multi-page   | >90%          | >85%       | >95%         | >90%    |
| Edge Cases   | >80%          | >75%       | >85%         | >80%    |

**Overall Dataset:** >90% extraction accuracy

## License

These synthetic invoices are released under MIT License for testing purposes.
All company names, addresses, and tax IDs are fictional.
