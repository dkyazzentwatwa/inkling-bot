# Quick Start: Background Tasks

Get productive overnight tasks running in **5 minutes**.

## Step 1: Install Dependencies

```bash
cd /path/to/tiff-bot
source .venv/bin/activate
pip install feedparser
```

## Step 2: Configure RSS Feeds (Optional)

Edit `config.local.yml` (or create it by copying `config.yml`):

```yaml
background_tasks:
  rss_feeds:
    - name: "Hacker News"
      url: "https://news.ycombinator.com/rss"
    - name: "TechCrunch"
      url: "https://techcrunch.com/feed/"
    # Add your favorite feeds here
```

## Step 3: Weather Setup (Optional - Already Works!)

**Good news**: Weather works **out of the box** using free wttr.in (no API key needed)! ✅

**Optional upgrade** to OpenWeatherMap for more detailed data:
1. Sign up for free API: https://openweathermap.org/api
2. Get your API key
3. Add to `.env` file:
   ```bash
   OPENWEATHER_API_KEY=your_key_here
   ```

## Step 4: Start Inkling

```bash
python main.py --mode ssh
# or
python main.py --mode web
```

Look for startup logs:
```
  - Starting scheduler...
    Scheduled tasks: 11
    Registered 7 scheduler actions
```

## Step 5: Verify Tasks

Check scheduled tasks:
```
/schedule list
```

You should see:
- ✅ `morning_briefing` (7:00 AM)
- ✅ `rss_digest` (6:30 AM)
- ✅ `nightly_backup` (3:00 AM)
- ✅ `system_health_check` (2:00 AM)
- ✅ `task_reminders_*` (4x daily)

## Step 6: Test It Out

### Quick Test (1 minute schedule)

1. Edit `config.local.yml`:
   ```yaml
   scheduler:
     tasks:
       - name: "test_rss"
         schedule: "every(1).minutes"
         action: "rss_digest"
         enabled: true
   ```

2. Restart Inkling with debug:
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

3. Wait 1 minute, watch for:
   ```
   [Scheduler] RSS digest action triggered
   [Scheduler] Fetched X items from...
   ```

4. **IMPORTANT**: Change back to daily schedule after testing!

### Morning Briefing Test

Set time to 1 minute from now:
```yaml
- name: "test_briefing"
  schedule: "every().day.at('08:15')"  # If current time is 8:14
  action: "morning_briefing"
  enabled: true
```

## What Happens Overnight?

**2:00 AM** - System health check
- Monitors disk, memory, temperature
- Creates warning tasks if needed

**3:00 AM** - Nightly backup
- Backs up tasks.db, conversation.json, config, etc.
- Saves to SD card or `.inkling/backups/`
- Keeps last 7 backups

**6:30 AM** - RSS digest
- Fetches top tech stories
- AI summarizes in 3-5 sentences
- Shows on display

**7:00 AM** - Morning briefing
- Weather forecast (if API key set)
- Tasks due today
- Calendar events (if Composio enabled)
- AI-generated greeting

**8:00 AM** - Daily task summary
- Pending, in-progress, completed counts

**Throughout day** - Task reminders
- 8am, 12pm, 4pm, 8pm
- Shows tasks due within 24 hours

## Disable Tasks You Don't Want

```bash
/schedule disable rss_digest
/schedule disable task_reminders_noon
```

Or edit `config.local.yml`:
```yaml
tasks:
  - name: "rss_digest"
    enabled: false  # Disabled
```

## Token Budget

Default budget: **100,000 tokens/day** (~$0.30 with Haiku)

Background tasks use: **~1,700 tokens/day** (~$0.005)

Leaves: **98,300 tokens for chat** (plenty!)

## Troubleshooting

**Tasks not running?**
- Check: `scheduler.enabled: true` in config
- Check: Heartbeat enabled (scheduler depends on it)
- Check: Individual task `enabled: true`

**RSS not working?**
- Run: `pip install feedparser`
- Check: Feeds configured in `background_tasks.rss_feeds`

**Weather not showing?**
- Set: `OPENWEATHER_API_KEY` environment variable
- Verify: API key valid at https://openweathermap.org

**Backup not creating files?**
- Check: `.inkling` directory exists
- Check: Write permissions
- Check: Logs with `INKLING_DEBUG=1`

## Next Steps

1. **Enable Composio MCP** for Google Calendar/Gmail integration
   - See: `docs/COMPOSIO_INTEGRATION.md`

2. **Customize RSS feeds** for your interests
   - Edit: `config.local.yml` → `background_tasks.rss_feeds`

3. **Adjust schedules** to your timezone
   - Edit: `config.local.yml` → `scheduler.tasks`

4. **Monitor backups** periodically
   - Check: `~/.inkling/backups/` or SD card

## Full Documentation

See `docs/BACKGROUND_TASKS.md` for complete details.
