# Screen Saver & Dark Mode Testing Guide

This document provides instructions for testing the newly implemented screen saver and dark mode features.

## Quick Test with Test Script

The fastest way to verify the implementation:

```bash
source .venv/bin/activate
python test_screensaver.py
```

This automated test will:
1. Test dark mode toggle (normal → dark → normal)
2. Test screen saver activation after idle timeout
3. Test screen saver page cycling (stats, quotes, faces, progression)
4. Test screen saver commands (on/off/toggle)

Expected output: All tests should pass with "All tests completed successfully!" message.

## Manual Testing with SSH Mode

### Setup

1. Copy test configuration:
```bash
cp config.test.yml config.local.yml
```

2. Start in SSH mode:
```bash
source .venv/bin/activate
python main.py --mode ssh
```

### Test 1: Dark Mode Toggle

Test the `/darkmode` command with different arguments:

```bash
# Toggle dark mode on
/darkmode on

# Display should show inverted colors (white-on-black)
# Mock display will show inverted ASCII art

# Toggle back to normal
/darkmode off

# Display should return to normal (black-on-white)

# Toggle without argument (switches state)
/darkmode
```

**Expected Results:**
- Display colors invert when dark mode is enabled
- Changes apply immediately with force refresh
- Commands print confirmation messages (✓ Dark mode enabled/disabled)

### Test 2: Screen Saver Manual Control

Test the `/screensaver` command:

```bash
# Enable screen saver
/screensaver on

# Disable screen saver
/screensaver off

# Toggle without argument
/screensaver
```

**Expected Results:**
- Commands print confirmation messages (✓ Screen saver enabled/disabled)
- Settings persist until changed

### Test 3: Screen Saver Auto-Activation

The screen saver should automatically activate after 30 seconds of idle time (configured in config.test.yml):

1. Start SSH chat mode
2. Wait 30 seconds without sending any messages
3. Screen saver should activate automatically
4. Display will cycle through pages every 3 seconds:
   - **Stats page**: System stats (CPU, memory, temp, uptime)
   - **Quote page**: Inspirational quote
   - **Faces page**: Random face expression
   - **Progression page**: XP/level progress

5. Send any message to exit screen saver
6. Display returns to normal chat mode

**Expected Results:**
- Screen saver activates after 30 seconds idle
- Pages cycle automatically every 3 seconds
- Heartbeat log shows: `[Heartbeat] Activating screen saver (idle detected)`
- User interaction stops screen saver immediately
- Screen saver doesn't re-activate until another idle period

### Test 4: Screen Saver + Dark Mode Combined

Test both features together:

```bash
# Enable dark mode
/darkmode on

# Wait 30 seconds for screen saver to activate
# (or disable temporarily with /screensaver off)

# Screen saver pages should display in dark mode
```

**Expected Results:**
- Screen saver pages render with inverted colors when dark mode is enabled
- Both features work independently and together

### Test 5: Configuration Testing

Edit `config.local.yml` to test different settings:

```yaml
display:
  # Test dark mode default
  dark_mode: true  # Start with dark mode enabled

  screensaver:
    enabled: true
    idle_timeout_minutes: 1  # Change to 1 minute
    page_duration_seconds: 5  # Change to 5 seconds
    pages:
      - type: "stats"  # Show only stats page
```

Restart the app and verify:
- Dark mode is enabled on startup
- Screen saver uses new timeout and duration
- Only configured pages are shown

## Expected Display Output (Mock Mode)

### Normal Mode (Black-on-White)
```
================================================================================
#...............................................................................
: ::.:.:...::.:..   #::.......... .
: :#.@::#:#:#.:.:   @::#:@@.@@.@:@.
#.........................:..:..::..............................................
[... message content ...]
```

### Dark Mode (White-on-Black) - Inverted
```
================================================================================
:###############################################################################
:@::@###@##::@##@@@@.:###@##@##@#@#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
:@::@.:::::::@###@@@ ::::  #. #.: #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
:#########################:##:###:##############################################
[... inverted message content ...]
```

## Troubleshooting

