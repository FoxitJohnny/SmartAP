"""
Seed-Aligned Invoice Generator for SmartAP

Generates sample invoices whose PO references, vendor names, and line items
match the deterministic seed data in ``src/db/seed_data.py``, so that
3-way matching works correctly during demonstrations.

Output
------
- 20 clean invoices  (``clean/``)
- 15 messy invoices  (``messy/``)   – same layout, marked poor-quality
- 15 edge-case invoices (``edge-cases/``)
    * 5 multi-page
    * 3 duplicates
    * 3 price spikes
    * 4 missing PO

Usage
-----
    cd backend
    python scripts/generate_sample_data.py
"""

import copy
import json
import os
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Deterministic seed for reproducibility
random.seed(42)

# ── Paths ─────────────────────────────────────────────────────────
OUTPUT_DIR = Path("sample-data/invoices")
CLEAN_DIR = OUTPUT_DIR / "clean"
MESSY_DIR = OUTPUT_DIR / "messy"
EDGE_DIR = OUTPUT_DIR / "edge-cases"

# ── Buyer (our organisation receiving the invoices) ───────────────
OUR_COMPANY = {
    "name": "Contoso Ltd",
    "address": "100 Corporate Blvd, Suite 500, Dallas, TX 75201",
    "tax_id": "11-2345678",
}

# ── Vendors (mirror of SEED_VENDORS in src/db/seed_data.py) ──────
VENDORS = {
    "V001": {
        "name": "Acme Office Supplies Inc.",
        "address": "123 Business Blvd, New York, NY 10001",
        "tax_id": "12-3456789",
    },
    "V002": {
        "name": "TechGear Solutions",
        "address": "456 Tech Park Dr, San Francisco, CA 94102",
        "tax_id": "98-7654321",
    },
    "V003": {
        "name": "QuickPrint Services",
        "address": "789 Print Lane, Chicago, IL 60601",
        "tax_id": "45-1234567",
    },
    "V004": {
        "name": "Global Logistics LLC",
        "address": "321 Shipping Way, Houston, TX 77001",
        "tax_id": "67-8901234",
    },
    "V006": {
        "name": "Premium IT Services",
        "address": "987 Silicon Ave, Austin, TX 73301",
        "tax_id": "89-0123456",
    },
    "V007": {
        "name": "Metro Facility Services",
        "address": "147 Maintenance Rd, Boston, MA 02101",
        "tax_id": "34-5678901",
    },
    "V008": {
        "name": "FastShip Express",
        "address": "258 Express Way, Miami, FL 33101",
        "tax_id": "56-7890123",
    },
    "V010": {
        "name": "Enterprise Solutions Group",
        "address": "741 Corporate Plaza, Atlanta, GA 30301",
        "tax_id": "90-1234567",
    },
}

# ── PO data (mirror of SEED_PURCHASE_ORDERS in src/db/seed_data.py)
SEED_POS = {
    "PO-2025-001": {
        "vendor_id": "V001",
        "status": "open",
        "items": [
            {"desc": "Printer Paper - 10 reams", "sku": "PP-100", "qty": 10, "price": 45.00},
            {"desc": "Stapler Set", "sku": "ST-250", "qty": 20, "price": 15.00},
            {"desc": "File Folders - Box of 100", "sku": "FF-300", "qty": 50, "price": 12.00},
            {"desc": "Ballpoint Pens - Pack of 12", "sku": "BP-400", "qty": 100, "price": 8.00},
            {"desc": "Desk Organizers", "sku": "DO-500", "qty": 50, "price": 25.00},
            {"desc": "Whiteboard Markers - 4-Pack", "sku": "WM-600", "qty": 50, "price": 22.00},
        ],
    },
    "PO-2025-002": {
        "vendor_id": "V002",
        "status": "open",
        "items": [
            {"desc": "Laptop Computer - Dell XPS 15", "sku": "LAP-XPS15", "qty": 5, "price": 1500.00},
            {"desc": "USB-C Docking Station", "sku": "DOCK-USBC", "qty": 5, "price": 250.00},
            {"desc": "27-inch Monitor", "sku": "MON-27", "qty": 10, "price": 325.00},
        ],
    },
    "PO-2025-003": {
        "vendor_id": "V003",
        "status": "open",
        "items": [
            {"desc": "Business Cards - 1000 qty", "sku": "BC-1000", "qty": 10, "price": 50.00},
            {"desc": "Brochures - Full Color", "sku": "BR-COLOR", "qty": 5, "price": 140.00},
        ],
    },
    "PO-2025-004": {
        "vendor_id": "V004",
        "status": "open",
        "items": [
            {"desc": "Freight Shipping - West Coast", "sku": "FREIGHT-WC", "qty": 1, "price": 8000.00},
            {"desc": "Freight Shipping - East Coast", "sku": "FREIGHT-EC", "qty": 1, "price": 10000.00},
        ],
    },
    "PO-2025-005": {
        "vendor_id": "V006",
        "status": "partially_received",
        "items": [
            {"desc": "Software License - Annual", "sku": "SW-LIC-ANNUAL", "qty": 20, "price": 300.00, "received": 10},
            {"desc": "Technical Support - 100 hours", "sku": "TECH-SUPP-100", "qty": 1, "price": 2000.00, "received": 0},
        ],
    },
    "PO-2025-006": {
        "vendor_id": "V001",
        "status": "partially_received",
        "items": [
            {"desc": "Office Chairs - Ergonomic", "sku": "CHAIR-ERG", "qty": 10, "price": 250.00, "received": 6},
        ],
    },
    "PO-2025-007": {
        "vendor_id": "V003",
        "status": "closed",
        "items": [
            {"desc": "Marketing Flyers - 5000 qty", "sku": "FLYER-5K", "qty": 5, "price": 170.00},
        ],
    },
    "PO-2025-008": {
        "vendor_id": "V007",
        "status": "closed",
        "items": [
            {"desc": "Monthly Facility Maintenance", "sku": "FAC-MAINT-MONTH", "qty": 1, "price": 2000.00},
            {"desc": "HVAC Service", "sku": "HVAC-SERVICE", "qty": 1, "price": 1500.00},
        ],
    },
    "PO-2024-099": {
        "vendor_id": "V002",
        "status": "closed",
        "items": [
            {"desc": "Desktop Computers - 5 units", "sku": "DESK-PC", "qty": 5, "price": 1000.00},
        ],
    },
    "PO-2025-009": {
        "vendor_id": "V001",
        "status": "open",
        "items": [
            {"desc": "Toner Cartridges", "sku": "TONER-HP", "qty": 10, "price": 85.00},
        ],
    },
    "PO-2025-010": {
        "vendor_id": "V008",
        "status": "open",
        "items": [
            {"desc": "Express Shipping - 3 packages", "sku": "SHIP-EXP", "qty": 3, "price": 250.00},
        ],
    },
}

