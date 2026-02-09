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


def _get_journal_dir():
    """Get journal directory path, create if needed."""
    from pathlib import Path
    journal_dir = Path.home() / ".inkling" / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    return journal_dir


def _cleanup_old_journal_entries(pattern="*.txt", days=30):
    """Delete journal entries older than specified days."""
    from pathlib import Path
    from datetime import datetime, timedelta

    journal_dir = _get_journal_dir()
    cutoff = datetime.now() - timedelta(days=days)

    for file in journal_dir.glob(pattern):
        try:
            if file.stat().st_mtime < cutoff.timestamp():
                file.unlink()
                logger.debug(f"[Scheduler] Cleaned up old journal: {file.name}")
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to clean up {file.name}: {e}")


async def action_daily_summary(inkling):
    """Daily task summary action."""
    logger.info("[Scheduler] Daily summary action triggered")
    try:
        if not inkling.task_manager:
            logger.warning("[Scheduler] Task manager not available")
            return

        # Get task stats
        stats = await inkling.task_manager.get_stats()
        pending = stats.get("pending", 0)
        in_progress = stats.get("in_progress", 0)
        completed_today = stats.get("completed_today", 0)

        # Create summary message
        summary = f"📋 Daily Summary: {pending} pending, {in_progress} in progress, {completed_today} completed today"

        # Display on screen
        if inkling.display:
            await inkling.display.update(
                face="happy",
                text=summary,
                status="SUMMARY"
            )
        logger.info(f"[Scheduler] {summary}")
    except Exception as e:
        logger.error(f"[Scheduler] Daily summary failed: {e}")


async def action_weekly_cleanup(inkling):
    """Weekly cleanup action - prune old memories and archive completed tasks."""
    logger.info("[Scheduler] Weekly cleanup action triggered")
    try:
        # Archive old completed tasks (older than 30 days)
        if inkling.task_manager:
            # This would require adding archive functionality to TaskManager
            # For now, just log
            logger.info("[Scheduler] Task archival not yet implemented")

        # Prune old memories (if memory module exists)
        # This would integrate with core/memory.py
        logger.info("[Scheduler] Memory pruning not yet implemented")

        if inkling.display:
            await inkling.display.update(
                face="cool",
                text="✨ Weekly cleanup complete",
                status="CLEANUP"
            )
    except Exception as e:
        logger.error(f"[Scheduler] Weekly cleanup failed: {e}")


async def action_nightly_backup(inkling):
    """Nightly backup of critical files to SD card or .inkling/backups."""
    logger.info("[Scheduler] Nightly backup action triggered")
    try:
        import shutil
        import tarfile
        from pathlib import Path
        from datetime import datetime

        # Source directory
        inkling_dir = Path.home() / ".inkling"
        if not inkling_dir.exists():
            logger.warning("[Scheduler] .inkling directory not found")
            return

        # Determine backup destination
        backup_base = None
        config = inkling.config if hasattr(inkling, 'config') else {}
        storage_config = config.get("storage", {})
        sd_config = storage_config.get("sd_card", {})

        # Try SD card first if enabled
        if sd_config.get("enabled", False):
            sd_path = sd_config.get("path", "auto")
            if sd_path == "auto":
                # Auto-detect SD card
                for mount_point in ["/media/pi", "/mnt"]:
                    mount_path = Path(mount_point)
                    if mount_path.exists():
                        sd_dirs = list(mount_path.iterdir())
                        if sd_dirs:
                            backup_base = sd_dirs[0] / "inkling_backups"
                            break
            else:
                backup_base = Path(sd_path) / "inkling_backups"

        # Fallback to .inkling/backups
        if not backup_base:
            backup_base = inkling_dir / "backups"

        backup_base.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_base / f"backup_{timestamp}.tar.gz"

        # Files to backup
        files_to_backup = [
            "tasks.db",
            "conversation.json",
            "memory.db",
            "config.local.yml",
            "personality.json"
        ]

        # Create tar.gz archive
        with tarfile.open(backup_file, "w:gz") as tar:
            for filename in files_to_backup:
                filepath = inkling_dir / filename
                if filepath.exists():
                    tar.add(filepath, arcname=filename)
                    logger.debug(f"[Scheduler] Backed up: {filename}")

        # Keep only last 7 backups
        backups = sorted(backup_base.glob("backup_*.tar.gz"))
        while len(backups) > 7:
            oldest = backups.pop(0)
            oldest.unlink()
            logger.debug(f"[Scheduler] Removed old backup: {oldest.name}")

        backup_size_mb = backup_file.stat().st_size / (1024 * 1024)
        logger.info(f"[Scheduler] Backup created: {backup_file.name} ({backup_size_mb:.2f} MB)")

        if inkling.display:
            await inkling.display.update(
                face="happy",
                text=f"💾 Backup complete ({backup_size_mb:.1f}MB)",
                status="BACKUP"
            )

    except Exception as e:
        logger.error(f"[Scheduler] Nightly backup failed: {e}")


