"""
Pre-computes which MRT stations are within THRESHOLD_M metres of each building.
Stores results in building_mrt_proximity for fast filtering.

Run once after geocoding, re-run if MRT network changes.
"""
import sqlite3, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from enrichment import MRT_STATIONS, haversine_m

DB = Path(__file__).parent / "rentals.db"
THRESHOLD_M = 1_000   # ~12-15 min walk

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("Creating building_mrt_proximity table…")
cur.execute("""
    CREATE TABLE IF NOT EXISTS building_mrt_proximity (
        building_id  INTEGER NOT NULL REFERENCES buildings(id),
        station_name TEXT    NOT NULL,
        distance_m   INTEGER NOT NULL,
        PRIMARY KEY (building_id, station_name)
    )
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_bmp_station ON building_mrt_proximity(station_name)")
cur.execute("DELETE FROM building_mrt_proximity")   # fresh compute

print("Loading geocoded buildings…")
rows = cur.execute(
    "SELECT id, lat, lng FROM buildings WHERE lat IS NOT NULL AND lng IS NOT NULL"
).fetchall()
print(f"  {len(rows):,} buildings with coordinates")
print(f"  {len(MRT_STATIONS)} MRT/LRT stations")
print(f"  Threshold: {THRESHOLD_M}m")

t0 = time.time()
inserts = []
for building_id, blat, blng in rows:
    for name, slat, slng in MRT_STATIONS:
        d = haversine_m(blat, blng, slat, slng)
        if d <= THRESHOLD_M:
            inserts.append((building_id, name, round(d)))

print(f"\nComputed {len(rows):,} × {len(MRT_STATIONS)} distances in {time.time()-t0:.1f}s")
print(f"Proximity pairs within {THRESHOLD_M}m: {len(inserts):,}")

cur.executemany(
    "INSERT OR IGNORE INTO building_mrt_proximity VALUES (?,?,?)",
    inserts
)
conn.commit()

# Summary stats
stats = cur.execute("""
    SELECT
        (SELECT COUNT(DISTINCT building_id) FROM building_mrt_proximity),
        (SELECT COUNT(DISTINCT station_name) FROM building_mrt_proximity),
        (SELECT ROUND(AVG(c),1) FROM (
            SELECT COUNT(*) c FROM building_mrt_proximity GROUP BY building_id)),
        (SELECT MAX(c) FROM (
            SELECT COUNT(*) c FROM building_mrt_proximity GROUP BY building_id))
""").fetchone()

print(f"\nResults:")
print(f"  Buildings near at least one station : {stats[0]:,}")
print(f"  Stations with at least one building : {stats[1]}")
print(f"  Avg stations per building           : {stats[2]}")
print(f"  Max stations for one building       : {stats[3]}")

conn.close()
print("\nDone.")
