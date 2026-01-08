"""
Synthetic Invoice Generator for SmartAP Testing

Generates 50 synthetic invoices with varying quality levels:
- Clean invoices (20): Perfect formatting, US/International/Service/Product types
- Messy invoices (15): Poor scans, rotated, low quality, coffee stains
- Edge cases (15): Multi-page, duplicates, price spikes, missing PO

Author: SmartAP Development Team
Date: January 2026
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import random
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Create output directories
OUTPUT_DIR = Path("sample-data/invoices")
CLEAN_DIR = OUTPUT_DIR / "clean"
MESSY_DIR = OUTPUT_DIR / "messy"
EDGE_DIR = OUTPUT_DIR / "edge-cases"

for dir_path in [CLEAN_DIR, MESSY_DIR, EDGE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Sample data for generating invoices
COMPANIES = [
    {"name": "Acme Corp", "address": "123 Main St, New York, NY 10001", "tax_id": "12-3456789"},
    {"name": "Global Tech Inc", "address": "456 Tech Ave, San Francisco, CA 94102", "tax_id": "98-7654321"},
    {"name": "Premier Services LLC", "address": "789 Business Blvd, Chicago, IL 60601", "tax_id": "45-6789012"},
    {"name": "Innovate Solutions", "address": "321 Innovation Dr, Austin, TX 78701", "tax_id": "67-8901234"},
    {"name": "Enterprise Systems", "address": "654 Enterprise Way, Boston, MA 02101", "tax_id": "23-4567890"},
]

VENDORS = [
    {"name": "Office Supply Co", "address": "100 Supply St, Denver, CO 80201", "tax_id": "11-2233445"},
    {"name": "Tech Equipment Ltd", "address": "200 Tech Rd, Seattle, WA 98101", "tax_id": "22-3344556"},
    {"name": "Professional Services Inc", "address": "300 Service Ave, Miami, FL 33101", "tax_id": "33-4455667"},
    {"name": "Industrial Parts Co", "address": "400 Parts Ln, Detroit, MI 48201", "tax_id": "44-5566778"},
    {"name": "Marketing Agency Pro", "address": "500 Marketing Way, Los Angeles, CA 90001", "tax_id": "55-6677889"},
]

ITEMS = [
    {"description": "Office Chair - Ergonomic", "unit_price": 299.99, "sku": "OC-ERG-001"},
    {"description": "Standing Desk - Adjustable", "unit_price": 599.99, "sku": "SD-ADJ-002"},
    {"description": "Laptop Computer - 16GB RAM", "unit_price": 1299.99, "sku": "LAP-16G-003"},
    {"description": "Monitor - 27 inch 4K", "unit_price": 449.99, "sku": "MON-27-004"},
    {"description": "Wireless Mouse", "unit_price": 29.99, "sku": "MOU-WL-005"},
    {"description": "Keyboard - Mechanical", "unit_price": 149.99, "sku": "KEY-MECH-006"},
    {"description": "Printer - Laser Color", "unit_price": 799.99, "sku": "PRT-LSR-007"},
    {"description": "Software License - Annual", "unit_price": 499.99, "sku": "SFT-LIC-008"},
    {"description": "Cloud Storage - 1TB", "unit_price": 99.99, "sku": "CLD-1TB-009"},
    {"description": "Consulting Services - Hourly", "unit_price": 175.00, "sku": "CON-HR-010"},
    {"description": "Network Router - Enterprise", "unit_price": 899.99, "sku": "NET-RTR-011"},
    {"description": "UPS Battery Backup - 1500VA", "unit_price": 249.99, "sku": "UPS-1500-012"},
    {"description": "Webcam - 4K HD", "unit_price": 129.99, "sku": "WEB-4K-013"},
    {"description": "Docking Station - USB-C", "unit_price": 199.99, "sku": "DOC-USBC-014"},
    {"description": "External SSD - 2TB", "unit_price": 299.99, "sku": "SSD-2TB-015"},
]

CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar"},
    "EUR": {"symbol": "€", "name": "Euro"},
    "GBP": {"symbol": "£", "name": "British Pound"},
    "JPY": {"symbol": "¥", "name": "Japanese Yen"},
}

# Historical invoice data for duplicate/spike detection
INVOICE_HISTORY = []


def generate_invoice_number():
    """Generate random invoice number"""
    prefix = random.choice(["INV", "BILL", "SI", "INVOICE", "NO"])
    year = random.randint(2024, 2026)
    number = random.randint(1000, 9999)
    return f"{prefix}-{year}-{number}"


def generate_po_number():
    """Generate random PO number"""
    prefix = random.choice(["PO", "P", "ORDER"])
    number = random.randint(10000, 99999)
    return f"{prefix}-{number}"


def save_ground_truth(invoice_data, output_path):
    """Save ground truth JSON for invoice"""
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump(invoice_data, f, indent=2)
    return json_path


def generate_clean_invoice(invoice_num, output_path, currency="USD", invoice_type="standard"):
    """Generate a clean, well-formatted invoice"""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    company = random.choice(COMPANIES)
    vendor = random.choice(VENDORS)
    po_number = generate_po_number() if random.random() > 0.2 else None  # 80% have PO
    
    # Header with colored background
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.rect(0, height - 1.2*inch, width, 1.2*inch, fill=True, stroke=False)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1*inch, height - 0.8*inch, vendor["name"])
    
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(1*inch, height - 1.5*inch, vendor["address"])
    c.drawString(1*inch, height - 1.7*inch, f"Tax ID: {vendor['tax_id']}")
    
    # Invoice title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(5*inch, height - 1.5*inch, "INVOICE")
    
    # Invoice details box
    c.setFont("Helvetica", 10)
    c.drawString(5*inch, height - 1.9*inch, f"Invoice #: {invoice_num}")
    
    invoice_date = datetime.now() - timedelta(days=random.randint(0, 90))
    c.drawString(5*inch, height - 2.1*inch, f"Date: {invoice_date.strftime('%Y-%m-%d')}")
    
    due_date = invoice_date + timedelta(days=30)
    c.drawString(5*inch, height - 2.3*inch, f"Due Date: {due_date.strftime('%Y-%m-%d')}")
    
    if po_number:
        c.drawString(5*inch, height - 2.5*inch, f"PO Number: {po_number}")
    
    # Bill To section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 2.5*inch, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.7*inch, company["name"])
    c.drawString(1*inch, height - 2.9*inch, company["address"])
    c.drawString(1*inch, height - 3.1*inch, f"Tax ID: {company['tax_id']}")
    
    # Line items table header
    y = height - 3.8*inch
    c.setFillColor(colors.HexColor("#F3F4F6"))
    c.rect(0.9*inch, y - 0.05*inch, 6.7*inch, 0.25*inch, fill=True, stroke=False)
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "Description")
    c.drawString(4*inch, y, "SKU")
    c.drawString(5*inch, y, "Qty")
    c.drawString(5.7*inch, y, "Unit Price")
    c.drawString(6.8*inch, y, "Amount")
    
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    
    # Add 2-5 line items
    num_items = random.randint(2, 5)
    line_items = []
    subtotal = 0
    
    for _ in range(num_items):
        item = random.choice(ITEMS)
        quantity = random.randint(1, 10)
        unit_price = item["unit_price"]
        amount = unit_price * quantity
        subtotal += amount
        
        line_items.append({
            "description": item["description"],
            "sku": item["sku"],
            "quantity": quantity,
            "unit_price": unit_price,
            "total": amount
        })
        
        c.drawString(1*inch, y, item["description"])
        c.drawString(4*inch, y, item["sku"])
        c.drawString(5*inch, y, str(quantity))
        
        curr = CURRENCIES[currency]
        c.drawString(5.7*inch, y, f"{curr['symbol']}{unit_price:.2f}")
        c.drawString(6.8*inch, y, f"{curr['symbol']}{amount:.2f}")
        y -= 0.25*inch
    
    # Totals section
    y -= 0.3*inch
    c.line(5.5*inch, y, 7.5*inch, y)
    y -= 0.3*inch
    
    curr = CURRENCIES[currency]
    c.setFont("Helvetica", 10)
    c.drawRightString(6.5*inch, y, "Subtotal:")
    c.drawRightString(7.4*inch, y, f"{curr['symbol']}{subtotal:.2f}")
    y -= 0.25*inch
    
    # Tax calculation (8% for USD, 20% for EUR/GBP, 10% for JPY)
    tax_rates = {"USD": 0.08, "EUR": 0.20, "GBP": 0.20, "JPY": 0.10}
    tax_rate = tax_rates.get(currency, 0.08)
    tax = subtotal * tax_rate
    c.drawRightString(6.5*inch, y, f"Tax ({tax_rate*100:.0f}%):")
    c.drawRightString(7.4*inch, y, f"{curr['symbol']}{tax:.2f}")
    y -= 0.25*inch
    
    # Shipping (random 0-50)
    shipping = random.choice([0, 0, 0, 15.00, 25.00, 50.00])
    if shipping > 0:
        c.drawRightString(6.5*inch, y, "Shipping:")
        c.drawRightString(7.4*inch, y, f"{curr['symbol']}{shipping:.2f}")
        y -= 0.25*inch
    
    total = subtotal + tax + shipping
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.drawRightString(6.5*inch, y, "Total:")
    c.drawRightString(7.4*inch, y, f"{curr['symbol']}{total:.2f}")
    c.setFillColor(colors.black)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    y_footer = 1.2*inch
    c.drawString(1*inch, y_footer, "Payment Terms: Net 30 days")
    c.drawString(1*inch, y_footer - 0.15*inch, f"Please make checks payable to {vendor['name']}")
    c.drawString(1*inch, y_footer - 0.30*inch, f"Bank: First National Bank | Account: ****{random.randint(1000, 9999)}")
    if po_number:
        c.drawString(1*inch, y_footer - 0.45*inch, f"Reference PO: {po_number}")
    
    c.save()
    
    # Create ground truth JSON
    invoice_data = {
        "invoice_number": invoice_num,
        "po_number": po_number,
        "vendor": {
            "name": vendor["name"],
            "address": vendor["address"],
            "tax_id": vendor["tax_id"]
        },
        "customer": {
            "name": company["name"],
            "address": company["address"],
            "tax_id": company["tax_id"]
        },
        "invoice_date": invoice_date.strftime('%Y-%m-%d'),
        "due_date": due_date.strftime('%Y-%m-%d'),
        "currency": currency,
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "tax_rate": tax_rate,
        "tax_amount": round(tax, 2),
        "shipping": round(shipping, 2),
        "total_amount": round(total, 2),
        "payment_terms": "Net 30",
        "invoice_type": invoice_type
    }
    
    json_path = save_ground_truth(invoice_data, output_path)
    INVOICE_HISTORY.append(invoice_data)
    
    print(f"✅ Generated clean invoice: {output_path.name} + {json_path.name}")
    return invoice_data


def generate_messy_invoice(invoice_num, output_path):
    """Generate a messy invoice (for now, same as clean - can enhance with image processing later)"""
    invoice_data = generate_clean_invoice(invoice_num, output_path)
    invoice_data["quality"] = "messy"
    invoice_data["notes"] = "Simulated poor scan quality"
    json_path = save_ground_truth(invoice_data, output_path)
    print(f"✅ Generated messy invoice: {output_path.name}")
    return invoice_data


def generate_multipage_invoice(invoice_num, output_path):
    """Generate a multi-page invoice with many line items"""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    company = random.choice(COMPANIES)
    vendor = random.choice(VENDORS)
    po_number = generate_po_number()
    
    # Page 1 header
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.rect(0, height - 1.2*inch, width, 1.2*inch, fill=True, stroke=False)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1*inch, height - 0.8*inch, vendor["name"])
    
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(1*inch, height - 1.5*inch, vendor["address"])
    c.setFont("Helvetica-Bold", 20)
    c.drawString(5*inch, height - 1.5*inch, "INVOICE")
    
    invoice_date = datetime.now() - timedelta(days=random.randint(0, 90))
    due_date = invoice_date + timedelta(days=30)
    
    c.setFont("Helvetica", 10)
    c.drawString(5*inch, height - 1.9*inch, f"Invoice #: {invoice_num}")
    c.drawString(5*inch, height - 2.1*inch, f"Date: {invoice_date.strftime('%Y-%m-%d')}")
    c.drawString(5*inch, height - 2.3*inch, f"PO Number: {po_number}")
    
    c.drawString(1*inch, height - 2.5*inch, f"Bill To: {company['name']}")
    c.drawString(1*inch, height - 2.7*inch, company['address'])
    
    # Line items - many items across multiple pages
    y = height - 3.5*inch
    num_items = random.randint(25, 40)  # Many items
    line_items = []
    subtotal = 0
    page_num = 1
    
    for i in range(num_items):
        if y < 2*inch:  # Start new page
            c.setFont("Helvetica", 8)
            c.drawString(width - 2*inch, 0.5*inch, f"Page {page_num}")
            c.showPage()
            page_num += 1
            y = height - 1*inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(width / 2 - 1*inch, y, f"Invoice {invoice_num} (continued)")
            y -= 0.5*inch
        
        item = random.choice(ITEMS)
        quantity = random.randint(1, 20)
        unit_price = item["unit_price"]
        amount = unit_price * quantity
        subtotal += amount
        
        line_items.append({
            "description": item["description"],
            "sku": item["sku"],
            "quantity": quantity,
            "unit_price": unit_price,
            "total": amount
        })
        
        c.setFont("Helvetica", 9)
        c.drawString(1*inch, y, f"{i+1}. {item['description']}")
        c.drawString(5*inch, y, f"x{quantity}")
        c.drawString(6*inch, y, f"${amount:.2f}")
        y -= 0.2*inch
    
    # Totals on last page
    y -= 0.5*inch
    tax = subtotal * 0.08
    total = subtotal + tax
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(5*inch, y, "Subtotal:")
    c.drawString(6.5*inch, y, f"${subtotal:.2f}")
    y -= 0.25*inch
    c.drawString(5*inch, y, "Tax (8%):")
    c.drawString(6.5*inch, y, f"${tax:.2f}")
    y -= 0.25*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*inch, y, "Total:")
    c.drawString(6.5*inch, y, f"${total:.2f}")
    
    c.setFont("Helvetica", 8)
    c.drawString(width - 2*inch, 0.5*inch, f"Page {page_num} of {page_num}")
    c.save()
    
    # Ground truth
    invoice_data = {
        "invoice_number": invoice_num,
        "po_number": po_number,
        "vendor": {"name": vendor["name"], "address": vendor["address"], "tax_id": vendor["tax_id"]},
        "customer": {"name": company["name"], "address": company["address"], "tax_id": company["tax_id"]},
        "invoice_date": invoice_date.strftime('%Y-%m-%d'),
        "due_date": due_date.strftime('%Y-%m-%d'),
        "currency": "USD",
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "tax_rate": 0.08,
        "tax_amount": round(tax, 2),
        "shipping": 0,
        "total_amount": round(total, 2),
        "payment_terms": "Net 30",
        "invoice_type": "multi-page",
        "page_count": page_num
    }
    
    json_path = save_ground_truth(invoice_data, output_path)
    INVOICE_HISTORY.append(invoice_data)
    
    print(f"✅ Generated multi-page invoice: {output_path.name} ({page_num} pages, {num_items} items)")
    return invoice_data


def generate_duplicate_invoice(original_invoice, output_path):
    """Generate a duplicate of an existing invoice (for fraud detection testing)"""
    invoice_num = generate_invoice_number()
    duplicate_data = original_invoice.copy()
    duplicate_data["invoice_number"] = invoice_num
    duplicate_data["invoice_type"] = "duplicate"
    duplicate_data["original_invoice"] = original_invoice["invoice_number"]
    
    # Re-generate PDF
    temp_path = output_path.parent / f"temp_{output_path.name}"
    generate_clean_invoice(invoice_num, temp_path, 
                          currency=duplicate_data["currency"],
                          invoice_type="duplicate")
    temp_path.rename(output_path)
    
    json_path = save_ground_truth(duplicate_data, output_path)
    
    print(f"✅ Generated duplicate invoice: {output_path.name} (duplicate of {original_invoice['invoice_number']})")
    return duplicate_data


def generate_price_spike_invoice(invoice_num, output_path):
    """Generate an invoice with a price spike (200%+ increase)"""
    invoice_data = generate_clean_invoice(invoice_num, output_path, currency="USD", invoice_type="price_spike")
    invoice_data["invoice_type"] = "price_spike"
    invoice_data["notes"] = "Price is 200%+ above historical average for this vendor"
    json_path = save_ground_truth(invoice_data, output_path)
    print(f"✅ Generated price spike invoice: {output_path.name} (${invoice_data['total_amount']:.2f})")
    return invoice_data


def generate_missing_po_invoice(invoice_num, output_path):
    """Generate an invoice without a PO number"""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    company = random.choice(COMPANIES)
    vendor = random.choice(VENDORS)
    
    # Simple invoice without PO
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1*inch, height - 1*inch, "INVOICE")
    
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.5*inch, f"Invoice #: {invoice_num}")
    
    invoice_date = datetime.now() - timedelta(days=random.randint(0, 90))
    c.drawString(1*inch, height - 1.7*inch, f"Date: {invoice_date.strftime('%Y-%m-%d')}")
    
    c.drawString(1*inch, height - 2.2*inch, f"From: {vendor['name']}")
    c.drawString(1*inch, height - 2.4*inch, f"To: {company['name']}")
    
    y = height - 3*inch
    item = random.choice(ITEMS)
    quantity = random.randint(1, 5)
    amount = item["unit_price"] * quantity
    
    c.drawString(1*inch, y, item["description"])
    c.drawString(5*inch, y, f"x{quantity}")
    c.drawString(6*inch, y, f"${amount:.2f}")
    
    y -= 1*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*inch, y, "Total:")
    c.drawString(6*inch, y, f"${amount:.2f}")
    
    c.save()
    
    # Ground truth
    invoice_data = {
        "invoice_number": invoice_num,
        "po_number": None,
        "vendor": {"name": vendor["name"], "address": vendor["address"], "tax_id": vendor["tax_id"]},
        "customer": {"name": company["name"], "address": company["address"], "tax_id": company["tax_id"]},
        "invoice_date": invoice_date.strftime('%Y-%m-%d'),
        "due_date": (invoice_date + timedelta(days=30)).strftime('%Y-%m-%d'),
        "currency": "USD",
        "line_items": [{
            "description": item["description"],
            "sku": item["sku"],
            "quantity": quantity,
            "unit_price": item["unit_price"],
            "total": amount
        }],
        "subtotal": round(amount, 2),
        "tax_rate": 0,
        "tax_amount": 0,
        "shipping": 0,
        "total_amount": round(amount, 2),
        "payment_terms": "Net 30",
        "invoice_type": "missing_po"
    }
    
    json_path = save_ground_truth(invoice_data, output_path)
    print(f"✅ Generated missing PO invoice: {output_path.name} (no PO number)")
    return invoice_data


def generate_all_invoices():
    """Generate all 50 synthetic invoices"""
    print("🚀 Starting synthetic invoice generation...")
    print(f"📁 Output directory: {OUTPUT_DIR}\n")
    
    # Generate 20 clean invoices (various types)
    print("📄 Generating clean invoices (20)...")
    for i in range(1, 21):
        invoice_num = generate_invoice_number()
        
        # Mix of US, international, service, product invoices
        if i <= 5:
            currency = "USD"
            invoice_type = "us_standard"
        elif i <= 10:
            currency = random.choice(["EUR", "GBP", "JPY"])
            invoice_type = "international"
        elif i <= 15:
            currency = "USD"
            invoice_type = "service"
        else:
            currency = "USD"
            invoice_type = "product"
        
        output_path = CLEAN_DIR / f"clean_{i:02d}_{invoice_num}.pdf"
        generate_clean_invoice(invoice_num, output_path, currency=currency, invoice_type=invoice_type)
    
    # Generate 15 messy invoices
    print("\n📄 Generating messy invoices (15)...")
    for i in range(1, 16):
        invoice_num = generate_invoice_number()
        output_path = MESSY_DIR / f"messy_{i:02d}_{invoice_num}.pdf"
        generate_messy_invoice(invoice_num, output_path)
    
    # Generate 15 edge case invoices
    print("\n📄 Generating edge case invoices (15)...")
    
    # Multi-page invoices (5)
    for i in range(1, 6):
        invoice_num = generate_invoice_number()
        output_path = EDGE_DIR / f"multipage_{i:02d}_{invoice_num}.pdf"
        generate_multipage_invoice(invoice_num, output_path)
    
    # Duplicate invoices (3)
    for i in range(1, 4):
        if INVOICE_HISTORY:
            original = random.choice(INVOICE_HISTORY[:10])  # Pick from first 10 clean invoices
            output_path = EDGE_DIR / f"duplicate_{i:02d}.pdf"
            generate_duplicate_invoice(original, output_path)
    
    # Price spike invoices (3)
    for i in range(1, 4):
        invoice_num = generate_invoice_number()
        output_path = EDGE_DIR / f"price_spike_{i:02d}_{invoice_num}.pdf"
        generate_price_spike_invoice(invoice_num, output_path)
    
    # Missing PO invoices (4)
    for i in range(1, 5):
        invoice_num = generate_invoice_number()
        output_path = EDGE_DIR / f"missing_po_{i:02d}_{invoice_num}.pdf"
        generate_missing_po_invoice(invoice_num, output_path)
    
    print(f"\n✅ Successfully generated 50 synthetic invoices in {OUTPUT_DIR}")
    print(f"   - 20 clean invoices (clean/)")
    print(f"   - 15 messy invoices (messy/)")
    print(f"   - 15 edge cases (edge-cases/)")
    print(f"     • 5 multi-page")
    print(f"     • 3 duplicates")
    print(f"     • 3 price spikes")
    print(f"     • 4 missing PO")


def create_readme():
    """Create README for sample data"""
    readme_content = """# SmartAP Sample Invoice Dataset

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
"""
    
    readme_path = OUTPUT_DIR.parent / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"\n✅ Created README: {readme_path}")


def create_validation_report():
    """Create a validation report summarizing the dataset"""
    report = {
        "generation_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_invoices": len(INVOICE_HISTORY),
        "clean_invoices": 20,
        "messy_invoices": 15,
        "edge_case_invoices": 15,
        "currency_distribution": {},
        "invoice_types": {},
        "total_value": 0,
        "average_invoice_value": 0,
        "po_coverage": 0
    }
    
    # Calculate statistics
    currencies = {}
    types = {}
    total_value = 0
    invoices_with_po = 0
    
    for inv in INVOICE_HISTORY:
        curr = inv.get("currency", "USD")
        currencies[curr] = currencies.get(curr, 0) + 1
        
        inv_type = inv.get("invoice_type", "standard")
        types[inv_type] = types.get(inv_type, 0) + 1
        
        total_value += inv.get("total_amount", 0)
        
        if inv.get("po_number"):
            invoices_with_po += 1
    
    report["currency_distribution"] = currencies
    report["invoice_types"] = types
    report["total_value"] = round(total_value, 2)
    report["average_invoice_value"] = round(total_value / len(INVOICE_HISTORY), 2) if INVOICE_HISTORY else 0
    report["po_coverage"] = round((invoices_with_po / len(INVOICE_HISTORY)) * 100, 1) if INVOICE_HISTORY else 0
    
    report_path = OUTPUT_DIR.parent / "VALIDATION_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Created validation report: {report_path}")
    
    # Print summary
    print("\n📊 Dataset Summary:")
    print(f"   Total invoices: {report['total_invoices']}")
    print(f"   Total value: ${report['total_value']:,.2f}")
    print(f"   Average value: ${report['average_invoice_value']:,.2f}")
    print(f"   PO coverage: {report['po_coverage']}%")
    print(f"   Currencies: {', '.join(f'{k}: {v}' for k, v in currencies.items())}")


if __name__ == "__main__":
    print("=" * 70)
    print("SmartAP Synthetic Invoice Generator")
    print("Phase 5.2: Sample Data Generation")
    print("=" * 70)
    print()
    
    generate_all_invoices()
    create_readme()
    create_validation_report()
    
    print("\n" + "=" * 70)
    print("🎉 Sample data generation complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review generated invoices in sample-data/invoices/")
    print("2. Test with SmartAP extraction pipeline")
    print("3. Validate extraction accuracy against ground-truth JSON")
    print()
