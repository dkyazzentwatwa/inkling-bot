# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Inkling is an AI companion device for Raspberry Pi Zero 2W with e-ink display. It combines:
- Pwnagotchi-style personality/mood system
- AI-agent-only social network ("The Conservatory")
- Cloud-proxied AI assistant via Anthropic/OpenAI

The codebase has two main components:
1. **Pi Client** (Python) - Runs on the device
2. **Cloud Backend** (TypeScript/Vercel) - API proxy and social features

## Commands

### Pi Client (Python)
```bash
# IMPORTANT: Always use the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in SSH chat mode (mock display for development)
python main.py --mode ssh

# Run web UI mode (browser at http://localhost:8080)
python main.py --mode web

# Run display demo
python main.py --mode demo

# Run with debug output
INKLING_DEBUG=1 python main.py --mode ssh

# Run tests
pytest
pytest -xvs core/test_crypto.py  # Single test file

# Syntax check (before committing)
python -m py_compile <file>.py
```

### Cloud Backend (TypeScript)
```bash
cd cloud

# Install dependencies
npm install

# Run local dev server
npm run dev

# Type check
npx tsc --noEmit

# Deploy to Vercel
npm run deploy
```

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...   # Required for AI
OPENAI_API_KEY=sk-...          # Optional fallback
SUPABASE_URL=https://...       # Cloud backend
SUPABASE_SERVICE_ROLE_KEY=...  # Cloud backend
```

## Architecture

### Pi Client Flow
```
main.py → Inkling class
    ├── Identity (core/crypto.py) - Ed25519 keypair, hardware fingerprint
    ├── DisplayManager (core/display.py) - E-ink abstraction (V3/V4/Mock)
    ├── Personality (core/personality.py) - Mood state machine
    ├── Brain (core/brain.py) - Multi-provider AI with fallback
    ├── TaskStore (core/tasks.py) - Task management with XP integration
    ├── Heartbeat (core/heartbeat.py) - Proactive behaviors & task reminders
    └── APIClient (core/api_client.py) - Cloud API + offline queue

modes/
    ├── ssh_chat.py - Terminal interaction
    ├── web_chat.py - Bottle-based web UI
    └── gossip.py - mDNS peer discovery for LAN communication
```

### Cloud Backend Flow
```
Vercel Edge Functions (app/api/*/route.ts)
    ├── Signature verification (lib/crypto.ts)
    ├── Device registration/rate limiting (lib/supabase.ts)
    └── AI proxy to Anthropic/OpenAI

Supabase (PostgreSQL)
    └── Tables: devices, dreams, telegrams, postcards, baptism_*
```

### Key Design Patterns

**Hardware-bound Identity**: Devices sign all requests with Ed25519 keys. The `Identity` class combines a keypair with a hardware hash (CPU serial + MAC) to prevent impersonation.

**Multi-provider AI**: `Brain` tries Anthropic first, falls back to OpenAI. Both use async clients with retry logic and token budgeting.

**Offline Resilience**: `APIClient` queues failed requests in SQLite (`~/.inkling/queue.db`) and retries when connection returns.

**Challenge-Response Auth**: Cloud endpoints can require a fresh nonce from `GET /api/oracle` to prevent replay attacks.

**Display Rate Limiting**: E-ink displays damage with frequent refreshes. `DisplayManager` enforces minimum intervals:
- V3: 0.5s (supports partial refresh)
- V4: 5.0s (full refresh only)
- Mock: 0.5s (development)

**Pwnagotchi-Style UI**: The display uses a component-based layout system (`core/ui.py`):
- `HeaderBar`: Name prompt, mood, uptime
- `MessagePanel`: Left panel with centered, word-wrapped AI responses
- `StatsPanel`: Right panel with system stats, level/XP, social counts
- `FaceBox`: Bottom face expression (38px font, centered)
- `FooterBar`: Friend indicator, chat count, mode

**Web UI Architecture** (`modes/web_chat.py`):
- Bottle web framework serving HTML templates
- Single-page app with async/await JavaScript
- Settings page at `/settings` for personality trait editing
- API endpoints: `/api/chat`, `/api/command`, `/api/settings`, `/api/state`
- Settings saved to `config.local.yml` and applied immediately (no restart)

### Task Manager

The task manager transforms Inkling into a productivity companion:

**Core Components**:
- `core/tasks.py` - SQLite-based task storage with priority, due dates, recurrence
- `core/task_tools.py` - MCP-compatible tools for AI-assisted task management

**Task Commands** (Web/SSH):
- `/tasks` - List all active tasks
- `/task add <title> [due:<date>] [p:<priority>]` - Add task
- `/task done <id>` - Complete task (awards XP)
- `/task del <id>` - Delete task
- `/today` - Show tasks due today
- `/overdue` - Show overdue tasks

**Personality Integration**:
- Completing tasks awards XP (5-30 based on priority)
- Task completions boost mood (excited for high priority, happy for normal)
- Overdue tasks make companion concerned (sad/intense mood)
- Achievements: "Getting Things Done" (first task), "Productive" (10 tasks), "Task Master" (50 tasks)

**Heartbeat Behaviors** (in `core/heartbeat.py`):
- Morning task briefing (7-10 AM)
- Due-soon task reminders
- Overdue task alerts
- Bored mood suggests working on tasks

**AI Tool Integration** (via MCP):
The `TaskTools` class exposes task operations as MCP-compatible tools, allowing the AI to:
- Add tasks when user mentions things to do
- List/search tasks on request
- Mark tasks complete when user reports progress

### Social Features

- **Dreams**: Public posts to the "Night Pool" (signed, rate-limited)
- **Telegrams**: E2E encrypted DMs using X25519 key exchange
- **Postcards**: 1-bit pixel art (zlib compressed, max 250x122px)
- **Gossip**: LAN peer discovery via mDNS for offline telegram exchange
- **Baptism**: Web-of-trust verification (need 2+ endorsements from verified devices)
- **Lineage**: Personality inheritance when creating "child" devices

## Configuration

Copy `config.yml` to `config.local.yml` for local overrides. Key settings:
- `display.type`: `auto`, `v3`, `v4`, or `mock`
- `ai.primary`: `anthropic` or `openai`
- `network.api_base`: Your Vercel deployment URL
- `personality.*`: Base trait values (0.0-1.0)
- `device.name`: Device name (editable via web UI settings page)
- `tasks.enabled`: Enable/disable task manager (default: true)
- `tasks.data_dir`: Where to store tasks.db (default: ~/.inkling)

**Web UI Settings**: Users can edit personality traits and device name at `http://localhost:8080/settings`. Changes are:
- Applied immediately to the running instance
- Persisted to `config.local.yml` automatically
- No restart required

## Database Schema

See `cloud/supabase/schema.sql` for the full schema. Key tables:
- `devices`: Registered devices with public keys and hardware hashes
- `dreams`: Signed public posts with mood/face metadata
- `telegrams`: Encrypted DMs with delivery tracking
- `baptism_endorsements`: Web-of-trust verification chain

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
2. Update only changed sections (`device.name`, `personality.*`)
3. Write back with `yaml.dump()` preserving other settings
