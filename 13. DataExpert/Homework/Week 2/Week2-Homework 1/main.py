import json
import os

from dotenv import load_dotenv

load_dotenv()

from workflows.issue_triage import triage_issue
from workflows.pr_summary import summarize_pr
from workflows.commit_digest import generate_email
from workflows.pull_request_email import generate_pull_request_email
from github_client import fetch_issue, fetch_pr, fetch_commits


def run_issue_triage():
    print("\n--- GitHub Issue Triage ---")
    repo = input("Repo (owner/repo): ").strip()
    try:
        issue_number = int(input("Issue number: ").strip())
    except ValueError:
        print("[Error] Issue number must be an integer.")
        return

    print(f"\nFetching issue #{issue_number} from {repo}...")
    try:
        issue = fetch_issue(repo, issue_number)
    except ValueError as e:
        print(f"[Error] {e}")
        return

    print(f"  Title: {issue['title']}")
    print(f"  Body:  {len(issue['body'])} chars")
    print(f"  Comments: {len(issue['comments'])} chars")

    print("\nAnalyzing issue...")
    try:
        result = triage_issue(issue["title"], issue["body"], issue["comments"])
        print("\n[Result]")
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"\n[Error] {e}")


def run_pr_summary():
    print("\n--- PR Summary Generator ---")
    repo = input("Repo (owner/repo): ").strip()
    try:
        pr_number = int(input("PR number: ").strip())
    except ValueError:
        print("[Error] PR number must be an integer.")
        return

    print(f"\nFetching PR #{pr_number} from {repo}...")
    try:
        pr = fetch_pr(repo, pr_number)
    except ValueError as e:
        print(f"[Error] {e}")
        return

    print(f"  Title: {pr['title']}")
    print(f"  Description: {len(pr['description'])} chars")
    print(f"  Diff snippets: {len(pr['diff_snippets'])} chars")

    print("\nSummarizing PR...")
    try:
        result = summarize_pr(pr["title"], pr["description"], pr["diff_snippets"])
        print("\n[Result]")
        print(f"Summary: {result['summary']}")
        print("\nRisk Checklist:")
        for item in result["risk_checklist"]:
            status_icon = {"ok": "✓", "needs_review": "?", "concern": "!"}.get(
                item.get("status", ""), "-"
            )
            print(f"  [{status_icon}] {item.get('item', item)}")
    except ValueError as e:
        print(f"\n[Error] {e}")


def run_commit_digest():
    print("\n--- Commit Digest to Email ---")
    repo = input("Repo (owner/repo): ").strip()
    branch = input("Branch (default: main): ").strip() or "main"
    try:
        days_input = input("How many days back? (default: 7): ").strip()
        since_days = int(days_input) if days_input else 7
    except ValueError:
        print("[Error] Days must be an integer.")
        return

    print(f"\nFetching commits from {repo}/{branch} (last {since_days} days)...")
    try:
        commits = fetch_commits(repo, since_days=since_days, branch=branch)
    except ValueError as e:
        print(f"[Error] {e}")
        return

    if not commits:
        print(f"No commits found in the last {since_days} days on branch '{branch}'.")
        return

    print(f"  Found {len(commits)} commit(s).")

    print("\nGenerating stakeholder email...")
    try:
        email = generate_email(commits)
        print("\n" + "=" * 60)
        print(email)
        print("=" * 60)
    except Exception as e:
        print(f"\n[Error] {e}")


def run_pull_request_email():
    print("\n--- Pull Request Email Digest ---")
    repo = input("Repo (owner/repo): ").strip()
    try:
        days_input = input("How many days back for commits? (default: 7): ").strip()
        since_days = int(days_input) if days_input else 7
    except ValueError:
        print("[Error] Days must be an integer.")
        return

    print(f"\nFetching activity from {repo}...")
    try:
        email = generate_pull_request_email(repo, since_days=since_days)
        print("\n" + "=" * 60)
        print(email)
        print("=" * 60)
    except Exception as e:
        print(f"\n[Error] {e}")


def main():
    print("\n=== Claude Ops Assistant ===")

    while True:
        print("\n1. GitHub Issue Triage")
        print("2. PR Summary Generator")
        print("3. Commit Digest to Email")
        print("4. Pull Request Email Digest (all-in-one)")
        print("5. Quit")

        choice = input("\nSelect an option (1-5): ").strip()

        if choice == "1":
            run_issue_triage()
        elif choice == "2":
            run_pr_summary()
        elif choice == "3":
            run_commit_digest()
        elif choice == "4":
            run_pull_request_email()
        elif choice == "5":
            print("Bye.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()
