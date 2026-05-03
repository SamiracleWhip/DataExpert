import aiosqlite
from fastapi import APIRouter, Depends
from database import get_db
from enrichment import mrt_lines_geojson, mrt_stops_geojson

router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("")
async def list_stations(db: aiosqlite.Connection = Depends(get_db)):
    """All MRT/LRT stations that have at least one building within 1km, sorted by name."""
    cursor = await db.execute("""
        SELECT station_name, COUNT(DISTINCT building_id) AS building_count
        FROM building_mrt_proximity
        GROUP BY station_name
        ORDER BY station_name
    """)
    rows = await cursor.fetchall()
    return [{"name": r["station_name"], "building_count": r["building_count"]} for r in rows]


@router.get("/lines")
async def mrt_lines():
    """GeoJSON FeatureCollection of MRT/LRT lines with official colours."""
    return mrt_lines_geojson()


@router.get("/stops")
async def mrt_stops():
    """GeoJSON FeatureCollection of MRT/LRT station stops (unique, coloured by primary line)."""
    return mrt_stops_geojson()
