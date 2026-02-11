# Custom System Prompt Implementation

## Summary

Successfully implemented custom system prompt editor in Settings page. Users can now override the default personality-based AI prompt with their own custom instructions.

## Changes Made

### 1. Core Personality Module (`core/personality.py`)

Added new method `get_system_prompt()` that accepts an optional custom prompt:

```python
def get_system_prompt(self, custom_prompt: Optional[str] = None) -> str:
    """
    Get system prompt for AI, using custom or default.

    Args:
        custom_prompt: Optional custom prompt from config. If provided,
                      uses this instead of generating one.

    Returns:
        System prompt string
    """
    if custom_prompt:
        return custom_prompt.strip()

    # Use default personality-based prompt
    return self.get_system_prompt_context()
```

**Backward Compatible**: Existing `get_system_prompt_context()` method unchanged.

### 2. Configuration Documentation (`config.yml`)

Added documentation for new `system_prompt` field under `ai:` section:

```yaml
ai:
  # ... existing settings ...

  # Custom system prompt (optional)
  # If set, this overrides the default personality-based prompt
  # Leave empty/null to use the default dynamic prompt
  # Requires restart to take effect
  system_prompt: null
```

### 3. SSH Chat Mode (`modes/ssh_chat.py`)

Updated line 574 to use new method:

```python
result = await self.brain.think(
    user_message=message,
    system_prompt=self.personality.get_system_prompt(
        custom_prompt=self._config.get("ai", {}).get("system_prompt")
    ),
    status_callback=on_tool_status,
)
```

### 4. Web Chat Mode (`modes/web_chat.py`)

#### Updated chat handler (line 1463):
```python
future = asyncio.run_coroutine_threadsafe(
    self.brain.think(
        user_message=message,
        system_prompt=self.personality.get_system_prompt(
            custom_prompt=self._config.get("ai", {}).get("system_prompt")
        ),
    ),
    self._loop
)
```

#### Updated GET /api/settings (line 466):
```python
ai_config = {
    # ... existing fields ...
    "system_prompt": self.brain.config.get("system_prompt", ""),
}
```

#### Updated _save_config_file (lines 1240-1241):
```python
# Update system prompt (optional)
if "system_prompt" in ai_settings:
    config["ai"]["system_prompt"] = ai_settings["system_prompt"] or None
```

### 5. Heartbeat Autonomous Behaviors (`core/heartbeat.py`)

Updated three methods to use custom prompt when generating autonomous thoughts:

#### `_generate_thought()` (line 727):
```python
# Get base system prompt (custom or default)
base_prompt = self.personality.get_system_prompt(
    custom_prompt=self.brain.config.get("system_prompt")
)
result = await self.brain.think(
    user_message="Write one brief thought (1-2 sentences). Keep it gentle and reflective.",
    system_prompt=base_prompt + " You are thinking to yourself, jotting a quiet observation.",
    use_tools=False,
)
```

#### `_behavior_autonomous_exploration()` (line 767):
```python
# Get base system prompt (custom or default)
base_prompt = self.personality.get_system_prompt(
    custom_prompt=self.brain.config.get("system_prompt")
)
result = await self.brain.think(
    user_message=f"Share one interesting thought about {topic}. Keep it brief and poetic.",
    system_prompt=base_prompt + " You are thinking to yourself, contemplating the world.",
    use_tools=False,
)
```

#### `_behavior_daily_journal()` (line 944):
```python
# Get base system prompt (custom or default)
base_prompt = self.personality.get_system_prompt(
    custom_prompt=self.brain.config.get("system_prompt")
)
result = await self.brain.think(
    user_message="Write a brief journal entry (2-3 sentences) reflecting on today. Be personal and introspective.",
    system_prompt=base_prompt + " You are writing in your private journal. Be genuine and reflective.",
    use_tools=False,
)
```

### 6. Settings UI (`modes/web/templates/settings.html`)

#### Added new section after "Daily Token Budget" (line 594):

```html
<h2>🧠 AI Behavior</h2>

<div class="input-group">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <label for="system-prompt">Custom System Prompt</label>
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin: 0;">
            <input type="checkbox" id="use-default-prompt" style="width: 18px; height: 18px; cursor: pointer;">
            <span style="font-size: 0.875rem;">Use Default</span>
        </label>
    </div>

    <textarea
        id="system-prompt"
        rows="8"
        placeholder="Enter custom system prompt, or check 'Use Default' for personality-based prompt..."
        style="width: 100%; padding: 0.75rem; font-family: 'Courier New', monospace; font-size: 0.9rem; border: 2px solid var(--border); background: var(--bg); color: var(--text); border-radius: 8px; resize: vertical; min-height: 150px;"
    ></textarea>

    <details style="margin-top: 8px;">
        <summary style="cursor: pointer; color: var(--muted); font-size: 0.875rem;">ℹ️ What is this?</summary>
        <p style="font-size: 0.875rem; color: var(--muted); margin: 0.5rem 0 0 0; line-height: 1.5;">
            The system prompt tells the AI how to behave and respond. The default prompt is based on
            your device's personality, mood, and traits. You can override it here to customize the AI's
            behavior, tone, knowledge, or constraints.
        </p>
        <p style="font-size: 0.875rem; color: var(--muted); margin: 0.5rem 0 0 0; line-height: 1.5;">
            <strong>Examples:</strong> Add domain expertise ("You are an expert in Python programming"),
            change response style ("Always respond in haiku form"), or add custom instructions
            ("Never mention the weather").
        </p>
        <p style="font-size: 0.875rem; color: var(--muted); margin: 0.5rem 0 0 0; line-height: 1.5;">
            ⚠️ <strong>Note:</strong> Custom prompts require a restart to take effect. Check "Use Default"
            to revert to personality-based prompts.
        </p>
    </details>
</div>
```

