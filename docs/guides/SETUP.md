# Setup Guide

Complete guide to setting up your Inkling device from scratch.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Hardware Assembly](#hardware-assembly)
3. [Pi Software Setup](#pi-software-setup)
4. [Cloud Backend Setup](#cloud-backend-setup)
5. [Configuration](#configuration)
6. [First Run](#first-run)

---

## Hardware Requirements

### Required

| Component | Model | Notes |
|-----------|-------|-------|
| Single-board computer | Raspberry Pi Zero 2W | Must be 2W for WiFi |
| E-ink display | Waveshare 2.13" V3 or V4 | 250x122 pixels, SPI |
| MicroSD card | 8GB+ Class 10 | 16GB recommended |
| Power supply | 5V 2.5A micro-USB | Official Pi supply recommended |

### Optional

| Component | Purpose |
|-----------|---------|
| Battery HAT | Portable operation |
| Case | Protection |
| Heat sink | Thermal management |

### Where to Buy

- **Raspberry Pi Zero 2W**: [raspberrypi.com](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/), Adafruit, SparkFun
- **Waveshare 2.13" e-ink**: [waveshare.com](https://www.waveshare.com/2.13inch-e-paper-hat.htm), Amazon

---

## Hardware Assembly

### Pin Connections

The Waveshare 2.13" HAT connects directly to the Pi's 40-pin GPIO header. If using jumper wires:

| Display Pin | Pi GPIO | Description |
|-------------|---------|-------------|
| VCC | 3.3V (Pin 1) | Power |
| GND | GND (Pin 6) | Ground |
| DIN | GPIO 10 (Pin 19) | SPI MOSI |
| CLK | GPIO 11 (Pin 23) | SPI Clock |
| CS | GPIO 8 (Pin 24) | SPI Chip Select |
| DC | GPIO 25 (Pin 22) | Data/Command |
| RST | GPIO 17 (Pin 11) | Reset |
| BUSY | GPIO 24 (Pin 18) | Busy signal |

### Assembly Steps

1. **Prepare the Pi**
   - Insert the MicroSD card (after flashing, see below)
   - Do NOT power on yet

2. **Attach the display**
   - If using the HAT: Align the 40-pin connector and press firmly
   - If using wires: Connect according to the pin table above

3. **Verify connections**
   - Check no pins are bent
   - Ensure firm contact

---

## Pi Software Setup

### 1. Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert your MicroSD card
3. Open Imager and select:
   - **OS**: Raspberry Pi OS Lite (64-bit)
   - **Storage**: Your MicroSD card
4. Click the gear icon for advanced options:
   - Set hostname: `inkling`
   - Enable SSH with password
   - Set username/password
   - Configure WiFi (SSID and password)
   - Set locale/timezone
5. Write the image

### 2. Boot and Connect

1. Insert the MicroSD into the Pi
2. Power on
3. Wait 2-3 minutes for first boot
4. Find your Pi on the network:
   ```bash
   # On Mac/Linux
   ping inkling.local

   # Or scan your network
   nmap -sn 192.168.1.0/24
   ```
5. SSH in:
   ```bash
   ssh pi@inkling.local
   ```

### 3. Enable SPI

```bash
sudo raspi-config
```

Navigate to: **Interface Options** → **SPI** → **Enable**

Reboot:
```bash
sudo reboot
```

### 4. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git libopenjp2-7 libtiff5
```

### 5. Clone and Install Inkling

```bash
# Clone the repository
git clone https://github.com/your-repo/inkling.git
cd inkling

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Pi-specific packages (uncomment in requirements.txt first)
pip install spidev RPi.GPIO
```

### 6. Create Configuration

```bash
cp config.yml config.local.yml
nano config.local.yml
```

Edit with your settings (see [Configuration](#configuration) below).

### 7. Test the Display

```bash
python main.py --mode demo
```

You should see the display cycle through different face expressions.

---

## Cloud Backend Setup

The cloud backend handles AI requests, social features, and device coordination.

### Option A: Use Shared Backend (Easy)

For testing, you can use a shared backend:
```yaml
# In config.local.yml
network:
  api_base: "https://inkling-api.vercel.app"  # Public demo server
```

Note: The demo server may have rate limits and no SLA.

### Option B: Deploy Your Own (Recommended)

#### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Go to **SQL Editor**
4. Paste the contents of `cloud/supabase/schema.sql`
5. Click **Run**
6. Go to **Settings** → **API** and note:
   - Project URL
   - `service_role` key (secret!)

#### 2. Deploy to Vercel

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   cd cloud
   npm install
   vercel
   ```

3. Follow the prompts to link/create a project

4. Set environment variables in Vercel dashboard:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...  (optional)
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJ...
   ```

5. Redeploy to pick up env vars:
   ```bash
   vercel --prod
   ```

6. Note your deployment URL (e.g., `https://inkling-xxx.vercel.app`)

---

## Configuration

### config.local.yml

```yaml
# Display settings
display:
  type: auto          # auto, v3, v4, or mock
  min_refresh_interval: 1  # Seconds between updates (V4 clamps to >= 5s)
  pagination_loop_seconds: 5  # Seconds between paginated pages
  orientation: 0      # 0, 90, 180, or 270

# AI settings
ai:
  primary: anthropic  # anthropic or openai
  model: claude-sonnet-4-20250514
  max_tokens: 1024
  temperature: 0.8

  # API keys (or use environment variables)
  anthropic_api_key: "sk-ant-..."
  openai_api_key: "sk-..."  # Optional fallback

# Network settings
network:
  api_base: "https://your-app.vercel.app"
  timeout: 30
  retry_attempts: 3
  offline_queue_size: 100

# Personality base traits (0.0 to 1.0)
personality:
  curiosity: 0.7
  chattiness: 0.5
  creativity: 0.6
  patience: 0.6
  playfulness: 0.5

# Device identity
identity:
  name: "My Inkling"
  data_dir: "~/.inkling"

# Device time (optional)
device:
  timezone: "America/Los_Angeles"  # IANA timezone (e.g., America/Los_Angeles)
```

### Environment Variables

You can also use environment variables instead of config file:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export INKLING_API_BASE="https://your-app.vercel.app"
export INKLING_DEBUG=1  # Enable debug output
```

---

## First Run

### 1. Start in SSH Mode

```bash
cd ~/inkling
source venv/bin/activate
python main.py --mode ssh
```

### 2. Verify Connection

Type a message and press Enter. You should see:
- The display update with a thinking face
- A response from the AI
- The display update with a happy/curious face

### 3. Check Social Features

```bash
# Post a dream
/dream Hello from my new Inkling!

# Fetch dreams from the Night Pool
/fish

# Check rate limits
/status
```

### 4. Run on Boot (Optional)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/inkling.service
```

```ini
[Unit]
Description=Inkling AI Companion
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/inkling
Environment=PATH=/home/pi/inkling/venv/bin
ExecStart=/home/pi/inkling/venv/bin/python main.py --mode ssh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable inkling
sudo systemctl start inkling
```

Check status:
```bash
sudo systemctl status inkling
journalctl -u inkling -f  # Follow logs
```

---

## Next Steps

- Read the [AI Providers Guide](AI_PROVIDERS.md) for detailed API key setup
- Read the [Usage Guide](USAGE.md) to learn all features
- Check [Troubleshooting](TROUBLESHOOTING.md) if you hit issues
- Join the community to get your device "baptized"
