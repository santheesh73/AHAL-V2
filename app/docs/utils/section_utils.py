from unittest.mock import Mock

def safe_str(value, default="") -> str:
    if value is None:
        return default
    if isinstance(value, Mock):
        return default
    if isinstance(value, (str, int, float, bool)):
        text = str(value)
        return text if text else default
    return default
