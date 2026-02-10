# Quick Start Guide

Get Inkling running in 10 minutes on any computer for development, or on a Raspberry Pi for the full e-ink experience.

## Prerequisites

- Python 3.9 or higher
- Git
- One API key from: Anthropic, OpenAI, or Google (Gemini)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/inkling-bot.git
cd inkling-bot
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

Create a `.env` file in the project root:

```bash
cp .env.example .env
nano .env
```

Add at least one API key:

```bash
# Choose one or more:
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-api-key-here
```

### 5. Run Inkling

**SSH/Terminal Mode** (development):
```bash
python main.py --mode ssh
```

**Web UI Mode** (browser interface):
```bash
python main.py --mode web
# Then open http://localhost:8081
```

## First Interaction

Once running, try these commands:

```
> Hello!
# Inkling will greet you back

> /help
# Shows all available commands

> /mood
# Shows current mood and intensity

> /tasks
# Lists your tasks (empty at first)

> /task Buy groceries
# Creates a new task

> /done <task-id>
# Marks task complete and awards XP
```

## Understanding the Interface

### SSH Mode
```
┌─ Inkling ─────────────────────────────────┐
│ (^_^)  Inkling                    1h 23m  │
├───────────────────────────────────────────┤
│                                           │
│           Hello! How are you?             │
│                                           │
├───────────────────────────────────────────┤
│ (^_^) | L1 NEWB | 54%mem | CHAT3 | SSH    │
└───────────────────────────────────────────┘
```

- **Face**: Shows current mood (^_^) = happy
- **Level**: L1 NEWB = Level 1, Newborn Inkling
- **Stats**: Memory usage, CPU, temperature
- **Mode**: CHAT3 = 3 messages in conversation

### Web Mode

Navigate to `http://localhost:8081`:
- **Chat**: Main conversation interface
- **Settings**: Personality, AI config, themes
- **Tasks**: Kanban board for task management
- **Files**: Browse `~/.inkling/` directory

## Configuration

### Basic Config

Copy the default config for customization:

```bash
cp config.yml config.local.yml
nano config.local.yml
```

Key settings:

```yaml
device:
  name: "Inkling"  # Your companion's name

ai:
  primary: "anthropic"  # anthropic, openai, or gemini

personality:
  curiosity: 0.7      # 0.0-1.0
  cheerfulness: 0.6
  verbosity: 0.5
  playfulness: 0.6
  empathy: 0.7
  independence: 0.4

memory:
  enabled: true
  prompt_context:
    enabled: true
  capture:
    rule_based: true
    llm_enabled: false

focus:
  enabled: true
  default_work_minutes: 25
  short_break_minutes: 5
  long_break_minutes: 15
  sessions_until_long_break: 4
  quiet_mode_during_focus: true
```

### Enable Task Management

Task management is enabled by default through MCP. Verify in config:

```yaml
mcp:
  enabled: true
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

## Common Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/mood` | Current mood and intensity |
| `/level` | XP, level, and achievements |
| `/tasks` | List all tasks |
| `/task <title>` | Create new task |
| `/done <id>` | Complete task (awards XP) |
| `/stats` | AI token usage |
| `/system` | System info (CPU, memory, temp) |
| `/memory` | Memory stats and recent entries |
| `/focus start [minutes] [task]` | Start a focus session |
| `/focus pause` | Pause active focus session |
| `/focus resume` | Resume paused focus session |
| `/focus break` | Start a break immediately |
| `/focus status` | Show current focus timer state |
| `/focus stats` | Show today's focus totals |
| `/focus week` | Show 7-day focus totals |
| `/clear` | Clear conversation history |
| `/quit` | Exit (SSH mode only) |

## Troubleshooting

### "No AI providers configured"

Ensure your API key is set:
```bash
# Check if key is loaded
echo $ANTHROPIC_API_KEY

# Or check .env file
cat .env
```

### "Module not found" errors

Activate the virtual environment:
```bash
source .venv/bin/activate
```

### Web UI not loading

Check port 8081 is free:
```bash
lsof -i :8081
# If occupied, change port in config.local.yml
```

### Display not updating

For development, ensure mock display:
```yaml
display:
  type: "mock"
```

## Next Steps

1. **Customize Personality**: [Personality Tuning Guide](../configuration/personality-tuning.md)
2. **Set Up Hardware**: [Hardware Assembly Guide](hardware-assembly.md)
3. **Add Integrations**: [MCP Integration Guide](../features/mcp-integration.md)
4. **Build a Case**: [Enclosures Guide](../hardware/enclosures.md)

## Running on Raspberry Pi

For the full e-ink experience, see the [Hardware Assembly Guide](hardware-assembly.md).

Quick Pi setup:

```bash
# Enable SPI
sudo raspi-config
# Interface Options > SPI > Enable

# Install system dependencies
sudo apt update
sudo apt install python3-pip python3-venv libopenjp2-7

# Clone and setup (same as above)
git clone https://github.com/your-repo/inkling-bot.git
cd inkling-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with auto display detection
python main.py --mode ssh
```

## Running as a Service

To run Inkling automatically on boot:

```bash
# Create service file
sudo nano /etc/systemd/system/inkling.service
```

```ini
[Unit]
Description=Inkling AI Companion
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/inkling-bot
Environment="PATH=/home/pi/inkling-bot/.venv/bin"
ExecStart=/home/pi/inkling-bot/.venv/bin/python main.py --mode web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable inkling
sudo systemctl start inkling

# Check status
sudo systemctl status inkling
```
