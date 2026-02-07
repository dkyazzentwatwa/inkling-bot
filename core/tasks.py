"""
Project Inkling - Task Manager

Manages tasks with personality-aware behaviors and XP integration.
Local-first with SQLite storage, designed for AI companion interaction.
"""

import sqlite3
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timedelta
import os


class TaskStatus(Enum):
    """Task completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
    """A task with AI companion integration."""
    id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    created_at: float = field(default_factory=time.time)
    due_date: Optional[float] = None
    completed_at: Optional[float] = None

    # AI companion integration
    mood_on_creation: Optional[str] = None  # Companion's mood when created
    celebration_level: float = 0.5  # How excited to be when completed (0.0-1.0)

    # MCP integration
    mcp_tool: Optional[str] = None  # MCP tool to execute
    mcp_params: Optional[Dict[str, Any]] = None  # Tool parameters
    mcp_result: Optional[str] = None  # Result from tool execution

    # Organization
    tags: List[str] = field(default_factory=list)
    project: Optional[str] = None

    # Time tracking
    estimated_minutes: Optional[int] = None
    actual_minutes: int = 0

    # Subtasks
    subtasks: List[str] = field(default_factory=list)
    subtasks_completed: List[bool] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary."""
        data = data.copy()
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = Priority(data['priority'])
        return cls(**data)

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status == TaskStatus.COMPLETED:
            return False
        return time.time() > self.due_date

    @property
    def days_until_due(self) -> Optional[int]:
        """Days until due date (negative if overdue)."""
        if not self.due_date:
            return None
        delta = self.due_date - time.time()
        return int(delta / 86400)  # Convert to days

    @property
    def completion_percentage(self) -> float:
        """Percentage of subtasks completed."""
        if not self.subtasks:
            return 100.0 if self.status == TaskStatus.COMPLETED else 0.0
        completed = sum(self.subtasks_completed)
        return (completed / len(self.subtasks)) * 100


