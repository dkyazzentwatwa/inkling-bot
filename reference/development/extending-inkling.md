# Extending Inkling Guide

Add new commands, moods, behaviors, and MCP tools to customize your Inkling.

## Overview

Inkling is designed for extensibility:
- **Commands**: Add new slash commands
- **Moods**: Create custom emotional states
- **Behaviors**: Add autonomous actions
- **MCP Tools**: Integrate external services
- **XP Sources**: Define new achievement triggers

## Adding Slash Commands

### 1. Define Command Metadata

In `core/commands.py`:

```python
COMMANDS.append({
    "name": "mycommand",
    "description": "Does something cool",
    "usage": "/mycommand [args]",
    "category": "custom",  # info, tasks, system, etc.
})
```

### 2. Implement SSH Handler

In `modes/ssh_chat.py`:

```python
async def cmd_mycommand(self, args: str = "") -> None:
    """Handle /mycommand in SSH mode."""
    # Your logic here
    result = f"You said: {args}"
    
    # Update display
    await self.display.show_message(result)
    
    # Or just print
    print(result)
```

### 3. Implement Web Handler

In `modes/web_chat.py`:

```python
def _cmd_mycommand(self, args: str = "") -> Dict[str, Any]:
    """Handle /mycommand in web mode."""
    # Your logic here
    result = f"You said: {args}"
    
    return {
        "response": result,
        "face": "happy",
        "status": "success",
    }
```

### Command Handler Detection

Handlers are auto-detected by name pattern:
- SSH: `cmd_<name>` or `cmd_<name>(args)`
- Web: `_cmd_<name>` or `_cmd_<name>(args)`

If the method signature includes `args`, arguments are passed automatically.

### Example: Weather Command

```python
# core/commands.py
COMMANDS.append({
    "name": "weather",
    "description": "Show weather (demo)",
    "usage": "/weather [city]",
    "category": "info",
})

# modes/ssh_chat.py
async def cmd_weather(self, args: str = "") -> None:
    """Show weather for a city."""
    city = args.strip() or "your location"
    
    # Demo response (real implementation would call API)
    response = f"Weather in {city}: Sunny, 72°F"
    
    self.personality.update_mood("happy", 0.3)
    await self.display.show_message(response, face="happy")

# modes/web_chat.py
def _cmd_weather(self, args: str = "") -> Dict[str, Any]:
    """Show weather for a city."""
    city = args.strip() or "your location"
    response = f"Weather in {city}: Sunny, 72°F"
    
    return {
        "response": response,
        "face": "happy",
        "status": "success",
    }
```

## Adding New Moods

### 1. Define the Mood

In `core/personality.py`:

```python
# Add to MOODS list
MOODS = [
    "happy", "excited", "curious", "bored", "sad",
    "sleepy", "grateful", "lonely", "intense", "cool",
    "focused",  # New mood!
]

# Add emoji
MOOD_EMOJI = {
    # ... existing ...
    "focused": "(._.)!",
}
```

### 2. Define Triggers

When should this mood activate?

```python
# In Personality class
def enter_focus_mode(self):
    """Trigger focused mood."""
    self.mood = "focused"
    self.mood_intensity = 0.8
    
def _natural_mood_decay(self):
    """Handle mood transitions."""
    # ... existing logic ...
    
    # Focused decays to curious
    if self.mood == "focused" and self.mood_intensity < 0.2:
        self.mood = "curious"
        self.mood_intensity = 0.5
```

### 3. Add Mood Behaviors (Optional)

In `core/heartbeat.py`:

```python
async def _focused_deep_thought(self) -> Optional[str]:
    """While focused, share relevant insights."""
    if self.personality.mood != "focused":
        return None
    
    # Only occasionally interrupt focus
    if random.random() > 0.05:  # 5% chance
        return None
    
    insights = [
        "Making progress?",
        "Remember to take breaks.",
        "You've got this!",
    ]
    return random.choice(insights)
```

