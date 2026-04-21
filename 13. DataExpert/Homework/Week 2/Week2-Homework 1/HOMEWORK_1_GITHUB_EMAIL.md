# Homework 1 — Claude Skills for GitHub + Email Workflows

## Title
**Claude Ops Assistant: GitHub Triage + Email Drafting**

## Learning Goals
Students will:
1. Design practical AI workflows for software-team operations.
2. Use Claude to automate GitHub understanding (issues/PRs/commits).
3. Use Claude to draft professional, context-aware emails.
4. Apply guardrails (privacy, hallucination control, validation).

## Task
Build a mini assistant workflow (CLI/app/notebook) that uses Claude to do all of the following.

### Required Features
1. **GitHub Issue Triage**
   - Input: issue text (title/body/comments)
   - Output: severity, priority, labels, and recommended owner/team

2. **PR Summary Generator**
   - Input: PR title/description/diff snippets
   - Output: concise technical summary + risk checklist

3. **Commit Digest to Email**
   - Input: list of commits from a date range
   - Output: polished stakeholder email with sections:
     - What changed
     - Risk/Impact
     - Action needed

4. **Safety/Quality Guardrails**
   - Must include at least 2 of:
     - PII redaction
     - uncertainty statements
     - citation to source text snippets
     - “insufficient context” fallback mode
     - schema validation for output

## Deliverables
- Source code
- A `claude_skills/` folder containing the Claude skills/prompts used for the workflow
- `README.md` with setup + usage
- 3 sample inputs + outputs
- Short design note (1–2 pages) covering:
  - prompt strategy
  - error handling
  - known limitations