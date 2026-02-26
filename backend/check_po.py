"""Check PO P-26179 and its line items."""
import sqlite3

conn = sqlite3.connect('smartap.db')
c = conn.cursor()

# List all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in c.fetchall()])

# Check if there's a po_line_items table
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%line%'")
line_tables = c.fetchall()
print(f"\nLine item tables: {line_tables}")

for table in line_tables:
    table_name = table[0]
    c.execute(f"PRAGMA table_info({table_name})")
    print(f"\n{table_name} columns: {[r[1] for r in c.fetchall()]}")
    
    # Get items for PO 13 (which is P-26179)
    try:
        c.execute(f"SELECT * FROM {table_name} WHERE po_id = 13")
        rows = c.fetchall()
        print(f"Items for PO 13: {rows}")
    except:
        pass

# Check PO details
c.execute("SELECT id, po_number, vendor_id, total_amount FROM purchase_orders WHERE po_number = 'P-26179'")
print(f"\nPO P-26179: {c.fetchone()}")

conn.close()