### Screen Saver Not Activating
- Check config: `screensaver.enabled: true`
- Verify idle timeout: `idle_timeout_minutes` must pass without user interaction
- Check heartbeat is running: `heartbeat.enabled: true`
- Heartbeat tick interval: Must be <= idle timeout for detection

### Dark Mode Not Working
- Verify PIL/ImageOps is available: `python -c "from PIL import ImageOps; print('OK')"`
- Check display driver supports 1-bit images
- Try force refresh: `/refresh` command

### Commands Not Found
- Verify commands are registered in `core/commands.py`
- Check command handlers exist in mode files (ssh_chat.py, web_chat.py)
- Restart the application to reload command registry

## Configuration Reference

### Display Settings

```yaml
display:
  # Dark mode (inverted colors: white-on-black instead of black-on-white)
  dark_mode: false  # true to enable by default

  # Screen saver settings
  screensaver:
    enabled: true  # Set to false to disable screen saver
    idle_timeout_minutes: 5  # Activate after 5 minutes of idle time
    page_duration_seconds: 10  # Time to show each page before cycling
    pages:
      - type: "stats"         # System stats summary (CPU, memory, temp, uptime)
      - type: "quote"         # AI-generated thoughtful quote
      - type: "faces"         # Random face expressions
      - type: "progression"   # XP/level progress
```

### Page Types

1. **stats** - System statistics
   - Uptime
   - CPU usage
   - Memory usage
   - Temperature

2. **quote** - Inspirational quotes
   - Predefined philosophical quotes
   - Optional: AI-generated (requires Brain integration)

3. **faces** - Face expressions
   - Shows random face from FACES dictionary
   - Displays face ASCII art

4. **progression** - XP and leveling
   - Current level and title
   - Progress percentage to next level
   - XP needed for next level
   - Total XP earned

## Performance Notes

### E-ink Display Health
- Screen saver respects `min_refresh_interval` settings
- V3 displays: 0.5s minimum (partial refresh)
- V4 displays: 5.0s minimum (full refresh only)
- No additional wear compared to normal operation

### Battery Impact
- Dark mode has no battery impact on e-ink displays (same power for black/white pixels)
- Screen saver uses existing display refresh mechanisms
- No additional background processing beyond heartbeat tick

### Memory Usage
- Screen saver state: ~100 bytes
- No images cached in memory
- Renders on-demand per page cycle

## Known Limitations

1. **AI Quote Generation**: Currently uses predefined quotes. Brain integration for AI-generated quotes is optional and commented out in `_get_screensaver_quote()`.

2. **Face Preference**: Screen saver uses the same face preference (ASCII vs Unicode) as the main display.

3. **Page Customization**: Page types are hardcoded. Future enhancement: custom page plugins.

4. **V4 Display Looping**: Full refresh displays (V4) may show only one page if refresh rate is too slow for comfortable cycling.

## Future Enhancements

Potential improvements (not yet implemented):

1. **Custom Screen Saver Pages**:
   - Weather display (with API integration)
   - Calendar/schedule view
   - Task list summary
   - Friend activity (if social features re-added)

2. **Animated Screen Savers**:
   - Bouncing face animation
   - Matrix rain effect
   - Starfield animation

3. **Smart Triggers**:
   - Time-based activation (e.g., activate at specific times)
   - Battery-based (activate when charging)
   - Context-aware (different pages for different times of day)

4. **Dark Mode Schedule**:
   - Auto-enable dark mode at night
   - Configurable hours for light/dark themes

## Rollback Instructions

If issues arise with the new features:

1. **Disable Screen Saver**:
```yaml
display:
  screensaver:
    enabled: false
```

2. **Disable Dark Mode**:
```yaml
display:
  dark_mode: false
```

Or via commands:
```bash
/screensaver off
/darkmode off
```

3. **Remove Screen Saver Check** (temporary):
Comment out in `core/heartbeat.py` line ~325:
```python
# if self.display and self.display.should_activate_screensaver():
#     await self.display.start_screensaver()
```

4. **Revert to Previous Version** (if needed):
```bash
git revert <commit-hash>
```
