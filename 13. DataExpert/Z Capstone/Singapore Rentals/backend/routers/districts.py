import json
import math
import ssl
import urllib.request
import aiosqlite
from fastapi import APIRouter, Depends
from database import get_db

router = APIRouter(prefix="/api/districts", tags=["districts"])

# ── convex hull ────────────────────────────────────────────────────────────────

def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

def _convex_hull(pts: list[tuple[float, float]]) -> list[list[float]]:
    """Graham scan. Returns closed polygon [[lng,lat],...] in GeoJSON order."""
    unique = list(set(pts))
    if len(unique) < 3:
        # Degenerate: return a small circle approximation around centroid
        cx = sum(p[0] for p in unique) / len(unique)
        cy = sum(p[1] for p in unique) / len(unique)
        r = 0.02
        n = 12
        circle = [[cx + r * math.cos(2 * math.pi * i / n),
                   cy + r * math.sin(2 * math.pi * i / n)] for i in range(n)]
        circle.append(circle[0])
        return circle

    pivot = min(unique, key=lambda p: (p[1], p[0]))

    def angle_key(p):
        return math.atan2(p[1] - pivot[1], p[0] - pivot[0])

    sorted_pts = sorted(unique, key=angle_key)
    hull: list[tuple[float, float]] = []
    for p in sorted_pts:
        while len(hull) >= 2 and _cross(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)

    closed = [[p[0], p[1]] for p in hull]
    closed.append(closed[0])
    return closed


def _expand_hull(hull: list[list[float]], margin: float = 0.005) -> list[list[float]]:
    """Push each vertex outward from the centroid by `margin` degrees."""
    cx = sum(p[0] for p in hull[:-1]) / (len(hull) - 1)
    cy = sum(p[1] for p in hull[:-1]) / (len(hull) - 1)
    expanded = []
    for p in hull[:-1]:
        dx, dy = p[0] - cx, p[1] - cy
        dist = math.hypot(dx, dy) or 1e-9
        expanded.append([p[0] + dx / dist * margin, p[1] + dy / dist * margin])
    expanded.append(expanded[0])
    return expanded


# ── module-level caches ────────────────────────────────────────────────────────

_boundaries_cache: dict | None = None
_outline_cache: dict | None = None
_landmass_cache: dict | None = None

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ── routes ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_districts(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute(
        "SELECT district, area_name FROM districts ORDER BY CAST(district AS INTEGER)"
    )
    rows = await cursor.fetchall()
    return [{"district": r["district"], "area_name": r["area_name"]} for r in rows]


@router.get("/boundaries")
async def district_boundaries(db: aiosqlite.Connection = Depends(get_db)):
    global _boundaries_cache
    if _boundaries_cache is not None:
        return _boundaries_cache

    # Pull one (lng, lat) per unique building per district
    cursor = await db.execute("""
        SELECT rc.district, b.lng, b.lat
        FROM buildings b
        JOIN (
            SELECT DISTINCT building_id, district
            FROM rental_contracts
            WHERE district IS NOT NULL
        ) rc ON rc.building_id = b.id
        WHERE b.lat IS NOT NULL AND b.lng IS NOT NULL
    """)
    rows = await cursor.fetchall()

    # Group points by district
    from collections import defaultdict
    pts_by_district: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        pts_by_district[row["district"]].append((row["lng"], row["lat"]))

    # Fetch area names for tooltip
    cursor2 = await db.execute("SELECT district, area_name FROM districts")
    area_names = {r["district"]: r["area_name"] for r in await cursor2.fetchall()}

    features = []
    for district, pts in sorted(pts_by_district.items()):
        hull = _convex_hull(pts)
        hull = _expand_hull(hull, margin=0.008)
        features.append({
            "type": "Feature",
            "properties": {
                "district": district,
                "area_name": area_names.get(district, ""),
            },
            "geometry": {"type": "Polygon", "coordinates": [hull]},
        })

    _boundaries_cache = {"type": "FeatureCollection", "features": features}
    return _boundaries_cache


@router.get("/outline")
async def singapore_outline():
    """Singapore land boundary from OSM Nominatim (relation 536780), cached."""
    global _outline_cache
    if _outline_cache is not None:
        return _outline_cache

    url = (
        "https://nominatim.openstreetmap.org/search"
        "?q=Singapore&format=geojson&polygon_geojson=1&featuretype=country&limit=1"
    )
    headers = {
        "User-Agent": "SingaporeRentalsDashboard/1.0 (educational project)",
        "Accept-Language": "en",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read())
        # Nominatim returns a FeatureCollection; grab the first feature's geometry
        features = data.get("features", [])
        if features:
            _outline_cache = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": features[0]["geometry"],
                }],
            }
            return _outline_cache
    except Exception:
        pass

    # Fallback: rough Singapore main-island polygon
    _outline_cache = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [103.6350, 1.2650], [103.6750, 1.2400], [103.7500, 1.2200],
                    [103.8200, 1.2200], [103.8800, 1.2500], [103.9200, 1.2850],
                    [103.9900, 1.3200], [104.0350, 1.3600], [104.0300, 1.4000],
                    [103.9800, 1.4400], [103.9200, 1.4600], [103.8500, 1.4650],
                    [103.7800, 1.4500], [103.7200, 1.4100], [103.6700, 1.3700],
                    [103.6350, 1.3200], [103.6350, 1.2650],
                ]],
            },
        }],
    }
    return _outline_cache


@router.get("/landmass")
async def singapore_landmass():
    """Singapore main island coastline from OSM Nominatim, cached."""
    global _landmass_cache
    if _landmass_cache is not None:
        return _landmass_cache

    url = (
        "https://nominatim.openstreetmap.org/search"
        "?q=Singapore+Island&format=geojson&polygon_geojson=1&limit=1"
    )
    headers = {
        "User-Agent": "SingaporeRentalsDashboard/1.0 (educational project)",
        "Accept-Language": "en",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read())
        features = data.get("features", [])
        if features:
            _landmass_cache = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": features[0]["geometry"],
                }],
            }
            return _landmass_cache
    except Exception:
        pass

    return {"type": "FeatureCollection", "features": []}
