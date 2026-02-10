"""Focus session commands."""
from typing import Dict, Any

from . import CommandHandler


class FocusCommands(CommandHandler):
    """Handlers for /focus command family."""

    def focus(self, args: str = "") -> Dict[str, Any]:
        if not self.focus_manager or not self.focus_manager.is_enabled:
            return {"response": "Focus manager is not available.", "error": True}

        parts = args.split() if args else []
        sub = parts[0].lower() if parts else "status"

        if sub == "start":
            minutes = None
            task_ref = None
            if len(parts) >= 2:
                try:
                    minutes = int(parts[1])
                except ValueError:
                    task_ref = " ".join(parts[1:])
            if len(parts) >= 3:
                task_ref = " ".join(parts[2:])

            task = self._resolve_task_ref(task_ref) if task_ref else None
            result = self.focus_manager.start(
                minutes=minutes,
                task_id=task.id if task else None,
                task_title=task.title if task else None,
            )
            if not result.get("ok"):
                return {"response": result.get("error", "Could not start focus session"), "error": True}
            status = result["status"]
            return {
                "response": self._format_status(status),
                "status": "focus-active",
                "focus": self.focus_manager.get_display_snapshot(),
                "face": "intense",
            }

        if sub == "stop":
            result = self.focus_manager.stop(stopped_early=True)
            if not result.get("ok"):
                return {"response": result.get("error", "No active session"), "error": True}
            return {"response": "Focus session stopped.", "status": "focus-idle", "focus": {"focus_active": False}}

        if sub == "pause":
            result = self.focus_manager.pause()
            if not result.get("ok"):
                return {"response": result.get("error", "Unable to pause"), "error": True}
            return {"response": self._format_status(result["status"]), "status": "focus-paused", "focus": self.focus_manager.get_display_snapshot()}

        if sub == "resume":
            result = self.focus_manager.resume()
            if not result.get("ok"):
                return {"response": result.get("error", "Unable to resume"), "error": True}
            return {"response": self._format_status(result["status"]), "status": "focus-active", "focus": self.focus_manager.get_display_snapshot()}

        if sub == "break":
            result = self.focus_manager.start_break()
            if not result.get("ok"):
                return {"response": result.get("error", "Unable to start break"), "error": True}
            return {"response": self._format_status(result["status"]), "status": "focus-break", "focus": self.focus_manager.get_display_snapshot()}

        if sub == "stats":
            stats = self.focus_manager.stats_today()
            return {
                "response": (
                    f"Focus Today\n\n"
                    f"Sessions: {stats['sessions']}\n"
                    f"Completed: {stats['completed_count']}\n"
                    f"Total time: {stats['total_sec'] // 60}m\n"
                    f"Work time: {stats['work_sec'] // 60}m"
                ),
                "status": "focus-stats",
            }

        if sub == "week":
            week = self.focus_manager.stats_week()
            lines = ["Focus This Week", ""]
            for day in week["days"]:
                lines.append(f"{day['date']}: {day['sessions']} sessions ({day['total_sec'] // 60}m)")
            lines.append("")
            lines.append(f"Total: {week['total_sessions']} sessions ({week['total_sec'] // 60}m)")
            return {"response": "\n".join(lines), "status": "focus-stats"}

        if sub == "config":
            cfg = self.focus_manager.config
            return {
                "response": (
                    "Focus Config\n\n"
                    f"Work: {cfg.default_work_minutes}m\n"
                    f"Short break: {cfg.short_break_minutes}m\n"
                    f"Long break: {cfg.long_break_minutes}m\n"
                    f"Long break cadence: every {cfg.sessions_until_long_break}\n"
                    f"Quiet mode: {'on' if cfg.quiet_mode_during_focus else 'off'}"
                ),
                "status": "focus-config",
            }

        status = self.focus_manager.status()
        if not status.get("active"):
            return {"response": "No active focus session.", "status": "focus-idle", "focus": {"focus_active": False}}
        return {"response": self._format_status(status), "status": "focus-active", "focus": self.focus_manager.get_display_snapshot()}

    def _format_status(self, status: Dict[str, Any]) -> str:
        if not status.get("active"):
            return "No active focus session."
        remaining = int(status.get("remaining_sec", 0))
        mm = remaining // 60
        ss = remaining % 60
        label = status.get("phase_label", "FOCUS")
        paused = " [PAUSED]" if status.get("paused") else ""
        task = status.get("task_title")
        task_line = f"\nTask: {task}" if task else ""
        return f"{label}{paused}: {mm:02d}:{ss:02d}{task_line}"

    def _resolve_task_ref(self, task_ref: str):
        if not task_ref or not self.task_manager:
            return None
        task = self.task_manager.get_task(task_ref)
        if task:
            return task
        ref = task_ref.lower()
        matches = [
            t for t in self.task_manager.list_tasks()
            if t.id.startswith(task_ref) or ref in t.title.lower()
        ]
        return matches[0] if len(matches) == 1 else None
