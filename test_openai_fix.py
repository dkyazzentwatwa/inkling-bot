#!/usr/bin/env python3
"""Test OpenAI API with max_completion_tokens parameter."""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.brain import OpenAIProvider, Message


async def test_openai():
    """Test a simple OpenAI API call."""
    # Enable debug mode
    os.environ["INKLING_DEBUG"] = "1"

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False

    print("Testing OpenAI API with max_completion_tokens...")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")

    # Create provider with default model (gpt-5-mini)
    provider = OpenAIProvider(
        api_key=api_key,
        model="gpt-5-mini",
        max_tokens=50
    )

    print(f"Model: {provider.model}")
    print(f"Max tokens: {provider.max_tokens}")

    # Simple test message
    messages = [Message(role="user", content="Say 'hello' in one word.")]

    try:
        result = await provider.generate(
            system_prompt="You are a helpful assistant.",
            messages=messages
        )

        print("\n✓ Success!")
        print(f"Response: {result.content}")
        print(f"Tokens used: {result.tokens_used}")
        print(f"Model: {result.model}")
        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_openai())
    sys.exit(0 if success else 1)
