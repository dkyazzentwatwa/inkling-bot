# Optional Integrations Guide

This guide covers **optional** external integrations that enhance background tasks.

## ✅ What Works Out of the Box (No Setup)

- **Weather**: Uses free wttr.in API (no key needed)
- **RSS Feeds**: Pre-configured 8 feeds
- **System Monitoring**: Uses psutil
- **Task Management**: Built-in TaskManager
- **Backups**: Local filesystem or SD card
- **MCP Tools**: Tasks, System, Filesystem (built-in)

**Result**: Morning briefing and all background tasks work immediately after `pip install feedparser`.

**Composio is NOT required** - it's completely optional for advanced users who want Gmail/Calendar integration.

---

## 🌤️ Weather Options

### Option 1: wttr.in (Default - FREE, No API Key) ✅

**Status**: Enabled by default
**API Key**: Not required
**Provides**: Current conditions + temperature

**Example output**: `☀️ Portland: ☀️  +52°F`

**How it works**:
- Uses public wttr.in service
- Format: `https://wttr.in/Portland,OR?format=%C+%t`
- No rate limits for reasonable use
- ANSI codes automatically stripped

**Configuration**: None needed! Set location in `config.yml`:
```yaml
background_tasks:
  weather:
    city: "Portland"
    state: "OR"
    country: "US"
```

---

### Option 2: OpenWeatherMap (Optional Upgrade)

**Status**: Disabled by default
**API Key**: Required (free tier available)
**Provides**: Detailed weather data (humidity, pressure, wind, etc.)

**Example output**: `☀️ Portland: 52°F, Cloudy`

**Setup**:
1. Sign up: https://openweathermap.org/api
2. Get free API key (1000 calls/day)
3. Set environment variable:
   ```bash
   export OPENWEATHER_API_KEY=your_key_here
   ```
4. Restart Inkling

**Fallback**: If API key not set, uses wttr.in automatically.

**Rate Limits**: Free tier = 1,000 calls/day (plenty for 1 call/day at 7 AM)

---

## 📧 Composio MCP (Google Calendar + Gmail)

### What It Provides

**Morning Briefing Enhancements**:
- Google Calendar: Events for the day
- Gmail: Unread count + top 3 urgent subjects
- Google Sheets: (Future) Metrics logging
- GitHub: (Future) Notifications
- Slack: (Future) Unread messages

**Future Use Cases**:
- Email Zero Assistant (Phase 3)
- Calendar-based task scheduling
- Automated meeting summaries
- Task creation from emails

---

### Setup Guide

**Status**: Disabled by default (commented out in `config.yml`)

**1. Get API Key**:
- Sign up: https://app.composio.dev/settings
- Free tier available
- Copy your API key

**2. Set Environment Variable**:
```bash
export COMPOSIO_API_KEY=your_key_here
```

**3. Enable in config.yml**:

Edit `config.yml` or `config.local.yml`:
```yaml
mcp:
  enabled: true
  max_tools: 30  # Increase from 20 to accommodate Google tools
  servers:
    # ... existing servers ...

    # Uncomment Composio section:
    composio:
      transport: "http"
      url: "https://backend.composio.dev/v3/mcp"
      headers:
        x-api-key: "${COMPOSIO_API_KEY}"
```

**4. Connect Google Account**:

Visit Composio dashboard and connect:
- Google Calendar
- Gmail
- (Optional) Google Sheets

**5. Restart Inkling**:
```bash
python main.py --mode ssh
```

**6. Verify Tools Loaded**:

Check startup logs:
```
[MCP] Loaded tools from composio: gmail_*, googlecalendar_*, googlesheets_*
```

**7. Test Morning Briefing**:

Set schedule to 1 minute from now and verify calendar/email appear in output.

---

### Composio Free Tier Limits

- **API Calls**: 1,000/month (plenty for daily briefings)
- **Connected Apps**: Unlimited
- **Tool Access**: All 500+ integrations

