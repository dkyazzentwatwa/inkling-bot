"""
Project Inkling - Persistent Memory

Long-term memory storage for the Inkling companion.
Remembers important information across sessions and conversations.
"""

import sqlite3
import time
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class Memory:
    """A single memory entry."""
    id: int
    key: str
    value: str
    importance: float
    category: str
    created_at: float
    last_accessed: float
    access_count: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "importance": self.importance,
            "category": self.category,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
        }


class MemoryStore:
    """
    Persistent memory storage for the Inkling.

    Stores memories in SQLite with importance weighting.
    Memories can be recalled by key, category, or keyword search.
    Old, low-importance memories are periodically pruned.
    """

    # Memory categories
    CATEGORY_USER = "user"          # Things about the user
    CATEGORY_PREFERENCE = "pref"    # User preferences
    CATEGORY_FACT = "fact"          # Learned facts
    CATEGORY_EVENT = "event"        # Past events
    CATEGORY_SOCIAL = "social"      # Social network info

    def __init__(self, data_dir: str = "~/.inkling"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "memory.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

    def initialize(self) -> None:
        """Initialize the database."""
        with self._lock:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=5.0,
            )
            self._conn.row_factory = sqlite3.Row
            self._create_tables()

    def _create_tables(self) -> None:
        """Create the memory tables."""
        self._conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            category TEXT DEFAULT 'fact',
            created_at REAL NOT NULL,
            last_accessed REAL NOT NULL,
            access_count INTEGER DEFAULT 1,
            UNIQUE(key, category)
        )
        """)
        self._conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)
        """)
        self._conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)
        """)
        # WAL mode improves read/write coexistence for multi-threaded access.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.commit()

    def remember(
        self,
        key: str,
        value: str,
        importance: float = 0.5,
        category: str = "fact",
    ) -> Memory:
        """
        Store or update a memory.

        Args:
            key: Short identifier for the memory (e.g., "user_name", "favorite_color")
            value: The content to remember
            importance: 0.0-1.0, higher = more important (less likely to forget)
            category: One of user, pref, fact, event, social

        Returns:
            The stored Memory object
        """
        importance = max(0.0, min(1.0, importance))
        now = time.time()
        with self._lock:
            # Try to update existing memory
            cursor = self._conn.execute(
                """
                UPDATE memories
                SET value = ?, importance = MAX(importance, ?),
                    last_accessed = ?, access_count = access_count + 1
                WHERE key = ? AND category = ?
                """,
                (value, importance, now, key, category)
            )

            if cursor.rowcount == 0:
                # Insert new memory
                cursor = self._conn.execute(
                    """
                    INSERT INTO memories (key, value, importance, category, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (key, value, importance, category, now, now)
                )

            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM memories WHERE key = ? AND category = ?",
                (key, category)
            ).fetchone()
            return self._row_to_memory(row)

    def get(self, key: str, category: str = "fact") -> Optional[Memory]:
        """
        Retrieve a specific memory by key.

        Updates access time and count.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM memories WHERE key = ? AND category = ?",
                (key, category)
            ).fetchone()

            if row:
                # Update access stats
                self._conn.execute(
                    "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                    (time.time(), row["id"])
                )
                self._conn.commit()
                return self._row_to_memory(row)

        return None

    def recall(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Memory]:
        """
        Search memories by keyword.

        Args:
            query: Search term (matches key or value)
            category: Optional category filter
            limit: Maximum results to return

        Returns:
            List of matching memories, ordered by importance
        """
        query_pattern = f"%{query.lower()}%"

        with self._lock:
            if category:
                rows = self._conn.execute(
                    """
                    SELECT * FROM memories
                    WHERE category = ? AND (LOWER(key) LIKE ? OR LOWER(value) LIKE ?)
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT ?
                    """,
                    (category, query_pattern, query_pattern, limit)
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT * FROM memories
                    WHERE LOWER(key) LIKE ? OR LOWER(value) LIKE ?
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT ?
                    """,
                    (query_pattern, query_pattern, limit)
                ).fetchall()

            # Update access stats for recalled memories
            for row in rows:
                self._conn.execute(
                    "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                    (time.time(), row["id"])
                )
            self._conn.commit()

        return [self._row_to_memory(row) for row in rows]

    def recall_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> List[Memory]:
        """Get all memories in a category."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM memories
                WHERE category = ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
                """,
                (category, limit)
            ).fetchall()

        return [self._row_to_memory(row) for row in rows]

    def recall_recent(self, limit: int = 10) -> List[Memory]:
        """Get most recently accessed memories."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM memories
                ORDER BY last_accessed DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return [self._row_to_memory(row) for row in rows]

    def recall_important(self, limit: int = 10) -> List[Memory]:
        """Get most important memories."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM memories
                ORDER BY importance DESC, access_count DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return [self._row_to_memory(row) for row in rows]

    def forget(self, key: str, category: str = "fact") -> bool:
        """
        Remove a specific memory.

        Returns True if memory existed and was removed.
        """
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM memories WHERE key = ? AND category = ?",
                (key, category)
            )
            self._conn.commit()
            return cursor.rowcount > 0

    def forget_old(
        self,
        max_age_days: int = 30,
        importance_threshold: float = 0.3,
    ) -> int:
        """
        Prune old, low-importance memories.

        Keeps memories that are:
        - Newer than max_age_days, OR
        - More important than importance_threshold, OR
        - Frequently accessed (access_count > 5)

        Returns number of memories pruned.
        """
        cutoff_time = time.time() - (max_age_days * 86400)

        with self._lock:
            cursor = self._conn.execute(
                """
                DELETE FROM memories
                WHERE last_accessed < ?
                  AND importance < ?
                  AND access_count < 5
                """,
                (cutoff_time, importance_threshold)
            )
            self._conn.commit()
            return cursor.rowcount

    def count(self, category: Optional[str] = None) -> int:
        """Count memories, optionally by category."""
        with self._lock:
            if category:
                row = self._conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE category = ?",
                    (category,)
                ).fetchone()
            else:
                row = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()
            return row[0]

    def get_context_for_prompt(self, limit: int = 10) -> str:
        """
        Generate a context string for AI prompts.

        Includes the most important and relevant memories.
        """
        memories = self.recall_important(limit)

        if not memories:
            return ""

        lines = ["Things I remember:"]
        for mem in memories:
            lines.append(f"- {mem.key}: {mem.value}")

        return "\n".join(lines)

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert a database row to a Memory object."""
        return Memory(
            id=row["id"],
            key=row["key"],
            value=row["value"],
            importance=row["importance"],
            category=row["category"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
        )

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None


# Convenience functions for common memory operations
def remember_user_info(store: MemoryStore, key: str, value: str) -> Memory:
    """Remember something about the user (high importance)."""
    return store.remember(key, value, importance=0.8, category=MemoryStore.CATEGORY_USER)


def remember_preference(store: MemoryStore, key: str, value: str) -> Memory:
    """Remember a user preference (high importance)."""
    return store.remember(key, value, importance=0.9, category=MemoryStore.CATEGORY_PREFERENCE)


def remember_event(store: MemoryStore, description: str, importance: float = 0.5) -> Memory:
    """Remember an event (auto-generated key)."""
    key = f"event_{int(time.time())}"
    return store.remember(key, description, importance=importance, category=MemoryStore.CATEGORY_EVENT)


def remember_social(store: MemoryStore, device_id: str, info: str) -> Memory:
    """Remember something about another Inkling."""
    return store.remember(device_id, info, importance=0.6, category=MemoryStore.CATEGORY_SOCIAL)
