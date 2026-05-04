from __future__ import annotations

import hashlib
import threading
import uuid
from typing import Optional

from app.config import config
from app.context.smart_context_selector import SmartContextSelector
from app.indexing.models import DeltaChangedFile, DeltaScanRequest, DeltaScanResult, FileFingerprint, RepoIndex
from app.models.file_schema import FileMetadata, Priority, ScanResult, ScanStats, ScanStatus
from app.sessions.models import utc_now_iso
from app.sessions.session_manager import session_manager
from app.storage import storage_backend
from app.utils.ignored_paths import is_ignored_path


class RepoIndexer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._indexes: dict[str, RepoIndex] = {}
        self._history: dict[str, list[dict]] = {}
        self._selector = SmartContextSelector()

    def create_index(self, session_id: str, info, scan_result: ScanResult) -> RepoIndex:
        now = utc_now_iso()
        source_type = "repo" if getattr(info, "session_type", "folder") == "repo" else "folder"
        repo_url = getattr(info, "source_name", "") if source_type == "repo" else None
        index = RepoIndex(
            index_id=uuid.uuid4().hex,
            session_id=session_id,
            repo_url=repo_url,
            source_type=source_type,
            source_name=getattr(info, "source_name", ""),
            file_fingerprints=self._compute_fingerprints(scan_result, session_id),
            last_scan_session_id=session_id,
            created_at=now,
            updated_at=now,
            status="ready",
            warnings=[],
        )
        with self._lock:
            self._indexes[index.index_id] = index
            self._history[index.index_id] = [
                {
                    "type": "index_created",
                    "session_id": session_id,
                    "timestamp": now,
                    "status": "ready",
                }
            ]
        storage_backend.create_repo_index(index.index_id, index.model_dump())
        storage_backend.update_repo_index(index.index_id, {"history": self._history[index.index_id]})
        return index

    def get_index(self, index_id: str) -> Optional[RepoIndex]:
        with self._lock:
            index = self._indexes.get(index_id)
        if index is not None:
            return index
        stored = storage_backend.get_repo_index(index_id)
        if stored:
            return RepoIndex.model_validate(stored)
        return None

    def get_history(self, index_id: str) -> list[dict]:
        with self._lock:
            history = list(self._history.get(index_id, []))
        if history:
            return history
        return list(storage_backend.list_repo_index_history(index_id) or [])

    def run_delta(self, request: DeltaScanRequest) -> DeltaScanResult:
        with self._lock:
            index = self._indexes.get(request.index_id)
            if index is None:
                raise KeyError(request.index_id)
            previous = {item.path: item for item in index.file_fingerprints}

        added: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        new_contents: dict[str, str] = {}
        new_fingerprints = {path: fp for path, fp in previous.items()}

        for item in request.changed_files[: config.scanner.change_max_files]:
            path = self._normalize_path(item.path)
            if not path or self._is_sensitive_or_ignored(path):
                continue
            if item.status == "deleted":
                deleted.append(path)
                new_fingerprints.pop(path, None)
                continue

            content = str(item.content or "")
            fingerprint = self._fingerprint(path, content, index.last_scan_session_id)
            if path not in previous:
                added.append(path)
            elif previous[path].hash != fingerprint.hash or previous[path].size != fingerprint.size:
                modified.append(path)
            else:
                continue
            new_fingerprints[path] = fingerprint
            new_contents[path] = content

        unchanged_count = max(0, len(previous) - len(set(added + modified + deleted)))
        prioritized = self._selector.select_from_mapping(new_contents)
        rescan_scope = self._determine_scope(request.force_full_rescan, prioritized, added, modified, deleted)

        base_session_id = index.last_scan_session_id
        new_session_id = session_manager.create_session(session_type=index.source_type, source_name=index.source_name)
        delta_scan = self._build_delta_scan_result(new_session_id, new_contents, added, modified, deleted)
        session_manager.set_result(new_session_id, delta_scan)

        now = utc_now_iso()
        delta_result = DeltaScanResult(
            index_id=index.index_id,
            base_session_id=base_session_id,
            new_session_id=new_session_id,
            added_files=sorted(added),
            modified_files=sorted(modified),
            deleted_files=sorted(deleted),
            unchanged_files_count=unchanged_count,
            rescan_scope=rescan_scope,
            summary=self._summary(added, modified, deleted, rescan_scope),
            warnings=[],
            confidence="high" if added or modified or deleted else "medium",
        )

        updated_index = index.model_copy(
            update={
                "file_fingerprints": sorted(new_fingerprints.values(), key=lambda item: item.path),
                "last_scan_session_id": new_session_id,
                "updated_at": now,
                "status": "ready",
            }
        )
        with self._lock:
            self._indexes[index.index_id] = updated_index
            self._history.setdefault(index.index_id, []).append(
                {
                    "type": "delta_scan",
                    "timestamp": now,
                    "base_session_id": base_session_id,
                    "new_session_id": new_session_id,
                    "summary": delta_result.summary,
                    "rescan_scope": rescan_scope,
                }
            )
        storage_backend.update_repo_index(index.index_id, updated_index.model_dump())
        storage_backend.update_repo_index(index.index_id, {"history": self._history[index.index_id]})
        return delta_result

    def find_by_repo_url(self, repo_url: str) -> Optional[RepoIndex]:
        target = str(repo_url or "").strip().lower()
        if not target:
            return None
        match = None
        with self._lock:
            for index in self._indexes.values():
                if str(index.repo_url or "").strip().lower() == target:
                    match = index
        return match

    def _compute_fingerprints(self, scan_result: ScanResult, session_id: str) -> list[FileFingerprint]:
        contents = getattr(scan_result, "contents", {}) or {}
        if not isinstance(contents, dict):
            return []
        rows = []
        for path, content in sorted(contents.items(), key=lambda item: self._normalize_path(item[0])):
            normalized_path = self._normalize_path(path)
            if not normalized_path or self._is_sensitive_or_ignored(normalized_path):
                continue
            rows.append(self._fingerprint(normalized_path, str(content or ""), session_id))
        return rows

    def _fingerprint(self, path: str, content: str, session_id: str) -> FileFingerprint:
        normalized_content = str(content or "").replace("\r\n", "\n").strip()
        digest = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        return FileFingerprint(
            path=path,
            hash=digest,
            size=len(normalized_content.encode("utf-8")),
            modified_at=None,
            category=self._categorize(path),
            last_seen_scan_id=session_id,
        )

    def _categorize(self, path: str) -> str:
        lowered = path.lower()
        if "readme" in lowered or lowered.endswith((".md", ".rst")):
            return "docs"
        if any(token in lowered for token in ["/api/", "routes", "controller"]):
            return "api"
        if any(token in lowered for token in ["service", "logic", "worker", "pipeline"]):
            return "service"
        if any(token in lowered for token in ["model", "schema", "database", "db", "migration"]):
            return "model"
        if any(token in lowered for token in ["docker", ".github/workflows", "gitlab-ci", "config", "settings"]):
            return "config"
        return "source"

    def _determine_scope(self, force_full_rescan: bool, prioritized, added: list[str], modified: list[str], deleted: list[str]) -> str:
        if force_full_rescan:
            return "full"
        changed = added + modified + deleted
        important = []
        for path in changed:
            category = self._categorize(path)
            if category in {"api", "service", "model", "config"} or "auth" in path.lower():
                important.append(path)
        if important:
            return "high-priority-delta"
        if getattr(prioritized, "files", []):
            return "targeted"
        return "minimal"

    def _build_delta_scan_result(self, session_id: str, contents: dict[str, str], added: list[str], modified: list[str], deleted: list[str]) -> ScanResult:
        files = []
        for path, content in sorted(contents.items()):
            files.append(
                FileMetadata(
                    path=path,
                    size_bytes=len(str(content or "").encode("utf-8")),
                    extension="." + path.split(".")[-1] if "." in path else "",
                    priority=Priority.HIGH if self._categorize(path) in {"api", "service", "model", "config"} else Priority.MEDIUM,
                )
            )
        errors = []
        if deleted:
            errors.append(f"Deleted files detected: {', '.join(sorted(deleted)[:10])}")
        return ScanResult(
            session_id=session_id,
            status=ScanStatus.COMPLETED,
            progress=100,
            stats=ScanStats(
                total_files_discovered=len(files),
                files_included=len(files),
                total_size_bytes=sum(file.size_bytes for file in files),
                included_size_bytes=sum(file.size_bytes for file in files),
            ),
            files=files,
            contents=contents,
            errors=errors,
        )

    def _summary(self, added: list[str], modified: list[str], deleted: list[str], scope: str) -> str:
        parts = []
        if added:
            parts.append(f"{len(added)} file{'s' if len(added) != 1 else ''} added")
        if modified:
            parts.append(f"{len(modified)} modified")
        if deleted:
            parts.append(f"{len(deleted)} deleted")
        if not parts:
            parts.append("No file-level changes detected")
        return f"{', '.join(parts)}. Rescan scope: {scope}."

    def _normalize_path(self, path: str) -> str:
        return str(path or "").replace("\\", "/").strip()

    def _is_sensitive_or_ignored(self, path: str) -> bool:
        lowered = path.lower()
        if is_ignored_path(path):
            return True
        filename = lowered.split("/")[-1]
        if filename.startswith(".env") or any(token in filename for token in ["secret", "token", "credential", "apikey", "api_key"]):
            return True
        return False


repo_indexer = RepoIndexer()
