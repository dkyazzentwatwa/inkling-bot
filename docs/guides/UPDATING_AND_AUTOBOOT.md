# Safe Updating & Auto-Boot Guide

Complete guide for safely updating Inkling and setting up automatic startup on Raspberry Pi.

---

## 📦 Safe Update Procedure

### What Gets Updated (Safe)
- ✅ Python code files
- ✅ Default `config.yml` template
- ✅ Documentation
- ✅ Dependencies (if `requirements.txt` changed)

### What Stays Safe (Never Touched)
- ✅ `~/.inkling/` directory (all your data)
- ✅ `config.local.yml` (your custom settings)
- ✅ Tasks database (`~/.inkling/tasks.db`)
- ✅ Conversation memory (`~/.inkling/memory.db`)
- ✅ XP, level, and personality state
- ✅ All logs and user files

---

## 🔄 Update Steps

### Method 1: Quick Update (Recommended)

```bash
# 1. SSH into your Pi
ssh pi@your-pi-ip

# 2. Navigate to Inkling directory
cd ~/cypher/inkling-bot  # Or wherever you installed it

# 3. Check current status
git status
git log --oneline -5  # See recent commits

# 4. Pull latest updates
git pull

# 5. Check if dependencies changed
git diff HEAD~1 requirements.txt

# 6. Update dependencies (if needed)
source .venv/bin/activate
pip install -r requirements.txt

# 7. Restart Inkling
sudo systemctl restart inkling

# 8. Verify it's running
sudo systemctl status inkling

# 9. Test the web UI
# Visit http://your-pi-ip:8081
```

### Method 2: Safe Update (With Backup)

```bash
# 1. SSH in
ssh pi@your-pi-ip

# 2. Go to Inkling directory
cd ~/cypher/inkling-bot

# 3. Backup your data (optional but recommended)
tar -czf ~/inkling-backup-$(date +%Y%m%d).tar.gz ~/.inkling/

# 4. Check what will change
git fetch
git log HEAD..origin/main --oneline  # See what's new

# 5. Check for local changes (should be none)
git status

# 6. If you have local changes, stash them
git stash

# 7. Pull updates
git pull

# 8. Check if config.yml changed
git diff HEAD~1 config.yml

# 9. If config.yml changed, update your config.local.yml
# Compare and merge any new settings
nano config.local.yml

# 10. Update dependencies if requirements.txt changed
source .venv/bin/activate
pip install -r requirements.txt --upgrade

# 11. Restart
sudo systemctl restart inkling

# 12. Monitor startup
sudo journalctl -u inkling -f
# Press Ctrl+C when you see it's running

# 13. Test everything
curl http://localhost:8081
# Should return HTML

# 14. Visit web UI and verify features work
```

### Method 3: Nuclear Update (If Something's Broken)

```bash
# 1. Backup everything
tar -czf ~/inkling-full-backup-$(date +%Y%m%d).tar.gz ~/cypher/inkling-bot ~/.inkling/

# 2. Save your config
cp ~/cypher/inkling-bot/config.local.yml ~/config.local.yml.backup

# 3. Reset repository to clean state
cd ~/cypher/inkling-bot
git fetch
git reset --hard origin/main

# 4. Restore your config
cp ~/config.local.yml.backup ~/cypher/inkling-bot/config.local.yml

# 5. Rebuild virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 6. Restart
sudo systemctl restart inkling
sudo systemctl status inkling
```

---

## 🚀 Auto-Boot Setup

Set up Inkling to start automatically when your Raspberry Pi boots.

### Prerequisites

1. **Inkling is installed and working**
   ```bash
   cd ~/cypher/inkling-bot
   source .venv/bin/activate
   python main.py --mode web
   # Should start successfully - press Ctrl+C to stop
   ```

2. **You know your installation path**
   ```bash
   pwd
   # Example output: /home/pi/cypher/inkling-bot
   ```

### Method 1: Systemd Service (Recommended)

**Best for:** Production use, automatic restarts, logging

#### Step 1: Create Startup Script

```bash
# Navigate to Inkling directory
cd ~/cypher/inkling-bot

# Create startup script
cat > start.sh <<'EOF'
#!/bin/bash
cd /home/pi/cypher/inkling-bot
source .venv/bin/activate
exec python main.py --mode web
EOF

# Make it executable
chmod +x start.sh

# Test it works
./start.sh
# Should start - press Ctrl+C to stop
```

