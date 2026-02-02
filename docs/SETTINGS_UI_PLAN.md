# Web UI Settings Editor - Implementation Plan

## Overview
Add a settings page to the web UI for adjusting configuration without editing YAML files.

## Features to Include

### 1. Personality Settings (Safe to Change Live)
- **Traits** (0.0 - 1.0 sliders):
  - Curiosity
  - Cheerfulness
  - Verbosity
  - Playfulness
  - Empathy
  - Independence

- **Name**: Text input for device name

### 2. AI Provider Settings (Requires Restart)
- **Primary Provider**: Dropdown (anthropic/openai)
- **Model Selection**: Dropdown per provider
- **Max Tokens**: Number input (50-500)
- **Daily Token Budget**: Number input

### 3. Display Settings
- **Refresh Interval**: Number input (1.0-30.0 seconds)
- **Display Type**: Dropdown (auto/v3/v4/mock)
- **Prefer ASCII Faces**: Checkbox

### 4. Read-Only Info
- **API Keys**: Show if configured (masked: sk-***...)
- **Hardware ID**: Show device fingerprint
- **Network**: Show API base URL

## UI Design

### Settings Page Structure
```
┌─────────────────────────────────────────┐
│ ⚙️ Settings                    [Save]   │
├─────────────────────────────────────────┤
│                                         │
│ 👤 Personality                          │
│   Name: [Inkling        ]               │
│   Curiosity:     [======>---] 70%       │
│   Cheerfulness:  [=====>----] 60%       │
│   Verbosity:     [====>-----] 50%       │
│   ...                                   │
│                                         │
│ 🤖 AI Configuration                     │
│   Primary: [Anthropic ▼]                │
│   Model:   [haiku      ▼]               │
│   Tokens:  [150        ]                │
│                                         │
│ 🖥️ Display                              │
│   Type:     [auto ▼]                    │
│   Refresh:  [5.0  ] seconds             │
│   □ Prefer ASCII faces                  │
│                                         │
│ ℹ️ Info (Read-Only)                     │
│   API Key: sk-ant-***...  ✓             │
│   Device:  abc123...                    │
│                                         │
└─────────────────────────────────────────┘
```

## Implementation

### Step 1: Add Settings Route
```python
# modes/web_chat.py

@self._app.route("/settings")
def settings_page():
    return template(SETTINGS_TEMPLATE, config=get_current_config())

@self._app.route("/api/settings", method="GET")
def get_settings():
    # Return current config as JSON
    return json.dumps({
        "personality": {...},
        "ai": {...},
        "display": {...}
    })

@self._app.route("/api/settings", method="POST")
def save_settings():
    # Update config and save to config.local.yml
    new_settings = request.json
    update_config(new_settings)
    return {"success": True}
```

### Step 2: Settings Template
Create new HTML template with:
- Sliders for personality traits
- Dropdowns for AI provider/model
- Number inputs for limits
- Save button with confirmation

### Step 3: Live Updates
- Personality traits: Apply immediately
- AI settings: Show "Restart required" warning
- Display settings: Apply on next refresh

### Step 4: Config File Management
```python
def update_config(new_settings):
    # Load config.local.yml or create it
    # Merge new settings
    # Save back to file
    # Update runtime config (personality only)
```

## Safety Features

### 1. Validation
- Range checks (0.0-1.0 for traits)
- Required fields
- Valid enum values

### 2. Backup
- Save to `config.local.yml.backup` before changes
- Rollback option if something breaks

### 3. Restart Warnings
Show which settings require restart:
- ⚠️ AI provider changes
- ⚠️ Display type changes
- ✓ Personality traits (instant)

### 4. Read-Only Fields
- API keys (security - can't change via web)
- Hardware ID (immutable)
- Network settings (security)

## User Flow

### Changing Personality
1. Click "Settings" button
2. Adjust sliders
3. Click "Save"
4. See immediate effect in responses

### Changing AI Provider
1. Select new provider
2. Warning: "Requires restart"
3. Click "Save"
4. Show: "Saved. Run: sudo systemctl restart inkling-web"

## Command Addition

Add `/settings` command:
```python
def _cmd_settings(self) -> Dict[str, Any]:
    """Open settings page."""
    return {
        "response": "Settings page: http://inkling.local:8080/settings",
        "redirect": "/settings",  # Client-side redirect
    }
```

## Security Considerations

### What CAN be edited:
- ✅ Personality traits (safe)
- ✅ Display preferences (safe)
- ✅ AI model selection (safe)
- ✅ Token limits (safe)

### What CANNOT be edited:
- ❌ API keys (must use .env file)
- ❌ Network/API base (must use config.yml)
- ❌ Hardware bindings (immutable)
- ❌ Cryptographic keys (security)

## Implementation Phases

### Phase 1 (Quick Win):
- Settings page with personality sliders
- Save to config.local.yml
- Immediate personality updates

### Phase 2 (Full Features):
- AI provider selection
- Display settings
- Restart detection/warnings

### Phase 3 (Polish):
- Export/import config
- Reset to defaults button
- Theme customization

## File Changes

1. **modes/web_chat.py**
   - Add `/settings` route
   - Add `/api/settings` GET/POST
   - Add settings template

2. **core/config_manager.py** (new)
   - Load/save config.local.yml
   - Merge with config.yml
   - Validate settings

3. **web UI template**
   - Add Settings button
   - Settings page HTML/CSS
   - JavaScript for sliders/saves

## Benefits

- ✅ No SSH needed for common changes
- ✅ User-friendly sliders/dropdowns
- ✅ Immediate personality updates
- ✅ Safe with validation
- ✅ Great for experimentation

## Example Usage

```bash
# User workflow:
1. Open http://inkling.local:8080
2. Click "Settings" button
3. Adjust "Curiosity" slider to 90%
4. Adjust "Verbosity" slider to 30%
5. Click "Save"
6. Immediately see Inkling become more curious & concise!
```

Would you like me to implement this?
