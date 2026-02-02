#!/usr/bin/env python3
"""
Project Inkling - Main Entry Point

An AI companion device for Raspberry Pi Zero 2W with e-ink display.

Usage:
    python main.py --mode ssh      # Interactive terminal chat
    python main.py --mode web      # Web UI (Phase 2)
    python main.py --help          # Show help

Environment variables:
    ANTHROPIC_API_KEY   - Anthropic API key
    OPENAI_API_KEY      - OpenAI API key (fallback)
"""

import argparse
import asyncio
import gc
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import yaml

from core.brain import Brain
from core.crypto import Identity
from core.display import DisplayManager
from core.mcp_client import MCPClientManager
from core.personality import Personality, PersonalityTraits
from core.api_client import APIClient
from modes.ssh_chat import SSHChatMode
from modes.web_chat import WebChatMode


# Memory management for Pi Zero 2W (512MB RAM)
def configure_memory():
    """Configure Python for low-memory environment."""
    # Aggressive garbage collection
    gc.set_threshold(100, 5, 5)

    # Disable debug features
    if not os.environ.get("INKLING_DEBUG"):
        sys.tracebacklimit = 3


def load_config(config_path: str = "config.yml") -> dict:
    """
    Load configuration from YAML file.

    Supports environment variable substitution for ${VAR} patterns.
    Falls back to config.local.yml if it exists.
    """
    # Check for local override
    local_path = Path(config_path).with_suffix(".local.yml")
    if local_path.exists():
        config_path = str(local_path)

    config_file = Path(config_path)
    if not config_file.exists():
        print(f"Warning: Config file not found: {config_path}")
        return get_default_config()

    with open(config_file) as f:
        content = f.read()

    # Substitute environment variables
    import re
    def replace_env(match):
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    content = re.sub(r'\$\{(\w+)\}', replace_env, content)

    return yaml.safe_load(content)


def get_default_config() -> dict:
    """Return default configuration."""
    return {
        "device": {"name": "Inkling"},
        "ai": {
            "primary": "anthropic",
            "anthropic": {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 150,
            },
            "openai": {
                "model": "gpt-4o-mini",
                "max_tokens": 150,
            },
            "budget": {
                "daily_tokens": 10000,
                "per_request_max": 500,
            },
        },
        "display": {
            "type": "mock",
            "width": 250,
            "height": 122,
            "min_refresh_interval": 5.0,
        },
        "personality": {
            "curiosity": 0.7,
            "cheerfulness": 0.6,
            "verbosity": 0.5,
        },
    }


