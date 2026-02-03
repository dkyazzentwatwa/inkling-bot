# Task Manager + AI Companion Implementation

## Overview

This document describes the implementation of task management features for Inkling, turning it into an AI companion that helps you stay productive while maintaining its personality-driven charm.

## ✅ What's Been Implemented

### 1. Core Task Management (`core/tasks.py`)

**Task Model:**
```python
@dataclass
class Task:
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus  # pending, in_progress, completed, cancelled
    priority: Priority  # low, medium, high, urgent
    created_at: float
    due_date: Optional[float]
    completed_at: Optional[float]

    # AI companion integration
    mood_on_creation: Optional[str]
    celebration_level: float

    # MCP integration
    mcp_tool: Optional[str]
    mcp_params: Optional[Dict]
    mcp_result: Optional[str]

    # Organization
    tags: List[str]
    project: Optional[str]

    # Time tracking
    estimated_minutes: Optional[int]
    actual_minutes: int

    # Subtasks
    subtasks: List[str]
    subtasks_completed: List[bool]
```

**TaskManager Class:**
- SQLite storage (`~/.inkling/tasks.db`)
- CRUD operations: create, get, update, delete
- Filtering: by status, project, tags, priority
- Smart queries: overdue tasks, due soon, statistics
- Completion tracking with streaks

### 2. MCP Tool Server (`mcp_servers/tasks.py`)

**6 AI-accessible tools:**

1. **task_create** - Create new tasks
   - Input: title, description, priority, due_in_days, tags, project
   - Output: Created task with ID

2. **task_list** - List tasks with filters
   - Input: status, project, tags, limit
   - Output: Array of tasks

3. **task_complete** - Mark task as done
   - Input: task_id
   - Output: Updated task with completion time

4. **task_update** - Update task details
   - Input: task_id, fields to update
   - Output: Updated task

5. **task_delete** - Delete a task
   - Input: task_id
   - Output: Success status

6. **task_stats** - Get statistics
   - Output: Total, pending, completed, overdue, completion rate

**Usage:** The AI can now use these tools to manage tasks autonomously!

### 3. Personality Integration

**New XP Sources (in `core/progression.py`):**
```python
TASK_CREATED = +5 XP
TASK_COMPLETED_LOW = +10 XP
TASK_COMPLETED_MEDIUM = +15 XP
TASK_COMPLETED_HIGH = +25 XP
TASK_COMPLETED_URGENT = +40 XP
TASK_ON_TIME_BONUS = +10 XP
TASK_STREAK_3 = +15 XP
TASK_STREAK_7 = +30 XP
```

**Event Handler (in `core/personality.py`):**
```python
def on_task_event(event_type, task_data) -> Dict:
    # Returns: {xp_awarded, message}
    # Events: task_created, task_completed, task_started, task_overdue
```

**Mood Reactions:**
- **Task Created (Urgent):** Intensity increases, "I feel the urgency! 💪"
- **Task Created (Fun):** Mood → Excited, "Ooh this sounds fun! 🎉"
- **Task Completed (High Priority):** Mood → Grateful, "Phew! Thanks for handling that 🙏"
- **Task Completed (Normal):** Mood → Happy, "+15 XP ✨"
- **Task Overdue (Lonely mood):** "Hey... wanna work on 'X' together?"

### 4. Command Registry (`core/commands.py`)

**New commands added:**
```
/tasks       - List all tasks
/task <args> - Show or create a task
/done <id>   - Mark task as complete
/taskstats   - Show task statistics
```

Commands are available in both SSH and web modes.

### 5. Integration with Main App (`main.py`)

- `TaskManager` initialized during startup
- Available to all modes (SSH, web)
- Integrated with personality system for XP/mood

### 6. Configuration (`config.yml`)

**New MCP server entry:**
```yaml
mcp:
  enabled: false  # Set to true to enable
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

---

## 🔄 How Multi-Step Actions Work

### Current Brain Implementation

The `Brain` class supports **multi-step tool execution** (up to 5 rounds by default):

```python
# In brain.py (lines 582-587)
tool_round = 0
while result.is_tool_use and tool_round < max_tool_rounds:
    tool_round += 1
    result = await self._execute_tools_and_continue(
        provider, system_prompt, result, tools, status_callback
    )