async def action_system_health_check(inkling):
    """Check system health (disk, memory, temperature)."""
    logger.info("[Scheduler] System health check triggered")
    try:
        import psutil
        from datetime import datetime

        # Get system stats
        disk = psutil.disk_usage('/')
        memory = psutil.virtual_memory()
        cpu_temp = None

        # Try to get CPU temperature (Raspberry Pi)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                cpu_temp = int(f.read().strip()) / 1000.0
        except:
            pass

        # Check for warnings
        warnings = []
        if disk.percent > 80:
            warnings.append(f"⚠️ Disk usage: {disk.percent:.1f}% (high)")
        if memory.percent > 90:
            warnings.append(f"⚠️ Memory usage: {memory.percent:.1f}% (high)")
        if cpu_temp and cpu_temp > 65:
            warnings.append(f"⚠️ Temperature: {cpu_temp:.1f}°C (high)")

        # Build health log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_lines = [
            f"=== System Health Check - {timestamp} ===",
            f"Disk: {disk.percent:.1f}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)",
            f"Memory: {memory.percent:.1f}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)",
        ]
        if cpu_temp:
            log_lines.append(f"CPU Temp: {cpu_temp:.1f}°C")

        if warnings:
            log_lines.append("\nWARNINGS:")
            log_lines.extend(warnings)
        else:
            log_lines.append("\nStatus: ✅ All systems healthy")

        log_content = "\n".join(log_lines) + "\n\n"

        # Save to journal
        journal_dir = _get_journal_dir()
        today = datetime.now().strftime("%Y%m%d")
        journal_file = journal_dir / f"health_{today}.log"

        # Append to daily log file
        with open(journal_file, 'a') as f:
            f.write(log_content)
        logger.debug(f"[Scheduler] Health check saved to {journal_file.name}")

        # Create tasks for warnings
        if warnings and inkling.task_manager:
            for warning in warnings:
                await inkling.task_manager.create_task(
                    title="System Health Warning",
                    description=warning,
                    priority="high"
                )
                logger.warning(f"[Scheduler] {warning}")

        # Log healthy status
        if not warnings:
            status_msg = f"✅ System healthy - Disk: {disk.percent:.1f}%, Memory: {memory.percent:.1f}%"
            if cpu_temp:
                status_msg += f", Temp: {cpu_temp:.1f}°C"
            logger.info(f"[Scheduler] {status_msg}")

        # Cleanup old logs (keep 30 days)
        _cleanup_old_journal_entries(pattern="health_*.log", days=30)

    except Exception as e:
        logger.error(f"[Scheduler] Health check failed: {e}")


