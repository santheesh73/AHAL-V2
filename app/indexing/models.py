from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FileFingerprint(BaseModel):
    path: str
    hash: str
    size: int
    modified_at: Optional[str] = None
    category: str
    last_seen_scan_id: str


class RepoIndex(BaseModel):
    index_id: str
    session_id: str
    repo_url: Optional[str] = None
    source_type: Literal["folder", "repo"]
    source_name: str
    file_fingerprints: list[FileFingerprint] = Field(default_factory=list)
    last_scan_session_id: str
    created_at: str
    updated_at: str
    status: str
    warnings: list[str] = Field(default_factory=list)


class DeltaChangedFile(BaseModel):
    path: str
    content: Optional[str] = None
    status: Literal["added", "modified", "deleted", "unknown"] = "unknown"


class DeltaScanRequest(BaseModel):
    index_id: str
    changed_files: list[DeltaChangedFile] = Field(default_factory=list)
    force_full_rescan: bool = False


class DeltaScanResult(BaseModel):
    index_id: str
    base_session_id: str
    new_session_id: str
    added_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)
    unchanged_files_count: int = 0
    rescan_scope: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
