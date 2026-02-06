"""Tests for OpenAI-compatible provider behavior (Ollama Cloud)."""

import asyncio

from core.brain import Brain, Message, OpenAIProvider


class _DummyCompletions:
    def __init__(self, capture):
        self._capture = capture

    async def create(self, **kwargs):
        self._capture.update(kwargs)

        class _Msg:
            content = "ok"
            tool_calls = None

        class _Choice:
            message = _Msg()

        class _Usage:
            total_tokens = 1

        class _Resp:
            choices = [_Choice()]
            usage = _Usage()

        return _Resp()


class _DummyChat:
    def __init__(self, capture):
        self.completions = _DummyCompletions(capture)


class _DummyClient:
    def __init__(self, capture):
        self.chat = _DummyChat(capture)


def test_openai_provider_ollama_cloud_uses_max_tokens(monkeypatch):
    provider = OpenAIProvider(
        api_key="ollama-cloud-key",
        model="gpt-oss:20b",
        max_tokens=123,
        base_url="https://ollama.com/v1",
    )

    capture = {}
    monkeypatch.setattr(provider, "_get_client", lambda: _DummyClient(capture))

    asyncio.run(
        provider.generate(
            system_prompt="sys",
            messages=[Message(role="user", content="hi")],
            tools=None,
        )
    )

    assert "max_tokens" in capture
    assert capture["max_tokens"] == 123
    assert "max_completion_tokens" not in capture


def test_openai_provider_groq_cloud_uses_max_tokens(monkeypatch):
    provider = OpenAIProvider(
        api_key="groq-key",
        model="llama-3.1-8b-instant",
        max_tokens=64,
        base_url="https://api.groq.com/openai/v1",
    )

    capture = {}
    monkeypatch.setattr(provider, "_get_client", lambda: _DummyClient(capture))

    asyncio.run(
        provider.generate(
            system_prompt="sys",
            messages=[Message(role="user", content="hi")],
            tools=None,
        )
    )

    assert "max_completion_tokens" in capture
    assert capture["max_completion_tokens"] == 64
    assert "max_tokens" not in capture


def test_openai_provider_default_uses_max_completion_tokens(monkeypatch):
    provider = OpenAIProvider(
        api_key="openai-key",
        model="gpt-5-mini",
        max_tokens=77,
        base_url=None,
    )

    capture = {}
    monkeypatch.setattr(provider, "_get_client", lambda: _DummyClient(capture))

    asyncio.run(
        provider.generate(
            system_prompt="sys",
            messages=[Message(role="user", content="hi")],
            tools=None,
        )
    )

    assert "max_completion_tokens" in capture
    assert capture["max_completion_tokens"] == 77
    assert "max_tokens" not in capture


def test_brain_ollama_cloud_uses_ollama_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-cloud-key")

    config = {
        "primary": "openai",
        "openai": {
            "base_url": "https://ollama.com/v1",
            "model": "gpt-oss:20b",
            "max_tokens": 50,
        },
    }

    brain = Brain(config)
    providers = [p for p in brain.providers if p.name == "openai"]

    assert providers
    assert providers[0].api_key == "ollama-cloud-key"


def test_brain_ollama_cloud_missing_key_skips_provider(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    config = {
        "primary": "openai",
        "openai": {
            "base_url": "https://ollama.com/v1",
            "model": "gpt-oss:20b",
            "max_tokens": 50,
        },
    }

    brain = Brain(config)
    providers = [p for p in brain.providers if p.name == "openai"]

    assert not providers

    output = capsys.readouterr().out
    assert "Ollama Cloud base_url set" in output


def test_brain_groq_cloud_uses_groq_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")

    config = {
        "primary": "openai",
        "openai": {
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.1-8b-instant",
            "max_tokens": 50,
        },
    }

    brain = Brain(config)
    providers = [p for p in brain.providers if p.name == "openai"]

    assert providers
    assert providers[0].api_key == "groq-key"


def test_brain_groq_cloud_missing_key_skips_provider(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    config = {
        "primary": "openai",
        "openai": {
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.1-8b-instant",
            "max_tokens": 50,
        },
    }

    brain = Brain(config)
    providers = [p for p in brain.providers if p.name == "openai"]

    assert not providers

    output = capsys.readouterr().out
    assert "Groq base_url set" in output
