# Singapore Rental Intelligence Dashboard — Build Summary

---

## Project Overview

A geospatial dashboard visualising private residential rental prices across Singapore using official URA (Urban Redevelopment Authority) transaction data. Users can explore rental prices by district, track trends over time per building and zone, and filter by property parameters. A Claude-powered assistant will answer natural language queries about the data.

**Data source:** URA Data Service API — private residential rental contracts submitted to IRAS for Stamp Duty assessment.

---

## Step 1: URA API Setup & Historical Data Pull

### 1.1 Registration

Registered for a URA API access key at:
`https://eservice.ura.gov.sg/maps/api/reg.html`

Upon approval, URA emails an **Access Key** (a permanent credential). This was stored in a `.env` file:

```
URA_ACCESS_KEY=your_access_key_here
```

### 1.2 Protecting the Access Key

A `.gitignore` was created immediately to prevent the `.env` file from being accidentally committed to git. The git repository root is at `/Users/samirbhojwani/Documents`, covering the entire Documents folder, making this protection critical.

`.gitignore` covers: `.env`, `__pycache__/`, `*.pyc`, `.DS_Store`, `*.db`, `*.sqlite`, `.venv/`, `venv/`

### 1.3 How the URA API Works

The URA API uses a **two-step authentication** system:

1. **Access Key** — permanent, received by email, stored in `.env`
2. **Token** — generated fresh each day using the Access Key, valid for that day only

**Token generation endpoint:**
```
GET https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1
Header: AccessKey: <your_access_key>
```

**Data retrieval endpoint:**
```
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Rental&refPeriod=25q1
Headers: AccessKey: <your_access_key>
         Token: <today's_token>
```

`refPeriod` is in `yyqq` format — e.g. `25q1` = 2025 Q1.

### 1.4 Technical Quirks

Two issues were discovered when calling the API from Python:

1. **Self-signed SSL certificate** — URA's server uses a self-signed certificate. Fixed by setting `verify=False` in requests and suppressing the warning with `urllib3.disable_warnings()`.
2. **Bot detection** — URA's server blocks Python's default User-Agent. Fixed by setting `User-Agent: curl/8.4.0` in all request headers.

### 1.5 Data Scope Decision

**Excluded property types:** `Semi-Detached House` and `Detached House` were excluded upstream in the fetch script at the user's request. These are landed private housing not relevant to the rental intelligence use case.

**Kept property types:**
| Type | Share |
|---|---|
| Non-landed Properties (condos/apartments) | 92.1% |
| Terrace House | 2.8% |
| Executive Condominium | 2.3% |

**Not included:** HDB flats — this is a URA dataset covering private residential properties only. HDB data is managed separately by the HDB agency.

**Bedroom data:** 13.6% of contracts have `"NA"` for number of bedrooms. This is expected — the URA API notes bedroom info is not always provided. These records are stored with `NULL` in the database (not the string "NA") for cleaner SQL filtering.

### 1.6 The Fetch Script (`fetch_historical.py`)

Pulls all quarters from 2022 Q1 to 2026 Q1 (17 quarters total), applies the property type filter, and saves to `raw_rental_contracts_all.json`.

**Quarters covered:** `22q1` through `26q1`

**Output structure:**
```json
{
  "22q1": [ { "project": "...", "street": "...", "x": "...", "y": "...", "rental": [...] } ],
  "22q2": [ ... ],
  ...
}
```

Each rental contract contains: `leaseDate` (mmyy format), `propertyType`, `district`, `areaSqft`, `areaSqm`, `noOfBedRoom`, `rent`.

**Results:**
- 17 quarters fetched
- 43,220 project-level records (before deduplication)
- Saved to `raw_rental_contracts_all.json`

---

## Step 2: SQLite Database

### 2.1 Why SQLite

SQLite was chosen for simplicity — no server setup required, queryable with standard SQL. After deduplication, the dataset contains ~336,000 unique contracts across 4,230 buildings. At ~20,000 new unique contracts per quarter, even 5 years of future growth keeps the database well under 1 million rows — well within SQLite's practical limits. File size: 56.5 MB.

### 2.2 Schema

**`districts`** — static lookup table mapping district codes to area names
```sql
CREATE TABLE districts (
    district  TEXT PRIMARY KEY,   -- e.g. "10"
    area_name TEXT NOT NULL        -- e.g. "Ardmore, Bukit Timah, Holland Road, Tanglin"
);
```

