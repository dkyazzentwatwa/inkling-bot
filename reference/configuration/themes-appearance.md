# Themes & Appearance Guide

Customize the look and feel of Inkling's web UI and display.

## Web UI Themes

### Built-in Themes

The web UI supports multiple color themes:

| Theme | Description |
|-------|-------------|
| **Light** | Clean white background, dark text |
| **Dark** | Dark background, light text (default) |
| **Midnight** | Deep blue/purple dark theme |
| **Forest** | Green-tinted nature theme |
| **Sunset** | Warm orange/red tones |

### Changing Themes

**Via Web UI**:
1. Navigate to `http://localhost:8081/settings`
2. Select theme from dropdown
3. Changes apply instantly (saved to browser localStorage)

**Via JavaScript Console** (advanced):
```javascript
document.documentElement.setAttribute('data-theme', 'midnight');
localStorage.setItem('theme', 'midnight');
```

## Face Expressions

### Available Faces

Inkling uses ASCII faces that change with mood:

| Face | Name | Used For |
|------|------|----------|
| `(^_^)` | happy | Happy mood, success |
| `(>_<)` | excited | Excited mood, celebrations |
| `(o_o)` | curious | Curious mood, questions |
| `(-_-)` | bored | Bored mood, idle |
| `(;_;)` | sad | Sad mood, failures |
| `(-_-)zzZ` | sleep | Sleepy mood, night |
| `(^_^)b` | grateful | Grateful mood, thanks |
| `(._.)` | lonely | Lonely mood, long idle |
| `(>_<)!` | intense | Intense mood, focus |
| `(._.)~` | cool | Cool mood, baseline |
| `(@_@)` | confused | Errors, unexpected |
| `(^o^)` | success | Task completion |
| `(._.)...` | working | Processing, thinking |

### Testing Faces

```bash
/face happy
/face excited
/faces  # List all available faces
```

### ASCII vs Unicode Faces

**E-ink displays** (V3/V4): Use ASCII faces for better rendering
**Mock/Web displays**: Can use Unicode faces for prettier appearance

This is handled automatically by `DisplayManager._prefer_ascii_faces`.

## Display Layout

### E-Ink Layout (122px x 250px)

```
┌─────────────────────────────────────────────┐
│  (^_^)  Inkling                     1h 23m  │  ← HeaderBar (14px)
├─────────────────────────────────────────────┤
│                                             │
│                                             │
│           Hello! How can I                  │  ← MessagePanel (86px)
│              help you?                      │     ~40 chars/line
│                                             │     6 lines max
│                                             │
├─────────────────────────────────────────────┤
│ (^_^) | L7 CHAT | 54%mem 1%cpu 43° | SSH    │  ← FooterBar (22px)
└─────────────────────────────────────────────┘
```

### Component Details

**HeaderBar** (14px):
- Face expression
- Device name
- Uptime

**MessagePanel** (86px):
- Centered text (horizontal and vertical)
- Word-wrapped at ~40 characters
- Auto-pagination for long messages

**FooterBar** (22px):
- Mood face
- Level and title
- System stats
- Current mode

## Web UI Layout

### Main Chat Page

```
┌─────────────────────────────────────────────┐
│  Inkling        [Settings] [Tasks] [Files]  │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ (^_^)                               │   │
│  │                                     │   │
│  │     Hello! How are you today?       │   │
│  │                                     │   │
│  │ L7 CURIOUS | 45% to L8 | 3-day      │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Type a message...          [Send]   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [/help] [/tasks] [/mood] [/level]         │
└─────────────────────────────────────────────┘
```

### Settings Page

Accessible at `/settings`:
- Device name editor
- Personality trait sliders (6 sliders, 0-100%)
- AI configuration (provider, model, tokens)
- Theme selector

### Tasks Page (Kanban)

Accessible at `/tasks`:
- Three columns: Pending, In Progress, Completed
- Drag-and-drop between columns
- Quick add form
- Filter by project/tags

## Customizing the Display

### Device Name

Change your Inkling's name:

**Via Web UI**:
1. Go to Settings
2. Edit "Device Name"
3. Save (requires restart for AI changes)

**Via Config**:
```yaml
device:
  name: "Pixel"  # Or any name you like
```

### Status Bar Customization

The footer bar format is:
```
(face) | Level Title | stats | Mode
```

Example outputs:
```
(^_^) | L1 NEWB | 54%mem 1%cpu 43° | CHAT3 | SSH
(o_o) | L7 CHAT | 32%mem 5%cpu 51° | CHAT12 | WEB
```

### Message Display

Messages auto-paginate when too long:
- 6 lines max per page
- 3-second delay between pages
- Automatic word wrapping

Configure in code (advanced):
```python
# In core/display.py
MESSAGE_PANEL_HEIGHT = 86  # pixels
CHARS_PER_LINE = 40
LINES_PER_PAGE = 6
PAGE_DELAY = 3.0  # seconds
```

## CSS Theme Variables

For advanced customization, the web UI uses CSS variables:

```css
:root[data-theme="dark"] {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --text-primary: #eaeaea;
  --text-secondary: #a0a0a0;
  --accent: #e94560;
  --success: #4ecca3;
  --warning: #ffc107;
  --border: #2a2a4a;
}
```

### Creating Custom Themes

Add to web template (in `modes/web_chat.py`):

```css
:root[data-theme="custom"] {
  --bg-primary: #your-color;
  --bg-secondary: #your-color;
  --text-primary: #your-color;
  --text-secondary: #your-color;
  --accent: #your-color;
  --success: #your-color;
  --warning: #your-color;
  --border: #your-color;
}
```

## Refresh Rate & Display Protection

### E-Ink Considerations

E-ink displays can be damaged by frequent refreshes:

| Display | Min Interval | Refresh Type |
|---------|--------------|--------------|
| V3 | 0.5s | Partial (fast) |
| V4 | 5.0s | Full only |
| Mock | 0.5s | Instant |

### Configured in Display Manager

```yaml
display:
  min_refresh_interval: 5.0  # seconds
  partial_refresh: true      # V3 only
```

### Ghosting Prevention

For V3 displays, periodic full refresh prevents ghosting:
- Every 10 partial refreshes
- Handled automatically

## Accessibility

### Font Sizes

Web UI uses responsive font sizing:
- Desktop: 16px base
- Mobile: 14px base
- All sizes scale with browser zoom

### High Contrast

Use "Light" theme for maximum contrast, or create custom high-contrast theme.

### Screen Reader Support

Web UI includes:
- Semantic HTML
- ARIA labels on interactive elements
- Focus indicators

## Mobile Support

The web UI is responsive:
- Chat interface adapts to screen width
- Touch-friendly buttons
- Swipe support on Kanban board

Access from any device:
```
http://inkling.local:8081
# Or use IP address
http://192.168.1.x:8081
```

## Tips

1. **E-ink**: Stick to high-contrast ASCII faces
2. **Web**: Use dark theme to reduce eye strain
3. **Kanban**: Works great on tablets
4. **Mobile**: Bookmark for quick access

## Next Steps

- [Tune Personality](personality-tuning.md)
- [Set Up Task Management](../features/task-management.md)
- [Build an Enclosure](../hardware/enclosures.md)
