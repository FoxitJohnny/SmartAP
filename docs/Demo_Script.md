# SmartAP Demo Script

> **Duration:** 25-30 minutes  
> **Audience:** Stakeholders, potential customers, executive leadership  
> **Prerequisites:** Backend running on port 8000, Frontend on port 3000, seed data loaded

---

## Pre-Demo Checklist

- [ ] Backend server running: `http://localhost:8000`
- [ ] Frontend running: `http://localhost:3000`
- [ ] Database seeded with vendors, POs, and demo users (auto-seeds on first start in debug mode)
- [ ] Demo files ready in `backend/sample-data/invoices/`
- [ ] Browser zoom at 100%, clear browser cache
- [ ] Close unnecessary applications/notifications

---

## Demo User Accounts

Demo users are auto-created on first login. Use these credentials:

| Role | Email | Password | Purpose |
|------|-------|----------|---------|
| **Admin** | `admin@smartap.dev` | `Admin1234!` | Full access: user management, settings, all features |
| **Finance Manager** | `finance@smartap.dev` | `Finance1234!` | Approvals, risk review, invoice management |
| **Accountant** | `accountant@smartap.dev` | `Account1234!` | Invoice processing, matching, day-to-day operations |
| **Viewer** | `viewer@smartap.dev` | `Viewer1234!` | Read-only access: dashboards and reports |

> **Tip:** Start the demo logged in as **Admin** to show all features including User Management and Settings. Then log out and log in as **Finance Manager** to show the approval workflow from a different perspective.

---

## Demo Files Location

All sample files for the demo are in:
- **Clean invoices:** `backend/sample-data/invoices/clean/`
- **Edge cases:** `backend/sample-data/invoices/edge-cases/`

### Files to Use in Demo

| Scenario | File | Purpose |
|----------|------|---------|
| Happy Path | `clean/clean_01_NO-2026-9469.pdf` | Standard invoice, shows AI extraction |
| Multi-page | `edge-cases/multipage_01_INV-2026-4808.pdf` | Complex invoice with multiple pages |
| Missing PO | `edge-cases/missing_po_01_INV-2026-7388.pdf` | Invoice without matching PO |
| Price Spike | `edge-cases/price_spike_01_BILL-2024-8162.pdf` | Anomalous pricing for fraud detection |
| Duplicate | `edge-cases/duplicate_01.pdf` | Duplicate invoice detection |

---

## Demo Flow

### Opening (1 minute)

**Script:**
> "Today I'll demonstrate SmartAP, our AI-powered accounts payable automation platform. SmartAP transforms manual invoice processing into an intelligent, streamlined workflow—reducing processing time by up to 80% while catching fraud before it reaches payment."

---

## Scene 1: Login & Dashboard Overview (2 minutes)

### Actions:
1. Open browser to `http://localhost:3000`
2. Login with Admin credentials: `admin@smartap.dev` / `Admin1234!`
3. Dashboard loads automatically after login

### Points to Highlight:
- **Real-time metrics** at the top: Total invoices, pending approvals, approval rate
- **Processing STP rate** (Straight-Through Processing): Shows automation efficiency
- **Risk flags count**: Active fraud/risk warnings
- **Recent activity feed**: Live updates of system actions
- **Invoice volume chart**: Historical processing trends

**Script:**
> "The dashboard gives finance teams instant visibility into their AP operation. We can see X invoices processed this month, with Y pending approval and a Z% straight-through processing rate—meaning most invoices require no manual intervention."

---

## Scene 2: Invoice Upload & AI Extraction (4 minutes)

### Demo 2A: Standard Invoice Upload

**Actions:**
1. Click **"Upload Invoice"** button (top right) or navigate to `/invoices/upload`
2. Drag and drop `clean/clean_01_NO-2026-9469.pdf`
3. Watch the AI extraction progress indicator
4. Review the extracted data

