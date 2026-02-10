"""Integration tests for focus wiring across modes/components."""

import asyncio

from core.focus import FocusManager
from core.ui import DisplayContext, PwnagotchiUI
from core.heartbeat import Heartbeat, HeartbeatConfig, ProactiveBehavior, BehaviorType


class _FocusStub:
    def __init__(self, quiet=True):
        self._quiet = quiet

    def is_quiet_mode_active(self):
        return self._quiet

    def get_display_snapshot(self):
        return {
            "focus_active": True,
            "focus_phase": "FOCUS",
            "focus_remaining_sec": 1200,
            "focus_progress": 0.2,
            "focus_task_label": "Task A",
            "focus_cadence_sec": 30,
            "takeover_enabled": True,
        }


def test_focus_manager_enabled_and_status(temp_data_dir):
    fm = FocusManager(config={"enabled": True}, data_dir=temp_data_dir)
    fm.initialize()
    try:
        fm.start(25)
        status = fm.status()
        assert status["active"] is True
        assert "phase_label" in status
    finally:
        fm.close()


def test_ui_focus_takeover_renders():
    ui = PwnagotchiUI()
    ctx = DisplayContext(
        message="ignored",
        focus_active=True,
        focus_phase="FOCUS",
        focus_remaining_sec=1500,
        focus_progress=0.3,
        focus_task_label="API docs",
    )
    image = ui.render(ctx)
    assert image is not None
    assert image.size == (250, 122)


def test_heartbeat_suppresses_noncritical_messages_during_focus(personality):
    hb = Heartbeat(personality, config=HeartbeatConfig(tick_interval_seconds=1), focus_manager=_FocusStub(quiet=True))
    seen = []

    async def on_message(msg, face):
        seen.append((msg, face))

    hb.on_message(on_message)

    async def noisy():
        return "noise"

    hb.register_behavior(
        ProactiveBehavior(
            name="noisy",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=noisy,
            probability=1.0,
            cooldown_seconds=0,
        )
    )
    # Ensure it is considered mood-valid.
    hb._should_run_mood_behavior = lambda _b: True

    asyncio.run(hb._run_behaviors())
    assert seen == []