28 Singapore postal districts (D01–D28) are seeded at load time.

**`buildings`** — one row per unique property
```sql
CREATE TABLE buildings (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    street  TEXT NOT NULL,
    x       REAL,   -- SVY21 x coordinate (from URA)
    y       REAL,   -- SVY21 y coordinate (from URA)
    lat     REAL,   -- WGS84 latitude (added in Step 3)
    lng     REAL,   -- WGS84 longitude (added in Step 3)
    UNIQUE(project, street)
);
```

**`rental_contracts`** — one row per unique rental contract
```sql
CREATE TABLE rental_contracts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id    INTEGER NOT NULL REFERENCES buildings(id),
    lease_year     INTEGER NOT NULL,
    lease_month    INTEGER NOT NULL,
    property_type  TEXT,
    district       TEXT REFERENCES districts(district),
    area_sqft      TEXT,    -- stored as range string e.g. "1000-1100"
    area_sqm       TEXT,    -- stored as range string e.g. "100-110"
    no_of_bedrooms TEXT,    -- NULL where URA did not provide bedroom info
    rent           INTEGER NOT NULL,
    UNIQUE(building_id, lease_year, lease_month, property_type,
           district, area_sqft, no_of_bedrooms, rent)
);
```

Indexes are created on `building_id`, `district`, `lease_year/month`, and `no_of_bedrooms` for query performance.

### 2.3 Deduplication

The URA API returns up to 5 years of history per quarter call. This means the same rental contract appears in multiple quarters. Deduplication is handled via the `UNIQUE` constraint on `rental_contracts` — duplicate inserts are silently ignored using `INSERT OR IGNORE`.

**Deduplication results:**
- Raw contracts across all quarters: 367,497
- Unique contracts loaded: 336,751
- Duplicates skipped: 30,746

### 2.4 Load Script (`load_to_sqlite.py`)

Reads `raw_rental_contracts_all.json`, creates the database, seeds districts, and loads all data. `leaseDate` (mmyy format e.g. `"0125"`) is parsed into separate `lease_year` (2025) and `lease_month` (1) columns.

**Final database contents:**
| Table | Rows |
|---|---|
| districts | 28 |
| buildings | 4,230 |
| rental_contracts | 336,751 |

---

## Step 3: Geocoding Buildings

The URA API provides building coordinates in **SVY21 format** — Singapore's local projected coordinate system. These need to be converted to standard **WGS84 lat/lng** for use on web maps.

### 3.1 Strategy

Two-step approach:

1. **SVY21 → WGS84 conversion** for the 4,099 buildings that already have URA coordinates — done mathematically using the `pyproj` library (EPSG:3414 → EPSG:4326). Instant, no API calls needed.
2. **OneMap API geocoding** for the 131 buildings with missing URA coordinates — search by project name + street using Singapore's official geocoding service at `https://www.onemap.gov.sg/api/common/elastic/search`.

### 3.2 OneMap API Note

The OneMap API returns results without authentication but includes a warning: `"Authentication token missing. Please create an account and generate or renew your API Token."` This is a soft warning — results are valid. For future re-runs, registering for a free OneMap account at developers.onemap.sg is recommended in case they enforce authentication.

### 3.3 Results

| Method | Buildings |
|---|---|
| SVY21 conversion | 4,099 |
| OneMap geocoded | 58 |
| Not geocoded | 73 |
| **Total geocoded** | **4,157 (98.3%)** |

The 73 ungeocodable buildings are generic entries like `"LANDED HOUSING DEVELOPMENT"` with no specific project name — OneMap has nothing to search against. These are a negligible fraction and will simply not appear on the map.

**Coordinate validation:** All lat/lng values fall within Singapore's geographic bounds (lat: 1.24–1.46, lng: 103.69–103.98). ✅

Geocoding script: `geocode_buildings.py`

---

## Current File Structure

