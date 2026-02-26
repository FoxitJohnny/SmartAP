# Risk Assessment Logic

## Overview

SmartAP's Risk Assessment system evaluates every uploaded invoice using six weighted
detection dimensions.  The output is an overall **risk score** (0 – 1), a **risk
level** (LOW / MEDIUM / HIGH / CRITICAL), an array of **risk flags** with evidence,
and a **recommended action** that drives the approval workflow.

```
┌───────────────────────────────────────────────────┐
│                 Invoice Upload                     │
└────────────────────┬──────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  RiskDetectionAgent  │   ← agents/risk_detection_agent.py
          └──────────┬──────────┘
                     │
   ┌─────────────────┼──────────────────────┐
   │  Six parallel   │  detection           │
   │  dimensions     │                      │
   ▼                 ▼                      ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ Duplicate│  │  Vendor  │  │  Price       │
│    25%   │  │   20%    │  │  Anomaly 15% │
└──────────┘  └──────────┘  └──────────────┘
   ▼                 ▼                      ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│  Amount  │  │ Matching │  │  Pattern     │
│    10%   │  │   20%    │  │    10%       │
└──────────┘  └──────────┘  └──────────────┘
                     │
          ┌──────────▼──────────┐
          │  Weighted Sum →  0-1 │
          │  Risk Level          │
          │  Recommended Action  │
          └─────────────────────┘
```

---

## 1. Duplicate Detection (Weight: 25%)

**Service:** `DuplicateDetector` (`services/duplicate_detector.py`)

### Detection Methods

| Method | Description | Similarity score |
|--------|-------------|-----------------|
| **Hash match** | SHA-256 file-content hash — exact file re-upload | 1.0 |
| **Invoice # match** | Same invoice number from same vendor | 0.95 |
| **Fuzzy match** | Similar amount (±5%), same vendor, close date (±7 days) | 0.70 – 0.90 |

### Scoring

- Score = `similarity_score` from the best duplicate candidate (0 – 1).
- A `RiskFlag` is raised when `is_duplicate` is true, with:
  - `flag_type`: `duplicate_exact`, `duplicate_near`, or `duplicate_fuzzy`
  - `severity`: derived from similarity score (≥ 0.90 → critical, ≥ 0.70 → high, etc.)
  - `evidence`, `related_invoice_id`, and `details` for investigation

---

## 2. Vendor Risk Analysis (Weight: 20%)

**Service:** `VendorRiskAnalyzer` (`services/vendor_risk_analyzer.py`)

### Vendor ID Resolution

If the upload pipeline doesn't supply a `vendor_id`, the agent performs a
**name-based fallback lookup** using `VendorRepository.search_by_name()`.
It prefers an exact case-insensitive match and falls back to the top result.

### Vendor Risk Factors

| Factor | Contribution |
|--------|-------------|
| **Blocked/suspended vendor** | score → vendor_risk_score (usually high) |
| **New vendor** (< 3 invoices) | score → 0.40 – 0.60 |
| **Active fraud flags** | adds 0.10 per flag |
| **Payment history** | late payments, disputes raise score |

### Flag Threshold

A `RiskFlag` is raised when `vendor_score ≥ 0.40`:
- `vendor_blocked` – vendor is blacklisted
- `vendor_new` – new vendor with limited history
- `vendor_spoofing` – elevated risk / fraud flags

---

## 3. Price Anomaly Detection (Weight: 15%)

**Service:** `PriceAnomalyDetector` (`services/price_anomaly_detector.py`)

### Algorithm

1. Fetch up to 50 historical invoices from the same vendor.
2. **Exclude the current invoice** from the baseline (by `document_id`) to prevent
   self-inflation of the average.
3. Require at least **3 historical invoices** for a meaningful comparison.
4. Compute **mean ($\mu$)** and **standard deviation ($\sigma$)** of historical totals.
5. Compute **z-score**: $z = \frac{\text{current total} - \mu}{\sigma}$.
6. An anomaly is flagged when $|z| \ge 2.0$ **and** the invoice total $\ge \$1{,}000$.

### Risk Score Mapping

| Percentage deviation | Score |
|---------------------|-------|
| ≥ 50% from average | 1.0 |
| ≥ 30% from average | 0.70 |
| ≥ 15% from average | 0.40 |
| < 15% from average | 0.20 |

### Flag Content

- `flag_type`: `price_anomaly`
- Evidence includes z-score, historical average, and standard deviation
- `expected_value` / `actual_value` show the dollar comparison

---

## 4. Amount Risk (Weight: 10%)

**Service:** `PriceAnomalyDetector.calculate_amount_risk()`

Evaluates the absolute invoice amount against a typical range ($0 – $100,000).

| Condition | Score |
|-----------|-------|
| Amount > $200,000 | 0.30 + scaled excess |
| Amount < 50% of minimum | 0.10 |
| Within normal range | 0.0 |

A `RiskFlag` (`amount_anomaly`) is raised when score ≥ 0.30.

---

## 5. PO Matching Risk (Weight: 20%)

**New in v2.0** — evaluates the quality of the PO-matching step.

### Inputs

The `MatchingResult` from the `POMatchingAgent` is passed into the risk agent
by the upload pipeline (`routes.py`) or workflow node (`workflow_nodes.py`).

### Scoring Matrix

| Condition | Base score |
|-----------|-----------|
| No matching result available | 0.35 |
| **Not matched** (no PO found) | 0.70 |
| Match score < 0.60 | 0.60 |
| Match score < 0.80 | 0.30 |
| Match score < 0.85 | 0.15 |
| Match score ≥ 0.85, no critical discrepancies | 0.0 |