async def action_task_reminders(inkling):
    """Check for tasks due soon and display reminders."""
    logger.info("[Scheduler] Task reminders triggered")
    try:
        if not inkling.task_manager:
            logger.warning("[Scheduler] Task manager not available")
            return

        from datetime import datetime, timedelta

        # Get tasks due within 24 hours
        all_tasks = await inkling.task_manager.list_tasks(status="pending")
        now = datetime.now()
        due_soon = []

        for task in all_tasks:
            if task.due_date:
                # Parse due date (assuming ISO format)
                try:
                    due = datetime.fromisoformat(task.due_date)
                    hours_until = (due - now).total_seconds() / 3600
                    if 0 < hours_until <= 24:
                        due_soon.append((task, hours_until))
                except:
                    pass

        if due_soon:
            # Sort by time until due
            due_soon.sort(key=lambda x: x[1])

            # Display top 3
            if inkling.display:
                if len(due_soon) == 1:
                    task, hours = due_soon[0]
                    msg = f"⏰ Task due in {hours:.0f}h: {task.title}"
                else:
                    msg = f"⏰ {len(due_soon)} tasks due soon"

                await inkling.display.update(
                    face="curious",
                    text=msg,
                    status="REMINDER"
                )

            logger.info(f"[Scheduler] {len(due_soon)} tasks due within 24 hours")
        else:
            logger.debug("[Scheduler] No tasks due soon")

    except Exception as e:
        logger.error(f"[Scheduler] Task reminders failed: {e}")


async def action_morning_briefing(inkling):
    """Morning briefing: weather, tasks, AI greeting.

    Note: Gmail/Calendar integration removed (was Composio-dependent).
    Users can add their own MCP servers for email/calendar if needed.
    """
    logger.info("[Scheduler] Morning briefing triggered")
    try:
        from datetime import datetime
        briefing_parts = []

        # 1. Weather (Portland, OR)
        try:
            import os
            import json
            import re

            # Get weather config
            config = inkling.config if hasattr(inkling, 'config') else {}
            bg_config = config.get("background_tasks", {})
            weather_config = bg_config.get("weather", {})
            city = weather_config.get("city", "Portland")
            state = weather_config.get("state", "OR")

            weather_key = os.getenv("OPENWEATHER_API_KEY")

            if weather_key and inkling.mcp_client:
                # Option 1: OpenWeatherMap API (requires key)
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city},{state},US&appid={weather_key}&units=imperial"
                result = await inkling.mcp_client.call_tool("curl", {"url": url})
                if result and not result.get("isError"):
                    data = json.loads(result.get("content", [{}])[0].get("text", "{}"))
                    temp = data.get("main", {}).get("temp", "?")
                    desc = data.get("weather", [{}])[0].get("main", "?")
                    briefing_parts.append(f"☀️ {city}: {temp}°F, {desc}")
            elif inkling.mcp_client:
                # Option 2: wttr.in (free, no API key needed)
                # Format: Portland,OR?format=%C+%t (condition + temp)
                location = f"{city},{state}".replace(" ", "+")
                url = f"https://wttr.in/{location}?format=%C+%t&u"  # %C=condition, %t=temp, &u=USCS units
                result = await inkling.mcp_client.call_tool("curl", {"url": url})
                if result and not result.get("isError"):
                    weather_text = result.get("content", [{}])[0].get("text", "").strip()
                    # Clean up ANSI codes if any
                    weather_text = re.sub(r'\x1b\[[0-9;]*m', '', weather_text)
                    if weather_text:
                        briefing_parts.append(f"☀️ {city}: {weather_text}")
        except Exception as e:
            logger.debug(f"[Scheduler] Weather fetch failed: {e}")

        # 2. Tasks due today
        if inkling.task_manager:
            try:
                tasks = await inkling.task_manager.list_tasks(status="pending")
                today = datetime.now().date()
                due_today = [t for t in tasks if t.due_date and datetime.fromisoformat(t.due_date).date() == today]
                if due_today:
                    briefing_parts.append(f"✅ {len(due_today)} tasks due today")
            except Exception as e:
                logger.debug(f"[Scheduler] Task check failed: {e}")

        # 3. AI-generated greeting based on mood
        if inkling.brain and briefing_parts:
            try:
                context = " | ".join(briefing_parts)
                prompt = f"Generate a brief, cheerful good morning message (1 sentence) considering: {context}"
                greeting = await inkling.brain.chat(prompt)
                briefing_parts.insert(0, greeting.strip())
            except Exception as e:
                logger.debug(f"[Scheduler] AI greeting failed: {e}")

        # Save to journal
        if briefing_parts:
            journal_dir = _get_journal_dir()
            today = datetime.now().strftime("%Y%m%d")
            journal_file = journal_dir / f"briefing_{today}.txt"

            briefing_content = f"=== Morning Briefing - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            briefing_content += "\n".join(briefing_parts) + "\n\n"

            with open(journal_file, 'w') as f:
                f.write(briefing_content)
            logger.debug(f"[Scheduler] Morning briefing saved to {journal_file.name}")

            # Display briefing
            if inkling.display:
                briefing_text = "\n".join(briefing_parts)
                await inkling.display.update(
                    face="happy",
                    text=briefing_text,
                    status="BRIEFING"
                )
            logger.info(f"[Scheduler] Morning briefing: {len(briefing_parts)} items")

            # Cleanup old briefings (keep 30 days)
            _cleanup_old_journal_entries(pattern="briefing_*.txt", days=30)
        else:
            logger.info("[Scheduler] Morning briefing: no items to display")

    except Exception as e:
        logger.error(f"[Scheduler] Morning briefing failed: {e}")


