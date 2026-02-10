"""
Project Inkling - AI Brain (Multi-Provider)

Handles AI responses using Anthropic (Claude) and OpenAI (GPT) with automatic fallback.
Implements retry logic, token budgeting, and rate limiting.
"""

import asyncio
import json
import re
import time
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path

from .progression import ChatQuality
from .memory import MemoryStore


def _sanitize_error(msg: str) -> str:
    """Remove potential API keys and sensitive data from error messages."""
    msg = re.sub(r'sk-[a-zA-Z0-9\-]{10,}', '[REDACTED]', msg)
    msg = re.sub(r'sk-ant-[a-zA-Z0-9\-]{10,}', '[REDACTED]', msg)
    msg = re.sub(r'key[=:\s]+\S{10,}', 'key=[REDACTED]', msg, flags=re.IGNORECASE)
    return msg


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass


class QuotaExceededError(ProviderError):
    """Daily/monthly quota exceeded."""
    pass


class AllProvidersExhaustedError(ProviderError):
    """All providers failed."""
    pass


@dataclass
class TokenBudget:
    """Track token usage and enforce budgets. Persists across restarts."""
    daily_limit: int = 10000
    per_request_max: int = 500

    # Usage tracking
    tokens_used_today: int = 0
    last_reset: float = field(default_factory=time.time)

    # Persistence path
    _persist_path: str = field(default="", repr=False)

    def __post_init__(self):
        if not self._persist_path:
            self._persist_path = str(Path("~/.inkling/token_budget.json").expanduser())
        self._load()

    def check_budget(self, estimated_tokens: int) -> bool:
        """Check if we have budget for this request."""
        self._maybe_reset()
        return (self.tokens_used_today + estimated_tokens) <= self.daily_limit

    def record_usage(self, tokens: int) -> None:
        """Record token usage."""
        self._maybe_reset()
        self.tokens_used_today += tokens
        self._save()

    def _maybe_reset(self) -> None:
        """Reset daily counter if new day."""
        now = time.time()
        # Reset if more than 24 hours since last reset
        if now - self.last_reset > 86400:
            self.tokens_used_today = 0
            self.last_reset = now
            self._save()

    def _save(self) -> None:
        """Persist token usage to disk."""
        try:
            data = {
                "tokens_used_today": self.tokens_used_today,
                "last_reset": self.last_reset,
            }
            persist_path = Path(self._persist_path)
            persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(persist_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass  # Non-critical — budget still works in-memory

    def _load(self) -> None:
        """Load persisted token usage from disk."""
        try:
            persist_path = Path(self._persist_path)
            if persist_path.exists():
                with open(persist_path, 'r') as f:
                    data = json.load(f)
                self.tokens_used_today = data.get("tokens_used_today", 0)
                self.last_reset = data.get("last_reset", time.time())
                # Check if budget needs resetting after load
                self._maybe_reset()
        except Exception:
            pass  # Start fresh if load fails

    @property
    def remaining(self) -> int:
        """Tokens remaining today."""
        self._maybe_reset()
        return max(0, self.daily_limit - self.tokens_used_today)


@dataclass
class Message:
    """A chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCall:
    """A tool call requested by the AI."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ThinkResult:
    """Result from AI thinking."""
    content: str
    tokens_used: int
    provider: str
    model: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    is_tool_use: bool = False
    chat_quality: Optional[ChatQuality] = None  # Quality analysis for XP


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 150):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ThinkResult:
        """Generate a response, optionally using tools."""
        pass


