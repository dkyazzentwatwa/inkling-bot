# Task Management Guide

Inkling includes a full-featured task management system with AI companion integration, XP rewards, and a visual Kanban board.

## Overview

The task system provides:
- **SQLite storage**: Local, private, no cloud dependency
- **AI integration**: Create and manage tasks through conversation
- **XP rewards**: Earn experience for completing tasks
- **Kanban board**: Visual web interface for task management
- **Slash commands**: Quick task operations from chat

## Quick Start

### Create a Task

```bash
> /task Buy groceries
# Creates: "Buy groceries" with medium priority

> /task Fix bug in login page
# Creates: "Fix bug in login page"
```

### List Tasks

```bash
> /tasks
# Shows all pending and in-progress tasks

> /tasks completed
# Shows completed tasks
```

### Complete a Task

```bash
> /done abc123
# Marks task abc123 as complete
# Awards XP based on priority!

> /done ab
# Partial ID matching - finds task starting with "ab"
```

### Cancel or Delete

```bash
> /cancel abc123
# Cancels task (keeps record, no XP)

> /delete abc123
# Permanently removes task
```

## Task Properties

### Status

| Status | Description | Icon |
|--------|-------------|------|
| `pending` | Not started | ⬜ |
| `in_progress` | Currently working on | 🔄 |
| `completed` | Done! | ✅ |
| `cancelled` | Cancelled (kept for records) | ❌ |

### Priority

| Priority | XP Reward | Use For |
|----------|-----------|---------|
| `low` | 10 XP | Nice-to-have, someday |
| `medium` | 15 XP | Standard tasks (default) |
| `high` | 25 XP | Important, needs attention |
| `urgent` | 40 XP | Critical, do immediately |

### Due Dates

Tasks can have optional due dates:
- **Overdue**: Past due date, not completed
- **Due Soon**: Within 3 days
- **On-Time Bonus**: +10 XP for completing before due date

## Slash Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/tasks` | List all tasks | `/tasks` |
| `/tasks <filter>` | Filter by status | `/tasks completed` |
| `/task <title>` | Create new task | `/task Buy milk` |
| `/task <id>` | Show task details | `/task abc123` |
| `/done <id>` | Mark complete | `/done abc` |
| `/cancel <id>` | Cancel task | `/cancel abc` |
| `/delete <id>` | Delete permanently | `/delete abc` |
| `/taskstats` | Show statistics | `/taskstats` |

### Partial ID Matching

You don't need to type the full task ID:

```bash
# Task ID: abc123-def456-ghi789
/done abc    # Works!
/done abc1   # Also works!
```

## Web UI Kanban Board

### Accessing the Board

Navigate to `http://localhost:8081/tasks`

### Interface

```
┌─────────────────────────────────────────────────────────┐
│  [+ Add Task]                    Filter: [All ▼]        │
├─────────────────┬─────────────────┬─────────────────────┤
│    PENDING      │   IN PROGRESS   │     COMPLETED       │
├─────────────────┼─────────────────┼─────────────────────┤
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────────┐ │
│ │ Buy milk    │ │ │ Fix bug     │ │ │ ✓ Write docs   │ │
│ │ 🟡 Medium   │ │ │ 🔴 High     │ │ │ Completed 2h   │ │
│ │ Due: Today  │ │ │ Due: Fri    │ │ │ +25 XP         │ │
│ └─────────────┘ │ └─────────────┘ │ └─────────────────┘ │
│ ┌─────────────┐ │                 │ ┌─────────────────┐ │
│ │ Call mom    │ │                 │ │ ✓ Deploy app   │ │
│ │ 🟢 Low      │ │                 │ │ Completed 1d   │ │
│ └─────────────┘ │                 │ └─────────────────┘ │
└─────────────────┴─────────────────┴─────────────────────┘
```

### Drag and Drop

- Drag tasks between columns to change status
- Dropping in "Completed" awards XP
- Dropping in "In Progress" triggers mood change

### Quick Add

1. Click "+ Add Task"
2. Enter title
3. Select priority (optional)
4. Set due date (optional)
5. Click "Add"

### Filters

