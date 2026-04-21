1# Design Note: Claude Ops Assistant

## Prompt Strategy

All system prompts live in `claude_skills/` as plain Markdown files. This keeps them human-readable and version-controllable without being buried in code strings.

### Structured output (Issue Triage + PR Summary)
Both prompts instruct Claude to respond with **JSON only** — no markdown fences, no prose. This makes `json.loads()` reliable. The prompts define the exact keys and enumerate valid enum values (e.g. `"critical"/"high"/"medium"/"low"`) to minimize hallucinated structure.

### Free-text output (Commit Digest)
The commit digest prompt produces a plain-text email with three labeled sections. This avoids forcing JSON on a format that's inherently narrative, while still being structurally predictable (the section headings are required in the prompt).

## Guardrail Design

### Schema Validator
Validates key presence and Python types (`str`, `list`, etc.). Intentionally shallow — it doesn't recurse into list items because the risk_checklist items vary in structure and Claude generally follows the format reliably. Raising `ValueError` (not silently returning partial data) forces the caller to handle failures explicitly.

### PII Redactor
Uses regex patterns rather than an NLP model. Trade-off: faster, zero external dependencies, fully deterministic — but will miss contextual PII like full names without honorifics. The patterns cover the highest-risk categories (emails, phones, SSNs, credit cards, IPs). A redaction report is printed to stdout so users can audit what was stripped.

## Error Handling

- JSON parse errors from Claude are surfaced with the raw response for debugging
- Schema mismatches include the specific key and type that failed
- PII redaction is non-blocking — it always returns cleaned text even if no PII was found
- Network/API errors from the Anthropic SDK propagate naturally (not swallowed)

## Skill Integration

The project ships as a Claude Code skill (`/pull_request_email`) that eliminates the interactive menu entirely. When invoked, it runs the orchestrator directly without asking follow-up questions about which workflow to run.

### Invocation

```
/pull_request_email owner/repo          # uses 7-day commit window (default)
/pull_request_email owner/repo 14       # explicit lookback in days
/pull_request_email                     # prompts once for the repo, then runs
```

### How it works

The skill (`~/.claude/skills/pull_request_email/SKILL.md`) instructs Claude Code to:

1. Parse `owner/repo` and optional `days` from the invocation arguments (ask only if the repo is missing)
2. Run `python cli.py --repo REPO --days DAYS` — a thin argument-parsing wrapper around `generate_pull_request_email()`
3. Print the full email output, without paraphrasing or commentary

### `cli.py`

`cli.py` is a non-interactive entry point added alongside `main.py`. It accepts `--repo` and `--days` flags and exits with a non-zero code on failure, making it safe to call from scripts or the skill.

### Design rationale

The three underlying workflows (issue triage → PR summary → commit digest) already existed. The skill adds no new logic — it replaces the interactive menu with a single command so the user never has to answer questions about which workflow to run.

## Known Limitations

1. **PII regex misses names** — detecting personal names without an NLP model is error-prone; names are not currently redacted
2. **No retry logic** — a transient API failure will surface as an exception rather than retrying
3. **Single-turn only** — no conversation history; each workflow call is stateless
4. **Model hardcoded** — uses `claude-sonnet-4-6`; switching models requires a code change
5. **Diff input is manual** — the PR summary workflow accepts diff snippets as a string; it does not fetch from GitHub directly