```
Singapore Rentals/
├── .claude/
│   └── commands/
│       └── refresh.md            # /refresh slash command — runs refresh.py
├── .env                          # URA access key (git-ignored)
├── .gitignore                    # Protects .env, *.db, etc.
├── API Docs.docx                 # Original URA API email attachment
├── ura.md                        # URA API documentation (copied from browser)
├── Samir-Singapore-Capstone-Proposal.md
├── fetch_historical.py           # Fetches all quarters from URA API
├── load_to_sqlite.py             # Loads raw JSON into SQLite
├── geocode_buildings.py          # Adds lat/lng to buildings table
├── raw_rental_contracts_all.json # Raw API output (git-ignored)
├── rentals.db                    # SQLite database (git-ignored)
├── summary.md                    # This file
├── dashboard_requirements.md     # User requirements
├── backend/                      # FastAPI backend
│   ├── main.py                   # App entry + CORS
│   ├── database.py               # DB connection + filter builder
│   ├── requirements.txt          # fastapi, uvicorn, aiosqlite
│   └── routers/
│       ├── districts.py          # GET /api/districts
│       ├── buildings.py          # GET /api/buildings (map markers), GET /api/buildings/search?q=
│       ├── trends.py             # GET /api/trends (time-series)
│       ├── stats.py              # GET /api/stats, /district-breakdown, /histogram, /deals
│       └── contracts.py          # GET /api/contracts (paginated)
└── frontend/                     # React + Vite + Tailwind
    └── src/
        ├── App.tsx               # Root: tab routing, dark mode, filter state
        ├── index.css             # Tailwind + dark mode variant
        ├── types/index.ts        # Shared TypeScript types
        ├── lib/api.ts            # API client functions
        ├── hooks/
        │   ├── useFilters.ts     # Global filter state hook
        │   └── useQuery.ts       # Data fetching + abort controller
        └── components/
            ├── Layout/
            │   ├── Navbar.tsx        # Tab nav + dark mode toggle
            │   ├── FilterBar.tsx     # Persistent filter bar (all dimensions)
            │   └── BuildingSearch.tsx # Autocomplete search with ghost-text Tab completion
            ├── Map/
            │   └── MapView.tsx   # Leaflet map + building markers + side drawer
            ├── Charts/
            │   └── ChartsView.tsx # Stats cards, trend line, district bar, histogram, deals
            └── Table/
                └── ContractsTable.tsx # Paginated sortable contracts
```

---

## Step 4: Dashboard

### 4.1 Tech Stack
- **Backend**: FastAPI (Python) with aiosqlite — REST API, CORS enabled
- **Frontend**: React + Vite + TypeScript + Tailwind CSS v4 + Space Grotesk font
- **Map**: react-leaflet (building markers + district selector)
- **Charts**: Recharts (LineChart, BarChart) — pure React
- **Icons**: lucide-react
- **Brand name**: Casota

### 4.2 Running the Dashboard
```bash
# Terminal 1 — backend (from backend/ directory)
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend (from frontend/ directory)
npm run dev
# Opens at http://localhost:5173/
# Vite proxies /api/* → http://127.0.0.1:8000
```

### 4.3 Database Schema Additions
- `area_sqm_min`, `area_sqm_max`, `area_sqft_min`, `area_sqft_max` — INTEGER columns added to `rental_contracts` (migrated from range strings via `migrate_area_columns.py`)
- `building_mrt_proximity (building_id, station_name, distance_m)` — pre-computed table of buildings within 1,000m (~15 min walk) of each MRT/LRT station. Populated by `compute_mrt_proximity.py`. 8,172 pairs covering 3,627 buildings and 133 stations.

### 4.4 Backend API Endpoints
| Endpoint | Description |
|---|---|
| `GET /api/districts` | 28 postal districts |
| `GET /api/districts/boundaries` | District polygon GeoJSON (convex hull from building locations) |
| `GET /api/districts/outline` | Singapore territorial boundary from OSM Nominatim |
| `GET /api/districts/landmass` | Singapore main island coastline from OSM Nominatim |
| `GET /api/buildings` | Building markers with avg rent (filtered) |
| `GET /api/buildings/search?q=` | Autocomplete building name search |
| `GET /api/buildings/recommend` | Similar buildings by district + price range |
| `GET /api/buildings/enrich` | MRT distance, schools within 1km, avg PSM for a building |
| `GET /api/trends` | Monthly avg rent + PSM time-series (single / by-district / by-building) |
| `GET /api/stats` | Aggregate stats (avg, median, min, max rent) |
| `GET /api/stats/district-breakdown` | Avg rent per district |
| `GET /api/stats/histogram` | Rent distribution in $500 buckets |
| `GET /api/stats/deals` | Buildings where latest month is ≥10% below 12-month avg |
| `GET /api/contracts` | Paginated individual contracts |
| `GET /api/stations` | All MRT/LRT stations with building counts |