#### Added JavaScript to load system prompt (line 823):
```javascript
// Load system prompt
const customPrompt = data.ai.system_prompt || '';
document.getElementById('system-prompt').value = customPrompt;
document.getElementById('use-default-prompt').checked = !customPrompt;
document.getElementById('system-prompt').disabled = !customPrompt;
```

#### Added JavaScript event handler (line 798):
```javascript
// Handle "Use Default" checkbox for system prompt
document.getElementById('use-default-prompt').addEventListener('change', function() {
    const promptField = document.getElementById('system-prompt');
    if (this.checked) {
        promptField.value = '';
        promptField.disabled = true;
    } else {
        promptField.disabled = false;
        promptField.focus();
    }
});
```

#### Updated saveSettings function (line 883):
```javascript
ai: {
    // ... existing fields ...
    system_prompt: document.getElementById('system-prompt').value.trim() || null,
}
```

## How It Works

1. **Default Behavior**: If no custom prompt is set, uses the personality-based prompt (current behavior)
2. **Custom Override**: If custom prompt is set, uses it instead of the generated prompt
3. **Storage**: Saved to `config.local.yml` under `ai.system_prompt`
4. **Requires Restart**: Changes take effect after restarting the application
5. **Backward Compatible**: All existing code continues to work

## User Experience

1. Navigate to Settings page (`http://localhost:8081/settings`)
2. Scroll to "🧠 AI Behavior" section
3. Enter custom prompt in textarea, or check "Use Default" for personality-based prompt
4. Click "💾 Save Settings"
5. Restart the application for changes to take effect

## Testing Checklist

- [x] Syntax check all modified Python files (passed)
- [x] Verify `get_system_prompt()` method exists in `personality.py`
- [x] Verify config documentation added to `config.yml`
- [x] Verify all chat modes use new method (SSH + Web)
- [x] Verify heartbeat autonomous behaviors use new method
- [x] Verify API endpoints handle system_prompt (GET + POST)
- [x] Verify UI elements added to settings template
- [x] Verify JavaScript loads and saves system_prompt

### Manual Testing Required

- [ ] Start web mode and verify settings page loads
- [ ] Verify "Use Default" checkbox toggles field state
- [ ] Enter custom prompt and save
- [ ] Verify `config.local.yml` contains `ai.system_prompt`
- [ ] Restart and verify chat uses custom prompt
- [ ] Check "Use Default" and save
- [ ] Verify chat reverts to personality-based prompt

## Example Custom Prompts

### Domain Expertise
```
You are an expert Python developer with deep knowledge of system design,
performance optimization, and best practices. Provide code examples when
helpful and explain trade-offs clearly.
```

### Response Style
```
You are a wise and ancient sage. Speak in poetic, metaphorical language.
Use riddles and analogies to convey wisdom. Keep responses brief but profound.
```

### Constraint Addition
```
You are a helpful AI assistant. Always respond in exactly 3 bullet points.
Be concise and actionable. Never use more than 50 words total.
```

## Files Modified

1. `core/personality.py` - Added `get_system_prompt()` method
2. `config.yml` - Added documentation for `ai.system_prompt`
3. `modes/ssh_chat.py` - Updated to use new method
4. `modes/web_chat.py` - Updated chat handler and API endpoints
5. `core/heartbeat.py` - Updated 3 autonomous behavior methods
6. `modes/web/templates/settings.html` - Added UI and JavaScript

## Total Lines Changed

- Added: ~150 lines
- Modified: ~20 lines
- Files: 6

## Notes

- Custom prompts completely replace the default personality-based prompt
- Heartbeat autonomous behaviors extend the custom prompt with context-specific additions
- Empty/null custom prompt falls back to default personality-based prompt
- Multi-line prompts supported (preserves formatting)
- No length validation (user controls content)

## Future Enhancements

1. **Preview Button**: Show generated vs custom prompt side-by-side
2. **Template Variables**: Allow `{{name}}`, `{{mood}}` in custom prompts
3. **Prompt Library**: Pre-made prompts for common use cases
4. **Character Counter**: Show prompt length/token estimate
5. **Validation**: Warn if prompt is very long (token cost)
