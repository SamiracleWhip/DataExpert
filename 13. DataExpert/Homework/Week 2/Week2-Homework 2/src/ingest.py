"""
ingest.py — Load and normalise PR/commit data.

Reads from local JSON files by default. When GITHUB_TOKEN and GITHUB_REPO
are set in the environment the loader can be extended to hit the real API;
that path is not implemented here (the mock path is identical in schema).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: str | None) -> datetime | None:
    """Return a timezone-aware datetime from an ISO-8601 string, or None."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalise_pr(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["id"],
        "number": raw["number"],
        "title": raw["title"],
        "author": raw["author"],
        "state": raw["state"],               # "open" | "merged" | "closed"
        "created_at": _parse_dt(raw["created_at"]),
        "merged_at": _parse_dt(raw.get("merged_at")),
        "closed_at": _parse_dt(raw.get("closed_at")),
        "url": raw["url"],
        "labels": raw.get("labels", []),
        "reviewers": raw.get("reviewers", []),
        "comments": raw.get("comments", 0),
        "additions": raw.get("additions", 0),
        "deletions": raw.get("deletions", 0),
    }


def _normalise_commit(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "sha": raw["sha"],
        "message": raw["message"],
        "author": raw["author"],
        "timestamp": _parse_dt(raw["timestamp"]),
        "pr_id": raw.get("pr_id"),
        "additions": raw.get("additions", 0),
        "deletions": raw.get("deletions", 0),
    }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_prs(data_dir: str | Path = "data") -> list[dict[str, Any]]:
    """Load and normalise PRs from mock_prs.json."""
    path = Path(data_dir) / "mock_prs.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [_normalise_pr(r) for r in raw]


def load_commits(data_dir: str | Path = "data") -> list[dict[str, Any]]:
    """Load and normalise commits from mock_commits.json."""
    path = Path(data_dir) / "mock_commits.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [_normalise_commit(r) for r in raw]


def load_all(data_dir: str | Path = "data") -> tuple[list, list]:
    """Convenience wrapper — returns (prs, commits)."""
    return load_prs(data_dir), load_commits(data_dir)
