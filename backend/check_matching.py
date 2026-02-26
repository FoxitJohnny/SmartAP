"""Check why matching isn't working."""
import sqlite3
import json

conn = sqlite3.connect('smartap.db')
c = conn.cursor()

# Find PO P-26179
c.execute("SELECT po_number, vendor_id, total_amount, status FROM purchase_orders WHERE po_number = 'P-26179'")
po = c.fetchone()
print(f"PO P-26179: {po}")

if po:
    vendor_id = po[1]
    # Find vendor
    c.execute("SELECT vendor_id, vendor_name, status FROM vendors WHERE vendor_id = ?", (vendor_id,))
    vendor = c.fetchone()
    print(f"Vendor: {vendor}")

# Also check all vendors with "Marketing" in name
print("\nVendors with 'Marketing' in name:")
c.execute("SELECT vendor_id, vendor_name, status FROM vendors WHERE vendor_name LIKE '%Marketing%'")
for v in c.fetchall():
    print(f"  {v}")

# Check if matching ran for invoice 12
print("\nChecking processing events for invoice bd82c9e1-98a2-475c-800d-f948b1990e44:")
c.execute("SELECT stage, status, message FROM processing_events WHERE entity_id = 'bd82c9e1-98a2-475c-800d-f948b1990e44' ORDER BY created_at")
for ev in c.fetchall():
    print(f"  {ev[0]}: {ev[1]} - {ev[2]}")

conn.close()
