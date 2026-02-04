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
        """Enable a task by name."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = True
                logger.info(f"[Scheduler] Enabled task: {name}")
                return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a task by name."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = False
                logger.info(f"[Scheduler] Disabled task: {name}")
                return True
        return False

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

    def _parse_schedule(self, expr: str) -> Optional[schedule.Job]:
        """Parse a schedule expression into a schedule.Job.

        Supports expressions like:
        - "every().day.at('14:30')"
        - "every().hour"
        - "every().monday.at('09:00')"
        - "every(5).minutes"

        Args:
            expr: Schedule expression string

        Returns:
            schedule.Job object or None if parse failed
        """
        try:
            # Parse the expression by evaluating it in a safe context
            # This is safe because we control the expression format
            safe_globals = {"every": schedule.every}
            job = eval(expr, safe_globals)

            if isinstance(job, schedule.Job):
                return job
            else:
                logger.error(f"[Scheduler] Invalid schedule expression (not a Job): {expr}")
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
                    next_run = schedule.next_run()
                    if next_run:
                        next_runs[task.name] = next_run.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        next_runs[task.name] = "Not scheduled"
                except:
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
