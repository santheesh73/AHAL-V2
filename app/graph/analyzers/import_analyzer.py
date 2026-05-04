"""Deterministic Python and JS/TS import analyzer."""

from __future__ import annotations

import posixpath
import re

from app.graph.models import GraphEdge
from app.graph.utils.graph_evidence import make_graph_evidence
from app.graph.utils.graph_ids import make_edge_id, make_node_id
from app.graph.utils.path_matcher import normalize_import_path
from app.utils.ignored_paths import is_ignored_path

_PY_IMPORT = re.compile(r"^\s*import\s+([A-Za-z_][\w\.]*)", re.MULTILINE)
_PY_FROM = re.compile(r"^\s*from\s+([.\w]+)\s+import\s+([\w*,\s]+)", re.MULTILINE)
_JS_IMPORT = re.compile(r"""^\s*import(?:\s+.+?\s+from)?\s*['"]([^'"]+)['"]""", re.MULTILINE)
_JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")


class ImportAnalyzer:
    def analyze(self, scan_result, intelligence_result, node_ids: set[str] | None = None) -> list[GraphEdge]:
        node_ids = node_ids or set()
        files = {
            normalize_import_path(getattr(f, "path", ""))
            for f in getattr(scan_result, "files", []) or []
            if not is_ignored_path(getattr(f, "path", ""))
        }
        dep_ids = self._dependency_ids(intelligence_result)
        edges: list[GraphEdge] = []

        for path, content in (getattr(scan_result, "contents", {}) or {}).items():
            src_path = normalize_import_path(path)
            if not src_path or is_ignored_path(src_path):
                continue
            src_id = make_node_id("file", src_path)
            if node_ids and src_id not in node_ids:
                continue
            try:
                imports = self._extract_python(content) if src_path.endswith(".py") else []
                if src_path.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                    imports.extend(self._extract_js(content))
                for imported, snippet in imports:
                    target = self._resolve_import(src_path, imported, files, dep_ids)
                    if not target:
                        continue
                    edge = GraphEdge(
                        id=make_edge_id(src_id, target, "imports"),
                        source=src_id,
                        target=target,
                        type="imports",
                        label="imports",
                        metadata={"import": imported},
                        evidence=[make_graph_evidence(src_path, f"Import statement references {imported}", snippet=snippet, confidence="high")],
                        confidence="high",
                    )
                    edges.append(edge)
            except Exception:
                continue
        return edges

    def _extract_python(self, content: str) -> list[tuple[str, str]]:
        text = _strip_py_comments(content or "")
        out = [(m.group(1), m.group(0).strip()) for m in _PY_IMPORT.finditer(text)]
        out.extend((m.group(1), m.group(0).strip()) for m in _PY_FROM.finditer(text))
        return out

    def _extract_js(self, content: str) -> list[tuple[str, str]]:
        text = _strip_js_comments(content or "")
        out = [(m.group(1), m.group(0).strip()) for m in _JS_IMPORT.finditer(text)]
        out.extend((m.group(1), m.group(0).strip()) for m in _JS_REQUIRE.finditer(text))
        return out

    def _dependency_ids(self, intelligence_result) -> dict[str, str]:
        deps = {}
        for dep in getattr(intelligence_result, "dependencies", []) or []:
            name = str(getattr(dep, "name", "")).lower()
            eco = str(getattr(dep, "ecosystem", "unknown"))
            if name:
                deps[name] = make_node_id("dependency", f"{eco}:{getattr(dep, 'name', '')}")
        return deps

    def _resolve_import(self, source_path: str, imported: str, files: set[str], dep_ids: dict[str, str]) -> str | None:
        imported = str(imported or "").strip()
        if not imported:
            return None
        if imported.startswith("."):
            return self._resolve_relative(source_path, imported, files)
        package = imported.split("/")[0].split(".")[0].lower()
        if imported.startswith("@"):
            package = "/".join(imported.split("/")[:2]).lower()
        dependency = dep_ids.get(imported.lower()) or dep_ids.get(package)
        if dependency:
            return dependency
        return self._resolve_absolute(imported, files)

    def _resolve_relative(self, source_path: str, imported: str, files: set[str]) -> str | None:
        base = posixpath.dirname(source_path)
        if source_path.endswith(".py"):
            dots = len(imported) - len(imported.lstrip("."))
            rest = imported[dots:].replace(".", "/")
            base_parts = base.split("/") if base else []
            keep = max(0, len(base_parts) - max(0, dots - 1))
            candidate = "/".join(base_parts[:keep] + ([rest] if rest else []))
            exts = [".py", "/__init__.py"]
        else:
            candidate = posixpath.normpath(posixpath.join(base, imported))
            exts = ["", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.ts", "/index.tsx"]
        for ext in exts:
            path = normalize_import_path(candidate + ext)
            if path in files:
                return make_node_id("file", path)
        return None

    def _resolve_absolute(self, imported: str, files: set[str]) -> str | None:
        candidate = imported.replace(".", "/")
        for ext in (".py", "/__init__.py", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.ts", "/index.tsx"):
            path = normalize_import_path(candidate + ext)
            if path in files:
                return make_node_id("file", path)
        return None


def _strip_py_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _strip_js_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())
