"""
AHAL AI — Language Detector (Phase 2, Step 3)

Detect programming languages by file extension.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

from typing import Dict, List

from app.intelligence.models import ConfidenceLevel, DetectedLanguage, EvidenceItem
from app.intelligence.utils.evidence import make_evidence
from app.intelligence.utils.path_utils import extension, iter_files
from app.models.file_schema import ScanResult

# Extension → Language name
_EXT_MAP: Dict[str, str] = {
    ".py":    "Python",
    ".js":    "JavaScript",
    ".jsx":   "JavaScript",
    ".ts":    "TypeScript",
    ".tsx":   "TypeScript",
    ".java":  "Java",
    ".go":    "Go",
    ".rs":    "Rust",
    ".php":   "PHP",
    ".rb":    "Ruby",
    ".cs":    "C#",
    ".cpp":   "C++",
    ".c":     "C",
    ".swift": "Swift",
    ".kt":    "Kotlin",
    ".dart":  "Dart",
    ".html":  "HTML",
    ".css":   "CSS",
    ".sql":   "SQL",
}

_MAX_EVIDENCE = 5


class LanguageDetector:
    """Detect programming languages from file extensions in ScanResult."""

    def detect(self, scan_result: ScanResult) -> List[DetectedLanguage]:
        """
        Count files by extension, compute percentages, and return
        DetectedLanguage entries sorted by file count descending.
        """
        lang_files: Dict[str, List[str]] = {}

        for fm in iter_files(scan_result):
            ext = extension(fm.path)
            lang = _EXT_MAP.get(ext)
            if lang is None:
                continue
            lang_files.setdefault(lang, []).append(fm.path)

        total_code_files = sum(len(f) for f in lang_files.values())
        if total_code_files == 0:
            return []

        results: List[DetectedLanguage] = []
        for lang_name, files in sorted(lang_files.items(), key=lambda x: -len(x[1])):
            count = len(files)
            pct = round((count / total_code_files) * 100, 2)
            conf: ConfidenceLevel = "high" if count >= 3 else "medium"

            evidence: List[EvidenceItem] = [
                make_evidence(
                    file=f,
                    reason=f"File extension maps to {lang_name}",
                    confidence=conf,
                )
                for f in files[:_MAX_EVIDENCE]
            ]

            results.append(DetectedLanguage(
                name=lang_name,
                file_count=count,
                percentage=pct,
                confidence=conf,
                evidence=evidence,
            ))

        return results
