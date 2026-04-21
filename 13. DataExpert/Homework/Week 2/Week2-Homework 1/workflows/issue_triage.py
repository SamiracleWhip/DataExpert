"""
issue_triage.py — Workflow: GitHub Issue Triage
Reads the system prompt from claude_skills/issue_triage.md,
runs PII redaction on input, calls Claude, validates the output schema.
"""

import json
import os
from pathlib import Path

import anthropic

from guardrails.pii_redactor import redact_pii
from guardrails.schema_validator import validate_schema

_PROMPT_PATH = Path(__file__).parent.parent / "claude_skills" / "issue_triage.md"

_SCHEMA = {
    "severity": str,
    "priority": str,
    "labels": list,
    "recommended_owner": str,
}


def triage_issue(title: str, body: str, comments: str = "") -> dict:
    """
    Triage a GitHub issue.

    Args:
        title: Issue title
        body: Issue body/description
        comments: Optional concatenated comments string

    Returns:
        Validated dict with keys: severity, priority, labels, recommended_owner
    """
    system_prompt = _PROMPT_PATH.read_text()

    raw_input = f"Title: {title}\n\nBody:\n{body}"
    if comments.strip():
        raw_input += f"\n\nComments:\n{comments}"

    cleaned_input, redactions = redact_pii(raw_input)

    if redactions:
        print("\n[PII Redactor] Removed the following before sending to Claude:")
        for r in redactions:
            print(f"  - [{r['type']}] {r['original']!r} → {r['replacement']}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=512,
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
