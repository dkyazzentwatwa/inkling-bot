"""
Project Inkling - AI Brain (Multi-Provider)

Handles AI responses using Anthropic (Claude) and OpenAI (GPT) with automatic fallback.
Implements retry logic, token budgeting, and rate limiting.
"""

import asyncio
import json
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
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"Anthropic rate limit: {e}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"Anthropic quota: {e}")
            raise ProviderError(f"Anthropic error: {e}")


class OpenAIProvider(AIProvider):
    """OpenAI (GPT) provider.

    Also supports OpenAI-compatible APIs (Ollama, Together, Groq, OpenRouter, etc.)
    by specifying a custom base_url.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
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
            # Check if model needs max_completion_tokens (o1, o3 models)
            use_max_completion_tokens = any(
                self.model.startswith(prefix)
                for prefix in ("o1", "o3")
            )

            kwargs = {
                "model": self.model,
                "messages": api_messages,
            }

            # Use appropriate token limit parameter
            if use_max_completion_tokens:
                kwargs["max_completion_tokens"] = self.max_tokens
            else:
                kwargs["max_tokens"] = self.max_tokens

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
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"OpenAI rate limit: {e}")
            if "quota" in error_str or "insufficient" in error_str:
                raise QuotaExceededError(f"OpenAI quota: {e}")
            raise ProviderError(f"OpenAI error: {e}")


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
            if "rate" in error_str or "429" in error_str or "quota" in error_str:
                raise RateLimitError(f"Gemini rate limit: {e}")
            if "resource" in error_str or "exhausted" in error_str:
                raise QuotaExceededError(f"Gemini quota: {e}")
            raise ProviderError(f"Gemini error: {e}")

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

    def __init__(self, config: Dict[str, Any], mcp_client=None):
        """
        Initialize the brain with configuration.

        Config should include:
        - anthropic: {api_key, model, max_tokens}
        - openai: {api_key, model, max_tokens}
        - gemini: {api_key, model, max_tokens}
        - primary: "anthropic", "openai", or "gemini"
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
        gemini_config = self.config.get("gemini", {})

        anthropic_key = anthropic_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        openai_key = openai_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        gemini_key = gemini_config.get("api_key") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

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

        if openai_key:
            self.providers.append(OpenAIProvider(
                api_key=openai_key,
                model=openai_config.get("model", "gpt-4o-mini"),
                max_tokens=openai_config.get("max_tokens", 150),
                base_url=openai_config.get("base_url"),
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

        # Get tools if MCP is available
        tools = None
        if use_tools and self.mcp_client and self.mcp_client.has_tools:
            tools = self.mcp_client.get_tools_for_ai()

        # Try each provider
        last_error = None
        for provider in self.providers:
            for attempt in range(max_retries):
                try:
                    result = await provider.generate(
                        system_prompt=system_prompt,
                        messages=self._messages,
                        tools=tools,
                    )

                    # Handle tool use loop
                    tool_round = 0
                    while result.is_tool_use and tool_round < max_tool_rounds:
                        tool_round += 1
                        result = await self._execute_tools_and_continue(
                            provider, system_prompt, result, tools, status_callback
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
