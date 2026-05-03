import aiosqlite
from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import get_db, build_rental_filter
from enrichment import nearest_mrt, schools_within

router = APIRouter(prefix="/api/buildings", tags=["buildings"])


@router.get("/search")
async def search_buildings(
    q: str = "",
    limit: int = 10,
    db: aiosqlite.Connection = Depends(get_db),
):
    if not q.strip():
        return []
    cursor = await db.execute(
        """
        SELECT id, project, street
        FROM buildings
        WHERE LOWER(project) LIKE LOWER(?)
        ORDER BY project
        LIMIT ?
        """,
        [f"%{q.strip()}%", limit],
    )
    rows = await cursor.fetchall()
    return [{"id": r["id"], "project": r["project"], "street": r["street"]} for r in rows]


@router.get("/recommend")
async def recommend_buildings(
    building_id: int,
    exclude: list[int] = Query(default=[]),
    limit: int = 5,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return buildings in the same district with the closest avg rent to the reference building."""
    # Get reference building's district + recent avg rent (last 2 years)
    ref_cur = await db.execute(
        """
        SELECT r.district, AVG(r.rent) AS ref_avg
        FROM rental_contracts r
        WHERE r.building_id = ?
          AND r.lease_year >= 2024
        GROUP BY r.district
        LIMIT 1
        """,
        [building_id],
    )
    ref = await ref_cur.fetchone()
    if not ref or not ref["ref_avg"]:
        return []

    district = ref["district"]
    ref_avg = ref["ref_avg"]
    low = ref_avg * 0.65
    high = ref_avg * 1.35

    exclude_ids = list(set(exclude + [building_id]))
    excl_placeholders = ",".join("?" * len(exclude_ids))

    cur = await db.execute(
        f"""
        SELECT
            b.id,
            b.project,
            b.street,
            ROUND(AVG(r.rent), 0) AS avg_rent,
            ABS(AVG(r.rent) - ?) AS rent_diff
        FROM rental_contracts r
        JOIN buildings b ON b.id = r.building_id
        WHERE r.district = ?
          AND r.building_id NOT IN ({excl_placeholders})
          AND r.lease_year >= 2024
          AND UPPER(b.project) NOT LIKE '%HOUSING DEVELOPMENT%'
          AND UPPER(b.project) NOT LIKE 'STRATA LANDED%'
          AND LENGTH(TRIM(b.project)) > 4
        GROUP BY b.id
        HAVING avg_rent BETWEEN ? AND ?
        ORDER BY rent_diff ASC
        LIMIT ?
        """,
        [ref_avg, district, *exclude_ids, low, high, limit],
    )
    rows = await cur.fetchall()
    return [
        {
            "id": r["id"],
            "project": r["project"],
            "street": r["street"],
            "avg_rent": r["avg_rent"],
        }
        for r in rows
    ]


@router.get("/enrich")
async def enrich_building(
    building_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return MRT distance, nearby schools, and PSF for a building."""
    cur = await db.execute(
        "SELECT lat, lng FROM buildings WHERE id = ?", [building_id]
    )
    row = await cur.fetchone()
    if not row or not row["lat"]:
        return {"building_id": building_id, "error": "no coordinates"}

    lat, lng = row["lat"], row["lng"]
    mrt = nearest_mrt(lat, lng)
    nearby = schools_within(lat, lng, radius_m=1000)

    # Avg PSF from recent data
    psf_cur = await db.execute(
        """
        SELECT ROUND(AVG(
            CASE WHEN area_sqm_min > 0 AND area_sqm_max > 0
            THEN rent * 1.0 / ((area_sqm_min + area_sqm_max) / 2.0)
            ELSE NULL END
        ), 1) AS avg_psm
        FROM rental_contracts
        WHERE building_id = ? AND lease_year >= 2023
        """,
        [building_id],
    )
    psf_row = await psf_cur.fetchone()

    return {
        "building_id": building_id,
        "nearest_mrt": mrt["station"],
        "mrt_distance_m": mrt["distance_m"],
        "schools_1km": len(nearby),
        "school_names": [s["name"] for s in nearby[:5]],
        "avg_psm": psf_row["avg_psm"] if psf_row else None,
        "year_built": None,  # not available from free public sources
    }


@router.get("")
async def list_buildings(
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

    # Inject the lat/lng guard — append to existing WHERE or start one
    lat_guard = "b.lat IS NOT NULL AND b.lng IS NOT NULL"
    if where:
        sql_where = where + f" AND {lat_guard}"
    else:
        sql_where = f"WHERE {lat_guard}"

    sql = f"""
        SELECT
            b.id,
            b.project,
            b.street,
            b.lat,
            b.lng,
            ROUND(AVG(r.rent), 0) AS avg_rent,
            COUNT(*) AS contract_count
        FROM buildings b
        JOIN rental_contracts r ON r.building_id = b.id
        {sql_where}
        GROUP BY b.id
    """

    cursor = await db.execute(sql, values)
    rows = await cursor.fetchall()

    return [
        {
            "id": r["id"],
            "project": r["project"],
            "street": r["street"],
            "lat": r["lat"],
            "lng": r["lng"],
            "avg_rent": r["avg_rent"],
            "contract_count": r["contract_count"],
        }
        for r in rows
    ]
