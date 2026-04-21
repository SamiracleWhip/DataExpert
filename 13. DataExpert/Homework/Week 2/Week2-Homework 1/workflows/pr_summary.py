"""
pr_summary.py — Workflow: PR Summary Generator
Reads the system prompt from claude_skills/pr_summary.md,
runs PII redaction on input, calls Claude, validates the output schema.
"""

import json
import os
from pathlib import Path

import anthropic

from guardrails.pii_redactor import redact_pii
from guardrails.schema_validator import validate_schema

_PROMPT_PATH = Path(__file__).parent.parent / "claude_skills" / "pr_summary.md"

_SCHEMA = {
    "summary": str,
    "risk_checklist": list,
}


def summarize_pr(title: str, description: str, diff_snippets: str = "") -> dict:
    """
    Summarize a pull request and produce a risk checklist.

    Args:
        title: PR title
        description: PR description / body
        diff_snippets: Optional key diff excerpts (not the full diff)

    Returns:
        Validated dict with keys: summary, risk_checklist
    """
    system_prompt = _PROMPT_PATH.read_text()

    raw_input = f"PR Title: {title}\n\nDescription:\n{description}"
    if diff_snippets.strip():
        raw_input += f"\n\nDiff Snippets:\n{diff_snippets}"

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
        raw_response = stream.get_final_text().strip()

    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    if raw_response.startswith("```"):
        raw_response = raw_response.split("```", 2)[1]
        if raw_response.startswith("json"):
            raw_response = raw_response[4:]
        raw_response = raw_response.strip()

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned non-JSON response: {e}\n\nRaw: {raw_response}")

    validate_schema(result, _SCHEMA)

    return result
