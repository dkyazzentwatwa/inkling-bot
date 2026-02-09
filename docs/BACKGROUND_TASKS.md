# Background Tasks Guide

This guide explains the productive overnight and idle background tasks implemented in Project Inkling.

## Overview

Inkling now runs **6 productive background tasks** during idle periods and overnight hours to maximize the utility of your 24/7 Raspberry Pi Zero 2W. These tasks automate monitoring, backups, information gathering, and daily summaries.

## Journal Directory

Background tasks save their outputs to `~/.inkling/journal/` for persistent storage:

- **Morning Briefing**: `briefing_YYYYMMDD.txt` - Daily weather, tasks, and AI greeting
- **RSS Digest**: `rss_YYYYMMDD.txt` - AI summaries of top tech stories with full headlines
- **System Health**: `health_YYYYMMDD.log` - Timestamped system metrics (appended throughout day)

**Auto-cleanup**: Journal entries older than 30 days are automatically deleted to prevent disk bloat.

**Access**: View journal files via the web UI (`/files` page) or directly on the filesystem.

## Implemented Tasks

### Tier 1: Easy Wins (No External Dependencies)

#### 1. **Nightly Backup** ⭐ CRITICAL
**When**: Daily at 3:00 AM
**What**: Backs up critical files to SD card (if available) or `.inkling/backups/`
**Files backed up**:
- `tasks.db` - Task database
- `conversation.json` - Chat history
- `memory.db` - Conversation memory
- `config.local.yml` - User configuration
- `personality.json` - Personality state

**Features**:
- Compressed `.tar.gz` archives
- Automatic cleanup (keeps last 7 backups)
- Auto-detection of SD card or fallback to local storage
- Display shows backup size on completion

**Configuration**: None required - works out of the box

---

#### 2. **System Health Check** ⭐ CRITICAL
**When**: Daily at 2:00 AM
**What**: Monitors system resources and creates tasks for warnings

**Checks**:
- Disk usage (warns if > 80%)
- Memory usage (warns if > 90%)
- CPU temperature (warns if > 65°C)

**Output**:
- Creates high-priority tasks for warnings
- Logs healthy status to console
- Saves to `~/.inkling/journal/health_YYYYMMDD.log` (appended each check)

**Configuration**: None required

---

#### 3. **Task Deadline Reminders** ⭐ HIGH IMPACT
**When**: Every 4 hours during waking hours (8am, 12pm, 4pm, 8pm)
**What**: Checks for tasks due within 24 hours and displays reminders

**Features**:
- Displays count of tasks due soon
- Shows top task title if only one due
- Non-intrusive notifications

**Configuration**: None required - uses TaskManager

---

### Tier 2: Moderate Effort (Requires Configuration)

#### 4. **Morning AI Briefing** ⭐ HIGH IMPACT
**When**: Daily at 7:00 AM
**What**: Morning summary with weather and tasks

**Includes**:
- Weather forecast (Portland, OR via wttr.in)
- Tasks due today
- AI-generated personalized greeting

**Output**:
- Displays on screen
- Saves to `~/.inkling/journal/briefing_YYYYMMDD.txt`

**Note**: Gmail/Calendar removed (was optional Composio feature)

**Configuration**:

**Weather** (Auto-fallback):
- **Option A**: Free wttr.in (no API key) - Works out of the box! ✅
- **Option B**: OpenWeatherMap (optional, more detailed)
  ```bash
  # Get free API key from: https://openweathermap.org/api
  export OPENWEATHER_API_KEY=your_key_here
  ```
- If no API key: Uses wttr.in automatically
- If API key set: Uses OpenWeatherMap API

**Example Output**:
```
☀️ Portland: 52°F, Cloudy
✅ 2 tasks due today
😊 Good morning! Ready for a productive day!
```

---

#### 5. **RSS Feed Digest** ⭐ HIGH IMPACT
**When**: Daily at 6:30 AM (before morning briefing)
**What**: Fetches RSS feeds, AI summarizes top stories

**Features**:
- Fetches up to 5 configured feeds
- Top 3 items per feed
- AI generates 3-5 sentence summary
- Displays on screen
- Saves to `~/.inkling/journal/rss_YYYYMMDD.txt` with AI summary and full headlines

**Pre-configured Feeds**:
- Hacker News
- TechCrunch
- Ars Technica
- The Verge
- GitHub Blog
- Dev.to
- Anthropic Blog

**Customization**:

Edit `config.local.yml`:
```yaml
background_tasks:
  rss_feeds:
    - name: "Your Feed Name"
      url: "https://example.com/feed.rss"
```

**Dependencies**:
```bash
pip install feedparser
```

---

#### 6. **Daily Task Summary** (Legacy)
**When**: Daily at 8:00 AM
**What**: Summary of task statistics

**Displays**:
- Pending tasks count
- In-progress tasks count
- Tasks completed today

---

#### 7. **Weekly Cleanup** (Placeholder)
**When**: Every Sunday at 2:00 AM
**What**: Planned for future implementation
- Archive old completed tasks (> 30 days)
- Prune old conversation memories
- Database cleanup

---

## Configuration

### Enable/Disable Tasks

All tasks are controlled via `config.local.yml`:

```yaml
scheduler:
  enabled: true  # Master switch
  tasks:
    - name: "morning_briefing"
      schedule: "every().day.at('07:00')"
      action: "morning_briefing"
      enabled: true  # Set to false to disable
```

### Disable Individual Tasks

Use slash commands:
```
/schedule disable morning_briefing
/schedule enable morning_briefing
```

### Schedule Format

Uses Python `schedule` library syntax:

```yaml
# Daily at specific time
schedule: "every().day.at('14:30')"

# Hourly
schedule: "every().hour"

# Weekly
schedule: "every().monday.at('09:00')"

# Every N minutes
schedule: "every(5).minutes"
```

---

## Token Budget

**Daily Token Usage Estimate**:

| Task | Tokens/Day | Cost (Haiku) |
|------|------------|--------------|
| Morning briefing | 600 | $0.002 |
| RSS digest | 1000 | $0.003 |
| Nightly backup | 0 | $0.000 |
| System health | 0 | $0.000 |
| Task reminders | 100 | $0.000 |
| **Background Total** | **1700** | **$0.005** |

This leaves ~98k tokens/day for interactive chat (within default 100k budget).

---

## Environment Variables

**Required**: None! Background tasks work out of the box. ✅

**Optional enhancements**:

```bash
# Weather API (optional - already uses free wttr.in by default)
export OPENWEATHER_API_KEY=your_key_here

# Google Apps (optional - for calendar/email in morning briefing)
export COMPOSIO_API_KEY=your_key_here
```

See `.env.example` for full list.

---

## Testing

### Test Individual Actions

You can manually trigger actions for testing:

1. **Reduce schedule interval** in `config.local.yml`:
   ```yaml
   tasks:
     - name: "test_rss_digest"
       schedule: "every(1).minutes"
       action: "rss_digest"
       enabled: true
   ```

2. **Run with debug logging**:
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

3. **Watch logs** for action execution:
   ```
   [Scheduler] RSS digest action triggered
   [Scheduler] Fetched 30 items from Hacker News
   [AI] Summarizing top stories...
   [Display] Updated with digest
   ```

4. **Change back to daily schedule** after testing.

### View Scheduled Tasks

```bash
/schedule list
```

Output:
```
📅 Scheduled Tasks (7 total)

morning_briefing (enabled)
  Schedule: every().day.at('07:00')
  Action: morning_briefing
  Next run: 2026-02-09 07:00:00

rss_digest (enabled)
  Schedule: every().day.at('06:30')
  Action: rss_digest
  Next run: 2026-02-09 06:30:00
```

---

## Troubleshooting

### RSS Digest Not Working

**Error**: `feedparser not installed`
**Fix**:
```bash
source .venv/bin/activate
pip install feedparser
```

**Error**: `No RSS feeds configured`
**Fix**: Add feeds to `config.local.yml` under `background_tasks.rss_feeds`

### Morning Briefing Missing Weather

**Error**: Weather not showing
**Fix**: Set `OPENWEATHER_API_KEY` environment variable

### Backup Not Creating Files

**Check**:
1. `.inkling` directory exists: `ls -la ~/.inkling`
2. Write permissions: `ls -ld ~/.inkling`
3. SD card mounted (if using): `df -h | grep media`
4. Logs: `INKLING_DEBUG=1 python main.py --mode ssh`

### Tasks Not Running

**Check**:
1. Scheduler enabled: `config.local.yml` → `scheduler.enabled: true`
2. Task enabled: Check individual task `enabled: true`
3. Action registered: Look for "Registered X scheduler actions" in startup logs
4. Heartbeat running: Scheduler depends on heartbeat ticks (every 60s)

---

## Future Enhancements

### Phase 3: Advanced Features (Not Yet Implemented)

**Email Zero Assistant** (Tier 2):
- AI triages unread emails
- Suggests quick replies or creates tasks
- Categorizes: urgent, informational, spam

**Automated Research Assistant** (Tier 2):
- Processes `#research` tagged tasks overnight
- Web search → AI summarization
- Updates task with findings

**Knowledge Base Building** (Tier 2):
- Reviews conversation history
- Extracts learnings, updates memory.db
- Builds long-term knowledge graph

---

## Implementation Details

### Architecture

**Scheduler**: `core/scheduler.py`
- Cron-style scheduling using `schedule` library
- Actions registered in `main.py` during initialization
- Checked every 60 seconds via Heartbeat

**Action Functions**: `core/scheduler.py:365-584`
- All actions accept `inkling` parameter for component access
- Error handling with detailed logging
- Display updates on completion

**Registration**: `main.py:324-347`
- Actions registered as lambdas: `lambda: action_name(self)`
- Provides access to all Inkling components

### Key Files

- `core/scheduler.py` - Scheduler engine + action implementations
- `main.py` - Action registration during init
- `config.yml` - Default task schedules
- `config.local.yml` - User overrides (edit this)
- `requirements.txt` - Python dependencies

---

## Credits

Based on research from:
- [XDA Developers - Raspberry Pi Zero 2 W Projects](https://www.xda-developers.com/raspberry-pi-zero-2-w-projects-almost-no-power/)
- [RaspberryTips - Raspberry Pi Projects for Home](https://raspberrytips.com/raspberry-pi-projects-for-home/)
- [Summate - AI Summarization](https://summate.io/)
- [Reclaim.ai - Calendar Optimization](https://reclaim.ai/)
