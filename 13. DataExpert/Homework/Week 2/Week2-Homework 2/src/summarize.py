"""
summarize.py — Build a structured weekly engineering summary from normalised data.

The summary dict is the single source of truth for both the plain-text report
and the email draft. Add new stats here; downstream formatters pick them up.
"""

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any


def _week_bounds(reference: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (start, end) of the ISO week containing *reference* (UTC)."""
    ref = reference or datetime.now(timezone.utc)
    # Monday = weekday 0
    start = (ref - timedelta(days=ref.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=7)
    return start, end


def _in_window(dt: datetime | None, start: datetime, end: datetime) -> bool:
    return dt is not None and start <= dt < end


# ---------------------------------------------------------------------------
# Main summariser
# ---------------------------------------------------------------------------

def build_summary(
    prs: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    week_start: datetime | None = None,
) -> dict[str, Any]:
    """
    Aggregate PR/commit data into a structured summary dict.

    Keys returned:
        week_start, week_end          — ISO week window
        total_prs                     — all PRs active this week
        merged_prs                    — list of merged PR dicts
        open_prs                      — list of open PR dicts
        closed_without_merge          — list of closed-without-merge dicts
        total_commits                 — commits in window
        authors                       — set of contributing authors
        by_author                     — {author: {merged, open, commits}}
        label_counts                  — {label: count} across merged PRs
        lines_added, lines_deleted    — net code-change stats (merged only)
        highlight_prs                 — top-3 merged PRs by total line changes
    """
    start, end = _week_bounds(week_start)

    merged = [p for p in prs if p["state"] == "merged" and _in_window(p["merged_at"], start, end)]
    open_prs = [p for p in prs if p["state"] == "open" and _in_window(p["created_at"], start, end)]
    closed = [p for p in prs if p["state"] == "closed" and _in_window(p["closed_at"], start, end)]
    week_commits = [c for c in commits if _in_window(c["timestamp"], start, end)]

    # Per-author stats
    by_author: dict[str, dict] = defaultdict(lambda: {"merged": 0, "open": 0, "commits": 0})
    for p in merged:
        by_author[p["author"]]["merged"] += 1
    for p in open_prs:
        by_author[p["author"]]["open"] += 1
    for c in week_commits:
        by_author[c["author"]]["commits"] += 1

    # Label counts on merged PRs
    label_counts: dict[str, int] = defaultdict(int)
    for p in merged:
        for label in p["labels"]:
            label_counts[label] += 1

    # Lines changed (merged only)
    lines_added = sum(p["additions"] for p in merged)
    lines_deleted = sum(p["deletions"] for p in merged)

    # Top-3 by total lines touched
    highlight_prs = sorted(
        merged, key=lambda p: p["additions"] + p["deletions"], reverse=True
    )[:3]

    all_authors = set(by_author.keys())

    return {
        "week_start": start,
        "week_end": end,
        "total_prs": len(merged) + len(open_prs) + len(closed),
        "merged_prs": merged,
        "open_prs": open_prs,
        "closed_without_merge": closed,
        "total_commits": len(week_commits),
        "authors": all_authors,
        "by_author": dict(by_author),
        "label_counts": dict(label_counts),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "highlight_prs": highlight_prs,
    }


def format_plain_text(summary: dict[str, Any]) -> str:
    """Render the summary as a human-readable plain-text report."""
    s = summary
    week = s["week_start"].strftime("%b %d") + " – " + (s["week_end"] - timedelta(seconds=1)).strftime("%b %d, %Y")
    lines = [
        "=" * 60,
        f"  RELEASE RADAR — Week of {week}",
        "=" * 60,
        "",
        f"  PRs this week : {s['total_prs']}  "
        f"(merged: {len(s['merged_prs'])}  |  open: {len(s['open_prs'])}  |  closed without merge: {len(s['closed_without_merge'])})",
        f"  Commits       : {s['total_commits']}",
        f"  Contributors  : {', '.join(sorted(s['authors'])) or 'none'}",
        f"  Lines added   : +{s['lines_added']}  /  deleted: -{s['lines_deleted']}",
        "",
    ]

    if s["merged_prs"]:
        lines.append("MERGED THIS WEEK")
        lines.append("-" * 40)
        for p in s["merged_prs"]:
            labels = f"[{', '.join(p['labels'])}]" if p["labels"] else ""
            lines.append(f"  #{p['number']}  {p['title']}  {labels}")
            lines.append(f"        by @{p['author']}  •  {p['url']}")
        lines.append("")

    if s["open_prs"]:
        lines.append("OPEN / IN REVIEW")
        lines.append("-" * 40)
        for p in s["open_prs"]:
            reviewers = ", ".join(f"@{r}" for r in p["reviewers"]) or "unassigned"
            lines.append(f"  #{p['number']}  {p['title']}")
            lines.append(f"        by @{p['author']}  •  reviewers: {reviewers}  •  {p['url']}")
        lines.append("")

    if s["label_counts"]:
        lines.append("LABEL BREAKDOWN (merged PRs)")
        lines.append("-" * 40)
        for label, count in sorted(s["label_counts"].items(), key=lambda x: -x[1]):
            lines.append(f"  {label:<20} {count}")
        lines.append("")

    lines.append("PER-AUTHOR CONTRIBUTIONS")
    lines.append("-" * 40)
    for author, stats in sorted(s["by_author"].items()):
        lines.append(
            f"  @{author:<15}  merged: {stats['merged']}  open: {stats['open']}  commits: {stats['commits']}"
        )
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