```

### Example Multi-Step Workflow

**User says:** "Create a GitHub issue for fixing the login bug and add it to my tasks"

**AI orchestration:**

```
Round 1:
  AI thinks: I need to create a GitHub issue first
  Tool call: github_create_issue(title="Fix login bug", ...)
  Result: {"url": "https://github.com/user/repo/issues/123"}

Round 2:
  AI receives: Issue created at #123
  AI thinks: Now I should create a task with this info
  Tool call: task_create(
    title="Fix login bug",
    description="GitHub issue #123: https://...",
    priority="high",
    tags=["bug", "github"]
  )
  Result: {"success": true, "task": {...}}

Round 3:
  AI receives: Task created
  AI thinks: I have everything I need
  No more tool calls
  Response: "✅ Created issue #123 and added to your tasks!"
```

**UI feedback during execution:**
```
Display updates in real-time:
  (⊙_⊙) Using github_create_issue...
  (⌐■_■) github_create_issue complete
  (⊙_⊙) Using task_create...
  (⌐■_■) task_create complete
  ✅ Created issue #123 and added to your tasks!
```

---

## 📋 What Still Needs Implementation

### 1. Command Handlers (modes/ssh_chat.py and modes/web_chat.py)

Add these methods to both SSH and Web chat modes:

```python
async def cmd_tasks(self, args: str = ""):
    """List tasks with optional filters."""
    # Parse args for status/project filters
    tasks = self.inkling.task_manager.list_tasks(...)

    # Format and display tasks
    for task in tasks:
        print(f"[{task.id[:8]}] {task.title} - {task.priority.value}")

    # Update display if available

async def cmd_task(self, args: str):
    """Create or show a task."""
    if not args:
        # Show help
        return

    # If args is a task ID, show details
    if len(args) == 36:  # UUID format
        task = self.inkling.task_manager.get_task(args)
        # Display task details
    else:
        # Create new task
        task = self.inkling.task_manager.create_task(
            title=args,
            mood=self.inkling.personality.mood.current.value
        )

        # Trigger personality event
        result = self.inkling.personality.on_task_event(
            "task_created",
            {"priority": "medium", "title": args}
        )

        if result and result.get('message'):
            print(result['message'])

async def cmd_done(self, task_id: str):
    """Complete a task."""
    task = self.inkling.task_manager.complete_task(task_id)

    if not task:
        print("Task not found")
        return

    # Calculate if on-time
    was_on_time = (
        not task.due_date or
        task.completed_at <= task.due_date
    )

    # Trigger personality event
    result = self.inkling.personality.on_task_event(
        "task_completed",
        {
            "priority": task.priority.value,
            "title": task.title,
            "was_on_time": was_on_time
        }
    )

    if result:
        print(result.get('message', 'Task completed!'))
        if 'xp_awarded' in result:
            print(f"+{result['xp_awarded']} XP")

async def cmd_taskstats(self):
    """Show task statistics."""
    stats = self.inkling.task_manager.get_stats()

    print(f"""
Task Statistics:
  Total: {stats['total']}
  Pending: {stats['pending']}
  In Progress: {stats['in_progress']}
  Completed: {stats['completed']}
  Overdue: {stats['overdue']}
  Due Soon: {stats['due_soon']}

  30-Day Completion Rate: {stats['completion_rate_30d']:.1%}
    """)
```

### 2. Web UI Task Page (`modes/web_chat.py`)

Add these routes:

```python
@app.route('/tasks')
def tasks_page():
    """Render task management page."""
    return template(TASKS_HTML_TEMPLATE)

@app.route('/api/tasks', method='GET')
def api_tasks_list():
    """Get all tasks."""
    status_filter = request.query.get('status')
    project_filter = request.query.get('project')

    if status_filter:
        status = TaskStatus(status_filter)
    else:
        status = None

    tasks = inkling.task_manager.list_tasks(
        status=status,
        project=project_filter
    )

    return {
        'tasks': [task.to_dict() for task in tasks]
    }

