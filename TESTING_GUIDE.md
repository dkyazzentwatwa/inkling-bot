# Task Manager Testing Guide

## Quick Start

This guide will help you test the new task management features in Inkling.

## Setup

### 1. Enable MCP Tools (Required for AI-driven task management)

Edit `config.local.yml`:

```yaml
mcp:
  enabled: true
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

### 2. Set API Keys

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# OR
export OPENAI_API_KEY=sk-...
```

### 3. Start Inkling

**SSH Mode:**
```bash
source .venv/bin/activate
python main.py --mode ssh
```

**Web Mode:**
```bash
source .venv/bin/activate
python main.py --mode web
# Then open http://localhost:8080 in your browser
```

---

## Testing SSH Commands

### Test 1: Create a Task

```
/task Fix the login bug !high #bug
```

**Expected:**
- Task created with high priority
- Tagged with "bug"
- Personality reacts (mood changes to Intense or Curious)
- +5 XP awarded
- Display shows celebration message

### Test 2: List Tasks

```
/tasks
```

**Expected:**
- Shows tasks grouped by status (To Do, In Progress, Completed today)
- Priority indicators (○ = low, ● = medium, red● = high, ‼ = urgent)
- Status indicators (□ = pending, ⏳ = in progress, ✓ = completed)
- Tags displayed with #
- Overdue tasks marked in red

### Test 3: View Task Details

```
/task <task_id>
```

**Expected:**
- Full task details
- Priority, status, tags
- Due date (if set)
- Subtasks (if any)
- Created/completed timestamps

### Test 4: Complete a Task

```
/done <task_id>
```

**Expected:**
- Task marked as completed
- Celebration message based on priority
- XP awarded (10-40 XP based on priority)
- On-time bonus if completed before due date (+10 XP)
- Mood changes to Happy or Grateful
- Display updates with face expression

### Test 5: Task Statistics

```
/taskstats
```

**Expected:**
- Total, pending, in-progress, completed counts
- Overdue count (in red if > 0)
- Due soon count (next 3 days)
- 30-day completion rate percentage
- Current level and XP

---

## Testing Web API

Use curl or your browser's developer console:

### Create a Task

```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Design new feature",
    "description": "Create mockups for the dashboard",
    "priority": "high",
    "tags": ["design", "ui"],
    "due_in_days": 3
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "task": {
    "id": "uuid-here",
    "title": "Design new feature",
    "status": "pending",
    "priority": "high",
    "tags": ["design", "ui"],
    "days_until_due": 3,
    ...
  },
  "celebration": "Got it! Added to our list ✓",
  "xp_awarded": 5
}
```

### List Tasks

```bash
curl http://localhost:8080/api/tasks
curl http://localhost:8080/api/tasks?status=pending
curl http://localhost:8080/api/tasks?project=myproject
```

### Complete a Task

```bash
curl -X POST http://localhost:8080/api/tasks/<task_id>/complete
```

**Expected Response:**
```json
{
  "success": true,
  "task": { ... },
  "celebration": "Nicely done! +25 XP ✨",
  "xp_awarded": 25
}
```

### Update a Task

```bash
curl -X PUT http://localhost:8080/api/tasks/<task_id> \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "priority": "urgent"
  }'
```

### Get Statistics

```bash
curl http://localhost:8080/api/tasks/stats
```

---

## Testing AI Multi-Step Workflows

### Test 1: Simple Task Creation

**User input:**
```
Create a task to review the PR
```

**Expected AI behavior:**
```
Round 1: AI calls task_create(title="Review the PR", priority="medium")
Response: "✓ Task created! I've added 'Review the PR' to your list."
Display: Shows task creation celebration
```

### Test 2: Task with Priority

**User input:**
```
Add an urgent task to fix the production bug
```

**Expected AI behavior:**
```
Round 1: AI calls task_create(title="Fix production bug", priority="urgent")
Response: "I feel the urgency! Let's tackle this 💪 Task added."
Mood: Changes to Intense
XP: +5
```

### Test 3: List and Complete

**User input:**
```
Show me my pending tasks
```

**Expected AI behavior:**
```
Round 1: AI calls task_list(status="pending")
Response: Lists all pending tasks with details
```

**Follow-up:**
```
Mark the first one as done
```

**Expected AI behavior:**
```
Round 1: AI calls task_complete(task_id="...")
Response: "Nicely done! +15 XP ✨" (or higher based on priority)
Mood: Changes to Happy
```

### Test 4: Complex Multi-Step (with other MCP tools)

If you have Composio or other MCP servers enabled:

**User input:**
```
Check my calendar for tomorrow and create tasks for each meeting
```

**Expected AI behavior:**
```
Round 1: Calls calendar API (via Composio/MCP)
Round 2: Calls task_create() for meeting 1
Round 3: Calls task_create() for meeting 2
Round 4: Calls task_create() for meeting 3
Response: "Added 3 tasks from your calendar!"
```

---

## Testing Heartbeat Behaviors

