# Singapore Rentals — Architecture

## End-to-End Flow

```
╔══════════════════════════════════════════════════════════════════════╗
║                         DATA SOURCE                                  ║
║                                                                      ║
║   URA API (eservice.ura.gov.sg)                                      ║
║   PMI_Resi_Rental — 17 quarters, ~337K contracts                     ║
╚══════════════════════════════════════════════════════════════════════╝
                              │
                    (REST + access token)
                              │
╔══════════════════════════════════════════════════════════════════════╗
║                         ETL PIPELINE                                 ║
║                    (run once or quarterly)                           ║
║                                                                      ║
║  1. fetch_historical.py / refresh.py                                 ║
║     └─ Fetch quarters from URA API → raw_rental_contracts_all.json   ║
║                                                                      ║
║  2. load_to_sqlite.py                                                ║
║     └─ Parse JSON → INSERT into buildings + rental_contracts tables  ║
║                                                                      ║
║  3. geocode_buildings.py                                             ║
║     └─ SVY21 (x/y) → WGS84 (lat/lng) via pyproj                    ║
║        + OneMap API fallback for unmatched buildings (~98.3% hit)    ║
║                                                                      ║
║  4. compute_mrt_proximity.py                                         ║
║     └─ Haversine distance: buildings × 143 MRT stations              ║
║        → building_mrt_proximity table (pairs within 1km)            ║
║                                                                      ║
║  5. scripts/build_embeddings.py                                      ║
║     └─ Embed 3 document types into ChromaDB (ONNX MiniLM)           ║
║        · 28  district summaries                                      ║
║        · ~4,230 building summaries (≥3 contracts)                   ║
║        · ~476  quarterly snapshots (per district × quarter)          ║
╚══════════════════════════════════════════════════════════════════════╝
                              │
╔══════════════════════════════════════════════════════════════════════╗
║                          STORAGE                                     ║
║                                                                      ║
║  rentals.db (SQLite, ~80MB)              chroma_db/ (ChromaDB)       ║
║  ┌─────────────────────┐                 ┌──────────────────────┐   ║
║  │ districts      (28) │                 │ districts collection  │   ║
║  │ buildings    (4,230)│                 │ buildings collection  │   ║
║  │ rental_contracts    │                 │ quarterly collection  │   ║
║  │          (336,751)  │                 │  ~4,734 docs total   │   ║
║  │ building_mrt_       │                 └──────────────────────┘   ║
║  │   proximity (8,172) │                                            ║
║  └─────────────────────┘                                            ║
╚══════════════════════════════════════════════════════════════════════╝
                              │
╔══════════════════════════════════════════════════════════════════════╗
║                    FASTAPI BACKEND  (:8000)                          ║
║                                                                      ║
║  main.py — CORS, router registration, startup                        ║
║  database.py — async SQLite pool, build_rental_filter()             ║
║                                                                      ║
║  REST Routers:                                                       ║
║  ┌──────────────────────────────────────────────────────────┐       ║
║  │ /api/districts   → district list, GeoJSON boundaries     │       ║
║  │ /api/buildings   → list, search, enrich, recommend       │       ║
║  │ /api/trends      → monthly avg rent time-series          │       ║
║  │ /api/stats       → aggregate stats, histograms, deals    │       ║
║  │ /api/contracts   → paginated raw rental records          │       ║
║  │ /api/stations    → MRT stops/lines GeoJSON               │       ║
║  └──────────────────────────────────────────────────────────┘       ║
║                                                                      ║
║  AI / Chat Router:                                                   ║
║  ┌──────────────────────────────────────────────────────────┐       ║
║  │ POST /api/chat                                           │       ║
║  │                                                          │       ║
║  │  User message                                            │       ║
║  │       │                                                  │       ║
║  │       ├─→ guard.py ──────→ profanity + relevance check  │       ║
║  │       │       (Claude Haiku, max_tokens=3)               │       ║
║  │       │                                                  │       ║
║  │       ├─→ rag.py ────────→ ChromaDB semantic search     │       ║
║  │       │       (3 collections queried concurrently)       │       ║
║  │       │                                                  │       ║
║  │       ↓                                                  │       ║
║  │  Build system prompt (context + active filters)          │       ║
║  │       ↓                                                  │       ║
║  │  Claude Sonnet 4.6 — tool-use loop (max 4 rounds)       │       ║
║  │       ↓                                                  │       ║
║  │  tools.py — 8 async tools (proxy → /api/* endpoints):   │       ║
║  │    · get_stats          · get_district_breakdown         │       ║
║  │    · get_trends         · get_buildings                  │       ║
║  │    · get_deals          · search_building                │       ║
║  │    · enrich_building    · get_contracts                  │       ║
║  │       ↓                                                  │       ║
║  │  SSE stream → frontend EventSource                       │       ║
║  └──────────────────────────────────────────────────────────┘       ║
╚══════════════════════════════════════════════════════════════════════╝
              │                                    │
              │ HTTP /api/*                        │ stdio (MCP)
              │                                    │
╔═════════════╧════════════════╗    ╔══════════════╧═════════════════╗
║   FRONTEND  (:5173 dev)      ║    ║   MCP SERVER                   ║
║   React 19 + Vite + TS       ║    ║   (mcp_server.py)              ║
║                              ║    ║                                 ║
║  Tabs:                       ║    ║  Same 8 tools exposed via       ║
║  · Landing (district map)    ║    ║  Model Context Protocol         ║
║  · Charts (trends, histo)    ║    ║  → Claude Desktop / Code        ║
║  · Map (Leaflet markers)     ║    ║                                 ║
║  · Table (paginated)         ║    ╚═════════════════════════════════╝
║  · Saved (filter presets)    ║
║  · AI (Casota chat)          ║
║                              ║
║  State:                      ║
║  · useFilters — 8 dims       ║
║  · useQuery — fetch + abort  ║
║  · useChat — SSE + history   ║
║                              ║
║  /api/* proxied → :8000      ║
╚══════════════════════════════╝
```

