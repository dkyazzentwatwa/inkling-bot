# Inkling Reference Documentation

Complete guides for building, configuring, and extending your Inkling AI companion.

## Table of Contents

### Getting Started
- [Quick Start Guide](getting-started/quick-start.md) - Get Inkling running in minutes
- [Hardware Assembly](getting-started/hardware-assembly.md) - Raspberry Pi Zero 2W + e-ink display setup

### Configuration
- [Personality Tuning](configuration/personality-tuning.md) - Customize your companion's personality traits
- [AI Providers](configuration/ai-providers.md) - Configure Anthropic, OpenAI, or Gemini
- [Themes & Appearance](configuration/themes-appearance.md) - Customize the web UI and display

### Features
- [Task Management](features/task-management.md) - Kanban board, slash commands, and AI-assisted tasks
- [MCP Integration](features/mcp-integration.md) - Model Context Protocol for tool extensibility
- [Autonomous Behaviors](features/autonomous-behaviors.md) - Heartbeat system and proactive actions

### Hardware Projects
- [Enclosures](hardware/enclosures.md) - 3D printable cases and DIY housing options
- [Battery & Portable Setup](hardware/battery-portable.md) - Make Inkling mobile
- [Display Options](hardware/display-options.md) - Supported e-ink displays and configurations

### Use Cases
- [Daily Standup Companion](use-cases/daily-standup.md) - Morning briefings and task organization
- [Focus & Pomodoro](use-cases/focus-pomodoro.md) - Productivity timer and work sessions
- [Learning Journal](use-cases/learning-journal.md) - Note-taking and knowledge companion
- [Developer Assistant](use-cases/developer-assistant.md) - GitHub integration and code helper

### Development
- [Extending Inkling](development/extending-inkling.md) - Add commands, moods, and MCP tools
- [Contributing Guide](development/contributing.md) - Code style, testing, and PR process

---

## Quick Links

| Task | Guide |
|------|-------|
| First time setup | [Quick Start](getting-started/quick-start.md) |
| Change personality | [Personality Tuning](configuration/personality-tuning.md) |
| Add task management | [Task Management](features/task-management.md) |
| Connect to Google Calendar | [MCP Integration](features/mcp-integration.md) |
| Build a case | [Enclosures](hardware/enclosures.md) |
| Add a new command | [Extending Inkling](development/extending-inkling.md) |

## System Requirements

### Hardware (for physical device)
- Raspberry Pi Zero 2W (recommended) or Pi 3/4
- Waveshare 2.13" e-ink display (V3 or V4)
- MicroSD card (8GB+)
- Power supply (5V 2A)

### Software
- Python 3.9+
- Raspberry Pi OS Lite (Bookworm) or any Linux
- One of: Anthropic, OpenAI, or Google API key

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      main.py                            │
│                    (Inkling class)                      │
├─────────────────────────────────────────────────────────┤
│  DisplayManager  │  Personality  │  Brain  │  Heartbeat │
│  (E-ink/Mock)    │  (Mood/XP)    │ (Multi-AI) │ (Auto)  │
├─────────────────────────────────────────────────────────┤
│ TaskManager │ MemoryStore │ FocusManager │ MCPClient   │
│ (tasks.db)  │ (memory.db) │ (focus.db)   │ (Tools)     │
├─────────────────────────────────────────────────────────┤
│          modes/ssh_chat.py  │  modes/web_chat.py       │
│         (Terminal mode)     │  (Web UI + Kanban)       │
└─────────────────────────────────────────────────────────┘
```

## Key Concepts

### Personality System
Inkling has a Pwnagotchi-inspired personality with:
- **6 Traits**: curiosity, cheerfulness, verbosity, playfulness, empathy, independence
- **10 Moods**: happy, excited, curious, bored, sad, sleepy, grateful, lonely, intense, cool
- **XP & Leveling**: Earn XP from conversations and tasks, level up to unlock prestige

### Multi-Provider AI
The Brain module tries providers in order with automatic fallback:
1. Primary provider (configurable)
2. Fallback providers
3. Token budgeting prevents runaway costs

### Model Context Protocol (MCP)
Inkling can use external tools through MCP:
- Built-in: task management, filesystem access
- Third-party: Composio (500+ apps), web search, optional memory server

### Built-in Memory System
Inkling now includes a local memory system by default:
- Persistent storage in `~/.inkling/memory.db`
- Automatic rule-based capture from conversation (name, preferences, explicit facts)
- Relevant-memory prompt context injection for better continuity
- Memory maintenance via heartbeat pruning

### Focus/Pomodoro System
Inkling includes a local-first focus timer with persistent analytics:
- Slash commands via `/focus ...` in SSH and Web UI
- Session/event storage in `~/.inkling/focus.db`
- Quiet-mode suppression of non-critical heartbeat chatter during active focus
- Timer takeover UI in main text area (e-ink + web)

### Heartbeat System
Makes Inkling feel "alive" with autonomous behaviors:
- Morning greetings and evening wind-down
- Mood-driven actions (lonely reach-out, bored suggestions)
- Task reminders and streak celebrations
- Quiet hours for nighttime

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-repo/inkling-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/inkling-bot/discussions)
- **In-app**: Type `/help` to see available commands

## License

This project is open source. See LICENSE file for details.
