from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from ..shared.config import ConfigLoader

class DatabaseManager:
    """Thread-safe SQLite database manager."""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        
        self.config = ConfigLoader.load()
        # Use config path or fallback to state/memory/memory.db
        self.db_path = self.config.memory_sqlite_path or (self.config.data_root / "memory" / "memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.initialized = True
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        """Initialize database schema from SQL file."""
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at {schema_path}")
            
        with self.get_connection() as conn:
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
            conn.commit()

# Single instance
db = DatabaseManager()
