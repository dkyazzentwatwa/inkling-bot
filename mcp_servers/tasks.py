#!/usr/bin/env python3
"""
Inkling Task Manager MCP Server

Provides MCP tools for task management that can be used by the AI:
- task_create: Create a new task
- task_list: List tasks with filters
- task_complete: Mark a task as completed
- task_update: Update task details
- task_delete: Delete a task
- task_stats: Get task statistics

Usage:
    python mcp_servers/tasks.py

Configuration in config.yml:
    mcp:
      enabled: true
      servers:
        tasks:
          command: "python"
          args: ["mcp_servers/tasks.py"]
"""

import sys
import json
import os
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tasks import TaskManager, Task, TaskStatus, Priority


class TaskMCPServer:
    """MCP server for task management."""

    def __init__(self):
        self.task_manager = TaskManager()
        self.request_id = 0

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._initialize(request_id)
            elif method == "tools/list":
                return self._list_tools(request_id)
            elif method == "tools/call":
                return self._call_tool(request_id, params)
            else:
                return self._error(request_id, f"Unknown method: {method}")

        except Exception as e:
            return self._error(request_id, str(e))

    def _initialize(self, request_id: int) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "1.0",
                "serverInfo": {
                    "name": "inkling-tasks",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

    def _list_tools(self, request_id: int) -> Dict[str, Any]:
        """List available tools."""
        tools = [
            {
                "name": "task_create",
                "description": "Create a new task. Returns the created task with its ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Task title (required)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed task description"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Task priority (default: medium)"
                        },
                        "due_in_days": {
                            "type": "number",
                            "description": "Days until due date (e.g., 3 for 3 days from now)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of tags for organization"
                        },
                        "project": {
                            "type": "string",
                            "description": "Project name"
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "task_list",
                "description": "List tasks with optional filters. Returns array of tasks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                            "description": "Filter by status"
                        },
                        "project": {
                            "type": "string",
                            "description": "Filter by project"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags (must have ALL tags)"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of tasks to return"
                        }
                    }
                }
            },
            {
                "name": "task_complete",
                "description": "Mark a task as completed. Returns the updated task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to complete"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_update",
                "description": "Update task details. Returns the updated task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to update"
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"]
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "project": {"type": "string"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_delete",
                "description": "Delete a task. Returns success status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to delete"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_stats",
                "description": "Get task statistics (total, pending, completed, overdue, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }

    def _call_tool(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "task_create":
            result = self._tool_create(arguments)
        elif tool_name == "task_list":
            result = self._tool_list(arguments)
        elif tool_name == "task_complete":
            result = self._tool_complete(arguments)
        elif tool_name == "task_update":
            result = self._tool_update(arguments)
        elif tool_name == "task_delete":
            result = self._tool_delete(arguments)
        elif tool_name == "task_stats":
            result = self._tool_stats(arguments)
        else:
            return self._error(request_id, f"Unknown tool: {tool_name}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        }

    def _tool_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        import time

        # Parse priority
        priority_str = args.get("priority", "medium")
        priority = Priority(priority_str)

        # Calculate due date
        due_date = None
        if "due_in_days" in args:
            days = float(args["due_in_days"])
            due_date = time.time() + (days * 86400)

        task = self.task_manager.create_task(
            title=args["title"],
            description=args.get("description"),
            priority=priority,
            due_date=due_date,
            tags=args.get("tags", []),
            project=args.get("project")
        )

        return {
            "success": True,
            "task": self._task_to_dict(task)
        }

    def _tool_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List tasks."""
        # Parse status filter
        status = None
        if "status" in args:
            status = TaskStatus(args["status"])

        tasks = self.task_manager.list_tasks(
            status=status,
            project=args.get("project"),
            tags=args.get("tags"),
            limit=args.get("limit")
        )

        return {
            "success": True,
            "count": len(tasks),
            "tasks": [self._task_to_dict(t) for t in tasks]
        }

    def _tool_complete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Complete a task."""
        task = self.task_manager.complete_task(args["task_id"])

        if not task:
            return {"success": False, "error": "Task not found"}

        return {
            "success": True,
            "task": self._task_to_dict(task)
        }

    def _tool_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task."""
        task = self.task_manager.get_task(args["task_id"])

        if not task:
            return {"success": False, "error": "Task not found"}

        # Update fields
        if "title" in args:
            task.title = args["title"]
        if "description" in args:
            task.description = args["description"]
        if "priority" in args:
            task.priority = Priority(args["priority"])
        if "status" in args:
            task.status = TaskStatus(args["status"])
        if "tags" in args:
            task.tags = args["tags"]
        if "project" in args:
            task.project = args["project"]

        self.task_manager.update_task(task)

        return {
            "success": True,
            "task": self._task_to_dict(task)
        }

    def _tool_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a task."""
        deleted = self.task_manager.delete_task(args["task_id"])

        return {
            "success": deleted,
            "message": "Task deleted" if deleted else "Task not found"
        }

    def _tool_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get task statistics."""
        stats = self.task_manager.get_stats()

        return {
            "success": True,
            "stats": stats
        }

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task to JSON-serializable dict."""
        from datetime import datetime

        data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": datetime.fromtimestamp(task.created_at).isoformat(),
            "tags": task.tags,
            "project": task.project,
        }

        if task.due_date:
            data["due_date"] = datetime.fromtimestamp(task.due_date).isoformat()
            data["days_until_due"] = task.days_until_due
            data["is_overdue"] = task.is_overdue

        if task.completed_at:
            data["completed_at"] = datetime.fromtimestamp(task.completed_at).isoformat()

        if task.subtasks:
            data["subtasks"] = task.subtasks
            data["subtasks_completed"] = task.subtasks_completed
            data["completion_percentage"] = task.completion_percentage

        return data

    def _error(self, request_id: int, message: str) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": message
            }
        }

    def run(self):
        """Run the MCP server (stdio transport)."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                response = self.handle_request(request)

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except KeyboardInterrupt:
                break
            except Exception as e:
                # Log error to stderr
                print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    server = TaskMCPServer()
    server.run()
