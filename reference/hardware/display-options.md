# Display Options Guide

Configure and optimize e-ink displays for Inkling, including different models and mock displays for development.

## Supported Displays

### Waveshare 2.13" V3 (Recommended)

**Specifications:**
- Resolution: 250x122 pixels
- Size: 2.13 inches diagonal
- Colors: Black and white
- Refresh: Full and partial
- Interface: SPI

**Pros:**
- Partial refresh (fast updates)
- Lower ghosting with partial
- Good availability

**Cons:**
- Older model
- Occasional ghosting

**Config:**
```yaml
display:
  type: "v3"  # Or "auto"
  width: 250
  height: 122
  min_refresh_interval: 0.5
  partial_refresh: true
```

### Waveshare 2.13" V4

**Specifications:**
- Resolution: 250x122 pixels
- Size: 2.13 inches diagonal
- Colors: Black and white
- Refresh: Full only
- Interface: SPI

**Pros:**
- Newer hardware
- Cleaner display
- Less ghosting

**Cons:**
- No partial refresh (slower)
- Longer minimum refresh interval

**Config:**
```yaml
display:
  type: "v4"  # Or "auto"
  width: 250
  height: 122
  min_refresh_interval: 5.0  # Required for V4!
  partial_refresh: false
```

### Mock Display (Development)

For development without hardware:

**Config:**
```yaml
display:
  type: "mock"
  width: 250
  height: 122
  min_refresh_interval: 0.5
```

**Output:**
- Renders to terminal (ASCII art)
- Can output to image file
- Instant "refresh"

## Auto-Detection

Inkling can detect display version automatically:

```yaml
display:
  type: "auto"
```

**Detection process:**
1. Try V3 initialization
2. If fails, try V4
3. If no hardware, fall back to mock

## Display Configuration

### Full Configuration

```yaml
display:
  # Display type: auto, v3, v4, or mock
  type: "auto"

  # Dimensions (rotated for landscape)
  width: 250
  height: 122

  # Refresh settings
  min_refresh_interval: 5.0  # Seconds between refreshes
  partial_refresh: true      # V3 only

  # Advanced
  rotation: 0                # 0, 90, 180, 270
  inverted: false           # Invert colors
```

### Refresh Rate Protection

E-ink displays can be damaged by too-frequent refreshes:

| Display | Safe Interval | Damage Risk Below |
|---------|---------------|-------------------|
| V3 (partial) | 0.5s | 0.2s |
| V3 (full) | 2.0s | 1.0s |
| V4 | 5.0s | 3.0s |

Inkling enforces minimum intervals automatically.

## Layout System

### Screen Layout

```
┌─────────────────────────────────────────────┐
│  HeaderBar (14px)                           │
│  - Face, Name, Uptime                       │
├─────────────────────────────────────────────┤
│                                             │
│  MessagePanel (86px)                        │
│  - Centered text                            │
│  - Word-wrapped at ~40 chars                │
│  - Auto-pagination for long messages        │
│                                             │
├─────────────────────────────────────────────┤
│  FooterBar (22px)                           │
│  - Mood, Level, Stats, Mode                 │
└─────────────────────────────────────────────┘
```

### Font Rendering

Inkling uses bitmap fonts for e-ink:
- **Header**: 14px DejaVu Sans
- **Message**: 12px DejaVu Sans
- **Footer**: 10px DejaVu Sans Mono

### Text Centering

Messages are centered both horizontally and vertically:

```python
# Horizontal centering per line
x = (screen_width - text_width) // 2

# Vertical centering for text block
y = (panel_height - block_height) // 2
```

## Refresh Types

### Full Refresh

Entire screen flashes black/white before updating:
- Clears all ghosting
- Takes 2-3 seconds
- Used by V4 always, V3 periodically

### Partial Refresh (V3 only)

Updates only changed pixels:
- Fast (~0.3 seconds)
- May accumulate ghosting
- Best for small changes

### Refresh Strategy

Inkling uses hybrid approach for V3:

```python
# Partial refresh for most updates
# Full refresh every 10 partial refreshes
# Full refresh on major content changes
```

## Display Commands

### Test Faces

```bash
/face happy
/face excited
/faces        # List all faces
```

### Force Refresh

```bash
/refresh      # Trigger full display refresh
```

### Display Demo

```bash
python main.py --mode demo
```

Shows:
1. All face expressions
2. Text rendering test
3. Layout components

## Troubleshooting

### Display Shows Nothing

1. **Check SPI is enabled:**
   ```bash
   ls /dev/spi*
   # Should show spidev0.0, spidev0.1
   ```

2. **Check wiring:**
   - Verify HAT is fully seated
   - Check GPIO alignment

3. **Force display type:**
   ```yaml
   display:
     type: "v3"  # Try v3 or v4 explicitly
   ```

4. **Run with debug:**
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

### Display Shows Garbage

1. **Wrong display version:**
   - V3 code on V4 hardware or vice versa
   - Try other display type

2. **Bad SPI connection:**
   - Reseat HAT
   - Check for bent pins

3. **Incorrect rotation:**
   ```yaml
   display:
     rotation: 180  # Try different values
   ```

### Ghosting (V3)

Ghost images from previous content:

1. **Use full refresh periodically:**
   - Already automatic
   - Manual: `/refresh`

2. **Reduce partial refreshes:**
   ```yaml
   display:
     partial_refresh: false  # Use full refresh only
   ```

3. **Clear display:**
   ```python
   # Fill with white, wait, fill with black, wait, fill with white
   ```

### Slow Response

1. **V4 has minimum 5s refresh:**
   - This is by design
   - Can't be reduced

2. **Lower display operations:**
   - Batch updates
   - Reduce refresh frequency

3. **Use V3 for faster updates:**
   - Partial refresh = faster

### Permission Denied

```bash
# Add user to spi and gpio groups
sudo usermod -aG spi,gpio $USER

# Logout and login, or:
newgrp spi
newgrp gpio
```

## Display Driver Details

### V3 Driver

```
EPD class: Waveshare_epd.epd2in13_V3
Partial refresh: Yes
LUT: Variable (partial/full)
Gray levels: 2 (black/white)
```

### V4 Driver

```
EPD class: Waveshare_epd.epd2in13_V4
Partial refresh: No
LUT: Fixed (full only)
Gray levels: 2 (black/white)
```

### Mock Driver

```
Class: MockDisplay
Output: Terminal ASCII art
Refresh: Instant
```

## Alternative Displays

### Larger E-Ink (Future)

Potentially supported with modifications:
- Waveshare 2.9" (296x128)
- Waveshare 3.7" (480x280)
- Waveshare 4.2" (400x300)

Would require:
- Different layout calculations
- New display drivers
- Updated UI components

### Color E-Ink

Not currently supported:
- Waveshare 2.13" (B) - Black/White/Red
- Slower refresh times
- More expensive

### Non-E-Ink

Inkling is designed for e-ink but could work with:
- OLED displays (different power/refresh)
- LCD screens (no sunlight visibility)
- LED matrices (very low resolution)

## Performance Tips

1. **Batch updates:**
   - Combine multiple text changes
   - Refresh once after all changes

2. **Use appropriate display:**
   - V3 for interactive use
   - V4 for always-on display

3. **Minimize refreshes:**
   - Don't update if content unchanged
   - Increase tick interval

4. **Mock for development:**
   - Much faster iteration
   - No hardware needed

## Next Steps

- [Hardware Assembly](../getting-started/hardware-assembly.md)
- [Build an Enclosure](enclosures.md)
- [Themes & Appearance](../configuration/themes-appearance.md)
