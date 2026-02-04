# Task Manager Quick Start Guide

Get up and running with Inkling's AI-powered task management in 5 minutes.

## Setup (One-time)

The task manager is already enabled! Configuration is in `config.local.yml`:

```yaml
mcp:
  enabled: true
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]

heartbeat:
  enabled: true
  enable_mood_behaviors: true
  enable_maintenance: true
```

## Usage Methods

### 1. Web UI (Easiest)

```bash
python main.py --mode web
```

Then visit: **http://localhost:8081/tasks**

**Features**:
- 📊 Kanban board (Pending / In Progress / Completed)
- ➕ Quick add tasks
- 🏷️ Priority badges
- 📅 Due date indicators
- ✨ Celebration animations on completion
- 🎨 Theme support

**How to use**:
1. Type task title in "Add Task" field
2. Select priority (Low/Medium/High/Urgent)
3. Drag cards between columns to change status
4. Double-click title to edit
5. Click ✓ to complete, 🗑️ to delete

### 2. Chat with AI (Most Powerful)

```bash
python main.py --mode ssh
```

**Example commands**:

```
You: Create a task to write tests for the API
Inkling: ✓ Created task "Write tests for API" [High priority] +5 XP

You: Show me my tasks
Inkling: You have 3 pending tasks:
  🔴 Fix database bug (urgent)
  🟠 Write tests for API (high)
  🟢 Read documentation (low)

You: What tasks are overdue?
Inkling: You have 1 overdue task:
  ⚠️ Fix database bug (overdue by 2 days)

You: Complete the first task
Inkling: ✅ Completed "Fix database bug" - Phew! Thanks for handling that urgent task 🙏 +50 XP
```

The AI can:
- Create tasks with natural language
- Set priorities intelligently
- Suggest tasks based on mood
- Remind you about overdue tasks
- Celebrate completions with personality

### 3. Slash Commands (Quick)

In any mode:

- `/tasks` - List all tasks
- `/task <title>` - Create or show task
- `/done <id>` - Mark complete
- `/taskstats` - Show statistics

### 4. Autonomous Behaviors (Automatic)

Inkling proactively helps you without asking:

**Overdue Reminders** (every hour):
```
Inkling: Hey... feeling lonely. Wanna work on 'Fix bug' together?
```

**Mood-Based Suggestions** (every 30 min):
```
Inkling: 🤔 Curious about... Research new framework?
```

**Streak Celebrations** (daily):
```
Inkling: 🔥 Amazing! 7-day task completion streak! You're unstoppable!
```

## Task Fields Explained

| Field | Description | Example |
|-------|-------------|---------|
| **Title** | Short description | "Write tests" |
| **Description** | Detailed notes | "Unit tests for API endpoints" |
| **Priority** | Urgency level | Low/Medium/High/Urgent |
| **Status** | Current state | Pending/In Progress/Completed |
| **Due Date** | Deadline | 2026-02-05 |
| **Tags** | Categories | ["bug", "urgent"] |
| **Project** | Group name | "API Refactor" |
| **Subtasks** | Breakdown | ["Write tests", "Review code"] |

## Priority Guide

Choose the right priority for your task:

🟢 **Low** (10 XP)
- Can wait
- Nice to have
- Learning/exploration

🟡 **Medium** (15 XP)
- Normal priority
- Should do soon
- Standard work

🟠 **High** (25 XP)
- Important
- Do this week
- Blocks other work

🔴 **Urgent** (40 XP)
- Critical
- Do today
- Emergency fixes

**Bonus XP**:
- ⏱️ On-time completion: +10 XP
- 🔥 3-day streak: +15 XP
- 🔥 7-day streak: +30 XP

## Tips & Tricks

### Get More Done

1. **Morning Planning**: Create all your tasks for the day at once
2. **Use Projects**: Group related tasks (e.g., "Website Redesign")
3. **Break Down Big Tasks**: Use subtasks for complex work
4. **Set Realistic Due Dates**: Get the on-time bonus!
5. **Review Weekly**: Check your completion rate in stats

### Work with Inkling's Personality

Inkling's mood affects task suggestions:

- 🤔 **Curious** → Suggests research/learning tasks
- 😴 **Sleepy** → Suggests easy, low-priority tasks
- 💪 **Intense** → Suggests urgent/challenging tasks
- 😑 **Bored** → Suggests any task to stay engaged