### Points to Highlight:
- **Drag-and-drop interface**: Easy file upload
- **Multi-format support**: PDF, TIFF, PNG, JPEG
- **Real-time extraction**: AI processes as you watch
- **Confidence scores**: Each field shows extraction confidence (95%+)
- **Structured data**: Line items, totals, vendor info auto-populated

**Script:**
> "Let me upload an invoice from one of our vendors. Notice how the AI extracts all relevant data in seconds—vendor details, line items, totals—with confidence scores for each field. No manual data entry required."

### Demo 2B: Review Extracted Data

**Actions:**
1. Point out the extracted fields: Invoice #, Vendor, Date, Line Items
2. Show the original PDF side-by-side (split view)
3. Click on a field to see extraction confidence

**Script:**
> "The system shows the original document alongside extracted data. Finance teams can verify at a glance. Notice the 98% confidence on this vendor name extraction."

---

## Scene 3: 3-Way Matching (4 minutes)

### Demo 3A: Successful Match

**Actions:**
1. Click **"Review for Approval"** button
2. System displays matching results (matching runs automatically during extraction)
3. Review the match results showing:
   - ✅ Vendor match: 100%
   - ✅ Amount match: 100%
   - ✅ Line items match: 100%
4. Show the detailed comparison table

**Script:**
> "SmartAP automatically performs 3-way matching—comparing the invoice against the purchase order and receiving records. This invoice matches perfectly: vendor confirmed, amounts verified, all line items accounted for."

### Demo 3B: Price Spike Scenario

**Actions:**
1. Go back to Invoices list
2. Upload `edge-cases/price_spike_01_BILL-2024-8162.pdf`
3. Run matching
4. Show the anomaly detected:
   - ⚠️ Price anomaly: Unusual pricing pattern
   - System flags for review

**Script:**
> "Not all invoices match perfectly. Here's one with anomalous pricing. SmartAP catches this discrepancy and flags it for review—preventing overpayment before it happens."

### Points to Highlight:
- **Configurable tolerances**: Admins set acceptable variance thresholds (show Settings later)
- **Line-by-line comparison**: Detailed breakdown of discrepancies
- **Automatic routing**: Mismatches route to appropriate approver

---

## Scene 4: Risk Assessment & Fraud Detection (4 minutes)

### Demo 4A: Risk Column in Invoice List

**Actions:**
1. Navigate to **Invoices** page (`/invoices`)
2. Point out the **Risk** column — shows risk flag counts for each invoice
3. Click an invoice with risk flags to see full risk assessment details

**Script:**
> "Every invoice in the list shows its risk status at a glance. Invoices with warnings show the number of risk flags detected. Click through to see the full risk breakdown."

### Demo 4B: Duplicate Invoice Detection

**Actions:**
1. Upload `edge-cases/duplicate_01.pdf`
2. Then upload `edge-cases/duplicate_02.pdf` (same invoice, different file)
3. Watch the fraud detection alert appear
4. Show the risk assessment panel:
   - 🔴 DUPLICATE DETECTED
   - Risk Score: HIGH
   - Evidence: Matching invoice number

**Script:**
> "Here's where SmartAP really protects your bottom line. I'm uploading what appears to be a new invoice, but watch what happens... The system immediately detects this is a duplicate—same invoice number was already submitted. This prevents a double payment."

### Demo 4C: Missing PO Alert

**Actions:**
1. Upload `edge-cases/missing_po_01_INV-2026-7388.pdf`
2. Show the alert:
   - ⚠️ No matching PO found
   - Requires manual review

**Script:**
> "SmartAP also catches invoices without a purchase order. This invoice has no matching PO in our system. It gets flagged for investigation—preventing unauthorized spending."

### Points to Highlight:
- **Multi-layer detection**: Duplicates, vendor risk, price anomalies, pattern analysis
- **Real-time alerts**: Issues caught at upload, not during payment
- **Risk scoring**: 0-100 scale with LOW/MEDIUM/HIGH/CRITICAL levels
- **Audit trail**: All detections logged for compliance

