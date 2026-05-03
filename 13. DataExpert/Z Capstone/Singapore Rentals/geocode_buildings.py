import time
import sqlite3
import requests
from pyproj import Transformer

DB_FILE = "rentals.db"

transformer = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)


def svy21_to_latlng(x, y):
    lng, lat = transformer.transform(x, y)
    return round(lat, 6), round(lng, 6)


def onemap_geocode(project, street):
    """Search OneMap by project name, fall back to street if no result."""
    for query in [project, f"{project} {street}"]:
        try:
            resp = requests.get(
                "https://www.onemap.gov.sg/api/common/elastic/search",
                params={
                    "searchVal": query,
                    "returnGeom": "Y",
                    "getAddrDetails": "Y",
                    "pageNum": 1,
                },
                timeout=10,
            )
            results = resp.json().get("results", [])
            if results:
                r = results[0]
                return round(float(r["LATITUDE"]), 6), round(float(r["LONGITUDE"]), 6)
        except Exception:
            pass
        time.sleep(0.3)
    return None, None


def add_latlng_columns(conn):
    existing = [row[1] for row in conn.execute("PRAGMA table_info(buildings)")]
    if "lat" not in existing:
        conn.execute("ALTER TABLE buildings ADD COLUMN lat REAL")
    if "lng" not in existing:
        conn.execute("ALTER TABLE buildings ADD COLUMN lng REAL")
    conn.commit()


if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    add_latlng_columns(conn)

    # --- Step 1: Convert SVY21 for buildings that have x/y ---
    buildings_with_coords = conn.execute(
        "SELECT id, x, y FROM buildings WHERE x IS NOT NULL AND y IS NOT NULL AND lat IS NULL"
    ).fetchall()

    print(f"Converting {len(buildings_with_coords):,} buildings from SVY21 to lat/lng...")
    for building_id, x, y in buildings_with_coords:
        lat, lng = svy21_to_latlng(x, y)
        conn.execute(
            "UPDATE buildings SET lat = ?, lng = ? WHERE id = ?",
            (lat, lng, building_id)
        )
    conn.commit()
    print(f"  Done.")

    # --- Step 2: OneMap geocode for buildings missing coordinates ---
    missing = conn.execute(
        "SELECT id, project, street FROM buildings WHERE x IS NULL OR y IS NULL"
    ).fetchall()

    print(f"\nGeocoding {len(missing)} buildings via OneMap...")
    found = 0
    not_found = []

    for building_id, project, street in missing:
        lat, lng = onemap_geocode(project, street)
        if lat:
            conn.execute(
                "UPDATE buildings SET lat = ?, lng = ? WHERE id = ?",
                (lat, lng, building_id)
            )
            found += 1
        else:
            not_found.append((building_id, project, street))
        time.sleep(0.3)

    conn.commit()

    print(f"  Found:     {found}")
    print(f"  Not found: {len(not_found)}")
    if not_found:
        print("\n  Buildings not geocoded:")
        for _, project, street in not_found:
            print(f"    {project} — {street}")

    # --- Summary ---
    total = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
    geocoded = conn.execute("SELECT COUNT(*) FROM buildings WHERE lat IS NOT NULL").fetchone()[0]
    print(f"\nFinal: {geocoded:,}/{total:,} buildings geocoded ({geocoded/total*100:.1f}%)")

    conn.close()
