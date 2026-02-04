# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Inkling is a local AI companion device for Raspberry Pi Zero 2W with e-ink display. It combines:
- Pwnagotchi-style personality/mood system
- Local AI assistant via Anthropic/OpenAI/Gemini
- Task management with AI integration
- Model Context Protocol (MCP) for tool extensibility

The codebase has one main component:
- **Pi Client** (Python) - Runs on the device with local AI and web UI

## Commands

### Pi Client (Python)
```bash
# IMPORTANT: Always use the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in SSH chat mode (mock display for development)
python main.py --mode ssh

# Run web UI mode (browser at http://localhost:8081)
python main.py --mode web

# Run display demo
python main.py --mode demo

# Run with debug output
INKLING_DEBUG=1 python main.py --mode ssh

# Run tests
pytest
pytest -xvs core/test_crypto.py  # Single test file
pytest --cov=core --cov-report=html  # With coverage

# Syntax check (before committing)
python -m py_compile <file>.py
```

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...   # Required for AI (or set in config.local.yml)
OPENAI_API_KEY=sk-...          # Optional fallback
GOOGLE_API_KEY=...             # For Gemini
INKLING_DEBUG=1                # Enable detailed logging
COMPOSIO_API_KEY=...           # For Composio MCP integration (optional)
```

## Architecture

### Pi Client Flow
```
main.py → Inkling class
    ├── Identity (core/crypto.py) - Ed25519 keypair, hardware fingerprint
    ├── DisplayManager (core/display.py) - E-ink abstraction (V3/V4/Mock)
    ├── Personality (core/personality.py) - Mood state machine + XP/leveling
    ├── Brain (core/brain.py) - Multi-provider AI with fallback
    ├── TaskManager (core/tasks.py) - Task management with AI companion features
    ├── Heartbeat (core/heartbeat.py) - Autonomous behaviors and maintenance
    └── MCPClient (core/mcp_client.py) - Model Context Protocol tool integration

modes/
    ├── ssh_chat.py - Terminal interaction
    └── web_chat.py - Bottle-based web UI with Kanban board

mcp_servers/
    └── tasks.py - MCP server exposing task management to AI
