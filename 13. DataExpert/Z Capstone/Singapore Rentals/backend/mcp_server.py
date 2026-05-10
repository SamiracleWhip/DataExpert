"""
Standalone MCP server for Shedza Singapore Rentals.

Exposes the same 8 data tools as the in-app RAG assistant, calling the running
FastAPI server via HTTP. Requires the FastAPI server to be running on port 8000.

Usage:
    python mcp_server.py

Claude Desktop config (~/.claude/claude_desktop_config.json or
~/Library/Application Support/Claude/claude_desktop_config.json):
    {
        "mcpServers": {
            "shedza": {
                "command": "python",
                "args": ["/path/to/backend/mcp_server.py"]
            }
        }
    }
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# The MCP server communicates via stdio — never print to stdout.
# Use sys.stderr for any debug output.

FASTAPI_BASE = "http://127.0.0.1:8000"

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP(
    "Casota Singapore Rentals",
    instructions=(
        "Tools for querying Singapore private residential rental data (2022–2026). "
        "336,751 contracts across 4,157 buildings in 28 postal districts. "
        "Data source: URA stamp duty records. Does NOT include HDB flats."
    ),
)


def _p(**kwargs) -> dict:
    """Build httpx params dict, dropping None and False values."""
    return {k: v for k, v in kwargs.items() if v is not None and v is not False and v != []}


async def _get(path: str, params: dict) -> str:
    r = await _get_http_client().get(f"{FASTAPI_BASE}{path}", params=params)
    r.raise_for_status()
    return r.text


@mcp.tool()
async def get_rental_stats(
    district: list[str] | None = None,
    bedrooms: list[str] | None = None,
    property_type: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    station: list[str] | None = None,
) -> str:
    """
    Get aggregate rental statistics: average, median, min, max rent and contract/building counts.

    district: postal district codes e.g. ['10', '15'] — leave empty for all
    bedrooms: '1','2','3','4','5' or 'unknown' — leave empty for all
    property_type: 'Non-landed Properties', 'Executive Condominium', 'Terrace House'
    date_from / date_to: YYYY-MM format e.g. '2024-01'
    station: MRT/LRT station names e.g. ['Orchard'] — filters to buildings within 1km
    """
    return await _get("/api/stats", _p(
        district=district, bedrooms=bedrooms, property_type=property_type,
        date_from=date_from, date_to=date_to, station=station,
    ))


@mcp.tool()
async def get_district_breakdown(
    bedrooms: list[str] | None = None,
    property_type: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """
    Get average rent per postal district, sorted highest to lowest.
    Use to compare districts or identify expensive vs affordable areas.
    """
    return await _get("/api/stats/district-breakdown", _p(
        bedrooms=bedrooms, property_type=property_type,
        date_from=date_from, date_to=date_to,
    ))


@mcp.tool()
async def get_rental_trends(
    district: list[str] | None = None,
    bedrooms: list[str] | None = None,
    property_type: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_by_district: bool = False,
) -> str:
    """
    Get monthly average rent and price-per-sqm time series.
    Set group_by_district=True for separate series per district.
    Returns at most the last 24 months to keep response size reasonable.
    """
    data = json.loads(await _get("/api/trends", _p(
        district=district, bedrooms=bedrooms, property_type=property_type,
        date_from=date_from, date_to=date_to,
        group_by_district=group_by_district or None,
    )))
    if isinstance(data, list) and len(data) > 24:
        data = data[-24:]
    return json.dumps(data)


@mcp.tool()
async def find_buildings(
    district: list[str] | None = None,
    station: list[str] | None = None,
    bedrooms: list[str] | None = None,
    property_type: list[str] | None = None,
    limit: int = 20,
) -> str:
    """
    List buildings matching filters with their average rent and nearest MRT station.
    Useful for finding condos in a specific area or near an MRT station.
    """
    return await _get("/api/buildings", _p(
        district=district, station=station, bedrooms=bedrooms,
        property_type=property_type, limit=limit,
    ))


@mcp.tool()
async def find_rental_deals(
    district: list[str] | None = None,
    bedrooms: list[str] | None = None,
    threshold_pct: float = 10.0,
) -> str:
    """
    Find buildings where the most recent month's average rent is significantly
    below their 12-month trailing average — i.e., potential rental deals.
    threshold_pct: minimum % below trailing average (default 10%).
    """
    return await _get("/api/stats/deals", _p(
        district=district, bedrooms=bedrooms, threshold_pct=threshold_pct,
    ))


@mcp.tool()
async def search_building_by_name(name: str, limit: int = 5) -> str:
    """
    Search for buildings by name (partial match). Returns building IDs, names, and streets.
    Use before enrich_building to find a building's ID.
    """
    return await _get("/api/buildings/search", {"q": name, "limit": limit})


@mcp.tool()
async def get_building_details(building_id: int) -> str:
    """
    Get enriched details for a specific building: nearest MRT and walking distance,
    schools within 1km, and average price per sqm.
    Use the ID from search_building_by_name.
    """
    return await _get("/api/buildings/enrich", {"building_id": building_id})


@mcp.tool()
async def get_rental_contracts(
    district: list[str] | None = None,
    bedrooms: list[str] | None = None,
    property_type: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10,
    sort_by: str = "lease_year",
    sort_dir: str = "desc",
) -> str:
    """
    Get individual rental contract records with full details (rent, bedrooms, area, date).
    Useful for showing specific recent transactions.
    sort_by: 'lease_year' (default), 'rent', 'district'
    sort_dir: 'desc' (default) or 'asc'
    """
    return await _get("/api/contracts", _p(
        district=district, bedrooms=bedrooms, property_type=property_type,
        date_from=date_from, date_to=date_to,
        limit=limit, sort_by=sort_by, sort_dir=sort_dir,
    ))


if __name__ == "__main__":
    mcp.run()