TAX_RATE = 0.08  # 8 % US sales tax


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────


def _po_line_items(po_number, *, indices=None, price_mult=1.0, qty_override=None):
    """Build invoice line-items from a PO.

    indices      – if given, only include these 0-based item indexes
    price_mult   – multiply every unit price by this factor
    qty_override – dict  {item_index: new_quantity}
    """
    po = SEED_POS[po_number]
    if indices is not None:
        source = [(i, po["items"][i]) for i in indices]
    else:
        source = list(enumerate(po["items"]))

    result = []
    for idx, it in source:
        qty = qty_override.get(idx, it["qty"]) if qty_override else it["qty"]
        price = round(it["price"] * price_mult, 2)
        result.append(
            {
                "description": it["desc"],
                "sku": it["sku"],
                "quantity": qty,
                "unit_price": price,
                "total": round(qty * price, 2),
            }
        )
    return result


def _make_items(defs):
    """Turn simple dicts into invoice-style line-items."""
    return [
        {
            "description": d["desc"],
            "sku": d.get("sku", "MISC"),
            "quantity": d["qty"],
            "unit_price": d["price"],
            "total": round(d["qty"] * d["price"], 2),
        }
        for d in defs
    ]


# ────────────────────────────────────────────────────────────────────
# 20 clean-invoice scenario definitions
# ────────────────────────────────────────────────────────────────────

