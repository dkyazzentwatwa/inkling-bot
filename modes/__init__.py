"""
Project Inkling - Interaction Modes

Different ways to interact with your Inkling:
- ssh_chat: Terminal-based chat via SSH
- web_chat: Local web UI (Phase 2)
"""

from .ssh_chat import SSHChatMode

__all__ = ['SSHChatMode']
