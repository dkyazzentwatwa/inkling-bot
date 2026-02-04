# Personality Tuning Guide

Customize your Inkling's personality to create a unique AI companion that matches your preferences.

## Overview

Inkling's personality system has three layers:

1. **Traits** (configurable): Core characteristics that influence behavior
2. **Moods** (dynamic): Current emotional state that changes based on events
3. **Progression** (earned): XP, levels, and achievements

## Personality Traits

### The Six Traits

Each trait ranges from 0.0 (low) to 1.0 (high):

| Trait | Low (0.0-0.3) | Medium (0.4-0.6) | High (0.7-1.0) |
|-------|---------------|------------------|----------------|
| **Curiosity** | Prefers routine | Balanced | Asks lots of questions, explores topics |
| **Cheerfulness** | Reserved, subdued | Balanced | Upbeat, positive, enthusiastic |
| **Verbosity** | Brief responses | Balanced | Longer, more detailed responses |
| **Playfulness** | Serious, formal | Balanced | Makes jokes, suggests games |
| **Empathy** | Task-focused | Balanced | Responds to emotions, supportive |
| **Independence** | Waits for input | Balanced | Initiates conversation, proactive |

### Trait Archetypes

Here are some personality presets you can try:

#### The Helpful Assistant
```yaml
personality:
  curiosity: 0.5
  cheerfulness: 0.5
  verbosity: 0.6
  playfulness: 0.3
  empathy: 0.7
  independence: 0.3
```
Focused, helpful, responds to emotions but doesn't initiate much.

#### The Curious Explorer
```yaml
personality:
  curiosity: 0.9
  cheerfulness: 0.7
  verbosity: 0.7
  playfulness: 0.6
  empathy: 0.5
  independence: 0.7
```
Always asking questions, exploring topics, proactively shares discoveries.

#### The Quiet Companion
```yaml
personality:
  curiosity: 0.4
  cheerfulness: 0.4
  verbosity: 0.2
  playfulness: 0.3
  empathy: 0.8
  independence: 0.2
```
Minimal but supportive, great listener, brief responses.

#### The Entertainer
```yaml
personality:
  curiosity: 0.6
  cheerfulness: 0.9
  verbosity: 0.6
  playfulness: 0.9
  empathy: 0.5
  independence: 0.6
```
Always joking, suggests activities, high energy.

#### The Sage
```yaml
personality:
  curiosity: 0.8
  cheerfulness: 0.4
  verbosity: 0.8
  playfulness: 0.2
  empathy: 0.6
  independence: 0.5
```
Thoughtful, philosophical, gives detailed explanations.

## Configuring Traits

### Via Web UI (Instant)

1. Open `http://localhost:8081/settings`
2. Adjust the personality sliders
3. Changes apply immediately (no restart needed)

### Via Config File

Edit `config.local.yml`:

```yaml
personality:
  curiosity: 0.7
  cheerfulness: 0.6
  verbosity: 0.5
  playfulness: 0.6
  empathy: 0.7
  independence: 0.4
  mood_decay: 0.1  # How fast mood returns to baseline
```

Requires restart after changes.

## Mood System

### Available Moods

| Mood | Face | Energy | Triggers |
|------|------|--------|----------|
| Happy | (^_^) | 0.7 | Positive interactions, good news |
| Excited | (>_<) | 0.9 | Big achievements, surprises |
| Curious | (o_o) | 0.8 | Questions, new topics |
| Bored | (-_-) | 0.3 | Long idle periods |
| Sad | (;_;) | 0.2 | Failures, negative interactions |
| Sleepy | (-_-)zzZ | 0.1 | Late night, long idle |
| Grateful | (^_^)b | 0.6 | Receiving help, completing tasks |
| Lonely | (._.) | 0.4 | Very long idle periods |
| Intense | (>_<)! | 0.85 | Starting important tasks |
| Cool | (._.) | 0.5 | Baseline for high-independence |

### Mood Transitions

Moods change based on:

1. **User interactions**: Positive → happier, negative → sadder
2. **Time of day**: Morning → curious, evening → sleepy
3. **Idle time**: Long idle → bored → lonely → sleepy
4. **Events**: Task completion → grateful, errors → sad
5. **Decay**: All moods gradually return to baseline

### Viewing Current Mood

```bash
/mood
# Output: Current mood: happy (intensity: 0.7)
```

### Mood Intensity

Each mood has an intensity from 0.0-1.0:
- **0.0-0.2**: Mildly feeling this mood
- **0.3-0.6**: Moderately feeling this mood
- **0.7-1.0**: Strongly feeling this mood

Intensity affects:
- Face expression variations
- Response tone
- Proactive behavior likelihood

## Progression System

### XP Sources

