"""
pull_request_email.py — Orchestrator: Pull Request Email Digest

Automatically fetches open issues, open PRs, and recent commits from a GitHub
repo, runs triage and summarization on each, then synthesizes everything into
one stakeholder email. No manual input required beyond the repo name.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from github import Github, GithubException

from guardrails.pii_redactor import redact_pii
from github_client import fetch_commits
from workflows.issue_triage import triage_issue
from workflows.pr_summary import summarize_pr

_PROMPT_PATH = Path(__file__).parent.parent / "claude_skills" / "pull_request_email.md"


def generate_pull_request_email(
    repo: str,
    since_days: int = 7,
    issue_since: datetime | None = None,
    issue_until: datetime | None = None,
) -> str:
    """
    Orchestrate all three sub-workflows and synthesize a single stakeholder email.

    Args:
        repo: Repository in "owner/repo" format
        since_days: How many days back to look for commits (default: 7)
        issue_since: Only include issues created on or after this date (UTC).
                     When provided, all issue states are fetched (not just open).
        issue_until: Only include issues created on or before this date (UTC).

    Returns:
        Formatted plain-text stakeholder email string
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    g = Github(token) if token else Github()

    try:
        repository = g.get_repo(repo)
    except GithubException as e:
        raise ValueError(f"Could not access repo {repo}: {e.data.get('message', e)}")

    # 1. Fetch and triage issues — all states when a date range is given, open-only otherwise
    if issue_since or issue_until:
        kwargs = {"state": "all"}
        if issue_since:
            kwargs["since"] = issue_since
        raw_issues = [i for i in repository.get_issues(**kwargs) if not i.pull_request]
        if issue_since:
            raw_issues = [i for i in raw_issues if i.created_at >= issue_since]
        if issue_until:
            raw_issues = [i for i in raw_issues if i.created_at <= issue_until]
        state_label = "date-filtered"
    else:
        raw_issues = [i for i in repository.get_issues(state="open") if not i.pull_request]
        state_label = "open"

    triaged_issues = []
    if raw_issues:
        print(f"  Triaging {len(raw_issues)} {state_label} issue(s)...")
        for issue in raw_issues[:10]:
            comments_text = "\n\n".join(
                f"@{c.user.login}: {c.body}" for c in issue.get_comments()
            )
            try:
                triage = triage_issue(issue.title, issue.body or "", comments_text)
                triaged_issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    **triage,
                })
            except Exception as e:
                print(f"    [Warning] Could not triage issue #{issue.number}: {e}")
    else:
        print(f"  No {state_label} issues found.")

    # 2. Fetch and summarize open PRs (cap at 10)
    open_prs = list(repository.get_pulls(state="open"))
    summarized_prs = []
    if open_prs:
        print(f"  Summarizing {len(open_prs)} open PR(s)...")
        for pr in open_prs[:10]:
            files = list(pr.get_files())
            diff_lines = []
            for f in files[:10]:
                diff_lines.append(f"--- {f.filename} (+{f.additions}/-{f.deletions})")
                if f.patch:
                    diff_lines.append("\n".join(f.patch.splitlines()[:20]))
                diff_lines.append("")
            try:
                summary = summarize_pr(pr.title, pr.body or "", "\n".join(diff_lines))
                summarized_prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    **summary,
                })
            except Exception as e:
                print(f"    [Warning] Could not summarize PR #{pr.number}: {e}")
    else:
        print("  No open pull requests found.")

    # 3. Fetch recent commits
    commits = fetch_commits(repo, since_days=since_days)
    print(f"  Found {len(commits)} commit(s) in the last {since_days} day(s).")

    # 4. Synthesize all results into one email
    print("  Synthesizing final email...")
    return _synthesize_email(repo, triaged_issues, summarized_prs, commits)


def _synthesize_email(
    repo: str,
    issues: list[dict],
    prs: list[dict],
    commits: list[dict],
) -> str:
    system_prompt = _PROMPT_PATH.read_text()

    parts = [f"Repository: {repo}\n"]

    parts.append("## Open Issues")
    if issues:
        for issue in issues:
            parts.append(f"Issue #{issue['number']}: {issue['title']}")
            parts.append(f"  Severity: {issue['severity']} | Priority: {issue['priority']}")
            parts.append(f"  Labels: {', '.join(issue['labels'])}")
            parts.append(f"  Recommended Owner: {issue['recommended_owner']}")
            parts.append("")
    else:
        parts.append("No open issues.\n")

    parts.append("## Active Pull Requests")
    if prs:
        for pr in prs:
            parts.append(f"PR #{pr['number']}: {pr['title']}")
            parts.append(f"  Summary: {pr['summary']}")
            concerns = [i for i in pr["risk_checklist"] if i.get("status") == "concern"]
            needs_review = [i for i in pr["risk_checklist"] if i.get("status") == "needs_review"]
            if concerns:
                parts.append(f"  Concerns: {'; '.join(i['item'] for i in concerns)}")
            if needs_review:
                parts.append(f"  Needs Review: {'; '.join(i['item'] for i in needs_review)}")
            parts.append("")
    else:
        parts.append("No open pull requests.\n")

    parts.append("## Recent Commits")
    if commits:
        for c in commits:
            parts.append(f"- [{c['date']}] {c['message']}")
    else:
        parts.append("No recent commits.")

    raw_input = "\n".join(parts)
    cleaned_input, redactions = redact_pii(raw_input)

    if redactions:
        print("\n[PII Redactor] Removed the following before sending to Claude:")
        for r in redactions:
            print(f"  - [{r['type']}] {r['original']!r} → {r['replacement']}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": cleaned_input}],
        metadata={"user_id": "claude-ops-assistant"},
    ) as stream:
        return stream.get_final_text().strip()