---

## Scene 5: Approval Workflows (4 minutes)

### Demo 5A: Standard Approval

**Actions:**
1. Navigate to **Approvals** page (`/approvals`)
2. Show the approval queue with pending invoices
3. Click on an invoice requiring approval
4. Review invoice details, matching results, and risk assessment
5. Click **"Approve"** button
6. Show status change and audit log entry

**Script:**
> "For invoices requiring human review, we have a streamlined approval workflow. Approvers see all relevant information in one view—the invoice, PO match results, and risk assessment. One click to approve or reject."

### Demo 5B: Bulk Approval

**Actions:**
1. Select multiple invoices using checkboxes
2. Click **"Bulk Approve"**
3. Confirm the action
4. Show all selected invoices approved simultaneously

**Script:**
> "For efficiency, approvers can process multiple invoices at once. Select the invoices you've reviewed, click bulk approve, and they're all processed in one action."

---

## Scene 6: Vendor Management (2 minutes)

**Actions:**
1. Navigate to **Vendors** page (`/vendors`)
2. Show vendor list with status indicators (Active, Suspended, etc.)
3. Click on "Acme Office Supplies Inc." (V001)
4. Show vendor detail page:
   - Contact information
   - Risk profile
   - Payment history

**Script:**
> "SmartAP maintains a complete vendor master. Each vendor has a risk profile built from payment history and fraud detection results. Here's Acme Office Supplies—a trusted vendor with 245 invoices processed and zero fraud flags."

### Points to Highlight:
- **Vendor risk scores**: Calculated automatically from history
- **Status management**: Active, Inactive, Suspended, Blocked
- **Compliance ready**: Tax IDs, banking details, audit history

---

## Scene 7: Purchase Orders (2 minutes)

**Actions:**
1. Navigate to **Purchase Orders** (`/purchase-orders`)
2. Show PO list with status filters (Open, Partially Received, Closed)
3. Click on PO-2025-002 (TechGear Solutions)
4. Show PO detail:
   - Line items
   - Received quantities
   - Linked invoices

**Script:**
> "The purchase order module tracks all POs from creation through fulfillment. This PO from TechGear shows 5 laptops ordered, and we can see linked invoices that were matched and approved."

---

## Scene 8: Analytics & Reporting (2 minutes)

**Actions:**
1. Navigate to **Analytics** page (`/analytics`)
2. Show key visualizations:
   - Invoice volume over time
   - Processing time trends
   - Status distribution (pie chart)
   - STP rate

**Script:**
> "The analytics dashboard helps you measure and improve your AP operation. We can see invoice volumes, processing trends, and the STP rate—showing what percentage of invoices flow through automatically."

### Points to Highlight:
- **ROI tracking**: See efficiency gains over time
- **Bottleneck identification**: Find where invoices get stuck
- **Compliance reporting**: Audit-ready data exports

---

## Scene 9: Settings & Configuration (3 minutes)

### Demo 9A: Matching Settings

**Actions:**
1. Navigate to **Settings > Matching** (`/settings/matching`)
2. Show configurable parameters:
   - Price tolerance threshold
   - Quantity tolerance threshold
   - Auto-approve settings

**Script:**
> "Administrators can fine-tune the system to match your business rules. Here you can set tolerance thresholds—maybe you allow 2% price variance before flagging. These settings control how aggressive the automation is."

### Demo 9B: Risk Detection Settings

**Actions:**
1. Navigate to **Settings > Risk** (`/settings/risk`)
2. Show the configurable risk detection parameters:
   - **Component Weights**: Adjust how much each risk detector contributes to the overall score (Price Anomaly, Duplicate Detection, Vendor Risk)
   - **Price Anomaly Thresholds**: Z-score threshold, small sample fallback percentage, minimum history count
   - **Duplicate Detection**: Similarity threshold, time window for duplicate checks
   - **Vendor Risk**: New vendor threshold (days), payment reliability weight, fraud history weight