Filter tasks by:
- Status: All, Pending, In Progress, Completed
- Priority: All, Low, Medium, High, Urgent
- Project: Group related tasks

## AI-Powered Task Management

### Natural Language Creation

Ask Inkling to create tasks:

```
> Can you add a task to review the quarterly report?
Inkling: Got it! Added "Review quarterly report" to your tasks. ✓

> Remind me to call the dentist tomorrow
Inkling: Created task "Call the dentist" due tomorrow. I'll remind you!
```

### MCP Tool Integration

When MCP is enabled, Inkling can use these tools:

| Tool | Description |
|------|-------------|
| `task_create` | Create a new task |
| `task_list` | List tasks with filters |
| `task_complete` | Mark task complete |
| `task_update` | Modify task properties |
| `task_delete` | Delete a task |
| `task_stats` | Get completion statistics |

Enable in config:

```yaml
mcp:
  enabled: true
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

## XP and Rewards

### XP by Priority

| Action | Low | Medium | High | Urgent |
|--------|-----|--------|------|--------|
| Create task | 5 | 5 | 5 | 5 |
| Complete task | 10 | 15 | 25 | 40 |
| On-time bonus | +10 | +10 | +10 | +10 |

### Streaks

Complete tasks on consecutive days for bonus XP:

| Streak | Bonus |
|--------|-------|
| 3 days | +15 XP |
| 7 days | +30 XP |

### Mood Reactions

Completing tasks affects Inkling's mood:

- **Urgent task**: Grateful mood, big celebration
- **Regular task**: Happy mood, positive response
- **Overdue task**: Still happy! No guilt-tripping

## Task Statistics

View your productivity stats:

```bash
> /taskstats

Task Statistics
───────────────
Total tasks: 47
├─ Pending: 8
├─ In Progress: 2
├─ Completed: 35
└─ Overdue: 2

30-Day Completion Rate: 74%
Current Streak: 5 days
Due Soon: 3 tasks
```

## Advanced Features

### Projects

Group related tasks:

```bash
# In web UI or via AI
Create task "Design homepage" in project "Website Redesign"
```

Filter by project in Kanban board.

### Tags

Add tags for categorization:

```
Tags: work, urgent, client-x
```

### Subtasks

Break down complex tasks:

```
Main Task: Launch new feature
├─ [ ] Design mockups
├─ [x] Write backend API
├─ [ ] Frontend integration
└─ [ ] Testing
```

Completion percentage calculated automatically.

### Time Tracking

Estimate and track time:

```yaml
task:
  estimated_minutes: 60
  actual_minutes: 45  # Tracked automatically
```

### Due Date Reminders

The heartbeat system reminds you about:
- Overdue tasks (gentle, personality-appropriate)
- Tasks due soon (if enabled)

Configure in heartbeat settings:

```yaml
heartbeat:
  enable_maintenance: true  # Enables task reminders
```

## Database Location

Tasks stored in SQLite:
```
~/.inkling/tasks.db
```

### Backup

```bash
cp ~/.inkling/tasks.db ~/.inkling/tasks.db.backup
```

### Reset

```bash
rm ~/.inkling/tasks.db
# New database created on next start
```

## Tips

1. **Use priorities wisely**: Reserve "urgent" for truly critical tasks
2. **Set due dates**: Enables on-time bonuses and reminders
3. **Complete daily**: Build streaks for bonus XP
4. **Use AI**: Natural language is often faster than commands
5. **Review weekly**: Use `/taskstats` to track progress

## Troubleshooting

### Tasks not showing

```bash
# Check MCP is enabled
/config
# Look for mcp.enabled: true

# Check tasks database exists
ls ~/.inkling/tasks.db
```

### Kanban not loading

- Check JavaScript console for errors
- Verify web server is running
- Try hard refresh (Ctrl+Shift+R)

### AI not creating tasks

- Ensure MCP is enabled
- Check tasks server is configured
- Try explicit command: `/task Your task title`

## Next Steps

- [Set Up MCP Integration](mcp-integration.md) for AI-powered task management
- [Configure Autonomous Behaviors](autonomous-behaviors.md) for task reminders
- [Tune Personality](../configuration/personality-tuning.md) for celebration style
