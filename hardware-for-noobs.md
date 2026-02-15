# Hardware Setup for Complete Beginners

**Never built anything with electronics before? Perfect! This guide is for you.**

This is a step-by-step guide to building your own Inkling AI companion device. We'll use simple language and explain everything along the way.

## What You'll Build

A small, portable device that:
- Has a screen showing your AI companion's face
- Talks to you using AI (like ChatGPT, but your own personal friend)
- Fits in your pocket
- Runs on battery power
- Has a web interface you can access from your phone

**Total time**: 2-3 hours (most of that is waiting for downloads)
**Difficulty**: Easy - if you can follow a recipe, you can do this

## Before You Buy Anything

### Try It First (Recommended!)

You don't need any hardware to try Inkling. You can run it on your regular computer first to see if you like it.

**Try it on your laptop/desktop**:
1. Follow the [Quick Start Guide](reference/getting-started/quick-start.md)
2. Chat with your Inkling for a few days
3. If you love it, come back and build the hardware version

**Why build hardware?**
- Take it anywhere (no laptop needed)
- Always on and ready
- Cool e-ink screen that doesn't hurt your eyes
- Fun to show friends
- Learn about building electronics projects

## Shopping List

### What You Need to Buy ($50-60 total)

**The Brain**: Raspberry Pi Zero 2W ($15)
- This is a tiny computer (smaller than a credit card)
- Has WiFi built-in (you'll need this)
- Where to buy: [Adafruit](https://www.adafruit.com/product/5291), [SparkFun](https://www.sparkfun.com/products/18713), or search "Raspberry Pi Zero 2W"
- ⚠️ Make sure it says "Zero 2W" not just "Zero" - the W means it has WiFi

**The Screen**: Waveshare 2.13" E-Ink Display ($20-25)
- This is like a Kindle screen - easy to read, saves battery
- Version: Get V3 if you can find it (faster), V4 is fine too
- Where to buy: [Amazon](https://www.amazon.com/s?k=waveshare+2.13+e-ink), [Waveshare official store](https://www.waveshare.com/product/displays/e-paper.htm)

**The Storage**: MicroSD Card ($8)
- 8GB or bigger
- Must say "Class 10" or "U1" on it
- Where to buy: Amazon, Best Buy, Target

**The Power**: USB Power Adapter ($10)
- 5V, 2.5A (this means volts and amps - just check the label)
- Official Raspberry Pi adapter is safest
- Where to buy: Electronics store, Amazon

**The Connection**: GPIO Header (Usually included)
- These are the pins that let the screen talk to the computer
- Most Pi Zero 2W come with this already attached
- If yours doesn't have pins, you'll need to buy them separately ($2)

**Total**: About $55-60

### Optional Extras (Buy Later)

You can add these after you get it working:

- **Battery** ($10-15): Makes it portable
- **Battery Manager** ($15-25): PiSugar 2 or LiPo SHIM - keeps battery safe
- **Case** ($10-20): 3D printed or bought - protects your device
- **Heat Sink** ($5): Keeps it cool if you use it a lot

### Which Screen Should I Get?

There are two versions of the screen:

**V3** (older but better):
- ✅ Updates faster
- ✅ Better for interactive use
- ✅ Usually cheaper
- ⚠️ Sometimes has "ghosting" (faint images from before)

**V4** (newer but slower):
- ✅ Cleaner image
- ✅ Less ghosting
- ⚠️ Takes 5+ seconds to update (feels slow)

**Bottom line**: Get V3 if you can find it. V4 works fine too. Inkling automatically detects which one you have.

## Tools You Already Have

- **A computer** (Mac, Windows, or Linux)
- **A way to read SD cards** (built into many laptops, or buy a $5 USB adapter)
- **WiFi at home** (for setup and for the AI to work)

You probably DON'T need:
- ❌ Soldering iron (unless your Pi doesn't have pins attached)
- ❌ Monitor/keyboard for the Pi
- ❌ Special cables

## Step 1: Prepare the SD Card

Think of this like installing Windows on a computer, but for your tiny Raspberry Pi.

### Download the Installer (5 minutes)

1. Go to [raspberrypi.com/software](https://www.raspberrypi.com/software/)
2. Download "Raspberry Pi Imager"
3. Install it on your computer

### Write the Operating System (30 minutes)

1. **Put SD card in your computer**
   - Use built-in slot or USB adapter

2. **Open Raspberry Pi Imager**

3. **Choose the OS**:
   - Click "Choose OS"
   - Select "Raspberry Pi OS (other)"
   - Pick "Raspberry Pi OS Lite (64-bit)"
   - (We pick "Lite" because we don't need desktop graphics - saves space!)

4. **Choose your SD card**:
   - Click "Choose Storage"
   - Select your SD card
   - ⚠️ **IMPORTANT**: Make absolutely sure you picked the right card - everything on it will be erased!

5. **Configure settings** (THE MOST IMPORTANT PART):
   - Click the gear icon ⚙️ in the bottom right
   - This is how you'll connect to your Pi without needing a monitor

   **Fill these in**:
   - ✅ **Hostname**: `inkling` (or any name you like)
   - ✅ **Enable SSH**: Check the box, choose "password authentication"
   - ✅ **Username**: `pi` (recommended, easier to follow guides)
   - ✅ **Password**: Pick a password you'll remember
   - ✅ **WiFi**:
     - SSID: Your WiFi network name (exactly as it appears)
     - Password: Your WiFi password
     - WiFi country: Your country (US, GB, etc.)
   - ✅ **Timezone**: Your timezone
   - ✅ **Keyboard**: Your keyboard layout (usually US)

6. **Write it**:
   - Click "Save"
   - Click "Write"
   - Say "Yes" to the warning
   - Wait 5-10 minutes
   - When it's done, eject the SD card safely

**What just happened?** You installed an operating system on the SD card and told it how to connect to your WiFi. When you power on the Pi, it will automatically join your network.

## Step 2: First Boot and Connect

### Power It On

1. **Take the SD card out of your computer**
2. **Put it in the Pi**:
   - SD card slot is on the bottom
   - Metal contacts face UP
   - Push it in until it clicks
3. **Plug in power**:
   - Use the port labeled "PWR IN" (not the one labeled "USB")
   - Green LED should start blinking
4. **Wait 2-3 minutes**:
   - First boot takes longer
   - The green LED will blink a lot - this is normal

### Connect to Your Pi

Your Pi is now on your WiFi. Let's talk to it!

**On Mac or Linux**:
1. Open Terminal (search for "Terminal" in your applications)
2. Type this and press Enter:
   ```bash
   ssh pi@inkling.local
   ```
3. If it asks "Are you sure?", type `yes` and press Enter
4. Enter the password you set earlier

**On Windows**:
1. Open PowerShell (search for "PowerShell" in the Start menu)
2. Type this and press Enter:
   ```bash
   ssh pi@inkling.local
   ```
3. If it asks "Are you sure?", type `yes` and press Enter
4. Enter the password you set earlier

**If that doesn't work**:
- Your Pi might not be showing up as `inkling.local`
- Find your Pi's IP address:
  - Check your WiFi router's admin page (usually 192.168.1.1)
  - Or download "Fing" app on your phone
  - Look for device named "inkling" or "Raspberry Pi"
- Connect using the IP instead:
  ```bash
  ssh pi@192.168.1.XXX
  ```
  (Replace XXX with the actual numbers)

**Success looks like**:
```
pi@inkling:~ $
```

You're now controlling your Pi from your computer! Everything you type here runs on the Pi.

### Update Everything

Before we do anything else, let's update the system. Copy these commands one at a time:

```bash
# Get list of updates
sudo apt update
```

(Wait for it to finish, then:)

```bash
# Install updates (takes 5-10 minutes)
sudo apt upgrade -y
```

(This will download and install updates. Be patient!)

```bash
# Restart to apply updates
sudo reboot
```

The Pi will restart. Wait about 1 minute, then reconnect:

```bash
ssh pi@inkling.local
```

## Step 3: Connect the Display

### Enable the Screen Interface

The screen uses something called "SPI" to talk to the Pi. Let's turn that on:

```bash
sudo raspi-config
```

A menu appears. Use arrow keys to navigate:
1. Arrow down to "Interface Options", press Enter
2. Arrow down to "SPI", press Enter
3. Arrow right to "Yes", press Enter
4. Press Enter on "OK"
5. Arrow right to "Finish", press Enter

Now restart:
```bash
sudo reboot
```

Wait 1 minute, reconnect via SSH.

### Physically Attach the Screen

**⚠️ IMPORTANT: Turn off power first!**

```bash
sudo shutdown -h now
```

Wait 30 seconds until the green LED stops blinking completely, then unplug the power cable.

**Attach the HAT (the screen)**:

1. Look at your Pi - see the 40 pins sticking up? (Two rows of 20 pins)
2. Look at the screen - it has a connector that matches those pins
3. **Line them up**:
   - The screen should sit directly on top of the Pi
   - Make sure the USB ports are on the same end
4. **Press down firmly** until the screen sits flat on the Pi
5. **Check**: All pins should be inside the connector - none sticking out

It should look like a sandwich:
```
┌─────────────────┐
│     SCREEN      │  ← Screen on top
│                 │
└─────────────────┘
        |||          ← Pins connect them
┌─────────────────┐
│  RASPBERRY PI   │  ← Pi on bottom
│    ZERO 2W      │
└─────────────────┘
```

**Plug power back in**

### Check It Worked

Reconnect via SSH and type:

```bash
ls /dev/spi*
```

You should see:
```
/dev/spidev0.0  /dev/spidev0.1
```

If you see those, the screen is connected! 🎉

### Fix Permissions

This lets the software talk to the screen:

```bash
sudo usermod -aG spi,gpio $USER
```

Restart to apply it:
```bash
sudo reboot
```

## Step 4: Install Inkling

Reconnect via SSH after the reboot.

### Install Required Software

```bash
# Update the package list
sudo apt update
```

```bash
# Install everything Inkling needs (takes about 5 minutes)
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

### Download Inkling

```bash
# Make sure you're in your home folder
cd ~

# Download Inkling from GitHub
git clone https://github.com/dkyazzentwatwa/inkling.git

# Go into the folder
cd inkling
```

### Set Up Python

Python is the programming language Inkling is written in. We need to set up a "virtual environment" (think of it like a clean workspace for Inkling):

```bash
# Create the workspace
python3 -m venv .venv

# Start using it
source .venv/bin/activate
```

Your command prompt should now start with `(.venv)` - this means it worked!

### Install Inkling's Dependencies

```bash
# Install all the Python packages Inkling needs (5-10 minutes)
pip install -r requirements.txt
```

This downloads a bunch of code libraries Inkling uses. Be patient!

### Get an AI API Key

Inkling needs to talk to an AI service. You have three choices:

**Option 1: Anthropic Claude (Recommended)**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account (free)
3. Go to "API Keys"
4. Click "Create Key"
5. Copy the key (looks like `sk-ant-api03-xxxxx...`)
6. **Pricing**: About $0.01-0.05 per day of normal chatting

**Option 2: OpenAI ChatGPT**
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account
3. Add payment method (requires $5 minimum)
4. Create API key
5. Copy it (looks like `sk-xxxxx...`)

**Option 3: Google Gemini**
1. Go to [ai.google.dev](https://ai.google.dev)
2. Create account
3. Get API key
4. Copy it

**Save your key to Inkling**:

```bash
# Copy the example file
cp .env.example .env

# Edit it
nano .env
```

You're now in a text editor. Use arrow keys to move around. Add your key:

```bash
# If you chose Anthropic:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx-paste-your-key-here-xxxxx

# OR if you chose OpenAI:
OPENAI_API_KEY=sk-xxxxx-paste-your-key-here-xxxxx

# OR if you chose Google:
GOOGLE_API_KEY=xxxxx-paste-your-key-here-xxxxx
```

**Save and exit**:
- Press `Ctrl+X`
- Press `Y` (for "yes, save")
- Press `Enter`

## Step 5: First Run! 🎉

### Test the Display

Let's make sure the screen works:

```bash
# Make sure you're in the right folder with virtual environment active
cd ~/inkling
source .venv/bin/activate

# Run the display test
python main.py --mode demo
```

**What you should see**:
- The screen turns white (clears)
- A face appears! (looks like `^_^` or similar)
- Text saying "Display Demo"
- Stats at the bottom
- The face changes every few seconds

**Press Ctrl+C to stop**

**If nothing appears on the screen**: Jump to [Troubleshooting](#troubleshooting) below.

### Chat via SSH

Now let's actually talk to your Inkling:

```bash
python main.py --mode ssh
```

You'll see:
```
🌙 Inkling starting...
✅ Display initialized (V3/V4)
✅ Brain initialized (Anthropic/OpenAI/Gemini)
🚀 Ready!

inkling>
```

**Try saying hello**:
```
inkling> Hi there!
```

Your Inkling should respond! The screen should also update with its face and message.

**Try some commands**:
```
inkling> /help
inkling> /mood
inkling> /stats
```

Type `/quit` or press `Ctrl+C` to exit.

### Open the Web Interface

This is the full experience - works from any device on your network!

```bash
python main.py --mode web
```

You'll see:
```
🌐 Starting web UI on http://0.0.0.0:8081
✅ Web UI ready at http://inkling.local:8081
```

**On your phone or laptop**, open a web browser and go to:
```
http://inkling.local:8081
```

Or use the IP address:
```
http://192.168.1.XXX:8081
```

You should see:
- Chat interface (talk to your Inkling)
- Settings page (change personality, AI model, colors)
- Tasks page (Kanban board for to-dos)
- Files page (browse files on your Pi)

**Try it out!** Chat with your Inkling, adjust the personality sliders, try different color themes.

## Step 6: Make It Start Automatically (Optional)

Right now, you have to manually start Inkling every time you power on the Pi. Let's make it automatic!

### Create a Startup Service

```bash
sudo nano /etc/systemd/system/inkling.service
```

Paste this (if your username isn't `pi`, change it in the file):

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

**Save**: Press `Ctrl+X`, then `Y`, then `Enter`

### Enable It

```bash
# Reload system services
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable inkling

# Start it right now
sudo systemctl start inkling

# Check if it's running
sudo systemctl status inkling
```

Should say "active (running)" in green text.

**Now when you power on your Pi**, wait 1-2 minutes and the web interface will be ready automatically! Just go to `http://inkling.local:8081` in your browser.

### View Live Logs (Optional)

Want to see what Inkling is doing?

```bash
journalctl -u inkling -f
```

Press `Ctrl+C` to exit.

## Step 7: Make It Portable (Optional)

### Easy Way: USB Battery Pack

**Simplest solution**:
1. Buy any USB battery pack (the kind you use to charge your phone)
2. Plug it into the Pi's "PWR IN" port
3. Turn on the battery pack
4. Done!

**Battery life**: 3-6 hours depending on battery size (10,000mAh = longer)

### Advanced Way: Built-in Battery

For a more integrated solution:
1. Buy a LiPo battery (1200mAh or bigger) with JST connector
2. Buy a PiSugar 2 or Pimoroni LiPo SHIM
3. Install the battery management board between your Pi and screen
4. Connect the battery

**Benefits**:
- Compact
- Shows battery level
- Safe charging
- Looks professional

**See**: [Battery Guide](reference/hardware/battery-portable.md) for detailed instructions (coming soon)

## Troubleshooting

### The Screen Shows Nothing

**First, check SPI is enabled**:
```bash
ls /dev/spi*
```

Should show `/dev/spidev0.0` and `/dev/spidev0.1`

If not:
```bash
sudo raspi-config
# Go to Interface Options → SPI → Enable
sudo reboot
```

**Check permissions**:
```bash
groups
```

Should include the words `spi` and `gpio`

If not:
```bash
sudo usermod -aG spi,gpio $USER
sudo reboot
```

**Try forcing the display type**:
```bash
nano ~/inkling/config.local.yml
```

Add:
```yaml
display:
  type: "v3"
```

(Or `"v4"` if you have V4)

Save with `Ctrl+X`, `Y`, `Enter`

### The Screen Shows Garbage/Random Pixels

The wrong display version was detected. Force the correct one:

```bash
nano ~/inkling/config.local.yml
```

Add:
```yaml
display:
  type: "v4"  # or "v3" depending on which you have
```

### Can't Connect via SSH

**Test the connection**:
```bash
ping inkling.local
```

No response? Try these:
- Make sure your computer and Pi are on the same WiFi network
- Check you entered WiFi details correctly in Pi Imager
- Try using the IP address instead of `inkling.local`
- Make sure the Pi is powered on (green LED should blink)
- Wait 2-3 minutes after powering on

**Find the IP address**:
- Check your WiFi router's admin page (usually 192.168.1.1 or 192.168.0.1)
- Or download "Fing" app on your phone
- Look for "Raspberry Pi" or "inkling"

### "No API key configured" Error

**Check your .env file**:
```bash
cd ~/inkling
cat .env
```

Make sure:
- Your API key is there
- There's no `#` at the start of the line
- The key is correct (no extra spaces or missing characters)

### "Module not found" or Import Errors

**Activate the virtual environment**:
```bash
cd ~/inkling
source .venv/bin/activate
```

Your prompt should show `(.venv)` at the start.

If you still get errors:
```bash
pip install -r requirements.txt
```

### The Display Doesn't Update

**This is normal!** E-ink screens can't update as fast as regular screens:
- V3: Updates every 0.5 seconds minimum
- V4: Updates every 5+ seconds

The screen needs time to refresh. This is how e-ink works - it saves battery but updates slowly.

### The Pi Gets Hot

The Pi Zero 2W gets warm when working hard. This is normal.

**To keep it cooler**:
- Add a small heatsink (stick-on aluminum piece)
- Make sure your case has ventilation holes
- Don't leave it in direct sunlight
- Check temperature with `/system` command

It will automatically slow down if it gets too hot (above 80°C).

### Web Interface Won't Load

**Check the service is running**:
```bash
sudo systemctl status inkling
```

Should say "active (running)"

If not:
```bash
sudo systemctl start inkling
```

**Check the URL**:
- Try `http://inkling.local:8081`
- Try `http://192.168.1.XXX:8081` (use your Pi's IP)
- Make sure you include the `:8081` port number

**Check firewall**: The Pi's firewall might be blocking it (rare). Disable temporarily:
```bash
sudo ufw disable
```

## Next Steps

### Customize Your Inkling

1. **Web UI → Settings**:
   - Change the name
   - Adjust personality traits (6 sliders)
   - Pick a color theme (13 options!)
   - Change AI model

2. **Try the features**:
   - `/tasks` - Task manager with Kanban board
   - `/schedule` - Background tasks (morning briefings, reminders)
   - `/wifi` - Check WiFi status
   - `/mood` - See current mood and energy

### Learn More

- **Full user guide**: [docs/guides/USAGE.md](docs/guides/USAGE.md)
- **Web UI guide**: [docs/guides/WEB_UI.md](docs/guides/WEB_UI.md)
- **Background tasks**: [docs/BACKGROUND_TASKS.md](docs/BACKGROUND_TASKS.md)
- **Advanced features**: [reference/README.md](reference/README.md)

### Add More Features

- **Remote access**: Enable ngrok in settings to access from anywhere
- **WiFi switching**: Install BTBerryWifi to change WiFi via Bluetooth from your phone
- **Task automation**: Set up scheduled tasks for morning summaries, reminders, etc.
- **MCP tools**: Connect Google Calendar, Gmail, Notion, and more

### Build a Case

Protect your device:
- **3D print**: Find designs on Thingiverse (search "Pi Zero e-ink case")
- **Buy**: Search Amazon for "Raspberry Pi Zero case"
- **DIY**: Get a small project box from an electronics store

### Join the Community

- **GitHub**: Report issues or request features
- **Share**: Post photos of your build!
- **Contribute**: The code is open source

## Tips for Success

### Save Money on AI
- Use Anthropic Claude Haiku (cheapest)
- Set a daily token limit in settings
- Lower the verbosity trait
- Clear conversation history regularly with `/clear`

### Save Battery
- Use SSH mode instead of web mode (uses less power)
- Disable heartbeat (autonomous behaviors) in config
- Lower AI request rate
- Use a bigger battery (10,000+ mAh)

### Keep Display Healthy
- E-ink wears out with too many refreshes
- V3 partial refresh is easier on the display
- Enable screensaver when idle
- Do a full refresh occasionally to clear ghosting

### Development Tips
- Test on your laptop first (with mock display)
- Use SSH mode for debugging
- Check logs with `journalctl -u inkling -f`
- Use web mode for showing off to friends

## Common Questions

**Do I really need to buy all this?**
No! Try Inkling on your laptop first. You might be happy with just that.

**Can I use a different Raspberry Pi?**
Yes! Pi 3, Pi 4, Pi Zero - they all work. Zero 2W is just the smallest and cheapest.

**Do I need to know how to code?**
Nope! Just follow this guide. Copy-paste the commands.

**What if I break something?**
It's very hard to break. Worst case, you re-flash the SD card and start over. Your Pi is safe!

**How much does it cost to run?**
About $0.01-0.05 per day for AI (with moderate chatting). Electricity cost is negligible.

**Can I use it without internet?**
No - Inkling needs internet to talk to the AI service. Local AI support may come in the future.

**Is it safe?**
Yes! Your conversations stay on your Pi. The AI provider (Anthropic/OpenAI/Google) sees your messages per their privacy policy.

**Can I turn it off?**
Just unplug the power! Or run `sudo shutdown -h now` first (safer for SD card).

**What if I get stuck?**
- Read the [Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md)
- Check GitHub issues
- Ask for help in the community

## You Did It! 🎉

You've built your own AI companion device from scratch!

**What you accomplished**:
- ✅ Set up a Raspberry Pi
- ✅ Connected an e-ink display
- ✅ Installed and configured software
- ✅ Connected to an AI service
- ✅ Built a portable AI companion

**Pretty cool, right?**

Now go chat with your new friend! Try teaching it about yourself, give it tasks, customize its personality. Make it yours.

**Welcome to the Inkling community!** 🌙

---

*Need help? See [Getting Help](docs/guides/TROUBLESHOOTING.md) or open an issue on GitHub.*
