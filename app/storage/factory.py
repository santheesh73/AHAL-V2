from __future__ import annotations

from app.storage.memory_store import MemorySessionStore
from app.storage.mongodb_store import MongoDBStore


def create_storage_backend(app_config, client=None):
    backend = str(getattr(app_config.scanner, "storage_backend", "memory") or "memory").strip().lower()
    if backend == "memory":
        return MemorySessionStore()
    if backend == "mongodb":
        return MongoDBStore(
            uri=getattr(app_config.scanner, "mongodb_uri", "mongodb://localhost:27017"),
            database=getattr(app_config.scanner, "mongodb_db", "ahal_ai"),
            ttl_hours=int(getattr(app_config.scanner, "session_ttl_hours", 24)),
            client=client,
        )
    raise RuntimeError(f"Unsupported storage backend: {backend}")
