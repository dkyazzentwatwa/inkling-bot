"""
Project Inkling - AI Brain (Multi-Provider)

Handles AI responses using Anthropic (Claude) and OpenAI (GPT) with automatic fallback.
Implements retry logic, token budgeting, and rate limiting.
"""

import asyncio
import time
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


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
    """Track token usage and enforce budgets."""
    daily_limit: int = 10000
    per_request_max: int = 500

    # Usage tracking
    tokens_used_today: int = 0
    last_reset: float = field(default_factory=time.time)

    def check_budget(self, estimated_tokens: int) -> bool:
        """Check if we have budget for this request."""
        self._maybe_reset()
        return (self.tokens_used_today + estimated_tokens) <= self.daily_limit

    def record_usage(self, tokens: int) -> None:
        """Record token usage."""
        self._maybe_reset()
        self.tokens_used_today += tokens

    def _maybe_reset(self) -> None:
        """Reset daily counter if new day."""
        now = time.time()
        # Reset if more than 24 hours since last reset
        if now - self.last_reset > 86400:
            self.tokens_used_today = 0
            self.last_reset = now

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


@dataclass
class ThinkResult:
    """Result from AI thinking."""
    content: str
    tokens_used: int
    provider: str
    model: str


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
    ) -> ThinkResult:
        """Generate a response."""
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
    ) -> ThinkResult:
        """Generate using Claude."""
        client = self._get_client()

        # Convert messages to Anthropic format
        api_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=api_messages,
            )

            content = response.content[0].text if response.content else ""
            tokens = response.usage.input_tokens + response.usage.output_tokens

            return ThinkResult(
                content=content,
                tokens_used=tokens,
                provider=self.name,
                model=self.model,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"Anthropic rate limit: {e}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"Anthropic quota: {e}")
            raise ProviderError(f"Anthropic error: {e}")


class OpenAIProvider(AIProvider):
    """OpenAI (GPT) provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 150
    ):
        super().__init__(api_key, model, max_tokens)
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        system_prompt: str,
        messages: List[Message],
    ) -> ThinkResult:
        """Generate using GPT."""
        client = self._get_client()

        # Convert messages to OpenAI format (with system message)
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend([
            {"role": m.role, "content": m.content}
            for m in messages
        ])

        try:
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=api_messages,
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            return ThinkResult(
                content=content,
                tokens_used=tokens,
                provider=self.name,
                model=self.model,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"OpenAI rate limit: {e}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"OpenAI quota: {e}")
            raise ProviderError(f"OpenAI error: {e}")


class Brain:
    """
    Multi-provider AI brain for Inkling.

    Features:
    - Automatic fallback between providers
    - Retry logic with exponential backoff
    - Token budget tracking
    - Conversation history management
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the brain with configuration.

        Config should include:
        - anthropic: {api_key, model, max_tokens}
        - openai: {api_key, model, max_tokens}
        - primary: "anthropic" or "openai"
        - budget: {daily_tokens, per_request_max}
        """
        self.config = config
        self.providers: List[AIProvider] = []
        self.budget = TokenBudget(
            daily_limit=config.get("budget", {}).get("daily_tokens", 10000),
            per_request_max=config.get("budget", {}).get("per_request_max", 500),
        )

        # Conversation history
        self._messages: List[Message] = []
        self._max_history = 10  # Keep last N messages

        # Initialize providers
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize AI providers based on config."""
        primary = self.config.get("primary", "anthropic")

        # Get API keys from config or environment
        anthropic_config = self.config.get("anthropic", {})
        openai_config = self.config.get("openai", {})

        anthropic_key = anthropic_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        openai_key = openai_config.get("api_key") or os.environ.get("OPENAI_API_KEY")

        # Build provider list with primary first
        if primary == "anthropic" and anthropic_key:
            self.providers.append(AnthropicProvider(
                api_key=anthropic_key,
                model=anthropic_config.get("model", "claude-3-haiku-20240307"),
                max_tokens=anthropic_config.get("max_tokens", 150),
            ))

        if openai_key:
            self.providers.append(OpenAIProvider(
                api_key=openai_key,
                model=openai_config.get("model", "gpt-4o-mini"),
                max_tokens=openai_config.get("max_tokens", 150),
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
    ) -> ThinkResult:
        """
        Process user message and generate AI response.

        Args:
            user_message: The user's input
            system_prompt: System prompt with personality context
            max_retries: Maximum retry attempts per provider

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

        # Try each provider
        last_error = None
        for provider in self.providers:
            for attempt in range(max_retries):
                try:
                    result = await provider.generate(
                        system_prompt=system_prompt,
                        messages=self._messages,
                    )

                    # Record usage and add to history
                    self.budget.record_usage(result.tokens_used)
                    self._messages.append(Message(role="assistant", content=result.content))
                    self._trim_history()

                    return result

                except RateLimitError as e:
                    last_error = e
                    # Exponential backoff
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    await asyncio.sleep(wait_time)
                    continue

                except QuotaExceededError:
                    # Skip to next provider
                    break

                except ProviderError as e:
                    last_error = e
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

    def _trim_history(self) -> None:
        """Keep only recent messages to manage context size."""
        if len(self._messages) > self._max_history:
            self._messages = self._messages[-self._max_history:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._messages.clear()

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
