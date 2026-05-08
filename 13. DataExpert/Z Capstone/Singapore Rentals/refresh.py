"""
Quarterly refresh for Shedza rental data.

Detects which quarters are missing since the last fetch, pulls them from the
URA API, and runs the full downstream pipeline: DB insert, geocoding, area
column population, MRT proximity update.

Usage:
    python refresh.py
"""

import json
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
import urllib3
from dotenv import load_dotenv
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from enrichment import MRT_STATIONS, haversine_m

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

ACCESS_KEY = os.getenv("URA_ACCESS_KEY")
BASE_URL = "https://eservice.ura.gov.sg/uraDataService"
HEADERS_BASE = {"User-Agent": "curl/8.4.0"}
REQUEST_OPTS = {"verify": False}

DB_FILE = Path(__file__).parent / "rentals.db"
RAW_FILE = Path(__file__).parent / "raw_rental_contracts_all.json"

EXCLUDED_TYPES = {"Semi-Detached House", "Detached House"}
MRT_THRESHOLD_M = 1_000


# ── Quarter helpers ───────────────────────────────────────────────────────────

def current_quarter():
    today = date.today()
    q = (today.month - 1) // 3 + 1
    return today.year % 100, q


def quarter_key(yy, q):
    return f"{yy:02d}q{q}"


def parse_quarter(s):
    yy, q = s.split("q")
    return int(yy), int(q)


def quarters_after(last_yy, last_q, end_yy, end_q):
    """All quarters strictly after (last_yy, last_q) up to (end_yy, end_q)."""
    result = []
    yy, q = last_yy, last_q
    while True:
        q += 1
        if q > 4:
            q, yy = 1, yy + 1
        if (yy, q) > (end_yy, end_q):
            break
        result.append(quarter_key(yy, q))
    return result


# ── URA API ───────────────────────────────────────────────────────────────────

def get_token():
    resp = requests.get(
        f"{BASE_URL}/insertNewToken/v1",
        headers={**HEADERS_BASE, "AccessKey": ACCESS_KEY},
        **REQUEST_OPTS,
    )
    resp.raise_for_status()
    data = resp.json()
    if data["Status"] != "Success":
        raise RuntimeError(f"Token error: {data['Message']}")
    return data["Result"]


def fetch_quarter(token, ref_period):
    resp = requests.get(
        f"{BASE_URL}/invokeUraDS/v1",
        params={"service": "PMI_Resi_Rental", "refPeriod": ref_period},
        headers={**HEADERS_BASE, "AccessKey": ACCESS_KEY, "Token": token},
        **REQUEST_OPTS,
    )
    resp.raise_for_status()
    data = resp.json()
    if data["Status"] != "Success":
        raise RuntimeError(f"API error for {ref_period}: {data['Message']}")
    return data["Result"]


# ── Geocoding ─────────────────────────────────────────────────────────────────

_transformer = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)


def svy21_to_latlng(x, y):
    lng, lat = _transformer.transform(x, y)
    return round(lat, 6), round(lng, 6)


