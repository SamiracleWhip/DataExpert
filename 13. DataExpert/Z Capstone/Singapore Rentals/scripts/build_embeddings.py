"""
One-time script to build the ChromaDB vector store for the Shedza AI assistant.

Generates ~8,900+ context documents from rentals.db:
  - 28 district summaries
  - ~4,230 building summaries (buildings with ≥3 contracts)
  - ~476 quarterly district snapshots (28 districts × ~17 quarters)
  - ~2,000–4,000 building enrichment docs (PropertyGuru data — requires load_pg_enrichment.py)

Run from the project root:
    python scripts/build_embeddings.py

Re-run after each quarterly data refresh to add new buildings and snapshots,
or after running load_pg_enrichment.py to index new PropertyGuru data.
Output: backend/chroma_db/  (gitignored, ~50–150MB after embedding)

Uses ChromaDB's built-in ONNX embedding function (all-MiniLM-L6-v2) — no PyTorch needed.
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "rentals.db"
CHROMA_PATH = PROJECT_ROOT / "backend" / "chroma_db"

if not DB_PATH.exists():
    print(f"Error: rentals.db not found at {DB_PATH}", file=sys.stderr)
    sys.exit(1)

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

print("Connecting to ChromaDB (ONNX embeddings — no PyTorch required)…")
ef = DefaultEmbeddingFunction()
client = chromadb.PersistentClient(path=str(CHROMA_PATH))

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row


def _upsert(collection, ids: list, docs: list, metas: list, label: str):
    print(f"  Upserting {len(docs)} {label} documents…")
    batch_size = 64
    for i in range(0, len(docs), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=docs[i : i + batch_size],
            metadatas=metas[i : i + batch_size],
        )
        print(f"    {min(i + batch_size, len(docs))}/{len(docs)}")
    print(f"  ✓ {len(docs)} {label} docs upserted.")


# ─────────────────────────────────────────────
# 1. DISTRICT SUMMARIES
# ─────────────────────────────────────────────
print("\n[1/3] Building district summaries…")

district_rows = db.execute("""
    SELECT
        d.district,
        d.area_name,
        ROUND(AVG(r.rent), 0)                                          AS avg_rent,
        ROUND(AVG(CASE WHEN r.lease_year >= 2024 THEN r.rent END), 0)  AS avg_rent_recent,
        COUNT(DISTINCT r.building_id)                                  AS building_count,
        COUNT(*)                                                        AS contract_count
    FROM districts d
    LEFT JOIN rental_contracts r ON r.district = d.district
    GROUP BY d.district, d.area_name
    ORDER BY d.district
""").fetchall()

district_stations: dict[str, list[str]] = {}
for row in db.execute("""
    SELECT r.district, bmp.station_name, COUNT(*) AS cnt
    FROM rental_contracts r
    JOIN building_mrt_proximity bmp ON bmp.building_id = r.building_id
    GROUP BY r.district, bmp.station_name
    ORDER BY r.district, cnt DESC
""").fetchall():
    d = row["district"]
    if d not in district_stations:
        district_stations[d] = []
    if len(district_stations[d]) < 4:
        district_stations[d].append(row["station_name"])

dist_ids, dist_docs, dist_metas = [], [], []
for row in district_rows:
    d = row["district"]
    avg = int(row["avg_rent"] or 0)
    recent = int(row["avg_rent_recent"] or avg)
    stations = ", ".join(district_stations.get(d, [])) or "none recorded"
    doc = (
        f"District {d} — {row['area_name']}. "
        f"{row['building_count']} buildings, {row['contract_count']} contracts total. "
        f"Average rent S${avg:,}/mo overall; S${recent:,}/mo in 2024+. "
        f"Key MRT stations: {stations}."
    )
    dist_ids.append(f"district_{d}")
    dist_docs.append(doc)
    dist_metas.append({"district": d, "type": "district_summary"})

col_districts = client.get_or_create_collection("districts", embedding_function=ef)
_upsert(col_districts, dist_ids, dist_docs, dist_metas, "district")


# ─────────────────────────────────────────────
# 2. BUILDING SUMMARIES
# ─────────────────────────────────────────────
print("\n[2/3] Building summaries…")

building_rows = db.execute("""
    SELECT
        b.id,
        b.project,
        b.street,
        r.district,
        d.area_name,
        ROUND(AVG(r.rent), 0)                                         AS avg_rent,
        COUNT(*)                                                       AS contract_count,
        (SELECT station_name FROM building_mrt_proximity
         WHERE building_id = b.id ORDER BY distance_m LIMIT 1)        AS nearest_mrt,
        (SELECT distance_m FROM building_mrt_proximity
         WHERE building_id = b.id ORDER BY distance_m LIMIT 1)        AS nearest_mrt_m
    FROM buildings b
    JOIN rental_contracts r ON r.building_id = b.id
    JOIN districts d ON d.district = r.district
    GROUP BY b.id, b.project, b.street, r.district, d.area_name
    HAVING COUNT(*) >= 3
    ORDER BY b.id
""").fetchall()

bld_ids, bld_docs, bld_metas = [], [], []
seen_bld_ids: set[str] = set()
for row in building_rows:
    avg = int(row["avg_rent"] or 0)
    mrt_part = (
        f"Nearest MRT: {row['nearest_mrt']} ({row['nearest_mrt_m']}m)."
        if row["nearest_mrt"]
        else "No MRT data."
    )
    doc = (
        f"{row['project']}, {row['street']}. "
        f"District {row['district']} ({row['area_name']}). "
        f"Average rent S${avg:,}/mo ({row['contract_count']} contracts). "
        f"{mrt_part}"
    )
    uid = f"building_{row['id']}"
    if uid in seen_bld_ids:
        continue
    seen_bld_ids.add(uid)
    bld_ids.append(uid)
    bld_docs.append(doc)
    bld_metas.append({
        "building_id": row["id"],
        "district": row["district"],
        "type": "building_summary",
    })

col_buildings = client.get_or_create_collection("buildings", embedding_function=ef)
_upsert(col_buildings, bld_ids, bld_docs, bld_metas, "building")


# ─────────────────────────────────────────────
# 3. QUARTERLY DISTRICT SNAPSHOTS
# ─────────────────────────────────────────────
print("\n[3/3] Building quarterly district snapshots…")

quarterly_rows = db.execute("""
    SELECT
        r.district,
        d.area_name,
        r.lease_year,
        CASE
            WHEN r.lease_month BETWEEN 1  AND 3  THEN 1
            WHEN r.lease_month BETWEEN 4  AND 6  THEN 2
            WHEN r.lease_month BETWEEN 7  AND 9  THEN 3
            ELSE 4
        END                          AS lease_quarter,
        ROUND(AVG(r.rent), 0)       AS avg_rent,
        COUNT(*)                     AS contract_count
    FROM rental_contracts r
    JOIN districts d ON d.district = r.district
    GROUP BY r.district, d.area_name, r.lease_year, lease_quarter
    ORDER BY r.district, r.lease_year, lease_quarter
""").fetchall()

prev: dict[str, int] = {}
q_ids, q_docs, q_metas = [], [], []
for row in quarterly_rows:
    d = row["district"]
    avg = int(row["avg_rent"] or 0)
    qoq = ""
    if d in prev and prev[d] > 0:
        chg = (avg - prev[d]) / prev[d] * 100
        direction = "up" if chg >= 0 else "down"
        qoq = f", {direction} {abs(chg):.1f}% QoQ"
    prev[d] = avg
    doc = (
        f"District {d} ({row['area_name']}), "
        f"Q{row['lease_quarter']} {row['lease_year']}: "
        f"avg rent S${avg:,}/mo{qoq}. "
        f"{row['contract_count']} contracts."
    )
    uid = f"quarterly_{d}_{row['lease_year']}q{row['lease_quarter']}"
    q_ids.append(uid)
    q_docs.append(doc)
    q_metas.append({
        "district": d,
        "year": row["lease_year"],
        "quarter": row["lease_quarter"],
        "type": "quarterly_snapshot",
    })

col_quarterly = client.get_or_create_collection("quarterly", embedding_function=ef)
_upsert(col_quarterly, q_ids, q_docs, q_metas, "quarterly snapshot")


# ─────────────────────────────────────────────
# 4. BUILDING ENRICHMENT (PropertyGuru data)
# ─────────────────────────────────────────────
print("\n[4/4] Building enrichment summaries (PropertyGuru data)…")

# Check if the enrichment tables exist
has_enrichment = db.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='building_enrichment'"
).fetchone() is not None

enrich_ids, enrich_docs, enrich_metas = [], [], []

if not has_enrichment:
    print("  ⚠ building_enrichment table not found — run load_pg_enrichment.py first.")
    print("  Skipping enrichment collection.")
else:
    enrich_rows = db.execute("""
        SELECT
            e.building_id,
            b.project,
            b.street,
            r.district,
            d.area_name,
            e.developer,
            e.year_completed,
            e.tenure,
            e.total_units,
            e.description
        FROM building_enrichment e
        JOIN buildings b ON b.id = e.building_id
        LEFT JOIN rental_contracts r ON r.building_id = e.building_id
        LEFT JOIN districts d ON d.district = r.district
        GROUP BY e.building_id
        ORDER BY e.building_id
    """).fetchall()

    # Pre-fetch facilities for all enriched buildings
    fac_rows = db.execute(
        "SELECT building_id, GROUP_CONCAT(facility, ', ') AS facilities FROM building_facilities GROUP BY building_id"
    ).fetchall()
    facilities_by_id: dict[int, str] = {r["building_id"]: r["facilities"] for r in fac_rows}

    for row in enrich_rows:
        bid = row["building_id"]
        facilities_str = facilities_by_id.get(bid, "")
        desc = (row["description"] or "")[:400]

        parts = [f"{row['project']}, {row['street']}."]
        if row["year_completed"]:
            parts.append(f"Built {row['year_completed']}.")
        if row["tenure"]:
            parts.append(f"Tenure: {row['tenure']}.")
        if row["developer"]:
            parts.append(f"Developer: {row['developer']}.")
        if row["total_units"]:
            parts.append(f"{row['total_units']} units.")
        if facilities_str:
            parts.append(f"Facilities: {facilities_str}.")
        if desc:
            parts.append(desc)

        doc = " ".join(parts)
        enrich_ids.append(f"enrich_{bid}")
        enrich_docs.append(doc)
        enrich_metas.append({
            "building_id": bid,
            "district": row["district"] or "",
            "type": "building_enrichment",
        })

    if enrich_docs:
        col_enrich = client.get_or_create_collection("building_enrichment", embedding_function=ef)
        _upsert(col_enrich, enrich_ids, enrich_docs, enrich_metas, "enrichment")
    else:
        print("  No enrichment rows to embed.")

db.close()

total = len(dist_docs) + len(bld_docs) + len(q_docs) + len(enrich_docs)
print(f"\n✅ Done. {total} documents embedded and stored at {CHROMA_PATH}")
print(f"   Districts:   {len(dist_docs)}")
print(f"   Buildings:   {len(bld_docs)}")
print(f"   Quarterly:   {len(q_docs)}")
print(f"   Enrichment:  {len(enrich_docs)}")