@app.route('/api/tasks', method='POST')
def api_tasks_create():
    """Create a new task."""
    data = request.json

    task = inkling.task_manager.create_task(
        title=data['title'],
        description=data.get('description'),
        priority=Priority(data.get('priority', 'medium')),
        mood=inkling.personality.mood.current.value,
        tags=data.get('tags', []),
        project=data.get('project')
    )

    # Trigger personality event
    result = inkling.personality.on_task_event(
        "task_created",
        {"priority": task.priority.value, "title": task.title}
    )

    return {
        'task': task.to_dict(),
        'celebration': result.get('message') if result else None
    }

@app.route('/api/tasks/<task_id>/complete', method='POST')
def api_tasks_complete(task_id):
    """Mark task as complete."""
    task = inkling.task_manager.complete_task(task_id)

    if not task:
        response.status = 404
        return {'error': 'Task not found'}

    was_on_time = (
        not task.due_date or
        task.completed_at <= task.due_date
    )

    result = inkling.personality.on_task_event(
        "task_completed",
        {
            "priority": task.priority.value,
            "title": task.title,
            "was_on_time": was_on_time
        }
    )

    return {
        'task': task.to_dict(),
        'celebration': result.get('message') if result else None,
        'xp_awarded': result.get('xp_awarded') if result else 0
    }
```

**HTML Template (Kanban-style):**

Create a simple task board with three columns:
- To Do (pending tasks)
- In Progress
- Done Today (completed today)

Include face animation and celebration messages when tasks are completed.

### 3. Heartbeat Task Reminders (`core/heartbeat.py`)

Add these proactive behaviors:

```python
async def remind_overdue_tasks(inkling):
    """Remind about overdue tasks."""
    tasks = inkling.task_manager.get_overdue_tasks()

    if not tasks:
        return None

    task = random.choice(tasks)

    result = inkling.personality.on_task_event(
        "task_overdue",
        {"title": task.title}
    )

    return result.get('message') if result else None

async def suggest_next_task(inkling):
    """Suggest a task based on current mood and time."""
    mood = inkling.personality.mood.current

    # Match tasks to mood
    if mood == Mood.CURIOUS:
        tasks = inkling.task_manager.list_tasks(
            tags=["research", "learning"],
            limit=3
        )
    elif mood == Mood.SLEEPY:
        tasks = inkling.task_manager.list_tasks(limit=3)
        tasks = [t for t in tasks if t.priority == Priority.LOW]
    else:
        tasks = inkling.task_manager.list_tasks(
            status=TaskStatus.PENDING,
            limit=3
        )

    if tasks:
        task = tasks[0]
        return f"Feeling {mood.value}... how about: {task.title}?"

    return None

# Add to BEHAVIORS list in __init__:
ProactiveBehavior(
    name="remind_overdue",
    behavior_type=BehaviorType.MAINTENANCE,
    handler=remind_overdue_tasks,
    probability=0.7,
    cooldown_seconds=3600  # Once per hour
),
ProactiveBehavior(
    name="suggest_task",
    behavior_type=BehaviorType.MOOD_DRIVEN,
    handler=suggest_next_task,
    probability=0.3,
    cooldown_seconds=1800  # Every 30 minutes
),
```

---

## 🚀 Testing Multi-Step Task Creation

### Prerequisites

1. Enable MCP in `config.local.yml`:
   ```yaml
   mcp:
     enabled: true
     servers:
       tasks:
         command: "python"
         args: ["mcp_servers/tasks.py"]
   ```

2. Ensure you have an API key configured:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

### Test Cases

**Test 1: Simple Task Creation**
```
User: "Create a task to fix the login bug"

Expected:
  Round 1: AI calls task_create(title="Fix login bug", priority="medium")
  Response: "Got it! Added to our list ✓"
  XP: +5 XP awarded
```

**Test 2: Complex Multi-Step**
```
User: "Research React Server Components and create a high-priority task with a due date in 3 days"

Expected:
  Round 1: AI calls task_create(
    title="Research React Server Components",
    priority="high",
    due_in_days=3
  )
  Response: Mood → Curious, "Got it! Added to our list ✓"
  XP: +5 XP
```

**Test 3: List and Complete**
```
User: "Show me my tasks"
  Round 1: AI calls task_list()
  Response: Lists all pending tasks

