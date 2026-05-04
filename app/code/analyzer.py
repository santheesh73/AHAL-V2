from __future__ import annotations

import ast
import re
from typing import Iterable

from app.code.models import CodeEvidence, CodeSessionResult
from app.docs.utils.production_text import clean_list, clean_sentence, join_capabilities


_LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
}


class CodeAnalyzer:
    def analyze(self, code: str, filename: str = "", language: str = "") -> CodeSessionResult:
        normalized = str(code or "")
        detected_language = self._detect_language(normalized, filename, language)

        if detected_language == "python":
            return self._analyze_python(normalized)
        if detected_language in {"javascript", "typescript"}:
            return self._analyze_regex(normalized, detected_language)
        if detected_language == "java":
            return self._analyze_regex(normalized, detected_language)
        if detected_language == "go":
            return self._analyze_regex(normalized, detected_language)
        return self._analyze_generic(normalized, detected_language)

    def _detect_language(self, code: str, filename: str, language: str) -> str:
        explicit = str(language or "").strip().lower()
        if explicit:
            return explicit

        lowered_name = str(filename or "").lower()
        for suffix, mapped in _LANGUAGE_BY_EXTENSION.items():
            if lowered_name.endswith(suffix):
                return mapped

        if "def " in code or "import " in code or "if __name__ ==" in code:
            return "python"
        if "function " in code or "const " in code or "=>" in code:
            return "javascript"
        if "public class " in code or "import java." in code:
            return "java"
        if "func " in code or "package " in code:
            return "go"
        return "text"

    def _analyze_python(self, code: str) -> CodeSessionResult:
        warnings: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            warnings.append(f"Python syntax could not be parsed completely: {exc.msg}.")
            return self._analyze_generic(code, "python", warnings=warnings)

        functions: list[str] = []
        classes: list[str] = []
        imports: list[str] = []
        entrypoints: list[str] = []
        issues: list[str] = []
        improvements: list[str] = []
        evidence: list[CodeEvidence] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                evidence.append(CodeEvidence(source_id=f"function:{node.name}", reason=f"Detected function `{node.name}`."))
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
                evidence.append(CodeEvidence(source_id=f"function:{node.name}", reason=f"Detected async function `{node.name}`."))
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                evidence.append(CodeEvidence(source_id=f"class:{node.name}", reason=f"Detected class `{node.name}`."))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", code):
            entrypoints.append("__main__")
            evidence.append(CodeEvidence(source_id="entrypoint:__main__", reason="Detected a Python __main__ entrypoint."))
        if re.search(r"\bmain\s*\(", code):
            entrypoints.append("main")
        if re.search(r"\bFastAPI\s*\(", code):
            entrypoints.append("FastAPI app")
            evidence.append(CodeEvidence(source_id="entrypoint:fastapi", reason="Detected FastAPI application initialization."))

        if re.search(r"except\s*:\s", code):
            issues.append("Potential issue: broad exception handling may hide important failures.")
        if re.search(r"print\s*\(", code) and "logging" not in code:
            improvements.append("Replace ad-hoc print statements with structured logging for production workflows.")
        if "TODO" in code or "FIXME" in code:
            issues.append("Potential issue: unfinished TODO or FIXME markers are present in the code.")
        if functions and not re.search(r"\bpytest\b|\bunittest\b", code) and len(functions) >= 3:
            improvements.append("Add automated tests for the detected functions and edge cases.")

        summary = self._build_summary(
            language="Python",
            functions=functions,
            classes=classes,
            entrypoints=entrypoints,
            imports=imports,
        )
        confidence = "high" if functions or classes else "medium"
        return CodeSessionResult(
            language="python",
            summary=summary,
            detected_functions=clean_list(functions, max_items=20),
            detected_classes=clean_list(classes, max_items=20),
            imports=clean_list(imports, max_items=20),
            entrypoints=clean_list(entrypoints, max_items=10),
            issues=clean_list(issues),
            suggested_improvements=clean_list(improvements),
            evidence=evidence[:20],
            confidence=confidence,
            warnings=clean_list(warnings),
        )

    def _analyze_regex(self, code: str, language: str) -> CodeSessionResult:
        function_patterns = {
            "javascript": [r"function\s+([A-Za-z_][A-Za-z0-9_]*)", r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\("],
            "typescript": [r"function\s+([A-Za-z_][A-Za-z0-9_]*)", r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\("],
            "java": [r"(?:public|private|protected)?\s+(?:static\s+)?[A-Za-z0-9_<>\[\]]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("],
            "go": [r"func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("],
        }
        class_patterns = {
            "javascript": [r"class\s+([A-Za-z_][A-Za-z0-9_]*)"],
            "typescript": [r"class\s+([A-Za-z_][A-Za-z0-9_]*)", r"interface\s+([A-Za-z_][A-Za-z0-9_]*)"],
            "java": [r"class\s+([A-Za-z_][A-Za-z0-9_]*)"],
            "go": [r"type\s+([A-Za-z_][A-Za-z0-9_]*)\s+struct"],
        }
        import_patterns = {
            "javascript": [r"import\s+.*?from\s+['\"]([^'\"]+)['\"]", r"require\(['\"]([^'\"]+)['\"]\)"],
            "typescript": [r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"],
            "java": [r"import\s+([A-Za-z0-9_.*]+);"],
            "go": [r"import\s+\"([^\"]+)\""],
        }

        functions = self._matches(code, function_patterns.get(language, []))
        classes = self._matches(code, class_patterns.get(language, []))
        imports = self._matches(code, import_patterns.get(language, []))
        entrypoints = []
        if language in {"javascript", "typescript"} and ("express()" in code or "Fastify(" in code or "createServer(" in code):
            entrypoints.append("server bootstrap")
        if language == "java" and "public static void main" in code:
            entrypoints.append("main")
        if language == "go" and re.search(r"func\s+main\s*\(", code):
            entrypoints.append("main")

        issues: list[str] = []
        improvements: list[str] = []
        if "TODO" in code or "FIXME" in code:
            issues.append("Potential issue: unfinished TODO or FIXME markers are present in the code.")
        if re.search(r"console\.log\s*\(", code):
            improvements.append("Replace console logging with structured logging where operational visibility matters.")
        if len(functions) >= 3:
            improvements.append("Add targeted tests for the detected public functions or handlers.")

        evidence = [
            CodeEvidence(source_id=f"function:{name}", reason=f"Detected function `{name}`.")
            for name in functions[:10]
        ] + [
            CodeEvidence(source_id=f"class:{name}", reason=f"Detected class or type `{name}`.")
            for name in classes[:10]
        ]
        summary = self._build_summary(
            language=language.title(),
            functions=functions,
            classes=classes,
            entrypoints=entrypoints,
            imports=imports,
        )
        confidence = "high" if functions or classes else "medium"
        return CodeSessionResult(
            language=language,
            summary=summary,
            detected_functions=clean_list(functions, max_items=20),
            detected_classes=clean_list(classes, max_items=20),
            imports=clean_list(imports, max_items=20),
            entrypoints=clean_list(entrypoints, max_items=10),
            issues=clean_list(issues),
            suggested_improvements=clean_list(improvements),
            evidence=evidence[:20],
            confidence=confidence,
            warnings=[],
        )

    def _analyze_generic(self, code: str, language: str, warnings: list[str] | None = None) -> CodeSessionResult:
        lines = [line for line in code.splitlines() if line.strip()]
        imports = self._matches(code, [r"import\s+([A-Za-z0-9_.*]+)", r"from\s+([A-Za-z0-9_.]+)\s+import"])
        issues = []
        if "TODO" in code or "FIXME" in code:
            issues.append("Potential issue: unfinished TODO or FIXME markers are present in the code.")
        summary = clean_sentence(
            f"This {language or 'text'} snippet contains {len(lines)} non-empty lines"
            + (f" and imports {join_capabilities(imports[:3])}" if imports else "")
            + "."
        )
        return CodeSessionResult(
            language=language or "text",
            summary=summary,
            imports=clean_list(imports, max_items=20),
            issues=clean_list(issues),
            suggested_improvements=["Add clearer structure, naming, and tests before relying on this snippet in production workflows."] if lines else [],
            evidence=[CodeEvidence(source_id="snippet", reason="Analyzed the submitted code snippet directly.")],
            confidence="low" if not lines else "medium",
            warnings=clean_list(warnings or []),
        )

    def _build_summary(
        self,
        language: str,
        functions: list[str],
        classes: list[str],
        entrypoints: list[str],
        imports: list[str],
    ) -> str:
        parts = [f"This {language} code snippet"]
        details = []
        if functions:
            details.append(f"defines {len(functions)} function{'s' if len(functions) != 1 else ''}")
        if classes:
            details.append(f"includes {len(classes)} class{'es' if len(classes) != 1 else ''}")
        if entrypoints:
            details.append(f"exposes entrypoints such as {join_capabilities(entrypoints[:3])}")
        if imports:
            details.append(f"depends on imports like {join_capabilities(imports[:3])}")
        if details:
            parts.append(", ".join(details))
        else:
            parts.append("does not expose strong structural signals")
        return clean_sentence(" ".join(parts))

    def _matches(self, code: str, patterns: Iterable[str]) -> list[str]:
        found: list[str] = []
        for pattern in patterns:
            found.extend(re.findall(pattern, code, flags=re.MULTILINE))
        return clean_list(found, max_items=20)
