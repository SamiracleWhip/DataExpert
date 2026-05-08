#!/usr/bin/env python3
"""
Load scraped PropertyGuru enrichment data from raw_pg_enrichment.json into rentals.db.

Creates three new tables if they don't exist:
  - building_enrichment   (developer, year_completed, tenure, total_units, description, pg_url)
  - building_facilities   (one row per facility per building)
  - building_photos       (photo URLs, ready for download + CLIP embedding)

Run from project root:
    python scripts/load_pg_enrichment.py

Idempotent: uses INSERT OR REPLACE for enrichment, INSERT OR IGNORE for facilities/photos.
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "rentals.db"
INPUT_PATH = PROJECT_ROOT / "raw_pg_enrichment.json"

MATCH_THRESHOLD = 75


def create_tables(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS building_enrichment (
            building_id    INTEGER PRIMARY KEY REFERENCES buildings(id),
            developer      TEXT,
            year_completed INTEGER,
            tenure         TEXT,
            total_units    INTEGER,
            description    TEXT,
            pg_url         TEXT,
            scraped_at     TEXT
        );

        CREATE TABLE IF NOT EXISTS building_facilities (
            building_id  INTEGER REFERENCES buildings(id),
            facility     TEXT NOT NULL,
            PRIMARY KEY (building_id, facility)
        );

        CREATE TABLE IF NOT EXISTS building_photos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id  INTEGER REFERENCES buildings(id),
            pg_url       TEXT NOT NULL,
            local_path   TEXT,
            chroma_id    TEXT,
            photo_order  INTEGER,
            UNIQUE (building_id, photo_order)
        );

        CREATE INDEX IF NOT EXISTS idx_enrich_building ON building_enrichment(building_id);
        CREATE INDEX IF NOT EXISTS idx_facilities_building ON building_facilities(building_id);
        CREATE INDEX IF NOT EXISTS idx_photos_building ON building_photos(building_id);
    """)
    db.commit()


def load(db: sqlite3.Connection, data: dict[str, dict]) -> tuple[int, int, int]:
    """Insert enrichment records. Returns (enrichment_rows, facility_rows, photo_rows)."""
    scraped_at = datetime.now(timezone.utc).isoformat()
    enrich_count = 0
    facility_count = 0
    photo_count = 0

    for building_id_str, rec in data.items():
        building_id = int(building_id_str)
        score = rec.get("match_score", 0)

        # Only load records that had a successful match
        if score < MATCH_THRESHOLD:
            continue
        if rec.get("error") and not rec.get("pg_url"):
            continue

        db.execute(
            """
            INSERT OR REPLACE INTO building_enrichment
                (building_id, developer, year_completed, tenure, total_units,
                 description, pg_url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                building_id,
                rec.get("developer"),
                rec.get("year_completed"),
                rec.get("tenure"),
                rec.get("total_units"),
                rec.get("description"),
                rec.get("pg_url"),
                scraped_at,
            ),
        )
        enrich_count += 1

        for facility in rec.get("facilities") or []:
            facility = facility.strip()
            if not facility:
                continue
            try:
                db.execute(
                    "INSERT OR IGNORE INTO building_facilities (building_id, facility) VALUES (?, ?)",
                    (building_id, facility),
                )
                facility_count += 1
            except sqlite3.IntegrityError:
                pass

        for order, photo_url in enumerate(rec.get("photos") or []):
            photo_url = photo_url.strip()
            if not photo_url:
                continue
            try:
                db.execute(
                    """
                    INSERT OR IGNORE INTO building_photos (building_id, pg_url, photo_order)
                    VALUES (?, ?, ?)
                    """,
                    (building_id, photo_url, order),
                )
                photo_count += 1
            except sqlite3.IntegrityError:
                pass

    db.commit()
    return enrich_count, facility_count, photo_count


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    if not INPUT_PATH.exists():
        print(f"Error: {INPUT_PATH} not found. Run scrape_propertyguru.py first.", file=sys.stderr)
        sys.exit(1)

    with open(INPUT_PATH) as f:
        data = json.load(f)
    print(f"Records in JSON: {len(data)}")

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    create_tables(db)
    print("Tables created/verified.")

    ec, fc, pc = load(db, data)
    db.close()

    print(f"\n✅ Loaded:")
    print(f"   building_enrichment rows: {ec}")
    print(f"   building_facilities rows: {fc}")
    print(f"   building_photos rows:     {pc}")
