from __future__ import annotations

from app.utils.ignored_paths import is_ignored_path


_SENSITIVE_KEYS = {"api_key", "apikey", "token", "secret", "password", "gemini_api_key", "mongodb_uri"}


def safe_model_dump(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    elif hasattr(value, "dict"):
        value = value.dict()
    return sanitize_for_storage(value)


def sanitize_for_storage(value):
    if isinstance(value, dict):
        cleaned = {}
        lowered_keys = {str(key).lower(): key for key in value.keys()}
        path_value = ""
        for path_key in ("path", "file", "source_file"):
            original = lowered_keys.get(path_key)
            if original is not None:
                path_value = str(value.get(original, "") or "")
                break
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in _SENSITIVE_KEYS:
                continue
            if lowered == "contents" and isinstance(item, dict):
                cleaned[key] = {
                    path: sanitize_for_storage(content)
                    for path, content in item.items()
                    if not _is_sensitive_path(path)
                }
                continue
            if lowered in {"content", "before", "after", "diff_text"} and path_value and _is_sensitive_path(path_value):
                continue
            cleaned[key] = sanitize_for_storage(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_for_storage(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_storage(item) for item in value]
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value


def _is_sensitive_path(path: str) -> bool:
    lowered = str(path or "").replace("\\", "/").lower()
    if not lowered:
        return False
    filename = lowered.rsplit("/", 1)[-1]
    if is_ignored_path(lowered):
        return True
    return filename.startswith(".env") or any(token in filename for token in ("secret", "token", "credential", "apikey", "api_key"))
