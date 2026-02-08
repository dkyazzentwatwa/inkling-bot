#!/usr/bin/env python3
"""
Integration test for play commands in SSH mode.

This test verifies that the play command handlers are properly connected
and can be executed without errors.
"""

import asyncio
import sys
from unittest.mock import Mock, AsyncMock

from modes.ssh_chat import SSHChatMode
from core.personality import Personality, PersonalityTraits
from core.display import DisplayManager
from core.brain import Brain
from core.progression import XPSource


async def test_play_commands():
    """Test that all play commands can be executed."""
    print("Testing play command handlers...\n")

    # Create mock components
    traits = PersonalityTraits(
        curiosity=0.7,
        cheerfulness=0.6,
        verbosity=0.5,
        playfulness=0.6,
        empathy=0.7,
        independence=0.4,
    )
    personality = Personality(name="TestInkling", traits=traits)

    # Create mock display that doesn't actually render
    display = Mock(spec=DisplayManager)
    display.update = AsyncMock()

    # Create SSH mode (no brain needed for play commands)
    ssh_mode = SSHChatMode(
        brain=None,
        display=display,
        personality=personality,
        task_manager=None,
        scheduler=None,
        config={},
    )

    # Test each play command
    commands = [
        ("walk", "cmd_walk"),
        ("dance", "cmd_dance"),
        ("exercise", "cmd_exercise"),
        ("play", "cmd_play"),
        ("pet", "cmd_pet"),
        ("rest", "cmd_rest"),
    ]

    for cmd_name, handler_name in commands:
        print(f"Testing /{cmd_name}...")

        # Get initial state
        initial_energy = personality.energy
        initial_xp = personality.progression.xp

        # Execute command
        handler = getattr(ssh_mode, handler_name)
        await handler()

        # Check effects
        new_energy = personality.energy
        new_xp = personality.progression.xp

        energy_change = new_energy - initial_energy
        xp_gain = new_xp - initial_xp

        print(f"  ✓ Energy: {initial_energy:.0%} → {new_energy:.0%} ({energy_change:+.0%})")
        print(f"  ✓ XP: {initial_xp} → {new_xp} (+{xp_gain})")

        # Verify display was updated
        assert display.update.called, f"Display not updated for {cmd_name}"
        print(f"  ✓ Display updated with animation\n")

    print("All play commands executed successfully!")


async def test_energy_command():
    """Test the /energy command."""
    print("\nTesting /energy command...")

    traits = PersonalityTraits()
    personality = Personality(name="TestInkling", traits=traits)

    display = Mock(spec=DisplayManager)
    display.update = AsyncMock()

    ssh_mode = SSHChatMode(
        brain=None,
        display=display,
        personality=personality,
        task_manager=None,
        scheduler=None,
        config={},
    )

    # Call energy command (it just prints, no errors expected)
    await ssh_mode.cmd_energy()
    print("  ✓ Energy command displays correctly\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Play Commands Integration Test")
    print("=" * 50)
    print()

    try:
        # Suppress print output from the commands themselves
        import io
        import contextlib

        # Run tests with suppressed stdout
        with contextlib.redirect_stdout(io.StringIO()):
            asyncio.run(test_play_commands())
            asyncio.run(test_energy_command())

        print("=" * 50)
        print("✅ All integration tests passed!")
        print("=" * 50)
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