```

### Key Design Patterns

**Hardware-bound Identity**: Devices have Ed25519 keys. The `Identity` class combines a keypair with a hardware hash (CPU serial + MAC) for unique device identification.

**Multi-provider AI**: `Brain` tries Anthropic first, falls back to OpenAI or Gemini. All use async clients with retry logic and token budgeting.

**Display Rate Limiting**: E-ink displays damage with frequent refreshes. `DisplayManager` enforces minimum intervals:
- V3: 0.5s (supports partial refresh)
- V4: 5.0s (full refresh only)
- Mock: 0.5s (development)

**Pwnagotchi-Style UI**: The display uses a component-based layout system (`core/ui.py`):
- `HeaderBar`: Name prompt, mood, uptime
- `MessagePanel`: Left panel with centered, word-wrapped AI responses
- `StatsPanel`: Right panel with system stats, level/XP
- `FaceBox`: Bottom face expression (38px font, centered)
- `FooterBar`: Chat count, mode

**Web UI Architecture** (`modes/web_chat.py`):
- Bottle web framework serving HTML templates (embedded in Python file)
- Single-page app with async/await JavaScript
- Routes:
  - `/` - Main chat interface
  - `/settings` - Personality, AI config, and appearance settings
  - `/tasks` - Kanban board for task management
  - `/files` - File browser for viewing/downloading files from `~/.inkling/`
- API endpoints: `/api/chat`, `/api/command`, `/api/settings`, `/api/state`, `/api/tasks/*`, `/api/files/*`
- Settings changes:
  - Personality traits: Applied immediately (no restart)
  - AI configuration: Saved to `config.local.yml`, requires restart
  - Theme: Saved to localStorage

### Task Management System

**TaskManager** (`core/tasks.py`): SQLite-based task tracking with AI companion integration
- Tasks stored in `~/.inkling/tasks.db`
- Fields: title, description, status (pending/in_progress/completed/cancelled), priority, due date, tags, project
- AI integration: mood_on_creation, celebration_level, MCP tool/params
- Time tracking: estimated_minutes, actual_minutes
- Subtasks with completion tracking
- Task statistics: completion rate, streaks, overdue count

**MCP Server** (`mcp_servers/tasks.py`): Exposes 6 tools to AI via Model Context Protocol
- `task_create`, `task_list`, `task_complete`, `task_update`, `task_delete`, `task_stats`
- Enable in `config.yml` under `mcp.servers.tasks`

**Web UI** (`/tasks` route): Kanban board with drag-and-drop, filtering, quick add

**XP Integration**: Tasks award XP based on priority (5-40 XP), with bonuses for on-time completion and streaks

### Autonomous Behaviors (Heartbeat System)

**Heartbeat** (`core/heartbeat.py`): Makes Inkling "alive" with autonomous actions
- Tick interval: Configurable (default 60s)
- Behavior types (can be toggled):
  - **Mood behaviors**: Reach out when lonely, suggest activities when bored
  - **Time behaviors**: Morning greetings, evening wind-down
  - **Maintenance**: Memory pruning, task reminders
- Quiet hours: Suppress spontaneous messages (default 11pm-7am)
- Enable/disable in `config.yml` under `heartbeat.*`

## Configuration

Copy `config.yml` to `config.local.yml` for local overrides. Key settings:
- `device.name`: Device name (editable via web UI)
- `display.type`: `auto`, `v3`, `v4`, or `mock`
- `ai.primary`: `anthropic`, `openai`, or `gemini`
- `ai.anthropic.model`: Model selection (haiku/sonnet/opus)
- `ai.openai.model`: Model selection (gpt-4o-mini/gpt-4o/o1-mini)
- `ai.gemini.model`: Model selection (gemini-2.0-flash-exp/gemini-1.5-pro)
- `ai.budget.daily_tokens`: Daily token limit (default 10000)
- `ai.budget.per_request_max`: Max tokens per request (default 500)
- `personality.*`: Base trait values (curiosity, cheerfulness, verbosity, playfulness, empathy, independence - 0.0-1.0)
- `heartbeat.enabled`: Enable autonomous behaviors (default true)
- `heartbeat.tick_interval`: Check interval in seconds (default 60)
- `heartbeat.enable_mood_behaviors`: Mood-driven actions (default true)
- `heartbeat.enable_time_behaviors`: Time-based greetings (default true)
- `heartbeat.quiet_hours_start/end`: Suppress spontaneous messages (default 23-7)
- `mcp.enabled`: Enable Model Context Protocol servers (default false)
- `mcp.servers.*`: Configure MCP servers (tasks, filesystem, etc.)

**Web UI Settings** (`http://localhost:8081/settings`):
- **Instant Apply** (no restart): Device name, personality traits (6 sliders), color theme
- **Requires Restart**: AI provider, model selection, token limits
- All changes automatically saved to `config.local.yml`

## Core Modules Reference

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `core/brain.py` | Multi-provider AI | `Brain` class, async chat methods, token budgeting |
| `core/personality.py` | Mood & traits | `Personality`, `PersonalityTraits`, mood state machine |
| `core/progression.py` | XP & leveling | `Progression`, `XPSource` enum, achievements |
| `core/tasks.py` | Task management | `TaskManager`, `Task` dataclass, CRUD operations |
| `core/heartbeat.py` | Autonomous behaviors | `Heartbeat` class, tick cycle, behavior triggers |
| `core/mcp_client.py` | MCP tool integration | `MCPClient`, tool discovery, async tool calls |
| `core/display.py` | E-ink abstraction | `DisplayManager`, V3/V4/Mock drivers |
| `core/ui.py` | Display layout | `HeaderBar`, `MessagePanel`, `StatsPanel`, `FaceBox` |
| `core/crypto.py` | Identity & signing | `Identity`, Ed25519 keypair, hardware fingerprint |
| `core/memory.py` | Conversation memory | Summarization, context pruning |
| `core/commands.py` | Slash commands | `COMMANDS` dict, command metadata |

## Database Schema

**Local SQLite** (`~/.inkling/`):
- `tasks.db`: Task manager storage (created by TaskManager)
- `memory.db`: Conversation summaries (created by Memory)

## Important Implementation Notes

**Display Text Rendering**: AI response text in `MessagePanel` is centered both horizontally (per line) and vertically (as block). Use `textbbox()` to calculate width for centering.

**Face Preference**:
- E-ink displays (V3/V4): Use ASCII faces from `FACES` (better rendering on e-ink)
- Mock/Web displays: Use Unicode faces from `UNICODE_FACES` (prettier appearance)
- Set via `DisplayManager._prefer_ascii_faces`

**Async/Sync Bridge**: Web mode (`web_chat.py`) runs Bottle in a thread with an async event loop. Use `asyncio.run_coroutine_threadsafe()` to call async methods from sync Bottle handlers.

**Personality State**: `Personality` class tracks:
- `traits`: Editable via settings (curiosity, cheerfulness, verbosity, playfulness, empathy, independence)
- `mood`: Runtime state machine (happy, excited, curious, bored, sad, sleepy, grateful, lonely, intense, cool)
- `progression`: XP/leveling system with achievements and prestige

**Config File Management**: When saving settings via web UI:
1. Load existing `config.local.yml` (or create empty dict)
2. Update only changed sections (`device.name`, `personality.*`, `ai.*`)
3. Write back with `yaml.dump()` preserving other settings
4. AI settings require restart; personality changes apply immediately

**MCP Integration**: Inkling can use external tools via Model Context Protocol
- Built-in servers: `tasks` (task management)
- Third-party servers: `filesystem`, `fetch`, `memory`, `brave-search`, etc.
- **Composio integration**: 500+ app integrations (Google Calendar, GitHub, Slack, etc.)
  - Ready to use! Just set COMPOSIO_API_KEY environment variable
  - See COMPOSIO_INTEGRATION.md for setup guide
- Enable in `config.yml` under `mcp.servers.*`

**Web UI Template Structure** (`modes/web_chat.py`):
- Templates are embedded as string constants (HTML_TEMPLATE, SETTINGS_TEMPLATE, TASKS_TEMPLATE)
- Use Bottle's `template()` function with simple variable substitution: `{{name}}`, `{{int(value)}}`
- JavaScript in templates uses async/await for API calls
- Theme support via CSS variables and `data-theme` attribute
- Keep templates self-contained (inline CSS and JS)
- When adding new routes, define template constant then use: `template(YOUR_TEMPLATE, name=self.personality.name, ...)`

## Common Development Patterns

**Adding a New Slash Command**:
1. Add command metadata to `COMMANDS` dict in `core/commands.py`
2. Implement handler method in mode file (e.g., `_cmd_mycommand` in `modes/web_chat.py`)
3. Command handler returns `Dict[str, Any]` with keys: `success`, `message`, `data` (optional)

**Adding a New XP Source**:
1. Add enum value to `XPSource` in `core/progression.py`
2. Define XP amount in `XP_REWARDS` dict
3. Call `personality.progression.award_xp(XPSource.YOUR_SOURCE)` when event occurs
4. Optionally add achievement in `ACHIEVEMENTS` dict

**Adding a New MCP Tool**:
1. Create tool definition in `mcp_servers/tasks.py` or new MCP server file
2. Add server config to `config.yml` under `mcp.servers.*`
3. Brain will auto-discover tools on startup if `mcp.enabled: true`
4. AI can now call tool via function calling

**Adding a New Mood**:
1. Add mood to `MOODS` list in `core/personality.py`
2. Define emoji in `MOOD_EMOJI` dict
3. Add transition rules in `Personality._natural_mood_decay()`
4. Optionally add mood-specific heartbeat behavior

**Modifying Web UI**:
1. For existing pages: Edit template constant in `modes/web_chat.py`
2. For new pages: Create template constant, add route with `@self._app.route()`
3. API endpoints: Add route with JSON response using `response.content_type = "application/json"`
4. Test with `python main.py --mode web` and visit `http://localhost:8081`

## Troubleshooting

**Import Errors**:
- Always activate venv: `source .venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Display Not Working**:
- Check `config.local.yml` has `display.type: mock` for development
- For real hardware, ensure SPI is enabled and display connected properly

**AI Not Responding**:
- Verify API key in `config.local.yml` or environment variable
- Check token budget not exceeded: use `/stats` command
- Enable debug mode: `INKLING_DEBUG=1 python main.py --mode ssh`

**Web UI Not Loading**:
- Check port 8081 is not in use
- Verify Bottle is installed: `pip show bottle`
- Check browser console for JavaScript errors

**Task Manager Not Working**:
- Ensure MCP is enabled: `mcp.enabled: true` in config
- Check tasks server configured: `mcp.servers.tasks` exists
- Verify `~/.inkling/tasks.db` has write permissions
