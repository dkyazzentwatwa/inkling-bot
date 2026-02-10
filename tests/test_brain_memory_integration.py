"""Tests for Brain + MemoryStore integration."""

import asyncio

from core.brain import Brain, ThinkResult
from core.memory import MemoryStore


class _DummyProvider:
    """Simple provider for deterministic Brain tests."""

    def __init__(self, content: str = "ok"):
        self._content = content
        self.last_system_prompt = None

    @property
    def name(self) -> str:
        return "dummy"

    async def generate(self, system_prompt, messages, tools=None):
        self.last_system_prompt = system_prompt
        return ThinkResult(
            content=self._content,
            tokens_used=1,
            provider="dummy",
            model="dummy-model",
        )


def test_brain_enriches_system_prompt_with_relevant_memory(temp_data_dir):
    store = MemoryStore(data_dir=temp_data_dir)
    store.initialize()
    try:
        store.remember("user_name", "Alice", category=MemoryStore.CATEGORY_USER, importance=0.9)
        store.remember(
            "favorite_food",
            "pizza",
            category=MemoryStore.CATEGORY_PREFERENCE,
            importance=0.9,
        )

        brain = Brain(
            config={},
            memory_store=store,
            memory_config={
                "enabled": True,
                "prompt_context": {"enabled": True, "max_items": 5},
                "capture": {"rule_based": False, "llm_enabled": False},
            },
        )
        provider = _DummyProvider()
        brain.providers = [provider]

        asyncio.run(
            brain.think(
                user_message="What is my name?",
                system_prompt="Base system prompt",
                use_tools=False,
            )
        )

        assert provider.last_system_prompt is not None
        assert "Base system prompt" in provider.last_system_prompt
        assert "Things I remember" in provider.last_system_prompt
        assert "user_name: Alice" in provider.last_system_prompt
    finally:
        store.close()


def test_brain_extracts_user_info_and_preferences_from_chat(temp_data_dir):
    store = MemoryStore(data_dir=temp_data_dir)
    store.initialize()
    try:
        brain = Brain(
            config={},
            memory_store=store,
            memory_config={
                "enabled": True,
                "prompt_context": {"enabled": False},
                "capture": {
                    "rule_based": True,
                    "llm_enabled": False,
                    "max_new_per_turn": 5,
                },
            },
        )
        brain.providers = [_DummyProvider(content="Nice to meet you.")]

        asyncio.run(
            brain.think(
                user_message="My name is Bob and I like sushi.",
                system_prompt="Base system prompt",
                use_tools=False,
            )
        )

        name_mem = store.get("user_name", category=MemoryStore.CATEGORY_USER)
        pref_hits = store.recall("sushi", category=MemoryStore.CATEGORY_PREFERENCE, limit=5)

        assert name_mem is not None
        assert name_mem.value == "Bob"
        assert len(pref_hits) >= 1
    finally:
        store.close()


def test_brain_think_is_safe_when_memory_unavailable():
    brain = Brain(
        config={},
        memory_store=None,
        memory_config={
            "enabled": True,
            "prompt_context": {"enabled": True},
            "capture": {"rule_based": True, "llm_enabled": False},
        },
    )
    brain.providers = [_DummyProvider(content="All good.")]

    result = asyncio.run(
        brain.think(
            user_message="I like tea.",
            system_prompt="Base system prompt",
            use_tools=False,
        )
    )

    assert result.content == "All good."