3. Adjust a threshold and click **Save**
4. Show **Reset to Defaults** button for quick recovery

**Script:**
> "New in this release: configurable risk detection settings. You can fine-tune how sensitive each risk detector is. For example, if you're seeing too many false positives on price anomalies, raise the z-score threshold. Each organization can calibrate risk detection to their tolerance level."

---

## Scene 10: User Management (2 minutes)

**Actions:**
1. Navigate to **Users** (`/admin/users`) from the sidebar
2. Show the user list with columns: Name, Email, Role, Department, Status, Last Login
3. Click **Edit Role** on a user to change their role via dropdown
4. Show the **Activate/Deactivate** toggle for user accounts
5. Point out that the current (admin) user cannot deactivate themselves

**Script:**
> "Administrators can manage user accounts directly from the UI. Each user has a role—Admin, Finance Manager, Accountant, or Viewer—that controls what they can access. You can edit roles, deactivate accounts, and see login activity at a glance."

### Demo 10B: Multi-User Role Demo

**Actions:**
1. Click your profile avatar (top right) > **Log out**
2. Login as Finance Manager: `finance@smartap.dev` / `Finance1234!`
3. Show that the Users page shows "Access Denied" for non-admin roles
4. Navigate through the app to show Finance Manager's view
5. Log out again and log back in as Admin

**Script:**
> "Let me show how role-based access works. I'll log out and sign in as a Finance Manager. Notice they can see invoices, approvals, and vendors—but the Users management page is restricted to admins only. This is role-based access control in action."

---

## Closing (1 minute)

**Script:**
> "That's SmartAP—AI-powered invoice processing with intelligent matching, real-time fraud detection, configurable risk thresholds, role-based access control, and streamlined approval workflows. Questions?"

---

## Q&A Talking Points

### "How does the AI extraction work?"
> "We use a combination of OCR and machine learning models trained on thousands of invoice formats. The system learns from corrections, improving over time."

### "What's the integration story?"
> "SmartAP integrates with major ERPs—NetSuite, SAP, QuickBooks, Xero, Oracle, and Dynamics 365. We support bidirectional sync for vendors, POs, and payment status."

### "What about security and compliance?"
> "All data is encrypted at rest and in transit. We maintain full audit trails for SOX compliance. Role-based access controls who sees what—and admins can manage users and roles directly from the UI."

### "How long does implementation take?"
> "Typical implementation is 4-6 weeks including ERP integration, approval workflow configuration, and user training."

### "What's the ROI?"
> "Customers typically see 80% reduction in invoice processing time, 95%+ accuracy on data extraction, and significant reduction in duplicate payments and fraud."

### "Can we configure the risk detection sensitivity?"
> "Absolutely. The Risk Settings page lets admins adjust thresholds for price anomaly detection, duplicate detection, and vendor risk analysis. Each parameter can be fine-tuned to your organization's risk tolerance, and you can always reset to defaults."

---

## Troubleshooting During Demo

| Issue | Solution |
|-------|----------|
| Invoice upload slow | Check backend logs, may be processing queue |
| Matching fails | Verify PO seed data is loaded |
| No risk alerts | Use edge-case files (duplicate, price_spike) |
| UI not loading | Clear cache, check frontend console |
| Login fails | Demo users are auto-created on first login attempt. Check backend is running. |
| Can't log out | Clear browser localStorage and refresh |

---

## Demo Reset

To reset the demo environment:

```bash
# Stop servers
Ctrl+C in both terminals

# Delete database to force re-seed
cd backend
del smartap.db   # Windows
# rm smartap.db  # Mac/Linux

# Restart backend (auto-seeds in debug mode)
python -m uvicorn src.main:app --reload --port 8000

# Restart frontend
cd ../frontend && npm run dev
```