**Shared filter params** accepted by all data endpoints:
`district`, `station`, `bedrooms`, `property_type`, `area_min`, `area_max`, `area_unit` (sqm/sqft), `date_from`, `date_to` (YYYY-MM), `building_id` (repeatable)

### 4.5 Features Built

**Landing page (Casota home)**
- Typewriter CTA cycling through 4 phrases (~3s cycle)
- Left column: all filters. Right column: Singapore district map
- District map: real OSM coastline + territorial boundary layers, 28 district polygons (convex hulls from building data), click to multi-select, each district a distinct colour
- "Explore Rentals →" navigates to Charts with filters applied
- Logo in navbar returns to landing page at any time

**Filter bar** (persistent across Charts / Map / Table):
- **Building search** — multi-select up to 10 buildings; ghost-text Tab completion; search history from localStorage (shown when input focused with empty query); recommendations (similar buildings by district + price range, shown as amber chips after selecting ≥1 building)
- **Property type** — toggle chips (Non-landed default, EC, Terrace)
- **Bedrooms** — toggle chips (Studio, 1–5BR+)
- **Area (sqm/sqft)** — min/max number inputs with m²/ft² toggle (clears values on unit switch; backend routes to correct integer column)
- **MRT station** — searchable dropdown of 133 stations; selected stations shown as chips coloured by official line colour (NS=red, EW=green, NE=purple, CC=orange, DT=dark blue, TE=brown); filters to buildings within 1,000m of any selected station
- **Date range** — dual-handle slider with M/Q toggle (month or quarter resolution, Jan 2022–Mar 2026)
- **Districts** — set via landing page map; shown as coloured chips in filter bar

**Charts tab**
- 4 stats cards (avg/median/min/max rent)
- **Multi-building comparison mode** (≥2 buildings selected):
  - Snapshot table: avg rent, avg PSM, nearest MRT + distance, schools within 1km
  - Avg Rent Over Time: one coloured line per building
  - Monthly Deal Count: one coloured line per building
  - Avg PSM Over Time: one coloured line per building
  - Building Comparison bar chart (avg rent per building)
- **Single/district mode**: single trend line, district bar chart, rent histogram, deal finder table
- Y-axis on trend charts auto-scales to data range with 8% cushion

**Map tab**: 4,157 building markers, colour-coded green→red by avg rent, click → side drawer with building info + trend chart

**Table tab**: Paginated 50 rows/page, sortable. Shows `area_sqm_min` and `area_sqm_max` as separate integer columns.

**Dark mode**: Tailwind class strategy, toggled via navbar, persisted in localStorage

### 4.6 Data Enrichment
`backend/enrichment.py` — in-memory data loaded once per server run:
- **143 MRT/LRT stations** with coordinates (hardcoded, covers NS/EW/NE/CC/DT/TE/LRT)
- **Schools** fetched from OneMap API on first request (searches for Primary School, Secondary School, Junior College, High School terms; cached)
- Haversine distance function for both use cases

### 4.7 One-time Scripts
| Script | Purpose |
|---|---|
| `fetch_historical.py` | Pull URA API (2022 Q1–2026 Q1) — one-time historical seed |
| `load_to_sqlite.py` | Load raw JSON into SQLite — one-time initial load |
| `geocode_buildings.py` | SVY21→WGS84 + OneMap fallback geocoding — one-time |
| `migrate_area_columns.py` | Split area range strings into integer min/max columns — one-time |
| `compute_mrt_proximity.py` | Pre-compute building↔station proximity table — one-time |
| `refresh.py` | **Quarterly refresh** — detects missing quarters, fetches from URA, inserts into DB, geocodes new buildings, populates area columns, updates MRT proximity. Run once per quarter (`python refresh.py`) or via the `/refresh` Claude Code slash command. |
| `scripts/build_embeddings.py` | Rebuild all ChromaDB collections (districts, buildings, quarterly). Re-run after each quarterly refresh. |

---

## Step 5: AI Assistant (Casota AI)

### 5.1 Architecture

Claude Sonnet 4.6 powers a streaming chat assistant in the "Casota AI" tab. The assistant has live access to the database via tool calls and optional RAG context from ChromaDB.

