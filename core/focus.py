"""
Project Inkling - Focus/Pomodoro manager.

Local-first focus session management with persistent history and stats.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List


@dataclass
class FocusConfig:
    enabled: bool = True
    default_work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_until_long_break: int = 4
    quiet_mode_during_focus: bool = True
    allow_pause: bool = True
    auto_start_breaks: bool = True
    timer_takeover_enabled: bool = True
    timer_style: str = "digital_progress"
    eink_cadence_normal_sec: int = 30
    eink_cadence_final_min_sec: int = 10

    @classmethod
    def from_dict(cls, cfg: Optional[Dict[str, Any]]) -> "FocusConfig":
        cfg = cfg or {}
        timer_ui = cfg.get("timer_ui", {})
        eink = timer_ui.get("eink", {})
        return cls(
            enabled=cfg.get("enabled", True),
            default_work_minutes=int(cfg.get("default_work_minutes", 25)),
            short_break_minutes=int(cfg.get("short_break_minutes", 5)),
            long_break_minutes=int(cfg.get("long_break_minutes", 15)),
            sessions_until_long_break=int(cfg.get("sessions_until_long_break", 4)),
            quiet_mode_during_focus=cfg.get("quiet_mode_during_focus", True),
            allow_pause=cfg.get("allow_pause", True),
            auto_start_breaks=cfg.get("auto_start_breaks", True),
            timer_takeover_enabled=timer_ui.get("takeover_enabled", True),
            timer_style=timer_ui.get("style", "digital_progress"),
            eink_cadence_normal_sec=int(eink.get("cadence_normal_sec", 30)),
            eink_cadence_final_min_sec=int(eink.get("cadence_final_min_sec", 10)),
        )


@dataclass
class FocusSession:
    id: int
    phase: str
    started_at: float
    ended_at: Optional[float]
    duration_planned_sec: int
    duration_actual_sec: int
    completed: bool
    stopped_early: bool
    task_id: Optional[str]
    task_title_snapshot: Optional[str]


class FocusManager:
    """Manage focus sessions, transitions, persistence, and stats."""

    PHASE_WORK = "work"
    PHASE_SHORT_BREAK = "short_break"
    PHASE_LONG_BREAK = "long_break"

    def __init__(self, config: Optional[Dict[str, Any]] = None, data_dir: str = "~/.inkling"):
        self.config = FocusConfig.from_dict(config)
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "focus.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

        self._active: Optional[Dict[str, Any]] = None
        self._work_sessions_since_long_break = 0
        self._last_transition_message: Optional[str] = None

    def initialize(self) -> None:
        with self._lock:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=5.0)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
            self._recover_open_sessions()
            self._load_cycle_counter()

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at REAL NOT NULL,
                ended_at REAL,
                duration_planned_sec INTEGER NOT NULL,
                duration_actual_sec INTEGER DEFAULT 0,
                phase TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                stopped_early INTEGER DEFAULT 0,
                task_id TEXT,
                task_title_snapshot TEXT,
                created_date TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                event_type TEXT NOT NULL,
                ts REAL NOT NULL,
                meta_json TEXT DEFAULT "{}"
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_date ON focus_sessions(created_date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_started ON focus_sessions(started_at)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_task_id ON focus_sessions(task_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_events_session_ts ON focus_events(session_id, ts)")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.commit()

    def _recover_open_sessions(self) -> None:
        """Mark any previously open sessions as stopped early on restart."""
        now = time.time()
        rows = self._conn.execute(
            "SELECT id, started_at, duration_planned_sec FROM focus_sessions WHERE ended_at IS NULL"
        ).fetchall()
        for row in rows:
            actual = max(0, int(now - row["started_at"]))
            self._conn.execute(
                """
                UPDATE focus_sessions
                SET ended_at = ?, duration_actual_sec = ?, completed = 0, stopped_early = 1
                WHERE id = ?
                """,
                (now, actual, row["id"]),
            )
            self._log_event(row["id"], "recovered_stop", now, "{}")
        self._conn.commit()

    def _load_cycle_counter(self) -> None:
        row = self._conn.execute(
            "SELECT value FROM focus_state WHERE key = 'work_sessions_since_long_break'"
        ).fetchone()
        if row:
            try:
                self._work_sessions_since_long_break = int(row["value"])
            except Exception:
                self._work_sessions_since_long_break = 0

    def _save_cycle_counter(self) -> None:
        self._conn.execute(
            """
            INSERT INTO focus_state(key, value) VALUES('work_sessions_since_long_break', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(self._work_sessions_since_long_break),),
        )
        self._conn.commit()

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled and self._conn is not None

    @property
    def is_active(self) -> bool:
        self._refresh_transitions()
        return self._active is not None

    def is_quiet_mode_active(self) -> bool:
        return bool(self.is_active and self.config.quiet_mode_during_focus and self._active["phase"] == self.PHASE_WORK)

    def start(
        self,
        minutes: Optional[int] = None,
        task_id: Optional[str] = None,
        task_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if not self.is_enabled:
                return {"ok": False, "error": "Focus mode is disabled."}
            if self._active is not None:
                return {"ok": False, "error": "A focus session is already active.", "status": self.status()}

            work_minutes = int(minutes or self.config.default_work_minutes)
            work_minutes = max(5, min(180, work_minutes))
            return self._start_phase(
                phase=self.PHASE_WORK,
                minutes=work_minutes,
                task_id=task_id,
                task_title=task_title,
            )

    def start_break(self, minutes: Optional[int] = None, long_break: bool = False) -> Dict[str, Any]:
        with self._lock:
            if not self.is_enabled:
                return {"ok": False, "error": "Focus mode is disabled."}
            if self._active is not None:
                return {"ok": False, "error": "Cannot start break while a session is active.", "status": self.status()}
            phase = self.PHASE_LONG_BREAK if long_break else self.PHASE_SHORT_BREAK
            default_minutes = self.config.long_break_minutes if long_break else self.config.short_break_minutes
            break_minutes = int(minutes or default_minutes)
            break_minutes = max(1, min(60, break_minutes))
            return self._start_phase(phase=phase, minutes=break_minutes, task_id=None, task_title=None)

    def _start_phase(
        self,
        phase: str,
        minutes: int,
        task_id: Optional[str],
        task_title: Optional[str],
    ) -> Dict[str, Any]:
        now = time.time()
        created_date = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        planned_sec = int(minutes * 60)
        cursor = self._conn.execute(
            """
            INSERT INTO focus_sessions(
                started_at, ended_at, duration_planned_sec, duration_actual_sec,
                phase, completed, stopped_early, task_id, task_title_snapshot, created_date
            ) VALUES(?, NULL, ?, 0, ?, 0, 0, ?, ?, ?)
            """,
            (now, planned_sec, phase, task_id, task_title, created_date),
        )
        session_id = cursor.lastrowid
        self._log_event(session_id, "start", now, "{}")
        self._conn.commit()

        self._active = {
            "id": session_id,
            "phase": phase,
            "started_at": now,
            "duration_planned_sec": planned_sec,
            "paused_total_sec": 0,
            "pause_started_at": None,
            "task_id": task_id,
            "task_title": task_title,
        }
        self._last_transition_message = None
        return {"ok": True, "status": self.status()}

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            if not self._active:
                return {"ok": False, "error": "No active focus session."}
            if not self.config.allow_pause:
                return {"ok": False, "error": "Pause is disabled in config."}
            if self._active["pause_started_at"] is not None:
                return {"ok": False, "error": "Session is already paused."}
            now = time.time()
            self._active["pause_started_at"] = now
            self._log_event(self._active["id"], "pause", now, "{}")
            self._conn.commit()
            return {"ok": True, "status": self.status()}

    def resume(self) -> Dict[str, Any]:
        with self._lock:
            if not self._active:
                return {"ok": False, "error": "No active focus session."}
            pause_started = self._active.get("pause_started_at")
            if pause_started is None:
                return {"ok": False, "error": "Session is not paused."}
            now = time.time()
            self._active["paused_total_sec"] += max(0, int(now - pause_started))
            self._active["pause_started_at"] = None
            self._log_event(self._active["id"], "resume", now, "{}")
            self._conn.commit()
            return {"ok": True, "status": self.status()}

    def stop(self, stopped_early: bool = True) -> Dict[str, Any]:
        with self._lock:
            if not self._active:
                return {"ok": False, "error": "No active focus session."}
            return self._finish_active(completed=not stopped_early, stopped_early=stopped_early, reason="stop")

    def status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_transitions()
            if not self._active:
                return {"active": False}

            now = time.time()
            remaining = self._remaining_seconds(now)
            total = self._active["duration_planned_sec"]
            progress = 1.0 - (remaining / max(1, total))
            phase = self._active["phase"]
            return {
                "active": True,
                "session_id": self._active["id"],
                "phase": phase,
                "phase_label": self._phase_label(phase, self._active.get("pause_started_at") is not None),
                "paused": self._active.get("pause_started_at") is not None,
                "remaining_sec": max(0, remaining),
                "planned_sec": total,
                "progress": max(0.0, min(1.0, progress)),
                "task_id": self._active.get("task_id"),
                "task_title": self._active.get("task_title"),
                "ends_at": now + max(0, remaining),
                "quiet_mode_active": self.is_quiet_mode_active(),
                "takeover_enabled": self.config.timer_takeover_enabled,
                "timer_style": self.config.timer_style,
            }

    def pop_transition_message(self) -> Optional[str]:
        with self._lock:
            msg = self._last_transition_message
            self._last_transition_message = None
            return msg

    def _refresh_transitions(self) -> None:
        if not self._active:
            return
        if self._active.get("pause_started_at") is not None:
            return
        if self._remaining_seconds(time.time()) > 0:
            return

        phase = self._active["phase"]
        if phase == self.PHASE_WORK:
            self._finish_active(completed=True, stopped_early=False, reason="complete")
            if self.config.auto_start_breaks:
                self._work_sessions_since_long_break += 1
                if self._work_sessions_since_long_break >= self.config.sessions_until_long_break:
                    self._work_sessions_since_long_break = 0
                    self._save_cycle_counter()
                    result = self._start_phase(self.PHASE_LONG_BREAK, self.config.long_break_minutes, None, None)
                    if result.get("ok"):
                        self._last_transition_message = (
                            f"Focus complete. Starting long break ({self.config.long_break_minutes}m)."
                        )
                else:
                    self._save_cycle_counter()
                    result = self._start_phase(self.PHASE_SHORT_BREAK, self.config.short_break_minutes, None, None)
                    if result.get("ok"):
                        self._last_transition_message = (
                            f"Focus complete. Starting short break ({self.config.short_break_minutes}m)."
                        )
        else:
            self._finish_active(completed=True, stopped_early=False, reason="break_complete")
            self._last_transition_message = "Break complete. Ready for the next focus session."

    def _finish_active(self, completed: bool, stopped_early: bool, reason: str) -> Dict[str, Any]:
        now = time.time()
        if not self._active:
            return {"ok": False, "error": "No active focus session."}

        actual = self._elapsed_seconds(now)
        session_id = self._active["id"]
        self._conn.execute(
            """
            UPDATE focus_sessions
            SET ended_at = ?, duration_actual_sec = ?, completed = ?, stopped_early = ?
            WHERE id = ?
            """,
            (now, actual, 1 if completed else 0, 1 if stopped_early else 0, session_id),
        )
        self._log_event(session_id, reason, now, "{}")
        self._conn.commit()
        self._active = None
        return {"ok": True, "completed": completed, "stopped_early": stopped_early}

    def _elapsed_seconds(self, now: float) -> int:
        if not self._active:
            return 0
        elapsed = int(now - self._active["started_at"])
        elapsed -= int(self._active.get("paused_total_sec", 0))
        pause_started = self._active.get("pause_started_at")
        if pause_started is not None:
            elapsed -= int(now - pause_started)
        return max(0, elapsed)

    def _remaining_seconds(self, now: float) -> int:
        if not self._active:
            return 0
        return max(0, self._active["duration_planned_sec"] - self._elapsed_seconds(now))

    def _phase_label(self, phase: str, paused: bool) -> str:
        if paused:
            return "PAUSED"
        if phase == self.PHASE_WORK:
            return "FOCUS"
        if phase == self.PHASE_SHORT_BREAK:
            return "SHORT BREAK"
        if phase == self.PHASE_LONG_BREAK:
            return "LONG BREAK"
        return phase.upper()

    def get_display_snapshot(self) -> Dict[str, Any]:
        state = self.status()
        if not state.get("active"):
            return {"focus_active": False}

        remaining = int(state["remaining_sec"])
        if remaining <= 60:
            cadence = max(5, self.config.eink_cadence_final_min_sec)
        else:
            cadence = max(10, self.config.eink_cadence_normal_sec)

        return {
            "focus_active": True,
            "focus_phase": state["phase_label"],
            "focus_remaining_sec": remaining,
            "focus_progress": float(state["progress"]),
            "focus_task_label": state.get("task_title"),
            "focus_cadence_sec": cadence,
            "quiet_mode_active": state.get("quiet_mode_active", False),
            "timer_style": self.config.timer_style,
            "takeover_enabled": self.config.timer_takeover_enabled,
            "paused": state.get("paused", False),
        }

    def stats_today(self) -> Dict[str, Any]:
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) AS sessions,
                    SUM(duration_actual_sec) AS total_sec,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed_count,
                    SUM(CASE WHEN phase = 'work' THEN duration_actual_sec ELSE 0 END) AS work_sec
                FROM focus_sessions
                WHERE created_date = ?
                """,
                (today,),
            ).fetchone()
            return {
                "date": today,
                "sessions": int(row["sessions"] or 0),
                "total_sec": int(row["total_sec"] or 0),
                "completed_count": int(row["completed_count"] or 0),
                "work_sec": int(row["work_sec"] or 0),
            }

    def stats_week(self) -> Dict[str, Any]:
        with self._lock:
            today = datetime.now().date()
            start = today - timedelta(days=6)
            rows = self._conn.execute(
                """
                SELECT created_date, COUNT(*) AS sessions, SUM(duration_actual_sec) AS total_sec
                FROM focus_sessions
                WHERE created_date >= ? AND created_date <= ?
                GROUP BY created_date
                ORDER BY created_date ASC
                """,
                (start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")),
            ).fetchall()
            by_day = {row["created_date"]: {"sessions": int(row["sessions"] or 0), "total_sec": int(row["total_sec"] or 0)} for row in rows}
            days: List[Dict[str, Any]] = []
            total_sessions = 0
            total_sec = 0
            for i in range(7):
                day = start + timedelta(days=i)
                key = day.strftime("%Y-%m-%d")
                entry = by_day.get(key, {"sessions": 0, "total_sec": 0})
                total_sessions += entry["sessions"]
                total_sec += entry["total_sec"]
                days.append({"date": key, **entry})
            return {"days": days, "total_sessions": total_sessions, "total_sec": total_sec}

    def _log_event(self, session_id: Optional[int], event_type: str, ts: float, meta_json: str) -> None:
        self._conn.execute(
            "INSERT INTO focus_events(session_id, event_type, ts, meta_json) VALUES(?, ?, ?, ?)",
            (session_id, event_type, ts, meta_json),
        )

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
