"""
Migration: split area_sqm and area_sqft range strings into integer min/max columns.

Before: area_sqm = "80-90"  (TEXT)
After:  area_sqm_min = 80, area_sqm_max = 90  (INTEGER)
"""
import sqlite3, time
from pathlib import Path

DB = Path(__file__).parent / "rentals.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("Adding new columns…")
for col in ("area_sqm_min", "area_sqm_max", "area_sqft_min", "area_sqft_max"):
    try:
        cur.execute(f"ALTER TABLE rental_contracts ADD COLUMN {col} INTEGER")
        print(f"  + {col}")
    except sqlite3.OperationalError:
        print(f"  (already exists) {col}")

print("Parsing and populating integer values…")
t0 = time.time()
cur.execute("""
    UPDATE rental_contracts SET
        area_sqm_min  = CASE WHEN INSTR(COALESCE(area_sqm,''),  '-') > 0
                        THEN CAST(SUBSTR(area_sqm,  1, INSTR(area_sqm,  '-') - 1) AS INTEGER) ELSE NULL END,
        area_sqm_max  = CASE WHEN INSTR(COALESCE(area_sqm,''),  '-') > 0
                        THEN CAST(SUBSTR(area_sqm,  INSTR(area_sqm,  '-') + 1)    AS INTEGER) ELSE NULL END,
        area_sqft_min = CASE WHEN INSTR(COALESCE(area_sqft,''), '-') > 0
                        THEN CAST(SUBSTR(area_sqft, 1, INSTR(area_sqft, '-') - 1) AS INTEGER) ELSE NULL END,
        area_sqft_max = CASE WHEN INSTR(COALESCE(area_sqft,''), '-') > 0
                        THEN CAST(SUBSTR(area_sqft, INSTR(area_sqft, '-') + 1)    AS INTEGER) ELSE NULL END
""")
print(f"  Updated {cur.rowcount:,} rows in {time.time()-t0:.1f}s")

print("Creating indexes…")
for idx, col in [
    ("idx_area_sqm_min",  "area_sqm_min"),
    ("idx_area_sqm_max",  "area_sqm_max"),
    ("idx_area_sqft_min", "area_sqft_min"),
    ("idx_area_sqft_max", "area_sqft_max"),
]:
    cur.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON rental_contracts({col})")
    print(f"  + {idx}")

conn.commit()
conn.close()

# Verify
conn2 = sqlite3.connect(DB)
row = conn2.execute(
    "SELECT area_sqm, area_sqm_min, area_sqm_max FROM rental_contracts "
    "WHERE area_sqm IS NOT NULL LIMIT 1"
).fetchone()
print(f"\nVerification sample: area_sqm='{row[0]}' → min={row[1]}, max={row[2]}")
conn2.close()
print("\nMigration complete.")