---

## Layer Summary

| Layer | Technology | Key Files |
|---|---|---|
| **Data Source** | URA REST API | — |
| **ETL Pipeline** | Python scripts | `fetch_historical.py`, `load_to_sqlite.py`, `geocode_buildings.py`, `compute_mrt_proximity.py`, `refresh.py` |
| **Embedding Build** | ChromaDB + ONNX MiniLM | `scripts/build_embeddings.py` |
| **Storage** | SQLite + ChromaDB | `rentals.db`, `backend/chroma_db/` |
| **REST API** | FastAPI + aiosqlite | `backend/main.py`, `backend/routers/*` |
| **AI Chat** | Claude Sonnet 4.6 + SSE | `backend/routers/chat.py`, `backend/ai/*` |
| **Frontend** | React 19 + Vite + Leaflet + Recharts | `frontend/src/*` |
| **MCP** | Model Context Protocol | `backend/mcp_server.py` |

---

## Quarterly Refresh Flow

```
refresh.py
  1. Detect missing quarters since last DB entry
  2. Fetch new quarters from URA API
  3. load_to_sqlite   — insert new buildings + contracts
  4. geocode_buildings — geocode any new buildings
  5. compute_mrt_proximity — update proximity table
  6. build_embeddings — rebuild ChromaDB collections
```

---

## Key Design Notes

- **Storage is dual**: SQLite for structured queries, ChromaDB for semantic/RAG retrieval
- **AI tools are self-referential**: Claude's 8 tools call back into the same FastAPI `/api/*` endpoints the frontend uses — no duplicated query logic
- **Guard + RAG run concurrently**: each chat request fires both in parallel before the first Claude call
- **Refresh is incremental**: `refresh.py` detects missing quarters and only fetches new data, then re-runs the full enrichment + embedding chain
- **MCP server** mirrors the AI tools to Claude Desktop/Code via stdio — same logic, different transport
