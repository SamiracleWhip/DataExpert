# Plan 2: Live GitHub Integration (Read-Only)

## Context
The current CLI prompts users to manually paste issue text, PR descriptions, and commit messages. This is tedious and error-prone. The goal is to replace manual input with live GitHub API fetches — the user provides a `owner/repo` identifier and an issue/PR number (or date range for commits), and the tool fetches the real data automatically before passing it to the existing Claude workflows.

The three workflow functions (`triage_issue`, `summarize_pr`, `generate_email`) are **unchanged** — they already accept the right input shapes. Only the data-fetching layer and the CLI menus need to change.

---

## What Changes

### New file: `github_client.py` (project root)
A thin wrapper around PyGitHub with three functions:

```python
def fetch_issue(repo: str, issue_number: int) -> dict
    # returns: {"title": str, "body": str, "comments": str}

def fetch_pr(repo: str, pr_number: int) -> dict
    # returns: {"title": str, "description": str, "diff_snippets": str}

def fetch_commits(repo: str, since_days: int = 7, branch: str = "main") -> list[dict]
    # returns: [{"date": "YYYY-MM-DD", "message": str}, ...]
```

- Reads `GITHUB_TOKEN` from env (falls back to unauthenticated if missing, with a warning — rate limited to 60 req/hr)
- `fetch_pr` fetches patch previews for up to 10 files and passes them as `diff_snippets`
- `fetch_commits` defaults to the last 7 days; user can override

### Update `requirements.txt`
Add `PyGithub` (the `github` package).

### Update `.env`
Add `GITHUB_TOKEN=ghp_...` (user fills in). Document in README.

### Update `main.py` — replace manual prompts with GitHub fetch
Each menu option now prompts for a repo slug and number instead of raw text:

**Option 1 — Issue Triage:**
```
Repo (owner/repo): anthropics/anthropic-sdk-python
Issue number: 123
→ calls fetch_issue() → passes result to triage_issue()
```

**Option 2 — PR Summary:**
```
Repo (owner/repo): anthropics/anthropic-sdk-python
PR number: 456
→ calls fetch_pr() → passes result to summarize_pr()
```

**Option 3 — Commit Digest:**
```
Repo (owner/repo): anthropics/anthropic-sdk-python
Branch (default: main): main
How many days back? (default: 7): 7
→ calls fetch_commits() → passes result to generate_email()
```

---

## Files Modified
| File | Change |
|------|--------|
| `requirements.txt` | Added `PyGithub` |
| `.env` | Added `GITHUB_TOKEN=` line |
| `main.py` | Replaced manual input prompts with repo/number prompts + `github_client` calls |

## New Files
| File | Purpose |
|------|---------|
| `github_client.py` | Fetches issues, PRs, and commits from GitHub API via PyGitHub |

## Files NOT changed
- `workflows/issue_triage.py` — input signature unchanged
- `workflows/pr_summary.py` — input signature unchanged
- `workflows/commit_digest.py` — input signature unchanged
- All guardrails, prompts, samples — unchanged

---

## Build Steps

1. `pip install PyGithub` + add to `requirements.txt`
2. Add `GITHUB_TOKEN=` to `.env`
3. Create `github_client.py` with the three fetch functions
4. Update `run_issue_triage()` in `main.py` — swap manual text input for `fetch_issue(repo, number)`
5. Update `run_pr_summary()` in `main.py` — swap for `fetch_pr(repo, number)`
6. Update `run_commit_digest()` in `main.py` — swap for `fetch_commits(repo, since_days, branch)`

---

## Verification
- Run `python3 main.py` and select option 1 with a real public GitHub issue
- Confirm the fetched title/body/comments are printed before Claude is called
- Confirm PII redaction still runs on the fetched text
- Run option 2 with a real PR number; confirm diff snippets appear in the output
- Run option 3; confirm commits from the last N days are fetched and the email reflects real commit messages
- Test with an invalid repo/issue number to confirm a clean error message rather than a crash