User: "Mark the first one as done"
  Round 1: AI calls task_complete(task_id="...")
  Response: "Nicely done! +15 XP ✨"
  Mood → Happy
  XP: +15 XP (medium priority)
```

**Test 4: Multi-Tool Orchestration (with Composio)**
```
User: "Check my Google Calendar for tomorrow and create tasks for each meeting"

Expected:
  Round 1: AI calls composio_google_calendar_list(date="tomorrow")
  Round 2: AI calls task_create() for meeting 1
  Round 3: AI calls task_create() for meeting 2
  Round 4: AI calls task_create() for meeting 3
  Response: "Added 3 tasks from your calendar!"
```

### Debugging

Enable debug mode:
```bash
INKLING_DEBUG=1 python main.py --mode ssh
```

You'll see tool calls logged:
```
[Brain] Calling tool: task_create
[Brain] Tool result: {"success": true, "task": {...}}
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     User Input                          │
│  "Create a task to fix the login bug with high priority"│
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                  Brain (AI)                             │
│  • Analyzes intent                                      │
│  • Plans tool calls                                     │
│  • Max 5 rounds of tool execution                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Client Manager                         │
│  • Routes tool calls to servers                         │
│  • Collects results                                     │
│  • Returns to Brain                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┐
        ▼                     ▼              ▼
┌──────────────┐   ┌─────────────────┐   ┌──────────────┐
│ Task Server  │   │ Composio Server │   │ Other Servers│
│ (Built-in)   │   │ (HTTP)          │   │ (stdio)      │
└──────┬───────┘   └────────┬────────┘   └──────┬───────┘
       │                    │                   │
       ▼                    ▼                   ▼
┌──────────────┐   ┌─────────────────┐   ┌──────────────┐
│ TaskManager  │   │ External APIs   │   │ FS/Web/etc   │
│ (SQLite)     │   │ (Calendar, etc) │   │              │
└──────┬───────┘   └─────────────────┘   └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                  Personality System                     │
│  • on_task_event() → XP rewards                         │
│  • Mood transitions                                     │
│  • Celebration messages                                 │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                Display Manager                          │
│  • Show face expressions                                │
│  • Update UI with task progress                         │
│  • Real-time tool execution feedback                    │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Next Steps

1. **Implement command handlers** in `modes/ssh_chat.py` and `modes/web_chat.py`
2. **Create web UI** task page with Kanban board
3. **Add heartbeat reminders** for overdue tasks
4. **Test with MCP enabled** and verify multi-step workflows
5. **Add Composio integration** for external tool orchestration (Calendar, GitHub, etc.)
6. **Create task achievements** (e.g., "Task Master: Complete 50 tasks")
7. **Build task analytics** dashboard showing productivity trends

---

## 💡 Design Philosophy

**Keep the companion, add the structure:**

| Traditional Task Manager | Inkling Task Companion |
|--------------------------|------------------------|
| Cold reminder | "Hey friend, still thinking about that task?" |
| Neutral checkmark | "YES! 🎉 You did it! +15 XP" |
| Overdue in red | "I know you're busy... want to reschedule?" |
| Silent background | "Feeling energized? Perfect time for that challenging task!" |

The companion doesn't just track tasks—it **cares** about your productivity and emotional state.

---

## 📝 File Summary

**New Files:**
- `core/tasks.py` (491 lines) - Task model and manager
- `mcp_servers/tasks.py` (408 lines) - MCP tool server
- `TASK_MANAGER_IMPLEMENTATION.md` (this file)

**Modified Files:**
- `core/progression.py` - Added task XP sources
- `core/personality.py` - Added task event handler
- `core/commands.py` - Added task commands
- `main.py` - Integrated TaskManager
- `config.yml` - Added task MCP server example

**Total New Code:** ~900 lines

---

## 🔗 References

- MCP Protocol: https://modelcontextprotocol.io/
- Composio MCP: https://docs.composio.dev/mcp
- Brain tool execution: `core/brain.py:582-702`
- Personality system: `core/personality.py`
- Progression system: `core/progression.py`

---

**Created:** 2026-02-03
**Status:** Core implementation complete, UI/integration pending
**Branch:** `claude/task-manager-ai-companion-LqyIU`
