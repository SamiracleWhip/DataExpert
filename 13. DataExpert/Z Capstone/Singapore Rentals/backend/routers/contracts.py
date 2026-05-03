import aiosqlite
from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import get_db, build_rental_filter

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

ALLOWED_SORT_COLS = {
    "rent", "lease_year", "lease_month", "district", "no_of_bedrooms",
    "area_sqm_min", "area_sqm_max",
}


@router.get("")
async def list_contracts(
    district: list[str] = Query(default=[]),
    bedrooms: list[str] = Query(default=[]),
    property_type: list[str] = Query(default=[]),
    area_min: Optional[int] = None,
    area_max: Optional[int] = None,
    area_unit: str = "sqm",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    station: list[str] = Query(default=[]),
    building_id: list[int] = Query(default=[]),
    sort_by: str = "lease_year",
    sort_dir: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    params = dict(
        district=district or None,
        bedrooms=bedrooms or None,
        property_type=property_type or None,
        area_min=area_min,
        area_max=area_max,
        area_unit=area_unit,
        date_from=date_from,
        date_to=date_to,
        station=station or None,
        building_id=building_id or None,
    )
    where, values = build_rental_filter(params, table_alias="r")

    col = sort_by if sort_by in ALLOWED_SORT_COLS else "lease_year"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    sql = f"""
        SELECT
            r.id,
            b.project,
            b.street,
            r.district,
            r.no_of_bedrooms,
            r.area_sqm_min,
            r.area_sqm_max,
            r.rent,
            r.lease_year,
            r.lease_month,
            r.property_type
        FROM rental_contracts r
        JOIN buildings b ON b.id = r.building_id
        {where}
        ORDER BY r.{col} {direction}
        LIMIT ? OFFSET ?
    """

    sql_count = f"""
        SELECT COUNT(*) AS total
        FROM rental_contracts r
        {where}
    """

    cursor = await db.execute(sql, values + [limit, offset])
    rows = await cursor.fetchall()
    cursor2 = await db.execute(sql_count, values)
    count_row = await cursor2.fetchone()

    return {
        "total": count_row["total"],
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": r["id"],
                "project": r["project"],
                "street": r["street"],
                "district": r["district"],
                "bedrooms": r["no_of_bedrooms"],
                "area_sqm_min": r["area_sqm_min"],
                "area_sqm_max": r["area_sqm_max"],
                "rent": r["rent"],
                "lease_year": r["lease_year"],
                "lease_month": r["lease_month"],
                "property_type": r["property_type"],
            }
            for r in rows
        ],
    }