CLEAN_SCENARIOS = [
    # ── 1–6  Exact matches against OPEN POs ────────────────────────
    {
        "idx": 1,
        "inv": "INV-2025-1001",
        "po": "PO-2025-001",
        "tag": "exact_match",
        "days_ago": 10,
        "note": "Happy-path demo invoice — matches PO-2025-001 exactly",
    },
    {
        "idx": 2,
        "inv": "INV-2025-1002",
        "po": "PO-2025-002",
        "tag": "exact_match",
        "days_ago": 8,
        "note": "IT equipment — matches PO-2025-002 exactly",
    },
    {
        "idx": 3,
        "inv": "INV-2025-1003",
        "po": "PO-2025-003",
        "tag": "exact_match",
        "days_ago": 3,
        "note": "Printing services — matches PO-2025-003 exactly",
    },
    {
        "idx": 4,
        "inv": "INV-2025-1004",
        "po": "PO-2025-004",
        "tag": "exact_match",
        "days_ago": 25,
        "note": "Freight shipping — matches PO-2025-004 exactly",
    },
    {
        "idx": 5,
        "inv": "INV-2025-1005",
        "po": "PO-2025-009",
        "tag": "exact_match",
        "days_ago": 2,
        "note": "Toner cartridges — matches PO-2025-009 exactly",
    },
    {
        "idx": 6,
        "inv": "INV-2025-1006",
        "po": "PO-2025-010",
        "tag": "exact_match",
        "days_ago": 1,
        "note": "Express shipping — matches PO-2025-010 exactly",
    },
    # ── 7–8  Partial deliveries ────────────────────────────────────
    {
        "idx": 7,
        "inv": "INV-2025-1007",
        "po": "PO-2025-005",
        "tag": "partial_delivery",
        "days_ago": 15,
        "custom_items": [
            {"desc": "Software License - Annual", "sku": "SW-LIC-ANNUAL", "qty": 10, "price": 300.00},
        ],
        "note": "First partial — 10 of 20 licences delivered",
    },
    {
        "idx": 8,
        "inv": "INV-2025-1008",
        "po": "PO-2025-006",
        "tag": "partial_delivery",
        "days_ago": 18,
        "custom_items": [
            {"desc": "Office Chairs - Ergonomic", "sku": "CHAIR-ERG", "qty": 4, "price": 250.00},
        ],
        "note": "Remaining 4 of 10 chairs (6 already received)",
    },
    # ── 9–12  Discrepancy invoices ─────────────────────────────────
    {
        "idx": 9,
        "inv": "INV-2025-1009",
        "po": "PO-2025-001",
        "tag": "price_variance",
        "days_ago": 12,
        "price_mult": 1.05,
        "note": "All unit prices 5% above PO — should flag price variance",
    },
    {
        "idx": 10,
        "inv": "INV-2025-1010",
        "po": "PO-2025-002",
        "tag": "quantity_mismatch",
        "days_ago": 7,
        "qty_override": {2: 12},  # 12 monitors instead of 10
        "note": "12 monitors invoiced vs 10 on PO — over-delivery",
    },
    {
        "idx": 11,
        "inv": "INV-2025-1011",
        "po": "PO-2025-004",
        "tag": "overbilled",
        "days_ago": 22,
        "price_mult": 1.10,
        "note": "All amounts 10% above PO — overbilling",
    },
    {
        "idx": 12,
        "inv": "INV-2025-1012",
        "po": "PO-2025-005",
        "tag": "partial_remaining",
        "days_ago": 5,
        "custom_items": [
            {"desc": "Software License - Annual", "sku": "SW-LIC-ANNUAL", "qty": 10, "price": 300.00},
            {"desc": "Technical Support - 100 hours", "sku": "TECH-SUPP-100", "qty": 1, "price": 2000.00},
        ],
        "note": "Second partial — remaining 10 licences + tech support",
    },
    # ── 13–15  Missing PO number ───────────────────────────────────
    {
        "idx": 13,
        "inv": "INV-2025-1013",
        "po": None,
        "vendor_id": "V001",
        "tag": "missing_po",
        "days_ago": 14,
        "custom_items": [
            {"desc": "Copy Paper - Letter Size", "sku": "CP-LTR", "qty": 25, "price": 38.00},
            {"desc": "Sticky Notes - 12 Pack", "sku": "SN-12", "qty": 30, "price": 6.50},
        ],
        "note": "No PO reference — manual review required",
    },
    {
        "idx": 14,
        "inv": "INV-2025-1014",
        "po": None,
        "vendor_id": "V007",
        "tag": "missing_po",
        "days_ago": 20,
        "custom_items": [
            {"desc": "Building Cleaning Service", "sku": "CLEAN-01", "qty": 1, "price": 1800.00},
            {"desc": "Pest Control - Quarterly", "sku": "PEST-Q", "qty": 1, "price": 450.00},
        ],
        "note": "Service invoice, no PO reference",
    },
    {
        "idx": 15,
        "inv": "INV-2025-1015",
        "po": None,
        "vendor_id": "V010",
        "tag": "missing_po",
        "days_ago": 17,
        "custom_items": [
            {"desc": "Strategic Consulting - 40 hrs", "sku": "CON-40", "qty": 40, "price": 250.00},
            {"desc": "Project Setup Fee", "sku": "SETUP-01", "qty": 1, "price": 2500.00},
        ],
        "note": "Enterprise consulting, no PO reference",
    },
    # ── 16–18  Against CLOSED POs ──────────────────────────────────
    {
        "idx": 16,
        "inv": "INV-2025-1016",
        "po": "PO-2025-007",
        "tag": "closed_po",
        "days_ago": 30,
        "note": "Invoice against CLOSED PO — should flag",
    },
    {
        "idx": 17,
        "inv": "INV-2025-1017",
        "po": "PO-2025-008",
        "tag": "closed_po",
        "days_ago": 28,
        "note": "Invoice against CLOSED PO — should flag",
    },
    {
        "idx": 18,
        "inv": "INV-2025-1018",
        "po": "PO-2024-099",
        "tag": "closed_po",
        "days_ago": 60,
        "note": "Invoice against CLOSED PO from prior year",
    },
    # ── 19–20  Other realistic variations ──────────────────────────
    {
        "idx": 19,
        "inv": "INV-2025-1019",
        "po": "PO-2025-001",
        "tag": "partial_shipment",
        "days_ago": 6,
        "indices": [0, 2, 4],  # Paper, Folders, Organizers only
        "note": "Partial shipment — 3 of 6 PO line items",
    },
    {
        "idx": 20,
        "inv": "INV-2025-1020",
        "po": "PO-2025-002",
        "tag": "discount_applied",
        "days_ago": 4,
        "price_mult": 0.95,
        "note": "Negotiated 5% discount on all items",
    },
]

