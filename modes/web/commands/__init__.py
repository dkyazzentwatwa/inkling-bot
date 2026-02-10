"""Web command handlers."""
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from modes.web_chat import WebChatMode


class CommandHandler:
    """Base class for command handlers.

    Provides access to WebChatMode components without circular imports.
    """

    def __init__(self, web_mode: 'WebChatMode'):
        self.web_mode = web_mode
        # Shortcuts to commonly used attributes
        self.personality = web_mode.personality
        self.display = web_mode.display
        self.brain = web_mode.brain
        self.task_manager = web_mode.task_manager
        self.memory_store = web_mode.memory_store
        self.focus_manager = web_mode.focus_manager
        self.scheduler = web_mode.scheduler
        self._config = web_mode._config

    @property
    def _loop(self):
        """Get event loop dynamically (it's set after __init__)."""
        return self.web_mode._loop

    def _get_face_str(self) -> str:
        """Get current face emoji."""
        return self.web_mode._get_face_str()
