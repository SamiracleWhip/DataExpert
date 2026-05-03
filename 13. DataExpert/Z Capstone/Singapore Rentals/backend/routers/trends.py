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

    if group_by_building:
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
        sql = f"""
            SELECT
                r.lease_year,
                r.lease_month,
                ROUND(AVG(r.rent), 0) AS avg_rent,
                {_PSM},
                COUNT(*) AS contracts
            FROM rental_contracts r
            {where}
            GROUP BY r.lease_year, r.lease_month
            ORDER BY r.lease_year, r.lease_month
        """

    cursor = await db.execute(sql, values)
    rows = await cursor.fetchall()

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
            "avg_psm": r["avg_psm"],
            "contracts": r["contracts"],
        }
        for r in rows
    ]
