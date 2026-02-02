"""
Project Inkling - Interaction Modes

Different ways to interact with your Inkling:
- ssh_chat: Terminal-based chat via SSH
- web_chat: Local web UI (Phase 2)
"""

from .ssh_chat import SSHChatMode
from .web_chat import WebChatMode

__all__ = ['SSHChatMode', 'WebChatMode']
