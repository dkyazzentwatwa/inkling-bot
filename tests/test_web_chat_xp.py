"""Regression tests for web chat XP awarding behavior."""

import asyncio

from core.brain import ThinkResult
from core.progression import ChatQuality
from modes.web_chat import WebChatMode


class _DummyFuture:
    """Simple Future-like wrapper for synchronous coroutine execution in tests."""

    def __init__(self, value):
        self._value = value

    def result(self, timeout=None):
        del timeout
        return self._value


class _DisplayStub:
    """Minimal display stub for WebChatMode tests."""

    def __init__(self):
        self.chat_count = 0

    def set_mode(self, _mode):
        return None

    def increment_chat_count(self):
        self.chat_count += 1

    async def update(self, **kwargs):
        del kwargs
        return None

    async def show_message_paginated(self, **kwargs):
        del kwargs
        return 1


class _BrainStub:
    """Minimal brain stub that returns a deterministic ThinkResult."""

    def __init__(self, result):
        self._result = result

    async def think(self, **kwargs):
        del kwargs
        return self._result


def test_web_chat_uses_chat_quality_for_xp(monkeypatch, personality):
    """Web chat should award XP with chat quality + user message context."""
    chat_quality = ChatQuality(
        message_length=80,
        turn_count=3,
        is_question=True,
        sentiment="positive",
    )
    think_result = ThinkResult(
        content="Great question!",
        tokens_used=42,
        provider="test-provider",
        model="test-model",
        chat_quality=chat_quality,
    )

    brain = _BrainStub(think_result)
    display = _DisplayStub()
    mode = WebChatMode(brain=brain, display=display, personality=personality)
    mode._loop = object()

    captured = {"calls": 0}

    def fake_on_interaction(*, positive, chat_quality, user_message):
        captured["calls"] += 1
        captured["positive"] = positive
        captured["chat_quality"] = chat_quality
        captured["user_message"] = user_message
        return 15

    monkeypatch.setattr(personality, "on_interaction", fake_on_interaction)

    def run_coroutine_sync(coro, loop):
        del loop
        return _DummyFuture(asyncio.run(coro))

    monkeypatch.setattr("modes.web_chat.asyncio.run_coroutine_threadsafe", run_coroutine_sync)

    result = mode._handle_chat_sync("How are you today?")

    assert captured["calls"] == 1
    assert captured["positive"] is True
    assert captured["chat_quality"] is chat_quality
    assert captured["user_message"] == "How are you today?"
    assert "+15 XP" in result["meta"]
    assert display.chat_count == 1
