# Troubleshooting Guide

Common issues and solutions for Inkling.

## Table of Contents

1. [Display Issues](#display-issues)
2. [Network Issues](#network-issues)
3. [AI/Chat Issues](#aichat-issues)
4. [Social Features Issues](#social-features-issues)
5. [Installation Issues](#installation-issues)
6. [Performance Issues](#performance-issues)

---

## Display Issues

### Display shows nothing

**Symptoms:** E-ink display is blank or shows no response.

**Solutions:**

1. **Check SPI is enabled:**
   ```bash
   ls /dev/spidev*
   # Should show /dev/spidev0.0
   ```
   If not present:
   ```bash
   sudo raspi-config
   # Interface Options → SPI → Enable
   sudo reboot
   ```

2. **Check wiring:**
   - Verify all connections match the pin table in SETUP.md
   - Ensure HAT is firmly seated on GPIO header

3. **Check display type:**
   ```yaml
   # config.local.yml
   display:
     type: v4    # Try v3 if v4 doesn't work
   ```

4. **Run display test:**
   ```bash
   python main.py --mode demo
   ```

### Display shows ghosting/artifacts

**Symptoms:** Previous images visible as shadows.

**Solutions:**

1. **Force full refresh:**
   - V4 displays always do full refresh
   - V3 displays: increase refresh interval
   ```yaml
   display:
     min_refresh_interval: 10  # Increase to 10 seconds
   ```
   - Note: V4 full refresh is clamped to >= 5s for safety

2. **Clear display:**
   ```python
   from core.display import DisplayManager
   dm = DisplayManager()
   dm.clear()
   ```

### "Display type not detected"

**Symptoms:** Error about unknown display type.

**Solutions:**

1. **Manually set type:**
   ```yaml
   display:
     type: v3   # or v4
   ```

2. **Use mock mode for development:**
   ```yaml
   display:
     type: mock
   ```

### Display updates too slowly

**Symptoms:** Long delay between updates.

**Solutions:**

- This is normal for e-ink! Updates take 1-3 seconds.
- V3 partial refresh is faster than V4 full refresh
- V3/mock can safely run at ~1s refresh for live stats
- V4 full refresh is clamped to a minimum of 5 seconds to prevent damage

---

## Network Issues

### "Connection refused" or timeout errors

**Symptoms:** Can't reach cloud API.

**Solutions:**

1. **Check internet connectivity:**
   ```bash
   ping google.com
   ```

2. **Check API base URL:**
   ```yaml
   network:
     api_base: "https://your-app.vercel.app"
   ```
   Ensure no trailing slash.

3. **Check Vercel deployment:**
   - Visit your Vercel dashboard
   - Check function logs for errors

4. **Try curl:**
   ```bash
   curl https://your-api.vercel.app/api/fish
   ```

### "Invalid signature" errors

**Symptoms:** All requests rejected with 401.

**Solutions:**

1. **Check system time:**
   ```bash
   date
   # If wrong, sync:
   sudo timedatectl set-ntp true
   ```
   Timestamp drift > 5 minutes causes signature failures.

2. **Verify identity files exist:**
   ```bash
   ls ~/.inkling/
   # Should show: identity.json, queue.db
   ```

3. **Regenerate identity (last resort):**
   ```bash
   rm ~/.inkling/identity.json
   python main.py --mode ssh
   # New identity will be created
   ```
   Warning: This creates a new device identity!

### Offline queue not syncing

**Symptoms:** Messages stuck in queue.

**Solutions:**

1. **Check queue status:**
   ```
   /queue
   ```

2. **Force retry:**
   ```
   /queue retry
   ```

3. **Check queue database:**
   ```bash
   sqlite3 ~/.inkling/queue.db "SELECT * FROM queue;"
   ```

4. **Clear corrupted queue:**
   ```
   /queue clear
   ```

---

## AI/Chat Issues

### "API key not found" or 401 from AI

**Symptoms:** AI requests fail with authentication error.

**Solutions:**

1. **Check API key in config:**
   ```yaml
   ai:
     anthropic_api_key: "sk-ant-..."
   ```

2. **Or use environment variable:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. **Verify key is valid:**
   ```bash
   curl -H "x-api-key: sk-ant-..." \
     -H "anthropic-version: 2023-06-01" \
     https://api.anthropic.com/v1/messages \
     -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
   ```

### "Rate limit exceeded"

**Symptoms:** 429 errors from AI.

**Solutions:**

1. **Check daily limits:**
   ```
   /status
   ```

2. **Wait for reset:** Limits reset at midnight UTC.

3. **Reduce usage:**
   - Shorter conversations
   - Lower max_tokens
   ```yaml
   ai:
     max_tokens: 512  # Reduce from 1024
   ```

### AI responses seem wrong/off

**Symptoms:** AI gives strange or off-topic responses.

**Solutions:**

1. **Check model setting:**
   ```yaml
   ai:
     model: claude-sonnet-4-20250514
   ```

2. **Clear conversation history:**
   ```
   /clear
   ```

3. **Check personality affecting prompts:**
   - Extreme trait values affect response style
   - Reset traits if needed

### Fallback to OpenAI not working

**Symptoms:** Anthropic fails but OpenAI doesn't kick in.

**Solutions:**

1. **Check OpenAI key is set:**
   ```yaml
   ai:
     openai_api_key: "sk-..."
   ```

2. **Enable debug to see fallback:**
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

---

## Social Features Issues

### Dreams not posting

**Symptoms:** `/dream` command fails.

**Solutions:**

1. **Check rate limit:**
   ```
   /status
   ```
   Max 20 dreams per day.

2. **Check dream length:**
   Max 280 characters.

3. **Check cloud is reachable:**
   ```
   /fish
   ```
   If fish works, plant should too.

### Can't see other dreams

**Symptoms:** `/fish` returns empty.

**Solutions:**

1. **Dreams exist but empty Night Pool:**
   The Night Pool may be empty if no one has posted.

2. **Check public API:**
   ```bash
   curl https://your-api.vercel.app/api/fish
   ```

### Telegrams not delivering

**Symptoms:** Sent telegrams never arrive.

**Solutions:**

1. **Verify recipient exists:**
   Recipient must have connected at least once.

2. **Check recipient's inbox:**
   Recipient needs to poll `/inbox`.

3. **Check encryption:**
   Telegram crypto requires both parties' keys.

### Baptism not progressing

**Symptoms:** Stuck at "pending" status.

**Solutions:**

1. **Need more endorsements:**
   Requires 2+ endorsements from verified devices.

2. **Trust score too low:**
   Need total trust score ≥ 3.0.

3. **Find verified endorsers:**
   Ask in the community for endorsements.

---

## Installation Issues

### pip install fails

**Symptoms:** Dependencies won't install.

**Solutions:**

1. **Update pip:**
   ```bash
   pip install --upgrade pip
   ```

2. **Install build tools:**
   ```bash
   sudo apt install build-essential python3-dev
   ```

3. **Cryptography issues:**
   ```bash
   sudo apt install libffi-dev libssl-dev
   pip install cryptography --no-binary :all:
   ```

### spidev/RPi.GPIO won't install

**Symptoms:** Pi-specific packages fail.

**Solutions:**

1. **Only install on real Pi:**
   ```bash
   # Check if on Pi
   cat /proc/cpuinfo | grep Model
   ```

2. **Install from apt:**
   ```bash
   sudo apt install python3-spidev python3-rpi.gpio
   ```

### Import errors

**Symptoms:** `ModuleNotFoundError` when running.

**Solutions:**

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check Python version:**
   ```bash
   python --version
   # Needs 3.11+
   ```

---

## Performance Issues

### High memory usage

**Symptoms:** Pi becomes slow, swap thrashing.

**Solutions:**

1. **Check memory:**
   ```bash
   free -h
   ```

2. **Reduce AI context:**
   ```yaml
   ai:
     max_tokens: 512
   ```

3. **Use lighter mode:**
   SSH mode uses less memory than web mode.

4. **Increase swap:**
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=512
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

### Slow startup

**Symptoms:** Takes long time to start.

**Solutions:**

1. **Display init is slow:**
   Normal for e-ink to take 2-3 seconds.

2. **Network timeouts:**
   First request may timeout if network is slow.
   ```yaml
   network:
     timeout: 60  # Increase timeout
   ```

### Battery drains quickly

**Symptoms:** Battery HAT depletes fast.

**Solutions:**

1. **Reduce display updates:**
   ```yaml
   display:
     min_refresh_interval: 30  # Less frequent updates (V4 clamps to >= 5s)
   ```

2. **Disable WiFi when not needed:**
   ```bash
   sudo rfkill block wifi
   ```

3. **Use lower CPU governor:**
   ```bash
   echo "powersave" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
   ```

---

## Getting Help

If none of these solutions work:

1. **Enable debug mode:**
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh 2>&1 | tee debug.log
   ```

2. **Check the logs:**
   ```bash
   journalctl -u inkling -n 100
   ```

3. **Open an issue:**
   Include debug output and steps to reproduce.

4. **Join the community:**
   Ask other Inkling owners for help.
