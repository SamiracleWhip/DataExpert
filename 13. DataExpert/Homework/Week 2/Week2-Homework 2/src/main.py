"""
main.py — CLI entry point for Release Radar.

Usage:
    python -m src.main                          # use default data/ and output/ dirs
    python -m src.main --data data/ --out output/
    python -m src.main --week-start 2026-04-07  # override the week window

Outputs:
    output/summary_YYYY-MM-DD.txt   — plain-text engineering report
    output/email_YYYY-MM-DD.txt     — stakeholder email draft
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.ingest import load_all
from src.summarize import build_summary, format_plain_text
from src.email_draft import draft_email


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Release Radar — weekly PR digest generator")
    p.add_argument("--data", default="data", help="Directory containing mock JSON files")
    p.add_argument("--out", default="output", help="Directory to write output files")
    p.add_argument(
        "--week-start",
        default=None,
        help="Override week start date (YYYY-MM-DD). Defaults to the current ISO week.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)

    data_dir = Path(args.data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Optional week override
    week_start: datetime | None = None
    if args.week_start:
        week_start = datetime.fromisoformat(args.week_start).replace(tzinfo=timezone.utc)

    # --- Ingest ---
    print("[1/3] Loading PR and commit data...")
    prs, commits = load_all(data_dir)
    print(f"      {len(prs)} PRs, {len(commits)} commits loaded.")

    # --- Summarise ---
    print("[2/3] Building weekly summary...")
    summary = build_summary(prs, commits, week_start=week_start)
    plain_report = format_plain_text(summary)

    week_label = summary["week_start"].strftime("%Y-%m-%d")
    summary_path = out_dir / f"summary_{week_label}.txt"
    summary_path.write_text(plain_report, encoding="utf-8")
    print(f"      Summary written → {summary_path}")

    # --- Draft email ---
    print("[3/3] Drafting stakeholder email...")
    subject, body = draft_email(summary)

    email_path = out_dir / f"email_{week_label}.txt"
    email_path.write_text(body, encoding="utf-8")
    print(f"      Email draft written → {email_path}")
    print(f"      Subject: {subject}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
