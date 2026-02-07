# GEMINI.md - Project Inkling Context

## Project Overview
**Project Inkling** (also referred to as `tiff-bot` in this environment) is a fully local AI companion device designed for the Raspberry Pi Zero 2W with an e-ink display. Inspired by Pwnagotchi, it features an evolving personality, mood system, XP/leveling mechanics, and proactive behaviors.

### Main Technologies
- **Language:** Python 3.11+
- **AI Providers:** Multi-provider support (Anthropic Claude, OpenAI GPT, Google Gemini, Ollama Cloud, Groq) with automatic fallback and token budgeting.
- **Web Framework:** [Bottle](http://bottlepy.org/) (used for the Web UI).
- **Task Management:** SQLite-backed task manager with AI integration via MCP.
- **Tool Integration:** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for extending AI capabilities (tasks, system stats, filesystem).
- **Display:** Support for Waveshare 2.13" e-ink displays (V3/V4) and a Mock display for development.
- **Networking:** BTBerryWifi for Bluetooth-based WiFi configuration.

### System Architecture
The project follows a modular, subsystem-based architecture:
- **`core/brain.py`**: The AI logic center, handling provider switching, retries, and token budgets.
- **`core/personality.py`**: A state machine managing moods (Happy, Curious, Bored, etc.), traits, and interaction history.
- **`core/display.py`**: Manages the e-ink display output, including ASCII faces and system stats.
- **`core/tasks.py`**: Core task management logic (Kanban, priorities, XP rewards).
- **`core/mcp_client.py`**: Integration with MCP servers for tool usage.
- **`core/heartbeat.py`**: Handles autonomous behaviors and spontaneous thoughts.
- **`core/progression.py`**: Tracks XP, levels, and achievements.

## Building and Running

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure (copies default to local override)
cp config.yml config.local.yml
```

### Key Execution Commands
- **SSH/Terminal Mode:** `python main.py --mode ssh` (Best for development)
- **Web UI Mode:** `python main.py --mode web` (Accessible at http://localhost:8081)
- **Display Demo:** `python main.py --mode demo` (Cycles through all faces)
- **Debug Mode:** `INKLING_DEBUG=1 python main.py --mode ssh`

### Testing
- **Run all tests:** `pytest`
- **Run specific test:** `pytest tests/test_commands.py`

## Development Conventions

### Coding Style & Patterns
- **Asynchronous Programming:** Extensive use of `asyncio` for non-blocking I/O (AI calls, heartbeat, web server).
- **Type Hinting:** Modern Python type hints are used throughout the codebase.
- **Low-Memory Optimization:** Aggressive garbage collection (`gc`) and minimal traceback limits configured in `main.py` to fit the Pi Zero 2W's 512MB RAM.
- **Configuration:** Preferences are stored in `config.yml` (and `.local.yml`). Environment variables (via `.env`) are used for sensitive keys.
- **Persistence:** Personality state and conversation history are saved in `~/.inkling/` as JSON. Tasks are stored in an SQLite database.

### Integration Principles
- **Slash Commands:** Interactions are often handled via slash commands (e.g., `/mood`, `/tasks`, `/level`).
- **AI Constraints:** System prompts strictly enforce brief responses (1-2 sentences) to fit the limited e-ink display real estate.
- **Fallback Logic:** The Brain subsystem is designed to be resilient, falling back to secondary AI providers if the primary one is rate-limited or fails.

## Key Files
- `main.py`: Entry point and subsystem orchestrator.
- `core/`: Core logic modules (Brain, Personality, Display, etc.).
- `modes/`: Interaction interfaces (SSH, Web).
- `mcp_servers/`: Custom MCP servers providing tools to the AI.
- `docs/`: Comprehensive guides for setup, usage, and development.
- `CLAUDE.md`: Technical summary for AI assistants.
