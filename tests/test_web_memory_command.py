"""Regression tests for web /memory command behavior."""

import threading
from types import SimpleNamespace

from core.memory import MemoryStore
from modes.web.commands.utilities import UtilityCommands


def _build_web_mode(memory_store):
    personality = SimpleNamespace(face="happy", last_thought=None)
    return SimpleNamespace(
        personality=personality,
        display=None,
        brain=None,
        task_manager=None,
        memory_store=memory_store,
        focus_manager=None,
        scheduler=None,
        _config={},
        _loop=None,
        _get_face_str=lambda: "happy",
    )


def test_web_memory_command_cross_thread(temp_data_dir):
    """Shared MemoryStore should work when /memory is called on a worker thread."""
    store = MemoryStore(data_dir=temp_data_dir)
    store.initialize()
    store.remember("user_name", "Cypher", importance=0.9, category=MemoryStore.CATEGORY_USER)

    cmd = UtilityCommands(_build_web_mode(store))
    result = {"response": None, "error": None}

    def worker():
        try:
            result["response"] = cmd.memory()
        except Exception as exc:  # pragma: no cover - regression guard
            result["error"] = str(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    store.close()

    assert result["error"] is None
    assert isinstance(result["response"], dict)
    assert "Memory Store" in result["response"]["response"]
