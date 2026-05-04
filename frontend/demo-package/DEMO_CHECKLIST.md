# AHAL AI Demo Checklist

## Commands

Backend:

```bash
cd "C:\Users\babus\OneDrive\Desktop\AHAL v2"
python -m app.main
```

Frontend:

```bash
cd "C:\Users\babus\OneDrive\Desktop\AHAL v2\frontend"
npm run dev
```

## Demo

1. Open `http://localhost:5173`
2. Click `Analyze Project`
3. Click `View Demo Dashboard` or switch to the repo session
4. Use the prefilled AHAL demo repo
5. Wait for dashboard completion
6. Open Chat
7. Ask `What is built?`
8. Open Downloads
9. Download PDF
10. Download JSON
11. Load Test Gap Report
12. Load Onboarding Report
13. Create Repo Index
14. Run Delta Scan

## Expected Outcomes

- no blank page
- no raw stack traces
- no huge paths
- no duplicate evidence chips
- no fake mock data when backend configured
- report download works

## ContextBridge Regression Criteria

- summary does not say `content management application` when explicit metadata says developer tool
- MongoDB is not shown as a language
- `POST /analyze` and `GET /status` variants are deduplicated
- workflow does not say `types/index.ts initializes FastAPI`
- long nested paths do not appear in primary UI
- `.env.example` and raw `mongodb://` evidence do not appear in primary UI
- test gap, onboarding, repo index, delta scan, chat, and downloads remain reachable from dashboard
