"""
github_client.py — Live GitHub data fetcher
Fetches issues, PRs, and commits from GitHub using PyGithub.
Reads GITHUB_TOKEN from env; falls back to unauthenticated (60 req/hr limit) with a warning.
"""

import os
from datetime import datetime, timedelta, timezone

from github import Github, GithubException


def _get_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print(
            "[Warning] GITHUB_TOKEN not set — using unauthenticated GitHub API "
            "(rate limited to 60 requests/hour). Set GITHUB_TOKEN in .env for higher limits."
        )
        return Github()
    return Github(token)


def fetch_issue(repo: str, issue_number: int) -> dict:
    """
    Fetch a GitHub issue and its comments.

    Args:
        repo: Repository in "owner/repo" format (e.g. "anthropics/anthropic-sdk-python")
        issue_number: The issue number

    Returns:
        {"title": str, "body": str, "comments": str}
    """
    g = _get_client()
    try:
        repository = g.get_repo(repo)
        issue = repository.get_issue(issue_number)
    except GithubException as e:
        raise ValueError(f"Could not fetch issue #{issue_number} from {repo}: {e.data.get('message', e)}")

    comments_text = ""
    comments = list(issue.get_comments())
    if comments:
        comments_text = "\n\n".join(
            f"@{c.user.login}: {c.body}" for c in comments
        )

    return {
        "title": issue.title,
        "body": issue.body or "",
        "comments": comments_text,
    }


def fetch_pr(repo: str, pr_number: int) -> dict:
    """
    Fetch a GitHub PR, its description, and a snippet of the diff.

    Args:
        repo: Repository in "owner/repo" format
        pr_number: The PR number

    Returns:
        {"title": str, "description": str, "diff_snippets": str}
    """
    g = _get_client()
    try:
        repository = g.get_repo(repo)
        pr = repository.get_pull(pr_number)
    except GithubException as e:
        raise ValueError(f"Could not fetch PR #{pr_number} from {repo}: {e.data.get('message', e)}")

    # Collect changed file summaries as diff snippets (avoids huge raw diffs)
    files = list(pr.get_files())
    diff_lines = []
    for f in files[:10]:  # cap at 10 files to stay within token budget
        diff_lines.append(f"--- {f.filename} (+{f.additions}/-{f.deletions})")
        if f.patch:
            # Take first 20 lines of each file's patch
            patch_preview = "\n".join(f.patch.splitlines()[:20])
            diff_lines.append(patch_preview)
        diff_lines.append("")

    return {
        "title": pr.title,
        "description": pr.body or "",
        "diff_snippets": "\n".join(diff_lines),
    }


def fetch_commits(repo: str, since_days: int = 7, branch: str = "main") -> list[dict]:
    """
    Fetch commits from a branch within the last N days.

    Args:
        repo: Repository in "owner/repo" format
        since_days: How many days back to look (default: 7)
        branch: Branch name (default: "main")

    Returns:
        List of {"date": "YYYY-MM-DD", "message": str}, newest first
    """
    g = _get_client()
    try:
        repository = g.get_repo(repo)
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        commits = repository.get_commits(sha=branch, since=since)
    except GithubException as e:
        raise ValueError(f"Could not fetch commits from {repo}/{branch}: {e.data.get('message', e)}")

    result = []
    for commit in commits:
        date_str = commit.commit.author.date.strftime("%Y-%m-%d")
        # Use only the first line of the commit message
        message = commit.commit.message.splitlines()[0]
        result.append({"date": date_str, "message": message})

    return result
