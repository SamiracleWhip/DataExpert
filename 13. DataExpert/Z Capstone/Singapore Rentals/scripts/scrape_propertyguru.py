#!/usr/bin/env python3
"""
Scrape PropertyGuru for building enrichment data (developer, TOP year, tenure,
total units, facilities, description, photo URLs).

Uses Playwright for JS rendering + rapidfuzz for project name matching.

Run from project root:
    python scripts/scrape_propertyguru.py [--limit N] [--dry-run]

Output: raw_pg_enrichment.json (git-ignored)
Resumable: buildings already present in the JSON are skipped.

Dependencies (install once):
    pip install playwright rapidfuzz beautifulsoup4
    playwright install chromium
"""

import argparse
import asyncio
import json
import random
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "rentals.db"
OUTPUT_PATH = PROJECT_ROOT / "raw_pg_enrichment.json"

BASE_URL = "https://www.propertyguru.com.sg"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Fuzzy match threshold — 85 = strong match, 75 = moderate
MATCH_THRESHOLD = 75

# Max photos to store per building
MAX_PHOTOS = 8


def _load_buildings() -> list[dict]:
    """Load all buildings from the database."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT b.id, b.project, b.street,
               (SELECT district FROM rental_contracts WHERE building_id = b.id LIMIT 1) AS district
        FROM buildings b
        ORDER BY b.id
        """
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def _load_existing(path: Path) -> dict[int, dict]:
    """Load already-scraped buildings from the output JSON."""
    if not path.exists():
        return {}
    with open(path) as f:
        data = json.load(f)
    return {int(k): v for k, v in data.items()}


def _save(path: Path, results: dict[int, dict]):
    with open(path, "w") as f:
        json.dump({str(k): v for k, v in results.items()}, f, indent=2, ensure_ascii=False)


