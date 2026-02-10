"""Tests for core/focus.py."""

import time


def test_focus_start_singleton_and_stop(temp_data_dir):
    from core.focus import FocusManager

    fm = FocusManager(config={"enabled": True}, data_dir=temp_data_dir)
    fm.initialize()
    try:
        start = fm.start(25)
        assert start["ok"] is True
        assert fm.is_active is True

        second = fm.start(10)
        assert second["ok"] is False

        stopped = fm.stop()
        assert stopped["ok"] is True
        assert fm.is_active is False
    finally:
        fm.close()


def test_focus_pause_resume_math(temp_data_dir):
    from core.focus import FocusManager

    fm = FocusManager(config={"enabled": True}, data_dir=temp_data_dir)
    fm.initialize()
    try:
        fm.start(5)
        time.sleep(1)
        before_pause = fm.status()["remaining_sec"]
        fm.pause()
        time.sleep(1)
        paused = fm.status()["remaining_sec"]
        fm.resume()
        time.sleep(1)
        after_resume = fm.status()["remaining_sec"]

        # Timer should not run while paused, then continue after resume
        assert paused >= before_pause - 1
        assert after_resume <= paused - 1
    finally:
        fm.close()


def test_focus_auto_break_cadence(temp_data_dir):
    from core.focus import FocusManager

    fm = FocusManager(
        config={
            "enabled": True,
            "default_work_minutes": 25,
            "short_break_minutes": 1,
            "long_break_minutes": 2,
            "sessions_until_long_break": 2,
            "auto_start_breaks": True,
        },
        data_dir=temp_data_dir,
    )
    fm.initialize()
    try:
        # First completion -> short break
        fm.start(5)
        fm._active["started_at"] -= 5 * 60  # force completion
        s1 = fm.status()
        assert s1["phase"] == fm.PHASE_SHORT_BREAK

        # Finish break
        fm._active["started_at"] -= 60
        fm.status()

        # Second completion -> long break
        fm.start(5)
        fm._active["started_at"] -= 5 * 60
        s2 = fm.status()
        assert s2["phase"] == fm.PHASE_LONG_BREAK
    finally:
        fm.close()


def test_focus_stats_today_and_week(temp_data_dir):
    from core.focus import FocusManager

    fm = FocusManager(config={"enabled": True}, data_dir=temp_data_dir)
    fm.initialize()
    try:
        fm.start(5)
        fm._active["started_at"] -= 120
        fm.stop(stopped_early=False)

        today = fm.stats_today()
        week = fm.stats_week()

        assert today["sessions"] >= 1
        assert today["total_sec"] >= 1
        assert week["total_sessions"] >= 1
        assert len(week["days"]) == 7
    finally:
        fm.close()
