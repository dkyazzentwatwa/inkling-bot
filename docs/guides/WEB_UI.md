# 🌐 Web UI Guide

The Inkling web interface provides a beautiful, mobile-friendly way to interact with your AI companion through your browser.

## 🚀 Getting Started

### Starting the Web Server

```bash
# Activate virtual environment
source .venv/bin/activate

# Start web mode
python main.py --mode web

# Open your browser
open http://localhost:8080
```

The server will be available at:
- **Local**: http://localhost:8080
- **Network**: http://YOUR_PI_IP:8080 (accessible from other devices on your network)

### First Visit

When you first open the web UI, you'll see:

1. **Header Bar** - Device name and status
2. **Face Display** - Large emoji showing current mood
3. **Message Area** - Chat history
4. **Command Palette** - Quick access to all commands
5. **Input Area** - Type messages or commands

---

## 💬 Chat Interface

### Sending Messages

Simply type in the input box and press Enter or click Send:

```
Hello! How are you?
```

Inkling will respond based on its current mood and personality traits.

### Message Types

The interface displays three types of messages:

- **User Messages** - Your input (blue left border)
- **Assistant Messages** - Inkling's responses
- **System Messages** - Command outputs (gray left border)

### Live Updates

The interface automatically updates every 5 seconds:
- 😊 Face expression changes with mood
- 📊 Status line updates (level, mood, energy)

---

## 🎯 Command Palette

Click any button to execute a command instantly:

<details>
<summary><b>📊 Info Commands</b></summary>

| Button | Command | Description |
|--------|---------|-------------|
| **Help** | `/help` | Show all available commands |
| **Level** | `/level` | View XP, level, and progression |
| **Stats** | `/stats` | Token usage and budget |
| **History** | `/history` | Recent messages |

</details>

<details>
<summary><b>🎭 Personality Commands</b></summary>

| Button | Command | Description |
|--------|---------|-------------|
| **Mood** | `/mood` | Current mood and intensity |
| **Energy** | `/energy` | Energy level with visual bar |
| **Traits** | `/traits` | All personality traits |

</details>

<details>
<summary><b>🌙 Social Commands</b></summary>

| Button | Command | Description |
|--------|---------|-------------|
| **Fish** | `/fish` | Fetch random dream from Night Pool |
| **Queue** | `/queue` | Offline message queue status |

</details>

<details>
<summary><b>⚙️ System Commands</b></summary>

| Button | Command | Description |
|--------|---------|-------------|
| **System** | `/system` | CPU, memory, temperature |
| **Config** | `/config` | AI provider info |
| **Identity** | `/identity` | Device public key |
| **Faces** | `/faces` | List all face expressions |
| **Refresh** | `/refresh` | Force display refresh |
| **Clear** | `/clear` | Clear conversation |
| **Settings** | - | Open settings page |

</details>

### Command Arguments

Some commands need additional text. Type them in the input box:

```
/face curious          - Test the "curious" face
/dream The night is peaceful...  - Post a dream
```

---

## ⚙️ Settings Page

Click the **Settings** button in the command palette to access configuration.

### Navigation

- **Back to Chat** button returns to the main interface
- Changes are saved immediately when you click "Save Settings"
- Settings are persisted to `config.local.yml`

### 🎨 Appearance Settings

#### Color Themes

Choose from 10 beautiful pastel themes:

| Theme | Colors | Best For |
|-------|--------|----------|
| **Cream** (default) | Warm beige | Easy on the eyes |
| **Pink** | Soft pink | Cute and friendly |
| **Mint** | Fresh green | Calm and refreshing |
| **Lavender** | Gentle purple | Elegant and soothing |
| **Peach** | Warm orange | Cozy and inviting |
| **Sky** | Light blue | Clear and open |
| **Butter** | Pale yellow | Cheerful and bright |
| **Rose** | Dusty pink | Romantic and soft |
| **Sage** | Muted green | Natural and grounded |
| **Periwinkle** | Blue-purple | Dreamy and creative |

**Theme settings are saved to your browser** (localStorage) and persist across sessions.

### 👤 Device & Personality

#### Device Name

Change your Inkling's name (max 20 characters):
- ✅ Applied immediately
- ✅ Visible in header and social posts
- ✅ Can be changed anytime

#### Personality Traits (6 Sliders)

Adjust each trait from 0-100%:

| Trait | Effect |
|-------|--------|
| **Curiosity** | How often it asks questions and explores topics |
| **Cheerfulness** | Tendency toward positive moods |
| **Verbosity** | Response length (low = concise, high = detailed) |
| **Playfulness** | Use of jokes, wordplay, and humor |
| **Empathy** | Emotional attunement to your messages |
| **Independence** | Autonomous behavior frequency |

**Changes apply immediately** to Inkling's behavior!

### 🤖 AI Configuration

⚠️ **Requires Restart** - AI changes take effect after restarting the app.

#### Primary AI Provider

Choose which AI to use:
- **Anthropic (Claude)** - Best for conversation, creative writing
- **OpenAI (GPT)** - Alternative with similar capabilities
- **Google (Gemini)** - Another alternative option

#### Model Selection

Each provider has multiple models with different tradeoffs:

**Anthropic:**
- **Claude 3 Haiku** - Fast and cheap (~$0.25/1M tokens)
- **Claude 3.5 Sonnet** - Balanced performance (~$3/1M tokens)
- **Claude 3 Opus** - Most capable (~$15/1M tokens)

**OpenAI:**
- **GPT-4o Mini** - Fast and affordable
- **GPT-4o** - Balanced and capable
- **o1 Mini** - Advanced reasoning model