# ── 15 messy-invoice scenarios (same data, different invoice #s) ──

MESSY_SCENARIOS = [
    {"idx": 1, "inv": "BILL-2025-3001", "po": "PO-2025-001", "tag": "exact_match", "days_ago": 35},
    {"idx": 2, "inv": "BILL-2025-3002", "po": "PO-2025-002", "tag": "exact_match", "days_ago": 32},
    {"idx": 3, "inv": "BILL-2025-3003", "po": "PO-2025-003", "tag": "exact_match", "days_ago": 29},
    {"idx": 4, "inv": "BILL-2025-3004", "po": "PO-2025-004", "tag": "exact_match", "days_ago": 40},
    {"idx": 5, "inv": "BILL-2025-3005", "po": "PO-2025-009", "tag": "exact_match", "days_ago": 26},
    {"idx": 6, "inv": "BILL-2025-3006", "po": "PO-2025-010", "tag": "exact_match", "days_ago": 24},
    {
        "idx": 7,
        "inv": "BILL-2025-3007",
        "po": "PO-2025-005",
        "tag": "partial_delivery",
        "days_ago": 21,
        "custom_items": [
            {"desc": "Software License - Annual", "sku": "SW-LIC-ANNUAL", "qty": 10, "price": 300.00},
        ],
    },
    {
        "idx": 8,
        "inv": "BILL-2025-3008",
        "po": "PO-2025-006",
        "tag": "partial_delivery",
        "days_ago": 33,
        "custom_items": [
            {"desc": "Office Chairs - Ergonomic", "sku": "CHAIR-ERG", "qty": 4, "price": 250.00},
        ],
    },
    {"idx": 9, "inv": "BILL-2025-3009", "po": "PO-2025-001", "tag": "price_variance", "price_mult": 1.05, "days_ago": 38},
    {"idx": 10, "inv": "BILL-2025-3010", "po": "PO-2025-002", "tag": "quantity_mismatch", "qty_override": {2: 12}, "days_ago": 27},
    {"idx": 11, "inv": "BILL-2025-3011", "po": "PO-2025-004", "tag": "overbilled", "price_mult": 1.10, "days_ago": 42},
    {"idx": 12, "inv": "BILL-2025-3012", "po": "PO-2025-007", "tag": "closed_po", "days_ago": 45},
    {"idx": 13, "inv": "BILL-2025-3013", "po": "PO-2025-008", "tag": "closed_po", "days_ago": 50},
    {
        "idx": 14,
        "inv": "BILL-2025-3014",
        "po": None,
        "vendor_id": "V001",
        "tag": "missing_po",
        "days_ago": 36,
        "custom_items": [
            {"desc": "Envelopes - Box of 500", "sku": "ENV-500", "qty": 10, "price": 22.00},
            {"desc": "Binder Clips - Assorted", "sku": "BC-ASST", "qty": 20, "price": 4.50},
        ],
    },
    {"idx": 15, "inv": "BILL-2025-3015", "po": "PO-2025-001", "tag": "partial_shipment", "indices": [1, 3, 5], "days_ago": 31},
]


# ────────────────────────────────────────────────────────────────────
# Data builder
# ────────────────────────────────────────────────────────────────────

INVOICE_HISTORY = []  # every generated invoice added here
CLEAN_INVOICES = []  # only clean invoices (for duplicate edge-cases)


def build_invoice_data(scenario):
    """Build a complete invoice-data dict from a scenario definition."""
    po_number = scenario.get("po")

    # Determine vendor
    if po_number:
        vendor_id = SEED_POS[po_number]["vendor_id"]
    else:
        vendor_id = scenario["vendor_id"]
    vendor = VENDORS[vendor_id]

    # Build line items
    if "custom_items" in scenario:
        items = _make_items(scenario["custom_items"])
    elif po_number:
        items = _po_line_items(
            po_number,
            indices=scenario.get("indices"),
            price_mult=scenario.get("price_mult", 1.0),
            qty_override=scenario.get("qty_override"),
        )
    else:
        items = []

    subtotal = round(sum(i["total"] for i in items), 2)
    tax_amount = round(subtotal * TAX_RATE, 2)
    shipping = scenario.get("shipping", 0)
    total = round(subtotal + tax_amount + shipping, 2)

    base_date = datetime.now() - timedelta(days=scenario.get("days_ago", 10))

    data = {
        "invoice_number": scenario["inv"],
        "po_number": po_number,
        "vendor": {
            "name": vendor["name"],
            "address": vendor["address"],
            "tax_id": vendor["tax_id"],
        },
        "customer": OUR_COMPANY.copy(),
        "invoice_date": base_date.strftime("%Y-%m-%d"),
        "due_date": (base_date + timedelta(days=30)).strftime("%Y-%m-%d"),
        "currency": "USD",
        "line_items": items,
        "subtotal": subtotal,
        "tax_rate": TAX_RATE,
        "tax_amount": tax_amount,
        "shipping": shipping,
        "total_amount": total,
        "payment_terms": "Net 30",
        "invoice_type": scenario.get("tag", "us_standard"),
    }
    if scenario.get("note"):
        data["notes"] = scenario["note"]

    INVOICE_HISTORY.append(data)
    return data


