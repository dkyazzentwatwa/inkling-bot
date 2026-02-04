# Daily Standup Companion Guide

Use Inkling to organize your mornings, prepare for standups, and stay on top of your day.

## Overview

Inkling as a standup companion helps you:
- Get morning briefings
- Prepare standup updates
- Track what you did yesterday
- Plan today's priorities
- Stay accountable

## Setup

### Enable Morning Greetings

```yaml
heartbeat:
  enabled: true
  enable_time_behaviors: true
  quiet_hours_start: 23
  quiet_hours_end: 7  # Greetings start at 7 AM
```

### Calendar Integration (Optional)

For meeting awareness, connect Google Calendar via Composio:

```yaml
mcp:
  enabled: true
  servers:
    composio:
      transport: "http"
      url: "https://backend.composio.dev/v3/mcp"
      headers:
        x-api-key: "${COMPOSIO_API_KEY}"
```

### Standup Personality

```yaml
personality:
  curiosity: 0.5      # Asks about your work
  cheerfulness: 0.7   # Positive morning energy
  verbosity: 0.4      # Concise briefings
  playfulness: 0.4    # Light but professional
  empathy: 0.7        # Understanding of workload
  independence: 0.6   # Proactive reminders
```

## Morning Briefing

### Automatic Wake-Up

Between 7-10 AM, Inkling greets you:

```
┌─────────────────────────────────────────┐
│ (^_^)  Inkling                   7:15   │
├─────────────────────────────────────────┤
│                                         │
│      Good morning! Ready to start       │
│           your day?                     │
│                                         │
└─────────────────────────────────────────┘
```

### Daily Briefing Command

```
You: /briefing

Inkling: Good morning! Here's your day:

         TODAY (Tuesday, Jan 14)
         - 9:30 AM: Daily Standup
         - 2:00 PM: Sprint Review
         - 4:00 PM: 1:1 with Sarah

         TASKS (3 in progress)
         - Fix login timeout bug
         - Review PR from Alice
         - Update API docs

         OVERDUE (1)
         - Deploy hotfix (due yesterday)

         Yesterday you completed 2 tasks.
         Keep the momentum!
```

## Standup Preparation

### Yesterday's Summary

```
You: What did I do yesterday?

Inkling: Yesterday's Activity:

         Completed:
         - Implemented dark mode toggle
         - Fixed memory leak in worker
         - Reviewed 2 pull requests

         In Progress:
         - Login timeout fix (60% done)
         - API documentation update

         Time tracked: 6.5 hours
```

### Today's Plan

```
You: What should I focus on today?

Inkling: Today's Priorities:

         1. Deploy hotfix (overdue!)
         2. Finish login timeout fix
         3. Continue API docs
         4. Start new feature if time

         Standup at 9:30 - you have 45 min.

         Want me to create tasks for these?
```

### Standup Script

```
You: Help me prepare my standup

Inkling: Your Standup Update:

         YESTERDAY:
         "I completed the dark mode toggle and
         fixed the memory leak. Also reviewed
         two PRs from the team."

         TODAY:
         "I'll deploy the hotfix first thing,
         then finish the login timeout fix.
         If time permits, I'll continue the
         API documentation."

         BLOCKERS:
         "No blockers currently."

         ---
         Copy this or adjust as needed!
```

## Task Integration

### Quick Task Creation

```
You: I need to review the new design mockups

Inkling: Created task: "Review design mockups"
         Priority: Medium
         Added to today's list.

         Want to set a due time?
```

### Mark Progress

```
You: The hotfix is deployed

Inkling: Marked "Deploy hotfix" as complete!
         +15 XP for completing a high-priority task

         Next up: Login timeout fix

         Great start to the day!
```

### End of Day Review

```
You: /eod

Inkling: End of Day Summary:

         Completed Today:
         - Deploy hotfix
         - Login timeout fix
         - Review design mockups

         Carried Over:
         - API documentation (70% done)

         Stats:
         - 3 tasks completed
         - 2 PRs reviewed
         - 5.5 hours tracked

         Tomorrow's Focus:
         - API documentation
         - Start user profile feature

         Great day! Rest well.
```

## Calendar Awareness

### Meeting Reminders

```
┌─────────────────────────────────────────┐
│ (o_o)  Inkling                   9:25   │
├─────────────────────────────────────────┤
│                                         │
│   Standup in 5 minutes!                 │
│   You have 3 items to share.            │
│                                         │
└─────────────────────────────────────────┘
```

### Focus Time Protection

```
You: I need 2 hours of focus time

Inkling: Focus mode activated!

         I'll hold non-urgent reminders
         until 11:30 AM.

         Your next meeting: 2:00 PM
         (Sprint Review - plenty of time)

         Good luck! I'm here if needed.
```

### Meeting Prep

```
You: What's my next meeting?

Inkling: Next: Sprint Review (2:00 PM)

         Duration: 1 hour
         Attendees: Team (8 people)

         Agenda:
         - Demo completed features
         - Review sprint metrics
         - Discuss blockers

         Your demos:
         - Dark mode toggle
         - Login timeout fix

         Need help preparing?
```

## Weekly Patterns

### Monday Planning

```
You: /week

Inkling: Week of Jan 13-17:

         Monday: Sprint planning
         Tuesday: Focus day (no meetings)
         Wednesday: Design review, Team sync
         Thursday: Focus day
         Friday: Sprint review, Retro

         Sprint goals:
         1. Ship user profile feature
         2. Fix all P1 bugs
         3. Update documentation

         12 tasks in backlog.
         Let's break these down?
```

### Friday Wrap-Up

```
You: /weekreview

Inkling: Week in Review:

         Completed: 8 tasks
         Carried Over: 2 tasks
         New Added: 5 tasks

         Highlights:
         - Shipped dark mode!
         - Zero P1 bugs remaining
         - 3-day completion streak

         Areas for next week:
         - Documentation still behind
         - Need to plan user profile

         Overall: Productive week!
```

## Habit Building

### Daily Streaks

```
┌─────────────────────────────────────────┐
│ (^_^)  Inkling                   8:00   │
├─────────────────────────────────────────┤
│                                         │
│   5-day streak! Keep it going!          │
│   Complete at least one task today.     │
│                                         │
└─────────────────────────────────────────┘
```

### Accountability

```
You: I keep putting off the documentation

Inkling: I noticed! It's been in progress
         for 5 days now.

         Ideas to help:
         1. Break it into smaller chunks
         2. Set a 30-min timer
         3. Make it today's first task
         4. Pair with someone?

         Want me to create subtasks?
```

### Progress Tracking

```
You: Am I being productive?

Inkling: Your Trends (last 2 weeks):

         Tasks/day: 2.3 avg (up from 1.8)
         Completion rate: 78%
         On-time: 65%

         Strengths:
         - Great at bug fixes
         - Quick PR reviews

         Growth areas:
         - Documentation tasks linger
         - Large features take longer

         You're improving! Keep it up.
```

## Best Practices

### Morning Routine (15 min)

1. Check Inkling's greeting (1 min)
2. Run `/briefing` (2 min)
3. Run `/standup` prep (3 min)
4. Review tasks, adjust priorities (5 min)
5. Handle urgent items (4 min)

### During Standup

1. Reference Inkling's script
2. Update task status live
3. Note any new tasks mentioned

### After Standup

1. Create tasks from discussions
2. Update priorities if changed
3. Start focused work

### End of Day (5 min)

1. Run `/eod` review
2. Mark completed tasks
3. Note tomorrow's priorities
4. Celebrate wins!

## Troubleshooting

### No Morning Greeting

1. Check heartbeat is enabled
2. Verify not in quiet hours
3. Check time zone settings

### Calendar Not Showing

1. Verify Composio connection
2. Check Google Calendar permissions
3. Refresh calendar sync

### Tasks Out of Sync

```
You: /tasks refresh

Inkling: Refreshed task list.
         5 pending, 2 in progress, 3 completed
```

## Next Steps

- [Task Management](../features/task-management.md) - Full task system
- [Focus & Pomodoro](focus-pomodoro.md) - Productivity sessions
- [Autonomous Behaviors](../features/autonomous-behaviors.md) - Customize reminders
- [Developer Assistant](developer-assistant.md) - GitHub integration
