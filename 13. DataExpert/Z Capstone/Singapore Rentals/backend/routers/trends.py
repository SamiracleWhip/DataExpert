import aiosqlite
from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import get_db, build_rental_filter

router = APIRouter(prefix="/api/trends", tags=["trends"])

# PSM: rent ÷ midpoint of integer area columns
_PSM = """ROUND(AVG(
    CASE WHEN r.area_sqm_min > 0 AND r.area_sqm_max > 0
    THEN r.rent * 1.0 / ((r.area_sqm_min + r.area_sqm_max) / 2.0)
    ELSE NULL END
), 1) AS avg_psm"""


@router.get("")
async def get_trends(
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
    group_by_district: bool = False,
    group_by_building: bool = False,
    group_by_bedrooms: bool = False,
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

    if group_by_bedrooms:
        sql = f"""
            WITH ordered AS (
                SELECT
                    r.lease_year, r.lease_month,
                    COALESCE(r.no_of_bedrooms, 'unknown') AS bedrooms,
                    r.rent,
                    ROW_NUMBER() OVER (PARTITION BY r.lease_year, r.lease_month, r.no_of_bedrooms ORDER BY r.rent) AS rn,
                    COUNT(*) OVER (PARTITION BY r.lease_year, r.lease_month, r.no_of_bedrooms) AS cnt
                FROM rental_contracts r
                {where}
            )
            SELECT
                lease_year, lease_month, bedrooms,
                ROUND(AVG(rent), 0) AS avg_rent,
                ROUND(AVG(CASE WHEN rn IN ((cnt + 1) / 2, (cnt + 2) / 2) THEN CAST(rent AS REAL) ELSE NULL END), 0) AS median_rent,
                COUNT(*) AS contracts
            FROM ordered
            GROUP BY lease_year, lease_month, bedrooms
            ORDER BY lease_year, lease_month, bedrooms
        """
    elif group_by_building:
        sql = f"""
            SELECT
                r.building_id,
                b.project,
                r.lease_year,
                r.lease_month,
                ROUND(AVG(r.rent), 0) AS avg_rent,
                {_PSM},
                COUNT(*) AS contracts
            FROM rental_contracts r
            JOIN buildings b ON b.id = r.building_id
            {where}
            GROUP BY r.building_id, r.lease_year, r.lease_month
            ORDER BY r.building_id, r.lease_year, r.lease_month
        """
    elif group_by_district:
        sql = f"""
            SELECT
                r.lease_year,
                r.lease_month,
                r.district,
                ROUND(AVG(r.rent), 0) AS avg_rent,
                {_PSM},
                COUNT(*) AS contracts
            FROM rental_contracts r
            {where}
            GROUP BY r.lease_year, r.lease_month, r.district
            ORDER BY r.lease_year, r.lease_month, r.district
        """
    else:
        # CTE with window functions to compute median alongside avg in one pass
        sql = f"""
            WITH ordered AS (
                SELECT
                    r.lease_year, r.lease_month, r.rent,
                    r.area_sqm_min, r.area_sqm_max,
                    ROW_NUMBER() OVER (PARTITION BY r.lease_year, r.lease_month ORDER BY r.rent) AS rn,
                    COUNT(*) OVER (PARTITION BY r.lease_year, r.lease_month) AS cnt
                FROM rental_contracts r
                {where}
            )
            SELECT
                lease_year,
                lease_month,
                ROUND(AVG(rent), 0) AS avg_rent,
                ROUND(AVG(CASE WHEN rn IN ((cnt + 1) / 2, (cnt + 2) / 2) THEN CAST(rent AS REAL) ELSE NULL END), 0) AS median_rent,
                ROUND(AVG(
                    CASE WHEN area_sqm_min > 0 AND area_sqm_max > 0
                    THEN rent * 1.0 / ((area_sqm_min + area_sqm_max) / 2.0)
                    ELSE NULL END
                ), 1) AS avg_psm,
                COUNT(*) AS contracts
            FROM ordered
            GROUP BY lease_year, lease_month
            ORDER BY lease_year, lease_month
        """

    cursor = await db.execute(sql, values)
    rows = await cursor.fetchall()

    if group_by_bedrooms:
        return [
            {
                "year": r["lease_year"],
                "month": r["lease_month"],
                "bedrooms": r["bedrooms"],
                "avg_rent": r["avg_rent"],
                "median_rent": r["median_rent"],
                "contracts": r["contracts"],
            }
            for r in rows
        ]

    if group_by_building:
        return [
            {
                "building_id": r["building_id"],
                "project": r["project"],
                "year": r["lease_year"],
                "month": r["lease_month"],
                "avg_rent": r["avg_rent"],
                "avg_psm": r["avg_psm"],
                "contracts": r["contracts"],
            }
            for r in rows
        ]

    if group_by_district:
        return [
            {
                "year": r["lease_year"],
                "month": r["lease_month"],
                "district": r["district"],
                "avg_rent": r["avg_rent"],
                "avg_psm": r["avg_psm"],
                "contracts": r["contracts"],
            }
            for r in rows
        ]

    return [
        {
            "year": r["lease_year"],
            "month": r["lease_month"],
            "avg_rent": r["avg_rent"],
            "median_rent": r["median_rent"],
            "avg_psm": r["avg_psm"],
            "contracts": r["contracts"],
        }
        for r in rows
    ]
