# Emoji Face Animation Design

**Date:** 2026-02-08
**Status:** Approved for implementation

## Problem Statement

The current sprite system has several issues:
1. PNG sprite animations show as circles (emoji fallback) instead of actual animations
2. Face doesn't animate when idle - appears static
3. Face displays during AI responses, reducing available text space
4. User prefers emoji text faces over PNG sprites for aesthetic appeal

## Goals

1. **Animated idle face** - Emoji face cycles through expressions when no message text
2. **Hide face during messages** - Maximize text area for AI responses (6+ lines vs 2 lines)
3. **Action command sequences** - Show themed emoji faces during /walk, /dance, etc.
4. **Remove PNG sprite system** - Disable gracefully, keep code dormant for future use

## Design

### 1. Idle Face Animation System

**Mood-Based Expression Sets:**

Each mood has its own set of related emoji faces that cycle every 3-5 seconds:

```python
IDLE_FACE_SEQUENCES = {
    "happy": ["(^_^)", "(^_~)", "(^ω^)", "(^_^)"],
    "excited": ["(*^_^*)", "(^o^)", "(*^ω^*)", "(*^_^*)"],
    "grateful": ["(^_^)b", "(^_~)b", "(^_^)b"],
    "curious": ["(o_O)?", "(O_o)?", "(o_O)?"],
    "sleepy": ["(-_-)zzZ", "(-.-)zzZ", "(-_-)zzZ"],
    "bored": ["(-_-)", "(-_~)", "(-_-)"],
    "sad": ["(;_;)", "(T_T)", "(;_;)"],
    "cool": ["( -_-)", "( ~_-)", "( -_-)"],
    "intense": ["(>_<)", "(>_<#)", "(>_<)"],
    # Add remaining moods...
}
```

**Animation Logic:**

- Track current index in face sequence
- Update every 3-5 seconds (randomized slightly for naturalness)
- Wrap around to beginning when reaching end
- Only animate when face is visible (no message text)

**Hiding Logic:**

In `FaceSprite.render()`:
```python
if ctx.message and ctx.message.strip():
    # Message present - don't render face, maximize text area
    return (0, 0)

# No message - show animated idle face
```

### 2. Action Command Face Sequences

**Action-Specific Sequences:**

Each action has a themed sequence of emoji faces:

```python
ACTION_FACE_SEQUENCES = {
    "walk": ["(o_O)?", "(^_^)", "(o_O)?", "(^_^)"],      # Looking around
    "dance": ["(*^_^*)", "(^o^)", "(*^ω^*)", "(^o^)"],    # Excited dancing
    "exercise": ["(>_<)", "(^_^)", "(>_<)", "(^_^)b"],    # Effort + success
    "play": ["(^_^)", "(^_~)", "(*^_^*)", "(^_^)"],       # Happy playful
    "pet": ["(^_^)", "(*^_^*)", "(^ω^)", "(*^_^*)"],      # Loving it
    "rest": ["(^_^)", "(-_-)", "(-.-)zzZ"],               # Calming down
}
```

**Playback in `_play_action()`:**

1. Get action sequence from `ACTION_FACE_SEQUENCES`
2. Iterate through faces with 0.8s delay between each
3. Show action text (e.g., "Walk!") with each face
4. After sequence completes, display automatically resumes idle animation

**Remove sprite calls:**
- Remove `self.display.set_animation(action_name, mood_key)`
- Remove `self.display.set_animation("idle", mood_key)`

### 3. AI Response Pagination

**Current behavior is correct** - `show_message_paginated()` already:
- Splits text into pages of `MESSAGE_MAX_LINES`
- Shows page indicators `[1/3]`
- Waits 3 seconds between pages

**The fix:** Once face is hidden when message present:
- Message area height increases from ~28px to ~86px
- Available lines increase from ~2 to ~6
- Pagination naturally shows more text per page

**No code changes needed** - hiding the face automatically provides the space.

### 4. Remove PNG Sprite System

**Graceful Disable (keep code for future):**

**In `core/display.py` (DisplayManager):**
- Remove or comment out sprite_manager initialization
- Pass `sprite_manager=None` to PwnagotchiUI

**In `core/ui.py` (FaceSprite):**
- Remove sprite_manager dependency from __init__
- Remove `get_animation_frame()` calls
- Remove PNG loading logic
- Keep only text-based emoji rendering
- Optionally rename to `AnimatedFace` for clarity

**Keep dormant:**
- `core/sprites.py` - File remains but unused
- `assets/sprites/` - Directory kept for future use

## Implementation Plan

### Phase 1: Add Face Animation Data
1. Define `IDLE_FACE_SEQUENCES` dict in `core/ui.py`
2. Define `ACTION_FACE_SEQUENCES` dict in `core/ui.py`
3. Add animation state tracking to FaceSprite (index, timer)

### Phase 2: Implement Face Hiding Logic
1. Modify `FaceSprite.render()` to check `ctx.message`
2. Return early if message text present (don't render face)
3. Test with AI responses - verify face disappears

### Phase 3: Implement Idle Animation
1. Add timer logic to FaceSprite
2. Cycle through current mood's face sequence
3. Update face every 3-5 seconds
4. Test idle animation with different moods

### Phase 4: Fix Action Commands
1. Update `_play_action()` to use `ACTION_FACE_SEQUENCES`
2. Remove `set_animation()` calls
3. Test each action (/walk, /dance, etc.)
4. Verify return to idle animation after action

### Phase 5: Disable Sprite System
1. Comment out sprite_manager initialization in DisplayManager
2. Simplify FaceSprite to remove sprite loading
3. Clean up unused imports
4. Test full flow: idle → action → AI response → idle

## Success Criteria

✅ Idle face animates slowly through mood-appropriate expressions (3-5s intervals)
✅ Face disappears when AI responds, showing 6+ lines of text
✅ Action commands show themed emoji face sequences
✅ Actions return to idle animation when complete
✅ No PNG sprite loading (system disabled cleanly)
✅ Code can easily re-enable sprites in future if desired

## Benefits

- **Better UX:** Animated idle face adds personality and liveliness
- **More readable:** AI responses show 6+ lines instead of 2
- **Simpler code:** No PNG loading, faster rendering
- **User preference:** Matches desired aesthetic (emoji faces over sprites)
- **Future-proof:** Can re-enable sprites later without major refactor

## Files Modified

- `core/ui.py` - Add face sequences, animation logic, hiding logic
- `core/display.py` - Remove sprite_manager initialization
- `modes/ssh_chat.py` - Update action commands to use emoji sequences
