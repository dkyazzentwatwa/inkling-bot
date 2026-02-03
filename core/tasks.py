"""
Project Inkling - Task Manager

A companion-friendly task management system that integrates with
the personality system. Tasks aren't just to-dos - they're things
your companion helps you accomplish and celebrates with you.
"""

import sqlite3
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    """Task status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecurrencePattern(Enum):
    """Task recurrence patterns."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKDAYS = "weekdays"  # Mon-Fri


@dataclass
class Task:
    """A single task."""
    id: int
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[float]  # Unix timestamp
    created_at: float
    completed_at: Optional[float]
    tags: List[str]
    recurrence: RecurrencePattern
    reminder_sent: bool
    xp_reward: int  # XP earned on completion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "due_date": self.due_date,
            "due_date_formatted": self._format_due_date(),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
            "recurrence": self.recurrence.value,
            "reminder_sent": self.reminder_sent,
            "xp_reward": self.xp_reward,
            "is_overdue": self.is_overdue,
            "is_due_today": self.is_due_today,
            "is_due_soon": self.is_due_soon,
        }

    def _format_due_date(self) -> Optional[str]:
        if not self.due_date:
            return None
        dt = datetime.fromtimestamp(self.due_date)
        return dt.strftime("%Y-%m-%d %H:%M")

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False
        return time.time() > self.due_date

    @property
    def is_due_today(self) -> bool:
        if not self.due_date:
            return False
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False
        due_dt = datetime.fromtimestamp(self.due_date)
        today = datetime.now().date()
        return due_dt.date() == today

    @property
    def is_due_soon(self) -> bool:
        """Due within 24 hours."""
        if not self.due_date:
            return False
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False
        hours_until = (self.due_date - time.time()) / 3600
        return 0 < hours_until <= 24