Heartbeat runs in the background with periodic ticks (default: every 60 seconds).

### Test 1: Overdue Reminder

1. Create a task with a past due date:
   ```
   /task Overdue task
   # Manually edit the database to set due_date in the past
   ```

2. Wait for heartbeat tick (up to 60 seconds)

**Expected:**
- Gentle reminder appears on display
- Message adapts to mood:
  - Lonely: "Hey... feeling lonely. Wanna work on 'Overdue task' together?"
  - Empathetic: "No pressure, but 'Overdue task' is waiting when you're ready 💙"
  - Default: "'Overdue task' is overdue. Still relevant?"

### Test 2: Task Suggestion

1. Create several pending tasks with different priorities and tags
2. Wait for heartbeat tick

**Expected:**
- Suggestion appears based on current mood:
  - Curious mood + tasks tagged #research: "🤔 Curious about... Research project?"
  - Sleepy mood + low priority: "😴 Easy one: Simple task?"
  - Intense mood + high priority: "💪 Ready to tackle: Important task?"

### Test 3: Streak Celebration

1. Complete tasks on 3-7 consecutive days
2. Wait for daily heartbeat celebration (once per day)

**Expected:**
- 3-day streak: "✨ 3-day streak! You're building great habits!"
- 5-day streak: "💪 5 days in a row! Keep the momentum going!"
- 7-day streak: "🔥 Amazing! 7-day task completion streak! You're unstoppable!"

### Heartbeat Configuration

You can adjust behavior in `config.local.yml`:

```yaml
heartbeat:
  enabled: true
  tick_interval: 60  # Seconds between ticks (set to 10 for faster testing)
  enable_mood_behaviors: true  # Task suggestions
  enable_maintenance: true     # Overdue reminders, streak celebrations
```

---

## Testing Personality Integration

### Test: XP Rewards

Create and complete tasks of different priorities:

```
/task Low priority task !low
/task Medium priority task
/task High priority task !high
/task URGENT FIX !urgent
```

Complete each and verify XP rewards:
- Low: +10 XP
- Medium: +15 XP
- High: +25 XP
- Urgent: +40 XP
- On-time bonus: +10 XP (if completed before due date)

### Test: Mood Reactions

**Urgent task:**
```
/task Critical production issue !!
```
- Mood intensity increases
- Face changes to intense/focused
- Message: "I feel the urgency! Let's tackle this 💪"

**Fun task:**
```
/task Make a fun game feature
```
- Mood: Excited
- Message: "Ooh this sounds fun! 🎉"

**Completion:**
```
/done <urgent_task_id>
```
- Mood: Grateful
- Message: "Phew! Thanks for handling that urgent task 🙏"

### Test: Streak Bonuses

Complete tasks on consecutive days:
- 3-day streak: +15 XP bonus
- 7-day streak: +30 XP bonus

---

## Database Location

All tasks are stored in SQLite:
```
~/.inkling/tasks.db
```

You can inspect it:
```bash
sqlite3 ~/.inkling/tasks.db
.tables
SELECT * FROM tasks;
```

---

## Troubleshooting

### Issue: MCP tools not working

**Check:**
1. Is MCP enabled in config.local.yml?
2. Is the tasks.py script executable?
   ```bash
   chmod +x mcp_servers/tasks.py
   ```
3. Check logs for MCP errors:
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

### Issue: No task suggestions from heartbeat

**Check:**
1. Are there pending tasks?
2. Is heartbeat enabled?
3. Has enough time passed (cooldown)?
4. Try reducing tick_interval for faster testing:
   ```yaml
   heartbeat:
     tick_interval: 10  # Test every 10 seconds
   ```

### Issue: XP not awarded

**Check:**
1. Did the personality event trigger? (should see mood change)
2. Check rate limiting (max 100 XP/hour)
3. Verify task was actually completed (check /tasks output)

---

## Next Steps

After testing the basics:

1. **Build Web UI** - Create a Kanban board at `/tasks`
2. **Add Composio Integration** - Connect Google Calendar, GitHub Issues, etc.
3. **Custom Task Types** - Add recurring tasks, dependencies, time estimates
4. **Task Analytics** - Visualize productivity trends
5. **Voice Commands** - Integrate with voice assistant for hands-free task management

---

## Expected Performance

- **Task creation**: < 100ms
- **Task listing**: < 50ms (even with hundreds of tasks)
- **AI task creation**: 1-3 seconds (depends on AI provider)
- **Heartbeat behaviors**: Non-blocking, runs in background

---

## Success Criteria

✅ Tasks can be created via commands and AI
✅ Tasks persist across restarts
✅ XP rewards work correctly
✅ Personality reacts to task events
✅ Heartbeat provides proactive reminders
✅ Multi-step AI workflows complete successfully
✅ Web API returns correct JSON
✅ Display updates show task status

---

**Happy testing!** 🎉

Report any issues or unexpected behavior. The task manager is designed to feel like a collaborative companion, not just a cold productivity tool.