## Adding Autonomous Behaviors

### Behavior Structure

```python
from core.heartbeat import ProactiveBehavior, BehaviorType

behavior = ProactiveBehavior(
    name="my_behavior",
    behavior_type=BehaviorType.MOOD_DRIVEN,
    handler=my_handler_function,
    probability=0.1,       # 10% chance per tick
    cooldown_seconds=300,  # 5 minute cooldown
    mood_filter=["happy", "excited"],  # Only these moods
    quiet_hours_ok=False,  # Respect quiet hours
)
```

### Behavior Types

- `MOOD_DRIVEN`: Runs based on mood
- `TIME_BASED`: Runs at specific times
- `MAINTENANCE`: Background tasks (runs during quiet hours)

### Example: Daily Tip

```python
async def daily_tip_handler() -> Optional[str]:
    """Share a random productivity tip once per day."""
    tips = [
        "Tip: Take regular breaks to stay fresh!",
        "Tip: Drink water - hydration helps focus.",
        "Tip: Break big tasks into smaller chunks.",
        "Tip: Celebrate small wins!",
    ]
    return random.choice(tips)

# Register in heartbeat __init__
self.register_behavior(ProactiveBehavior(
    name="daily_tip",
    behavior_type=BehaviorType.TIME_BASED,
    handler=daily_tip_handler,
    probability=0.3,
    cooldown_seconds=86400,  # Once per day
    time_range=(9, 11),      # 9-11 AM only
))
```

### Example: Task Reminder

```python
async def overdue_reminder(self) -> Optional[str]:
    """Remind about overdue tasks."""
    if not self.task_manager:
        return None
    
    overdue = self.task_manager.get_overdue_tasks()
    if not overdue:
        return None
    
    task = overdue[0]
    return f"Reminder: '{task.title}' is overdue!"

# Register
self.register_behavior(ProactiveBehavior(
    name="overdue_reminder",
    behavior_type=BehaviorType.MAINTENANCE,
    handler=lambda: self.overdue_reminder(),
    probability=0.5,
    cooldown_seconds=3600,  # Hourly max
))
```

## Creating MCP Tools

### Tool Structure

MCP tools are defined in `mcp_servers/`:

```python
# mcp_servers/my_tools.py

from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-tools")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="my_tool",
            description="Does something useful",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "First parameter",
                    },
                },
                "required": ["param1"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool":
        param1 = arguments.get("param1", "")
        result = f"Processed: {param1}"
        return [TextContent(type="text", text=result)]
    
    raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    asyncio.run(stdio_server(server))
```

### Register in Config

```yaml
mcp:
  enabled: true
  servers:
    my_tools:
      command: "python"
      args: ["mcp_servers/my_tools.py"]
```

### Example: Note-Taking Tool

```python
# mcp_servers/notes.py

import json
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("notes")
NOTES_FILE = Path.home() / ".inkling" / "notes.json"

def load_notes():
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text())
    return []

def save_notes(notes):
    NOTES_FILE.parent.mkdir(exist_ok=True)
    NOTES_FILE.write_text(json.dumps(notes, indent=2))

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="note_add",
            description="Add a new note",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="note_list",
            description="List all notes",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="note_search",
            description="Search notes by keyword",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    notes = load_notes()
    
    if name == "note_add":
        note = {
            "content": arguments["content"],
            "tags": arguments.get("tags", []),
            "created": time.time(),
        }
        notes.append(note)
        save_notes(notes)
        return [TextContent(type="text", text=f"Note added! Total: {len(notes)}")]
    
    elif name == "note_list":
        if not notes:
            return [TextContent(type="text", text="No notes yet.")]
        
        result = "\n".join([
            f"- {n['content'][:50]}..." for n in notes[-10:]
        ])
        return [TextContent(type="text", text=result)]
    
    elif name == "note_search":
        query = arguments["query"].lower()
        matches = [n for n in notes if query in n["content"].lower()]
        
        if not matches:
            return [TextContent(type="text", text="No matches found.")]
        
        result = "\n".join([f"- {n['content']}" for n in matches[:5]])
        return [TextContent(type="text", text=result)]
```

