"""
pii_redactor.py — Guardrail 2
Scrubs common PII patterns from text before sending it to Claude.
Returns (cleaned_text, redaction_report) where redaction_report is a list of
dicts describing what was redacted.
"""

import re

# Each entry: (label, compiled_regex, replacement_token)
_PATTERNS = [
    (
        "email",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE),
        "[REDACTED_EMAIL]",
    ),
    (
        "phone_number",
        re.compile(
            r"(?<!\d)(\+?1[\s\-.]?)?(\(?\d{3}\)?[\s\-.]?)(\d{3}[\s\-.]?\d{4})(?!\d)"
        ),
        "[REDACTED_PHONE]",
    ),
    (
        "ssn",
        re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
        "[REDACTED_SSN]",
    ),
    (
        "credit_card",
        re.compile(r"\b(?:\d[ \-]?){13,16}\b"),
        "[REDACTED_CC]",
    ),
    (
        "ip_address",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "[REDACTED_IP]",
    ),
]


def redact_pii(text: str) -> tuple[str, list[dict]]:
    """
    Scan `text` for PII and replace matches with placeholder tokens.

    Returns:
        cleaned_text (str): text with PII replaced
        report (list[dict]): list of {"type": ..., "original": ..., "replacement": ...}
    """
    report = []
    cleaned = text

    for label, pattern, replacement in _PATTERNS:
        matches = pattern.findall(cleaned)
        if matches:
            # findall returns tuples for grouped patterns; flatten to strings
            flat_matches = [
                "".join(m) if isinstance(m, tuple) else m for m in matches
            ]
            for original in flat_matches:
                if original and original not in [r["original"] for r in report]:
                    report.append(
                        {"type": label, "original": original, "replacement": replacement}
                    )
            cleaned = pattern.sub(replacement, cleaned)

    return cleaned, report