class TaskStore:
    """
    Persistent task storage for the Inkling companion.

    Integrates with personality system for:
    - XP rewards on completion
    - Mood-aware reminders
    - Smart task suggestions
    """

    # XP rewards by priority
    XP_REWARDS = {
        TaskPriority.LOW: 5,
        TaskPriority.MEDIUM: 10,
        TaskPriority.HIGH: 20,
        TaskPriority.URGENT: 30,
    }

    def __init__(self, data_dir: str = "~/.inkling"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "tasks.db"
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        """Initialize the database."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the task tables."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                due_date REAL,
                created_at REAL NOT NULL,
                completed_at REAL,
                tags TEXT DEFAULT '[]',
                recurrence TEXT DEFAULT 'none',
                reminder_sent INTEGER DEFAULT 0,
                xp_reward INTEGER DEFAULT 10
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)
        """)
        self._conn.commit()

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        recurrence: RecurrencePattern = RecurrencePattern.NONE,
    ) -> Task:
        """
        Add a new task.

        Args:
            title: Short task title
            description: Optional longer description
            priority: Task priority level
            due_date: Optional due date/time
            tags: Optional list of tags for organization
            recurrence: Whether this task repeats

        Returns:
            The created Task object
        """
        now = time.time()
        due_ts = due_date.timestamp() if due_date else None
        tags_json = json.dumps(tags or [])
        xp_reward = self.XP_REWARDS.get(priority, 10)

        cursor = self._conn.execute(
            """
            INSERT INTO tasks (title, description, priority, due_date, created_at, tags, recurrence, xp_reward)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, priority.value, due_ts, now, tags_json, recurrence.value, xp_reward)
        )
        self._conn.commit()

        return self.get_task(cursor.lastrowid)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a specific task by ID."""
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

        if row:
            return self._row_to_task(row)
        return None

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        status: Optional[TaskStatus] = None,
    ) -> Optional[Task]:
        """Update a task's fields."""
        task = self.get_task(task_id)
        if not task:
            return None

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority.value)
            updates.append("xp_reward = ?")
            params.append(self.XP_REWARDS.get(priority, 10))
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date.timestamp())
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
            if status == TaskStatus.COMPLETED:
                updates.append("completed_at = ?")
                params.append(time.time())

        if updates:
            params.append(task_id)
            self._conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                params
            )
            self._conn.commit()

        return self.get_task(task_id)

    def complete_task(self, task_id: int) -> Optional[Task]:
        """
        Mark a task as completed.

        Returns the completed task (for XP calculation) or None if not found.
        """
        task = self.get_task(task_id)
        if not task:
            return None

        if task.status == TaskStatus.COMPLETED:
            return task  # Already completed

        self._conn.execute(
            """
            UPDATE tasks SET status = ?, completed_at = ?
            WHERE id = ?
            """,
            (TaskStatus.COMPLETED.value, time.time(), task_id)
        )
        self._conn.commit()

        # Handle recurring tasks
        if task.recurrence != RecurrencePattern.NONE:
            self._create_next_occurrence(task)

        return self.get_task(task_id)

    def _create_next_occurrence(self, task: Task) -> None:
        """Create next occurrence of a recurring task."""
        if not task.due_date:
            return

        due_dt = datetime.fromtimestamp(task.due_date)

        # Calculate next due date
        if task.recurrence == RecurrencePattern.DAILY:
            next_due = due_dt + timedelta(days=1)
        elif task.recurrence == RecurrencePattern.WEEKLY:
            next_due = due_dt + timedelta(weeks=1)
        elif task.recurrence == RecurrencePattern.MONTHLY:
            # Approximate - add 30 days
            next_due = due_dt + timedelta(days=30)
        elif task.recurrence == RecurrencePattern.WEEKDAYS:
            next_due = due_dt + timedelta(days=1)
            while next_due.weekday() >= 5:  # Skip weekends
                next_due += timedelta(days=1)
        else:
            return

        # Create the new task
        self.add_task(
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=next_due,
            tags=task.tags,
            recurrence=task.recurrence,
        )

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        cursor = self._conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> List[Task]:
        """List tasks with optional filters."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)
        else:
            # Default: exclude completed/cancelled
            query += " AND status NOT IN (?, ?)"
            params.extend([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value])

        if priority:
            query += " AND priority = ?"
            params.append(priority.value)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY due_date ASC NULLS LAST, priority DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_today_tasks(self) -> List[Task]:
        """Get tasks due today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        rows = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE due_date >= ? AND due_date < ?
              AND status NOT IN (?, ?)
            ORDER BY due_date ASC, priority DESC
            """,
            (today_start.timestamp(), today_end.timestamp(),
             TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value)
        ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def get_overdue_tasks(self) -> List[Task]:
        """Get overdue tasks."""
        now = time.time()

        rows = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE due_date < ? AND due_date IS NOT NULL
              AND status NOT IN (?, ?)
            ORDER BY due_date ASC, priority DESC
            """,
            (now, TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value)
        ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Get tasks due in the next N days."""
        now = datetime.now()
        future = now + timedelta(days=days)

        rows = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE due_date >= ? AND due_date < ?
              AND status NOT IN (?, ?)
            ORDER BY due_date ASC, priority DESC
            """,
            (now.timestamp(), future.timestamp(),
             TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value)
        ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def get_high_priority_tasks(self) -> List[Task]:
        """Get high priority and urgent tasks."""
        rows = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE priority IN (?, ?)
              AND status NOT IN (?, ?)
            ORDER BY priority DESC, due_date ASC
            """,
            (TaskPriority.HIGH.value, TaskPriority.URGENT.value,
             TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value)
        ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def search_tasks(self, query: str, limit: int = 20) -> List[Task]:
        """Search tasks by title or description."""
        pattern = f"%{query.lower()}%"

        rows = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE (LOWER(title) LIKE ? OR LOWER(description) LIKE ?)
            ORDER BY status ASC, due_date ASC
            LIMIT ?
            """,
            (pattern, pattern, limit)
        ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def mark_reminder_sent(self, task_id: int) -> None:
        """Mark that a reminder was sent for this task."""
        self._conn.execute(
            "UPDATE tasks SET reminder_sent = 1 WHERE id = ?",
            (task_id,)
        )
        self._conn.commit()

    def get_pending_reminders(self) -> List[Task]:
        """Get tasks that need reminders (due soon, not reminded yet)."""
        now = time.time()
        soon = now + (24 * 3600)  # 24 hours from now

        rows = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE due_date BETWEEN ? AND ?
              AND reminder_sent = 0
              AND status NOT IN (?, ?)
            ORDER BY due_date ASC
            """,
            (now, soon, TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value)
        ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        pending = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = ?",
            (TaskStatus.PENDING.value,)
        ).fetchone()[0]
        completed = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = ?",
            (TaskStatus.COMPLETED.value,)
        ).fetchone()[0]
        overdue = len(self.get_overdue_tasks())
        today = len(self.get_today_tasks())

        # Completion rate (last 30 days)
        thirty_days_ago = time.time() - (30 * 86400)
        recent_completed = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = ? AND completed_at > ?",
            (TaskStatus.COMPLETED.value, thirty_days_ago)
        ).fetchone()[0]
        recent_total = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE created_at > ?",
            (thirty_days_ago,)
        ).fetchone()[0]

        completion_rate = (recent_completed / recent_total * 100) if recent_total > 0 else 0

        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "overdue": overdue,
            "due_today": today,
            "completion_rate_30d": round(completion_rate, 1),
        }

    def get_context_for_prompt(self, limit: int = 5) -> str:
        """
        Generate task context for AI prompts.

        Includes overdue, today, and high-priority tasks.
        """
        lines = []

        # Overdue tasks (most important)
        overdue = self.get_overdue_tasks()
        if overdue:
            lines.append(f"OVERDUE ({len(overdue)} tasks):")
            for task in overdue[:3]:
                lines.append(f"  - {task.title} (due {task._format_due_date()})")

        # Today's tasks
        today = self.get_today_tasks()
        if today:
            lines.append(f"Due today ({len(today)} tasks):")
            for task in today[:3]:
                lines.append(f"  - {task.title}")

        # High priority
        high_priority = self.get_high_priority_tasks()
        if high_priority:
            lines.append(f"High priority ({len(high_priority)} tasks):")
            for task in high_priority[:2]:
                priority_label = "URGENT" if task.priority == TaskPriority.URGENT else "HIGH"
                lines.append(f"  - [{priority_label}] {task.title}")

        if not lines:
            return ""

        return "User's tasks:\n" + "\n".join(lines)

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert a database row to a Task object."""
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=TaskPriority(row["priority"]),
            status=TaskStatus(row["status"]),
            due_date=row["due_date"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            recurrence=RecurrencePattern(row["recurrence"]) if row["recurrence"] else RecurrencePattern.NONE,
            reminder_sent=bool(row["reminder_sent"]),
            xp_reward=row["xp_reward"],
        )

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# ========== Helper Functions ==========