#### Step 2: Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/inkling.service > /dev/null <<'EOF'
[Unit]
Description=Inkling AI Companion
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/cypher/inkling-bot
ExecStart=/home/pi/cypher/inkling-bot/start.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**⚠️ Important:** If your Inkling is installed in a different location, update these paths:
- `WorkingDirectory=/home/pi/YOUR/PATH/HERE`
- `ExecStart=/home/pi/YOUR/PATH/HERE/start.sh`
- Also update the path in `start.sh`

#### Step 3: Enable and Start

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable inkling

# Start it now
sudo systemctl start inkling

# Check status
sudo systemctl status inkling
# Should show "active (running)"
```

#### Step 4: Verify Auto-Boot

```bash
# Reboot to test
sudo reboot

# After reboot, SSH back in and check
ssh pi@your-pi-ip
sudo systemctl status inkling
# Should be running automatically
```

### Method 2: Cron @reboot (Simple)

**Best for:** Simple setups, no automatic restart needed

```bash
# Edit crontab
crontab -e

# Add this line at the bottom:
@reboot cd /home/pi/cypher/inkling-bot && /home/pi/cypher/inkling-bot/.venv/bin/python main.py --mode web >> /home/pi/inkling-cron.log 2>&1

# Save and exit (Ctrl+O, Enter, Ctrl+X in nano)

# Test by rebooting
sudo reboot

# After reboot, check if it's running
ps aux | grep "python main.py"
# Should see the process

# Check logs
tail -f ~/inkling-cron.log
```

**Pros of cron:**
- Very simple setup
- No systemd knowledge needed

**Cons of cron:**
- No automatic restart if it crashes
- Harder to manage (start/stop/status)
- Logs to file instead of journalctl

---

## 🛠️ Managing Auto-Boot Service

### Systemd Commands

```bash
# Check if running
sudo systemctl status inkling

# Start service
sudo systemctl start inkling

# Stop service
sudo systemctl stop inkling

# Restart service
sudo systemctl restart inkling

# Enable auto-start on boot
sudo systemctl enable inkling

# Disable auto-start on boot
sudo systemctl disable inkling

# View logs (live)
sudo journalctl -u inkling -f

# View last 100 log lines
sudo journalctl -u inkling -n 100

# View logs since yesterday
sudo journalctl -u inkling --since yesterday
```

### Cron Commands

```bash
# Edit cron jobs
crontab -e

# List cron jobs
crontab -l

# Remove all cron jobs
crontab -r

# View cron logs
tail -f ~/inkling-cron.log
```

---

## 🔍 Troubleshooting

### Service Won't Start

**Check status for errors:**
```bash
sudo systemctl status inkling -l
sudo journalctl -u inkling -n 50
```

**Common issues:**

1. **Wrong paths in service file**
   ```bash
   # Check paths exist
   ls /home/pi/cypher/inkling-bot/start.sh
   ls /home/pi/cypher/inkling-bot/.venv/bin/python

   # Fix service file if needed
   sudo nano /etc/systemd/system/inkling.service
   sudo systemctl daemon-reload
   sudo systemctl restart inkling
   ```

2. **Virtual environment missing**
   ```bash
   cd ~/cypher/inkling-bot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart inkling
   ```

3. **Permission issues**
   ```bash
   # Make sure pi owns the files
   sudo chown -R pi:pi /home/pi/cypher/inkling-bot
   chmod +x /home/pi/cypher/inkling-bot/start.sh
   ```

4. **Port already in use**
   ```bash
   # Kill existing instances
   pkill -f "python main.py"
   sudo systemctl restart inkling
   ```

### Update Broke Something

**Rollback to previous version:**
```bash
cd ~/cypher/inkling-bot

# See recent commits
git log --oneline -10

# Rollback to previous commit
git reset --hard HEAD~1

# Or to specific commit
git reset --hard abc123

# Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Restart
sudo systemctl restart inkling
```

**Restore from backup:**
```bash
# Stop service
sudo systemctl stop inkling

# Restore code and data
tar -xzf ~/inkling-backup-20260204.tar.gz -C /

