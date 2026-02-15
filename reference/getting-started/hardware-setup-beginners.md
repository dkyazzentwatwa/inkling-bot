# Beginner's Guide to Hardware Setup

A complete step-by-step guide for building your first Inkling companion device. No prior hardware experience required!

## What You'll Build

By the end of this guide, you'll have:
- A functional Raspberry Pi Zero 2W running Inkling
- A connected e-ink display showing your AI companion's face
- A portable, battery-powered device (optional)
- A secure, remotely accessible web interface

**Time to complete**: 2-3 hours (including downloads and setup)

## Before You Start

### Do I Need Hardware?

**No!** You can run Inkling on any computer without hardware. The e-ink display is completely optional.

**Try Inkling first** on your laptop/desktop using the [Quick Start Guide](quick-start.md) to see if you like it before buying hardware.

### Why Build Hardware?

- **Portable**: Take your AI companion anywhere
- **Always-on**: No laptop required
- **E-ink Display**: Easy on eyes, readable in sunlight, runs on battery
- **Fun Project**: Learn about Raspberry Pi and hardware integration

## Shopping List

### Required Components ($50-60)

| Item | Where to Buy | Approx. Cost | Notes |
|------|-------------|--------------|-------|
| **Raspberry Pi Zero 2W** | [Adafruit](https://www.adafruit.com/product/5291), [SparkFun](https://www.sparkfun.com/products/18713), [PiShop](https://www.pishop.us) | $15 | Must have WiFi built-in |
| **Waveshare 2.13" E-Ink HAT** | [Amazon](https://www.amazon.com/s?k=waveshare+2.13+e-ink), [Waveshare Store](https://www.waveshare.com/product/displays/e-paper.htm) | $20-25 | Get V3 or V4 (see below) |
| **MicroSD Card** (8GB+) | Amazon, Best Buy | $8 | Class 10 or better |
| **USB Power Supply** (5V 2.5A) | Amazon, electronics store | $10 | Official Pi adapter recommended |
| **GPIO Header** (2x20 pin) | Included with Zero 2W or separate | $2 | Pre-soldered on most Zero 2W |

**Total**: ~$55-60

### Optional Upgrades ($30-80)

| Item | Cost | Purpose |
|------|------|---------|
| **LiPo Battery** (1200mAh+) | $10-15 | Portable power (3-6 hours) |
| **LiPo SHIM** or **PiSugar 2** | $15-25 | Battery management |
| **3D Printed Case** | $10-20 | Protection and style |
| **Heat Sink Kit** | $5 | Keeps Pi cool during heavy use |

### Display Version: V3 vs V4

**Get V3 if available**:
- ✅ Partial refresh (faster updates)
- ✅ Better for interactive use
- ✅ Less expensive
- ⚠️ Occasional ghosting

**V4 is newer but slower**:
- ✅ Cleaner image
- ✅ Less ghosting
- ⚠️ Full refresh only (slower)
- ⚠️ 5+ second delays between updates

**Either works!** Inkling auto-detects your display.

## Tools You'll Need

- **Computer** (Windows, Mac, or Linux)
- **MicroSD card reader** (built-in or USB adapter)
- **WiFi network** (for setup and AI API access)
- Optional: **Soldering iron** (only if GPIO header not pre-soldered)

## Step 1: Prepare the SD Card (30 minutes)

### Download Raspberry Pi Imager

1. Go to [raspberrypi.com/software](https://www.raspberrypi.com/software/)
2. Download **Raspberry Pi Imager** for your OS
3. Install and open the app

### Flash the OS

1. **Insert SD card** into your computer
2. **Open Raspberry Pi Imager**
3. Click **"Choose OS"**
   - Select **"Raspberry Pi OS (other)"**
   - Choose **"Raspberry Pi OS Lite (64-bit)"** (Bookworm)
   - No desktop needed - saves space!
4. Click **"Choose Storage"**
   - Select your SD card
   - ⚠️ Make sure it's the right card - it will be erased!

### Configure Advanced Options

**This is crucial!** Click the gear icon ⚙️ (bottom right) to open advanced options.

Set these:
- ✅ **Set hostname**: `inkling` (or any name you like)
- ✅ **Enable SSH**: Check "Use password authentication"
- ✅ **Set username and password**:
  - Username: `pi` (recommended)
  - Password: (your choice, remember it!)
- ✅ **Configure WiFi**:
  - SSID: Your WiFi network name
  - Password: Your WiFi password
  - WiFi country: Your country code
- ✅ **Set locale settings**:
  - Time zone: Your time zone
  - Keyboard layout: Your layout

### Write to SD Card

1. Click **"Save"** to save advanced options
2. Click **"Write"**
3. Confirm the warning (data will be erased)
4. Wait 5-10 minutes for writing and verification
5. When done, eject the SD card

**Why this matters**: These settings let you connect to your Pi over WiFi without needing a monitor, keyboard, or mouse (called "headless" setup).

## Step 2: First Boot (10 minutes)

### Insert SD Card and Power On

1. **Remove SD card** from your computer
2. **Insert into Pi**: SD card slot on bottom, contacts facing up
3. **Connect power**: Micro USB port labeled "PWR IN"
4. **Wait 2-3 minutes**: First boot takes longer (green LED flashes)

### Connect via SSH

Your Pi is now on your WiFi network. Let's connect to it!

**On Mac/Linux**:
```bash
# Open Terminal app
ssh pi@inkling.local
```

**On Windows**:
```bash
# Open PowerShell or Command Prompt
ssh pi@inkling.local
```

If `inkling.local` doesn't work, find your Pi's IP address:
- Check your router's admin page
- Or use an app like Fing (iOS/Android)

Then connect with:
```bash
ssh pi@192.168.1.XXX
```

Enter your password when prompted.

**You're in!** You should see:
```
pi@inkling:~ $
```

### Update the System

Run these commands one at a time:

```bash
# Update package lists
sudo apt update

# Upgrade installed packages (takes 5-10 minutes)
sudo apt upgrade -y

# Reboot to apply updates
sudo reboot
```

After reboot, wait 1 minute, then reconnect:
```bash
ssh pi@inkling.local
```

## Step 3: Connect the Display (15 minutes)

### Enable SPI Interface

The e-ink display uses SPI (Serial Peripheral Interface) to communicate. Let's enable it:

```bash
sudo raspi-config
```

Navigate with arrow keys:
1. Select **"Interface Options"** → Enter
2. Select **"SPI"** → Enter
3. Select **"Yes"** to enable → Enter
4. Select **"Finish"** → Enter

Reboot:
```bash
sudo reboot
```

Wait 1 minute, reconnect via SSH.

### Attach the Display

**⚠️ Power off first!**

```bash
sudo shutdown -h now
```

Wait for green LED to stop blinking (30 seconds), then unplug power.

**Connect the HAT**:

1. **Locate GPIO pins**: 40-pin header on Pi (2 rows of 20 pins)
2. **Align the HAT**:
   - Match pins - HAT should sit directly on top
   - USB ports should be on the same side
3. **Press down firmly**: Push until HAT is fully seated
4. **Double-check alignment**: All pins should be connected

**Visual guide**:
```
     E-Ink Display HAT
     ┌─────────────────┐
     │                 │
     │   [DISPLAY]     │
     │                 │
     └─────────────────┘
            |||          ← 40-pin connector
     ┌─────────────────┐
     │  Raspberry Pi   │
     │    Zero 2W      │
     └─────────────────┘
```

**Power back on**: Reconnect the USB cable.

### Verify SPI Connection

Reconnect via SSH and check:

```bash
# Should show /dev/spidev0.0 and /dev/spidev0.1
ls /dev/spi*
```

If you see those files, SPI is working!

### Fix Permissions (Important!)

Add your user to the SPI and GPIO groups:

```bash
sudo usermod -aG spi,gpio $USER
```

Reboot to apply:
```bash
sudo reboot
```

## Step 4: Install Inkling (20 minutes)

Reconnect via SSH after reboot.

### Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install required packages (takes 5 minutes)
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    libopenjp2-7 \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    fonts-dejavu \
    git
```

### Clone Inkling Repository

```bash
# Navigate to home directory
cd ~

# Clone the repo
git clone https://github.com/dkyazzentwatwa/inkling.git

# Enter directory
cd inkling
```

### Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# You should see (.venv) at the start of your prompt
```

### Install Python Dependencies

```bash
# Install Inkling's Python packages (takes 5-10 minutes)
pip install -r requirements.txt
```

### Configure Your API Key

Inkling needs an AI API key to work. Choose one provider:

**Option 1: Anthropic (Recommended)**
- Go to [console.anthropic.com](https://console.anthropic.com)
- Sign up for an account
- Create an API key
- Copy the key (starts with `sk-ant-`)

**Option 2: OpenAI**
- Go to [platform.openai.com](https://platform.openai.com)
- Create an API key
- Copy the key (starts with `sk-`)

**Option 3: Google Gemini**
- Go to [ai.google.dev](https://ai.google.dev)
- Get an API key
- Copy the key

**Add your key**:

```bash
# Create .env file
cp .env.example .env

# Edit it
nano .env
```

Add your key:
```bash
# For Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OR for OpenAI
OPENAI_API_KEY=sk-your-key-here

# OR for Gemini
GOOGLE_API_KEY=your-google-api-key-here
```

Save and exit: **Ctrl+X**, then **Y**, then **Enter**

## Step 5: First Run! (5 minutes)

### Test the Display

```bash
# Make sure virtual environment is active
source .venv/bin/activate

# Run display demo
python main.py --mode demo
```

**What you should see**:
1. Display clears to white
2. Face expression appears
3. Text shows "Display Demo"
4. Stats bar at bottom
5. Cycles through different faces

Press **Ctrl+C** to stop.

**If nothing appears**: See [Troubleshooting](#troubleshooting) section below.

### Run SSH Mode

```bash
python main.py --mode ssh
```

You should see:
```
🌙 Inkling starting...
✅ Display initialized (V3 or V4)
✅ Brain initialized (Anthropic/OpenAI/Gemini)
🚀 Ready! Personality loaded.

inkling>
```

Try chatting:
```
inkling> Hello!
```

Your Inkling should respond, and the display should update with its face and message!

### Run Web Mode

For the full web interface:

```bash
python main.py --mode web
```

Then on your laptop, open a browser to:
```
http://inkling.local:8081
```

(Or use the IP address: `http://192.168.1.XXX:8081`)

You should see the web UI with chat, settings, tasks, and files!

## Step 6: Auto-Start on Boot (Optional, 10 minutes)

Make Inkling start automatically when you power on your Pi.

### Create Service File

```bash
sudo nano /etc/systemd/system/inkling.service
```

Paste this (adjust username and paths if needed):

```ini
[Unit]
Description=Inkling AI Companion
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/inkling
Environment="PATH=/home/pi/inkling/.venv/bin"
ExecStart=/home/pi/inkling/.venv/bin/python main.py --mode web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save: **Ctrl+X**, **Y**, **Enter**

### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable inkling

# Start now
sudo systemctl start inkling

# Check status
sudo systemctl status inkling
```

Should show "active (running)" in green.

### View Logs

```bash
# Follow live logs
journalctl -u inkling -f

# Exit: Ctrl+C
```

Now Inkling will start automatically on boot! Just power on your Pi and wait 1-2 minutes.

## Step 7: Portable Power (Optional, 30 minutes)

### Option A: Simple USB Battery Pack

**Easiest solution**:
1. Get any USB battery pack (phone charger)
2. Connect to Pi's PWR IN port
3. Power on battery pack
4. Done!

**Runtime**: 3-6 hours depending on battery capacity.

### Option B: LiPo Battery with SHIM

**For integrated battery**:

1. **Buy parts**:
   - LiPo battery (1200mAh+ with JST connector)
   - LiPo SHIM (Pimoroni) or PiSugar 2
2. **Install SHIM**: Sits between Pi and display HAT
3. **Connect battery**: JST connector to SHIM
4. **Software setup**: PiSugar has web interface for battery management

**Benefits**:
- Compact design
- Battery level monitoring
- Safe charging circuit

**See**: [Battery & Portable Guide](../hardware/battery-portable.md) for detailed instructions.

## Troubleshooting

### Display Shows Nothing

**Check SPI**:
```bash
ls /dev/spi*
# Should show spidev0.0 and spidev0.1
```

If missing:
```bash
sudo raspi-config
# Enable SPI again
```

**Check permissions**:
```bash
groups
# Should include 'spi' and 'gpio'
```

If missing:
```bash
sudo usermod -aG spi,gpio $USER
sudo reboot
```

**Try different display type**:
```bash
nano ~/inkling/config.local.yml
```

Add:
```yaml
display:
  type: "v3"  # or "v4"
```

### Display Shows Garbage

**Wrong display version detected**. Force the correct one:

```yaml
display:
  type: "v4"  # if you have V4, or "v3" if you have V3
```

### SSH Connection Refused

**Check WiFi**:
```bash
# From your computer
ping inkling.local
```

No response?
- Check WiFi settings in Pi Imager were correct
- Try your Pi's IP address instead
- Make sure Pi is powered on (green LED blinking)

### "No API key configured"

**Check .env file**:
```bash
cd ~/inkling
cat .env
```

Make sure your API key is there and uncommented (no `#` at start of line).

### Python Module Errors

**Activate virtual environment**:
```bash
cd ~/inkling
source .venv/bin/activate
```

Prompt should show `(.venv)`.

### Display Not Updating

**Check rate limits**:
- V3: Updates every 0.5 seconds (partial) or 2 seconds (full)
- V4: Updates every 5+ seconds (full only)

This is normal! E-ink needs time between refreshes.

### Pi Gets Hot

**Normal for Zero 2W under load**. To reduce:
1. Add small heatsink to CPU
2. Ensure ventilation in case
3. Lower AI request rate
4. Check CPU temp: `/system` command

Throttles at 80°C automatically.

## Next Steps

### Customize Your Inkling

1. **Change Name**: Web UI → Settings → Device Name
2. **Adjust Personality**: Settings → 6 trait sliders
3. **Choose AI Model**: Settings → AI Provider (restart required)
4. **Pick a Theme**: Settings → 13 color themes

### Add Features

- **Task Management**: Already enabled! Try `/tasks`
- **Scheduler**: Background tasks (see [Background Tasks Guide](../../docs/implementation/BACKGROUND_TASKS.md))
- **WiFi Switching**: Install BTBerryWifi for Bluetooth WiFi config
- **Remote Access**: Enable ngrok in config for remote web UI

### Build a Case

Protect your hardware:
- **3D Print**: [Enclosures Guide](../hardware/enclosures.md)
- **Buy**: Search "Raspberry Pi Zero case" + "2.13 e-ink"
- **DIY**: Small project box from electronics store

### Learn More

- **Usage Guide**: [docs/guides/USAGE.md](../../docs/guides/USAGE.md)
- **Web UI**: [docs/guides/WEB_UI.md](../../docs/guides/WEB_UI.md)
- **Autonomous Mode**: [docs/guides/AUTONOMOUS_MODE.md](../../docs/guides/AUTONOMOUS_MODE.md)
- **MCP Integration**: [reference/features/mcp-integration.md](../features/mcp-integration.md)

## Tips for Success

### Battery Life
- Web mode uses more power than SSH mode
- Disable heartbeat for longer battery life
- Use lower AI token budgets
- Choose Haiku model (fastest, cheapest)

### Display Longevity
- E-ink wears out with excessive refreshes
- V3 partial refresh is easier on display
- Enable screensaver for idle protection
- Full refresh periodically clears ghosting

### Cost Optimization
- **Anthropic Haiku**: Cheapest per token
- Set daily token limit: `ai.budget.daily_tokens: 10000`
- Use shorter conversations
- Lower verbosity trait

### Development Workflow
- Develop on laptop with mock display first
- Test on Pi before final deployment
- Use SSH mode for debugging
- Web mode for production/demo

## Common Questions

**Q: Can I use a regular Raspberry Pi instead of Zero 2W?**
A: Yes! Any Pi works. Zero 2W is smallest and cheapest for portable use.

**Q: Do I need a monitor/keyboard for setup?**
A: No! Headless setup via SSH is easier and recommended.

**Q: Can I switch between AI providers?**
A: Yes! Change in web UI settings or config.local.yml. Restart required.

**Q: How much does AI usage cost?**
A: ~$0.01-0.05 per day with Haiku at moderate usage. See [AI Providers Guide](../../docs/guides/AI_PROVIDERS.md).

**Q: Can I use it offline?**
A: No. Inkling needs internet for AI API calls. Local AI coming in future version.

**Q: Is my data private?**
A: Yes! Conversations stay on your Pi. API calls go to AI provider (Anthropic/OpenAI/Google) per their privacy policy.

**Q: Can multiple people use the same Inkling?**
A: Yes, but conversation history is shared. Each person won't have their own personality.

## Get Help

- **Documentation**: [reference/README.md](../README.md)
- **Troubleshooting**: [docs/guides/TROUBLESHOOTING.md](../../docs/guides/TROUBLESHOOTING.md)
- **GitHub Issues**: [github.com/dkyazzentwatwa/inkling/issues](https://github.com/dkyazzentwatwa/inkling/issues)

## Summary

Congratulations! You've built your own AI companion device! 🎉

You now have:
- ✅ Raspberry Pi Zero 2W running Inkling
- ✅ E-ink display showing personality
- ✅ Web UI accessible on your network
- ✅ AI-powered chat and task management

**Enjoy your new Inkling companion!**