**Gemini:**
- **Gemini 2.0 Flash** - Fast and efficient
- **Gemini 1.5 Pro** - More capable

#### Token Budget

Control costs and usage:

| Setting | Default | Range | Impact |
|---------|---------|-------|--------|
| **Max Tokens** | 150 | 50-1000 | Response length |
| **Daily Budget** | 10,000 | 1000-50,000 | Daily spending limit |

**Cost Example (Claude 3 Haiku):**
- 10,000 tokens/day ≈ $0.03/day ≈ $0.90/month

### Saving Settings

Click **💾 Save Settings** to:
- ✅ Apply personality changes immediately
- ✅ Save AI settings to `config.local.yml`
- ✅ Persist device name

Success message tells you what takes effect immediately vs. on restart.

---

## 🎨 Customization

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Ctrl+K` | Focus input field |
| `Ctrl+L` | Clear messages |

### Mobile Experience

The UI is fully responsive:
- 📱 Touch-friendly buttons
- 📏 Adapts to screen size
- 🔄 Swipe to refresh (native browser)
- 💾 Installable as PWA (future)

### Browser Compatibility

Tested and working on:
- ✅ Chrome/Edge (Desktop & Mobile)
- ✅ Firefox (Desktop & Mobile)
- ✅ Safari (Desktop & Mobile)
- ✅ Brave, Arc, etc.

**Minimum Requirements:**
- JavaScript enabled
- LocalStorage support (for themes)
- ES6 support (modern browsers)

---

## 🔧 Advanced Usage

### API Access

Execute commands programmatically:

```bash
# Send a chat message
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# Execute a command
curl -X POST http://localhost:8080/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "/mood"}'

# Get current state
curl http://localhost:8080/api/state

# Get settings
curl http://localhost:8080/api/settings

# Update settings
curl -X POST http://localhost:8080/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NewName",
    "traits": {"curiosity": 0.9}
  }'
```

### Embedding in Other Apps

The web UI can be embedded in:
- Electron apps
- Mobile app WebViews
- Kiosk displays
- Home automation dashboards

Simply load `http://localhost:8080` in any WebView.

### Custom Styling

Want to completely customize the look? Edit the CSS in `modes/web_chat.py`:

```python
# Find HTML_TEMPLATE or SETTINGS_TEMPLATE
# Modify the <style> section
# Restart web mode to see changes
```

Consider theming CSS variables for easier customization:
```css
:root {
    --bg: #yourcolor;
    --text: #yourcolor;
    --accent: #yourcolor;
}
```

---

## 🐛 Troubleshooting

### Page Won't Load

**Problem:** Browser shows "Can't reach this page"

**Solutions:**
1. Check Inkling is running: `ps aux | grep "main.py"`
2. Verify port 8080 is free: `lsof -i :8080`
3. Try `http://127.0.0.1:8080` instead of `localhost`
4. Check firewall settings

### Commands Not Working

**Problem:** Clicking buttons does nothing

**Solutions:**
1. Open browser console (F12) and check for errors
2. Refresh the page (Ctrl+R or Cmd+R)
3. Clear browser cache
4. Try a different browser

### Settings Not Saving

**Problem:** Changes disappear after restart

**Solutions:**
1. Check `config.local.yml` was created
2. Verify file permissions (should be writable)
3. Look for YAML syntax errors in the file
4. Check console for error messages

### Slow Performance

**Problem:** Interface is laggy or unresponsive

**Solutions:**
1. Reduce polling interval in `web_chat.py` (default 5s)
2. Clear old messages with `/clear` command
3. Check CPU usage on Pi: `/system` command
4. Disable unnecessary features in `config.local.yml`

### Theme Not Changing

**Problem:** Theme resets to default

**Solutions:**
1. Check browser allows localStorage
2. Try incognito/private mode to test
3. Clear browser data and try again
4. Check console for storage errors

---

## 💡 Tips & Tricks

### Faster Input

- Use Tab to autocomplete slash commands (future feature)
- Press Up arrow to recall last message (future feature)
- Bookmark `/settings` for quick access

### Better Conversations

- Adjust **Verbosity** trait for response length
- Increase **Curiosity** for more questions
- Raise **Playfulness** for more humor
- Try different AI models for varied styles

### Cost Optimization

- Use **Claude 3 Haiku** for daily chats (cheapest)
- Reduce **Max Tokens** for shorter responses
- Set **Daily Budget** to control spending
- Monitor with `/stats` command regularly

### Multi-Device Access

1. Find your Pi's IP: `hostname -I`
2. Open `http://PI_IP:8080` on phone/tablet
3. Bookmark for easy access
4. Consider setting up HTTPS (future)

---

## 🚀 Future Enhancements

Planned features (not yet implemented):

- [ ] Real-time updates via WebSockets
- [ ] PWA support (install as app)
- [ ] Voice input/output
- [ ] Dark mode (in addition to themes)
- [ ] Gesture controls on mobile
- [ ] Notification support
- [ ] Multi-user chat rooms
- [ ] Export conversation history
- [ ] Custom face/avatar uploads

---

## 📚 Related Documentation

- **[Usage Guide](USAGE.md)** - General Inkling usage
- **[Web Commands](WEB_COMMANDS.md)** - Complete command reference
- **[Settings Plan](SETTINGS_UI_PLAN.md)** - Technical implementation details
- **[Autonomous Mode](AUTONOMOUS_MODE.md)** - Heartbeat and behaviors
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues

---

<div align="center">

**[← Back to Main README](../README.md)**

*Built with ❤️ for the Inkling community*

</div>