**Discrepancy penalties** (additive, capped at 0.90):
- +0.10 per critical discrepancy
- +0.05 per high discrepancy

### Flags

| Flag type | Condition |
|-----------|-----------|
| `matching_no_match` | Invoice had no matching PO |
| `matching_low_score` | Match score < 0.80 without critical discrepancies |
| `matching_discrepancy` | Critical discrepancies exist |

---

## 6. Pattern Risk (Weight: 10%)

Evaluates **combinations** of existing flags and suspicious patterns.

### Multi-Flag Escalation

| Condition | Score |
|-----------|-------|
| ≥ 2 critical flags | 1.0 |
| 1 critical + ≥ 1 high | 0.80 |
| ≥ 2 high flags | 0.60 |
| ≥ 3 flags of any severity | 0.40 |

### Round-Number Detection

Conservative thresholds to avoid false positives on normal invoices:

| Amount threshold | Divisibility |
|-----------------|-------------|
| ≥ $50,000 | divisible by $10,000 |
| ≥ $25,000 | divisible by $5,000 |
| ≥ $10,000 | divisible by $1,000 |

A match adds **0.10** to the pattern score (minor signal, not standalone evidence).

---

## Overall Risk Score

Weighted sum, clamped to [0, 1]:

$$
S = 0.25 \cdot D + 0.20 \cdot V + 0.15 \cdot P + 0.10 \cdot A + 0.20 \cdot M + 0.10 \cdot T
$$

where $D$ = duplicate, $V$ = vendor, $P$ = price anomaly, $A$ = amount, $M$ = matching, $T$ = pattern.

---

## Risk Level

| Score range | Level |
|-------------|-------|
| < 0.25 | **LOW** |
| 0.25 – 0.49 | **MEDIUM** |
| 0.50 – 0.74 | **HIGH** |
| ≥ 0.75 | **CRITICAL** |

---

## Recommended Action

| Condition | Action |
|-----------|--------|
| CRITICAL level **or** ≥ 2 critical flags | **REJECT** |
| 1 critical flag | **MANAGER_APPROVAL** |
| HIGH level **or** ≥ 2 high flags | **INVESTIGATE** |
| MEDIUM level | **REVIEW** |
| LOW level | **AUTO_APPROVE** |

---

## Risk Flag Schema

Every flag includes structured evidence:

```json
{
  "flag_type": "price_anomaly",
  "severity": "high",
  "description": "Price anomaly: +42.3% from vendor average ($12,500.00)",
  "confidence": 0.85,
  "evidence": "Z-score: 3.21, historical avg: $12,500.00, std dev: $2,100.00",
  "expected_value": "$12,500.00",
  "actual_value": "$17,800.00",
  "deviation": "+42.3%",
  "suggested_action": "Compare line items against recent invoices from this vendor",
  "details": {
    "z_score": 3.21,
    "current_amount": 17800.0,
    "average_amount": 12500.0,
    "std_dev": 2100.0,
    "deviation_pct": 42.3
  }
}
```

---

## Data Flow

```
Upload (routes.py)               Workflow (workflow_nodes.py)
     │                                   │
     ├─ Extract invoice                  ├─ Build Invoice from state
     ├─ PO Matching → matching_result    ├─ Get matching_result from state
     ├─ Resolve vendor_id by name        ├─ Get vendor_id from state
     │                                   │
     └─ RiskDetectionAgent.assess_risk(  └─ RiskDetectionAgent.assess_risk(
            invoice,                          invoice,
            vendor_id,                        vendor_id,
            matching_result                   matching_result
        )                                 )
     │                                   │
     ├─ Save RiskAssessment to DB        ├─ Update workflow state
     └─ Emit processing event            └─ Emit processing event
```

### Frontend Display

- **Invoice detail page** queries the latest `RiskAssessmentDB` row.
- `risk_level` is normalized to uppercase for the `RiskBadge` component.
- Each flag renders with severity badge, description, evidence, and
  suggested action.

---

## Configuration

Weights are defined as module-level constants in `risk_detection_agent.py`:

```python
WEIGHT_DUPLICATE = 0.25
WEIGHT_VENDOR    = 0.20
WEIGHT_PRICE     = 0.15
WEIGHT_AMOUNT    = 0.10
WEIGHT_MATCHING  = 0.20
WEIGHT_PATTERN   = 0.10
```

Detection thresholds are in each service:

| Parameter | Location | Default |
|-----------|----------|---------|
| Z-score threshold | `PriceAnomalyDetector.STANDARD_DEVIATIONS_THRESHOLD` | 2.0 |
| Min historical invoices | `PriceAnomalyDetector.MIN_HISTORICAL_INVOICES` | 3 |
| Significant amount | `PriceAnomalyDetector.SIGNIFICANT_AMOUNT_THRESHOLD` | $1,000 |
| Vendor flag threshold | `RiskDetectionAgent._assess_vendor_risk` | score ≥ 0.40 |
| Amount flag threshold | `RiskDetectionAgent._assess_amount_risk` | score ≥ 0.30 |

---

## Version History

| Version | Changes |
|---------|---------|
| 1.0 | Initial 5-component scoring (duplicate, vendor, price, amount, pattern) |
| 2.0 | Added PO matching risk component (20%); vendor name fallback lookup; price anomaly self-exclusion fix; tightened round-number thresholds; enriched flag evidence fields; rebalanced weights |