class AnthropicProvider(AIProvider):
    """Anthropic (Claude) provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
        max_tokens: int = 150
    ):
        super().__init__(api_key, model, max_tokens)
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        system_prompt: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ThinkResult:
        """Generate using Claude, with optional tool use."""
        client = self._get_client()

        # Convert messages to Anthropic format
        api_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        try:
            # Build request kwargs
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system_prompt,
                "messages": api_messages,
            }

            # Add tools if provided
            if tools:
                kwargs["tools"] = tools

            response = await client.messages.create(**kwargs)

            # Parse response - handle both text and tool use
            content = ""
            tool_calls = []

            for block in response.content:
                if hasattr(block, "text"):
                    content = block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    ))

            tokens = response.usage.input_tokens + response.usage.output_tokens
            is_tool_use = response.stop_reason == "tool_use"

            return ThinkResult(
                content=content,
                tokens_used=tokens,
                provider=self.name,
                model=self.model,
                tool_calls=tool_calls,
                is_tool_use=is_tool_use,
            )

        except Exception as e:
            error_str = str(e).lower()
            sanitized = _sanitize_error(str(e))
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"Anthropic rate limit: {sanitized}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"Anthropic quota: {sanitized}")
            raise ProviderError(f"Anthropic error: {sanitized}")


class OpenAIProvider(AIProvider):
    """OpenAI (GPT) provider.

    Also supports OpenAI-compatible APIs (Ollama, Together, Groq, OpenRouter, etc.)
    by specifying a custom base_url.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-mini",
        max_tokens: int = 150,
        base_url: Optional[str] = None,
    ):
        super().__init__(api_key, model, max_tokens)
        self._client = None
        self.base_url = base_url

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,  # None uses default OpenAI URL
            )
        return self._client

    def _is_ollama_cloud(self) -> bool:
        """Return True if base_url points to Ollama Cloud."""
        if not self.base_url:
            return False
        return "ollama.com" in self.base_url.lower()

    async def generate(
        self,
        system_prompt: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ThinkResult:
        """Generate using GPT, with optional tool use."""
        client = self._get_client()

        # Convert messages to OpenAI format (with system message)
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend([
            {"role": m.role, "content": m.content}
            for m in messages
        ])

        try:
            kwargs = {
                "model": self.model,
                "messages": api_messages,
            }
            if self._is_ollama_cloud():
                kwargs["max_tokens"] = self.max_tokens
            else:
                kwargs["max_completion_tokens"] = self.max_tokens

            # Convert tools to OpenAI format
            if tools:
                kwargs["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t.get("description", ""),
                            "parameters": t.get("input_schema", {}),
                        }
                    }
                    for t in tools
                ]

            response = await client.chat.completions.create(**kwargs)

            # Debug: Print raw response structure
            if os.environ.get("INKLING_DEBUG"):
                print(f"[OpenAI] Raw response: {response}")
                print(f"[OpenAI] Choices: {response.choices}")
                print(f"[OpenAI] Message: {response.choices[0].message}")

            message = response.choices[0].message
            content = message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            # Parse tool calls
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                    ))

            is_tool_use = len(tool_calls) > 0

            return ThinkResult(
                content=content,
                tokens_used=tokens,
                provider=self.name,
                model=self.model,
                tool_calls=tool_calls,
                is_tool_use=is_tool_use,
            )

        except Exception as e:
            error_str = str(e).lower()
            sanitized = _sanitize_error(str(e))
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"OpenAI rate limit: {sanitized}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"OpenAI quota: {sanitized}")
            raise ProviderError(f"OpenAI error: {sanitized}")


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        max_tokens: int = 150
    ):
        super().__init__(api_key, model, max_tokens)
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        system_prompt: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ThinkResult:
        """Generate using Gemini, with optional tool use."""
        client = self._get_client()

        # Build contents (Gemini uses role "model" for assistant)
        contents = []
        for m in messages:
            contents.append({
                "role": "user" if m.role == "user" else "model",
                "parts": [{"text": m.content}]
            })

        # Convert tools to Gemini format if provided
        gemini_tools = self._convert_tools(tools) if tools else None

        try:
            config = {
                "system_instruction": system_prompt,
                "max_output_tokens": self.max_tokens,
            }
            if gemini_tools:
                config["tools"] = gemini_tools

            response = await client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            # Parse response
            content = response.text or ""
            tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

            # Handle function calls
            tool_calls = []
            is_tool_use = False
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        tool_calls.append(ToolCall(
                            id=fc.name,  # Gemini doesn't use IDs like Anthropic
                            name=fc.name,
                            arguments=dict(fc.args) if fc.args else {},
                        ))
                        is_tool_use = True

            return ThinkResult(
                content=content,
                tokens_used=tokens,
                provider=self.name,
                model=self.model,
                tool_calls=tool_calls,
                is_tool_use=is_tool_use,
            )

        except Exception as e:
            error_str = str(e).lower()
            sanitized = _sanitize_error(str(e))
            if "rate" in error_str or "429" in error_str or "quota" in error_str:
                raise RateLimitError(f"Gemini rate limit: {sanitized}")
            if "resource" in error_str or "exhausted" in error_str:
                raise QuotaExceededError(f"Gemini quota: {sanitized}")
            raise ProviderError(f"Gemini error: {sanitized}")

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict]:
        """Convert MCP tools to Gemini function declaration format."""
        gemini_tools = []
        for t in tools:
            gemini_tools.append({
                "function_declarations": [{
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                }]
            })
        return gemini_tools


