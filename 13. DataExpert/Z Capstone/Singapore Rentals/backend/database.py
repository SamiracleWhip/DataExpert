import aiosqlite
from pathlib import Path
from typing import AsyncGenerator

DB_PATH = Path(__file__).parent.parent / "rentals.db"


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


def build_rental_filter(
    params: dict,
    table_alias: str = "r",
) -> tuple[str, list]:
    """Return (WHERE clause fragment, bind values) for rental_contracts filters.

    params keys: district (list[str]), bedrooms (list[str]), property_type (list[str]),
                 area_min (int), area_max (int),
                 date_from (str "YYYY-MM"), date_to (str "YYYY-MM"),
                 building_id (int)
    """
    clauses: list[str] = []
    values: list = []
    a = table_alias

    districts = params.get("district")
    if districts:
        placeholders = ",".join("?" * len(districts))
        clauses.append(f"{a}.district IN ({placeholders})")
        values.extend(districts)

    bedrooms = params.get("bedrooms")
    if bedrooms:
        null_requested = "unknown" in [b.lower() for b in bedrooms]
        non_null = [b for b in bedrooms if b.lower() != "unknown"]
        parts = []
        if null_requested:
            parts.append(f"{a}.no_of_bedrooms IS NULL")
        if non_null:
            placeholders = ",".join("?" * len(non_null))
            parts.append(f"{a}.no_of_bedrooms IN ({placeholders})")
            values.extend(non_null)
        if parts:
            clauses.append(f"({' OR '.join(parts)})")

    property_types = params.get("property_type")
    if property_types:
        placeholders = ",".join("?" * len(property_types))
        clauses.append(f"{a}.property_type IN ({placeholders})")
        values.extend(property_types)

    area_unit = params.get("area_unit", "sqm")  # "sqm" or "sqft"
    col_min = f"{a}.area_sqft_min" if area_unit == "sqft" else f"{a}.area_sqm_min"
    col_max = f"{a}.area_sqft_max" if area_unit == "sqft" else f"{a}.area_sqm_max"

    area_min = params.get("area_min")
    if area_min is not None:
        clauses.append(f"{col_min} >= ?")
        values.append(area_min)

    area_max = params.get("area_max")
    if area_max is not None:
        clauses.append(f"{col_max} <= ?")
        values.append(area_max)

    date_from = params.get("date_from")
    if date_from:
        y, m = int(date_from[:4]), int(date_from[5:7])
        clauses.append(f"({a}.lease_year * 100 + {a}.lease_month) >= ?")
        values.append(y * 100 + m)

    date_to = params.get("date_to")
    if date_to:
        y, m = int(date_to[:4]), int(date_to[5:7])
        clauses.append(f"({a}.lease_year * 100 + {a}.lease_month) <= ?")
        values.append(y * 100 + m)

    stations = params.get("station") or []
    if stations:
        placeholders = ",".join("?" * len(stations))
        clauses.append(
            f"{a}.building_id IN "
            f"(SELECT building_id FROM building_mrt_proximity WHERE station_name IN ({placeholders}))"
        )
        values.extend(stations)

    building_ids = params.get("building_id") or []
    if building_ids:
        placeholders = ",".join("?" * len(building_ids))
        clauses.append(f"{a}.building_id IN ({placeholders})")
        values.extend(building_ids)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, values