def _normalise(name: str) -> str:
    """Normalise a building name for fuzzy matching."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _fuzzy_score(query: str, candidate: str) -> int:
    q = _normalise(query)
    c = _normalise(candidate)
    return max(
        fuzz.token_set_ratio(q, c),
        fuzz.partial_ratio(q, c),
    )


def _parse_project_page(html: str, url: str) -> dict:
    """
    Parse a PropertyGuru condo project overview page.

    PropertyGuru renders key project info in structured HTML. The selectors
    here target common patterns; adjust if the site structure changes.
    Returns a dict with the fields we care about (values may be None if absent).
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict = {"pg_url": url}

    # ── Developer ──────────────────────────────────────────────────────────
    # PG typically shows "Developer: <Name>" in a details table
    developer = None
    for label_el in soup.find_all(string=re.compile(r"developer", re.I)):
        parent = label_el.parent
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                developer = sibling.get_text(strip=True)
                break
    # Also try structured data tables / dl/dd pairs
    if not developer:
        for dt in soup.find_all("dt"):
            if "developer" in dt.get_text().lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    developer = dd.get_text(strip=True)
                    break
    result["developer"] = developer

    # ── TOP / Year Completed ───────────────────────────────────────────────
    year_completed = None
    for label_el in soup.find_all(string=re.compile(r"(top|completion|year\s+built|completed)", re.I)):
        parent = label_el.parent
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                text = sibling.get_text(strip=True)
                m = re.search(r"(19|20)\d{2}", text)
                if m:
                    year_completed = int(m.group())
                    break
    result["year_completed"] = year_completed

    # ── Tenure ────────────────────────────────────────────────────────────
    tenure = None
    for label_el in soup.find_all(string=re.compile(r"tenure", re.I)):
        parent = label_el.parent
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                tenure = sibling.get_text(strip=True)
                break
    # Also scan page text for common tenure patterns
    if not tenure:
        for pattern in [r"freehold", r"\d{2,3}[- ]year leasehold", r"99-year", r"999-year"]:
            m = re.search(pattern, html, re.I)
            if m:
                tenure = m.group()
                break
    result["tenure"] = tenure

    # ── Total Units ───────────────────────────────────────────────────────
    total_units = None
    for label_el in soup.find_all(string=re.compile(r"(total\s+units?|no\.\s+of\s+units?|number\s+of\s+units?)", re.I)):
        parent = label_el.parent
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                m = re.search(r"\d+", sibling.get_text())
                if m:
                    total_units = int(m.group())
                    break
    result["total_units"] = total_units

    # ── Facilities ────────────────────────────────────────────────────────
    facilities: list[str] = []
    # Look for a facilities section (common pattern: ul/li under a "Facilities" heading)
    for heading in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
        if re.search(r"facilit|amenities|feature", heading.get_text(), re.I):
            # collect list items after this heading
            parent = heading.parent
            ul = heading.find_next("ul") if heading else None
            if ul:
                for li in ul.find_all("li"):
                    text = li.get_text(strip=True)
                    if text and len(text) < 60:
                        facilities.append(text)
            # Also look for span/div chips
            for chip in parent.find_all(["span", "div"], class_=re.compile(r"tag|chip|badge|facility|amenity", re.I)) if parent else []:
                text = chip.get_text(strip=True)
                if text and len(text) < 60:
                    facilities.append(text)
            break
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for f in facilities:
        key = f.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    result["facilities"] = deduped

    # ── Description ───────────────────────────────────────────────────────
    description = None
    for meta in soup.find_all("meta", attrs={"name": "description"}):
        description = meta.get("content", "").strip()
        if description:
            break
    if not description:
        # Look for og:description
        for meta in soup.find_all("meta", attrs={"property": "og:description"}):
            description = meta.get("content", "").strip()
            if description:
                break
    if not description:
        # Try to find a project description block
        for div in soup.find_all(["div", "section"], class_=re.compile(r"description|overview|about", re.I)):
            text = div.get_text(" ", strip=True)
            if len(text) > 100:
                description = text[:600]
                break
    result["description"] = description

    # ── Photos ────────────────────────────────────────────────────────────
    photos: list[str] = []
    # og:image first
    for meta in soup.find_all("meta", attrs={"property": "og:image"}):
        url_val = meta.get("content", "")
        if url_val and url_val not in photos:
            photos.append(url_val)
    # Gallery images: look for img tags with large dimensions or in carousel/gallery divs
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        if not src:
            continue
        # Skip tiny icons / SVGs / data URIs
        if src.startswith("data:") or src.endswith(".svg"):
            continue
        # PropertyGuru CDN pattern: usually contains "propertyguru" or "pgimages"
        if re.search(r"(propertyguru|pgimage|cloudfront|imgix)", src, re.I):
            # Prefer larger image variants (PG uses ?w=800 or similar)
            if src not in photos:
                photos.append(src)
        if len(photos) >= MAX_PHOTOS:
            break
    # Also check JSON-LD for image arrays
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
            imgs = ld.get("image") or []
            if isinstance(imgs, str):
                imgs = [imgs]
            for img_url in imgs:
                if img_url and img_url not in photos:
                    photos.append(img_url)
                if len(photos) >= MAX_PHOTOS:
                    break
        except (json.JSONDecodeError, AttributeError):
            pass
    result["photos"] = photos[:MAX_PHOTOS]

    return result