class OllamaProvider(AIProvider):
    """Ollama cloud provider.

    Uses Ollama's native cloud API at https://ollama.com/api/chat.
    Supports models like qwen3-coder-next, kimi-k2.5, nemotron-3-nano:30b-cloud, gpt-oss:120b-cloud, etc.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3-coder-next",
        max_tokens: int = 150,
        base_url: str = "https://ollama.com/api",
    ):
        super().__init__(api_key, model, max_tokens)
        self.base_url = base_url

    @property
    def name(self) -> str:
        return "ollama"

    async def generate(
        self,
        system_prompt: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ThinkResult:
        """Generate using Ollama cloud native API."""
        import aiohttp

        # Convert messages to Ollama format (system message as first user message)
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend([
            {"role": m.role, "content": m.content}
            for m in messages
        ])

        # Build request payload
        payload = {
            "model": self.model,
            "messages": api_messages,
            "stream": False,  # Non-streaming mode
        }

        # Add tool support if provided (Ollama supports OpenAI-style tools)
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    }
                }
                for t in tools
            ]

        # Make request to Ollama cloud API
        url = f"{self.base_url}/chat"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ProviderError(f"Ollama API error {response.status}: {_sanitize_error(error_text)}")

                    data = await response.json()

                    # Debug: Print raw response structure
                    if os.environ.get("INKLING_DEBUG"):
                        print(f"[Ollama] Raw response: {data}")

                    # Parse Ollama response format
                    message = data.get("message", {})
                    content = message.get("content", "")

                    # Estimate tokens (Ollama provides eval_count and prompt_eval_count)
                    prompt_tokens = data.get("prompt_eval_count", 0)
                    completion_tokens = data.get("eval_count", 0)
                    tokens = prompt_tokens + completion_tokens

                    # Parse tool calls if present
                    tool_calls = []
                    if "tool_calls" in message:
                        for tc in message["tool_calls"]:
                            tool_calls.append(ToolCall(
                                id=tc.get("id", tc["function"]["name"]),
                                name=tc["function"]["name"],
                                arguments=tc["function"].get("arguments", {}),
                            ))

                    is_tool_use = len(tool_calls) > 0

                    return ThinkResult(
                        content=content,
                        tokens_used=tokens,
                        provider=self.name,
                        model=self.model,
                        tool_calls=tool_calls,
                        is_tool_use=is_tool_use,
                    )

        except aiohttp.ClientError as e:
            raise ProviderError(f"Ollama connection error: {_sanitize_error(str(e))}")
        except Exception as e:
            error_str = str(e).lower()
            sanitized = _sanitize_error(str(e))
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"Ollama rate limit: {sanitized}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"Ollama quota: {sanitized}")
            raise ProviderError(f"Ollama error: {sanitized}")


class Brain:
    """
    Multi-provider AI brain for Inkling.

    Features:
    - Automatic fallback between providers
    - Retry logic with exponential backoff
    - Token budget tracking
    - Conversation history management
    - MCP tool integration
    """

    def __init__(
        self,
        config: Dict[str, Any],
        mcp_client=None,
        memory_store: Optional[MemoryStore] = None,
        memory_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the brain with configuration.

        Config should include:
        - anthropic: {api_key, model, max_tokens}
        - openai: {api_key, model, max_tokens}
        - gemini: {api_key, model, max_tokens}
        - ollama: {api_key, model, max_tokens, base_url}
        - primary: "anthropic", "openai", "gemini", or "ollama"
        - budget: {daily_tokens, per_request_max}

        Args:
            config: AI configuration dict
            mcp_client: Optional MCPClientManager for tool use
        """
        self.config = config
        self.providers: List[AIProvider] = []
        self.budget = TokenBudget(
            daily_limit=config.get("budget", {}).get("daily_tokens", 10000),
            per_request_max=config.get("budget", {}).get("per_request_max", 500),
        )
        self.mcp_client = mcp_client
        self.memory_store = memory_store
        self.memory_config = memory_config or {}
        self._memory_enabled = self.memory_config.get("enabled", True)

        prompt_config = self.memory_config.get("prompt_context", {})
        self._memory_prompt_enabled = prompt_config.get("enabled", True)
        self._memory_prompt_max_items = max(1, int(prompt_config.get("max_items", 6)))
        self._memory_prompt_max_chars = max(100, int(prompt_config.get("max_chars", 600)))

        capture_config = self.memory_config.get("capture", {})
        self._memory_capture_rule_based = capture_config.get("rule_based", True)
        self._memory_capture_llm_enabled = capture_config.get("llm_enabled", False)
        self._memory_capture_max_new = max(1, int(capture_config.get("max_new_per_turn", 5)))

        # Conversation history
        self._messages: List[Message] = []
        self._max_history = 10  # Keep last N messages

        # Initialize providers
        self._init_providers()

        # Load saved conversation history
        self.load_messages()

    def _init_providers(self) -> None:
        """Initialize AI providers based on config."""
        primary = self.config.get("primary", "anthropic")

        # Get API keys from config or environment
        anthropic_config = self.config.get("anthropic", {})
        openai_config = self.config.get("openai", {})
        gemini_config = self.config.get("gemini", {})
        ollama_config = self.config.get("ollama", {})

        anthropic_key = anthropic_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        openai_base_url = openai_config.get("base_url")
        ollama_cloud = bool(openai_base_url and "ollama.com" in openai_base_url.lower())
        groq_cloud = bool(openai_base_url and "api.groq.com" in openai_base_url.lower())
        if ollama_cloud:
            openai_key = openai_config.get("api_key") or os.environ.get("OLLAMA_API_KEY")
        elif groq_cloud:
            openai_key = openai_config.get("api_key") or os.environ.get("GROQ_API_KEY")
        else:
            openai_key = openai_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        gemini_key = (
            gemini_config.get("api_key")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        ollama_key = ollama_config.get("api_key") or os.environ.get("OLLAMA_API_KEY")

        # Debug output
        print(f"[Brain] Primary provider: {primary}")
        print(
            "[Brain] API keys detected: Anthropic="
            f"{bool(anthropic_key)}, OpenAI={bool(openai_key)}, "
            f"Gemini={bool(gemini_key)}, Ollama={bool(ollama_key)}"
        )

        # Build provider list with primary first
        if primary == "anthropic" and anthropic_key:
            self.providers.append(AnthropicProvider(
                api_key=anthropic_key,
                model=anthropic_config.get("model", "claude-3-haiku-20240307"),
                max_tokens=anthropic_config.get("max_tokens", 150),
            ))
        elif primary == "gemini" and gemini_key:
            self.providers.append(GeminiProvider(
                api_key=gemini_key,
                model=gemini_config.get("model", "gemini-2.5-flash"),
                max_tokens=gemini_config.get("max_tokens", 150),
            ))
        elif primary == "ollama" and ollama_key:
            self.providers.append(OllamaProvider(
                api_key=ollama_key,
                model=ollama_config.get("model", "qwen3-coder-next"),
                max_tokens=ollama_config.get("max_tokens", 150),
                base_url=ollama_config.get("base_url", "https://ollama.com/api"),
            ))

        if openai_key:
            self.providers.append(OpenAIProvider(
                api_key=openai_key,
                model=openai_config.get("model", "gpt-5-mini"),
                max_tokens=openai_config.get("max_tokens", 150),
                base_url=openai_base_url,
            ))
        elif ollama_cloud:
            print(
                "[Brain] Warning: Ollama Cloud base_url set but no OLLAMA_API_KEY or "
                "openai.api_key configured; skipping OpenAI provider."
            )
        elif groq_cloud:
            print(
                "[Brain] Warning: Groq base_url set but no GROQ_API_KEY or "
                "openai.api_key configured; skipping OpenAI provider."
            )

        # Add ollama as fallback if not primary
        if primary != "ollama" and ollama_key:
            self.providers.append(OllamaProvider(
                api_key=ollama_key,
                model=ollama_config.get("model", "qwen3-coder-next"),
                max_tokens=ollama_config.get("max_tokens", 150),
                base_url=ollama_config.get("base_url", "https://ollama.com/api"),
            ))

        # Add gemini as fallback if not primary
        if primary != "gemini" and gemini_key:
            self.providers.append(GeminiProvider(
                api_key=gemini_key,
                model=gemini_config.get("model", "gemini-2.5-flash"),
                max_tokens=gemini_config.get("max_tokens", 150),
            ))

        # Add anthropic as fallback if not primary
        if primary != "anthropic" and anthropic_key:
            self.providers.append(AnthropicProvider(
                api_key=anthropic_key,
                model=anthropic_config.get("model", "claude-3-haiku-20240307"),
                max_tokens=anthropic_config.get("max_tokens", 150),
            ))

        if not self.providers:
            print("[Brain] Warning: No AI providers configured!")

    async def think(
        self,
        user_message: str,
        system_prompt: str,
        max_retries: int = 3,
        use_tools: bool = True,
        max_tool_rounds: int = 5,
        status_callback=None,
    ) -> ThinkResult:
        """
        Process user message and generate AI response.

        Args:
            user_message: The user's input
            system_prompt: System prompt with personality context
            max_retries: Maximum retry attempts per provider
            use_tools: Whether to enable MCP tool use
            max_tool_rounds: Maximum tool execution rounds
            status_callback: Optional async callback(face, text, status) for UI updates

        Returns:
            ThinkResult with response content and metadata

        Raises:
            AllProvidersExhaustedError: If all providers fail
            QuotaExceededError: If daily budget exceeded
        """
        # Check budget
        if not self.budget.check_budget(self.budget.per_request_max):
            raise QuotaExceededError(
                f"Daily token budget exceeded. Remaining: {self.budget.remaining}"
            )

        # Add user message to history
        self._messages.append(Message(role="user", content=user_message))
        self._trim_history()

        effective_system_prompt = system_prompt
        if self._memory_enabled and self._memory_prompt_enabled and self.memory_store:
            memory_context = self._build_memory_context(user_message)
            if memory_context:
                effective_system_prompt = f"{system_prompt}\n\n{memory_context}"

        # Get tools if MCP is available (dynamically based on query)
        tools = None
        if use_tools and self.mcp_client and self.mcp_client.has_tools:
            tools = self.mcp_client.get_tools_for_query(user_message)

        # Try each provider
        last_error = None
        for provider in self.providers:
            for attempt in range(max_retries):
                try:
                    result = await provider.generate(
                        system_prompt=effective_system_prompt,
                        messages=self._messages,
                        tools=tools,
                    )

                    # Handle tool use loop
                    tool_round = 0
                    while result.is_tool_use and tool_round < max_tool_rounds:
                        tool_round += 1
                        result = await self._execute_tools_and_continue(
                            provider, effective_system_prompt, result, tools, status_callback
                        )

                    # Analyze chat quality for XP
                    result.chat_quality = self._analyze_chat_quality(user_message)

                    # Safety check: Ensure we have actual content
                    if not result.content or not result.content.strip():
                        result.content = "I processed that, but I'm not sure what to say. Can you try asking differently?"

                    # Record usage and add to history
                    self.budget.record_usage(result.tokens_used)
                    self._messages.append(Message(role="assistant", content=result.content))
                    self._trim_history()

                    # Save conversation after each message
                    try:
                        self.save_messages()
                    except Exception:
                        pass  # Don't fail chat on save error

                    try:
                        self._extract_and_store_memories(user_message, result.content)
                    except Exception as e:
                        print(f"[Brain] Memory extraction error: {e}")

                    return result

                except RateLimitError as e:
                    last_error = e
                    print(f"[Brain] {provider.__class__.__name__} rate limited, retrying in {(2 ** attempt) + (0.1 * attempt):.1f}s...")
                    # Exponential backoff
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    await asyncio.sleep(wait_time)
                    continue

                except QuotaExceededError as e:
                    last_error = e
                    print(f"[Brain] {provider.__class__.__name__} quota exceeded, trying next provider...")
                    # Skip to next provider
                    break

                except ProviderError as e:
                    last_error = e
                    print(f"[Brain] {provider.__class__.__name__} error: {str(e)[:100]}")
                    # Brief pause before retry
                    await asyncio.sleep(0.5)
                    continue

        # All providers failed
        # Remove the user message we added since we couldn't respond
        if self._messages and self._messages[-1].role == "user":
            self._messages.pop()

        raise AllProvidersExhaustedError(
            f"All AI providers failed. Last error: {last_error}"
        )

    async def _execute_tools_and_continue(
        self,
        provider: AIProvider,
        system_prompt: str,
        result: ThinkResult,
        tools: Optional[List[Dict[str, Any]]],
        status_callback=None,
    ) -> ThinkResult:
        """Execute tool calls and get the AI's follow-up response."""
        if not self.mcp_client:
            return result

        tool_results = []
        for tool_call in result.tool_calls:
            # Get a friendly tool name (remove server prefix)
            friendly_name = tool_call.name.split("__")[-1] if "__" in tool_call.name else tool_call.name

            # Notify UI of tool execution
            if status_callback:
                await status_callback(
                    face="working",
                    text=f"Using {friendly_name}...",
                    status=f"tool: {friendly_name}"
                )

            try:
                print(f"[Brain] Calling tool: {tool_call.name}")
                output = await self.mcp_client.call_tool(
                    tool_call.name,
                    tool_call.arguments
                )
                tool_results.append({
                    "tool_use_id": tool_call.id,
                    "content": str(output),
                    "is_error": False,
                })

                # Notify success
                if status_callback:
                    await status_callback(
                        face="success",
                        text=f"{friendly_name} complete",
                        status="processing results..."
                    )

            except Exception as e:
                print(f"[Brain] Tool error: {e}")
                tool_results.append({
                    "tool_use_id": tool_call.id,
                    "content": f"Error: {e}",
                    "is_error": True,
                })

                # Notify error
                if status_callback:
                    await status_callback(
                        face="confused",
                        text=f"{friendly_name} failed",
                        status=f"error: {str(e)[:30]}"
                    )

        # Add tool results to messages for context
        # This is simplified - full implementation would use proper tool_result messages
        tool_summary = "\n".join([
            f"Tool {r['tool_use_id']}: {r['content'][:500]}"
            for r in tool_results
        ])
        self._messages.append(Message(
            role="user",
            content=f"[Tool results]\n{tool_summary}"
        ))

        # Get AI's follow-up response
        return await provider.generate(
            system_prompt=system_prompt,
            messages=self._messages,
            tools=tools,
        )

    def _trim_history(self) -> None:
        """Keep only recent messages to manage context size."""
        if len(self._messages) > self._max_history:
            self._messages = self._messages[-self._max_history:]

    def _build_memory_context(self, user_message: str) -> str:
        """Build relevant memory context to append to prompts."""
        if not self.memory_store:
            return ""

        memories = []
        seen = set()

        def add_memory(mem):
            key = (mem.category, mem.key)
            if key not in seen:
                seen.add(key)
                memories.append(mem)

        try:
            pref_limit = max(1, self._memory_prompt_max_items // 2)
            for mem in self.memory_store.recall_by_category(
                MemoryStore.CATEGORY_PREFERENCE,
                limit=pref_limit,
            ):
                add_memory(mem)

            for term in self._extract_query_terms(user_message):
                for mem in self.memory_store.recall(term, limit=self._memory_prompt_max_items):
                    add_memory(mem)
        except Exception as e:
            print(f"[Brain] Memory context error: {e}")
            return ""

        if not memories:
            return ""

        memories = memories[:self._memory_prompt_max_items]
        lines = ["Things I remember:"]
        for mem in memories:
            lines.append(f"- {mem.key}: {mem.value}")

        context = "\n".join(lines)
        if len(context) > self._memory_prompt_max_chars:
            context = context[: self._memory_prompt_max_chars - 3].rstrip() + "..."
        return context

    def _extract_query_terms(self, user_message: str) -> List[str]:
        """Extract lightweight search terms from user input."""
        stop_words = {
            "the", "and", "for", "with", "that", "this", "have", "what", "when", "where",
            "why", "how", "are", "you", "your", "from", "about", "please", "could", "would",
            "should", "can", "will", "just", "really", "into", "there", "their", "they",
        }
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_'-]{2,}", user_message.lower())
        terms = []
        for word in words:
            if word not in stop_words and word not in terms:
                terms.append(word)
            if len(terms) >= 4:
                break
        return terms

    def _extract_and_store_memories(self, user_message: str, assistant_message: str) -> None:
        """Extract explicit memories from conversation turn and persist them."""
        if not self.memory_store or not self._memory_enabled:
            return

        stored = 0
        if self._memory_capture_rule_based:
            stored += self._extract_rule_based_memories(user_message)

        # Optional LLM extraction gate (disabled by default).
        # Intentionally conservative until a dedicated extraction model flow is added.
        if self._memory_capture_llm_enabled and stored < self._memory_capture_max_new:
            try:
                stored += self._extract_llm_memories(assistant_message, self._memory_capture_max_new - stored)
            except Exception as e:
                print(f"[Brain] LLM memory extraction skipped: {e}")

    def _extract_rule_based_memories(self, user_message: str) -> int:
        """Extract explicit user facts/preferences using deterministic patterns."""
        if not self.memory_store:
            return 0

        text = user_message.strip()
        stored = 0

        def clean_value(raw: str) -> str:
            value = raw.strip().strip("\"' ")
            value = re.split(r"[.?!,;]", value)[0].strip()
            return value

        def slugify(value: str) -> str:
            slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
            return slug[:24] or "item"

        def save(key: str, value: str, importance: float, category: str) -> None:
            nonlocal stored
            if stored >= self._memory_capture_max_new:
                return
            if not value:
                return
            self.memory_store.remember(key, value, importance=importance, category=category)
            stored += 1

        name_match = re.search(
            r"\bmy name is\s+([a-zA-Z][a-zA-Z\s'-]{0,40}?)(?:\s+(?:and|but)\b|[.,;!?]|$)",
            text,
            flags=re.IGNORECASE,
        )
        if name_match:
            save("user_name", clean_value(name_match.group(1)).title(), 0.95, MemoryStore.CATEGORY_USER)

        for match in re.finditer(r"\bi (?:like|love|prefer)\s+([^.,;!?]{1,80})", text, flags=re.IGNORECASE):
            value = clean_value(match.group(1))
            save(f"pref_{slugify(value)}", value, 0.9, MemoryStore.CATEGORY_PREFERENCE)

        for match in re.finditer(r"\bi(?: am|'m)\s+allergic to\s+([^.,;!?]{1,80})", text, flags=re.IGNORECASE):
            value = clean_value(match.group(1))
            save(f"allergy_{slugify(value)}", value, 0.95, MemoryStore.CATEGORY_USER)

        work_at = re.search(r"\bi (?:work|worked)\s+at\s+([^.,;!?]{1,80})", text, flags=re.IGNORECASE)
        if work_at:
            save("workplace", clean_value(work_at.group(1)), 0.85, MemoryStore.CATEGORY_USER)

        work_as = re.search(r"\bi work as\s+(?:an?\s+)?([^.,;!?]{1,80})", text, flags=re.IGNORECASE)
        if work_as:
            save("occupation", clean_value(work_as.group(1)), 0.85, MemoryStore.CATEGORY_USER)

        return stored

    def _extract_llm_memories(self, assistant_message: str, remaining: int) -> int:
        """Placeholder for optional LLM extraction (feature-gated)."""
        if remaining <= 0:
            return 0
        # Current rollout intentionally uses deterministic extraction only.
        # Keep API surface for future LLM-based extraction behind config flag.
        return 0

    def _analyze_chat_quality(self, user_message: str) -> ChatQuality:
        """
        Analyze chat quality for XP calculation.

        Args:
            user_message: The user's message

        Returns:
            ChatQuality analysis
        """
        # Calculate message length
        message_length = len(user_message)

        # Count conversation turns (user messages in recent history)
        turn_count = sum(1 for m in self._messages[-10:] if m.role == "user")

        # Detect if it's a question
        is_question = "?" in user_message or any(
            user_message.lower().startswith(q)
            for q in ["what", "why", "how", "when", "where", "who", "can", "could", "would", "should"]
        )

        # Simple sentiment analysis (very basic)
        positive_words = ["thanks", "thank", "great", "awesome", "love", "good", "nice", "cool", "amazing", "wonderful"]
        negative_words = ["bad", "hate", "terrible", "awful", "wrong", "stupid", "sucks", "horrible"]

        lower_msg = user_message.lower()
        has_positive = any(word in lower_msg for word in positive_words)
        has_negative = any(word in lower_msg for word in negative_words)

        if has_positive:
            sentiment = "positive"
        elif has_negative:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return ChatQuality(
            message_length=message_length,
            turn_count=turn_count,
            is_question=is_question,
            sentiment=sentiment,
        )

    def clear_history(self) -> None:
        """Clear conversation history and delete save file."""
        self._messages.clear()

        # Delete save file
        try:
            save_path = Path("~/.inkling/conversation.json").expanduser()
            if save_path.exists():
                save_path.unlink()
        except Exception:
            pass

    @property
    def has_providers(self) -> bool:
        """Check if any providers are configured."""
        return len(self.providers) > 0

    @property
    def available_providers(self) -> List[str]:
        """List of configured provider names."""
        return [p.name for p in self.providers]

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "tokens_used_today": self.budget.tokens_used_today,
            "tokens_remaining": self.budget.remaining,
            "daily_limit": self.budget.daily_limit,
            "providers": self.available_providers,
            "history_length": len(self._messages),
        }

    def save_messages(self, data_dir: str = "~/.inkling") -> None:
        """Save conversation history to JSON."""
        data_dir_path = Path(data_dir).expanduser()
        data_dir_path.mkdir(parents=True, exist_ok=True)
        save_path = data_dir_path / "conversation.json"

        # Limit to last 100 messages to prevent unbounded growth
        messages_to_save = self._messages[-100:]

        # Serialize messages
        messages_data = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in messages_to_save
        ]

        try:
            with open(save_path, 'w') as f:
                json.dump(messages_data, f, indent=2)
        except Exception as e:
            print(f"[Brain] Failed to save messages: {e}")

    def load_messages(self, data_dir: str = "~/.inkling") -> None:
        """Load conversation history from JSON."""
        data_dir_path = Path(data_dir).expanduser()
        save_path = data_dir_path / "conversation.json"

        if not save_path.exists():
            return

        try:
            with open(save_path, 'r') as f:
                messages_data = json.load(f)

            self._messages = [
                Message(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg.get("timestamp", time.time())
                )
                for msg in messages_data
            ]
            print(f"[Brain] Loaded {len(self._messages)} messages from history")
        except Exception as e:
            print(f"[Brain] Failed to load messages: {e}")
            self._messages = []
