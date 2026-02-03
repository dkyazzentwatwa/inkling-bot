"""
Project Inkling - Shared Command Registry

Central definition of all commands available in both SSH and web modes.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Command:
    """Definition of a command available in chat modes."""
    name: str
    description: str
    handler: str  # Method name to call (e.g., "cmd_help")
    category: str  # "info", "social", "system", "personality", "display", "session"
    requires_brain: bool = False
    requires_api: bool = False


# All available commands
COMMANDS: List[Command] = [
    # Info commands
    Command("help", "Show available commands", "cmd_help", "info"),
    Command("level", "Show XP and progression", "cmd_level", "info"),
    Command("prestige", "Reset level with XP bonus", "cmd_prestige", "info"),
    Command("stats", "Show token usage statistics", "cmd_stats", "info", requires_brain=True),
    Command("history", "Show recent messages", "cmd_history", "info", requires_brain=True),

    # Personality commands
    Command("mood", "Show current mood", "cmd_mood", "personality"),
    Command("energy", "Show energy level", "cmd_energy", "personality"),
    Command("traits", "Show personality traits", "cmd_traits", "personality"),

    # System commands
    Command("system", "Show system stats", "cmd_system", "system"),
    Command("config", "Show AI configuration", "cmd_config", "system", requires_brain=True),
    Command("identity", "Show device public key", "cmd_identity", "system", requires_api=True),

    # Display commands
    Command("face", "Test a face expression", "cmd_face", "display"),
    Command("faces", "List all available faces", "cmd_faces", "display"),
    Command("refresh", "Force display refresh", "cmd_refresh", "display"),

    # Social commands
    Command("dream", "Post a dream to the Night Pool", "cmd_dream", "social", requires_api=True),
    Command("fish", "Fetch random dream from pool", "cmd_fish", "social", requires_api=True),
    Command("telegrams", "Check telegram inbox", "cmd_telegrams", "social", requires_api=True),
    Command("telegram", "Send encrypted telegram", "cmd_telegram", "social", requires_api=True),
    Command("queue", "Show offline queue status", "cmd_queue", "social", requires_api=True),

    # Session commands (SSH only)
    Command("ask", "Explicit chat command", "cmd_ask", "session", requires_brain=True),
    Command("clear", "Clear conversation history", "cmd_clear", "session", requires_brain=True),
]


def get_commands_by_category() -> dict:
    """Group commands by category for display."""
    categories = {}
    for cmd in COMMANDS:
        if cmd.category not in categories:
            categories[cmd.category] = []
        categories[cmd.category].append(cmd)
    return categories


def get_command(name: str) -> Command | None:
    """Get a command by name (without leading /)."""
    name = name.lstrip("/").lower()
    for cmd in COMMANDS:
        if cmd.name == name:
            return cmd
    return None