def onemap_geocode(project, street):
    for query in [project, f"{project} {street}"]:
        try:
            resp = requests.get(
                "https://www.onemap.gov.sg/api/common/elastic/search",
                params={"searchVal": query, "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": 1},
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


# ── DB helpers ────────────────────────────────────────────────────────────────

def parse_lease_date(lease_date):
    return 2000 + int(lease_date[2:]), int(lease_date[:2])


def ensure_columns(conn):
    """Add area integer columns and MRT proximity table if not yet present."""
    for col in ("area_sqm_min", "area_sqm_max", "area_sqft_min", "area_sqft_max"):
        try:
            conn.execute(f"ALTER TABLE rental_contracts ADD COLUMN {col} INTEGER")
        except sqlite3.OperationalError:
            pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS building_mrt_proximity (
            building_id  INTEGER NOT NULL REFERENCES buildings(id),
            station_name TEXT    NOT NULL,
            distance_m   INTEGER NOT NULL,
            PRIMARY KEY (building_id, station_name)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bmp_station ON building_mrt_proximity(station_name)"
    )
    conn.commit()


def insert_projects(conn, projects):
    buildings_new = contracts_new = 0
    new_building_ids = []

    for project in projects:
        proj_name = project["project"]
        street = project["street"]
        x = float(project["x"]) if project.get("x") else None
        y = float(project["y"]) if project.get("y") else None

        cur = conn.execute(
            "INSERT OR IGNORE INTO buildings(project, street, x, y) VALUES (?,?,?,?)",
            (proj_name, street, x, y),
        )
        if cur.rowcount:
            buildings_new += 1
            new_building_ids.append(conn.execute(
                "SELECT id FROM buildings WHERE project=? AND street=?", (proj_name, street)
            ).fetchone()[0])

        building_id = conn.execute(
            "SELECT id FROM buildings WHERE project=? AND street=?", (proj_name, street)
        ).fetchone()[0]

        for c in project.get("rental", []):
            if c.get("propertyType") in EXCLUDED_TYPES:
                continue
            lease_year, lease_month = parse_lease_date(c["leaseDate"])
            bedrooms = c.get("noOfBedRoom")
            if bedrooms == "NA":
                bedrooms = None

            cur = conn.execute(
                """INSERT OR IGNORE INTO rental_contracts
                   (building_id, lease_year, lease_month, property_type,
                    district, area_sqft, area_sqm, no_of_bedrooms, rent)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (building_id, lease_year, lease_month, c.get("propertyType"),
                 c.get("district"), c.get("areaSqft"), c.get("areaSqm"), bedrooms, c["rent"]),
            )
            contracts_new += cur.rowcount

    conn.commit()
    return buildings_new, contracts_new, new_building_ids


def geocode_new_buildings(conn):
    # SVY21 conversion
    rows = conn.execute(
        "SELECT id, x, y FROM buildings WHERE x IS NOT NULL AND y IS NOT NULL AND lat IS NULL"
    ).fetchall()
    for bid, x, y in rows:
        lat, lng = svy21_to_latlng(x, y)
        conn.execute("UPDATE buildings SET lat=?, lng=? WHERE id=?", (lat, lng, bid))
    conn.commit()

    # OneMap fallback
    missing = conn.execute(
        "SELECT id, project, street FROM buildings WHERE lat IS NULL"
    ).fetchall()
    found = 0
    for bid, project, street in missing:
        lat, lng = onemap_geocode(project, street)
        if lat:
            conn.execute("UPDATE buildings SET lat=?, lng=? WHERE id=?", (lat, lng, bid))
            found += 1
        time.sleep(0.3)
    conn.commit()
    return len(rows), found


def populate_area_columns(conn):
    cur = conn.execute("""
        UPDATE rental_contracts SET
            area_sqm_min  = CASE WHEN INSTR(COALESCE(area_sqm,''),  '-') > 0
                            THEN CAST(SUBSTR(area_sqm,  1, INSTR(area_sqm,  '-')-1) AS INTEGER)
                            ELSE NULL END,
            area_sqm_max  = CASE WHEN INSTR(COALESCE(area_sqm,''),  '-') > 0
                            THEN CAST(SUBSTR(area_sqm,  INSTR(area_sqm,  '-')+1)    AS INTEGER)
                            ELSE NULL END,
            area_sqft_min = CASE WHEN INSTR(COALESCE(area_sqft,''), '-') > 0
                            THEN CAST(SUBSTR(area_sqft, 1, INSTR(area_sqft, '-')-1) AS INTEGER)
                            ELSE NULL END,
            area_sqft_max = CASE WHEN INSTR(COALESCE(area_sqft,''), '-') > 0
                            THEN CAST(SUBSTR(area_sqft, INSTR(area_sqft, '-')+1)    AS INTEGER)
                            ELSE NULL END
        WHERE area_sqm_min IS NULL AND area_sqm IS NOT NULL
    """)
    conn.commit()
    return cur.rowcount


def update_mrt_proximity(conn, building_ids):
    if not building_ids:
        return 0
    placeholders = ",".join("?" * len(building_ids))
    rows = conn.execute(
        f"SELECT id, lat, lng FROM buildings "
        f"WHERE id IN ({placeholders}) AND lat IS NOT NULL AND lng IS NOT NULL",
        building_ids,
    ).fetchall()
    pairs = [
        (bid, name, round(haversine_m(blat, blng, slat, slng)))
        for bid, blat, blng in rows
        for name, slat, slng in MRT_STATIONS
        if haversine_m(blat, blng, slat, slng) <= MRT_THRESHOLD_M
    ]
    if pairs:
        conn.executemany("INSERT OR IGNORE INTO building_mrt_proximity VALUES (?,?,?)", pairs)
        conn.commit()
    return len(pairs)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not ACCESS_KEY:
        print("ERROR: URA_ACCESS_KEY not found in .env")
        sys.exit(1)

    raw_data = {}
    if RAW_FILE.exists():
        with open(RAW_FILE) as f:
            raw_data = json.load(f)

    if raw_data:
        last_q = max(raw_data.keys(), key=parse_quarter)
        last_yy, last_q_num = parse_quarter(last_q)
        print(f"Last fetched quarter : {last_q}")
    else:
        last_yy, last_q_num = 21, 4
        print("No existing data — fetching from 22q1")

    cur_yy, cur_q_num = current_quarter()
    print(f"Current quarter      : {quarter_key(cur_yy, cur_q_num)}")

    to_fetch = quarters_after(last_yy, last_q_num, cur_yy, cur_q_num)
    if not to_fetch:
        print("\nAlready up to date. Nothing to fetch.")
        return

    print(f"Quarters to fetch    : {to_fetch}\n")

    print("Getting URA token...")
    token = get_token()
    print("Token obtained.\n")

    fetched = {}
    for qtr in to_fetch:
        print(f"  Fetching {qtr}...", end=" ", flush=True)
        try:
            records = fetch_quarter(token, qtr)
            for r in records:
                r["rental"] = [c for c in r.get("rental", [])
                               if c.get("propertyType") not in EXCLUDED_TYPES]
            records = [r for r in records if r["rental"]]
            fetched[qtr] = records
            print(f"{len(records)} projects")
        except Exception as e:
            print(f"FAILED: {e}")
            fetched[qtr] = []
        time.sleep(0.5)

    raw_data.update(fetched)
    with open(RAW_FILE, "w") as f:
        json.dump(raw_data, f, indent=2)
    print(f"\nRaw JSON updated ({RAW_FILE.name})")

    conn = sqlite3.connect(DB_FILE)
    ensure_columns(conn)

    total_buildings = total_contracts = 0
    all_new_building_ids = []

    for qtr, projects in fetched.items():
        if not projects:
            continue
        b, c, new_ids = insert_projects(conn, projects)
        all_new_building_ids.extend(new_ids)
        total_buildings += b
        total_contracts += c
        print(f"  {qtr}: +{b} buildings, +{c} contracts")

    print(f"\nInserted: {total_buildings} new buildings, {total_contracts} new contracts")

    if total_buildings > 0:
        print(f"\nGeocoding {total_buildings} new building(s)...")
        svy21_done, onemap_done = geocode_new_buildings(conn)
        print(f"  SVY21 converted : {svy21_done}")
        print(f"  OneMap geocoded : {onemap_done}")
        not_found = total_buildings - svy21_done - onemap_done
        if not_found > 0:
            print(f"  Not geocoded    : {not_found}")

    area_updated = populate_area_columns(conn)
    if area_updated:
        print(f"\nArea columns populated for {area_updated:,} new contracts")

    mrt_pairs = update_mrt_proximity(conn, all_new_building_ids)
    if mrt_pairs:
        print(f"MRT proximity pairs added: {mrt_pairs}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
