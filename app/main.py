"""
AHAL AI — Application Entry Point  [HARDENED v4]
FastAPI application with structured logging and CORS.

Fix 7: Extended /health with runtime stats; new /metrics endpoint.
"""

from __future__ import annotations

import logging
import sys
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyze import router as analyze_router
from app.config import config
from app.webhooks.github import router as webhook_router

# ── Record startup time (Fix 7) ──────────────────────────────────
_START_TIME = time.monotonic()

# ── Structured Logging ───────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("ahal")

logger.info(
    "LLM config: enabled=%s key_present=%s model=%s",
    config.scanner.llm_enabled,
    bool(config.scanner.gemini_api_key),
    config.scanner.llm_model,
)

# ── FastAPI App ──────────────────────────────────────────────────

app = FastAPI(
    title="AHAL AI — Ingestion Engine",
    description="High-performance file ingestion and streaming scanner for large codebases.",
    version=config.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────

app.include_router(analyze_router)
app.include_router(webhook_router)


# ── Health (Fix 7 — extended) ────────────────────────────────────

@app.get("/health")
async def health():
    """
    Operator health check. Unauthenticated.
    Returns runtime stats for monitoring.
    """
    from app.sessions.session_manager import session_manager  # late import avoids cycle
    return {
        "ok":                  True,
        "service":             "AHAL AI",
        "status":              "ok",
        "version":             config.version,
        "uptime_seconds":      round(time.monotonic() - _START_TIME, 1),
        "active_sessions":     session_manager.get_active_session_count(),
        "max_active_sessions": config.scanner.max_active_sessions,
        "bg_workers":          config.scanner.bg_worker_count,
    }


# ── Metrics (Fix 7 — new endpoint) ───────────────────────────────

@app.get("/metrics")
async def metrics():
    """
    Operator metrics endpoint. Unauthenticated.
    Returns session lifecycle counters and average scan time.
    """
    from app.sessions.session_manager import session_manager
    return session_manager.get_metrics()


# ── Root ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "AHAL AI Ingestion Engine",
        "version": config.version,
        "endpoints": {
            "upload":       "POST /analyze/upload",
            "github":       "POST /analyze/github",
            "github_webhook": "POST /webhooks/github",
            "status":       "GET /analyze/status/{session_id}",
            "result":       "GET /analyze/result/{session_id}",
            "cancel":       "POST /analyze/cancel/{session_id}",
            "intelligence": "GET /analyze/intelligence/{session_id}",
            "health":       "GET /health",
            "metrics":      "GET /metrics",
            "docs":         "GET /docs",
        },
    }


# ── CLI entry ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting AHAL AI Ingestion Engine on %s:%s", config.host, config.port)
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        workers=1,
    )