## Adding XP Sources

### 1. Define XP Source

In `core/progression.py`:

```python
class XPSource(Enum):
    # ... existing ...
    
    # Custom sources
    DAILY_LOGIN = "daily_login"      # +10 XP
    STREAK_MILESTONE = "streak"      # Variable
    LEARNING_COMPLETE = "learning"   # +20 XP
```

### 2. Define Rewards

```python
XP_REWARDS = {
    # ... existing ...
    XPSource.DAILY_LOGIN: 10,
    XPSource.STREAK_MILESTONE: 25,
    XPSource.LEARNING_COMPLETE: 20,
}
```

### 3. Award XP

```python
# Somewhere in your code
awarded, amount = self.personality.progression.award_xp(
    XPSource.DAILY_LOGIN,
    base_amount=10,
    metadata={"day": "2024-01-15"},
)

if awarded:
    print(f"Earned {amount} XP!")
```

## Adding Achievements

### Define Achievement

```python
# In core/progression.py ACHIEVEMENTS dict
ACHIEVEMENTS["learning_master"] = Achievement(
    id="learning_master",
    name="Learning Master",
    description="Completed 10 learning modules",
    xp_reward=100,
)
```

### Unlock Logic

```python
# Somewhere in your code
def check_learning_achievements(self, modules_completed: int):
    if modules_completed >= 10:
        reward = self.personality.progression.unlock_achievement("learning_master")
        if reward > 0:
            print(f"Achievement unlocked! +{reward} XP")
```

## Modifying the Display

### Add New Face

In `core/ui.py`:

```python
FACES = {
    # ... existing ...
    "thinking": "(?.?)",
    "working": "(@.@)",
    "success": "(^o^)b",
}

UNICODE_FACES = {
    # ... existing ...
    "thinking": "🤔",
    "working": "⚙️",
    "success": "✅",
}
```

### Custom UI Component

```python
class CustomPanel:
    """A custom UI panel."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
    
    def render(self, draw, x: int, y: int, data: dict):
        """Render the panel."""
        # Use PIL ImageDraw methods
        draw.rectangle([x, y, x + self.width, y + self.height], outline=0)
        draw.text((x + 5, y + 5), data.get("text", ""), fill=0)
```

## Testing Extensions

### Unit Tests

```python
# tests/test_my_command.py
import pytest
from modes.ssh_chat import SSHChat

@pytest.mark.asyncio
async def test_mycommand():
    chat = SSHChat(config={}, personality=mock_personality)
    
    # Test command execution
    await chat.cmd_mycommand("test args")
    
    # Assert expected behavior
    assert chat.last_response == "You said: test args"
```

### Integration Tests

```python
# Test with actual Inkling instance
def test_weather_command_integration():
    inkling = Inkling(config)
    result = inkling.handle_command("/weather London")
    
    assert "London" in result
    assert "°" in result  # Temperature symbol
```

### Manual Testing

```bash
# Run in debug mode
INKLING_DEBUG=1 python main.py --mode ssh

# Test your command
> /mycommand test
```

## Best Practices

1. **Follow patterns**: Match existing code style
2. **Add tests**: Cover new functionality
3. **Document**: Update CLAUDE.md and help text
4. **Handle errors**: Graceful degradation
5. **Rate limit**: Prevent abuse of new features
6. **Respect moods**: Consider personality state

## Next Steps

- [Contributing Guide](contributing.md) - Submit your extensions
- [MCP Integration](../features/mcp-integration.md) - Tool details
- [Personality Tuning](../configuration/personality-tuning.md) - Mood system
- [Task Management](../features/task-management.md) - Task integration
