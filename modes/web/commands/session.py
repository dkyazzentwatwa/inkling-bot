"""Session management commands."""
from typing import Dict, Any

from . import CommandHandler


class SessionCommands(CommandHandler):
    """Handlers for session commands (/ask, /clear, /history)."""

    def ask(self, args: str) -> Dict[str, Any]:
        """Handle explicit chat command."""
        if not args:
            return {"response": "Usage: /ask <your message>\n\nOr just type without / to chat!", "error": True}

        return self.web_mode._handle_chat_sync(args)

    def clear(self) -> Dict[str, Any]:
        """Clear conversation history."""
        self.brain.clear_history()
        return {
            "response": "Conversation cleared.",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def history(self) -> Dict[str, Any]:
        """Show recent messages."""
        if not self.brain._messages:
            return {
                "response": "No conversation history.",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        response = "RECENT MESSAGES\n\n"
        for msg in self.brain._messages[-10:]:
            prefix = "You" if msg.role == "user" else self.personality.name
            content = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
            response += f"{prefix}: {content}\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }
