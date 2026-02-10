# Focus & Pomodoro Guide

Use Inkling as a productivity timer and focus companion for deep work sessions.

## Overview

Inkling helps you:
- Run Pomodoro work sessions
- Track focus time
- Minimize distractions
- Celebrate productivity
- Build consistent habits

## Command Quick Reference

Use the `/focus` command family in SSH or Web:
- `/focus start`
- `/focus start <minutes>`
- `/focus start <minutes> <task_ref>`
- `/focus pause`
- `/focus resume`
- `/focus break`
- `/focus stop`
- `/focus status`
- `/focus stats`
- `/focus week`
- `/focus config`

## The Pomodoro Technique

Traditional Pomodoro:
1. **25 minutes** focused work
2. **5 minutes** short break
3. Repeat 4 times
4. **15-30 minutes** long break

Inkling adapts this to your preferences.

## Setup

### Focus-Friendly Personality

```yaml
personality:
  curiosity: 0.4      # Less interrupting
  cheerfulness: 0.6   # Encouraging
  verbosity: 0.3      # Brief updates
  playfulness: 0.3    # Minimal distractions
  empathy: 0.7        # Understanding
  independence: 0.5   # Balanced reminders
```

### Quiet During Focus

```yaml
focus:
  enabled: true
  quiet_mode_during_focus: true
  timer_ui:
    takeover_enabled: true
    style: "digital_progress"
    eink:
      cadence_normal_sec: 30
      cadence_final_min_sec: 10
```

```yaml
heartbeat:
  enabled: true
  enable_mood_behaviors: true   # Quiet mode suppresses non-critical chatter while active
  enable_time_behaviors: true
```

## Starting a Focus Session

### Quick Start

```
You: /focus start

Inkling: Pomodoro started! (25 min)

         Focus on your task.
         I'll be quiet until the timer ends.

         Session 1 of 4
```

### Custom Duration

```
You: /focus start 45

Inkling: Focus session started! (45 min)

         Ends at 10:45 AM
         
         I'll minimize interruptions.
         Good luck!
```

### With Task Context

```
You: /focus start 25 api-docs

Inkling: Focus: "API documentation" (25 min)

         Task marked as in-progress.
         
         When done, I'll ask about progress.
         
         Let's do this!
```

## During Focus

### Minimal Interruptions

During focus mode, Inkling:
- Holds non-urgent reminders
- Shows only critical alerts
- Keeps display minimal

```
┌─────────────────────────────────────────┐
│ (._.)  Inkling                 FOCUS    │
├─────────────────────────────────────────┤
│                                         │
│           API documentation             │
│               18:42                     │
│                                         │
└─────────────────────────────────────────┘
```

### Check Time Remaining

```
You: /focus status

Inkling: 12 minutes remaining.

         You're doing great!
         Stay focused.
```

### Emergency Exit

```
You: /focus stop

Inkling: Focus session ended early.
         You completed 13 of 25 minutes.

         That's okay! Sometimes we need
         to context switch.

         Resume later?
```

## Break Time

### Short Break (5 min)

```
┌─────────────────────────────────────────┐
│ (^_^)  Inkling                  10:25   │
├─────────────────────────────────────────┤
│                                         │
│      Pomodoro complete!                 │
│      Take a 5-minute break.             │
│                                         │
└─────────────────────────────────────────┘
```

### Break Suggestions

```
Inkling: Break ideas (5 min):
         - Stretch or walk
         - Get water
         - Look away from screen
         - Quick breathing exercise

         I'll let you know when to resume.
```

### Long Break (After 4 Sessions)

```
Inkling: 4 pomodoros complete!

         Time for a longer break (15-30 min).

         Today's focus: 1h 40m
         Tasks touched: 2

         Great work! You've earned this rest.
```

## Session Tracking

### Daily Stats

```
You: /focus stats

Inkling: Today's Focus:

         Sessions: 6 pomodoros
         Total time: 2h 30m
         Longest streak: 3 sessions

         Tasks worked on:
         - API documentation (45 min)
         - Bug fix #89 (50 min)
         - Code review (25 min)
         - Planning (30 min)

         Great productivity!
```

### Weekly Overview

```
You: /focus week

Inkling: Focus This Week:

         Mon: 4 sessions (1h 40m)
         Tue: 6 sessions (2h 30m)
         Wed: 3 sessions (1h 15m)
         Thu: 5 sessions (2h 5m)
         Fri: 2 sessions (50m) [so far]

         Total: 20 sessions (8h 20m)
         Avg: 4/day

         Best day: Tuesday
```

## Focus Modes

### Deep Work Mode

For extended concentration:

```
You: I need 2 hours of deep work

Inkling: Deep work mode (2 hours)

         All notifications held.
         I'll check in at the halfway point.

         Ending at 12:30 PM

         Dive deep!
```

### Meeting-Free Block

```
You: Block 9-11 AM for focus

Inkling: Focus block scheduled: 9-11 AM

         I'll remind you at 8:55 AM
         and protect this time.

         What will you work on?
```

### Flow State

When you're in the zone:

```
You: I'm in the flow, extend my session

Inkling: Understood! Timer paused.

         Keep going as long as you need.
         Say "done" when you finish.

         Enjoy the flow!
```

## Task Integration

### Auto-Track Focus Time

```
You: /done

Inkling: Task "API documentation" complete!

         Time tracked: 47 minutes
         (from 2 focus sessions)

         +15 XP

         What's next?
```

### Estimate vs Actual

```
You: /task stats

Inkling: API Documentation:

         Estimated: 1 hour
         Actual: 1h 47m
         Sessions: 4 pomodoros

         Notes:
         - More complex than expected
         - Added extra examples

         Update estimate for similar tasks?
```

## Break Activities

### Guided Breathing

```
You: Help me relax

Inkling: 4-7-8 Breathing Exercise:

         Breathe IN... (4 seconds)
         ████████████████

         HOLD... (7 seconds)
         ████████████████████████████

         Breathe OUT... (8 seconds)
         ████████████████████████████████

         Repeat 3 times.
         How do you feel?
```

### Quick Stretch

```
You: Stretch break

Inkling: Quick Desk Stretches (2 min):

         1. Neck rolls (30s)
            Slowly roll head in circles

         2. Shoulder shrugs (30s)
            Raise, hold, release

         3. Wrist circles (30s)
            Both directions

         4. Stand and reach (30s)
            Arms up, stretch tall

         Ready to focus again?
```

### Mindfulness Moment

```
You: I need to clear my head

Inkling: 1-Minute Reset:

         Close your eyes.
         
         Notice 3 things you hear.
         
         Take 3 deep breaths.
         
         Open your eyes.
         
         What's the ONE thing to
         focus on next?
```

## Customization

### Custom Session Lengths

```yaml
focus:
  default_work_minutes: 25
  short_break_minutes: 5
  long_break_minutes: 15
  sessions_until_long_break: 4
  auto_start_breaks: true
  allow_pause: true
```

### Strict Mode

```
You: Enable strict focus

Inkling: Strict mode ON.

         - No messages during focus
         - No early exit without confirm
         - Break reminders required

         Start a session when ready.
```

## Productivity Patterns

### Morning Focus Block

Best for creative/complex work:

```
7:00  - Morning routine
8:00  - Pomodoro 1 (deep work)
8:30  - Short break
8:35  - Pomodoro 2 (deep work)
9:00  - Short break
9:05  - Pomodoro 3 (deep work)
9:30  - Long break / standup
```

### Afternoon Sessions

For routine/admin work:

```
13:00 - Pomodoro 1 (emails/reviews)
13:30 - Short break
13:35 - Pomodoro 2 (meetings prep)
14:00 - Meetings...
16:00 - Pomodoro 3 (wrap up)
```

### Energy Management

```
You: When am I most productive?

Inkling: Your Focus Patterns:

         Peak hours: 8-11 AM
         - Longest sessions
         - Fewest interruptions
         - Most tasks completed

         Low energy: 2-3 PM
         - Shorter sessions
         - More breaks needed

         Suggestion: Schedule deep work
         in the morning!
```

## Troubleshooting

### Can't Focus

```
You: I can't concentrate today

Inkling: That happens! Try:

         1. Shorter session (15 min)
         2. Change location
         3. Different task
         4. Take a walk first
         5. Accept it - some days are hard

         Want to try a mini-session?
```

### Too Many Interruptions

```
You: I keep getting pulled away

Inkling: Interruption log today: 5

         Sources:
         - Slack: 3
         - Meetings: 1
         - Other: 1

         Ideas:
         - Set Slack to DND
         - Block calendar
         - Wear headphones
         - "Focus" door sign

         Protect your time!
```

### Burnout Prevention

```
Inkling: You've done 8 pomodoros today!

         That's great, but remember:
         - Take real breaks
         - Drink water
         - Step outside
         - Sustainable > sprint

         Maybe call it a day?
```

## Best Practices

1. **Start small**: 2-3 pomodoros/day is great
2. **Respect breaks**: They're part of the technique
3. **Track patterns**: Learn your peak hours
4. **Be flexible**: Adapt session length to tasks
5. **Celebrate**: Acknowledge completed sessions

## Next Steps

- [Task Management](../features/task-management.md) - Link focus to tasks
- [Daily Standup](daily-standup.md) - Morning planning
- [Autonomous Behaviors](../features/autonomous-behaviors.md) - Customize reminders
- [Personality Tuning](../configuration/personality-tuning.md) - Focus-friendly settings
