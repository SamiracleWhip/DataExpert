import aiosqlite
from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import get_db, build_rental_filter

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(
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

    sql_agg = f"""
        SELECT
            ROUND(AVG(r.rent), 0) AS avg_rent,
            MIN(r.rent) AS min_rent,
            MAX(r.rent) AS max_rent,
            COUNT(*) AS total_contracts,
            COUNT(DISTINCT r.building_id) AS total_buildings
        FROM rental_contracts r
        {where}
    """

    sql_median = f"""
        SELECT AVG(rent) AS median_rent
        FROM (
            SELECT r.rent
            FROM rental_contracts r
            {where}
            ORDER BY r.rent
            LIMIT 2 - (SELECT COUNT(*) FROM rental_contracts r {where}) % 2
            OFFSET (SELECT (COUNT(*) - 1) / 2 FROM rental_contracts r {where})
        )
    """

    cursor = await db.execute(sql_agg, values)
    agg = await cursor.fetchone()

    cursor2 = await db.execute(sql_median, values * 3)
    med = await cursor2.fetchone()

    return {
        "avg_rent": agg["avg_rent"],
        "median_rent": round(med["median_rent"]) if med and med["median_rent"] else None,
        "min_rent": agg["min_rent"],
        "max_rent": agg["max_rent"],
        "total_contracts": agg["total_contracts"],
        "total_buildings": agg["total_buildings"],
    }


@router.get("/district-breakdown")
async def district_breakdown(
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

    sql = f"""
        SELECT
            r.district,
            d.area_name,
            ROUND(AVG(r.rent), 0) AS avg_rent,
            COUNT(*) AS contracts
        FROM rental_contracts r
        LEFT JOIN districts d ON d.district = r.district
        {where}
        GROUP BY r.district
        ORDER BY avg_rent DESC
    """

    cursor = await db.execute(sql, values)
    rows = await cursor.fetchall()

    return [
        {
            "district": r["district"],
            "area_name": r["area_name"],
            "avg_rent": r["avg_rent"],
            "contracts": r["contracts"],
        }
        for r in rows
    ]


@router.get("/histogram")
async def rent_histogram(
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
    bucket_size: int = 500,
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

    sql = f"""
        SELECT
            (r.rent / ?) * ? AS bucket_start,
            COUNT(*) AS count
        FROM rental_contracts r
        {where}
        GROUP BY bucket_start
        ORDER BY bucket_start
    """

    cursor = await db.execute(sql, [bucket_size, bucket_size] + values)
    rows = await cursor.fetchall()

    return [{"bucket_start": r["bucket_start"], "count": r["count"]} for r in rows]


@router.get("/deals")
async def deal_finder(
    district: list[str] = Query(default=[]),
    station: list[str] = Query(default=[]),
    bedrooms: list[str] = Query(default=[]),
    property_type: list[str] = Query(default=[]),
    area_min: Optional[int] = None,
    area_max: Optional[int] = None,
    area_unit: str = "sqm",
    building_id: list[int] = Query(default=[]),
    threshold_pct: float = 10.0,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Buildings where most recent month avg rent is >= threshold_pct below 12-month trailing avg."""
    params = dict(
        district=district or None,
        station=station or None,
        bedrooms=bedrooms or None,
        property_type=property_type or None,
        area_min=area_min,
        area_max=area_max,
        area_unit=area_unit,
        building_id=building_id or None,
    )
    where, values = build_rental_filter(params, table_alias="r")

    cur = await db.execute(
        "SELECT MAX(lease_year * 100 + lease_month) AS latest FROM rental_contracts"
    )
    row = await cur.fetchone()
    latest_ym = row["latest"]
    latest_year = latest_ym // 100
    latest_month = latest_ym % 100

    sql = f"""
        WITH all_data AS (
            SELECT r.building_id, r.rent, r.lease_year, r.lease_month
            FROM rental_contracts r
            {where}
        ),
        recent AS (
            SELECT building_id, AVG(rent) AS recent_avg
            FROM all_data
            WHERE lease_year = ? AND lease_month = ?
            GROUP BY building_id
        ),
        trailing AS (
            SELECT building_id, AVG(rent) AS trailing_avg
            FROM all_data
            WHERE (lease_year * 100 + lease_month) > (? * 100 + ?) - 100
            GROUP BY building_id
        )
        SELECT
            b.id,
            b.project,
            b.street,
            MAX(r.district) AS district,
            recent.recent_avg,
            trailing.trailing_avg,
            ROUND((trailing.trailing_avg - recent.recent_avg) / trailing.trailing_avg * 100, 1) AS pct_below
        FROM recent
        JOIN trailing ON trailing.building_id = recent.building_id
        JOIN buildings b ON b.id = recent.building_id
        JOIN rental_contracts r ON r.building_id = b.id
        WHERE recent.recent_avg < trailing.trailing_avg * (1 - ? / 100.0)
        GROUP BY b.id
        ORDER BY pct_below DESC
        LIMIT 50
    """

    deal_values = values + [latest_year, latest_month, latest_year, latest_month, threshold_pct]
    cursor = await db.execute(sql, deal_values)
    rows = await cursor.fetchall()

    return [
        {
            "id": r["id"],
            "project": r["project"],
            "street": r["street"],
            "district": r["district"],
            "recent_avg": round(r["recent_avg"]),
            "trailing_avg": round(r["trailing_avg"]),
            "pct_below": r["pct_below"],
        }
        for r in rows
    ]
