# AHAL AI Frontend v2 QA Checklist

## Start Commands

Backend:
```bash
python -m app.main
```

Frontend:
```bash
npm run dev
```

Production build:
```bash
npm run build
```

## Code Session Test

Use this snippet in the Code Session flow:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/analyze")
def analyze(payload: dict):
    return {"status": "received"}
```

Expected:
- Analyze creates a session
- Dashboard polling completes
- Intelligence cards render
- Chat works
- Downloads work

## Flow Checks

1. Code session test
- Open `http://localhost:5173`
- Go to Analyze
- Submit the code snippet above
- Confirm redirect to dashboard

2. Folder upload test
- Upload a `.zip` archive
- Confirm loading state appears
- Confirm redirect to dashboard when accepted

3. Repo URL test
- Submit a GitHub URL
- Confirm loading state appears
- Confirm redirect to dashboard when accepted

4. Dashboard check
- Summary uses clean product-facing language
- No duplicate API endpoints
- MongoDB is not shown under languages
- Workflow does not claim frontend files initialize FastAPI
- Evidence list is short, deduplicated, and path-sanitized
- Action Center buttons show loading and status messages

5. Chat check
- Ask a question
- Confirm loading state appears
- Evidence chips are short and deduplicated
- LLM fallback warning renders as deterministic wording

6. Downloads check
- Open Downloads from dashboard
- Confirm report preview renders
- Confirm downloads are disabled before completion
- Download PDF, Markdown, LaTeX, and JSON after completion

7. Test gap check
- Click Load Test Gaps
- Confirm loading state and either content or empty/unavailable message

8. Onboarding check
- Click Generate Onboarding Report
- Confirm loading state and either content or empty/unavailable message

9. Index / delta scan check
- Click Create Repo Index
- Confirm index ID appears
- Click Run Delta Scan
- Confirm success message and diff panel update

10. Settings check
- Confirm backend URL renders
- Confirm health status renders
- Confirm current session ID is truncated
- Confirm token is shown only as saved/not saved
- Confirm Clear Session works

11. Mobile check
- Open devtools mobile viewport
- Confirm bottom navigation is reachable
- Confirm cards do not overflow
- Confirm tables scroll horizontally
- Confirm chips and buttons wrap safely

12. Failure mode check
- Stop backend while frontend is configured
- Confirm friendly network error appears
- Confirm no silent mock fallback is used

## Regression Expectations

- ContextBridge/Clairo session summary does not say `content management application`
- Summary reflects developer tool / code intelligence / structured queryable knowledge wording
- MongoDB is not shown as a language
- `POST /analyze` and `GET /status` variants are deduplicated
- Workflow does not say `types/index.ts initializes FastAPI`
- Long nested paths do not appear in primary UI
- `.env.example` and raw `mongodb://` evidence do not appear in primary UI
- Test gap, onboarding, repo index, delta scan, chat, and downloads remain reachable from dashboard
- Downloads remain backend-driven for real sessions
- Demo mode appears only when backend URL is missing or empty