class Inkling:
    """
    Main Inkling application controller.

    Manages all subsystems and coordinates the event loop.
    """

    def __init__(self, config: dict):
        self.config = config
        self._running = False

        # Core components (initialized in setup)
        self.identity: Optional[Identity] = None
        self.display: Optional[DisplayManager] = None
        self.personality: Optional[Personality] = None
        self.brain: Optional[Brain] = None
        self.api_client: Optional[APIClient] = None
        self.mcp_client: Optional[MCPClientManager] = None

        # Current mode
        self._mode = None

    async def setup(self) -> None:
        """Initialize all components."""
        print("Initializing Inkling...")

        # Identity/DNA
        print("  - Loading identity...")
        self.identity = Identity()
        self.identity.initialize()
        print(f"    Public key: {self.identity.public_key_hex[:16]}...")
        print(f"    Hardware hash: {self.identity.hardware_hash[:16]}...")

        # Display
        print("  - Initializing display...")
        display_config = self.config.get("display", {})
        self.display = DisplayManager(
            display_type=display_config.get("type", "mock"),
            width=display_config.get("width", 250),
            height=display_config.get("height", 122),
            min_refresh_interval=display_config.get("min_refresh_interval", 5.0),
        )
        self.display.init()

        # Personality
        print("  - Creating personality...")
        personality_config = self.config.get("personality", {})
        traits = PersonalityTraits(
            curiosity=personality_config.get("curiosity", 0.7),
            cheerfulness=personality_config.get("cheerfulness", 0.6),
            verbosity=personality_config.get("verbosity", 0.5),
        )
        device_name = self.config.get("device", {}).get("name", "Inkling")
        self.personality = Personality(name=device_name, traits=traits)

        # Register mood change callback to update display
        self.personality.on_mood_change(self._on_mood_change)

        # MCP Client (tool integration)
        mcp_config = self.config.get("mcp", {})
        if mcp_config.get("enabled", False):
            print("  - Starting MCP servers...")
            self.mcp_client = MCPClientManager(mcp_config)
            await self.mcp_client.start_all()
            if self.mcp_client.has_tools:
                print(f"    Tools available: {self.mcp_client.tool_count}")
            else:
                print("    No tools loaded (check server configs)")

        # Brain (AI)
        print("  - Connecting brain...")
        ai_config = self.config.get("ai", {})
        self.brain = Brain(ai_config, mcp_client=self.mcp_client)

        if self.brain.has_providers:
            print(f"    Providers: {', '.join(self.brain.available_providers)}")
        else:
            print("    Warning: No AI providers configured!")
            print("    Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables.")

        # API Client (for social features)
        network_config = self.config.get("network", {})
        api_base = network_config.get("api_base", "")
        if api_base and api_base != "https://your-project.vercel.app/api":
            print("  - Connecting to Conservatory...")
            self.api_client = APIClient(
                identity=self.identity,
                api_base=api_base,
            )
            print(f"    API: {api_base}")
        else:
            print("  - Social features disabled (no api_base configured)")

        print("Initialization complete!")

    def _on_mood_change(self, old_mood, new_mood) -> None:
        """Handle mood changes."""
        print(f"[Mood] {old_mood.value} -> {new_mood.value}")

    async def run_mode(self, mode: str) -> None:
        """Run a specific interaction mode."""
        self._running = True

        if mode == "ssh":
            self._mode = SSHChatMode(
                brain=self.brain,
                display=self.display,
                personality=self.personality,
                api_client=self.api_client,
            )
            await self._mode.run()

        elif mode == "web":
            self._mode = WebChatMode(
                brain=self.brain,
                display=self.display,
                personality=self.personality,
                api_client=self.api_client,
                port=self.config.get("web", {}).get("port", 8080),
            )
            await self._mode.run()

        elif mode == "demo":
            await self._run_demo()

        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: ssh, demo")

    async def _run_demo(self) -> None:
        """Run a quick demo of the display."""
        print("Running display demo...")

        faces = ["happy", "excited", "curious", "sad", "sleepy", "cool"]
        for face in faces:
            await self.display.update(
                face=face,
                text=f"This is the {face} face!",
                status=self.personality.get_status_line(),
                force=True,
            )
            await asyncio.sleep(2)

        print("Demo complete!")

    async def shutdown(self) -> None:
        """Clean shutdown."""
        print("\nShutting down...")

        if self._mode:
            self._mode.stop()

        if self.mcp_client:
            await self.mcp_client.stop_all()

        if self.api_client:
            await self.api_client.close()

        if self.display:
            self.display.sleep()

        # Force garbage collection
        gc.collect()

        print("Goodbye!")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Project Inkling - AI Companion Device",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode ssh      # Terminal chat mode
  python main.py --mode demo     # Display demo
  python main.py --config my.yml # Custom config file
        """,
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["ssh", "web", "demo"],
        default="ssh",
        help="Interaction mode (default: ssh)",
    )

    parser.add_argument(
        "--config", "-c",
        default="config.yml",
        help="Path to configuration file",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    args = parser.parse_args()

    # Debug mode
    if args.debug:
        os.environ["INKLING_DEBUG"] = "1"
    else:
        configure_memory()

    # Load configuration
    config = load_config(args.config)

    # Create and run Inkling
    inkling = Inkling(config)

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        asyncio.create_task(inkling.shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await inkling.setup()
        await inkling.run_mode(args.mode)
    except KeyboardInterrupt:
        pass
    finally:
        await inkling.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
