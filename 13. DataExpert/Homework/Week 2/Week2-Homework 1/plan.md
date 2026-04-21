# Plan: Claude Ops Assistant — GitHub Triage + Email Drafting

## Context
Building a mini workflow assistant for Week 2 homework. The project starts from an empty directory.
Goal: use Claude to triage GitHub issues, summarize PRs, and generate stakeholder emails — all with safety guardrails baked in.
The `claude_skills/` folder must remain visible (not hidden) and contain the actual prompt files used.

---

## Project Structure
```
Week 2/
├── main.py                        # CLI entry point (menu-driven)
├── requirements.txt
├── README.md
├── design_note.md
│
├── claude_skills/                 # Prompt files (visible, human-readable)
│   ├── issue_triage.md
│   ├── pr_summary.md
│   └── commit_digest.md
│
├── workflows/
│   ├── __init__.py
│   ├── issue_triage.py            # Feature 1
│   ├── pr_summary.py              # Feature 2
│   └── commit_digest.py           # Feature 3
│
├── guardrails/
│   ├── __init__.py
│   ├── schema_validator.py        # Guardrail 1: validate JSON output shape
│   └── pii_redactor.py            # Guardrail 2: strip PII before sending to Claude
│
└── samples/                       # 3 sample inputs + outputs
    ├── sample_issue.json
    ├── sample_pr.json
    └── sample_commits.json
```

---

## Sequential Build Steps

### Step 1 — Setup
- Create `requirements.txt` with `anthropic`, `python-dotenv`
- Create `.env` with `ANTHROPIC_API_KEY=...` (user fills in)
- Create `main.py` skeleton with a CLI menu (3 options + quit)

### Step 2 — `claude_skills/` Prompts (write these first, before code)
Each file is a plain-text prompt used by the corresponding workflow.

- **`issue_triage.md`**: System prompt instructing Claude to output severity, priority, labels, recommended owner/team as JSON
- **`pr_summary.md`**: System prompt for concise technical summary + risk checklist as JSON
- **`commit_digest.md`**: System prompt to produce a stakeholder email with three sections: What Changed, Risk/Impact, Action Needed

### Step 3 — Guardrails (build before workflows, since workflows depend on them)
- **`schema_validator.py`**: Takes a Claude response dict and an expected schema (keys + types). Returns validated output or raises a clear error.
- **`pii_redactor.py`**: Before sending input to Claude, scrub common PII patterns (emails, phone numbers, names flagged with regex). Returns cleaned text + a list of what was redacted.

### Step 4 — Workflow: Issue Triage (`workflows/issue_triage.py`)
- Reads the prompt from `claude_skills/issue_triage.md`
- Accepts: title, body, comments (strings)
- Runs PII redaction → calls Claude → validates output schema
- Returns: `{ severity, priority, labels, recommended_owner }`

### Step 5 — Workflow: PR Summary (`workflows/pr_summary.py`)
- Reads the prompt from `claude_skills/pr_summary.md`
- Accepts: PR title, description, diff snippets
- Runs PII redaction → calls Claude → validates output schema
- Returns: `{ summary, risk_checklist[] }`

### Step 6 — Workflow: Commit Digest to Email (`workflows/commit_digest.py`)
- Reads the prompt from `claude_skills/commit_digest.md`
- Accepts: list of commits (message + date)
- Runs PII redaction → calls Claude → returns formatted email string (3 sections)

### Step 7 — Wire into `main.py`
- Menu option 1 → issue triage (prompts user for inputs)
- Menu option 2 → PR summary
- Menu option 3 → commit digest → email

### Step 8 — Sample Inputs + Outputs
- Create 3 JSON files in `samples/` with realistic test data
- Run each workflow against the samples and capture outputs

### Step 9 — Docs
- `README.md`: setup steps, how to run, env vars needed
- `design_note.md`: prompt strategy, error handling, known limitations

---

## Guardrails Chosen
1. **Schema validation** — every structured output (issue triage, PR summary) is validated against an expected JSON shape before being returned
2. **PII redaction** — user input is scrubbed of emails, phone numbers, and other PII patterns before being sent to Claude; a redaction report is shown

---

## Verification
- Run `python main.py` and exercise each of the 3 menu options with sample inputs
- Deliberately pass in input with PII to confirm the redactor strips it
- Deliberately break the schema (mock a bad Claude response) to confirm the validator catches it
