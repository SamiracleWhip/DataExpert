# Claude Ops Assistant

A CLI tool that uses Claude to triage GitHub issues, summarize PRs, and generate stakeholder emails — with safety guardrails built in.

## Setup

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure your API key**

Edit `.env` and set your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

3. **Run the assistant**

```bash
python main.py
```

## Features

| Option | What it does |
|--------|-------------|
| 1. GitHub Issue Triage | Analyzes an issue and returns severity, priority, labels, and recommended owner as JSON |
| 2. PR Summary Generator | Summarizes a PR and produces a risk checklist |
| 3. Commit Digest to Email | Turns a list of commits into a formatted stakeholder email |
| 4. Pull Request Email Digest | **All-in-one orchestrator** — fetches open issues, open PRs, and recent commits automatically, runs triage + summarization on each, and synthesizes a single stakeholder email. Only requires a repo name. |

## Guardrails

Every workflow passes through two guardrails before/after calling Claude:

- **PII Redaction** (`guardrails/pii_redactor.py`): strips emails, phone numbers, SSNs, credit card numbers, and IP addresses from input before sending to Claude. Prints a redaction report.
- **Schema Validation** (`guardrails/schema_validator.py`): validates that Claude's JSON output contains all expected keys with correct types. Raises a clear error if the shape is wrong.

## Sample Inputs

The `samples/` directory contains three realistic test inputs:

- `sample_issue.json` — a SQL injection bug report with embedded PII in comments
- `sample_pr.json` — a session auth migration PR
- `sample_commits.json` — a week's worth of security/auth commits

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
