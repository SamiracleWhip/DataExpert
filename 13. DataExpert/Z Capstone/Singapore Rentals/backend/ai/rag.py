import json
import os
from pathlib import Path
from typing import Optional

CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "/tmp/chroma_db"))

_chroma_client = None
_ef = None
_chroma_available: Optional[bool] = None


def _init_chroma() -> bool:
    global _chroma_client, _ef, _chroma_available
    if _chroma_available is not None:
        return _chroma_available
    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        if not CHROMA_PATH.exists():
            _chroma_available = False
            return False
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _ef = DefaultEmbeddingFunction()
        _chroma_available = True
        return True
    except Exception:
        _chroma_available = False
        return False


def search_context(query: str, n_results: int = 8) -> str:
    if not _init_chroma() or _chroma_client is None:
        return ""

    docs: list[str] = []
    for collection_name in ("districts", "buildings", "quarterly"):
        try:
            col = _chroma_client.get_collection(collection_name, embedding_function=_ef)
            results = col.query(
                query_texts=[query],
                n_results=min(n_results, col.count()),
            )
            for doc in (results.get("documents") or [[]])[0]:
                docs.append(doc)
        except Exception:
            pass

    if not docs:
        return ""
    return "\n\n".join(docs)


def build_system_prompt(context: str, filters: dict) -> str:
    base = (
        "You are Casota AI, an intelligent assistant for the Casota Singapore Rental "
        "Intelligence Dashboard.\n\n"
        "You help users understand Singapore's private residential rental market. "
        "The database contains 336,751 rental contracts from January 2022 to March 2026, "
        "covering 4,157 buildings across 28 postal districts. "
        "Data source: URA (Urban Redevelopment Authority) stamp duty records.\n\n"
        "Property types covered: Non-landed Properties (condos/apartments), "
        "Executive Condominiums, Terrace Houses. HDB flats are NOT included.\n\n"
        "Singapore district context:\n"
        "- Districts 01–08: CBD, Marina Bay, Shenton Way (commercial/mixed)\n"
        "- Districts 09–11: Prime Central — Orchard, River Valley, Novena (most expensive)\n"
        "- Districts 12–20: Rest of Central — Toa Payoh, Bishan, Geylang, Katong\n"
        "- Districts 21–28: Outside Central — Bukit Timah, Jurong, Tampines, Woodlands (most affordable)\n"
        "'PSM' means price per square metre per month.\n\n"
    )

    if context:
        base += f"Relevant context from the database:\n{context}\n\n"

    active = _describe_filters(filters)
    if active:
        base += f"The user currently has these dashboard filters active: {active}\n\n"

    base += (
        "PRICING DATA RULES — follow these strictly:\n"
        "1. URA rental data is the authoritative source for all price-related answers. "
        "Always use URA prices for market analysis, comparisons, averages, trends, and recommendations.\n"
        "2. PropertyGuru prices must NEVER be used for price evaluations, analyses, or recommendations.\n"
        "3. PropertyGuru price data may only be mentioned in two situations: "
        "(a) when explicitly comparing a PropertyGuru-listed price against a URA price side-by-side, or "
        "(b) when surfacing it as supplementary context — in which case you MUST clearly label it as "
        "'PropertyGuru asking price' or 'PropertyGuru listing price', never as a market price.\n"
        "4. If only PropertyGuru pricing is available for a property (no URA contracts), "
        "state that no verified URA transaction data is available rather than substituting PropertyGuru prices.\n\n"
        "Use the available tools to fetch live data. "
        "Always cite specific numbers. "
        "Format responses with markdown — bold key figures, use bullet points for lists. "
        "Keep answers concise and conversational.\n\n"
        "CHARTS: When a comparison or trend would be clearer as a visual, emit a fenced code block "
        "tagged as `chart` containing a single JSON object:\n"
        '  {"type": "bar"|"line", "title": "...", "data": [{"label": "...", "value": 1234}, ...], "y_label": "SGD/month"}\n'
        "Use `bar` for comparisons (districts, buildings, bedroom types). "
        "Use `line` for time series (rent trends over months). "
        "Keep data to 12 points or fewer. "
        "Only emit a chart when it genuinely adds clarity — not on every response."
    )
    return base


def _describe_filters(filters: dict) -> str:
    parts: list[str] = []
    if filters.get("districts"):
        parts.append(f"Districts: {', '.join('D' + d for d in filters['districts'])}")
    if filters.get("bedrooms"):
        parts.append(f"Bedrooms: {', '.join(filters['bedrooms'])}")
    if filters.get("propertyTypes"):
        parts.append(f"Property type: {', '.join(filters['propertyTypes'])}")
    if filters.get("stations"):
        parts.append(f"MRT stations: {', '.join(filters['stations'])}")
    if filters.get("dateFrom") or filters.get("dateTo"):
        df = filters.get("dateFrom", "any")
        dt = filters.get("dateTo", "now")
        parts.append(f"Date range: {df} to {dt}")
    if filters.get("selectedBuildings"):
        names = [b.get("name", "") for b in filters["selectedBuildings"]]
        parts.append(f"Buildings: {', '.join(names)}")
    return "; ".join(parts)
