"""
commit_digest.py — Workflow: Commit Digest to Stakeholder Email
Reads the system prompt from claude_skills/commit_digest.md,
runs PII redaction on input, calls Claude, returns formatted email string.
"""

import os
from pathlib import Path

import anthropic

from guardrails.pii_redactor import redact_pii

_PROMPT_PATH = Path(__file__).parent.parent / "claude_skills" / "commit_digest.md"


def generate_email(commits: list[dict]) -> str:
    """
    Generate a stakeholder email from a list of commits.

    Args:
        commits: List of dicts with keys "message" and "date"
                 e.g. [{"message": "Fix login bug", "date": "2026-04-10"}, ...]

    Returns:
        Formatted plain-text email string (3 sections)
    """
    system_prompt = _PROMPT_PATH.read_text()

    commit_lines = "\n".join(
        f"- [{c['date']}] {c['message']}" for c in commits
    )
    raw_input = f"Commits:\n{commit_lines}"

    cleaned_input, redactions = redact_pii(raw_input)

    if redactions:
        print("\n[PII Redactor] Removed the following before sending to Claude:")
        for r in redactions:
            print(f"  - [{r['type']}] {r['original']!r} → {r['replacement']}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": cleaned_input}],
        metadata={"user_id": "claude-ops-assistant"},
    ) as stream:
        return stream.get_final_text().strip()