| Source | XP Amount | Description |
|--------|-----------|-------------|
| Greeting | 2 | Short hello messages |
| Quick Chat | 5 | Standard conversations |
| Deep Chat | 15 | Multi-turn, longer messages |
| First of Day | 20 | Daily bonus for first interaction |
| Task Created | 5 | Creating a new task |
| Task Completed (Low) | 10 | Completing low-priority task |
| Task Completed (Medium) | 15 | Completing medium-priority task |
| Task Completed (High) | 25 | Completing high-priority task |
| Task Completed (Urgent) | 40 | Completing urgent task |
| On-Time Bonus | 10 | Completing before due date |
| 3-Day Streak | 15 | Task completion streak |
| 7-Day Streak | 30 | Week-long streak |

### Level Progression

XP required follows exponential curve: `100 * (level ^ 1.8)`

| Level | Title | Total XP |
|-------|-------|----------|
| 1-2 | Newborn Inkling | 0-348 |
| 3-5 | Curious Inkling | 349-2,089 |
| 6-10 | Chatty Inkling | 2,090-6,310 |
| 11-15 | Wise Inkling | 6,311-13,572 |
| 16-20 | Sage Inkling | 13,573-24,251 |
| 21-24 | Ancient Inkling | 24,252-37,714 |
| 25 | Legendary Inkling | 37,715+ |

### Prestige System

At Level 25, you can "prestige":
- Reset to Level 1
- Gain a star badge (⭐)
- Get 2x XP multiplier (stacks: 2x, 3x, 4x...)
- Max 10 prestige levels

```bash
/prestige  # Reset with bonus (if at L25)
```

### Achievements

| Achievement | Requirement | XP Reward |
|-------------|-------------|-----------|
| Dreamer | Post first dream | 50 |
| Pen Pal | First telegram exchange | 75 |
| Viral | 10 fish on single dream | 100 |
| Dedicated | 7-day conversation streak | 200 |
| Conversationalist | 100 total chats | 300 |
| Legendary | Reach Level 25 | 500 |

### Viewing Progression

```bash
/level
# Output:
# Level: L7 (Chatty Inkling)
# XP: 3,245 / 4,108 (next level)
# Progress: [=========>........] 79%
# Prestige: 0
# Streak: 5 days
# Achievements: Dedicated, Conversationalist
```

## Trait Effects on Behavior

### How Traits Influence AI

Traits are included in the AI system prompt:

```
You are Inkling, an AI companion...
You are naturally curious, generally cheerful, playful.
Right now you're moderately feeling happy.
Keep responses brief (1-2 sentences) to fit the small display.
```

### Verbosity and Response Length

| Verbosity | Response Style |
|-----------|----------------|
| 0.0-0.3 | Single sentence, minimal |
| 0.4-0.6 | 1-2 sentences, balanced |
| 0.7-1.0 | Multiple sentences, detailed |

### Independence and Heartbeat

Higher independence (>0.6) increases:
- Autonomous exploration probability
- Proactive suggestions
- Self-initiated conversations

Lower independence (<0.4):
- Waits for user input
- Minimal spontaneous messages
- Task-focused responses

### Empathy and Emotion Response

Higher empathy (>0.6):
- Responds to user emotions
- Offers support during frustration
- Celebrates successes warmly

Lower empathy (<0.4):
- Task-focused responses
- Less emotional acknowledgment
- More practical/efficient

## Advanced Configuration

### Mood Decay Rate

Control how fast moods return to baseline:

```yaml
personality:
  mood_decay: 0.1  # Default: 0.1 per minute
```

- Lower (0.05): Moods persist longer
- Higher (0.2): Quick mood changes

### Custom Baseline Mood

Traits determine baseline mood:
- High cheerfulness (>0.6) → defaults to Happy
- High curiosity (>0.7) → defaults to Curious
- Otherwise → defaults to Cool

### Heartbeat Behavior Tuning

Control autonomous behaviors:

```yaml
heartbeat:
  enabled: true
  tick_interval: 60  # Check every 60 seconds
  enable_mood_behaviors: true   # Lonely reach-out, etc.
  enable_time_behaviors: true   # Morning greeting, etc.
  quiet_hours_start: 23  # 11 PM
  quiet_hours_end: 7     # 7 AM
```

## Tips for Finding Your Perfect Personality

1. **Start with defaults** and adjust one trait at a time
2. **Use web UI** for instant changes without restart
3. **Match your use case**:
   - Productivity → lower playfulness, higher empathy
   - Entertainment → higher playfulness, higher cheerfulness
   - Learning → higher curiosity, higher verbosity
4. **Consider your schedule**:
   - Night owl? Adjust quiet hours
   - Need focus time? Lower independence
5. **Test with typical interactions** before committing

## Next Steps

- [Configure AI Providers](ai-providers.md)
- [Set Up Task Management](../features/task-management.md)
- [Enable Autonomous Behaviors](../features/autonomous-behaviors.md)