async def action_rss_digest(inkling):
    """Fetch and summarize RSS feeds."""
    logger.info("[Scheduler] RSS digest action triggered")
    try:
        import feedparser
        import requests
        from datetime import datetime

        # Get RSS feeds from config
        config = inkling.config if hasattr(inkling, 'config') else {}
        bg_tasks_config = config.get("background_tasks", {})
        feeds = bg_tasks_config.get("rss_feeds", [])

        if not feeds:
            logger.warning("[Scheduler] No RSS feeds configured")
            return

        all_items = []
        for feed_config in feeds[:5]:  # Limit to 5 feeds to avoid timeout
            feed_name = feed_config.get("name", "Unknown")
            feed_url = feed_config.get("url")

            if not feed_url:
                continue

            try:
                # Fetch feed with timeout
                response = requests.get(feed_url, timeout=10)
                feed = feedparser.parse(response.content)

                # Get top 3 items from each feed
                for entry in feed.entries[:3]:
                    all_items.append({
                        "source": feed_name,
                        "title": entry.get("title", "Untitled"),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", "")
                    })

                logger.debug(f"[Scheduler] Fetched {len(feed.entries[:3])} items from {feed_name}")
            except Exception as e:
                logger.warning(f"[Scheduler] Failed to fetch {feed_name}: {e}")

        if not all_items:
            logger.info("[Scheduler] No RSS items fetched")
            return

        # AI summarization
        if inkling.brain:
            try:
                # Create concise summary of titles
                titles = [f"- {item['source']}: {item['title']}" for item in all_items[:10]]
                prompt = f"Summarize these top tech stories in 3-5 sentences:\n" + "\n".join(titles)
                summary = await inkling.brain.chat(prompt)

                # Save to journal
                journal_dir = _get_journal_dir()
                today = datetime.now().strftime("%Y%m%d")
                journal_file = journal_dir / f"rss_{today}.txt"

                journal_content = f"=== RSS Digest - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n"
                journal_content += f"AI SUMMARY:\n{summary.strip()}\n\n"
                journal_content += f"FULL HEADLINES ({len(all_items)} items):\n"
                for item in all_items:
                    journal_content += f"- [{item['source']}] {item['title']}\n"
                    if item['link']:
                        journal_content += f"  {item['link']}\n"
                journal_content += "\n"

                with open(journal_file, 'w') as f:
                    f.write(journal_content)
                logger.debug(f"[Scheduler] RSS digest saved to {journal_file.name}")

                # Display summary
                if inkling.display:
                    await inkling.display.update(
                        face="curious",
                        text=f"📰 RSS Digest:\n{summary.strip()}",
                        status="RSS"
                    )

                logger.info(f"[Scheduler] RSS digest: {len(all_items)} items from {len(feeds)} feeds")

                # Cleanup old digests (keep 30 days)
                _cleanup_old_journal_entries(pattern="rss_*.txt", days=30)

            except Exception as e:
                logger.error(f"[Scheduler] AI summarization failed: {e}")
        else:
            logger.warning("[Scheduler] Brain not available for RSS summarization")

    except ImportError:
        logger.error("[Scheduler] feedparser not installed. Run: pip install feedparser")
    except Exception as e:
        logger.error(f"[Scheduler] RSS digest failed: {e}")
