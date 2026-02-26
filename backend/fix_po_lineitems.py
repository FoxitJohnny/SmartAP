"""Fix PO P-26179 line items to match invoice NO-2026-9469."""
import sqlite3

conn = sqlite3.connect('smartap.db')
c = conn.cursor()

# PO P-26179 has id=13
PO_ID = 13

# Delete existing generic line item
c.execute("DELETE FROM po_line_items WHERE po_id = ?", (PO_ID,))
print(f"Deleted existing line items for PO {PO_ID}")

# Insert the 5 line items from invoice NO-2026-9469
line_items = [
    # (line_number, description, quantity, unit_price, amount, sku, unit, received_quantity)
    (1, "Software License - Annual", 4, 499.99, 1999.96, "SFT-LIC-008", "ea", 0),
    (2, "UPS Battery Backup - 1500VA", 2, 249.99, 499.98, "UPS-1500-012", "ea", 0),
    (3, "Network Router - Enterprise", 1, 899.99, 899.99, "NET-RTR-011", "ea", 0),
    (4, "Webcam - 4K HD", 5, 129.99, 649.95, "WEB-4K-013", "ea", 0),
    (5, "UPS Battery Backup - 1500VA", 5, 249.99, 1249.95, "UPS-1500-012", "ea", 0),
]

for item in line_items:
    c.execute("""
        INSERT INTO po_line_items (po_id, line_number, description, quantity, unit_price, amount, sku, unit, received_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (PO_ID, *item))
    print(f"Inserted line {item[0]}: {item[1]} ({item[5]}) = ${item[4]}")

# Verify subtotal matches
c.execute("SELECT SUM(amount) FROM po_line_items WHERE po_id = ?", (PO_ID,))
line_total = c.fetchone()[0]
print(f"\nLine items total: ${line_total}")

# Check PO totals
c.execute("SELECT subtotal, tax, total_amount FROM purchase_orders WHERE id = ?", (PO_ID,))
po = c.fetchone()
print(f"PO subtotal: ${po[0]}, tax: ${po[1]}, total: ${po[2]}")

# Update PO subtotal if needed (line items = subtotal, not total)
if abs(po[0] - line_total) > 0.01:
    # The line items sum to subtotal (5299.83), tax is 423.99, total is 5748.82
    new_subtotal = 5299.83
    c.execute("UPDATE purchase_orders SET subtotal = ? WHERE id = ?", (new_subtotal, PO_ID))
    print(f"Updated PO subtotal to ${new_subtotal}")

conn.commit()
print("\nDone! PO P-26179 now has 5 line items matching invoice NO-2026-9469")

# Verify
c.execute("SELECT * FROM po_line_items WHERE po_id = ?", (PO_ID,))
print("\nFinal line items:")
for row in c.fetchall():
    print(f"  {row}")

conn.close()