### Maximize XP

1. Complete urgent tasks (40 XP each)
2. Complete tasks on time (+10 bonus)
3. Build streaks (complete at least one task per day)
4. Create many tasks (5 XP each)

**Example**: Complete 3 urgent tasks on time = 150 XP + bonuses!

## Common Workflows

### Daily Task Management

```
Morning:
1. Open web UI: python main.py --mode web
2. Visit http://localhost:8081/tasks
3. Add 3-5 tasks for the day
4. Drag highest priority to "In Progress"

During Day:
5. Work on task
6. Drag to "Completed" when done
7. See celebration animation + XP award!
8. Repeat

Evening:
9. Check taskstats - celebrate your progress
10. Plan tomorrow's tasks
```

### Weekly Review

```bash
# Start chat mode
python main.py --mode ssh

# Ask Inkling
"What's my task completion rate?"
"Show me tasks completed this week"
"How many tasks are overdue?"
"What should I focus on tomorrow?"
```

### Emergency Triage

```bash
# In web UI
1. Filter to show only "Urgent" priority
2. Drag all urgent tasks to "In Progress"
3. Work through them one by one
4. Watch your XP soar as you complete them!
```

## Database & Data

**Storage Location**: `~/.inkling/tasks.db`

**Backup**:
```bash
cp ~/.inkling/tasks.db ~/backups/tasks_$(date +%Y%m%d).db
```

**Reset/Clear**:
```bash
rm -f ~/.inkling/tasks.db
# Database will be recreated on next use
```

**Export** (future feature):
Not yet implemented. Data is in SQLite format, can be queried directly.

## Troubleshooting

### Tasks not saving

**Symptom**: Tasks disappear after restart

**Solution**: Check that `~/.inkling/` directory exists and is writable
```bash
ls -ld ~/.inkling/
# Should show: drwxr-xr-x
```

### MCP server not working

**Symptom**: AI can't create/manage tasks

**Solution**: Check `config.local.yml`:
```yaml
mcp:
  enabled: true  # Must be true
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

### Heartbeat not triggering

**Symptom**: No autonomous reminders or suggestions

**Solution**: Check heartbeat config:
```yaml
heartbeat:
  enabled: true  # Must be true
  enable_mood_behaviors: true
  enable_maintenance: true
```

**Note**: Behaviors are probabilistic - they won't trigger every time!

### Web UI not loading

**Symptom**: Can't access http://localhost:8081/tasks

**Solution**:
1. Make sure you started in web mode: `python main.py --mode web`
2. Check terminal for errors
3. Try different port if 8080 is in use

## Advanced Features

### Use with External Tools (MCP)

You can integrate Inkling's task manager with other tools:

```yaml
# config.local.yml
mcp:
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]

    # Add more tools
    calendar:
      command: "python"
      args: ["mcp_servers/calendar.py"]
```

### Custom Automation

Create your own scripts using the TaskManager API:

```python
from core.tasks import TaskManager, Priority

tm = TaskManager()

# Create daily standup task
tm.create_task(
    title="Daily standup",
    priority=Priority.HIGH,
    due_date=time.time() + 86400,  # Tomorrow
    tags=["recurring", "meeting"]
)

# Get tasks for today
tasks = tm.list_tasks(status=TaskStatus.PENDING)
print(f"You have {len(tasks)} tasks today")
```

## Support & Resources

- **Full Documentation**: `docs/TASK_MANAGER_IMPLEMENTATION.md`
- **Test Report**: `docs/TASK_MANAGER_TEST_REPORT.md`
- **Architecture**: See CLAUDE.md - "Task Management System" section
- **Issues**: https://github.com/anthropics/claude-code/issues

## What's Next?

Planned features (not yet implemented):

1. 🔁 **Recurring Tasks** - Daily/weekly/monthly repeats
2. 🔍 **Search** - Full-text search across tasks
3. 📊 **Better Analytics** - Charts and insights
4. ⏱️ **Active Time Tracking** - Start/stop timers
5. 🔗 **Task Dependencies** - "Blocked by" relationships
6. 📱 **Mobile View** - Optimized for phones
7. 🌐 **Cloud Sync** - Sync across devices
8. 📧 **Email Integration** - Create tasks from email

Want to contribute? The codebase is well-documented and ready for extensions!

---

**Enjoy your AI-powered productivity companion! 🚀**