**Flow:**
1. User message → `POST /api/chat` (SSE)
2. Backend enriches with RAG context (if ChromaDB available) + active filter state
3. Claude streams a response, calling tools as needed (up to 3 tool-call rounds)
4. Tool results are fetched from the existing FastAPI endpoints and fed back to Claude
5. Final answer streams to the frontend as SSE text chunks

### 5.2 Backend Files

| File | Purpose |
|---|---|
| `backend/routers/chat.py` | SSE streaming endpoint `POST /api/chat`. Manages multi-turn history (trimmed to last 20 messages) and the tool-call loop (max 4 rounds). |
| `backend/ai/tools.py` | 8 Claude tool definitions + async executors that proxy to existing `/api/*` endpoints. |
| `backend/ai/rag.py` | ChromaDB RAG over 3 collections (`districts`, `buildings`, `quarterly`). Gracefully disabled if `chroma_db/` is absent. Also contains `build_system_prompt()` which injects RAG context + active filter state + pricing data rules. |
| `backend/mcp_server.py` | MCP server exposing the same tools for use with Claude Code / other MCP clients. |

### 5.3 Tools Available to Claude

| Tool | Description |
|---|---|
| `get_stats` | Aggregate avg/median/min/max rent + contract & building counts |
| `get_district_breakdown` | Avg rent per district, sorted highest→lowest |
| `get_trends` | Monthly avg rent + PSM time series; optional per-district grouping |
| `get_buildings` | Buildings list with avg rent + nearest MRT |
| `get_deals` | Buildings where latest month is ≥N% below 12-month trailing avg |
| `search_building` | Partial-match building name search |
| `enrich_building` | Nearest MRT distance, schools within 1km, avg PSM for a building |
| `get_contracts` | Raw individual rental contract records |

All tools accept standard filter params: `district`, `bedrooms`, `property_type`, `date_from`, `date_to`, `station`.

### 5.4 ChromaDB Collections

| Collection | Docs | Content |
|---|---|---|
| `districts` | 28 | District summaries with avg rent, building/contract counts, key MRT stations |
| `buildings` | ~4,230 | Building summaries with avg rent, contract count, nearest MRT |
| `quarterly` | ~476 | Per-district quarterly rent snapshots with QoQ change |

All collections use ChromaDB's DefaultEmbeddingFunction (ONNX all-MiniLM-L6-v2) — no PyTorch required.

### 5.5 Frontend Files

| File | Purpose |
|---|---|
| `components/AI/AiAssistant.tsx` | Chat UI — message thread, input bar, tool-call badges |
| `components/AI/ChatBubble.tsx` | Individual message bubble with markdown rendering |
| `components/AI/SuggestedChips.tsx` | Suggested question chips shown on empty state |
| `hooks/useChat.ts` | Chat state + SSE stream handler; persists history in `localStorage` (`casota_chat_history`, max 20 messages) |
| `lib/api.ts` | `chatStream()` — sends `POST /api/chat` and yields SSE events |

### 5.6 System Prompt Context

The system prompt tells Claude it is "Casota AI" and includes:
- Dataset summary (336,751 contracts, 4,157 buildings, 28 districts, Jan 2022–Mar 2026)
- District geography cheat-sheet (D01–08 CBD, D09–11 prime central, etc.)
- RAG snippets from ChromaDB (if available)
- User's currently active filter state (districts, bedrooms, date range, etc.)

### 5.7 Pricing Data Rules (system-level)

The system prompt enforces strict rules on data source usage:
1. **URA data is authoritative** — always used for price analysis, trends, comparisons, and recommendations
2. **PropertyGuru prices must never be used** for price evaluations or market analysis
3. **PropertyGuru prices may only appear** when (a) explicitly comparing a PG asking price against a URA transaction price side-by-side, or (b) as supplementary context — in which case the AI must label it as "PropertyGuru asking price" or "PropertyGuru listing price"
4. **No substitution** — if a building has no URA contracts, the AI states that rather than filling in with PG prices

---

## Steps Remaining

- [x] Claude-powered natural language assistant — Casota AI tab (Step 5)
- [x] Quarterly refresh mechanism — `refresh.py`
- [ ] Building-level enrichment data (developer, year built, tenure, facilities) — PropertyGuru blocked by Cloudflare; Claude knowledge API blocked by DataExpert proxy session requirements. Revisit with a reliable data source.
- [ ] MRT distance display enrichment (schools data quality improvement)
