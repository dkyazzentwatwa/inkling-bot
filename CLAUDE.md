# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Inkling is a **fully local** AI companion device for Raspberry Pi Zero 2W with e-ink display. It combines:
- Pwnagotchi-style personality/mood system
- Local AI assistant via Anthropic/OpenAI/Gemini APIs
- Task management with AI integration
- Model Context Protocol (MCP) for tool extensibility
- No cloud dependencies - all social features (The Conservatory) have been removed

The codebase has one main component:
- **Pi Client** (Python) - Runs on the device with local AI and web UI

**Note**: All social/cloud features (dreams, telegrams, Night Pool, etc.) have been completely removed. The bot is now 100% local and self-contained.

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

**Option 1: Use .env file (Recommended)**

Create a `.env` file in the project directory:

```bash
cp .env.example .env
nano .env
```

Then add your keys:

```bash
# AI Provider API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-api-key-here

# Optional
COMPOSIO_API_KEY=your-composio-key-here
SERVER_PW=your-web-password-here
INKLING_DEBUG=1  # Enable debug logging
INKLING_NO_DISPLAY_ECHO=1  # Disable ASCII display output in terminal/logs
```

**Option 2: Export manually**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=...
export COMPOSIO_API_KEY=...
export INKLING_DEBUG=1  # Enable detailed logging
export INKLING_NO_DISPLAY_ECHO=1  # Disable ASCII display output in terminal/logs
```

## Architecture

### Pi Client Flow
```
main.py → Inkling class
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
    ├── tasks.py - MCP server exposing task management to AI
    └── filesystem.py - Optional Python-based file operations (read/write/list/search)
```

### Key Design Patterns

**Removed Features**: The Conservatory social backend has been removed. All related features are gone:
- No social commands (/dream, /fish, /telegram, /queue, /identity)
- No cloud synchronization or P2P features
- `Identity` class (core/crypto.py) still exists but is unused
- Focus is now entirely on local AI companion functionality

**Multi-provider AI**: `Brain` tries Anthropic first, falls back to OpenAI or Gemini. All use async clients with retry logic and token budgeting.

**Display Rate Limiting**: E-ink displays damage with frequent refreshes. `DisplayManager` enforces minimum intervals:
- V3: 0.5s (supports partial refresh)
- V4: 5.0s (full refresh only)
- Mock: 0.5s (development)

**Pwnagotchi-Style UI**: The display uses a component-based layout system (`core/ui.py`):
- `HeaderBar`: Name prompt, mood, uptime (14px)
- `MessagePanel`: Full-width message area with centered, word-wrapped AI responses (86px, ~40 chars/line, 6 lines max)
- `FooterBar`: Compact footer with all stats in format `(^_^) | L1 NEWB | 54%mem 1%cpu 43° | CHAT3 | SSH` (22px)
- Auto-pagination: Long responses (>6 lines) automatically split into pages with 3-second transitions

**Web UI Architecture** (`modes/web_chat.py`):
- Bottle web framework serving HTML templates (embedded in Python file)
- Single-page app with async/await JavaScript
- Routes:
  - `/` - Main chat interface
  - `/settings` - Personality, AI config, and appearance settings
  - `/tasks` - Kanban board for task management
  - `/files` - File browser with multiple storage locations (see Storage Locations below)
- API endpoints: `/api/chat`, `/api/command`, `/api/settings`, `/api/state`, `/api/tasks/*`, `/api/files/*`
- Settings changes:
  - Personality traits: Applied immediately (no restart)
  - AI configuration: Saved to `config.local.yml`, requires restart
  - Theme: Saved to localStorage

### Storage Locations

Project Inkling supports multiple storage locations for user files:

**Inkling Data Directory** (`~/.inkling/`):
- Default location for all Inkling-managed data
- Contains: tasks.db, memory.db, logs, configs
- Always available

**SD Card** (optional):
- External storage for large files, backups, exports
- Auto-detected at `/media/pi/*` or `/mnt/*`, or configured manually
- Requires configuration in `config.yml` under `storage.sd_card`
- Configure in `config.local.yml`:
  ```yaml
  storage:
    sd_card:
      enabled: true
      path: "auto"  # or "/media/pi/SD_CARD" for specific path
  ```

**Filesystem MCP Access**:
- AI can access both locations via separate MCP server instances
- `filesystem-inkling` - Tools for .inkling directory (fs_list, fs_read, fs_write, fs_search, fs_info)
- `filesystem-sd` - Tools for SD card (same tool set, different base path)
- Enable in `config.yml` under `mcp.servers.*`
- Example configuration:
  ```yaml
  mcp:
    servers:
      filesystem-inkling:
        command: "python"
        args: ["mcp_servers/filesystem.py", "/home/pi/.inkling"]
      filesystem-sd:
        command: "python"
        args: ["mcp_servers/filesystem.py", "/media/pi/SD_CARD"]
  ```

**Web UI /files Page**:
- Storage selector dropdown to switch between locations
- Same browse/view/download functionality for both
- File type restrictions apply to all storage locations (.txt, .md, .csv, .json, .log)
- Auto-disables SD card option if not available

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

**Slash Commands**:
- `/tasks` - List all tasks (with optional filters)
- `/task [title]` - Show task details or create new task
- `/done <id>` - Mark task as complete (awards XP)
- `/cancel <id>` - Cancel a task (keeps record, no XP)
- `/delete <id>` - Permanently delete a task
- `/taskstats` - Show completion rate, streaks, overdue count
- All commands support partial ID matching (can use just first few characters)

**Web UI** (`/tasks` route): Kanban board with drag-and-drop, filtering, quick add

**XP Integration**: Tasks award XP based on priority (5-40 XP), with bonuses for on-time completion and streaks

### Scheduler System (Cron-Style Scheduling)

**ScheduledTaskManager** (`core/scheduler.py`): Time-based task scheduling with exact times
- Uses `schedule` library for cron-like functionality
- Integrates with Heartbeat (checked every 60 seconds)
- Tasks run at exact times (e.g., "daily at 2:30 PM")
- Stored in `config.yml` under `scheduler.tasks`

**Schedule Expressions**:
- Daily: `every().day.at('14:30')` - Run at 2:30 PM every day
- Hourly: `every().hour` - Run every hour on the hour
- Weekly: `every().monday.at('09:00')` - Run every Monday at 9 AM
- Interval: `every(5).minutes` - Run every 5 minutes

**Built-in Actions**:
- `daily_summary` - Daily task summary (default: 8 AM)
- `weekly_cleanup` - Prune old memories, archive tasks (default: Sunday 2 AM)
- `test_greeting` - Test action for debugging

**Slash Commands**:
- `/schedule` or `/schedule list` - List all scheduled tasks with next run times
- `/schedule enable <name>` - Enable a scheduled task
- `/schedule disable <name>` - Disable a scheduled task

**Configuration** (in `config.yml`):
```yaml
scheduler:
  enabled: true
  tasks:
    - name: "morning_summary"
      schedule: "every().day.at('08:00')"
      action: "daily_summary"
      enabled: true
    - name: "weekly_cleanup"
      schedule: "every().sunday.at('02:00')"
      action: "weekly_cleanup"
      enabled: true
```

**Adding Custom Actions**: Register actions in main.py:
```python
async def my_custom_action():
    # Your action code here
    pass

scheduler.register_action("my_action", my_custom_action)
```

### System Tools MCP Server

**SystemMCPServer** (`mcp_servers/system.py`): Lightweight Linux utility tools via MCP
- AI can use system commands without shell access
- Safe wrappers with validation and timeouts
- Enable in `config.yml` under `mcp.servers.system`

**Available Tools** (6 total):

1. **curl** - Make HTTP requests
   - Inputs: url (required), method (GET/POST), headers, body
   - Security: HTTP/HTTPS only, 1MB response limit, 5s timeout
   - Use: Check website status, fetch data, API calls

2. **df** - Disk space usage
   - Input: path (optional, default /)
   - Output: total/used/free space in GB, percent used

3. **free** - Memory usage
   - Output: RAM and swap (total/used/available in MB, percent)

4. **uptime** - System uptime
   - Output: uptime string, load averages (1/5/15 min)

5. **ps** - Process listing
   - Inputs: filter (name substring), limit (default 10)
   - Output: PID, name, CPU%, memory%, command
   - Sorted by CPU usage descending

6. **ping** - Network connectivity
   - Input: host (hostname or IP)
   - Output: reachable (bool), latency (ms), IP address
   - Tests ports 80 and 443 (HTTP/HTTPS)

**Dependencies**: Requires `psutil>=5.9.0` and `requests>=2.31.0`

**Token Budget**: ~50-100 tokens per tool × 6 = 300-600 tokens (well within 20-tool limit)

**Example AI Usage**:
- "What's my disk space?" → Uses `df` tool
- "Check memory usage" → Uses `free` tool
- "Is google.com reachable?" → Uses `ping` tool
- "Fetch https://api.github.com" → Uses `curl` tool

### Remote Access (Ngrok)

**Status**: Fully implemented and supported

Project Inkling supports secure remote access via ngrok tunneling. Access the web UI from anywhere while keeping the device local.

**Setup**:

1. Add to `config.local.yml`:
```yaml
network:
  ngrok:
    enabled: true
    auth_token: "your_ngrok_token"  # Optional, for custom domains
```

2. Set password protection (recommended for public URLs):
```bash
export SERVER_PW="your-secure-password"
```

3. Start web mode:
```bash
python main.py --mode web
```

You'll see:
```
🌐 Ngrok tunnel: https://xxxx.ngrok.io
🔐 Password protection enabled
```

**Security**:
- Always use `SERVER_PW` when ngrok is enabled
- Ngrok free tier has session limits (~2 hours)
- Paid ngrok plans support custom domains and longer sessions
- Web UI requires password authentication when `SERVER_PW` is set

**Implementation**: See `modes/web_chat.py:3272-3334` for ngrok integration code

### Available Slash Commands

All commands defined in `core/commands.py` and available in both SSH and web modes:

**Info & Status**:
- `/help` - Show all available commands
- `/level` - Show XP, progression, and achievements
- `/prestige` - Reset level with XP bonus
- `/stats` - Show AI token usage statistics
- `/history` - Show recent conversation messages

**Personality**:
- `/mood` - Show current mood and intensity
- `/energy` - Show energy level
- `/traits` - Show all personality traits

**Tasks** (see Task Management System section above for details):
- `/tasks` - List all tasks
- `/task [title]` - Show or create task
- `/done <id>` - Complete task (awards XP)
- `/cancel <id>` - Cancel task
- `/delete <id>` - Delete task permanently
- `/taskstats` - Show statistics

**Scheduler** (see Scheduler System section above for details):
- `/schedule` or `/schedule list` - List all scheduled tasks
- `/schedule enable <name>` - Enable a task
- `/schedule disable <name>` - Disable a task

**System**:
- `/system` - Show system stats (CPU, memory, temp, uptime)
- `/config` - Show AI configuration

**Display**:
- `/face <name>` - Test a face expression
- `/faces` - List all available faces
- `/refresh` - Force display refresh

**Session** (SSH only):
- `/ask <message>` - Explicit chat command
- `/clear` - Clear conversation history
- `/quit` or `/exit` - Exit chat

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
- `ai.anthropic.model`: Model selection (claude-haiku-4-5/claude-sonnet-4-5/claude-opus-4-5)
- `ai.openai.model`: Model selection (gpt-5-mini/gpt-5.2)
- `ai.gemini.model`: Model selection (gemini-2.0-flash-exp/gemini-1.5-flash/gemini-1.5-pro)
- `ai.budget.daily_tokens`: Daily token limit (default 10000)
- `ai.budget.per_request_max`: Max tokens per request (default 500)
- `personality.*`: Base trait values (curiosity, cheerfulness, verbosity, playfulness, empathy, independence - 0.0-1.0)
- `heartbeat.enabled`: Enable autonomous behaviors (default true)
- `heartbeat.tick_interval`: Check interval in seconds (default 60)
- `heartbeat.enable_mood_behaviors`: Mood-driven actions (default true)
- `heartbeat.enable_time_behaviors`: Time-based greetings (default true)
- `heartbeat.quiet_hours_start/end`: Suppress spontaneous messages (default 23-7)
- `scheduler.enabled`: Enable cron-style scheduled tasks (default true)
- `scheduler.tasks`: List of scheduled tasks with name, schedule, action, enabled
- `mcp.enabled`: Enable Model Context Protocol servers (default true)
- `mcp.max_tools`: Maximum tools to load (default 20, OpenAI limit 128)
- `mcp.servers.*`: Configure MCP servers (tasks, system, filesystem, etc.)
- `network.ngrok.enabled`: Enable ngrok tunnel for remote access (default false)
- `network.ngrok.auth_token`: Ngrok auth token for custom domains (optional)

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
| `core/scheduler.py` | Cron-style scheduling | `ScheduledTaskManager`, time-based task execution |
| `core/mcp_client.py` | MCP tool integration | `MCPClient`, tool discovery, async tool calls |
| `core/display.py` | E-ink abstraction | `DisplayManager`, V3/V4/Mock drivers |
| `core/ui.py` | Display layout | `HeaderBar`, `MessagePanel`, `FooterBar`, `PwnagotchiUI` |
| `core/crypto.py` | Identity (unused) | `Identity`, Ed25519 keypair - legacy from removed social features |
| `core/memory.py` | Conversation memory | Summarization, context pruning |
| `core/commands.py` | Slash commands | `COMMANDS` dict, command metadata |
| `core/storage.py` | Storage detection | SD card detection, storage availability checks |
| `mcp_servers/system.py` | System tools MCP | curl, df, free, uptime, ps, ping utilities |
| `mcp_servers/filesystem.py` | Filesystem MCP | File operations (list, read, write, search, info) |

## Database Schema

**Local SQLite** (`~/.inkling/`):
- `tasks.db`: Task manager storage (created by TaskManager)
- `memory.db`: Conversation summaries (created by Memory)

## Important Implementation Notes

**Display Text Rendering**:
- AI response text in `MessagePanel` is centered both horizontally (per line) and vertically (as block)
- Use `textbbox()` to calculate width for centering
- Full-width layout: ~40 chars per line, 6 lines max in 86px message area
- Auto-pagination: `display.show_message_paginated()` splits long messages into pages with 3-second delay
  - Used automatically in both SSH and web modes when response exceeds 6 lines

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
- Built-in servers:
  - `tasks` (task management) - Python-based, always available
  - `filesystem` (file operations) - Python-based, optional (see FILESYSTEM_MCP.md)
- Third-party servers: Composio (500+ app integrations), fetch, memory, brave-search, etc.
- **Composio integration**: Google Calendar, Gmail, Google Sheets, Notion, GitHub, Slack, etc.
  - HTTP transport with SSE (Server-Sent Events) support
  - Set `COMPOSIO_API_KEY` environment variable
  - Enable in `config.yml` under `mcp.servers.composio`
- **Tool limiting**: Set `mcp.max_tools` to limit total tools (default: 20)
  - Built-in tools prioritized over third-party
  - OpenAI has hard limit of 128 tools
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
1. Add command metadata to `COMMANDS` list in `core/commands.py`
2. Implement handler method in mode files:
   - SSH: `async def cmd_mycommand(self, args: str = "") -> None` in `modes/ssh_chat.py`
   - Web: `def _cmd_mycommand(self, args: str = "") -> Dict[str, Any]` in `modes/web_chat.py`
3. Command handlers are auto-detected using `inspect.signature()`:
   - If handler has `args` parameter without default value, args are passed automatically
   - No need to maintain hardcoded list of commands that need args
4. Web handler returns `Dict[str, Any]` with keys: `response`, `face`, `status`, optionally `error`

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
