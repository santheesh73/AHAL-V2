export const DEMO_CODE_SNIPPET = `from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/analyze")
def analyze(payload: dict):
    return {"status": "received"}

@app.post("/ask")
def ask(payload: dict):
    return {"answer": "grounded response"}
`

export const DEMO_REPO_URL = "https://github.com/bsrikumar855-dot/AHAL-AI"