# ────────────────────────────────────────────────────────────────────
# PDF rendering
# ────────────────────────────────────────────────────────────────────


def render_invoice_pdf(data, output_path):
    """Render a single-page invoice PDF from an invoice-data dict."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    w, h = letter
    vendor = data["vendor"]
    customer = data["customer"]

    # Header band
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.rect(0, h - 1.2 * inch, w, 1.2 * inch, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, h - 0.8 * inch, vendor["name"])

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(1 * inch, h - 1.5 * inch, vendor["address"])
    c.drawString(1 * inch, h - 1.7 * inch, f"Tax ID: {vendor['tax_id']}")

    # Invoice title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(5 * inch, h - 1.5 * inch, "INVOICE")

    # Invoice details
    c.setFont("Helvetica", 10)
    c.drawString(5 * inch, h - 1.9 * inch, f"Invoice #: {data['invoice_number']}")
    c.drawString(5 * inch, h - 2.1 * inch, f"Date: {data['invoice_date']}")
    c.drawString(5 * inch, h - 2.3 * inch, f"Due Date: {data['due_date']}")

    if data["po_number"]:
        c.drawString(5 * inch, h - 2.5 * inch, f"PO Number: {data['po_number']}")

    # Bill To
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, h - 2.5 * inch, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, h - 2.7 * inch, customer["name"])
    c.drawString(1 * inch, h - 2.9 * inch, customer["address"])
    c.drawString(1 * inch, h - 3.1 * inch, f"Tax ID: {customer['tax_id']}")

    # Line-item table header
    y = h - 3.8 * inch
    c.setFillColor(colors.HexColor("#F3F4F6"))
    c.rect(0.9 * inch, y - 0.05 * inch, 6.7 * inch, 0.25 * inch, fill=True, stroke=False)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Description")
    c.drawString(4 * inch, y, "SKU")
    c.drawString(5 * inch, y, "Qty")
    c.drawString(5.7 * inch, y, "Unit Price")
    c.drawString(6.8 * inch, y, "Amount")

    y -= 0.3 * inch
    c.setFont("Helvetica", 10)

    for item in data["line_items"]:
        c.drawString(1 * inch, y, item["description"])
        c.drawString(4 * inch, y, item["sku"])
        c.drawString(5 * inch, y, str(item["quantity"]))
        c.drawString(5.7 * inch, y, f"${item['unit_price']:.2f}")
        c.drawString(6.8 * inch, y, f"${item['total']:.2f}")
        y -= 0.25 * inch

    # Totals
    y -= 0.3 * inch
    c.line(5.5 * inch, y, 7.5 * inch, y)
    y -= 0.3 * inch

    c.setFont("Helvetica", 10)
    c.drawRightString(6.5 * inch, y, "Subtotal:")
    c.drawRightString(7.4 * inch, y, f"${data['subtotal']:.2f}")
    y -= 0.25 * inch

    c.drawRightString(6.5 * inch, y, f"Tax ({data['tax_rate'] * 100:.0f}%):")
    c.drawRightString(7.4 * inch, y, f"${data['tax_amount']:.2f}")
    y -= 0.25 * inch

    if data["shipping"]:
        c.drawRightString(6.5 * inch, y, "Shipping:")
        c.drawRightString(7.4 * inch, y, f"${data['shipping']:.2f}")
        y -= 0.25 * inch

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.drawRightString(6.5 * inch, y, "Total:")
    c.drawRightString(7.4 * inch, y, f"${data['total_amount']:.2f}")
    c.setFillColor(colors.black)

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    yf = 1.2 * inch
    c.drawString(1 * inch, yf, f"Payment Terms: {data['payment_terms']}")
    c.drawString(1 * inch, yf - 0.15 * inch, f"Please make checks payable to {vendor['name']}")
    c.drawString(
        1 * inch,
        yf - 0.30 * inch,
        f"Bank: First National Bank | Account: ****{random.randint(1000, 9999)}",
    )
    if data["po_number"]:
        c.drawString(1 * inch, yf - 0.45 * inch, f"Reference PO: {data['po_number']}")

    c.save()


def render_multipage_pdf(data, output_path):
    """Render a multi-page invoice with many line items."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    w, h = letter
    vendor = data["vendor"]
    customer = data["customer"]

    # Page 1 header
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.rect(0, h - 1.2 * inch, w, 1.2 * inch, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, h - 0.8 * inch, vendor["name"])

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(1 * inch, h - 1.5 * inch, vendor["address"])
    c.setFont("Helvetica-Bold", 20)
    c.drawString(5 * inch, h - 1.5 * inch, "INVOICE")

    c.setFont("Helvetica", 10)
    c.drawString(5 * inch, h - 1.9 * inch, f"Invoice #: {data['invoice_number']}")
    c.drawString(5 * inch, h - 2.1 * inch, f"Date: {data['invoice_date']}")
    if data["po_number"]:
        c.drawString(5 * inch, h - 2.3 * inch, f"PO Number: {data['po_number']}")
    c.drawString(1 * inch, h - 2.5 * inch, f"Bill To: {customer['name']}")
    c.drawString(1 * inch, h - 2.7 * inch, customer["address"])

    y = h - 3.5 * inch
    page_num = 1

    for i, item in enumerate(data["line_items"]):
        if y < 2 * inch:
            c.setFont("Helvetica", 8)
            c.drawString(w - 2 * inch, 0.5 * inch, f"Page {page_num}")
            c.showPage()
            page_num += 1
            y = h - 1 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(w / 2 - 1 * inch, y, f"Invoice {data['invoice_number']} (continued)")
            y -= 0.5 * inch

        c.setFont("Helvetica", 9)
        c.drawString(1 * inch, y, f"{i + 1}. {item['description']}")
        c.drawString(5 * inch, y, f"x{item['quantity']}")
        c.drawString(6 * inch, y, f"${item['total']:.2f}")
        y -= 0.2 * inch

    # Totals on last page
    y -= 0.5 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(5 * inch, y, "Subtotal:")
    c.drawString(6.5 * inch, y, f"${data['subtotal']:.2f}")
    y -= 0.25 * inch
    c.drawString(5 * inch, y, f"Tax ({data['tax_rate'] * 100:.0f}%):")
    c.drawString(6.5 * inch, y, f"${data['tax_amount']:.2f}")
    y -= 0.25 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5 * inch, y, "Total:")
    c.drawString(6.5 * inch, y, f"${data['total_amount']:.2f}")

    c.setFont("Helvetica", 8)
    c.drawString(w - 2 * inch, 0.5 * inch, f"Page {page_num} of {page_num}")
    c.save()

    data["page_count"] = page_num