**Daily Usage Estimate**:
- Morning briefing: 2-3 calls (calendar + email)
- Monthly: ~60-90 calls

---

### Troubleshooting Composio

**Tools not loading?**
1. Check API key: `echo $COMPOSIO_API_KEY`
2. Verify in config: `max_tools: 30` (increased from 20)
3. Check logs: `INKLING_DEBUG=1 python main.py --mode ssh`

**No calendar events showing?**
1. Visit Composio dashboard
2. Verify Google Calendar connected
3. Check permissions granted

**Morning briefing skips email/calendar?**
- Expected if Composio not enabled
- Rest of briefing still works (weather + tasks)

---

## 🎯 Recommended Setup

### Minimal Setup (5 minutes)
```bash
# Install dependencies
pip install feedparser

# Start Inkling - weather works immediately!
python main.py --mode ssh
```

**What you get**:
- ✅ Weather (wttr.in)
- ✅ RSS digest
- ✅ Task reminders
- ✅ System monitoring
- ✅ Nightly backups

---

### Enhanced Setup (15 minutes)
```bash
# 1. Minimal setup above

# 2. Get Composio API key
# Visit: https://app.composio.dev/settings

# 3. Set environment variable
export COMPOSIO_API_KEY=your_key

# 4. Enable in config.local.yml
# Uncomment composio section

# 5. Connect Google apps in dashboard

# 6. Restart Inkling
```

**What you get**:
- ✅ Everything from minimal
- ✅ Google Calendar events
- ✅ Gmail unread summaries
- ✅ Future AI assistant enhancements

---

### Premium Setup (Optional)
```bash
# Add OpenWeatherMap for detailed weather
export OPENWEATHER_API_KEY=your_key
```

**What you get**:
- ✅ Everything from enhanced
- ✅ Detailed weather (humidity, pressure, wind)

---

## 📊 Cost Comparison

| Integration | Cost | Rate Limit | Setup Time |
|-------------|------|------------|------------|
| wttr.in | **FREE** | Reasonable use | 0 min |
| OpenWeatherMap | FREE tier | 1000/day | 5 min |
| Composio | FREE tier | 1000/month | 15 min |

**Monthly Background Task Cost**: $0.00 (all free tiers) + $2.22 AI tokens = **$2.22/month**

---

## 🔍 Quick Status Check

### Check What's Enabled

```bash
# 1. Start Inkling with debug
INKLING_DEBUG=1 python main.py --mode ssh

# 2. Look for these lines:

# Weather (wttr.in):
[Scheduler] Morning briefing triggered
☀️ Portland: ☀️  +52°F

# Weather (OpenWeatherMap):
☀️ Portland: 52°F, Cloudy

# Composio:
[MCP] Loaded tools from composio: gmail_*, googlecalendar_*
```

### Test Morning Briefing

```bash
# Change schedule to 1 minute from now
# Edit config.local.yml:
- name: "test_briefing"
  schedule: "every().day.at('HH:MM')"  # Current time + 1 min
  action: "morning_briefing"
  enabled: true

# Restart and wait
python main.py --mode ssh
```

**Expected output**:
```
☀️ Portland: ☀️  +52°F                    # wttr.in
📅 3 events today: ...                    # Composio (if enabled)
📧 12 unread: ...                         # Composio (if enabled)
✅ 2 tasks due today                       # TaskManager
😊 Good morning! Ready for a productive day!  # AI greeting
```

---

## 📚 Related Documentation

- **Background Tasks**: `docs/BACKGROUND_TASKS.md`
- **Quick Start**: `docs/QUICK_START_BACKGROUND_TASKS.md`
- **Main Config**: `config.yml`
- **Composio Docs**: https://docs.composio.dev/

---

## 🎉 Summary

**Out of the box**: Weather, RSS, tasks, backups all work immediately.

**Optional**: Add Composio for Google Calendar/Gmail if desired.

**Recommendation**: Start with minimal setup, add Composio later if you want calendar/email integration.
