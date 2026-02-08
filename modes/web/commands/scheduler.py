"""Scheduler management commands."""
from typing import Dict, Any

from . import CommandHandler


class SchedulerCommands(CommandHandler):
    """Handlers for scheduler commands (/schedule)."""

    def schedule(self, args: str = "") -> Dict[str, Any]:
        """Manage scheduled tasks."""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return {
                "response": "Scheduler not available.\n\nEnable in config.yml under 'scheduler.enabled: true'",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "error": True
            }

        if not args:
            # List all scheduled tasks
            tasks = self.scheduler.list_tasks()

            if not tasks:
                return {
                    "response": "No scheduled tasks configured.\n\nAdd tasks in config.yml under 'scheduler.tasks'",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }

            response = "SCHEDULED TASKS\n\n"
            next_runs = self.scheduler.get_next_run_times()

            for task in tasks:
                status_icon = "✓" if task.enabled else "✗"
                response += f"{status_icon} {task.name}\n"
                response += f"   Schedule: {task.schedule_expr}\n"
                response += f"   Action:   {task.action}\n"

                if task.enabled:
                    next_run = next_runs.get(task.name, "Unknown")
                    response += f"   Next run: {next_run}\n"

                if task.last_run > 0:
                    import time
                    from datetime import datetime
                    last_run_dt = datetime.fromtimestamp(task.last_run)
                    response += f"   Last run: {last_run_dt.strftime('%Y-%m-%d %H:%M:%S')} ({task.run_count} times)\n"

                if task.last_error:
                    response += f"   Error: {task.last_error}\n"

                response += "\n"

            return {
                "response": response,
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        # Parse subcommands
        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()

        if subcmd == "list":
            # Redirect to list (same as no args)
            return self.schedule()

        elif subcmd == "enable":
            if len(parts) < 2:
                return {
                    "response": "Usage: /schedule enable <task_name>",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

            task_name = parts[1]
            if self.scheduler.enable_task(task_name):
                return {
                    "response": f"✓ Enabled: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }
            else:
                return {
                    "response": f"Task not found: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

        elif subcmd == "disable":
            if len(parts) < 2:
                return {
                    "response": "Usage: /schedule disable <task_name>",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

            task_name = parts[1]
            if self.scheduler.disable_task(task_name):
                return {
                    "response": f"✓ Disabled: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }
            else:
                return {
                    "response": f"Task not found: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

        else:
            return {
                "response": f"Unknown subcommand: {subcmd}\n\nAvailable commands:\n  /schedule           - List all scheduled tasks\n  /schedule list      - List all scheduled tasks\n  /schedule enable <name>  - Enable a task\n  /schedule disable <name> - Disable a task",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "error": True
            }
