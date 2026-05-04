# AHAL Public Demo Prompt

Use this prompt when preparing a public AHAL AI Frontend v2 demo, release rehearsal, handoff, or regression check.

## Goal

Show a production-grade developer SaaS experience that keeps live backend integration, premium motion, and trustworthy presentation quality.

## Required Demo Journey

1. Open the landing page.
2. Start a repo analysis session.
3. Wait for the dashboard to complete.
4. Verify cleaned intelligence.
5. Open Repo Chat and ask `What is built?`
6. Open Downloads and export PDF / JSON.
7. Load Test Gap Report.
8. Load Onboarding Report.
9. Create Repo Index.
10. Run Delta Scan or show a clean disabled/friendly state.

## Product Rules

- Preserve real backend integration.
- Do not silently switch to mock data when `VITE_AHAL_API_URL` is configured.
- Do not expose secrets, access tokens, `.env`, credentials, private keys, or raw connection strings.
- Do not show raw JSON as the primary UI.
- Do not show raw stack traces.
- Do not remove premium animations or route transitions.

## ContextBridge Regression Criteria

For the AHAL-AI / ContextBridge style repo:

- Do not display `content management application` when explicit metadata says developer tool.
- Do not show MongoDB as a language.
- Do not duplicate `POST /analyze` or `GET /status` variants.
- Do not show `types/index.ts initializes FastAPI`.
- Do not show long nested paths in primary UI.
- Do not expose `.env.example` or raw `mongodb://` evidence in primary UI.
- Test gap, onboarding, repo index, delta scan, chat, and downloads must remain reachable from dashboard.

## Acceptance

- Dashboard summary reads like a developer intelligence platform, not a CMS.
- Trust-adapter cleanup remains visible in summary, tech stack, API surface, workflow, and evidence.
- Chat evidence is short, deduplicated, and grounded.
- Downloads succeed or fail gracefully with user-facing copy.
- Repo-only success paths remain reachable from the dashboard action center.
