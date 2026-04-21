"""Tests for src/email_draft.py"""

from datetime import datetime, timezone

import pytest

from src.summarize import build_summary
from src.email_draft import draft_email


WEEK_START = datetime(2026, 4, 7, tzinfo=timezone.utc)


def _make_pr(id=1, number=1, title="test", author="alice", state="merged",
             created="2026-04-07T09:00:00Z", merged=None, closed=None,
             labels=None, reviewers=None, additions=50, deletions=10):
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


class TestDraftEmail:
    def _summary(self, prs=None, commits=None):
        return build_summary(prs or [], commits or [], week_start=WEEK_START)

    def test_returns_tuple_of_strings(self):
        subject, body = draft_email(self._summary())
        assert isinstance(subject, str)
        assert isinstance(body, str)

    def test_subject_contains_week(self):
        subject, _ = draft_email(self._summary())
        assert "Apr" in subject

    def test_body_contains_subject(self):
        subject, body = draft_email(self._summary())
        assert subject in body

    def test_merged_pr_appears_in_body(self):
        prs = [_make_pr(title="Ship the rocket", state="merged", merged="2026-04-08T10:00:00Z")]
        _, body = draft_email(self._summary(prs=prs))
        assert "Ship the rocket" in body

    def test_open_pr_appears_in_body(self):
        prs = [_make_pr(title="Pending work", state="open", created="2026-04-09T09:00:00Z",
                        reviewers=["carol"])]
        _, body = draft_email(self._summary(prs=prs))
        assert "Pending work" in body
        assert "carol" in body

    def test_no_prs_empty_message(self):
        _, body = draft_email(self._summary())
        assert "Nothing merged this week" in body

    def test_closed_without_merge_in_watch_list(self):
        prs = [_make_pr(state="closed", created="2026-04-07T09:00:00Z",
                        closed="2026-04-09T10:00:00Z")]
        _, body = draft_email(self._summary(prs=prs))
        assert "closed without merge" in body

    def test_contributor_count_in_body(self):
        prs = [
            _make_pr(id=1, number=1, author="alice", state="merged", merged="2026-04-08T10:00:00Z"),
            _make_pr(id=2, number=2, author="bob", state="merged", merged="2026-04-09T10:00:00Z"),
        ]
        _, body = draft_email(self._summary(prs=prs))
        assert "@alice" in body
        assert "@bob" in body
