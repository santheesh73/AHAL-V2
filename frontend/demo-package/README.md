# AHAL AI Frontend v2

AHAL AI Frontend v2 is the React + Vite interface for evidence-backed repository intelligence. It connects to the live FastAPI backend, normalizes noisy scanner output before rendering, and keeps dashboard, chat, downloads, onboarding, test gap, repo index, and delta workflows inside one product surface.

## Local Run

Backend:

```bash
cd "C:\Users\babus\OneDrive\Desktop\AHAL v2"
python -m app.main
```

Frontend:

```bash
cd "C:\Users\babus\OneDrive\Desktop\AHAL v2\frontend"
npm install
npm run dev
```

The frontend expects:

```env
VITE_AHAL_API_URL=http://localhost:8000
```

Demo mode is only used when `VITE_AHAL_API_URL` is missing or empty.

## Quality Gates

```bash
npm run lint
npm run typecheck
npm run build
```

## Public Demo Flow

1. Open `http://localhost:5173`
2. Click `Analyze Project` or `View Demo Dashboard`
3. Use the prefilled repo session for `https://github.com/bsrikumar855-dot/AHAL-AI`
4. Wait for the dashboard to complete
5. Open Repo Chat
6. Download PDF / Markdown / LaTeX / JSON
7. Load Test Gap Report
8. Generate Onboarding Report
9. Create Repo Index
10. Run Delta Scan

Detailed runbook:

- [DEMO_CHECKLIST.md](./DEMO_CHECKLIST.md)
- [QA_CHECKLIST.md](./QA_CHECKLIST.md)
- [PUBLIC_DEMO_PROMPT.md](./PUBLIC_DEMO_PROMPT.md)

## Packaging A Public Demo Bundle

Create a distributable frontend demo package:

```bash
npm run package:demo
```

This writes `frontend/demo-package/` with:

- the built `dist/` app
- this README
- the QA and demo checklists
- the public demo prompt and regression brief
- a small manifest for distribution handoff

## Regression Criteria

For the AHAL-AI / ContextBridge style repo:

- Do not display `content management application` when explicit metadata says developer tool.
- Do not show MongoDB as a language.
- Do not duplicate `POST /analyze` or `GET /status` variants.
- Do not show `types/index.ts initializes FastAPI`.
- Do not show long nested paths in primary UI.
- Do not expose `.env.example` or raw `mongodb://` evidence in primary UI.
- Test gap, onboarding, repo index, delta scan, chat, and downloads must remain reachable from dashboard.

## Release Notes

- Live backend integration is preserved.
- Mock/demo data is only used when no backend URL is configured.
- The trust adapter is the frontend presentation boundary for noisy backend intelligence.
