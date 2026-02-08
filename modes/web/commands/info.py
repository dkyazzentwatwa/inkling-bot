"""Info and status commands."""
from typing import Dict, Any

from core.commands import get_commands_by_category
from . import CommandHandler


class InfoCommands(CommandHandler):
    """Handlers for info commands (/help, /mood, /traits, /level, /prestige, /stats)."""

    def help(self) -> Dict[str, Any]:
        """Show all available commands."""
        categories = get_commands_by_category()

        response_lines = ["INKLING COMMANDS\n"]

        category_titles = {
            "info": "Status & Info",
            "personality": "Personality",
            "tasks": "Task Management",
            "scheduler": "Scheduler",
            "system": "System",
            "display": "Display",
            "session": "Session",
        }

        for cat_key in ["info", "personality", "tasks", "scheduler", "system", "display", "session"]:
            if cat_key in categories:
                response_lines.append(f"\n{category_titles.get(cat_key, cat_key.title())}:")
                for cmd in categories[cat_key]:
                    usage = f"/{cmd.name}"
                    if cmd.name in ("face", "ask", "task", "done", "cancel", "delete", "schedule", "bash"):
                        usage += " <arg>"
                    response_lines.append(f"  {usage} - {cmd.description}")

        response_lines.append("\n\nJust type (no /) to chat with AI")

        return {
            "response": "\n".join(response_lines),
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def mood(self) -> Dict[str, Any]:
        """Show current mood."""
        mood = self.personality.mood
        return {
            "response": f"Mood: {mood.current.value}\nIntensity: {mood.intensity:.0%}\nEnergy: {self.personality.energy:.0%}",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def traits(self) -> Dict[str, Any]:
        """Show personality traits."""
        traits = self.personality.traits

        def bar(value: float) -> str:
            filled = int(value * 10)
            return "█" * filled + "░" * (10 - filled)

        response = "PERSONALITY TRAITS\n\n"
        response += f"Curiosity:    [{bar(traits.curiosity)}] {traits.curiosity:.0%}\n"
        response += f"Cheerfulness: [{bar(traits.cheerfulness)}] {traits.cheerfulness:.0%}\n"
        response += f"Verbosity:    [{bar(traits.verbosity)}] {traits.verbosity:.0%}\n"
        response += f"Playfulness:  [{bar(traits.playfulness)}] {traits.playfulness:.0%}\n"
        response += f"Empathy:      [{bar(traits.empathy)}] {traits.empathy:.0%}\n"
        response += f"Independence: [{bar(traits.independence)}] {traits.independence:.0%}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def level(self) -> Dict[str, Any]:
        """Show level and progression."""
        from core.progression import LevelCalculator

        prog = self.personality.progression
        level_name = LevelCalculator.level_name(prog.level)
        level_display = prog.get_display_level()

        xp_progress = LevelCalculator.progress_to_next_level(prog.xp)
        xp_to_next = LevelCalculator.xp_to_next_level(prog.xp)
        bar_filled = int(xp_progress * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        response = f"PROGRESSION\n\n{level_display} - {level_name}\n\n"
        response += f"[{bar}] {xp_progress:.0%}\n"
        response += f"Total XP: {prog.xp}  •  Next level: {xp_to_next} XP\n"

        if prog.current_streak > 0:
            streak_emoji = "🔥" if prog.current_streak >= 7 else "✨"
            response += f"\n{streak_emoji} {prog.current_streak} day streak\n"

        if prog.can_prestige():
            response += f"\n🌟 You can prestige! (max level reached)"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def prestige(self) -> Dict[str, Any]:
        """Handle prestige (not supported in web mode)."""
        return {
            "response": "Prestige requires confirmation. Please use SSH mode:\n  python main.py --mode ssh\n  /prestige",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def stats(self) -> Dict[str, Any]:
        """Show token stats."""
        stats = self.brain.get_stats()
        return {
            "response": f"Tokens used: {stats['tokens_used_today']}\nRemaining: {stats['tokens_remaining']}\nProviders: {', '.join(stats['providers'])}",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }
