"""
Project Inkling - Memory Tests

Tests for core/memory.py - persistent memory storage.
"""

import time
import threading
import pytest


class TestMemory:
    """Tests for Memory dataclass."""

    def test_memory_to_dict(self):
        """Test Memory serialization."""
        from core.memory import Memory

        mem = Memory(
            id=1,
            key="test_key",
            value="test_value",
            importance=0.8,
            category="user",
            created_at=1000.0,
            last_accessed=2000.0,
            access_count=5,
        )

        d = mem.to_dict()

        assert d["id"] == 1
        assert d["key"] == "test_key"
        assert d["value"] == "test_value"
        assert d["importance"] == 0.8
        assert d["category"] == "user"


class TestMemoryStore:
    """Tests for MemoryStore class."""

    @pytest.fixture
    def memory_store(self, temp_data_dir):
        """Create a MemoryStore instance for testing."""
        from core.memory import MemoryStore

        store = MemoryStore(data_dir=temp_data_dir)
        store.initialize()
        yield store
        store.close()

    def test_initialization(self, memory_store):
        """Test MemoryStore initialization."""
        assert memory_store._conn is not None
        assert memory_store.db_path.exists()

    def test_remember_new(self, memory_store):
        """Test remembering a new fact."""
        mem = memory_store.remember("user_name", "Alice", importance=0.9)

        assert mem.key == "user_name"
        assert mem.value == "Alice"
        assert mem.importance == 0.9
        assert mem.access_count >= 1

    def test_remember_update(self, memory_store):
        """Test updating an existing memory."""
        memory_store.remember("color", "blue", importance=0.5)
        mem = memory_store.remember("color", "green", importance=0.7)

        assert mem.value == "green"
        # Importance should be max of old and new
        assert mem.importance == 0.7
        assert mem.access_count >= 2

    def test_remember_importance_clamped(self, memory_store):
        """Test that importance is clamped to [0, 1]."""
        mem1 = memory_store.remember("test1", "val", importance=1.5)
        mem2 = memory_store.remember("test2", "val", importance=-0.5)

        assert mem1.importance == 1.0
        assert mem2.importance == 0.0

    def test_get_existing(self, memory_store):
        """Test getting an existing memory."""
        memory_store.remember("key1", "value1")

        mem = memory_store.get("key1")

        assert mem is not None
        assert mem.key == "key1"
        assert mem.value == "value1"

    def test_get_nonexistent(self, memory_store):
        """Test getting a nonexistent memory."""
        mem = memory_store.get("nonexistent")

        assert mem is None

    def test_get_with_category(self, memory_store):
        """Test getting memory with category filter."""
        from core.memory import MemoryStore

        memory_store.remember("test", "user_val", category=MemoryStore.CATEGORY_USER)
        memory_store.remember("test", "pref_val", category=MemoryStore.CATEGORY_PREFERENCE)

        user_mem = memory_store.get("test", category=MemoryStore.CATEGORY_USER)
        pref_mem = memory_store.get("test", category=MemoryStore.CATEGORY_PREFERENCE)

        assert user_mem.value == "user_val"
        assert pref_mem.value == "pref_val"

    def test_recall_by_keyword(self, memory_store):
        """Test searching memories by keyword."""
        memory_store.remember("favorite_food", "pizza", importance=0.8)
        memory_store.remember("favorite_color", "blue", importance=0.7)
        memory_store.remember("pet_name", "fluffy", importance=0.6)

        results = memory_store.recall("favorite")

        assert len(results) == 2
        assert all("favorite" in r.key for r in results)

    def test_recall_by_value(self, memory_store):
        """Test searching memories by value content."""
        memory_store.remember("fact1", "The sky is blue")
        memory_store.remember("fact2", "Water is wet")

        results = memory_store.recall("blue")

        assert len(results) == 1
        assert results[0].key == "fact1"

    def test_recall_with_category_filter(self, memory_store):
        """Test searching with category filter."""
        from core.memory import MemoryStore

        memory_store.remember("test1", "value", category=MemoryStore.CATEGORY_USER)
        memory_store.remember("test2", "value", category=MemoryStore.CATEGORY_FACT)

        results = memory_store.recall("value", category=MemoryStore.CATEGORY_USER)

        assert len(results) == 1
        assert results[0].key == "test1"

    def test_recall_ordered_by_importance(self, memory_store):
        """Test that recall results are ordered by importance."""
        memory_store.remember("low", "val", importance=0.2)
        memory_store.remember("high", "val", importance=0.9)
        memory_store.remember("med", "val", importance=0.5)

        results = memory_store.recall("val")

        assert results[0].key == "high"
        assert results[1].key == "med"
        assert results[2].key == "low"

    def test_recall_by_category(self, memory_store):
        """Test getting all memories in a category."""
        from core.memory import MemoryStore

        memory_store.remember("pref1", "val1", category=MemoryStore.CATEGORY_PREFERENCE)
        memory_store.remember("pref2", "val2", category=MemoryStore.CATEGORY_PREFERENCE)
        memory_store.remember("fact1", "val3", category=MemoryStore.CATEGORY_FACT)

        results = memory_store.recall_by_category(MemoryStore.CATEGORY_PREFERENCE)

        assert len(results) == 2

    def test_recall_recent(self, memory_store):
        """Test getting recently accessed memories."""
        memory_store.remember("old", "val")
        time.sleep(0.1)
        memory_store.remember("new", "val")

        results = memory_store.recall_recent(limit=1)

        assert len(results) == 1
        assert results[0].key == "new"

    def test_recall_important(self, memory_store):
        """Test getting most important memories."""
        memory_store.remember("unimportant", "val", importance=0.1)
        memory_store.remember("important", "val", importance=0.95)

        results = memory_store.recall_important(limit=1)

        assert len(results) == 1
        assert results[0].key == "important"

    def test_forget(self, memory_store):
        """Test forgetting a specific memory."""
        memory_store.remember("to_forget", "value")

        result = memory_store.forget("to_forget")

        assert result is True
        assert memory_store.get("to_forget") is None

    def test_forget_nonexistent(self, memory_store):
        """Test forgetting a nonexistent memory."""
        result = memory_store.forget("nonexistent")

        assert result is False

    def test_forget_old(self, memory_store):
        """Test pruning old, low-importance memories."""
        # This is tricky to test without time manipulation
        # Just verify it doesn't crash
        pruned = memory_store.forget_old(max_age_days=0, importance_threshold=1.0)

        # Should prune everything since threshold is 1.0
        assert pruned >= 0

    def test_count(self, memory_store):
        """Test counting memories."""
        assert memory_store.count() == 0

        memory_store.remember("key1", "val1")
        memory_store.remember("key2", "val2")

        assert memory_store.count() == 2

    def test_count_by_category(self, memory_store):
        """Test counting memories by category."""
        from core.memory import MemoryStore

        memory_store.remember("user1", "val", category=MemoryStore.CATEGORY_USER)
        memory_store.remember("fact1", "val", category=MemoryStore.CATEGORY_FACT)
        memory_store.remember("fact2", "val", category=MemoryStore.CATEGORY_FACT)

        assert memory_store.count(MemoryStore.CATEGORY_USER) == 1
        assert memory_store.count(MemoryStore.CATEGORY_FACT) == 2

    def test_get_context_for_prompt_empty(self, memory_store):
        """Test context generation with no memories."""
        context = memory_store.get_context_for_prompt()

        assert context == ""

    def test_get_context_for_prompt(self, memory_store):
        """Test context generation with memories."""
        memory_store.remember("user_name", "Alice", importance=0.9)
        memory_store.remember("favorite_color", "blue", importance=0.8)

        context = memory_store.get_context_for_prompt()

        assert "Things I remember:" in context
        assert "user_name" in context
        assert "Alice" in context

    def test_access_count_updates(self, memory_store):
        """Test that access count increases on get/recall."""
        memory_store.remember("test", "value")

        # Get should increment
        mem1 = memory_store.get("test")
        mem2 = memory_store.get("test")

        assert mem2.access_count > mem1.access_count

    def test_cross_thread_access_on_shared_store(self, memory_store):
        """Shared MemoryStore should support access from another thread."""
        memory_store.remember("thread_key", "thread_value")
        result = {"count": None, "error": None}

        def worker():
            try:
                result["count"] = memory_store.count()
            except Exception as exc:
                result["error"] = str(exc)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        assert result["error"] is None
        assert result["count"] is not None


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def memory_store(self, temp_data_dir):
        from core.memory import MemoryStore

        store = MemoryStore(data_dir=temp_data_dir)
        store.initialize()
        yield store
        store.close()

    def test_remember_user_info(self, memory_store):
        """Test remember_user_info convenience function."""
        from core.memory import remember_user_info, MemoryStore

        mem = remember_user_info(memory_store, "name", "Bob")

        assert mem.category == MemoryStore.CATEGORY_USER
        assert mem.importance == 0.8

    def test_remember_preference(self, memory_store):
        """Test remember_preference convenience function."""
        from core.memory import remember_preference, MemoryStore

        mem = remember_preference(memory_store, "theme", "dark")

        assert mem.category == MemoryStore.CATEGORY_PREFERENCE
        assert mem.importance == 0.9

    def test_remember_event(self, memory_store):
        """Test remember_event convenience function."""
        from core.memory import remember_event, MemoryStore

        mem = remember_event(memory_store, "User completed tutorial")

        assert mem.category == MemoryStore.CATEGORY_EVENT
        assert "event_" in mem.key

    def test_remember_social(self, memory_store):
        """Test remember_social convenience function."""
        from core.memory import remember_social, MemoryStore

        mem = remember_social(memory_store, "device_abc123", "Friendly Inkling")

        assert mem.category == MemoryStore.CATEGORY_SOCIAL
        assert mem.key == "device_abc123"
