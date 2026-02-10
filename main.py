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
from dotenv import load_dotenv

from core.brain import Brain
from core.crypto import Identity
from core.display import DisplayManager
from core.mcp_client import MCPClientManager
from core.personality import Personality, PersonalityTraits
from core.heartbeat import Heartbeat, HeartbeatConfig
from core.focus import FocusManager
from core.memory import MemoryStore
from core.tasks import TaskManager
from core.battery import _client as pisugar_client # Import the singleton client for configuration
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
        "device": {"name": "Inkling", "timezone": "America/Los_Angeles"},
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
            "min_refresh_interval": 1.0,
            "pagination_loop_seconds": 5.0,
        },
        "personality": {
            "curiosity": 0.7,
            "cheerfulness": 0.6,
            "verbosity": 0.5,
        },
        "memory": {
            "enabled": True,
            "prompt_context": {
                "enabled": True,
                "max_items": 6,
                "max_chars": 600,
            },
            "capture": {
                "rule_based": True,
                "llm_enabled": False,
                "max_new_per_turn": 5,
            },
        },
        "focus": {
            "enabled": True,
            "default_work_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "sessions_until_long_break": 4,
            "quiet_mode_during_focus": True,
            "allow_pause": True,
            "auto_start_breaks": True,
            "timer_ui": {
                "takeover_enabled": True,
                "style": "digital_progress",
                "eink": {
                    "cadence_normal_sec": 30,
                    "cadence_final_min_sec": 10,
                },
            },
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
        self.mcp_client: Optional[MCPClientManager] = None
        self.heartbeat: Optional[Heartbeat] = None
        self.task_manager: Optional[TaskManager] = None
        self.memory_store: Optional[MemoryStore] = None
        self.focus_manager: Optional[FocusManager] = None
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

        # Personality (create first so display can reference it)
        print("  - Creating personality...")
        device_name = self.config.get("device", {}).get("name", "Inkling")
        self.personality = Personality.load()  # Load saved state

        # Battery (if enabled)
        battery_config = self.config.get("battery", {})
        if battery_config.get("enabled", False):
            pisugar_client.host = battery_config.get("host", "127.0.0.1")
            pisugar_client.port = battery_config.get("port", 8000)
            pisugar_client.enabled = True
            print(f"  - PiSugar battery monitoring enabled ({pisugar_client.host}:{pisugar_client.port})")
        else:
            # Disable client if not enabled in config
            pisugar_client.enabled = False
            print("  - PiSugar battery monitoring disabled")

        # Update name if changed in config
        if self.personality.name != device_name:
            self.personality.name = device_name

        # Update traits from config (user-editable via web UI)
        personality_config = self.config.get("personality", {})
        if "curiosity" in personality_config:
            self.personality.traits.curiosity = personality_config["curiosity"]
        if "cheerfulness" in personality_config:
            self.personality.traits.cheerfulness = personality_config["cheerfulness"]
        if "verbosity" in personality_config:
            self.personality.traits.verbosity = personality_config["verbosity"]
        if "playfulness" in personality_config:
            self.personality.traits.playfulness = personality_config["playfulness"]
        if "empathy" in personality_config:
            self.personality.traits.empathy = personality_config["empathy"]
        if "independence" in personality_config:
            self.personality.traits.independence = personality_config["independence"]

        # Display
        print("  - Initializing display...")
        display_config = self.config.get("display", {})
        dark_mode = display_config.get("dark_mode", False)
        sprite_config = display_config.get("sprites", {})
        self.display = DisplayManager(
            display_type=display_config.get("type", "mock"),
            width=display_config.get("width", 250),
            height=display_config.get("height", 122),
            min_refresh_interval=display_config.get("min_refresh_interval", 5.0),
            pagination_loop_seconds=display_config.get("pagination_loop_seconds", 5.0),
            device_name=device_name.lower()[:8],  # Truncate for header
            personality=self.personality,
            timezone=self.config.get("device", {}).get("timezone"),
            dark_mode=dark_mode,
            sprite_config=sprite_config,
        )
        self.display.init()

        # Configure screen saver if enabled
        screensaver_config = display_config.get("screensaver", {})
        if screensaver_config.get("enabled", False):
            self.display.configure_screensaver(
                enabled=True,
                idle_minutes=screensaver_config.get("idle_timeout_minutes", 5.0),
                page_duration=screensaver_config.get("page_duration_seconds", 10.0),
                pages=screensaver_config.get("pages", [
                    {"type": "stats"},
                    {"type": "quote"},
                    {"type": "faces"},
                    {"type": "progression"},
                ])
            )
            print(f"    Screen saver enabled (idle: {screensaver_config.get('idle_timeout_minutes', 5)}m)")
        if dark_mode:
            print("    Dark mode enabled")

        # Register mood change callback to update display
        self.personality.on_mood_change(self._on_mood_change)
        self.personality.on_level_up(self._on_level_up)

        # Task Manager
        print("  - Initializing task manager...")
        try:
            self.task_manager = TaskManager()
        except Exception as e:
            print(f"    Task manager failed to initialize: {e}")
            self.task_manager = None

        # Memory Store
        print("  - Initializing memory store...")
        try:
            self.memory_store = MemoryStore()
            self.memory_store.initialize()
            print("    Memory store ready")
        except Exception as e:
            print(f"    Memory store failed to initialize: {e}")
            self.memory_store = None

        # Focus Manager
        print("  - Initializing focus manager...")
        try:
            self.focus_manager = FocusManager(config=self.config.get("focus", {}))
            self.focus_manager.initialize()
            self.display.set_focus_manager(self.focus_manager)
            print("    Focus manager ready")
        except Exception as e:
            print(f"    Focus manager failed to initialize: {e}")
            self.focus_manager = None

        # Scheduler (cron-style task scheduling)
        scheduler_config_data = self.config.get("scheduler", {})
        scheduler_enabled = scheduler_config_data.get("enabled", True)

        if scheduler_enabled:
            print("  - Starting scheduler...")
            try:
                from core.scheduler import (
                    ScheduledTaskManager,
                    action_daily_summary,
                    action_weekly_cleanup,
                    action_nightly_backup,
                    action_system_health_check,
                    action_task_reminders,
                    action_morning_briefing,
                    action_rss_digest
                )

                self.scheduler = ScheduledTaskManager()

                # Register actions BEFORE loading config
                self.scheduler.register_action("daily_summary", lambda: action_daily_summary(self))
                self.scheduler.register_action("weekly_cleanup", lambda: action_weekly_cleanup(self))
                self.scheduler.register_action("nightly_backup", lambda: action_nightly_backup(self))
                self.scheduler.register_action("system_health_check", lambda: action_system_health_check(self))
                self.scheduler.register_action("task_reminders", lambda: action_task_reminders(self))
                self.scheduler.register_action("morning_briefing", lambda: action_morning_briefing(self))
                self.scheduler.register_action("rss_digest", lambda: action_rss_digest(self))

                # Now load config (actions are already registered)
                self.scheduler.load_from_config(scheduler_config_data)
                print(f"    Scheduled tasks: {len(self.scheduler.tasks)}")
                print(f"    Registered actions: {len(self.scheduler.action_handlers)}")
            except Exception as e:
                print(f"    Scheduler failed to initialize: {e}")
                self.scheduler = None
        else:
            self.scheduler = None
            print("  - Scheduler disabled")

        # MCP Client (tool integration) — before Brain so tools are available
        mcp_config = self.config.get("mcp", {})
        if mcp_config.get("enabled", False):
            print("  - Starting MCP servers...")
            try:
                self.mcp_client = MCPClientManager(mcp_config)
                await self.mcp_client.start_all()
                if self.mcp_client.has_tools:
                    print(f"    Tools available: {self.mcp_client.tool_count}")
                else:
                    print("    No tools loaded (check server configs)")
            except Exception as e:
                print(f"    MCP startup failed: {e}")
                self.mcp_client = None

        # Brain (AI) — before Heartbeat so autonomous behaviors have access
        print("  - Connecting brain...")
        ai_config = self.config.get("ai", {})
        memory_config = self.config.get("memory", {})
        self.brain = Brain(
            ai_config,
            mcp_client=self.mcp_client,
            memory_store=self.memory_store,
            memory_config=memory_config,
        )

        if self.brain.has_providers:
            print(f"    Providers: {', '.join(self.brain.available_providers)}")
        else:
            print("    Warning: No AI providers configured!")
            print("    Set ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, or OLLAMA_API_KEY environment variables.")

        # Heartbeat (proactive behaviors) — after Brain so it's available
        heartbeat_config_data = self.config.get("heartbeat", {})
        heartbeat_enabled = heartbeat_config_data.get("enabled", True)

        if heartbeat_enabled:
            print("  - Starting heartbeat...")
            heartbeat_config = HeartbeatConfig(
                tick_interval_seconds=heartbeat_config_data.get("tick_interval", 60),
                enable_mood_behaviors=heartbeat_config_data.get("enable_mood_behaviors", True),
                enable_time_behaviors=heartbeat_config_data.get("enable_time_behaviors", True),
                enable_social_behaviors=heartbeat_config_data.get("enable_social_behaviors", True),
                enable_maintenance=heartbeat_config_data.get("enable_maintenance", True),
                enable_thoughts=heartbeat_config_data.get("enable_thoughts", True),
                thought_interval_min_minutes=heartbeat_config_data.get("thought_interval_min_minutes", 15),
                thought_interval_max_minutes=heartbeat_config_data.get("thought_interval_max_minutes", 30),
                thought_surface_probability=heartbeat_config_data.get(
                    "thought_surface_probability", 0.35
                ),
                quiet_hours_start=heartbeat_config_data.get("quiet_hours_start", 23),
                quiet_hours_end=heartbeat_config_data.get("quiet_hours_end", 7),
                enable_battery_behaviors=heartbeat_config_data.get("enable_battery_behaviors", True),
                battery_low_threshold=heartbeat_config_data.get("battery_low_threshold", 20),
                battery_critical_threshold=heartbeat_config_data.get("battery_critical_threshold", 10),
                battery_full_threshold=heartbeat_config_data.get("battery_full_threshold", 95),
            )

            self.heartbeat = Heartbeat(
                personality=self.personality,
                display_manager=self.display,
                api_client=None,
                brain=self.brain,
                task_manager=self.task_manager,
                scheduler=self.scheduler,
                memory_store=self.memory_store,
                focus_manager=self.focus_manager,
                config=heartbeat_config,
            )

            # Register callback for spontaneous messages
            self.heartbeat.on_message(self._on_heartbeat_message)

            print(f"    Behaviors: {len(self.heartbeat._behaviors)}")
            print(f"    Tick interval: {heartbeat_config.tick_interval_seconds}s")
        else:
            print("  - Heartbeat disabled")

        print("Initialization complete!")

    def _on_mood_change(self, old_mood, new_mood) -> None:
        """Handle mood changes."""
        print(f"[Mood] {old_mood.value} -> {new_mood.value}")

    def _on_level_up(self, old_level: int, new_level: int) -> None:
        """Handle level up events."""
        from core.progression import LevelCalculator
        level_name = LevelCalculator.level_name(new_level)
        print(f"[Level Up!] {old_level} -> {new_level} ({level_name})")

    async def _on_heartbeat_message(self, message: str, face: str) -> None:
        """Handle spontaneous messages from heartbeat."""
        print(f"[Heartbeat] {message}")

        # Update display with spontaneous thought
        if self.display:
            await self.display.update(
                face=face,
                text=message,
                mood_text=self.personality.mood.current.value.title(),
            )

    async def run_mode(self, mode: str) -> None:
        """Run a specific interaction mode."""
        self._running = True

        # Start heartbeat in background if enabled
        heartbeat_task = None
        if self.heartbeat:
            heartbeat_task = asyncio.create_task(self.heartbeat.start())

        try:
            if mode == "ssh":
                self._mode = SSHChatMode(
                    brain=self.brain,
                    display=self.display,
                    personality=self.personality,
                    task_manager=self.task_manager,
                    scheduler=self.scheduler,
                    memory_store=self.memory_store,
                    focus_manager=self.focus_manager,
                    config=self.config,
                )
                await self._mode.run()

            elif mode == "web":
                port = self.config.get("web", {}).get("port", 8081)

                # Show QR code on first boot for easy mobile connection
                first_boot_marker = os.path.join(
                    os.path.expanduser("~"), ".inkling", ".first_boot_done"
                )
                if not os.path.exists(first_boot_marker):
                    try:
                        import socket
                        hostname = socket.gethostname()
                        try:
                            ip = socket.gethostbyname(hostname)
                        except socket.gaierror:
                            ip = "localhost"
                        url = f"http://{ip}:{port}"
                        await self.display.show_qr_code(url, f"Connect: {url}")
                        await asyncio.sleep(8)  # Show QR for 8 seconds
                        # Mark first boot done
                        os.makedirs(os.path.dirname(first_boot_marker), exist_ok=True)
                        with open(first_boot_marker, "w") as f:
                            f.write("done")
                    except Exception as e:
                        print(f"[Main] QR code display skipped: {e}")

                self._mode = WebChatMode(
                    brain=self.brain,
                    display=self.display,
                    personality=self.personality,
                    task_manager=self.task_manager,
                    scheduler=self.scheduler,
                    memory_store=self.memory_store,
                    focus_manager=self.focus_manager,
                    identity=self.identity,
                    config=self.config,
                    port=port,
                )
                await self._mode.run()

            elif mode == "demo":
                await self._run_demo()

            else:
                print(f"Unknown mode: {mode}")
                print("Available modes: ssh, demo")

        finally:
            # Stop heartbeat when mode exits
            if self.heartbeat:
                self.heartbeat.stop()
                if heartbeat_task:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass

    async def _run_demo(self) -> None:
        """Run a demo of the Pwnagotchi-style display."""
        print("Running display demo...")

        # Demo data showing different states
        demo_states = [
            {
                "face": "happy",
                "text": "Hello! I'm your new companion.",
                "mood": "Happy",
                "chat_count": 0,
            },
            {
                "face": "curious",
                "text": "I wonder what we'll discover today?",
                "mood": "Curious",
                "chat_count": 5,
            },
            {
                "face": "excited",
                "text": "Wow, that's amazing!",
                "mood": "Excited",
                "chat_count": 12,
                "dream_count": 3,
            },
            {
                "face": "thinking",
                "text": "Let me think about that...",
                "mood": "Thinking",
                "chat_count": 42,
                "telegram_count": 2,
            },
            {
                "face": "cool",
                "text": "Everything is under control.",
                "mood": "Cool",
                "chat_count": 100,
                "friend_nearby": True,
            },
            {
                "face": "sleepy",
                "text": "Time for a rest...",
                "mood": "Sleepy",
                "chat_count": 142,
            },
        ]

        for state in demo_states:
            # Update social stats for demo
            self.display.set_social_stats(
                chat_count=state.get("chat_count", 0),
                dream_count=state.get("dream_count", 0),
                telegram_count=state.get("telegram_count", 0),
                friend_nearby=state.get("friend_nearby", False),
            )

            await self.display.update(
                face=state["face"],
                text=state["text"],
                mood_text=state["mood"],
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

        # Save personality state
        if self.personality:
            try:
                self.personality.save()
                print("[Personality] State saved")
            except Exception as e:
                print(f"[Personality] Failed to save state: {e}")

        # Save conversation history
        if self.brain:
            try:
                self.brain.save_messages()
                print("[Brain] Conversation saved")
            except Exception as e:
                print(f"[Brain] Failed to save conversation: {e}")

        if self.display:
            self.display.sleep()

        if self.memory_store:
            try:
                self.memory_store.close()
            except Exception as e:
                print(f"[Memory] Failed to close memory store: {e}")

        if self.focus_manager:
            try:
                self.focus_manager.close()
            except Exception as e:
                print(f"[Focus] Failed to close focus manager: {e}")

        # Force garbage collection
        gc.collect()

        print("Goodbye!")


async def main():
    """Main entry point."""
    # Load environment variables from .env file
    load_dotenv()

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