async def _search_and_scrape(page, building: dict) -> Optional[dict]:
    """
    Search PropertyGuru for a building and scrape the best matching project page.
    Returns enrichment dict or None if no match found.
    """
    project_name = building["project"]
    district = building.get("district", "")

    # Build search URL — PG's rent listing search with keyword
    search_url = (
        f"{BASE_URL}/property-for-rent"
        f"?freetext={project_name.replace(' ', '+')}"
        f"&market=residential"
    )

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        html = await page.content()
    except Exception as e:
        return {"pg_url": None, "error": str(e), "match_score": 0}

    soup = BeautifulSoup(html, "html.parser")

    # Find project/listing cards and look for project-level links
    # PG shows listing cards with the project name; we look for a nav to the project overview
    best_score = 0
    best_href: Optional[str] = None
    best_name: Optional[str] = None

    # Strategy 1: Look for links that contain the building name as text
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        href = a["href"]
        if not link_text or len(link_text) < 3:
            continue
        # Only interested in property listing/project links, not nav/footer
        if not re.search(r"/(property-for-rent|singapore-property|listing)/", href, re.I):
            continue
        score = _fuzzy_score(project_name, link_text)
        if score > best_score:
            best_score = score
            best_href = href
            best_name = link_text

    # Strategy 2: Look for listing title h2/h3 elements
    for el in soup.find_all(["h2", "h3"], class_=re.compile(r"title|listing|project|name", re.I)):
        text = el.get_text(strip=True)
        if not text:
            continue
        score = _fuzzy_score(project_name, text)
        if score > best_score:
            best_score = score
            best_name = text
            # Try to find the parent link
            parent_a = el.find_parent("a")
            if parent_a:
                best_href = parent_a.get("href")

    if best_score < MATCH_THRESHOLD or not best_href:
        return {
            "pg_url": None,
            "error": f"no match (best: '{best_name}' score={best_score})",
            "match_score": best_score,
        }

    # Navigate to the matched listing page
    if best_href.startswith("/"):
        best_href = BASE_URL + best_href
    elif not best_href.startswith("http"):
        best_href = BASE_URL + "/" + best_href

    try:
        await page.goto(best_href, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        detail_html = await page.content()
    except Exception as e:
        return {"pg_url": best_href, "error": str(e), "match_score": best_score}

    result = _parse_project_page(detail_html, best_href)
    result["match_score"] = best_score
    result["matched_name"] = best_name
    return result


async def run(limit: Optional[int] = None, dry_run: bool = False):
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    buildings = _load_buildings()
    existing = _load_existing(OUTPUT_PATH)
    print(f"Buildings in DB: {len(buildings)}")
    print(f"Already scraped: {len(existing)}")

    to_scrape = [b for b in buildings if b["id"] not in existing]
    if limit:
        to_scrape = to_scrape[:limit]
    print(f"To scrape: {len(to_scrape)}")

    if dry_run:
        print("Dry run — exiting without scraping.")
        return

    if not to_scrape:
        print("Nothing to do.")
        return

    results = dict(existing)
    ua = random.choice(USER_AGENTS)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="en-SG",
            timezone_id="Asia/Singapore",
        )
        # Block analytics/tracking to speed things up
        await context.route(
            re.compile(r"(google-analytics|googletagmanager|facebook\.net|hotjar|newrelic)"),
            lambda route: route.abort(),
        )

        page = await context.new_page()

        # Brief warm-up visit to set cookies
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
        except Exception:
            pass

        for i, building in enumerate(to_scrape):
            bid = building["id"]
            print(f"[{i+1}/{len(to_scrape)}] {building['project']} (id={bid})", end="  ")

            enrichment = await _search_and_scrape(page, building)
            if enrichment is None:
                enrichment = {"pg_url": None, "error": "unknown failure", "match_score": 0}

            results[bid] = enrichment
            score = enrichment.get("match_score", 0)
            pg_url = enrichment.get("pg_url") or "(none)"
            status = "✓" if score >= MATCH_THRESHOLD else "✗"
            print(f"{status} score={score} url={pg_url[:60]}")

            # Save after every building so a crash doesn't lose progress
            _save(OUTPUT_PATH, results)

            # Rate limit: 2–4 second random delay
            await asyncio.sleep(random.uniform(2.0, 4.0))

            # Rotate user agent every ~20 requests
            if (i + 1) % 20 == 0:
                ua = random.choice(USER_AGENTS)
                await context.set_extra_http_headers({"User-Agent": ua})

        await browser.close()

    matched = sum(1 for v in results.values() if v.get("match_score", 0) >= MATCH_THRESHOLD)
    print(f"\nDone. {matched}/{len(results)} buildings matched. Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape PropertyGuru building data")
    parser.add_argument("--limit", type=int, default=None, help="Max buildings to scrape (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Print counts and exit without scraping")
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, dry_run=args.dry_run))
