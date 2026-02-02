"""
Project Inkling - Core Modules

An AI companion device for Raspberry Pi Zero 2W with e-ink display.
"""

from .crypto import Identity
from .display import DisplayManager
from .personality import Personality, Mood
from .brain import Brain

__all__ = ['Identity', 'DisplayManager', 'Personality', 'Mood', 'Brain']