# Restart
sudo systemctl start inkling
```

### Config Changes After Update

**If `config.yml` changed:**
```bash
# Compare old and new
git diff HEAD~1 config.yml

# Check for new sections or settings
# Example output:
# + storage:
# +   sd_card:
# +     enabled: false

# Add new sections to your config.local.yml
nano config.local.yml

# Add the new settings (if you want to use them)
```

**Your `config.local.yml` overrides `config.yml`**, so:
- Old settings keep working
- New features won't be enabled until you add them
- Safe to skip optional new features

---

## ✅ Post-Update Checklist

After updating, verify everything works:

- [ ] Service is running: `sudo systemctl status inkling`
- [ ] Web UI loads: `http://your-pi-ip:8081`
- [ ] Can chat with AI
- [ ] Tasks still exist: Check `/tasks` page
- [ ] Settings are preserved: Check `/settings` page
- [ ] Files accessible: Check `/files` page
- [ ] Logs show no errors: `sudo journalctl -u inkling -n 50`

---

## 🔐 Security Notes

### API Keys After Update

Your API keys are safe because they're stored in:
- `config.local.yml` (not in git)
- Environment variables (not in git)

**But double-check after major updates:**
```bash
# Verify your API key is still configured
grep -i api_key config.local.yml

# Or check if it's using environment variable
echo $OPENAI_API_KEY
```

### Password Protection

If using ngrok or exposing to internet, always set a password:
```bash
# Add to config.local.yml
nano config.local.yml

# Add:
web:
  web_password: ${SERVER_PW}

# Set environment variable
echo 'export SERVER_PW="your-secure-password"' >> ~/.bashrc
source ~/.bashrc

# Restart
sudo systemctl restart inkling
```

---

## 📊 Update Frequency Recommendations

**Stable setup:**
- Check for updates: Monthly
- Apply updates: When new features you want are added

**Active development:**
- Check for updates: Weekly
- Apply updates: After testing on a backup Pi first

**Critical fixes:**
- Security updates: Immediately
- Bug fixes affecting you: As soon as possible

---

## 🎯 Quick Reference Commands

### Update Inkling
```bash
cd ~/cypher/inkling-bot && git pull && source .venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart inkling
```

### Check Everything
```bash
sudo systemctl status inkling && curl -s http://localhost:8081 | head -1
```

### View Recent Logs
```bash
sudo journalctl -u inkling -n 50 --no-pager
```

### Backup Data
```bash
tar -czf ~/backup-$(date +%Y%m%d).tar.gz ~/.inkling/
```

### Full Restart
```bash
sudo systemctl stop inkling && sleep 2 && sudo systemctl start inkling && sudo systemctl status inkling
```

---

## 📝 Example Update Session

```bash
# Monthly update routine
ssh pi@192.168.1.100

# 1. Backup first
tar -czf ~/backup-$(date +%Y%m%d).tar.gz ~/.inkling/

# 2. Check what's new
cd ~/cypher/inkling-bot
git fetch
git log HEAD..origin/main --oneline

# 3. Pull updates
git pull

# 4. Update dependencies if needed
source .venv/bin/activate
pip install -r requirements.txt

# 5. Restart
sudo systemctl restart inkling

# 6. Verify
sudo systemctl status inkling
curl http://localhost:8081 | head

# 7. Test in browser
# Visit http://your-pi-ip:8081

# Done! ✅
```

---

## 🆘 Emergency Recovery

If everything is broken:

```bash
# 1. Stop everything
sudo systemctl stop inkling
pkill -f "python main.py"

# 2. Restore from backup
cd ~
tar -xzf inkling-backup-YYYYMMDD.tar.gz

# 3. Rebuild virtual environment
cd ~/cypher/inkling-bot
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Test manually first
python main.py --mode web
# Press Ctrl+C if it works

# 5. Start service
sudo systemctl start inkling
sudo systemctl status inkling
```

**Still broken?** Check:
- SD card not corrupted: `df -h`
- Python version: `python3 --version` (should be 3.9+)
- Disk space: `df -h ~/.inkling/`
- Permissions: `ls -la ~/cypher/inkling-bot/`

---

<div align="center">

**[← Back to Documentation Index](../README.md)**

</div>
