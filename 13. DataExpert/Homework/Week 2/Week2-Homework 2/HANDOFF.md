# HANDOFF.md — Release Radar

**Last updated**: 2026-04-14  
**Outgoing**: Samir Bhojwani  
**Incoming**: (next assignee)

---

## 1. Current Project Status

**Phase**: MVP complete — core pipeline working, tests green, docs written.  
**Milestone**: Week 2 Homework submission (DataExpert.io).

The app runs end-to-end: it loads 8 mock PRs + 9 mock commits, generates a plain-text weekly engineering summary, and drafts a stakeholder email. All 31 unit tests pass.

---

## 2. Completed Tasks

| # | Task | Notes |
|---|------|-------|
| 1 | Project scaffolding | `src/`, `data/`, `tests/`, `output/`, `.gitignore`, `.env.example` |
| 2 | Mock data | `data/mock_prs.json` (8 PRs across merged/open/closed states), `data/mock_commits.json` (9 commits) |
| 3 | `src/ingest.py` | Loads + normalises JSON; timezone-aware datetimes throughout |
| 4 | `src/summarize.py` | `build_summary()` aggregates into summary dict; `format_plain_text()` renders plain report |
| 5 | `src/email_draft.py` | `draft_email()` produces `(subject, body)` tuple |
| 6 | `src/main.py` | CLI with `--data`, `--out`, `--week-start` flags |
| 7 | Unit tests (31 total) | `tests/test_ingest.py`, `tests/test_summarize.py`, `tests/test_email_draft.py` |
| 8 | `CLAUDE.md` | AI operating context |
| 9 | `HANDOFF.md` | This document |

---

## 3. Pending / Open Tasks

| Priority | Task | Notes |
|----------|------|-------|
| High | Wire up real GitHub API | `GITHUB_TOKEN` env var is documented but `ingest.py` only reads JSON today. Needs a `load_from_github()` function using the REST API (`/repos/{owner}/{repo}/pulls`). |
| Medium | Add `ruff` linter + pre-commit hook | Style is currently unenforced. Agreed convention: `ruff` only (not pylint/flake8). |
| Medium | SMTP delivery option | `email_draft.py` produces the email body; an optional send path via SMTP should be added behind a `--send` flag. Rate-limit guard required. |
| Low | HTML email template | Stakeholders asked about a formatted HTML version. Not started; plain text is the approved format for now. |
| Low | Coverage reporting | `pytest --cov=src` works but no threshold is enforced in CI. |

---

## 4. Open Issues / Risks / Blockers

| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| No real GitHub data | Medium | Known gap | App is fully functional on mock data. Real API integration is the obvious next step but not required for the homework. |
| No CI pipeline | Medium | Open | Tests must be run manually. Adding a GitHub Actions workflow would be the first CI step. |
| Week window anchors to Monday | Low | By design | `_week_bounds()` always backs up to Monday. If the team's week starts on Sunday, the function needs a `week_start_day` parameter. |
| Output files are not idempotent on same-week re-runs | Low | Known | Re-running overwrites `output/summary_YYYY-MM-DD.txt`. This is intentional but could cause issues in an automated pipeline that expects atomic writes. |

---

## 5. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-14 | Plain text output only (no HTML email) | Stakeholder emails are often forwarded verbatim; plain text is universally readable and copy-pasteable without stripping tags. |
| 2026-04-14 | No pandas/numpy | The dataset is small (< 100 PRs/week). Heavy libraries add install weight and hide the logic. Standard library is sufficient and keeps the project approachable for contributors. |
| 2026-04-14 | Mock data via JSON files, not fixtures inside tests | JSON files double as realistic demo data and can be swapped for a live API response without changing the ingest contract. |
| 2026-04-14 | `build_summary()` dict as single source of truth | Both the plain-text report and the email template pull from one dict. Adding a new stat in one place propagates automatically to all outputs. |
| 2026-04-14 | `pathlib.Path` throughout | Avoids OS-specific path separator bugs and works identically on macOS, Linux, and Windows. |
| 2026-04-14 | Week window anchored to ISO Monday | ISO week is the most common convention in engineering orgs; avoids off-by-one ambiguity when "this week" is mentioned in passing. |

---

## 6. Next 7-Day Execution Plan

| Day | Owner | Task |
|-----|-------|------|
| Day 1 | Incoming | Clone repo, install deps (`pip install -r requirements.txt`), run tests, run `python3 -m src.main --week-start 2026-04-07` and read the output files |
| Day 2 | Incoming | Read `CLAUDE.md` end-to-end; familiarise with data flow diagram |
| Day 3 | Incoming | Add `ruff` to `requirements.txt`, configure `pyproject.toml`, fix any lint errors |
| Day 4 | Incoming | Implement `load_from_github()` in `ingest.py` using `urllib.request` (no new deps) — mirror the existing normalised schema |
| Day 5 | Incoming | Write tests for `load_from_github()` using a mocked HTTP response |
| Day 6 | Incoming | Add a basic GitHub Actions workflow: install → lint → test on every push to `main` |
| Day 7 | Incoming | Review open issues table above; close any resolved items; update this `HANDOFF.md` |

---

## 7. Ownership / Contact Map

| Role | Person | Contact |
|------|--------|---------|
| Project author / outgoing owner | Samir Bhojwani | (GitHub: @samirbhojwani) |
| Incoming owner | TBD | — |
| DataExpert.io course instructor | — | Course Slack / Discord |

---

## 8. Recovery Steps

### "The tests fail after I cloned the repo"

```bash
# Ensure you're in the project root
cd /path/to/Week2-Homework\ 2

# Install dependencies
pip install -r requirements.txt

# Run tests
python3 -m pytest tests/ -v
```

Common cause: running `pytest` instead of `python3 -m pytest` when your shell `pytest` binary points to a different virtual environment.

### "The app crashes with `FileNotFoundError: data/mock_prs.json`"

Run from the project root, not from inside `src/`:
```bash
python3 -m src.main   # correct — run from project root
```

### "Output file is empty or only contains the header line"

The week window filter may be excluding all your data. Check that the timestamps in `data/mock_prs.json` fall within the target week. Use `--week-start YYYY-MM-DD` to override:
```bash
python3 -m src.main --week-start 2026-04-07
```

Note: `--week-start` accepts any date within the desired week; the app always backs up to the Monday of that week.

### "I need to add a new field to the output email"

1. Add the field to `build_summary()` in `src/summarize.py`.
2. Add a corresponding `_format_*` helper in `src/email_draft.py`.
3. Insert a `{new_field}` placeholder in `_BODY_TEMPLATE` and pass it in `draft_email()`.
4. Add a test to `tests/test_email_draft.py`.
5. Run `python3 -m pytest tests/ -v` to confirm nothing regressed.

### "I accidentally deleted `output/` or the files inside it"

That directory is gitignored and regenerated at runtime — just re-run the app:
```bash
python3 -m src.main
```
