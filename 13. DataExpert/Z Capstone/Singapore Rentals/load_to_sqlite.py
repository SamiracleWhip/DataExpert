import json
import sqlite3

DB_FILE = "rentals.db"
RAW_FILE = "raw_rental_contracts_all.json"

DISTRICTS = {
    "01": "Raffles Place, Cecil, Marina, People's Park",
    "02": "Anson, Tanjong Pagar",
    "03": "Queenstown, Tiong Bahru",
    "04": "Telok Blangah, Harbourfront",
    "05": "Pasir Panjang, Clementi",
    "06": "City Hall, Beach Road",
    "07": "Middle Road, Golden Mile",
    "08": "Little India",
    "09": "Orchard, River Valley",
    "10": "Ardmore, Bukit Timah, Holland Road, Tanglin",
    "11": "Novena, Thomson, Watten",
    "12": "Balestier, Toa Payoh, Serangoon",
    "13": "Macpherson, Braddell",
    "14": "Geylang, Eunos",
    "15": "Katong, Joo Chiat, Amber Road",
    "16": "Bedok, Upper East Coast",
    "17": "Loyang, Changi",
    "18": "Tampines, Pasir Ris",
    "19": "Serangoon Garden, Hougang, Punggol",
    "20": "Bishan, Ang Mo Kio",
    "21": "Upper Bukit Timah, Ulu Pandan",
    "22": "Jurong",
    "23": "Hillview, Bukit Panjang, Choa Chu Kang",
    "24": "Lim Chu Kang, Tengah",
    "25": "Kranji, Woodgrove",
    "26": "Upper Thomson, Springleaf",
    "27": "Yishun, Sembawang",
    "28": "Seletar",
}


def create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS districts (
            district    TEXT PRIMARY KEY,
            area_name   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS buildings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project     TEXT NOT NULL,
            street      TEXT NOT NULL,
            x           REAL,
            y           REAL,
            UNIQUE(project, street)
        );

        CREATE TABLE IF NOT EXISTS rental_contracts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id     INTEGER NOT NULL REFERENCES buildings(id),
            lease_year      INTEGER NOT NULL,
            lease_month     INTEGER NOT NULL,
            property_type   TEXT,
            district        TEXT REFERENCES districts(district),
            area_sqft       TEXT,
            area_sqm        TEXT,
            no_of_bedrooms  TEXT,
            rent            INTEGER NOT NULL,
            UNIQUE(building_id, lease_year, lease_month, property_type,
                   district, area_sqft, no_of_bedrooms, rent)
        );

        CREATE INDEX IF NOT EXISTS idx_contracts_building
            ON rental_contracts(building_id);
        CREATE INDEX IF NOT EXISTS idx_contracts_district
            ON rental_contracts(district);
        CREATE INDEX IF NOT EXISTS idx_contracts_lease
            ON rental_contracts(lease_year, lease_month);
        CREATE INDEX IF NOT EXISTS idx_contracts_bedrooms
            ON rental_contracts(no_of_bedrooms);
    """)
    conn.commit()


def seed_districts(conn):
    conn.executemany(
        "INSERT OR IGNORE INTO districts VALUES (?, ?)",
        DISTRICTS.items()
    )
    conn.commit()


def parse_lease_date(lease_date):
    """Parse mmyy string (e.g. '0125') into (year, month)."""
    month = int(lease_date[:2])
    year = 2000 + int(lease_date[2:])
    return year, month


def load_data(conn, raw_file):
    with open(raw_file) as f:
        data = json.load(f)

    buildings_inserted = 0
    buildings_skipped = 0
    contracts_inserted = 0
    contracts_skipped = 0

    for quarter, projects in data.items():
        for project in projects:
            proj_name = project["project"]
            street = project["street"]
            x = float(project["x"]) if project.get("x") else None
            y = float(project["y"]) if project.get("y") else None

            cur = conn.execute(
                "INSERT OR IGNORE INTO buildings(project, street, x, y) VALUES (?, ?, ?, ?)",
                (proj_name, street, x, y)
            )
            if cur.rowcount:
                buildings_inserted += 1
            else:
                buildings_skipped += 1

            building_id = conn.execute(
                "SELECT id FROM buildings WHERE project = ? AND street = ?",
                (proj_name, street)
            ).fetchone()[0]

            for c in project.get("rental", []):
                lease_year, lease_month = parse_lease_date(c["leaseDate"])
                no_of_bedrooms = c.get("noOfBedRoom")
                if no_of_bedrooms == "NA":
                    no_of_bedrooms = None

                cur = conn.execute(
                    """INSERT OR IGNORE INTO rental_contracts
                       (building_id, lease_year, lease_month, property_type,
                        district, area_sqft, area_sqm, no_of_bedrooms, rent)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        building_id,
                        lease_year,
                        lease_month,
                        c.get("propertyType"),
                        c.get("district"),
                        c.get("areaSqft"),
                        c.get("areaSqm"),
                        no_of_bedrooms,
                        c["rent"],
                    )
                )
                if cur.rowcount:
                    contracts_inserted += 1
                else:
                    contracts_skipped += 1

    conn.commit()
    return buildings_inserted, buildings_skipped, contracts_inserted, contracts_skipped


if __name__ == "__main__":
    print(f"Creating database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)

    print("Creating tables...")
    create_tables(conn)

    print("Seeding districts...")
    seed_districts(conn)

    print("Loading rental data...")
    b_ins, b_skip, c_ins, c_skip = load_data(conn, RAW_FILE)

    print(f"\nBuildings  — inserted: {b_ins:,}  |  duplicates skipped: {b_skip:,}")
    print(f"Contracts  — inserted: {c_ins:,}  |  duplicates skipped: {c_skip:,}")

    conn.close()
    print(f"\nDone. Database saved to {DB_FILE}")