class TaskManager:
    """Manages tasks with personality-aware behaviors."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize task manager.

        Args:
            db_path: Path to SQLite database (default: ~/.inkling/tasks.db)
        """
        if db_path is None:
            home = os.path.expanduser("~")
            inkling_dir = os.path.join(home, ".inkling")
            os.makedirs(inkling_dir, exist_ok=True)
            db_path = os.path.join(inkling_dir, "tasks.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'medium',
                created_at REAL NOT NULL,
                due_date REAL,
                completed_at REAL,
                mood_on_creation TEXT,
                celebration_level REAL DEFAULT 0.5,
                mcp_tool TEXT,
                mcp_params TEXT,
                mcp_result TEXT,
                tags TEXT,
                project TEXT,
                estimated_minutes INTEGER,
                actual_minutes INTEGER DEFAULT 0,
                subtasks TEXT,
                subtasks_completed TEXT
            )
        """)

        # Index for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_due_date ON tasks(due_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project ON tasks(project)
        """)

        conn.commit()
        conn.close()

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        due_date: Optional[float] = None,
        mood: Optional[str] = None,
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
        **kwargs
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title
            description: Optional description
            priority: Task priority
            due_date: Unix timestamp for due date
            mood: Companion's mood when creating task
            tags: List of tags
            project: Project name
            **kwargs: Additional Task fields

        Returns:
            Created Task object
        """
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            mood_on_creation=mood,
            tags=tags or [],
            project=project,
            **kwargs
        )

        self._save_task(task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_task(row)
        return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Task]:
        """List tasks with optional filters.

        Args:
            status: Filter by status
            project: Filter by project
            tags: Filter by tags (task must have ALL tags)
            limit: Maximum number of tasks to return

        Returns:
            List of Task objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if project:
            query += " AND project = ?"
            params.append(project)

        # Order by priority and due date
        query += " ORDER BY CASE priority "
        query += "WHEN 'urgent' THEN 1 "
        query += "WHEN 'high' THEN 2 "
        query += "WHEN 'medium' THEN 3 "
        query += "WHEN 'low' THEN 4 END, "
        query += "due_date ASC NULLS LAST, created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(int(limit))

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        tasks = [self._row_to_task(row) for row in rows]

        # Filter by tags if specified
        if tags:
            tasks = [t for t in tasks if all(tag in t.tags for tag in tags)]

        return tasks

    def update_task(self, task: Task) -> None:
        """Update an existing task.

        Args:
            task: Task object with updated fields
        """
        self._save_task(task)

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed.

        Args:
            task_id: Task ID

        Returns:
            Updated Task object or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        self._save_task(task)

        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks.

        Returns:
            List of overdue Task objects
        """
        tasks = self.list_tasks(status=TaskStatus.PENDING)
        tasks.extend(self.list_tasks(status=TaskStatus.IN_PROGRESS))

        return [t for t in tasks if t.is_overdue]

    def get_due_soon(self, days: int = 3) -> List[Task]:
        """Get tasks due within specified days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of Task objects
        """
        cutoff = time.time() + (days * 86400)

        tasks = self.list_tasks(status=TaskStatus.PENDING)
        tasks.extend(self.list_tasks(status=TaskStatus.IN_PROGRESS))

        return [t for t in tasks if t.due_date and t.due_date <= cutoff]

    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics.

        Returns:
            Dictionary with stats
        """
        all_tasks = self.list_tasks()

        stats = {
            'total': len(all_tasks),
            'pending': len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            'in_progress': len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]),
            'completed': len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
            'overdue': len(self.get_overdue_tasks()),
            'due_soon': len(self.get_due_soon()),
        }

        # Completion rate (last 30 days)
        thirty_days_ago = time.time() - (30 * 86400)
        recent_completed = [
            t for t in all_tasks
            if t.status == TaskStatus.COMPLETED and t.completed_at and t.completed_at >= thirty_days_ago
        ]
        recent_total = [t for t in all_tasks if t.created_at >= thirty_days_ago]

        if recent_total:
            stats['completion_rate_30d'] = len(recent_completed) / len(recent_total)
        else:
            stats['completion_rate_30d'] = 0.0

        return stats

    def _save_task(self, task: Task):
        """Save task to database."""
        import json

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO tasks (
                id, title, description, status, priority,
                created_at, due_date, completed_at,
                mood_on_creation, celebration_level,
                mcp_tool, mcp_params, mcp_result,
                tags, project, estimated_minutes, actual_minutes,
                subtasks, subtasks_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id,
            task.title,
            task.description,
            task.status.value,
            task.priority.value,
            task.created_at,
            task.due_date,
            task.completed_at,
            task.mood_on_creation,
            task.celebration_level,
            task.mcp_tool,
            json.dumps(task.mcp_params) if task.mcp_params else None,
            task.mcp_result,
            json.dumps(task.tags),
            task.project,
            task.estimated_minutes,
            task.actual_minutes,
            json.dumps(task.subtasks),
            json.dumps(task.subtasks_completed)
        ))

        conn.commit()
        conn.close()

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        import json

        return Task(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            status=TaskStatus(row['status']),
            priority=Priority(row['priority']),
            created_at=row['created_at'],
            due_date=row['due_date'],
            completed_at=row['completed_at'],
            mood_on_creation=row['mood_on_creation'],
            celebration_level=row['celebration_level'] or 0.5,
            mcp_tool=row['mcp_tool'],
            mcp_params=json.loads(row['mcp_params']) if row['mcp_params'] else None,
            mcp_result=row['mcp_result'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            project=row['project'],
            estimated_minutes=row['estimated_minutes'],
            actual_minutes=row['actual_minutes'] or 0,
            subtasks=json.loads(row['subtasks']) if row['subtasks'] else [],
            subtasks_completed=json.loads(row['subtasks_completed']) if row['subtasks_completed'] else []
        )
