"""Tests for focus command registration."""

from core.commands import get_command


def test_focus_command_registered():
    cmd = get_command("focus")
    assert cmd is not None
    assert cmd.handler == "cmd_focus"
