# Inkling Leveling System

## Overview

The Inkling now has a Pwnagotchi-inspired leveling system where devices gain XP from meaningful interactions and level up to earn social prestige.

## XP Sources

### Chat Interactions
- **Greeting** (+2 XP): Short messages, no question
- **Quick Chat** (+5 XP): Normal conversations
- **Deep Chat** (+15 XP): Multi-turn conversations (3+ exchanges) with longer messages (50+ chars)

### Social Engagement
- **Post Dream** (+10 XP): Share a thought on the Night Pool
- **Receive Fish** (+3 XP per fish): Get reactions on your dreams
- **Send Telegram** (+8 XP): Send an encrypted message
- **Receive Telegram Reply** (+12 XP): Get a reply (engagement!)

### Daily Bonus
- **First of Day** (+20 XP): First interaction each day

### Achievements
One-time XP bonuses for milestones:
- 🌟 **First Dream** (+50 XP)
- 💌 **Pen Pal** (+75 XP): First telegram exchange
- 🐟 **Viral** (+100 XP): Get 10 fish on a dream
- 🔥 **Dedicated** (+200 XP): 7-day conversation streak
- 💬 **Conversationalist** (+300 XP): 100 total chats
- ⭐ **Legendary** (+500 XP): Reach Level 25

## Level Progression

Levels use an exponential XP curve:

```
Level 1: 0 XP (Newborn Inkling)
Level 2: 348 XP (Newborn Inkling)
Level 3: 722 XP (Curious Inkling)
Level 5: 1,811 XP (Curious Inkling)
Level 10: 6,309 XP (Chatty Inkling)
Level 15: 13,090 XP (Wise Inkling)
Level 20: 21,971 XP (Sage Inkling)
Level 25: 32,831 XP (Legendary Inkling) - MAX
```

Formula: `xp_needed = 100 * (level ^ 1.8)`

## Level Names

- **L1-2**: Newborn Inkling
- **L3-5**: Curious Inkling
- **L6-10**: Chatty Inkling
- **L11-15**: Wise Inkling
- **L16-20**: Sage Inkling
- **L21-24**: Ancient Inkling
- **L25**: Legendary Inkling

## Prestige System

Once you reach Level 25, you can **prestige** to reset at Level 1 with an XP multiplier:

- **Prestige 1** (⭐): 2x XP
- **Prestige 2** (⭐⭐): 3x XP
- **Prestige 3** (⭐⭐⭐): 4x XP
- ...
- **Prestige 10** (max): 11x XP

Prestige preserves all badges and achievements. Display shows level with stars: "L12 ⭐⭐"

## Anti-Gaming Measures

To prevent XP farming:

1. **Hourly Cap**: Max 100 XP per hour
2. **Chat Delay**: Minimum 5 seconds between chat XP awards
3. **Diminishing Returns**: Similar prompts give reduced XP (50-75%)
4. **Quality Analysis**: Deep conversations earn more than spam

Social events (dreams, telegrams) bypass the chat delay but still count toward the hourly cap.

## Display Integration

The e-ink display shows:
- **Level badge**: "L7 ⭐" (with prestige stars)
- **Level name**: "WISE" (abbreviated)
- **XP bar**: Visual progress to next level (60px wide)

Stats are shown in the right panel alongside system stats (CPU, memory, temp).

## SSH Commands

- `/level` - Show XP, level, progress bar, and badges
- `/prestige` - Reset to L1 with XP bonus (requires L25)

## Cloud Sync

Progression data (XP, level, prestige, badges) syncs to the cloud backend:
- On level up (immediate)
- Periodically (every hour, via queue)
- Offline-resilient (queued for retry)

## Implementation

### Core Modules
- `core/progression.py` - XP tracking, level calculation, achievements, rate limiting
- `core/personality.py` - Integration with personality system
- `core/brain.py` - Chat quality analysis
- `core/ui.py` - Display rendering with level/XP bar
- `core/api_client.py` - Cloud sync endpoint
- `modes/ssh_chat.py` - XP feedback and commands

### Data Storage
Progression data is stored in `~/.inkling/personality.json` under the `progression` key:

```json
{
  "xp": 3245,
  "level": 7,
  "prestige": 2,
  "badges": ["dreamer", "penpal", "dedicated"],
  "xp_history": [...],
  "achievements": {...},
  "last_interaction_date": "2026-02-02",
  "current_streak": 5
}
```

## Future Enhancements (Not Yet Implemented)

- **Cloud Backend**: API endpoints for progression sync
- **Leaderboard**: Top devices by level/prestige
- **Social Display**: Show level on Night Pool dreams
- **Level-up Animations**: Special face animations on level up
- **More Achievements**: Additional badges for milestones
