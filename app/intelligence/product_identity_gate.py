from __future__ import annotations


WEAK_PRODUCT_SIGNALS = {
    "summarization",
    "session tracking",
    "chat",
    "query",
    "report generation",
    "dashboard",
    "status endpoint",
    "health endpoint",
    "docker",
    "ci/cd",
    "auth",
    "database",
    "upload",
    "api surface",
}

GENERIC_PROJECT_NAMES = {"analyzed project", "uploaded project", "untitled", "project", "repo"}


def is_generic_project_name(project_name: str) -> bool:
    return str(project_name or "").strip().lower() in GENERIC_PROJECT_NAMES


def repo_type_label(repo_type: str, project_type: str = "") -> str:
    raw = str(repo_type or project_type or "repository").strip().lower()
    mapping = {
        "backend_service": "backend service",
        "frontend_app": "frontend application",
        "fullstack_app": "fullstack application",
        "backend": "backend service",
        "frontend": "frontend application",
        "fullstack": "fullstack application",
        "cli_tool": "command-line tool repository",
    }
    return mapping.get(raw, raw.replace("_", " ") or "repository")


def conservative_summary(project_name: str, repo_type: str, project_type: str = "") -> str:
    label = repo_type_label(repo_type, project_type)
    subject = "This repository" if is_generic_project_name(project_name) else project_name
    if subject == "This repository":
        return f"This repository appears to be a {label}. The exact product purpose is not fully specified in the analyzed evidence."
    return f"{subject} appears to be a {label}. The exact product purpose is not fully specified in the analyzed evidence."


def conservative_what(project_name: str, repo_type: str, project_type: str = "") -> str:
    label = repo_type_label(repo_type, project_type)
    subject = "This repository" if is_generic_project_name(project_name) else project_name
    return f"{subject} appears to be a {label} based on the detected repository structure."


def conservative_why() -> str:
    return "The business or user-facing reason is not fully specified in the analyzed evidence."
