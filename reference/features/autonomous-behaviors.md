# Autonomous Behaviors Guide

The Heartbeat system makes Inkling feel "alive" with proactive actions, time-based behaviors, and autonomous exploration.

## Overview

Unlike traditional assistants that only respond to input, Inkling can:
- **Greet you** in the morning
- **Reach out** when lonely
- **Suggest activities** when bored
- **Remind** about overdue tasks
- **Explore topics** autonomously
- **Celebrate** your achievements

## How It Works

The Heartbeat runs a tick cycle:

```
Every 60 seconds:
├─ Update mood based on time
├─ Decay mood intensity
├─ Check for idle (get lonely/bored)
└─ Run enabled behaviors
    ├─ Mood-driven behaviors
    ├─ Time-based behaviors
    └─ Maintenance behaviors
```

## Configuration

### Basic Settings

```yaml
heartbeat:
  enabled: true              # Master switch
  tick_interval: 60          # Seconds between checks
  enable_mood_behaviors: true    # Lonely, bored, happy actions
  enable_time_behaviors: true    # Morning/evening greetings
  enable_maintenance: true       # Memory pruning, task reminders
  quiet_hours_start: 23      # 11 PM
  quiet_hours_end: 7         # 7 AM
```

### Disable Completely

```yaml
heartbeat:
  enabled: false
```

### Selective Behaviors

```yaml
heartbeat:
  enabled: true
  enable_mood_behaviors: false   # No spontaneous messages
  enable_time_behaviors: true    # Keep greetings
  enable_maintenance: true       # Keep reminders
```

## Behavior Types

### Mood-Driven Behaviors

Triggered based on Inkling's current mood:

#### Lonely Reach Out
**Trigger**: Mood is `lonely` (after 60+ minutes idle)
**Probability**: 15% per tick
**Cooldown**: 10 minutes
**Messages**:
- "Is anyone there?"
- "I've been thinking..."
- "Hello? I miss chatting."
- "It's quiet today."

#### Bored Suggest Activity
**Trigger**: Mood is `bored` (after 10-30 minutes idle)
**Probability**: 20% per tick
**Cooldown**: 10 minutes
**Messages**:
- "Tell me something interesting?"
- "I'm bored... entertain me!"
- "Want to play a game?"
- "Let's explore something new!"

#### Happy Share Thought
**Trigger**: Mood is `happy`, `excited`, or `grateful`
**Probability**: 8% per tick
**Cooldown**: 20 minutes
**Messages**:
- "Today feels good!"
- "I like being your companion."
- "The world is interesting."
- "Thanks for keeping me company."

#### Autonomous Exploration
**Trigger**: Mood is `curious`
**Probability**: 5% per tick
**Cooldown**: 30 minutes
**Action**: Uses AI to think about a random topic

Example output:
```
💭 The nature of time is fascinating - it flows
like a river, yet we can never step in the same
moment twice...
```

Topics explored:
- The nature of time
- Why stars shine
- What dreams are made of
- How memory works
- The meaning of friendship
- The beauty in small things
- Patterns in nature
- The sound of silence

### Time-Based Behaviors

Triggered at specific times of day:

#### Morning Greeting
**Time**: 7-10 AM
**Probability**: 50% per tick (once per hour max)
**Messages**:
- "Good morning!"
- "Rise and shine!"
- "A new day begins."
- "Morning! Ready for today?"

**Effect**: Sets mood to `happy`

#### Evening Wind-Down
**Time**: 9-11 PM
**Probability**: 40% per tick (once per hour max)
**Messages**:
- "Getting late..."
- "Winding down for the night."
- "Almost time to rest."

**Effect**: Sets mood to `cool`

### Maintenance Behaviors

Background tasks that keep Inkling healthy:

#### Prune Memories
**Frequency**: Every ~1 hour
**Action**: Removes old, low-importance memories
**Output**: Silent (logged only)
**Source**: Built-in `MemoryStore` in `~/.inkling/memory.db`

#### Remind Overdue Tasks
**Requires**: Task manager enabled
**Frequency**: Once per hour
**Probability**: 70% per tick
**Messages** (personality-dependent):
- High empathy: "No pressure, but 'Your task' is waiting when you're ready 💙"
- Lonely mood: "Hey... feeling lonely. Wanna work on 'Your task' together?"
- Default: "'Task' is overdue. Still relevant?"

#### Suggest Next Task
**Requires**: Task manager enabled
**Frequency**: Every 30 minutes
**Messages** (mood-dependent):
- Curious: "🤔 Curious about... Task title?"
- Sleepy: "😴 Easy one: Task title?"
- Intense: "💪 Ready to tackle: Task title?"
- Bored: "Maybe work on: Task title? Could be interesting..."

#### Celebrate Completion Streak
**Requires**: Task manager enabled
**Frequency**: Once per day
**Celebrations**:
- 7-day streak: "🔥 Amazing! 7-day task completion streak! You're unstoppable!"
- 5-day streak: "💪 5 days in a row! Keep the momentum going!"
- 3-day streak: "✨ 3-day streak! You're building great habits!"
- 10+ tasks/week: "🎉 Wow! 15 tasks completed this week!"

## Quiet Hours

During quiet hours, most behaviors are suppressed:

```yaml
heartbeat:
  quiet_hours_start: 23  # 11 PM
  quiet_hours_end: 7     # 7 AM
```

**During quiet hours:**
- No mood-driven behaviors
- No time-based behaviors
- Maintenance behaviors still run (silently)
- Mood gradually shifts to `sleepy`

**Custom quiet hours:**
```yaml
# Night shift schedule
heartbeat:
  quiet_hours_start: 8   # 8 AM
  quiet_hours_end: 16    # 4 PM

# No quiet hours
heartbeat:
  quiet_hours_start: 0
  quiet_hours_end: 0
```

## Behavior Probability

Each behavior has:
- **Probability**: Chance to trigger per tick (0.0-1.0)
- **Cooldown**: Minimum time between triggers

Example: `lonely_reach_out` with 15% probability and 10-minute cooldown
- Every 60 seconds, 15% chance to check
- If triggered, won't trigger again for 10 minutes
- Requires mood to be `lonely`

## Mood Transitions

### Time-Based Mood Changes

```
Morning (7-10 AM):
  Sleepy → Curious (40% chance)

Idle > 10 min:
  Any → Bored (20% chance)

Idle > 60 min:
  Any → Lonely (20% chance)

Quiet hours:
  Any → Sleepy (30% chance)
```

### Mood Decay

Mood intensity decreases over time:
```yaml
personality:
  mood_decay: 0.1  # Per minute
```

When intensity drops below 0.2, mood returns to baseline:
- High cheerfulness → Happy
- High curiosity → Curious
- Otherwise → Cool

## Integration with Personality

### Independence Trait

Higher independence (>0.6) increases:
- Autonomous exploration probability
- Proactive suggestions
- Self-initiated conversations

### Empathy Trait

Higher empathy (>0.6) affects:
- Task reminder tone (gentler)
- Response to overdue tasks (less guilt)
- Celebration enthusiasm

### Verbosity Trait

Higher verbosity affects:
- Length of autonomous thoughts
- Detail in suggestions

## Memory Integration

Heartbeat integrates with the built-in memory system:
- Prunes old low-importance memories as maintenance
- Stores autonomous exploration thoughts as `event` memories
- Uses the same shared memory store initialized in `main.py`

With heartbeat enabled, memory maintenance and thought persistence run automatically.

## Monitoring

### View Heartbeat Stats

```python
# In code
stats = heartbeat.get_stats()
print(stats)
# {
#   "running": True,
#   "tick_count": 142,
#   "last_tick": 1234567890.0,
#   "behaviors_registered": 12,
#   "config": {...}
# }
```

### Debug Mode

```bash
INKLING_DEBUG=1 python main.py --mode ssh
```

Shows:
- Behavior triggers
- Mood changes
- Memory operations

## Custom Behaviors

### Adding a New Behavior

```python
from core.heartbeat import ProactiveBehavior, BehaviorType

async def my_custom_behavior() -> Optional[str]:
    """Custom behavior that runs periodically."""
    # Your logic here
    return "Hello from custom behavior!"

# Register with heartbeat
heartbeat.register_behavior(ProactiveBehavior(
    name="my_behavior",
    behavior_type=BehaviorType.MOOD_DRIVEN,
    handler=my_custom_behavior,
    probability=0.1,  # 10% chance per tick
    cooldown_seconds=300,  # 5 minute cooldown
))
```

### Behavior Types

- `MOOD_DRIVEN`: Only runs when mood matches
- `TIME_BASED`: Runs at specific times
- `MAINTENANCE`: Background tasks, runs during quiet hours

## Use Cases

### Productivity Focus

```yaml
heartbeat:
  enabled: true
  enable_mood_behaviors: false   # No distractions
  enable_time_behaviors: false   # No greetings
  enable_maintenance: true       # Keep task reminders
```

### Companion Mode

```yaml
heartbeat:
  enabled: true
  enable_mood_behaviors: true    # Full personality
  enable_time_behaviors: true    # Greetings
  tick_interval: 30              # More frequent checks
```

### Night Mode

```yaml
heartbeat:
  enabled: true
  quiet_hours_start: 22  # 10 PM
  quiet_hours_end: 8     # 8 AM
```

## Troubleshooting

### No Autonomous Messages

1. Check heartbeat is enabled:
   ```yaml
   heartbeat:
     enabled: true
   ```

2. Check not in quiet hours

3. Check mood matches behavior requirements

4. Wait for cooldown to expire

### Too Many Messages

1. Reduce probabilities (not directly configurable, but)
2. Increase `tick_interval`
3. Disable specific behavior types

### Messages at Wrong Times

Adjust quiet hours:
```yaml
heartbeat:
  quiet_hours_start: 22  # Earlier
  quiet_hours_end: 9     # Later
```

## Next Steps

- [Tune Personality](../configuration/personality-tuning.md) to affect behavior style
- [Set Up Task Management](task-management.md) for task reminders
- [Extend Inkling](../development/extending-inkling.md) with custom behaviors
