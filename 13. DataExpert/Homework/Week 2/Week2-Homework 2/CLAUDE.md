# CLAUDE.md — AI Operating Context for Release Radar

## 1. Project Overview & Goals

**Release Radar** is a lightweight internal CLI tool that:
1. Ingests PR/commit data from local JSON mock files (or optionally a real GitHub API)
2. Generates a structured weekly engineering summary (plain text)
3. Drafts a stakeholder-ready email update (plain text)

**Primary goal**: Produce a weekly digest that an engineering manager can review in < 2 minutes and forward to stakeholders without editing.

**Non-goals**: Real-time dashboards, GitHub webhook listeners, HTML/rich email rendering, user authentication.

---

## 2. Build / Test / Lint Commands

```bash
# Install dependencies (once)
pip install -r requirements.txt

# Run the full pipeline (current ISO week)
python3 -m src.main

# Run with explicit week override
python3 -m src.main --week-start 2026-04-07 --data data/ --out output/

# Run all tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_summarize.py -v

# Run tests with coverage (optional, not yet configured)
python3 -m pytest tests/ --cov=src
```

There is no linter configured yet. If you add one, use `ruff` — do not add `pylint` or `flake8`.

---

## 3. Folder Map & Key Modules

```
release-radar/
├── src/
│   ├── __init__.py
│   ├── ingest.py        # Load & normalise PR/commit JSON → Python dicts
│   ├── summarize.py     # Aggregate normalised data → summary dict + plain-text report
│   ├── email_draft.py   # summary dict → (subject, body) strings
│   └── main.py          # CLI entry point — orchestrates ingest → summarize → email
│
├── data/
│   ├── mock_prs.json    # 8 sample PRs (merged/open/closed states)
│   └── mock_commits.json # 9 sample commits linked to PRs via pr_id
│
├── tests/
│   ├── test_ingest.py       # Unit tests for load_prs / load_commits
│   ├── test_summarize.py    # Unit tests for build_summary / format_plain_text
│   └── test_email_draft.py  # Unit tests for draft_email
│
├── output/              # Generated at runtime — gitignored
├── .env.example         # Template for optional environment variables
├── .gitignore
└── requirements.txt
```

### Data flow

```
data/mock_prs.json
data/mock_commits.json
        │
        ▼
   src/ingest.py          load_all() → (prs, commits)
        │
        ▼
   src/summarize.py       build_summary() → summary dict
                          format_plain_text() → str
        │
        ▼
   src/email_draft.py     draft_email() → (subject, body)
        │
        ▼
   output/summary_YYYY-MM-DD.txt
   output/email_YYYY-MM-DD.txt
```

---

## 4. Coding Conventions & Style Rules

- **Python 3.12+** — use built-in generics (`list[str]`, `dict[str, Any]`), not `typing.List` / `typing.Dict`.
- **Type hints on all public functions**. Return types are mandatory.
- **No third-party data-processing libraries** (no pandas, no numpy). The project intentionally uses only the standard library + `python-dotenv`.
- Module-level docstrings on all source files (`src/*.py`). Function-level docstrings only where the logic is non-obvious.
- Error messages must be human-readable; never `raise Exception("error")`.
- Dates/times: always store and pass `timezone`-aware `datetime` objects. Never use naive datetimes internally.
- JSON field names use `snake_case`. Do not silently rename fields when normalising — add explicit mappings in `_normalise_*` functions.

---

## 5. Deployment / Runtime Constraints

- **No persistent storage required** — all state lives in flat JSON files under `data/`.
- **No server process** — the app is a one-shot CLI; run it via cron or CI.
- **Output files are ephemeral** — `output/` is gitignored and regenerated each run. Do not treat output files as durable state.
- Python 3.12 is the minimum version. No backports are included.
- Optional environment variables (see `.env.example`) are loaded via `python-dotenv`; the app works without them.
- The app must run offline (no network calls unless `GITHUB_TOKEN` is explicitly set — that path is not yet implemented).

---

## 6. Security / Privacy Boundaries

- **Never commit `.env`** — it is gitignored. Keep all credentials (tokens, SMTP passwords) out of source.
- **Mock data only in `data/`** — do not add real PR titles, author names, or repo URLs to `mock_prs.json` / `mock_commits.json`.
- **No secrets in output files** — the generated summary and email must not echo back any environment variable values.
- **SMTP is not implemented** — `email_draft.py` writes to disk only. Do not add SMTP-send code without explicit instruction and without rate-limiting safeguards.
- `GITHUB_TOKEN` is optional and scoped to read-only repo access (`repo:read` scope is sufficient).

---

## 7. Do / Don't Instructions for AI Assistants

### DO
- Read a file before editing it.
- Run the test suite after any non-trivial change: `python3 -m pytest tests/ -v`
- Keep the summary dict in `summarize.build_summary()` as the single source of truth. Both the plain-text report and the email pull from it.
- When adding a new statistic to the output, add it to `build_summary()` first, then update `format_plain_text()` and `email_draft.draft_email()`.
- Use `pathlib.Path` for all file operations — no raw string concatenation for paths.

### DON'T
- Don't add pandas, numpy, or any heavy data library.
- Don't introduce a database or any form of persistent mutable state.
- Don't add HTML email rendering — the stakeholder format is intentionally plain text.
- Don't skip the `_week_bounds()` logic to hard-code a date range; all filtering goes through that function.
- Don't add retry logic or network fallback in `ingest.py` — the mock-data path must stay network-free.
- Don't change the output file naming convention (`summary_YYYY-MM-DD.txt`, `email_YYYY-MM-DD.txt`) — downstream scripts may depend on it.
- Don't write new files unless absolutely necessary — prefer editing existing ones.

---

## 8. Common Pitfalls & Debugging Tips

### Week window is off by a day
`_week_bounds()` anchors to **Monday** of the ISO week containing the reference datetime. If you pass a Tuesday as `week_start`, it will back up to Monday. To pin an exact window, pass the Monday of the desired week.

### PR not appearing in summary
Check `state` + the relevant timestamp:
- `merged` → `merged_at` must fall within `[week_start, week_end)`
- `open` → `created_at` must fall within the window
- `closed` → `closed_at` must fall within the window

### Timezone-naive datetime errors
All datetimes in the normalised schema are UTC-aware. If you add new data sources, wrap timestamps with `.replace(tzinfo=timezone.utc)` or use `datetime.fromisoformat(s.replace("Z", "+00:00"))`.

### Tests fail with `FileNotFoundError`
`load_prs()` and `load_commits()` resolve paths relative to the calling process's CWD. Run tests from the project root:
```bash
cd /path/to/release-radar && python3 -m pytest tests/ -v
```

### Adding a new field to mock data
Update both `data/mock_prs.json` (or `mock_commits.json`) **and** the corresponding `_normalise_*` function in `ingest.py`. Tests will catch missing fields.
