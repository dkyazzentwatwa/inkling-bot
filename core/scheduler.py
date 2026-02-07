"""
Scheduler - Cron-style task scheduling for Inkling

Provides time-based scheduling similar to cron but with a simpler API.
Uses the `schedule` library for scheduling and integrates with Heartbeat.

Example schedules:
- Daily at specific time: "every().day.at('14:30')"
- Hourly: "every().hour"
- Weekly: "every().monday.at('09:00')"
- Every N minutes: "every(5).minutes"

Actions are defined as async functions that get called when scheduled.
"""

import asyncio
import logging
import os
import re
from typing import Callable, List, Dict, Any, Optional, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
import time

try:
    import schedule
except ImportError:
    print("ERROR: schedule library not installed. Install with: pip install schedule")
    raise

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A task scheduled to run at specific times."""
    name: str
    schedule_expr: str  # Human-readable schedule (e.g., "every day at 14:30")
    action: str  # Action name (maps to handler)
    enabled: bool = True
    last_run: float = 0.0
    run_count: int = 0
    last_error: Optional[str] = None
    job: Any = None  # schedule.Job object


class ScheduledTaskManager:
    """Manages cron-style scheduled tasks."""

    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.action_handlers: Dict[str, Callable[[], Coroutine]] = {}
        self.enabled = True
        self._config_path: Optional[str] = None
        logger.info("[Scheduler] Initialized")

    def register_action(self, name: str, handler: Callable[[], Coroutine]):
        """Register an action handler that can be scheduled.

        Args:
            name: Action name (used in config)
            handler: Async function to call when scheduled
        """
        self.action_handlers[name] = handler
        logger.debug(f"[Scheduler] Registered action: {name}")

    def add_task(
        self,
        name: str,
        schedule_expr: str,
        action: str,
        enabled: bool = True
    ) -> ScheduledTask:
        """Add a scheduled task programmatically.

        Args:
            name: Unique task name
            schedule_expr: Schedule expression (see parse_schedule)
            action: Action name (must be registered)
            enabled: Whether task is enabled

        Returns:
            Created ScheduledTask
        """
        # Check if action is registered
        if action not in self.action_handlers:
            logger.warning(f"[Scheduler] Action not registered: {action}")
            # Don't fail - allow action to be registered later

        # Parse and create schedule
        try:
            job = self._parse_schedule(schedule_expr)
            if job:
                # Wrap handler to track execution
                def wrapped_handler():
                    asyncio.create_task(self._run_action(name, action))

                job.do(wrapped_handler)
        except Exception as e:
            logger.error(f"[Scheduler] Failed to parse schedule '{schedule_expr}': {e}")
            job = None

        task = ScheduledTask(
            name=name,
            schedule_expr=schedule_expr,
            action=action,
            enabled=enabled,
            job=job
        )

        self.tasks.append(task)
        logger.info(f"[Scheduler] Added task: {name} ({schedule_expr})")
        return task

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task by name."""
        for i, task in enumerate(self.tasks):
            if task.name == name:
                # Cancel the scheduled job
                if task.job:
                    schedule.cancel_job(task.job)
                self.tasks.pop(i)
                logger.info(f"[Scheduler] Removed task: {name}")
                return True
        return False

    def enable_task(self, name: str) -> bool:
        """Enable a task by name. Persists to config."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = True
                logger.info(f"[Scheduler] Enabled task: {name}")
                self._persist_task_state(name, True)
                return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a task by name. Persists to config."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = False
                logger.info(f"[Scheduler] Disabled task: {name}")
                self._persist_task_state(name, False)
                return True
        return False

    def _persist_task_state(self, name: str, enabled: bool):
        """Persist task enable/disable state to config.local.yml."""
        try:
            import yaml
            config_path = self._config_path or "config.local.yml"
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}

            # Update the specific task's enabled state
            scheduler_tasks = config.setdefault("scheduler", {}).setdefault("tasks", [])
            for task_cfg in scheduler_tasks:
                if task_cfg.get("name") == name:
                    task_cfg["enabled"] = enabled
                    break
            else:
                # Task not in config yet — find it and add
                for task in self.tasks:
                    if task.name == name:
                        scheduler_tasks.append({
                            "name": name,
                            "schedule": task.schedule_expr,
                            "action": task.action,
                            "enabled": enabled,
                        })
                        break

            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            logger.debug(f"[Scheduler] Persisted state for {name}: enabled={enabled}")
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to persist task state: {e}")

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a task by name."""
        for task in self.tasks:
            if task.name == name:
                return task
        return None

    def list_tasks(self) -> List[ScheduledTask]:
        """Get all tasks."""
        return self.tasks.copy()

    def run_pending(self):
        """Check and run any pending scheduled tasks.

        Should be called from Heartbeat tick (every 60s).
        """
        if not self.enabled:
            return

        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"[Scheduler] Error running pending tasks: {e}")

    async def _run_action(self, task_name: str, action: str):
        """Run a scheduled action."""
        task = self.get_task(task_name)
        if not task:
            logger.warning(f"[Scheduler] Task not found: {task_name}")
            return

        if not task.enabled:
            logger.debug(f"[Scheduler] Task disabled, skipping: {task_name}")
            return

        handler = self.action_handlers.get(action)
        if not handler:
            error_msg = f"Action handler not found: {action}"
            logger.error(f"[Scheduler] {error_msg}")
            task.last_error = error_msg
            return

        try:
            logger.info(f"[Scheduler] Running task: {task_name} (action: {action})")
            await handler()
            task.last_run = time.time()
            task.run_count += 1
            task.last_error = None
            logger.debug(f"[Scheduler] Task completed: {task_name}")
        except Exception as e:
            error_msg = f"Action failed: {str(e)}"
            logger.error(f"[Scheduler] {error_msg} (task: {task_name})")
            task.last_error = error_msg

    # Allowed day names for schedule expressions
    _VALID_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
    # Allowed interval units
    _VALID_UNITS = {"seconds", "minutes", "hours", "days", "weeks",
                    "second", "minute", "hour", "day", "week"}

    def _parse_schedule(self, expr: str) -> Optional[schedule.Job]:
        """Parse a schedule expression into a schedule.Job safely.

        Supports expressions like:
        - "every().day.at('14:30')"
        - "every().hour"
        - "every().monday.at('09:00')"
        - "every(5).minutes"

        Uses regex validation instead of eval() for safety.

        Args:
            expr: Schedule expression string

        Returns:
            schedule.Job object or None if parse failed
        """
        try:
            # Validate expression format with regex before parsing
            # Match: every(N). or every(). followed by unit/day and optional .at('HH:MM')
            pattern = r"^every\((\d*)\)\.([\w]+)(?:\.at\('(\d{1,2}:\d{2})'\))?$"
            match = re.match(pattern, expr.strip())
            if not match:
                logger.error(f"[Scheduler] Invalid schedule expression format: {expr}")
                return None

            interval_str, unit_or_day, at_time = match.groups()
            interval = int(interval_str) if interval_str else None
            unit_or_day = unit_or_day.lower()

            # Validate unit/day name against whitelist
            if unit_or_day not in self._VALID_UNITS and unit_or_day not in self._VALID_DAYS:
                logger.error(f"[Scheduler] Invalid schedule unit/day: {unit_or_day}")
                return None

            # Validate time format if present
            if at_time:
                parts = at_time.split(":")
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    logger.error(f"[Scheduler] Invalid time in schedule: {at_time}")
                    return None

            # Build the job safely
            if interval:
                job = schedule.every(interval)
            else:
                job = schedule.every()

            # Chain the unit/day
            job = getattr(job, unit_or_day)

            # Chain .at() if specified
            if at_time:
                job = job.at(at_time)

            if isinstance(job, schedule.Job):
                return job
            else:
                logger.error(f"[Scheduler] Expression did not produce a Job: {expr}")
                return None

        except Exception as e:
            logger.error(f"[Scheduler] Failed to parse schedule expression '{expr}': {e}")
            return None

    def load_from_config(self, config: Dict[str, Any]):
        """Load scheduled tasks from configuration.

        Expected format:
        {
            "enabled": true,
            "tasks": [
                {
                    "name": "daily_summary",
                    "schedule": "every().day.at('08:00')",
                    "action": "send_summary",
                    "enabled": true
                }
            ]
        }
        """
        if not config:
            return

        self.enabled = config.get("enabled", True)
        tasks_config = config.get("tasks", [])

        for task_cfg in tasks_config:
            name = task_cfg.get("name")
            schedule_expr = task_cfg.get("schedule")
            action = task_cfg.get("action")
            enabled = task_cfg.get("enabled", True)

            if not all([name, schedule_expr, action]):
                logger.warning(f"[Scheduler] Incomplete task config: {task_cfg}")
                continue

            self.add_task(name, schedule_expr, action, enabled)

        logger.info(f"[Scheduler] Loaded {len(self.tasks)} tasks from config")

    def get_next_run_times(self) -> Dict[str, str]:
        """Get next run time for each task.

        Returns:
            Dict mapping task name to next run time string
        """
        next_runs = {}
        for task in self.tasks:
            if task.enabled and task.job:
                try:
                    next_run = task.job.next_run
                    if next_run:
                        next_runs[task.name] = next_run.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        next_runs[task.name] = "Not scheduled"
                except Exception:
                    next_runs[task.name] = "Unknown"
            else:
                next_runs[task.name] = "Disabled"
        return next_runs


# Built-in action handlers
# These can be registered by Inkling during initialization

async def action_test_greeting():
    """Test action - just logs a message."""
    logger.info("[Scheduler] Test greeting action triggered!")


async def action_daily_summary(inkling):
    """Daily task summary action."""
    # This will be properly implemented when integrated with Inkling
    logger.info("[Scheduler] Daily summary action triggered")
    # TODO: Get task stats and display on screen or send notification


async def action_weekly_cleanup(inkling):
    """Weekly cleanup action."""
    logger.info("[Scheduler] Weekly cleanup action triggered")
    # TODO: Prune old memories, archive completed tasks
