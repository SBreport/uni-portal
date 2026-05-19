import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = "C:/LocalGD/7_CODE/uni-portal/data/equipment.db"
conn = sqlite3.connect(DB)
conn.text_factory = str
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM device_info")
print("device_info count:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM equipment")
print("equipment count:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL")
print("equipment unlinked:", cur.fetchone()[0])

cur.execute("SELECT name FROM pragma_table_info('device_info') WHERE name='primary_category_id'")
print("has primary_category_id col:", bool(cur.fetchone()))

# Check eq.id=80 광교
cur.execute("SELECT id, branch_id, name, device_info_id, category_id FROM equipment WHERE id=80")
print("\neq.id=80:", cur.fetchone())

# Check eq.id=614 목동
cur.execute("SELECT id, branch_id, name, device_info_id, category_id FROM equipment WHERE id=614")
print("eq.id=614:", cur.fetchone())

# Check eq.id=685 목포
cur.execute("SELECT id, branch_id, name, device_info_id, category_id FROM equipment WHERE id=685")
print("eq.id=685:", cur.fetchone())

# Check eq.id=690 목포
cur.execute("SELECT id, branch_id, name, device_info_id, category_id, note FROM equipment WHERE id=690")
print("eq.id=690:", cur.fetchone())

# Check device_info id=31 올리지오X
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=31")
print("\ndevice_info id=31:", cur.fetchone())

# Check device_info id=72 실리프팅
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=72")
print("device_info id=72:", cur.fetchone())

# Check device_info id=92 비타민
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=92")
print("device_info id=92:", cur.fetchone())

# Check device_info id=18 크라이오
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=18")
print("device_info id=18:", cur.fetchone())

# Check categories table
cur.execute("SELECT id, name FROM categories ORDER BY id")
print("\ncategories:")
for row in cur.fetchall():
    print(row)

# Check device_info columns
cur.execute("SELECT name FROM pragma_table_info('device_info')")
print("\ndevice_info columns:", [r[0] for r in cur.fetchall()])

# Compute majority vote for category_mismatch - get all device_info with equipment refs
cur.execute("""
    SELECT di.id, di.name,
           e.category_id,
           COUNT(*) as cnt
    FROM device_info di
    JOIN equipment e ON e.device_info_id = di.id
    WHERE e.category_id IS NOT NULL
    GROUP BY di.id, e.category_id
    ORDER BY di.id, cnt DESC
""")
rows = cur.fetchall()
print(f"\ndevice_info with equipment refs (id, name, category_id, count): {len(rows)} combos")

# Compute per device_info majority
from collections import defaultdict
di_cats = defaultdict(list)
for di_id, di_name, cat_id, cnt in rows:
    di_cats[di_id].append((cnt, cat_id, di_name))

print(f"Unique device_info with refs: {len(di_cats)}")

# Show first 10
for di_id in list(di_cats.keys())[:10]:
    combos = sorted(di_cats[di_id], reverse=True)
    winner = combos[0]
    print(f"  di.id={di_id}: winner cat_id={winner[1]} (cnt={winner[0]}) [{winner[2]}]")

# Check if branch_id for eq.id=80 is what we expect
cur.execute("SELECT id, name FROM branches WHERE id=2")
result = cur.fetchone()
print("\nbranch id=2:", result)

conn.close()
print("\nDone.")
