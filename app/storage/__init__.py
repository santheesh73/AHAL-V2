from app.config import config
from app.storage.factory import create_storage_backend
from app.storage.memory_store import MemorySessionStore
from app.storage.mongodb_store import MongoDBStore

storage_backend = create_storage_backend(config)

__all__ = ["MemorySessionStore", "MongoDBStore", "create_storage_backend", "storage_backend"]
