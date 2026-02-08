"""Task management commands."""
import re
from typing import Dict, Any

from core.tasks import Task, TaskStatus, Priority
from . import CommandHandler


class TaskCommands(CommandHandler):
    """Handlers for task commands (/tasks, /task, /done, /cancel, /delete, /taskstats)."""

    def tasks(self, args: str = "") -> Dict[str, Any]:
        """List tasks with optional filters."""
        if not self.task_manager:
            return {
                "response": "Task manager not available.",
                "error": True
            }

        # Parse arguments for filters
        status_filter = None
        if args:
            args_lower = args.lower()
            if "pending" in args_lower:
                status_filter = TaskStatus.PENDING
            elif "progress" in args_lower or "in-progress" in args_lower:
                status_filter = TaskStatus.IN_PROGRESS
            elif "done" in args_lower or "completed" in args_lower:
                status_filter = TaskStatus.COMPLETED

        # Get tasks
        tasks = self.task_manager.list_tasks(
            status=status_filter
        )

        if not tasks:
            return {
                "response": "No tasks found. Use the Tasks page to create tasks, or /task <title> to create via chat.",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        # Priority icons
        priority_icons = {
            Priority.LOW: "○",
            Priority.MEDIUM: "●",
            Priority.HIGH: "●●",
            Priority.URGENT: "‼",
        }

        # Format tasks list
        response = "TASKS\n\n"
        for task in tasks:
            # Status emoji
            if task.status == TaskStatus.COMPLETED:
                status_emoji = "✅"
            elif task.status == TaskStatus.IN_PROGRESS:
                status_emoji = "⏳"
            else:
                status_emoji = "□"

            # Priority icon
            priority_icon = priority_icons.get(task.priority, "●")

            # Overdue indicator
            overdue = " [OVERDUE]" if task.is_overdue else ""

            response += f"{status_emoji} {priority_icon} [{task.id[:8]}] {task.title}{overdue}\n"
            if task.description:
                response += f"   {task.description[:60]}{'...' if len(task.description) > 60 else ''}\n"

        response += f"\nTotal: {len(tasks)} tasks"
        if status_filter:
            response += f" ({status_filter.value})"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def task(self, args: str) -> Dict[str, Any]:
        """Create or show a task."""
        if not self.task_manager:
            return {"response": "Task manager not available.", "error": True}

        if not args:
            return {
                "response": "Usage:\n  /task <title>           - Create a new task\n  /task <id>              - Show task details\n  /task <title> !high     - Create high-priority task\n  /task <title> #tag      - Create task with tag",
                "face": self._get_face_str(),
            }

        # Check if it's a task ID (8 or 36 characters UUID)
        if len(args) in [8, 36] and "-" in args or args.count("-") >= 3:
            # Show task details
            task = self.task_manager.get_task(args)
            if not task:
                # Try to find by partial ID
                all_tasks = self.task_manager.list_tasks()
                matching = [t for t in all_tasks if t.id.startswith(args)]
                if len(matching) == 1:
                    task = matching[0]
                elif len(matching) > 1:
                    resp = f"Multiple tasks match '{args}'. Be more specific:\n"
                    for t in matching[:5]:
                        resp += f"  {t.id[:16]} - {t.title}\n"
                    return {"response": resp, "error": True}
                else:
                    return {"response": f"Task not found: {args}", "error": True}

            return self._format_task_details(task)

        # Create new task - parse priority and tags
        title = args
        priority = Priority.MEDIUM
        tags = []

        # Extract priority markers
        if "!urgent" in args.lower() or "!!" in args:
            priority = Priority.URGENT
            title = title.replace("!urgent", "").replace("!!", "").strip()
        elif "!high" in args.lower() or "!" in args:
            priority = Priority.HIGH
            title = title.replace("!high", "").replace("!", "").strip()
        elif "!low" in args.lower():
            priority = Priority.LOW
            title = title.replace("!low", "").strip()

        # Extract tags (#tag)
        tag_matches = re.findall(r'#(\w+)', title)
        tags.extend(tag_matches)
        title = re.sub(r'#\w+', '', title).strip()

        if not title:
            return {"response": "Task title cannot be empty", "error": True}

        # Create task
        task = self.task_manager.create_task(
            title=title,
            priority=priority,
            mood=self.personality.mood.current.value,
            tags=tags
        )

        # Trigger personality event
        result = self.personality.on_task_event(
            "task_created",
            {"priority": task.priority.value, "title": task.title}
        )

        # Format response
        response = f"✓ Task created!\n\n"
        response += f"**{task.title}**\n"
        response += f"ID: `{task.id[:8]}`\n"
        response += f"Priority: {task.priority.value}\n"
        if tags:
            response += f"Tags: #{', #'.join(tags)}\n"

        if result and result.get('xp_awarded'):
            response += f"\n+{result['xp_awarded']} XP"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def done(self, args: str) -> Dict[str, Any]:
        """Mark a task as complete."""
        if not self.task_manager:
            return {"response": "Task manager not available.", "error": True}

        if not args:
            return {
                "response": "Usage: /done <task_id>\n\nUse '/tasks' to see task IDs",
                "error": True
            }

        # Find task
        task = self.task_manager.get_task(args)
        if not task:
            # Try partial match
            all_tasks = self.task_manager.list_tasks()
            matching = [t for t in all_tasks if t.id.startswith(args)]
            if len(matching) == 1:
                task = matching[0]
            elif len(matching) > 1:
                resp = f"Multiple tasks match. Be more specific:\n"
                for t in matching[:5]:
                    resp += f"  {t.id[:16]} - {t.title}\n"
                return {"response": resp, "error": True}
            else:
                return {"response": f"Task not found: {args}", "error": True}

        if task.status == TaskStatus.COMPLETED:
            return {
                "response": "Task already completed!",
                "face": self._get_face_str(),
            }

        # Complete the task
        task = self.task_manager.complete_task(task.id)

        # Calculate if on-time
        was_on_time = (
            not task.due_date or
            task.completed_at <= task.due_date
        )

        # Trigger personality event
        result = self.personality.on_task_event(
            "task_completed",
            {
                "priority": task.priority.value,
                "title": task.title,
                "was_on_time": was_on_time
            }
        )

        # Format celebration
        celebration = result.get('message', 'Task completed!') if result else 'Task completed!'
        response = f"✓ {celebration}\n\n**{task.title}**\n"

        if result and result.get('xp_awarded'):
            xp = result['xp_awarded']
            response += f"\n✨ +{xp} XP earned!"

        # Show level info
        level = self.personality.progression.level
        xp_current = self.personality.progression.xp
        response += f"\n\nLevel {level} | {xp_current} XP"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def cancel(self, args: str) -> Dict[str, Any]:
        """Cancel a task."""
        if not self.task_manager:
            return {"response": "Task manager not available.", "error": True}

        if not args:
            return {
                "response": "Usage: /cancel <task_id>\n\nUse '/tasks' to see task IDs",
                "error": True
            }

        # Find task
        task = self.task_manager.get_task(args)
        if not task:
            # Try partial match
            all_tasks = self.task_manager.list_tasks()
            matching = [t for t in all_tasks if t.id.startswith(args)]
            if len(matching) == 1:
                task = matching[0]
            elif len(matching) > 1:
                resp = f"Multiple tasks match. Be more specific:\n"
                for t in matching[:5]:
                    resp += f"  {t.id[:16]} - {t.title}\n"
                return {"response": resp, "error": True}
            else:
                return {"response": f"Task not found: {args}", "error": True}

        if task.status == TaskStatus.CANCELLED:
            return {
                "response": "Task already cancelled!",
                "face": self._get_face_str(),
            }

        # Cancel the task
        task.status = TaskStatus.CANCELLED
        self.task_manager.update_task(task)

        return {
            "response": f"✗ Task cancelled\n\n**{task.title}**",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def delete(self, args: str) -> Dict[str, Any]:
        """Delete a task permanently."""
        if not self.task_manager:
            return {"response": "Task manager not available.", "error": True}

        if not args:
            return {
                "response": "Usage: /delete <task_id>\n\nUse '/tasks' to see task IDs\n\n**WARNING: This permanently deletes the task!**",
                "error": True
            }

        # Find task
        task = self.task_manager.get_task(args)
        if not task:
            # Try partial match
            all_tasks = self.task_manager.list_tasks()
            matching = [t for t in all_tasks if t.id.startswith(args)]
            if len(matching) == 1:
                task = matching[0]
            elif len(matching) > 1:
                resp = f"Multiple tasks match. Be more specific:\n"
                for t in matching[:5]:
                    resp += f"  {t.id[:16]} - {t.title}\n"
                return {"response": resp, "error": True}
            else:
                return {"response": f"Task not found: {args}", "error": True}

        # Delete the task
        success = self.task_manager.delete_task(task.id)

        if success:
            return {
                "response": f"🗑 Task deleted permanently\n\n**{task.title}**",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }
        else:
            return {"response": "Failed to delete task", "error": True}

    def taskstats(self) -> Dict[str, Any]:
        """Show task statistics."""
        if not self.task_manager:
            return {
                "response": "Task manager not available.",
                "error": True
            }

        stats = self.task_manager.get_stats()

        response = "TASK STATISTICS\n\n"
        response += f"Overview:\n"
        response += f"  Total tasks:     {stats['total']}\n"
        response += f"  Pending:         {stats['pending']}\n"
        response += f"  In Progress:     {stats['in_progress']}\n"
        response += f"  Completed:       {stats['completed']}\n"

        if stats['overdue'] > 0:
            response += f"  ⚠️ Overdue:       {stats['overdue']}\n"

        if stats['due_soon'] > 0:
            response += f"  ⏰ Due soon (3d): {stats['due_soon']}\n"

        # 30-day completion rate
        completion_rate = stats['completion_rate_30d'] * 100
        response += f"\n30-Day Performance:\n"
        response += f"  Completion rate: {completion_rate:.0f}%\n"

        # Level and XP info
        level = self.personality.progression.level
        xp = self.personality.progression.xp
        streak = self.personality.progression.current_streak

        response += f"\nProgression:\n"
        response += f"  Level {level} | {xp} XP\n"

        if streak > 0:
            streak_emoji = "🔥" if streak >= 7 else "✨"
            response += f"  {streak_emoji} {streak} day streak\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _format_task_details(self, task: Task) -> Dict[str, Any]:
        """Format detailed task information."""
        from datetime import datetime

        response = "**TASK DETAILS**\n\n"
        response += f"**{task.title}**\n\n"
        response += f"ID: `{task.id}`\n"

        if task.description:
            response += f"Details: {task.description}\n"

        response += f"Status: {task.status.value}\n"
        response += f"Priority: {task.priority.value}\n"

        if task.due_date:
            due_str = datetime.fromtimestamp(task.due_date).strftime("%Y-%m-%d %H:%M")
            days_until = task.days_until_due
            if task.is_overdue:
                response += f"Due: **{due_str}** (OVERDUE by {abs(days_until)} days)\n"
            elif days_until is not None and days_until <= 3:
                response += f"Due: **{due_str}** ({days_until} days)\n"
            else:
                response += f"Due: {due_str}\n"

        if task.tags:
            response += f"Tags: #{', #'.join(task.tags)}\n"

        if task.project:
            response += f"Project: {task.project}\n"

        if task.subtasks:
            response += f"Subtasks: {sum(task.subtasks_completed)}/{len(task.subtasks)} complete\n"
            for i, subtask in enumerate(task.subtasks):
                status = "✓" if task.subtasks_completed[i] else "□"
                response += f"  {status} {subtask}\n"

        created = datetime.fromtimestamp(task.created_at).strftime("%Y-%m-%d %H:%M")
        response += f"Created: {created}\n"

        if task.completed_at:
            completed = datetime.fromtimestamp(task.completed_at).strftime("%Y-%m-%d %H:%M")
            response += f"Completed: {completed}\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }
