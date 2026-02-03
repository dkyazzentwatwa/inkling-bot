"""
Project Inkling - Task Tools for AI Integration

Provides MCP-compatible tool definitions that allow the AI companion
to manage tasks on behalf of the user. These tools integrate with
the personality system for a more engaging experience.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime

from .tasks import (
    TaskStore, Task, TaskPriority, TaskStatus,
    RecurrencePattern, parse_due_date, parse_priority
)


class TaskTools:
    """
    Tool provider for AI-assisted task management.

    Exposes task operations as callable tools that can be:
    1. Used directly by the Brain for tool use
    2. Exposed via MCP to external AI systems
    3. Called from slash commands

    Integrates with personality for:
    - XP rewards on task completion
    - Mood updates based on task progress
    - Personalized task suggestions
    """

    def __init__(self, task_store: TaskStore, personality=None):
        """
        Initialize task tools.

        Args:
            task_store: TaskStore instance for persistence
            personality: Optional Personality instance for integration
        """
        self.store = task_store
        self.personality = personality

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions in MCP/Claude format.

        These definitions can be used by the AI to understand
        what tools are available and how to use them.
        """
        return [
            {
                "name": "add_task",
                "description": "Add a new task for the user to complete. Use this when the user mentions something they need to do, want to remember, or asks you to remind them of something.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short, clear task title (e.g., 'Buy groceries', 'Call mom')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional longer description with details"
                        },
                        "due_date": {
                            "type": "string",
                            "description": "When the task is due. Supports: 'today', 'tomorrow', day names ('monday'), 'in 2 days', 'next week', or dates ('2024-01-15', '1/15')"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Task priority level"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for organization (e.g., ['work', 'meeting'])"
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "list_tasks",
                "description": "Show the user's tasks. Use this when they ask about their to-do list, what they need to do, or their schedule.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "enum": ["all", "today", "overdue", "upcoming", "high_priority"],
                            "description": "Which tasks to show"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return"
                        }
                    }
                }
            },
            {
                "name": "complete_task",
                "description": "Mark a task as completed. Use this when the user says they finished something or want to check off a task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "The ID of the task to complete"
                        },
                        "search": {
                            "type": "string",
                            "description": "Search for task by title if ID not known"
                        }
                    }
                }
            },
            {
                "name": "update_task",
                "description": "Update an existing task's details. Use when user wants to change a task's title, due date, priority, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "The ID of the task to update"
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "due_date": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"]
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "delete_task",
                "description": "Delete a task. Use when user wants to remove something from their list entirely.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "The ID of the task to delete"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_stats",
                "description": "Get statistics about the user's tasks. Use when they ask about their productivity or task completion rates.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "search_tasks",
                "description": "Search tasks by keyword. Use when user asks about a specific task but doesn't know the ID.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term to find in task titles or descriptions"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a task tool by name.

        Args:
            name: Tool name (e.g., "add_task", "complete_task")
            arguments: Tool arguments as dict

        Returns:
            Human-readable result string
        """
        handlers = {
            "add_task": self._handle_add_task,
            "list_tasks": self._handle_list_tasks,
            "complete_task": self._handle_complete_task,
            "update_task": self._handle_update_task,
            "delete_task": self._handle_delete_task,
            "task_stats": self._handle_task_stats,
            "search_tasks": self._handle_search_tasks,
        }

        handler = handlers.get(name)
        if not handler:
            return f"Unknown tool: {name}"

        try:
            return await handler(arguments)
        except Exception as e:
            return f"Error: {str(e)}"

    async def _handle_add_task(self, args: Dict[str, Any]) -> str:
        """Handle add_task tool call."""
        title = args.get("title", "").strip()
        if not title:
            return "Please provide a task title."

        description = args.get("description", "")
        priority = parse_priority(args.get("priority", "medium"))
        tags = args.get("tags", [])

        due_date = None
        if args.get("due_date"):
            due_date = parse_due_date(args["due_date"])
            if not due_date:
                return f"I couldn't understand the due date '{args['due_date']}'. Try 'today', 'tomorrow', a day name, or a date like '1/15'."

        task = self.store.add_task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags,
        )

        # Format response
        response = f"Added task #{task.id}: {task.title}"
        if task.due_date:
            response += f" (due {task._format_due_date()})"
        if task.priority != TaskPriority.MEDIUM:
            response += f" [{task.priority.value}]"

        return response

    async def _handle_list_tasks(self, args: Dict[str, Any]) -> str:
        """Handle list_tasks tool call."""
        filter_type = args.get("filter", "all")
        limit = args.get("limit", 10)

        if filter_type == "today":
            tasks = self.store.get_today_tasks()
            header = "Tasks due today"
        elif filter_type == "overdue":
            tasks = self.store.get_overdue_tasks()
            header = "Overdue tasks"
        elif filter_type == "upcoming":
            tasks = self.store.get_upcoming_tasks(days=7)
            header = "Upcoming tasks (next 7 days)"
        elif filter_type == "high_priority":
            tasks = self.store.get_high_priority_tasks()
            header = "High priority tasks"
        else:
            tasks = self.store.list_tasks(limit=limit)
            header = "All active tasks"

        if not tasks:
            return f"No {filter_type} tasks found."

        lines = [f"{header}:"]
        for task in tasks[:limit]:
            line = f"  #{task.id} {task.title}"
            if task.due_date:
                if task.is_overdue:
                    line += f" (OVERDUE: {task._format_due_date()})"
                elif task.is_due_today:
                    line += " (due TODAY)"
                else:
                    line += f" (due {task._format_due_date()})"
            if task.priority in (TaskPriority.HIGH, TaskPriority.URGENT):
                line += f" [{task.priority.value.upper()}]"
            lines.append(line)

        return "\n".join(lines)

    async def _handle_complete_task(self, args: Dict[str, Any]) -> str:
        """Handle complete_task tool call."""
        task_id = args.get("task_id")
        search = args.get("search", "").strip()

        if not task_id and search:
            # Search for task
            tasks = self.store.search_tasks(search, limit=1)
            if not tasks:
                return f"No task found matching '{search}'"
            task_id = tasks[0].id

        if not task_id:
            return "Please provide a task ID or search term."

        task = self.store.complete_task(task_id)
        if not task:
            return f"Task #{task_id} not found."

        # Award XP and update mood
        xp_earned = task.xp_reward
        response = f"Completed: {task.title} (+{xp_earned} XP)"

        if self.personality:
            self.personality.add_xp(xp_earned, source="task_completion")
            # Completing tasks makes us happy!
            from .personality import Mood
            self.personality.mood.set_mood(Mood.HAPPY, 0.6)

        return response

    async def _handle_update_task(self, args: Dict[str, Any]) -> str:
        """Handle update_task tool call."""
        task_id = args.get("task_id")
        if not task_id:
            return "Please provide a task ID."

        due_date = None
        if args.get("due_date"):
            due_date = parse_due_date(args["due_date"])

        priority = None
        if args.get("priority"):
            priority = parse_priority(args["priority"])

        task = self.store.update_task(
            task_id=task_id,
            title=args.get("title"),
            description=args.get("description"),
            due_date=due_date,
            priority=priority,
        )

        if not task:
            return f"Task #{task_id} not found."

        return f"Updated task #{task.id}: {task.title}"

    async def _handle_delete_task(self, args: Dict[str, Any]) -> str:
        """Handle delete_task tool call."""
        task_id = args.get("task_id")
        if not task_id:
            return "Please provide a task ID."

        task = self.store.get_task(task_id)
        if not task:
            return f"Task #{task_id} not found."

        title = task.title
        self.store.delete_task(task_id)
        return f"Deleted task: {title}"

    async def _handle_task_stats(self, args: Dict[str, Any]) -> str:
        """Handle task_stats tool call."""
        stats = self.store.get_stats()

        lines = [
            "Task Statistics:",
            f"  Total tasks: {stats['total']}",
            f"  Pending: {stats['pending']}",
            f"  Completed: {stats['completed']}",
            f"  Overdue: {stats['overdue']}",
            f"  Due today: {stats['due_today']}",
            f"  30-day completion rate: {stats['completion_rate_30d']}%",
        ]

        return "\n".join(lines)

    async def _handle_search_tasks(self, args: Dict[str, Any]) -> str:
        """Handle search_tasks tool call."""
        query = args.get("query", "").strip()
        if not query:
            return "Please provide a search term."

        tasks = self.store.search_tasks(query)
        if not tasks:
            return f"No tasks found matching '{query}'"

        lines = [f"Tasks matching '{query}':"]
        for task in tasks[:10]:
            status = "DONE" if task.status == TaskStatus.COMPLETED else ""
            line = f"  #{task.id} {task.title}"
            if status:
                line += f" [{status}]"
            lines.append(line)

        return "\n".join(lines)


# ========== Built-in Task Tools for MCP Server ==========

def get_builtin_task_tools(task_store: TaskStore, personality=None) -> 'TaskTools':
    """
    Create a TaskTools instance with built-in tools.

    This can be exposed as a local MCP server for AI tool use.
    """
    return TaskTools(task_store, personality)


def task_tools_to_mcp_format(task_tools: TaskTools) -> List[Dict[str, Any]]:
    """
    Convert TaskTools definitions to MCP server format.

    This allows the tools to be registered with MCPClientManager.
    """
    definitions = task_tools.get_tool_definitions()

    mcp_tools = []
    for defn in definitions:
        mcp_tools.append({
            "name": defn["name"],
            "description": f"[tasks] {defn['description']}",
            "inputSchema": defn["input_schema"],
        })

    return mcp_tools
