"""Tests for src/summarize.py"""

from datetime import datetime, timezone

import pytest

from src.summarize import build_summary, format_plain_text, _week_bounds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pr(
    id=1, number=1, title="test PR", author="alice",
    state="merged",
    created="2026-04-07T09:00:00Z",
    merged=None, closed=None,
    labels=None, reviewers=None,
    additions=100, deletions=20,
):
    def dt(s):
        return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None

    return {
        "id": id, "number": number, "title": title, "author": author,
        "state": state,
        "created_at": dt(created),
        "merged_at": dt(merged),
        "closed_at": dt(closed),
        "url": f"https://github.com/org/repo/pull/{number}",
        "labels": labels or [],
        "reviewers": reviewers or [],
        "comments": 0,
        "additions": additions,
        "deletions": deletions,
    }


def _make_commit(sha="abc", message="msg", author="alice",
                 ts="2026-04-07T10:00:00Z", pr_id=1):
    return {
        "sha": sha,
        "message": message,
        "author": author,
        "timestamp": datetime.fromisoformat(ts.replace("Z", "+00:00")),
        "pr_id": pr_id,
        "additions": 10,
        "deletions": 5,
    }


# Fixed Monday for all tests
WEEK_START = datetime(2026, 4, 7, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWeekBounds:
    def test_monday_is_week_start(self):
        start, end = _week_bounds(datetime(2026, 4, 9, tzinfo=timezone.utc))  # Thursday
        assert start.weekday() == 0  # Monday

    def test_window_is_seven_days(self):
        start, end = _week_bounds(WEEK_START)
        assert (end - start).days == 7


class TestBuildSummary:
    def test_merged_pr_appears_in_merged(self):
        pr = _make_pr(state="merged", merged="2026-04-08T10:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        assert len(summary["merged_prs"]) == 1

    def test_open_pr_appears_in_open(self):
        pr = _make_pr(state="open", created="2026-04-08T09:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        assert len(summary["open_prs"]) == 1

    def test_closed_without_merge(self):
        pr = _make_pr(state="closed", created="2026-04-07T09:00:00Z",
                      closed="2026-04-09T10:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        assert len(summary["closed_without_merge"]) == 1

    def test_pr_outside_window_excluded(self):
        pr = _make_pr(state="merged", merged="2026-03-01T10:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        assert len(summary["merged_prs"]) == 0

    def test_commit_count(self):
        commits = [_make_commit(ts="2026-04-07T10:00:00Z") for _ in range(3)]
        summary = build_summary([], commits, week_start=WEEK_START)
        assert summary["total_commits"] == 3

    def test_lines_stats(self):
        prs = [
            _make_pr(id=1, number=1, state="merged", merged="2026-04-08T10:00:00Z", additions=100, deletions=20),
            _make_pr(id=2, number=2, state="merged", merged="2026-04-09T10:00:00Z", additions=50, deletions=10),
        ]
        summary = build_summary(prs, [], week_start=WEEK_START)
        assert summary["lines_added"] == 150
        assert summary["lines_deleted"] == 30

    def test_by_author_counts(self):
        prs = [
            _make_pr(id=1, number=1, author="alice", state="merged", merged="2026-04-08T10:00:00Z"),
            _make_pr(id=2, number=2, author="alice", state="open", created="2026-04-09T09:00:00Z"),
            _make_pr(id=3, number=3, author="bob", state="merged", merged="2026-04-10T10:00:00Z"),
        ]
        summary = build_summary(prs, [], week_start=WEEK_START)
        assert summary["by_author"]["alice"]["merged"] == 1
        assert summary["by_author"]["alice"]["open"] == 1
        assert summary["by_author"]["bob"]["merged"] == 1

    def test_label_counts(self):
        prs = [
            _make_pr(id=1, number=1, state="merged", merged="2026-04-08T10:00:00Z", labels=["bug", "critical"]),
            _make_pr(id=2, number=2, state="merged", merged="2026-04-09T10:00:00Z", labels=["bug"]),
        ]
        summary = build_summary(prs, [], week_start=WEEK_START)
        assert summary["label_counts"]["bug"] == 2
        assert summary["label_counts"]["critical"] == 1

    def test_highlight_prs_max_three(self):
        prs = [
            _make_pr(id=i, number=i, state="merged", merged="2026-04-08T10:00:00Z",
                     additions=i * 100, deletions=0)
            for i in range(1, 6)
        ]
        summary = build_summary(prs, [], week_start=WEEK_START)
        assert len(summary["highlight_prs"]) == 3
        # Should be the largest ones
        assert summary["highlight_prs"][0]["additions"] == 500


class TestFormatPlainText:
    def test_returns_string(self):
        pr = _make_pr(state="merged", merged="2026-04-08T10:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        output = format_plain_text(summary)
        assert isinstance(output, str)

    def test_contains_week_label(self):
        pr = _make_pr(state="merged", merged="2026-04-08T10:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        output = format_plain_text(summary)
        # Apr 7 is a Tuesday; week window opens on Monday Apr 06
        assert "Apr 06" in output

    def test_contains_pr_title(self):
        pr = _make_pr(title="my special PR", state="merged", merged="2026-04-08T10:00:00Z")
        summary = build_summary([pr], [], week_start=WEEK_START)
        output = format_plain_text(summary)
        assert "my special PR" in output
