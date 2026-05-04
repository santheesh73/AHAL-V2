"""
AHAL AI — Intelligence test fixtures.

Provides factory functions for ScanResult objects used across all detector tests.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.models.file_schema import FileMetadata, Priority, ScanResult, ScanStats, ScanStatus


def make_scan_result(
    files: List[Dict[str, object]] | None = None,
    contents: Dict[str, str] | None = None,
    stats: ScanStats | None = None,
) -> ScanResult:
    """
    Build a ScanResult for testing.

    files: list of dicts with keys: path, size_bytes (optional), extension (optional)
    contents: dict of path -> content string
    """
    file_metas: List[FileMetadata] = []
    for f in (files or []):
        fm = FileMetadata(
            path=str(f.get("path", "")),
            size_bytes=int(f.get("size_bytes", 100)),
            extension=str(f.get("extension", "")),
            priority=f.get("priority", Priority.LOW),
            is_binary=bool(f.get("is_binary", False)),
            skipped=bool(f.get("skipped", False)),
            skip_reason=f.get("skip_reason"),
        )
        file_metas.append(fm)

    return ScanResult(
        session_id="test-session",
        status=ScanStatus.COMPLETED,
        progress=100,
        stats=stats or ScanStats(
            total_files_discovered=len(file_metas),
            files_included=len([f for f in file_metas if not f.skipped]),
        ),
        files=file_metas,
        contents=contents or {},
    )


def empty_scan_result() -> ScanResult:
    """Empty ScanResult — no files, no contents."""
    return make_scan_result(files=[], contents={})


def python_fastapi_scan() -> ScanResult:
    """A minimal FastAPI project scan result."""
    return make_scan_result(
        files=[
            {"path": "main.py", "extension": ".py"},
            {"path": "app/api/routes.py", "extension": ".py"},
            {"path": "app/models/user.py", "extension": ".py"},
            {"path": "app/services/auth.py", "extension": ".py"},
            {"path": "app/config.py", "extension": ".py"},
            {"path": "requirements.txt", "extension": ".txt"},
            {"path": "Dockerfile", "extension": ""},
        ],
        contents={
            "main.py": 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/health")\nasync def health():\n    return {"status": "ok"}\n',
            "app/api/routes.py": 'from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get("/users")\nasync def get_users():\n    return []\n\n@router.post("/users")\nasync def create_user():\n    return {}\n',
            "app/models/user.py": 'from pydantic import BaseModel\n\nclass User(BaseModel):\n    name: str\n    email: str\n',
            "app/services/auth.py": 'import asyncpg\n\nasync def get_db():\n    conn = await asyncpg.connect("postgresql://localhost/mydb")\n    return conn\n',
            "app/config.py": 'DB_URL = "postgresql://localhost/mydb"\nSECRET = "abc"\n',
            "requirements.txt": "fastapi>=0.100\nuvicorn\nasyncpg\npydantic\n",
            "Dockerfile": 'FROM python:3.11\nCOPY . /app\nCMD ["uvicorn", "main:app"]\n',
        },
    )


def react_nextjs_scan() -> ScanResult:
    """A minimal Next.js/React frontend scan result."""
    return make_scan_result(
        files=[
            {"path": "package.json", "extension": ".json"},
            {"path": "next.config.js", "extension": ".js"},
            {"path": "src/pages/_app.tsx", "extension": ".tsx"},
            {"path": "src/pages/index.tsx", "extension": ".tsx"},
            {"path": "src/components/Header.tsx", "extension": ".tsx"},
            {"path": "src/styles/globals.css", "extension": ".css"},
        ],
        contents={
            "package.json": '{"name":"my-app","dependencies":{"react":"18.2.0","react-dom":"18.2.0","next":"14.0.0"},"devDependencies":{"typescript":"5.0.0"},"scripts":{"dev":"next dev","build":"next build"}}',
            "next.config.js": "module.exports = { reactStrictMode: true };\n",
            "src/pages/_app.tsx": 'import React from "react";\nimport "../styles/globals.css";\n\nexport default function App({ Component, pageProps }) {\n  return <Component {...pageProps} />;\n}\n',
            "src/pages/index.tsx": 'import React from "react";\n\nexport default function Home() {\n  return <h1>Hello</h1>;\n}\n',
            "src/components/Header.tsx": 'import React from "react";\n\nexport function Header() {\n  return <header>AHAL</header>;\n}\n',
        },
    )


def fullstack_scan() -> ScanResult:
    """A fullstack (React + FastAPI + PostgreSQL) scan result."""
    return make_scan_result(
        files=[
            # Backend
            {"path": "backend/main.py", "extension": ".py"},
            {"path": "backend/api/routes.py", "extension": ".py"},
            {"path": "backend/services/user_service.py", "extension": ".py"},
            {"path": "backend/models/user.py", "extension": ".py"},
            {"path": "backend/requirements.txt", "extension": ".txt"},
            # Frontend
            {"path": "frontend/package.json", "extension": ".json"},
            {"path": "frontend/src/main.tsx", "extension": ".tsx"},
            {"path": "frontend/src/components/App.tsx", "extension": ".tsx"},
            # Config
            {"path": "docker-compose.yml", "extension": ".yml"},
        ],
        contents={
            "backend/main.py": 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/api/health")\ndef health():\n    return {"ok": True}\n',
            "backend/api/routes.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.get("/api/users")\ndef list_users():\n    return []\n',
            "backend/services/user_service.py": 'import asyncpg\n\nasync def connect():\n    return await asyncpg.connect("postgresql://db/app")\n',
            "backend/requirements.txt": "fastapi\nuvicorn\nasyncpg\n",
            "frontend/package.json": '{"dependencies":{"react":"18.0.0","react-dom":"18.0.0"},"scripts":{"dev":"vite"}}',
            "frontend/src/main.tsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\n\nReactDOM.createRoot(document.getElementById("root")!).render(<App />);\n',
            "frontend/src/components/App.tsx": 'import React from "react";\n\nexport default function App() {\n  return <div>Hello</div>;\n}\n',
            "docker-compose.yml": "version: '3'\nservices:\n  backend:\n    build: ./backend\n  frontend:\n    build: ./frontend\n  db:\n    image: postgres:15\n",
        },
    )


def express_mongo_scan() -> ScanResult:
    """A minimal Express + MongoDB scan result."""
    return make_scan_result(
        files=[
            {"path": "package.json", "extension": ".json"},
            {"path": "server.js", "extension": ".js"},
            {"path": "routes/users.js", "extension": ".js"},
            {"path": "models/User.js", "extension": ".js"},
        ],
        contents={
            "package.json": '{"dependencies":{"express":"4.18.0","mongoose":"7.0.0"},"scripts":{"start":"node server.js"}}',
            "server.js": 'const express = require("express");\nconst mongoose = require("mongoose");\n\nconst app = express();\nmongoose.connect("mongodb://localhost/mydb");\n\napp.get("/health", (req, res) => res.json({ok: true}));\napp.listen(3000);\n',
            "routes/users.js": 'const express = require("express");\nconst router = express.Router();\n\nrouter.get("/users", (req, res) => res.json([]));\nrouter.post("/users", (req, res) => res.json({}));\n\nmodule.exports = router;\n',
            "models/User.js": 'const mongoose = require("mongoose");\n\nconst UserSchema = new mongoose.Schema({ name: String });\nmodule.exports = mongoose.model("User", UserSchema);\n',
        },
    )
