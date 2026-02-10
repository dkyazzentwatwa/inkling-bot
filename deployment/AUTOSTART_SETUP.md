# Inkling Autostart Setup

Configure Inkling to start automatically when your Raspberry Pi boots.

## Choose Your Mode

You can run **either** web mode or SSH mode on startup (not both simultaneously).

### Option 1: Web Mode (Recommended for Always-On Device)

**Best for**: Accessing via browser from phone/computer, headless operation

```bash
# Copy service file
sudo cp deployment/inkling-web.service /etc/systemd/system/

# Create environment file with API keys
cat > /home/pi/inkling/.env << EOF
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
EOF

# Enable and start service
sudo systemctl enable inkling-web.service
sudo systemctl start inkling-web.service

# Check status
sudo systemctl status inkling-web.service
```

**Access**: Open `http://inkling.local:8081` in any browser

### Option 2: SSH Mode

**Best for**: Direct terminal interaction, development

```bash
# Copy service file
sudo cp deployment/inkling-ssh.service /etc/systemd/system/

# Create environment file
cat > /home/pi/inkling/.env << EOF
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
EOF

# Enable and start service
sudo systemctl enable inkling-ssh.service
sudo systemctl start inkling-ssh.service
```

**Access**: SSH into the Pi and attach to the session

## Environment File

Create `/home/pi/inkling/.env` with your API keys:

```bash
# Required for AI features
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional: Enable debug output
# INKLING_DEBUG=1

# Optional: Custom config
# INKLING_CONFIG=/path/to/config.yml
```

## Managing the Service

```bash
# View logs
sudo journalctl -u inkling-web.service -f

# Stop service
sudo systemctl stop inkling-web.service

# Restart service
sudo systemctl restart inkling-web.service

# Disable autostart
sudo systemctl disable inkling-web.service

# Check if running
sudo systemctl status inkling-web.service
```

After upgrading Inkling code, restart the service to load schema/runtime changes:

```bash
cd /home/pi/inkling
git pull
sudo systemctl restart inkling-web.service
```

## Switching Modes

To switch from web to SSH mode (or vice versa):

```bash
# Stop current mode
sudo systemctl stop inkling-web.service
sudo systemctl disable inkling-web.service

# Enable new mode
sudo systemctl enable inkling-ssh.service
sudo systemctl start inkling-ssh.service
```

## Running Both Modes (Advanced)

If you want to run both modes simultaneously, you'd need to:

1. **Modify the code** to support concurrent modes
2. Run them on different ports/interfaces
3. Share the same personality/brain state

**Current limitation**: The architecture supports only one mode at a time because:
- Both modes share the same `Personality` instance
- Display manager can only be in one mode
- Concurrent access could cause state conflicts

**Workaround**: Run two separate Pi devices, or modify `main.py` to support concurrent modes.

## Troubleshooting

### Service won't start
```bash
# Check for errors
sudo journalctl -u inkling-web.service -n 50

# Verify Python environment
/home/pi/inkling/.venv/bin/python --version

# Test manual run
cd /home/pi/inkling
.venv/bin/python main.py --mode web
```

### Can't access web UI
```bash
# Check if service is running
sudo systemctl status inkling-web.service

# Check port binding
sudo netstat -tlnp | grep 8081

# Check firewall
sudo ufw status

# Test locally
curl http://localhost:8081
```

### Environment variables not loading
```bash
# Verify .env file exists
cat /home/pi/inkling/.env

# Check file permissions
ls -la /home/pi/inkling/.env

# Should be readable by pi user
chmod 600 /home/pi/inkling/.env
```

## Installation Paths

Update the service files if your installation is in a different location:

```ini
# Edit these paths in the .service file:
WorkingDirectory=/your/path/to/inkling
EnvironmentFile=/your/path/to/.env
ExecStart=/your/path/to/.venv/bin/python main.py --mode web
```

## Persistent Local Data

Inkling stores runtime data under `~/.inkling/`:
- `tasks.db` (task system)
- `memory.db` (conversation memory)
- `focus.db` (focus/pomodoro sessions and weekly stats)
- `conversation.json` (chat history)

Keep this directory across reboots/deploys if you want continuity.

## Default Choice

**Recommendation**: Use **web mode** for autostart because:
- ✅ Accessible from any device on your network
- ✅ No SSH session required
- ✅ Better for "always-on" companion device
- ✅ Includes task, memory, and `/focus` workflows in one place
- ✅ Phone-friendly interface

Only use SSH mode for autostart if you primarily interact via terminal.
