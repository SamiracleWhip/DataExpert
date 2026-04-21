"""
cli.py — Non-interactive entry point for the Pull Request Email Digest.

Usage:
    python3 cli.py --repo owner/repo
    python3 cli.py --repo owner/repo --days 14
    python3 cli.py --repo owner/repo --issue-since 2025-07-01 --issue-until 2025-07-31

Designed to be called by the /pull_request_email Claude Code skill.
"""
import argparse
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from workflows.pull_request_email import generate_pull_request_email


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Pull Request Email Digest for a GitHub repository.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        metavar="owner/repo",
        help="GitHub repository in owner/repo format (e.g. torvalds/linux)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        metavar="N",
        help="How many days back to include in the commit history (default: 7)",
    )
    parser.add_argument(
        "--issue-since",
        metavar="YYYY-MM-DD",
        help="Only include issues created on or after this date",
    )
    parser.add_argument(
        "--issue-until",
        metavar="YYYY-MM-DD",
        help="Only include issues created on or before this date",
    )
    args = parser.parse_args()

    issue_since = _parse_date(args.issue_since) if args.issue_since else None
    issue_until = _parse_date(args.issue_until) if args.issue_until else None

    range_label = ""
    if issue_since or issue_until:
        range_label = f" | issues {args.issue_since or '?'} → {args.issue_until or 'now'}"

    print(f"\nFetching activity from {args.repo} (commits: last {args.days} day(s){range_label})...\n")

    try:
        email = generate_pull_request_email(
            args.repo,
            since_days=args.days,
            issue_since=issue_since,
            issue_until=issue_until,
        )
        print("\n" + "=" * 60)
        print(email)
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"[Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
