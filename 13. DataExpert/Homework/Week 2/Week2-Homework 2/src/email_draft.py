"""
email_draft.py — Draft a stakeholder-ready weekly update email.

Converts the summary dict into a polished plain-text email that a
non-technical stakeholder can read without any engineering context.
"""

from datetime import timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_SUBJECT_TEMPLATE = "Engineering Weekly Update — {week}"

_BODY_TEMPLATE = """\
Subject: {subject}

Hi team,

Here is your weekly engineering update for {week}. This summary covers
pull request activity, key deliveries, and work in progress.

──────────────────────────────────────────────────────────
HIGHLIGHTS
──────────────────────────────────────────────────────────
{highlights}

──────────────────────────────────────────────────────────
BY THE NUMBERS
──────────────────────────────────────────────────────────
  • Pull requests merged   : {merged_count}
  • Pull requests in review: {open_count}
  • Total commits          : {total_commits}
  • Net lines of code      : +{lines_added} / -{lines_deleted}
  • Active contributors    : {contributors}

──────────────────────────────────────────────────────────
WHAT WAS SHIPPED
──────────────────────────────────────────────────────────
{shipped}

──────────────────────────────────────────────────────────
IN PROGRESS
──────────────────────────────────────────────────────────
{in_progress}

──────────────────────────────────────────────────────────
UPCOMING / WATCH LIST
──────────────────────────────────────────────────────────
{watch_list}

──────────────────────────────────────────────────────────

Full details and links are available in the PR tracker.
Questions? Reach out to the engineering lead.

Regards,
Release Radar (automated)
"""


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _format_highlights(summary: dict[str, Any]) -> str:
    prs = summary["highlight_prs"]
    if not prs:
        return "  No notable merges this week."
    items = []
    for p in prs:
        items.append(f"  • {p['title']}\n    ({p['url']})")
    return "\n".join(items)


def _format_shipped(summary: dict[str, Any]) -> str:
    prs = summary["merged_prs"]
    if not prs:
        return "  Nothing merged this week."
    items = []
    for p in prs:
        label_str = f" [{', '.join(p['labels'])}]" if p["labels"] else ""
        items.append(f"  • {p['title']}{label_str}")
    return "\n".join(items)


def _format_in_progress(summary: dict[str, Any]) -> str:
    prs = summary["open_prs"]
    if not prs:
        return "  No open PRs at end of week."
    items = []
    for p in prs:
        reviewers = ", ".join(f"@{r}" for r in p["reviewers"]) or "unassigned"
        items.append(f"  • {p['title']} (author: @{p['author']}, reviewers: {reviewers})")
    return "\n".join(items)


def _format_watch_list(summary: dict[str, Any]) -> str:
    """Surface closed-without-merge PRs and any open PRs awaiting review."""
    items = []
    for p in summary["closed_without_merge"]:
        items.append(f"  • [closed without merge] {p['title']} — may need follow-up")
    for p in summary["open_prs"]:
        if not p["reviewers"]:
            items.append(f"  • [needs reviewer] {p['title']}")
    if not items:
        items.append("  • Nothing flagged this week.")
    return "\n".join(items)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def draft_email(summary: dict[str, Any]) -> tuple[str, str]:
    """
    Build (subject, body) for the stakeholder email.

    Returns plain strings suitable for writing to a file or passing to an
    SMTP client.
    """
    week = (
        summary["week_start"].strftime("%b %d")
        + " – "
        + (summary["week_end"] - timedelta(seconds=1)).strftime("%b %d, %Y")
    )
    subject = _SUBJECT_TEMPLATE.format(week=week)
    body = _BODY_TEMPLATE.format(
        subject=subject,
        week=week,
        highlights=_format_highlights(summary),
        merged_count=len(summary["merged_prs"]),
        open_count=len(summary["open_prs"]),
        total_commits=summary["total_commits"],
        lines_added=summary["lines_added"],
        lines_deleted=summary["lines_deleted"],
        contributors=", ".join(f"@{a}" for a in sorted(summary["authors"])) or "none",
        shipped=_format_shipped(summary),
        in_progress=_format_in_progress(summary),
        watch_list=_format_watch_list(summary),
    )
    return subject, body
