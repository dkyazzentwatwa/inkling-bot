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
    Command("bash", "Run a shell command", "cmd_bash", "system"),

    # Display commands
    Command("face", "Test a face expression", "cmd_face", "display"),
    Command("faces", "List all available faces", "cmd_faces", "display"),
    Command("refresh", "Force display refresh", "cmd_refresh", "display"),
    Command("screensaver", "Toggle screen saver on/off", "cmd_screensaver", "display"),
    Command("darkmode", "Toggle dark mode (inverted display)", "cmd_darkmode", "display"),

    # Crypto commands
    Command("price", "Check price of a cryptocurrency", "cmd_price", "crypto"),
    Command("watch", "List watched cryptocurrencies", "cmd_watch", "crypto"),
    Command("chart", "Show TA indicators for a coin", "cmd_chart", "crypto"),
    Command("portfolio", "Show portfolio value and holdings", "cmd_portfolio", "crypto"),
    Command("add", "Add coin to watchlist", "cmd_add", "crypto"),
    Command("remove", "Remove coin from watchlist", "cmd_remove", "crypto"),
    Command("alert", "Set price alert", "cmd_alert", "crypto"),
    Command("alerts", "List active price alerts", "cmd_alerts", "crypto"),
    Command("top", "Show top gainers/losers", "cmd_top", "crypto"),

    # Scheduler commands
    Command("schedule", "Manage scheduled price checks", "cmd_schedule", "scheduler"),

    # New utility commands
    Command("thoughts", "Show recent autonomous thoughts", "cmd_thoughts", "info"),
    Command("memory", "Show memory stats and entries", "cmd_memory", "info"),
    Command("settings", "Show current settings (SSH)", "cmd_settings", "system"),
    Command("backup", "Create backup of crypto data", "cmd_backup", "system"),

    # WiFi commands
    Command("wifi", "Show WiFi status and saved networks", "cmd_wifi", "system"),
    Command("btcfg", "Start BLE WiFi configuration (15 min)", "cmd_btcfg", "system"),
    Command("wifiscan", "Scan for nearby WiFi networks", "cmd_wifiscan", "system"),

    # Play commands
    Command("walk", "Go for a walk (boosts energy +3 XP)", "cmd_walk", "play"),
    Command("dance", "Dance around (boosts energy +5 XP)", "cmd_dance", "play"),
    Command("exercise", "Exercise and stretch (boosts energy +5 XP)", "cmd_exercise", "play"),
    Command("play", "Play with a toy (boosts energy +4 XP)", "cmd_play", "play"),
    Command("pet", "Get petted (boosts mood +3 XP)", "cmd_pet", "play"),
    Command("rest", "Take a short rest (calms down +2 XP)", "cmd_rest", "play"),
    Command("focus", "Manage focus/pomodoro sessions", "cmd_focus", "session"),

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
