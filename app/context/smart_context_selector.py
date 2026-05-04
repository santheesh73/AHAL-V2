from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field

from app.config import config
from app.models.file_schema import ScanResult
from app.utils.ignored_paths import is_ignored_path

_SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "secrets.env",
    "id_rsa",
    "id_dsa",
}
_SENSITIVE_TOKENS = ("secret", "secrets", "credential", "credentials", "token", "private_key", "apikey")


class SelectedContextFile(BaseModel):
    path: str
    reason: str
    priority_score: int
    excerpt: str
    evidence_id: str


class SelectedContext(BaseModel):
    files: list[SelectedContextFile] = Field(default_factory=list)
    total_chars: int = 0
    warnings: list[str] = Field(default_factory=list)
    confidence: str = "low"


class SmartContextSelector:
    def select(self, scan_result: ScanResult) -> SelectedContext:
        contents = getattr(scan_result, "contents", {}) or {}
        if not isinstance(contents, dict):
            return SelectedContext(warnings=["Context selection skipped because scan contents were unavailable."])

        candidates = []
        for path, raw_content in contents.items():
            path_str = str(path or "")
            if not path_str or is_ignored_path(path_str) or self._is_sensitive_path(path_str):
                continue
            score, reason = self._score_path(path_str)
            excerpt = str(raw_content or "")
            if self._looks_binary(excerpt):
                continue
            excerpt = excerpt[: config.scanner.max_file_context_chars]
            candidates.append((score, path_str.lower(), path_str, reason, excerpt))

        candidates.sort(key=lambda item: (-item[0], item[1]))

        selected: list[SelectedContextFile] = []
        total_chars = 0
        max_files = max(1, int(config.scanner.max_context_files))
        max_chars = max(1, int(config.scanner.max_total_context_chars))
        for score, _, path, reason, excerpt in candidates:
            if len(selected) >= max_files:
                break
            remaining = max_chars - total_chars
            if remaining <= 0:
                break
            clipped = excerpt[:remaining]
            if not clipped:
                continue
            total_chars += len(clipped)
            selected.append(
                SelectedContextFile(
                    path=path,
                    reason=reason,
                    priority_score=score,
                    excerpt=clipped,
                    evidence_id=f"E{len(selected) + 1}",
                )
            )

        warnings: list[str] = []
        if not selected:
            warnings.append("No eligible context files were available after ignore filtering.")
        confidence = "high" if any(item.priority_score >= 90 for item in selected) else "medium" if selected else "low"
        return SelectedContext(files=selected, total_chars=total_chars, warnings=warnings, confidence=confidence)

    def select_from_mapping(self, contents: dict[str, str]) -> SelectedContext:
        return self.select(ScanResult(session_id="context", contents=contents))

    def _score_path(self, path: str) -> tuple[int, str]:
        lowered = path.replace("\\", "/").lower()
        filename = lowered.split("/")[-1]

        if "readme" in filename or "/docs/" in lowered:
            return 100, "README or documentation"
        if filename in {"main.py", "app.py", "index.js", "server.js", "app.ts", "main.ts", "manage.py"}:
            return 95, "Entry point"
        if any(token in lowered for token in ["/routes/", "/route", "/controller", "/api/"]):
            return 90, "API routes or controllers"
        if any(token in lowered for token in ["/service", "/services/", "/core/", "/logic/"]):
            return 80, "Business logic or services"
        if any(token in lowered for token in ["/model", "/models/", "/schema", "/schemas/"]):
            return 70, "Models or schemas"
        if any(token in filename for token in ["dockerfile", "package.json", "requirements.txt", "pyproject.toml", ".env.example"]):
            return 60, "Project configuration"
        if any(token in lowered for token in ["/db", "/database", "/storage", "/migrations/"]):
            return 55, "Database or storage"
        if "/test" in lowered or "/tests/" in lowered or filename.startswith("test_"):
            return 40, "Tests"
        return 20, "General source file"

    def _is_sensitive_path(self, path: str) -> bool:
        lowered = path.replace("\\", "/").lower()
        filename = lowered.split("/")[-1]
        if filename in _SENSITIVE_FILENAMES:
            return True
        if filename.startswith(".env"):
            return True
        return any(token in filename for token in _SENSITIVE_TOKENS)

    def _looks_binary(self, text: str) -> bool:
        if not text:
            return False
        sample = text[:200]
        return "\x00" in sample
