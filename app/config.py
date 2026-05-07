"""
AHAL AI — Phase 1 Configuration
Central configuration for the ingestion and scanning engine.
"""

import os
from dataclasses import dataclass, field
from typing import FrozenSet

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_bool_or_none(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


GEMMA_4_26B_A4B_MODEL = "gemma-4-26b-a4b-it"
GEMMA_4_26B_UNAVAILABLE_WARNING = "Gemma 4 26B polish unavailable — deterministic answer shown."
GEMMA_4_26B_RATE_LIMIT_WARNING = "Gemma 4 26B rate limit reached — deterministic answer shown."
GEMMA_4_26B_TIMEOUT_WARNING = "Gemma 4 26B polish timed out — deterministic answer shown."
GEMMA_4_26B_VALIDATION_WARNING = "Gemma 4 26B polish was rejected by validation — deterministic answer shown."
_DEPRECATED_LLM_MODELS = {
    "gemma-26b-it": "gemma-26b-it is deprecated/invalid; use gemma-4-26b-a4b-it.",
}
_WARN_ONLY_LLM_MODELS = {
    "gemini-1.5-flash": "gemini-1.5-flash is not allowed; use gemma-4-26b-a4b-it.",
    "gemini-2.0-flash": "gemini-2.0-flash is not allowed; use gemma-4-26b-a4b-it.",
    "gemini-2.5-pro": "gemini-2.5-pro is not allowed; use gemma-4-26b-a4b-it.",
    "ollama": "ollama is not allowed; use gemma-4-26b-a4b-it through the Gemini API.",
}


def validate_llm_model_name(model: str | None, *, env_name: str = "AHAL_LLM_MODEL") -> tuple[str, tuple[str, ...]]:
    selected = (model or "").strip() or GEMMA_4_26B_A4B_MODEL
    if selected == GEMMA_4_26B_A4B_MODEL:
        return selected, ()
    if selected in _DEPRECATED_LLM_MODELS:
        return GEMMA_4_26B_A4B_MODEL, (f"{env_name}: {_DEPRECATED_LLM_MODELS[selected]}",)
    if selected in _WARN_ONLY_LLM_MODELS:
        return GEMMA_4_26B_A4B_MODEL, (f"{env_name}: {_WARN_ONLY_LLM_MODELS[selected]}",)
    return (
        GEMMA_4_26B_A4B_MODEL,
        (f"{env_name}: unsupported model '{selected}'; AHAL only supports gemma-4-26b-a4b-it.",),
    )


def _default_llm_model() -> str:
    return validate_llm_model_name(os.getenv("AHAL_LLM_MODEL", GEMMA_4_26B_A4B_MODEL))[0]


def _default_chat_llm_model() -> str:
    if os.getenv("AHAL_CHAT_LLM_MODEL"):
        return validate_llm_model_name(os.getenv("AHAL_CHAT_LLM_MODEL"), env_name="AHAL_CHAT_LLM_MODEL")[0]
    return validate_llm_model_name(os.getenv("AHAL_LLM_MODEL", GEMMA_4_26B_A4B_MODEL))[0]


def _default_docs_llm_model() -> str:
    if os.getenv("AHAL_DOCS_LLM_MODEL"):
        return validate_llm_model_name(os.getenv("AHAL_DOCS_LLM_MODEL"), env_name="AHAL_DOCS_LLM_MODEL")[0]
    return _default_chat_llm_model()


def _llm_model_warnings() -> tuple[str, ...]:
    warnings: list[str] = []
    _, base_warnings = validate_llm_model_name(
        os.getenv("AHAL_LLM_MODEL", GEMMA_4_26B_A4B_MODEL),
        env_name="AHAL_LLM_MODEL",
    )
    warnings.extend(base_warnings)
    if os.getenv("AHAL_CHAT_LLM_MODEL"):
        _, chat_warnings = validate_llm_model_name(
            os.getenv("AHAL_CHAT_LLM_MODEL"),
            env_name="AHAL_CHAT_LLM_MODEL",
        )
        warnings.extend(chat_warnings)
    if os.getenv("AHAL_DOCS_LLM_MODEL"):
        _, docs_warnings = validate_llm_model_name(
            os.getenv("AHAL_DOCS_LLM_MODEL"),
            env_name="AHAL_DOCS_LLM_MODEL",
        )
        warnings.extend(docs_warnings)
    return tuple(dict.fromkeys(warnings))


def _default_feature_flag(env_name: str, base_enabled: bool) -> bool:
    explicit = _env_bool_or_none(env_name)
    if explicit is None:
        return base_enabled
    return explicit


@dataclass(frozen=True)
class ScannerConfig:
    """Immutable configuration for the scanner subsystem."""

    # --- Size Limits ---
    max_zip_size_bytes: int = 1 * 1024 * 1024 * 1024  # 1 GB
    max_single_file_bytes: int = 100 * 1024 * 1024     # 100 MB

    # --- Content Loading Limits ---
    high_priority_max_bytes: int = 100 * 1024   # 100 KB
    default_max_bytes: int = 20 * 1024           # 20 KB

    # --- Concurrency ---
    # Inner file-scan pool: cpu_count capped at 8, env-overridable
    max_worker_threads: int = int(
        os.getenv("AHAL_MAX_WORKERS", str(min(8, os.cpu_count() or 4)))
    )
    # Outer background job pool (Fix 3)
    bg_worker_count: int = int(
        os.getenv("AHAL_BG_WORKERS", str(min(4, os.cpu_count() or 2)))
    )
    scan_queue_maxsize: int = 1000

    # --- Watchdog / Timeout ---
    max_scan_time_seconds: int = int(os.getenv("AHAL_MAX_SCAN_TIME", "300"))

    # --- Content Size Budget ---
    # Total decoded content stored in memory across all files (10 MB default)
    max_total_content_mb: int = int(os.getenv("AHAL_MAX_CONTENT_MB", "10"))

    # --- Session ---
    session_ttl_seconds: int = 3600  # 1 hour
    progress_update_interval: int = 50  # update progress every N files

    # --- Backpressure / Load Control ---
    max_active_sessions: int = int(os.getenv("AHAL_MAX_ACTIVE", "10"))

    # --- Session Security (Fix 5) ---
    # When true: status/result/cancel require X-Session-Token header
    require_session_token: bool = _env_bool("AHAL_REQUIRE_SESSION_TOKEN", False)

    # --- Rate Limiting (Fix 6) ---
    rate_limit_enabled: bool = _env_bool("AHAL_RATE_LIMIT_ENABLED", False)
    rate_limit_window_seconds: int = int(
        os.getenv("AHAL_RATE_LIMIT_WINDOW_SECONDS", "60")
    )
    rate_limit_max_requests: int = int(
        os.getenv("AHAL_RATE_LIMIT_MAX_REQUESTS", "20")
    )

    # --- LLM / Gemini API (Gemma 4 26B A4B only) ---
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    llm_enabled: bool = _env_bool("AHAL_LLM_ENABLED", False)
    llm_provider: str = os.getenv("AHAL_LLM_PROVIDER", "gemini").strip().lower() or "gemini"
    llm_model: str = field(default_factory=_default_llm_model)
    chat_llm_model: str = field(default_factory=_default_chat_llm_model)
    docs_llm_model: str = field(default_factory=_default_docs_llm_model)
    llm_model_warnings: tuple[str, ...] = field(default_factory=_llm_model_warnings)
    llm_timeout_seconds: int = int(
        os.getenv("AHAL_LLM_TIMEOUT_SECONDS", "180")
    )
    llm_require_validation: bool = _env_bool("AHAL_LLM_REQUIRE_VALIDATION", True)
    llm_max_retries: int = int(os.getenv("AHAL_LLM_MAX_RETRIES", os.getenv("AHAL_LLM_RETRY_COUNT", "1")))
    llm_retry_on_404: bool = _env_bool("AHAL_LLM_RETRY_ON_404", False)
    llm_retry_on_429: bool = _env_bool("AHAL_LLM_RETRY_ON_429", True)
    llm_rate_limit_cooldown_seconds: int = int(os.getenv("AHAL_LLM_RATE_LIMIT_COOLDOWN_SECONDS", "60"))

    # --- Phase 4 / Chat Configuration ---
    chat_history_max_messages: int = int(os.getenv("AHAL_CHAT_HISTORY_MAX_MESSAGES", "20"))
    chat_max_question_chars: int = int(os.getenv("AHAL_CHAT_MAX_QUESTION_CHARS", "2000"))
    code_max_chars: int = int(os.getenv("AHAL_CODE_MAX_CHARS", "50000"))
    code_max_filename_chars: int = int(os.getenv("AHAL_CODE_MAX_FILENAME_CHARS", "255"))
    change_max_diff_chars: int = int(os.getenv("AHAL_CHANGE_MAX_DIFF_CHARS", "200000"))
    change_max_files: int = int(os.getenv("AHAL_CHANGE_MAX_FILES", "100"))
    chat_max_context_items: int = int(os.getenv("AHAL_CHAT_MAX_CONTEXT_ITEMS", "50"))
    chat_max_context_chars: int = int(os.getenv("AHAL_CHAT_MAX_CONTEXT_CHARS", "30000"))
    chat_max_history_messages: int = int(os.getenv("AHAL_CHAT_MAX_HISTORY_MESSAGES", "8"))
    chat_memory_enabled: bool = _env_bool("AHAL_CHAT_MEMORY_ENABLED", True)
    chat_memory_max_messages: int = int(os.getenv("AHAL_CHAT_MEMORY_MAX_MESSAGES", "20"))
    chat_llm_enabled: bool = field(default_factory=lambda: _default_feature_flag("AHAL_CHAT_LLM_ENABLED", _env_bool("AHAL_LLM_ENABLED", False)))
    chat_llm_require_validation: bool = _env_bool("AHAL_CHAT_LLM_REQUIRE_VALIDATION", True)
    chat_llm_streaming: bool = _env_bool("AHAL_CHAT_LLM_STREAMING", False)
    docs_llm_enabled: bool = field(default_factory=lambda: _default_feature_flag("AHAL_DOCS_LLM_ENABLED", _env_bool("AHAL_LLM_ENABLED", False)))
    prd_llm_enabled: bool = field(default_factory=lambda: _default_feature_flag("AHAL_PRD_LLM_ENABLED", _env_bool("AHAL_LLM_ENABLED", False)))
    pdf_llm_enabled: bool = field(default_factory=lambda: _default_feature_flag("AHAL_PDF_LLM_ENABLED", _env_bool("AHAL_LLM_ENABLED", False)))
    purpose_extraction_max_chars: int = int(os.getenv("AHAL_PURPOSE_EXTRACTION_MAX_CHARS", "5000"))
    strict_json_llm_enabled: bool = _env_bool("AHAL_STRICT_JSON_LLM_ENABLED", False)
    llm_retry_count: int = int(os.getenv("AHAL_LLM_RETRY_COUNT", str(int(os.getenv("AHAL_LLM_MAX_RETRIES", "1")))))
    llm_orchestration_enabled: bool = _env_bool("AHAL_LLM_ORCHESTRATION_ENABLED", False)
    llm_primary_provider: str = os.getenv("AHAL_LLM_PRIMARY_PROVIDER", "gemini")
    llm_critic_provider: str = os.getenv("AHAL_LLM_CRITIC_PROVIDER", "gemini")
    llm_orchestration_max_rounds: int = int(os.getenv("AHAL_LLM_ORCHESTRATION_MAX_ROUNDS", "1"))
    llm_orchestration_timeout_seconds: int = int(os.getenv("AHAL_LLM_ORCHESTRATION_TIMEOUT_SECONDS", "120"))
    max_context_files: int = int(os.getenv("AHAL_MAX_CONTEXT_FILES", "8"))
    max_file_context_chars: int = int(os.getenv("AHAL_MAX_FILE_CHARS", "5000"))
    max_total_context_chars: int = int(os.getenv("AHAL_MAX_TOTAL_CONTEXT_CHARS", "30000"))
    storage_backend: str = os.getenv("AHAL_STORAGE_BACKEND", "memory")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "ahal_ai")
    session_ttl_hours: int = int(os.getenv("AHAL_SESSION_TTL_HOURS", "24"))

    # --- Directories to Ignore ---
    ignored_directories: FrozenSet[str] = frozenset({
        "node_modules",
        ".git",
        "dist",
        "build",
        "coverage",
        "__pycache__",
        ".next",
        ".nuxt",
        ".svelte-kit",
        "vendor",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "egg-info",
    })

    # --- File Extensions to Ignore ---
    ignored_extensions: FrozenSet[str] = frozenset({
        # Binaries
        ".exe", ".dll", ".so", ".dylib", ".o", ".a", ".lib",
        ".pyc", ".pyo", ".class", ".jar", ".war",
        # Archives (nested)
        ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz",
        # Media
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
        ".webp", ".tiff", ".tif",
        ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv",
        ".wav", ".ogg", ".flac",
        # Fonts
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        # Data blobs
        ".sqlite", ".db", ".mdb",
        # Lock files (large, low value)
        ".lock",
    })

    # --- High Priority Entry Files ---
    high_priority_entry_files: FrozenSet[str] = frozenset({
        "main.py", "app.py", "server.py", "wsgi.py", "asgi.py",
        "manage.py", "setup.py", "pyproject.toml",
        "index.ts", "index.tsx", "index.js", "index.jsx",
        "main.ts", "main.tsx", "main.js", "main.jsx",
        "App.ts", "App.tsx", "App.js", "App.jsx",
        "server.ts", "server.js",
        "package.json", "Cargo.toml", "go.mod",
        "Makefile", "Dockerfile", "docker-compose.yml",
        "requirements.txt",
    })

    # --- High Priority Directories ---
    high_priority_directories: FrozenSet[str] = frozenset({
        "src", "api", "services", "core", "lib", "app",
        "routes", "controllers", "handlers", "middleware",
    })

    # --- Medium Priority Directories ---
    medium_priority_directories: FrozenSet[str] = frozenset({
        "utils", "helpers", "common", "shared", "tools",
    })

    # --- Low Priority Directories ---
    low_priority_directories: FrozenSet[str] = frozenset({
        "config", "configs", "settings", "migrations",
        "scripts", "docs", "examples", "tests", "test",
        "fixtures", "mocks", "__tests__",
    })

    # --- GitHub ---
    github_clone_timeout_seconds: int = 120
    github_max_repo_size_mb: int = 500
    github_webhook_enabled: bool = _env_bool("AHAL_GITHUB_WEBHOOK_ENABLED", False)
    github_webhook_secret: str = os.getenv("AHAL_GITHUB_WEBHOOK_SECRET", "")

    # --- Temp directory ---
    temp_base_dir: str = os.getenv("AHAL_TEMP_DIR", "")

    def llm_startup_summary(self) -> dict[str, object]:
        return {
            "provider": self.llm_provider,
            "model": self.llm_model,
            "chat_model": self.chat_llm_model,
            "docs_model": self.docs_llm_model,
            "docs_llm_enabled": self.docs_llm_enabled,
            "chat_llm_enabled": self.chat_llm_enabled,
            "validation_enabled": self.llm_require_validation and self.chat_llm_require_validation,
            "key_present": bool(self.gemini_api_key),
            "llm_enabled": self.llm_enabled,
        }

    def llm_health_warnings(self) -> tuple[str, ...]:
        warnings = list(self.llm_model_warnings)
        if self.llm_enabled and not self.chat_llm_enabled:
            warnings.append("Global LLM is enabled but chat LLM is disabled. Chat will use deterministic fallback.")
        if self.llm_provider != "gemini":
            warnings.append(f"AHAL_LLM_PROVIDER: unsupported provider '{self.llm_provider}'; deterministic fallback will be used.")
        return tuple(dict.fromkeys(warnings))


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    host: str = os.getenv("AHAL_HOST", "0.0.0.0")
    port: int = int(os.getenv("AHAL_PORT", "8000"))
    debug: bool = _env_bool("AHAL_DEBUG", False)
    version: str = "1.0.0"
    scanner: ScannerConfig = field(default_factory=ScannerConfig)


# Singleton
config = AppConfig()
