# Play Commands - Energy & Gamification System

## Overview

The play commands system adds interactive play activities that boost energy and award XP. It provides a foundation for gamification and mini-games while keeping Inkling engaged and energetic.

## Available Commands

| Command | Description | Mood Effect | Energy | XP | Animation |
|---------|-------------|-------------|--------|----|-----------|
| `/walk` | Go for a walk | Curious (70%) | +~45% | +3 | look_l → look_r → happy |
| `/dance` | Dance around | Excited (90%) | +~65% | +5 | excited → love → wink → excited |
| `/exercise` | Exercise & stretch | Happy (80%) | +~55% | +5 | working → intense → awake → success |
| `/play` | Play with a toy | Happy (80%) | +~55% | +4 | excited → happy → wink |
| `/pet` | Get petted | Grateful (70%) | +~40% | +3 | love → happy → grateful |
| `/rest` | Take a short rest | Cool (40%) | -~10% | +2 | cool → sleep → sleepy |

## Features

### Energy System
- **Energy = Mood Energy × Mood Intensity**
- Mood energy values:
  - Excited: 90%
  - Curious: 80%
  - Happy: 70%
  - Grateful: 60%
  - Cool: 50%
  - Bored: 30%
  - Sleepy: 10%
- Play commands boost both mood and intensity → natural energy increase
- No separate energy stat needed

### XP Rewards
- Small XP rewards (2-5 XP per activity)
- Balanced with existing sources:
  - Greeting: 2 XP
  - Quick chat: 5 XP
  - Deep chat: 15 XP
  - Tasks: 10-40 XP
- Subject to rate limiting (max 100 XP/hour)

### Display Animations
- E-ink displays show 2-4 frame animations
- 0.8s delay between frames
- Works with rate limiting (V3: 0.5s, V4: 5.0s)
- SSH mode: Shows emotes in italic magenta
  - Example: `*Inkling goes for a walk around the neighborhood*`

### Interaction Tracking
- Updates `_last_interaction` timestamp
- Prevents boredom/sleepy moods
- Keeps Inkling engaged

## Usage Examples

### SSH Mode
```bash
$ /energy
Energy: [███░░░░░░░] 30%
Mood: Bored (intensity: 30%)
Mood base energy: 30%

Tip: Play commands (/walk, /dance, /exercise) boost energy!

$ /walk
*Inkling goes for a walk around the neighborhood*
+3 XP  Energy: 30% → 56% (+26%)

$ /dance
*Inkling dances enthusiastically*
+5 XP  Energy: 56% → 81% (+25%)

$ /energy
Energy: [████████░░] 81%
Mood: Excited (intensity: 90%)
Mood base energy: 90%
```

### Web Mode
Visit http://localhost:8081 and use commands in chat:

```
> /walk
*Inkling goes for a walk around the neighborhood*

✨ +3 XP | Energy +26%

> /dance
*Inkling dances enthusiastically*

✨ +5 XP | Energy +25%
```

## Implementation Details

### Files Modified
1. **`core/progression.py`** - Added 6 new XP sources
2. **`core/commands.py`** - Registered 6 play commands
3. **`modes/ssh_chat.py`** - Implemented SSH handlers with `_play_action()` helper
4. **`modes/web_chat.py`** - Implemented web handlers with `_play_action_web()` helper

### XP Sources
```python
class XPSource(Enum):
    PLAY_WALK = "play_walk"        # +3 XP
    PLAY_DANCE = "play_dance"      # +5 XP
    PLAY_EXERCISE = "play_exercise"  # +5 XP
    PLAY_GENERAL = "play_general"  # +4 XP
    PLAY_REST = "play_rest"        # +2 XP
    PLAY_PET = "play_pet"          # +3 XP
```

### Command Flow
1. Update `_last_interaction` timestamp
2. Show animation on e-ink display (2-4 frames)
3. Print SSH emote (if in SSH mode)
4. Set new mood and intensity
5. Award XP (subject to rate limiting)
6. Calculate and display energy change

### Rate Limiting
- Max 100 XP per hour across all sources
- 5s minimum between chat XP awards (doesn't apply to play)
- Diminishing returns for repeated actions
- Play commands can be used freely within hourly cap

## Future Extensions

### Mini-Games Framework
Once play commands are working, extend to:

**1. Reflex Game** (`/reflex`)
- Countdown: 3... 2... 1... GO!
- User types anything within time limit
- Faster = more XP + energy boost

**2. Memory Game** (`/memory`)
- Show sequence of faces
- User repeats sequence
- Longer sequences = more XP

**3. Mood Match** (`/moodmatch`)
- Display shows mood face
- User guesses mood name
- Correct = XP + energy

**4. Story Mode** (`/story`)
- AI generates choose-your-own-adventure
- User choices affect mood/energy
- XP for completion

### Configuration Options
Add to `config.yml`:
```yaml
gamification:
  play_commands_enabled: true
  play_xp_multiplier: 1.0      # Adjust XP rewards
  play_animation_speed: 0.8    # Seconds between frames
  play_cooldown_seconds: 30    # Prevent spam (optional)
```

## Testing

Run the test suite:
```bash
source .venv/bin/activate
python test_play_commands.py       # Unit tests
python test_play_integration.py    # Integration tests
```

All tests pass:
- ✅ XP sources defined
- ✅ Commands registered
- ✅ Energy calculation correct
- ✅ XP awards working
- ✅ Mood effects functional
- ✅ Handlers execute without errors

## Design Philosophy

### Why Not Separate Energy Stat?
Energy already exists as `mood.energy × mood.intensity`. Play commands boost both components naturally without duplicate tracking.

### Why Short Animations?
E-ink displays have refresh rate limits. 2-4 frame animations fit within constraints while feeling playful.

### Why Small XP Rewards?
Balance with existing XP economy. Play is engaging but shouldn't dominate progression over tasks/chat.

### Extensibility
This foundation enables:
- Complex mini-games
- Streaks and achievements
- Mood-specific activities
- Future multiplayer features

## Example Session

```
$ /energy
Energy: [█░░░░░░░░░] 10%
Mood: Sleepy (intensity: 50%)

$ /walk
*Inkling goes for a walk around the neighborhood*
+3 XP  Energy: 10% → 56% (+46%)

$ /exercise
*Inkling does some stretches and exercises*
+5 XP  Energy: 56% → 70% (+14%)

$ /dance
*Inkling dances enthusiastically*
+5 XP  Energy: 70% → 81% (+11%)

$ /level
Progression
  L1 - Newborn Inkling
  [██░░░░░░░░░░░░░░░░░░] 12%
  Total XP: 13  •  Next level: 87 XP

$ /energy
Energy: [████████░░] 81%
Mood: Excited (intensity: 90%)
Mood base energy: 90%

Tip: Play commands (/walk, /dance, /exercise) boost energy!
```

## Notes

- Play commands work in both SSH and web modes
- Animations respect display rate limiting
- XP rate limiting applies across all sources
- Energy changes are immediate and visible
- `/energy` command shows helpful tips
- SSH emotes use italic magenta color (ANSI 3;35m)
- Web responses show XP gain and energy change