def parse_due_date(text: str) -> Optional[datetime]:
    """
    Parse natural language due dates.

    Supports:
    - "today", "tomorrow"
    - "monday", "tuesday", etc.
    - "next week"
    - "2024-01-15", "1/15", "Jan 15"
    - "in 2 hours", "in 3 days"
    """
    text = text.lower().strip()
    now = datetime.now()

    # Relative dates
    if text == "today":
        return now.replace(hour=23, minute=59, second=0, microsecond=0)
    if text == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    if text == "next week":
        return (now + timedelta(weeks=1)).replace(hour=23, minute=59, second=0, microsecond=0)

    # Day names
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if text in days:
        target_day = days.index(text)
        days_ahead = target_day - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=0, microsecond=0)

    # "in X hours/days"
    if text.startswith("in "):
        parts = text[3:].split()
        if len(parts) >= 2:
            try:
                amount = int(parts[0])
                unit = parts[1]
                if unit.startswith("hour"):
                    return now + timedelta(hours=amount)
                elif unit.startswith("day"):
                    return (now + timedelta(days=amount)).replace(hour=23, minute=59, second=0, microsecond=0)
                elif unit.startswith("week"):
                    return (now + timedelta(weeks=amount)).replace(hour=23, minute=59, second=0, microsecond=0)
            except ValueError:
                pass

    # ISO format: 2024-01-15
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(hour=23, minute=59, second=0, microsecond=0)
    except ValueError:
        pass

    # MM/DD format
    try:
        dt = datetime.strptime(text, "%m/%d")
        return dt.replace(year=now.year, hour=23, minute=59, second=0, microsecond=0)
    except ValueError:
        pass

    return None


def parse_priority(text: str) -> TaskPriority:
    """Parse priority from text."""
    text = text.lower().strip()
    mapping = {
        "low": TaskPriority.LOW,
        "l": TaskPriority.LOW,
        "1": TaskPriority.LOW,
        "medium": TaskPriority.MEDIUM,
        "med": TaskPriority.MEDIUM,
        "m": TaskPriority.MEDIUM,
        "2": TaskPriority.MEDIUM,
        "high": TaskPriority.HIGH,
        "h": TaskPriority.HIGH,
        "3": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
        "u": TaskPriority.URGENT,
        "4": TaskPriority.URGENT,
        "!": TaskPriority.URGENT,
        "!!": TaskPriority.URGENT,
    }
    return mapping.get(text, TaskPriority.MEDIUM)
