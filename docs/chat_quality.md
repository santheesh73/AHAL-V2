# AHAL Chat Quality

## What Makes AHAL Chat Different

AHAL repo chat is designed to be better than a generic assistant for repositories because it combines:

- deterministic project intelligence
- selected repository context instead of whole-repo dumping
- conversation memory
- optional LLM orchestration with deterministic validation
- evidence-backed citations
- explicit uncertainty when evidence is weak

## Answer Structure

Good AHAL chat answers should:

- start with a direct answer
- explain key details in short sections
- use bullets when the content is list-shaped
- keep evidence visible and concise
- end with useful follow-up suggestions

## Evidence Policy

- Only cite evidence selected for the current question.
- Do not dump the entire repo.
- Do not expose `.env`, secrets, tokens, private keys, or raw connection strings.
- Do not show long absolute paths in the main UI.
- Prefer short, sanitized file references.

## Uncertainty Policy

If evidence is weak or partial, the answer should say so clearly.

Preferred wording:

- `The analyzed evidence does not fully specify this, but the detected structure suggests...`
- `This appears to be...`
- `The safest conclusion from the available evidence is...`

Avoid false certainty.

## LLM Validation Policy

When LLM orchestration is enabled:

- deterministic context remains the source of truth
- primary LLM drafts a cleaner answer
- critic LLM checks for unsupported claims and dropped citations
- deterministic validation rejects hallucinated APIs, files, modules, frameworks, databases, warnings, or risky claims
- deterministic fallback is preserved when LLM output is rejected or unavailable

## Good Answer Examples

### Question

`What is built?`

Expected characteristics:

- direct answer first
- grouped capabilities
- APIs or modules mentioned when detected
- evidence included
- no duplicate endpoints
- no raw paths
- useful follow-ups

### Question

`What APIs exist?`

Expected characteristics:

- grouped API overview
- request/handler/source when known
- deduplicated routes
- evidence cited

### Question

`What should a new engineer read first?`

Expected characteristics:

- reading order
- key entry points
- gotchas
- safe-first tasks when available

### Question

`What is risky?`

Expected characteristics:

- prioritized risks
- severity or importance
- suggested tests or fixes
- uncertainty when needed

## Rejected Bad Answers

Reject answers that:

- invent APIs, files, modules, commands, env vars, or schemas
- claim compliance, production readiness, or security guarantees
- dump raw scanner artifacts
- show raw noisy paths
- expose `.env.example` or `mongodb://` evidence in primary UI
- repeat the same summary paragraph over and over
