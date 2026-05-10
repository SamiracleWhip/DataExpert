import json
import os

import httpx

FASTAPI_BASE = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"

# Persistent client — reuses TCP connections across tool calls
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client

# Standard filter params accepted by all tools
_FILTER_PROPS = {
    "district": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Postal district codes to filter by, e.g. ['10', '15']. Leave empty for all districts.",
    },
    "bedrooms": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Bedroom counts: '1', '2', '3', '4', '5' for room counts, 'unknown' for unspecified. Leave empty for all.",
    },
    "property_type": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Property types: 'Non-landed Properties', 'Executive Condominium', 'Terrace House'. Leave empty for all.",
    },
    "date_from": {
        "type": "string",
        "description": "Start of date range in YYYY-MM format, e.g. '2024-01'.",
    },
    "date_to": {
        "type": "string",
        "description": "End of date range in YYYY-MM format, e.g. '2025-12'.",
    },
    "station": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Filter to buildings within 1km of these MRT/LRT station names, e.g. ['Orchard', 'City Hall'].",
    },
}

TOOL_DEFINITIONS = [
    {
        "name": "get_stats",
        "description": (
            "Get aggregate rental statistics: average, median, min, max rent plus contract and building counts. "
            "Use to answer questions about typical rent levels, price ranges, and market size."
        ),
        "input_schema": {
            "type": "object",
            "properties": _FILTER_PROPS,
            "required": [],
        },
    },
    {
        "name": "get_district_breakdown",
        "description": (
            "Get average rent per postal district, sorted highest to lowest. "
            "Use to compare districts, identify expensive vs affordable areas, or rank neighbourhoods."
        ),
        "input_schema": {
            "type": "object",
            "properties": _FILTER_PROPS,
            "required": [],
        },
    },
    {
        "name": "get_trends",
        "description": (
            "Get monthly average rent and price-per-sqm time series. "
            "Use to answer trend questions: is rent rising or falling, how has it changed over time. "
            "Set group_by_district=true to get separate series per district."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_FILTER_PROPS,
                "group_by_district": {
                    "type": "boolean",
                    "description": "Return one time series per district instead of an overall aggregate.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_buildings",
        "description": (
            "List buildings matching the filters with their average rent and nearest MRT. "
            "Use to find specific properties, list buildings in an area, or identify what's near an MRT station."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_FILTER_PROPS,
                "limit": {
                    "type": "integer",
                    "description": "Max buildings to return (default 20, max 50).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_deals",
        "description": (
            "Find buildings where the most recent month's average rent is significantly below their 12-month trailing average. "
            "Use to find current rental deals or price dips."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_FILTER_PROPS,
                "threshold_pct": {
                    "type": "number",
                    "description": "Minimum % below trailing average to qualify as a deal (default 10).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_building",
        "description": (
            "Search for buildings by name (partial match). "
            "Use when the user mentions a specific condo or building name to find its ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Building name to search for, e.g. 'Marina Bay Suites'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5).",
                },
            },
            "required": ["q"],
        },
    },
    {
        "name": "enrich_building",
        "description": (
            "Get detailed info for a specific building: nearest MRT and distance, "
            "number of schools within 1km, and average price per sqm. "
            "Use after search_building to get details on a specific property."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "building_id": {
                    "type": "integer",
                    "description": "Building ID (from search_building results).",
                },
            },
            "required": ["building_id"],
        },
    },
    {
        "name": "get_contracts",
        "description": (
            "Get individual rental contract records with details (rent, bedrooms, area, date, property). "
            "Use to show specific recent transactions or sample the raw data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_FILTER_PROPS,
                "limit": {
                    "type": "integer",
                    "description": "Number of records to return (default 10, max 50).",
                },
                "sort_by": {
                    "type": "string",
                    "description": "Sort field: 'lease_year' (default), 'rent', 'district'.",
                },
                "sort_dir": {
                    "type": "string",
                    "description": "Sort direction: 'desc' (default) or 'asc'.",
                },
            },
            "required": [],
        },
    },
]


def _build_params(tool_input: dict) -> dict:
    """Convert tool input dict to httpx params (handles list values)."""
    params: dict = {}
    for key, val in tool_input.items():
        if val is None:
            continue
        if isinstance(val, list):
            params[key] = val  # httpx serialises list as repeated params
        else:
            params[key] = val
    return params


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    try:
        return await _DISPATCH[tool_name](_get_http_client(), tool_input)
    except Exception as exc:
        return json.dumps({"error": str(exc), "tool": tool_name})


async def _get_stats(client: httpx.AsyncClient, inp: dict) -> str:
    r = await client.get(f"{FASTAPI_BASE}/api/stats", params=_build_params(inp))
    r.raise_for_status()
    return r.text


async def _get_district_breakdown(client: httpx.AsyncClient, inp: dict) -> str:
    r = await client.get(f"{FASTAPI_BASE}/api/stats/district-breakdown", params=_build_params(inp))
    r.raise_for_status()
    return r.text


async def _get_trends(client: httpx.AsyncClient, inp: dict) -> str:
    r = await client.get(f"{FASTAPI_BASE}/api/trends", params=_build_params(inp))
    r.raise_for_status()
    # Truncate to avoid huge payloads — return last 24 months
    data = r.json()
    if isinstance(data, list) and len(data) > 24:
        data = data[-24:]
    return json.dumps(data)


async def _get_buildings(client: httpx.AsyncClient, inp: dict) -> str:
    params = _build_params(inp)
    if "limit" not in params:
        params["limit"] = 20
    r = await client.get(f"{FASTAPI_BASE}/api/buildings", params=params)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        data = data[: params.get("limit", 20)]
    return json.dumps(data)


async def _get_deals(client: httpx.AsyncClient, inp: dict) -> str:
    r = await client.get(f"{FASTAPI_BASE}/api/stats/deals", params=_build_params(inp))
    r.raise_for_status()
    return r.text


async def _search_building(client: httpx.AsyncClient, inp: dict) -> str:
    params = {"q": inp["q"], "limit": inp.get("limit", 5)}
    r = await client.get(f"{FASTAPI_BASE}/api/buildings/search", params=params)
    r.raise_for_status()
    return r.text


async def _enrich_building(client: httpx.AsyncClient, inp: dict) -> str:
    r = await client.get(
        f"{FASTAPI_BASE}/api/buildings/enrich",
        params={"building_id": inp["building_id"]},
    )
    r.raise_for_status()
    return r.text


async def _get_contracts(client: httpx.AsyncClient, inp: dict) -> str:
    params = _build_params(inp)
    params.setdefault("limit", 10)
    params.setdefault("sort_by", "lease_year")
    params.setdefault("sort_dir", "desc")
    r = await client.get(f"{FASTAPI_BASE}/api/contracts", params=params)
    r.raise_for_status()
    return r.text


_DISPATCH = {
    "get_stats": _get_stats,
    "get_district_breakdown": _get_district_breakdown,
    "get_trends": _get_trends,
    "get_buildings": _get_buildings,
    "get_deals": _get_deals,
    "search_building": _search_building,
    "enrich_building": _enrich_building,
    "get_contracts": _get_contracts,
}
