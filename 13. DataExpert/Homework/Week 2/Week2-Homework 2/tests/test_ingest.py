"""Tests for src/ingest.py"""

import json
import tempfile
from pathlib import Path

import pytest

from src.ingest import load_prs, load_commits, load_all


@pytest.fixture()
def data_dir(tmp_path):
    """Write minimal JSON fixtures into a temp directory."""
    prs = [
        {
            "id": 1, "number": 1,
            "title": "feat: test PR",
            "author": "alice",
            "state": "merged",
            "created_at": "2026-04-07T09:00:00Z",
            "merged_at": "2026-04-08T10:00:00Z",
            "closed_at": "2026-04-08T10:00:00Z",
            "url": "https://github.com/org/repo/pull/1",
            "labels": ["feature"],
            "reviewers": ["bob"],
            "comments": 2,
            "additions": 50,
            "deletions": 10,
        }
    ]
    commits = [
        {
            "sha": "abc1234",
            "message": "feat: initial commit",
            "author": "alice",
            "timestamp": "2026-04-07T09:05:00Z",
            "pr_id": 1,
            "additions": 50,
            "deletions": 10,
        }
    ]
    (tmp_path / "mock_prs.json").write_text(json.dumps(prs))
    (tmp_path / "mock_commits.json").write_text(json.dumps(commits))
    return tmp_path


class TestLoadPRs:
    def test_returns_list(self, data_dir):
        result = load_prs(data_dir)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_normalises_timestamps(self, data_dir):
        pr = load_prs(data_dir)[0]
        from datetime import timezone
        assert pr["created_at"].tzinfo is not None
        assert pr["merged_at"].tzinfo is not None

    def test_null_merged_at_becomes_none(self, data_dir, tmp_path):
        prs = [
            {
                "id": 2, "number": 2,
                "title": "open PR",
                "author": "bob",
                "state": "open",
                "created_at": "2026-04-10T09:00:00Z",
                "merged_at": None,
                "closed_at": None,
                "url": "https://github.com/org/repo/pull/2",
                "labels": [],
                "reviewers": [],
                "comments": 0,
                "additions": 0,
                "deletions": 0,
            }
        ]
        (tmp_path / "mock_prs.json").write_text(json.dumps(prs))
        (tmp_path / "mock_commits.json").write_text("[]")
        pr = load_prs(tmp_path)[0]
        assert pr["merged_at"] is None

    def test_required_fields_present(self, data_dir):
        pr = load_prs(data_dir)[0]
        for field in ("id", "number", "title", "author", "state", "url", "labels", "reviewers"):
            assert field in pr


class TestLoadCommits:
    def test_returns_list(self, data_dir):
        commits = load_commits(data_dir)
        assert len(commits) == 1

    def test_normalises_timestamp(self, data_dir):
        commit = load_commits(data_dir)[0]
        assert commit["timestamp"].tzinfo is not None

    def test_fields(self, data_dir):
        commit = load_commits(data_dir)[0]
        for field in ("sha", "message", "author", "timestamp", "pr_id"):
            assert field in commit


class TestLoadAll:
    def test_returns_tuple(self, data_dir):
        prs, commits = load_all(data_dir)
        assert isinstance(prs, list)
        assert isinstance(commits, list)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_prs(tmp_path)