def render_missing_po_pdf(data, output_path):
    """Render a bare-bones invoice with no PO reference."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    w, h = letter
    vendor = data["vendor"]
    customer = data["customer"]

    c.setFont("Helvetica-Bold", 20)
    c.drawString(1 * inch, h - 1 * inch, "INVOICE")

    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, h - 1.5 * inch, f"Invoice #: {data['invoice_number']}")
    c.drawString(1 * inch, h - 1.7 * inch, f"Date: {data['invoice_date']}")
    c.drawString(1 * inch, h - 2.2 * inch, f"From: {vendor['name']}")
    c.drawString(1 * inch, h - 2.4 * inch, f"To: {customer['name']}")

    y = h - 3 * inch
    for item in data["line_items"]:
        c.drawString(1 * inch, y, item["description"])
        c.drawString(5 * inch, y, f"x{item['quantity']}")
        c.drawString(6 * inch, y, f"${item['total']:.2f}")
        y -= 0.25 * inch

    y -= 0.5 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5 * inch, y, "Total:")
    c.drawString(6 * inch, y, f"${data['total_amount']:.2f}")
    c.save()


def save_ground_truth(data, pdf_path):
    """Save the ground-truth JSON beside the PDF."""
    json_path = pdf_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
    return json_path


# ────────────────────────────────────────────────────────────────────
# Generation orchestration
# ────────────────────────────────────────────────────────────────────


def clean_output_dirs():
    """Remove old generated files and recreate directories."""
    for d in [CLEAN_DIR, MESSY_DIR, EDGE_DIR]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)


def generate_clean():
    """Generate 20 seed-aligned clean invoices."""
    print("📄 Generating 20 clean invoices …")
    for sc in CLEAN_SCENARIOS:
        data = build_invoice_data(sc)
        CLEAN_INVOICES.append(data)
        filename = f"clean_{sc['idx']:02d}_{sc['inv']}.pdf"
        path = CLEAN_DIR / filename
        render_invoice_pdf(data, path)
        save_ground_truth(data, path)
        print(f"  ✅ {filename}  PO={data['po_number'] or '—'}  ${data['total_amount']:,.2f}")


def generate_messy():
    """Generate 15 seed-aligned messy invoices."""
    print("\n📄 Generating 15 messy invoices …")
    for sc in MESSY_SCENARIOS:
        data = build_invoice_data(sc)
        data["quality"] = "messy"
        data["notes"] = (data.get("notes", "") + " | Simulated poor-quality scan").strip(" |")
        filename = f"messy_{sc['idx']:02d}_{sc['inv']}.pdf"
        path = MESSY_DIR / filename
        render_invoice_pdf(data, path)
        save_ground_truth(data, path)
        print(f"  ✅ {filename}")


def generate_edge_cases():
    """Generate 15 edge-case invoices."""
    print("\n📄 Generating 15 edge-case invoices …")

    #  ── 5 multi-page invoices ────────────────────────────────────
    multipage_pos = ["PO-2025-001", "PO-2025-002", "PO-2025-004", "PO-2025-005", "PO-2025-001"]
    for i, po_num in enumerate(multipage_pos, start=1):
        inv_num = f"INV-2025-{2000 + i}"
        po = SEED_POS[po_num]
        vid = po["vendor_id"]
        vendor = VENDORS[vid]

        # Repeat PO items to create 25-40 line items
        base_items = _po_line_items(po_num)
        items = []
        target = random.randint(25, 40)
        while len(items) < target:
            for it in base_items:
                items.append(
                    {
                        "description": it["description"],
                        "sku": it["sku"],
                        "quantity": random.randint(1, 20),
                        "unit_price": it["unit_price"],
                        "total": 0,
                    }
                )
                if len(items) >= target:
                    break
        for it in items:
            it["total"] = round(it["quantity"] * it["unit_price"], 2)

        subtotal = round(sum(it["total"] for it in items), 2)
        tax = round(subtotal * TAX_RATE, 2)
        base_date = datetime.now() - timedelta(days=10 + i * 5)

        data = {
            "invoice_number": inv_num,
            "po_number": po_num,
            "vendor": {"name": vendor["name"], "address": vendor["address"], "tax_id": vendor["tax_id"]},
            "customer": OUR_COMPANY.copy(),
            "invoice_date": base_date.strftime("%Y-%m-%d"),
            "due_date": (base_date + timedelta(days=30)).strftime("%Y-%m-%d"),
            "currency": "USD",
            "line_items": items,
            "subtotal": subtotal,
            "tax_rate": TAX_RATE,
            "tax_amount": tax,
            "shipping": 0,
            "total_amount": round(subtotal + tax, 2),
            "payment_terms": "Net 30",
            "invoice_type": "multi-page",
        }

        filename = f"multipage_{i:02d}_{inv_num}.pdf"
        path = EDGE_DIR / filename
        render_multipage_pdf(data, path)
        save_ground_truth(data, path)
        INVOICE_HISTORY.append(data)
        print(f"  ✅ {filename}  ({data.get('page_count', '?')} pages, {len(items)} items)")

    # ── 3 duplicate invoices (copies of clean_01, clean_02, clean_03) ─
    for i, src_idx in enumerate([0, 1, 2], start=1):
        original = CLEAN_INVOICES[src_idx]
        inv_num = f"INV-2025-{2100 + i}"
        dup = json.loads(json.dumps(original))  # deep copy
        dup["invoice_number"] = inv_num
        dup["invoice_type"] = "duplicate"
        dup["original_invoice"] = original["invoice_number"]

        filename = f"duplicate_{i:02d}_{inv_num}.pdf"
        path = EDGE_DIR / filename
        render_invoice_pdf(dup, path)
        save_ground_truth(dup, path)
        INVOICE_HISTORY.append(dup)
        print(f"  ✅ {filename}  (dup of {original['invoice_number']})")

    # ── 3 price-spike invoices ────────────────────────────────────
    spike_pos = ["PO-2025-001", "PO-2025-002", "PO-2025-004"]
    spike_mults = [3.0, 2.5, 4.0]
    for i, (po_num, mult) in enumerate(zip(spike_pos, spike_mults), start=1):
        inv_num = f"INV-2025-{2200 + i}"
        po = SEED_POS[po_num]
        vid = po["vendor_id"]
        vendor = VENDORS[vid]
        items = _po_line_items(po_num, price_mult=mult)
        subtotal = round(sum(it["total"] for it in items), 2)
        tax = round(subtotal * TAX_RATE, 2)
        base_date = datetime.now() - timedelta(days=5 * i)

        data = {
            "invoice_number": inv_num,
            "po_number": po_num,
            "vendor": {"name": vendor["name"], "address": vendor["address"], "tax_id": vendor["tax_id"]},
            "customer": OUR_COMPANY.copy(),
            "invoice_date": base_date.strftime("%Y-%m-%d"),
            "due_date": (base_date + timedelta(days=30)).strftime("%Y-%m-%d"),
            "currency": "USD",
            "line_items": items,
            "subtotal": subtotal,
            "tax_rate": TAX_RATE,
            "tax_amount": tax,
            "shipping": 0,
            "total_amount": round(subtotal + tax, 2),
            "payment_terms": "Net 30",
            "invoice_type": "price_spike",
            "notes": f"All prices {mult}x PO amounts — should trigger price-spike alert",
        }

        filename = f"price_spike_{i:02d}_{inv_num}.pdf"
        path = EDGE_DIR / filename
        render_invoice_pdf(data, path)
        save_ground_truth(data, path)
        INVOICE_HISTORY.append(data)
        print(f"  ✅ {filename}  ({mult}x prices, ${data['total_amount']:,.2f})")

    # ── 4 missing-PO invoices ─────────────────────────────────────
    missing_po_defs = [
        {
            "vendor_id": "V001",
            "items": [{"desc": "Desk Lamp - LED", "sku": "LAMP-LED", "qty": 5, "price": 65.00}],
        },
        {
            "vendor_id": "V002",
            "items": [
                {"desc": "Wireless Keyboard", "sku": "KEY-WL", "qty": 10, "price": 89.00},
                {"desc": "Mouse Pad - XL", "sku": "PAD-XL", "qty": 10, "price": 19.00},
            ],
        },
        {
            "vendor_id": "V007",
            "items": [{"desc": "Window Cleaning Service", "sku": "WIN-CLN", "qty": 1, "price": 600.00}],
        },
        {
            "vendor_id": "V010",
            "items": [
                {"desc": "Annual SLA Subscription", "sku": "SLA-ANNUAL", "qty": 1, "price": 12000.00},
                {"desc": "Priority Support Add-on", "sku": "SUP-PRI", "qty": 1, "price": 3000.00},
            ],
        },
    ]
    for i, defn in enumerate(missing_po_defs, start=1):
        inv_num = f"INV-2025-{2300 + i}"
        vendor = VENDORS[defn["vendor_id"]]
        items = _make_items(defn["items"])
        subtotal = round(sum(it["total"] for it in items), 2)
        tax = round(subtotal * TAX_RATE, 2)
        base_date = datetime.now() - timedelta(days=10 + i * 3)

        data = {
            "invoice_number": inv_num,
            "po_number": None,
            "vendor": {"name": vendor["name"], "address": vendor["address"], "tax_id": vendor["tax_id"]},
            "customer": OUR_COMPANY.copy(),
            "invoice_date": base_date.strftime("%Y-%m-%d"),
            "due_date": (base_date + timedelta(days=30)).strftime("%Y-%m-%d"),
            "currency": "USD",
            "line_items": items,
            "subtotal": subtotal,
            "tax_rate": TAX_RATE,
            "tax_amount": tax,
            "shipping": 0,
            "total_amount": round(subtotal + tax, 2),
            "payment_terms": "Net 30",
            "invoice_type": "missing_po",
            "notes": "No PO reference — manual review required",
        }

        filename = f"missing_po_{i:02d}_{inv_num}.pdf"
        path = EDGE_DIR / filename
        render_missing_po_pdf(data, path)
        save_ground_truth(data, path)
        INVOICE_HISTORY.append(data)
        print(f"  ✅ {filename}  (no PO)")


# ────────────────────────────────────────────────────────────────────
# README + validation report
# ────────────────────────────────────────────────────────────────────


def create_readme():
    """Create README documenting the sample dataset."""
    readme = """# SmartAP Sample Invoice Dataset

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
"""
    path = OUTPUT_DIR.parent / "README.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"\n✅ Created {path}")


def create_validation_report():
    """Create a JSON validation report summarising the dataset."""
    currencies = {}
    types = {}
    total_value = 0
    po_count = 0

    for inv in INVOICE_HISTORY:
        curr = inv.get("currency", "USD")
        currencies[curr] = currencies.get(curr, 0) + 1
        inv_type = inv.get("invoice_type", "standard")
        types[inv_type] = types.get(inv_type, 0) + 1
        total_value += inv.get("total_amount", 0)
        if inv.get("po_number"):
            po_count += 1

    n = max(len(INVOICE_HISTORY), 1)
    report = {
        "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_invoices": len(INVOICE_HISTORY),
        "clean_invoices": 20,
        "messy_invoices": 15,
        "edge_case_invoices": 15,
        "currency_distribution": currencies,
        "invoice_types": types,
        "total_value": round(total_value, 2),
        "average_invoice_value": round(total_value / n, 2),
        "po_coverage": round((po_count / n) * 100, 1),
    }

    report_path = OUTPUT_DIR.parent / "VALIDATION_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"✅ Created {report_path}")
    print(f"\n📊 Dataset Summary:")
    print(f"   Total invoices: {report['total_invoices']}")
    print(f"   Total value: ${report['total_value']:,.2f}")
    print(f"   Average value: ${report['average_invoice_value']:,.2f}")
    print(f"   PO coverage: {report['po_coverage']}%")


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("SmartAP Seed-Aligned Invoice Generator")
    print("=" * 70)
    print()

    clean_output_dirs()
    generate_clean()
    generate_messy()
    generate_edge_cases()
    create_readme()
    create_validation_report()

    print("\n" + "=" * 70)
    print("🎉 Done! 50 invoices generated, all aligned with seed PO data.")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review generated invoices in sample-data/invoices/")
    print("2. Test with SmartAP extraction pipeline")
    print("3. Upload clean_01_INV-2025-1001.pdf for happy-path demo")
    print()
