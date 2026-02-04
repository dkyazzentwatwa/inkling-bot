# Hardware Assembly Guide

Build a physical Inkling companion with a Raspberry Pi Zero 2W and e-ink display.

## Bill of Materials

### Required Components

| Component | Description | Approx. Cost |
|-----------|-------------|--------------|
| Raspberry Pi Zero 2W | Main board with WiFi | $15 |
| Waveshare 2.13" E-Ink HAT | V3 (partial refresh) or V4 | $20-25 |
| MicroSD Card | 8GB+ Class 10 | $8 |
| Power Supply | 5V 2.5A USB | $10 |
| GPIO Header | 2x20 pin (if not pre-soldered) | $2 |

### Optional Components

| Component | Description | Purpose |
|-----------|-------------|---------|
| LiPo Battery | 3.7V 1200mAh+ | Portable operation |
| LiPo SHIM | Pimoroni/Adafruit | Battery management |
| Case | 3D printed or purchased | Protection |
| Heat Sink | Aluminum mini heatsink | Thermal management |

## Raspberry Pi Setup

### 1. Flash Raspberry Pi OS

Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

1. Select **Raspberry Pi OS Lite (64-bit)** - Bookworm
2. Click gear icon for advanced options:
   - Set hostname: `inkling`
   - Enable SSH with password
   - Set username/password
   - Configure WiFi
   - Set locale/timezone
3. Flash to SD card

### 2. First Boot

Insert SD card and power on. Wait 2-3 minutes for first boot.

```bash
# SSH into Pi
ssh pi@inkling.local
# Or use IP address if hostname doesn't resolve
```

### 3. Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 4. Enable SPI Interface

```bash
sudo raspi-config
```

Navigate to:
- **Interface Options** > **SPI** > **Enable**
- **Interface Options** > **I2C** > **Enable** (optional, for sensors)

Reboot:
```bash
sudo reboot
```

## E-Ink Display Connection

### Waveshare 2.13" HAT Pinout

The display HAT connects directly to the Pi's 40-pin GPIO header:

```
┌────────────────────────────────────────┐
│  Waveshare 2.13" E-Ink Display HAT    │
├────────────────────────────────────────┤
│  VCC  → 3.3V (Pin 1)                  │
│  GND  → Ground (Pin 6)                │
│  DIN  → SPI MOSI (Pin 19)             │
│  CLK  → SPI SCLK (Pin 23)             │
│  CS   → SPI CE0 (Pin 24)              │
│  DC   → GPIO 25 (Pin 22)              │
│  RST  → GPIO 17 (Pin 11)              │
│  BUSY → GPIO 24 (Pin 18)              │
└────────────────────────────────────────┘
```

### Connection Steps

1. **Power off** the Pi completely
2. Align the HAT with GPIO pins (USB ports on same side)
3. Press down firmly until fully seated
4. Double-check alignment before powering on

### Verify Connection

```bash
# Check SPI is enabled
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1

# Test GPIO access
sudo apt install python3-gpiozero
python3 -c "from gpiozero import Device; print(Device.pin_factory)"
```

## Display Versions

### V3 (Recommended)

- **Partial refresh**: Yes (fast updates)
- **Full refresh time**: ~2 seconds
- **Partial refresh time**: ~0.3 seconds
- **Lifespan**: Better with partial refresh

### V4 (Newer)

- **Partial refresh**: No (full refresh only)
- **Full refresh time**: ~3 seconds
- **Ghosting**: Less than V3
- **Note**: Requires 5+ second delays between refreshes

### Auto-Detection

Inkling auto-detects the display version:

```yaml
# config.yml
display:
  type: "auto"  # Detects V3 or V4
```

Manual override if needed:
```yaml
display:
  type: "v3"  # or "v4"
```

## Software Installation

### 1. Install System Dependencies

```bash
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    libopenjp2-7 \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    fonts-dejavu
```

### 2. Clone and Setup Inkling

```bash
cd ~
git clone https://github.com/your-repo/inkling-bot.git
cd inkling-bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

```bash
cp .env.example .env
nano .env
```

Add your API key:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 4. Test the Display

```bash
# Run display demo
python main.py --mode demo
```

You should see:
1. Display clears to white
2. Face expression appears
3. Text message shows
4. Stats bar at bottom

### 5. Run Inkling

```bash
# SSH mode with real display
python main.py --mode ssh

# Or web mode
python main.py --mode web
```

## Troubleshooting

### Display Shows Nothing

1. Check SPI is enabled:
```bash
ls /dev/spi*
```

2. Check wiring if using jumper wires
3. Try forcing display type:
```yaml
display:
  type: "v3"  # or "v4"
```

### Display Shows Garbage

1. Wrong display version configured
2. Try the other version type
3. Check for loose connections

### "Permission denied" for SPI

```bash
# Add user to spi and gpio groups
sudo usermod -aG spi,gpio $USER

# Reboot
sudo reboot
```

### Display Ghosting (V3)

Ghosting is normal for e-ink. Reduce by:
1. Occasional full refresh (every 10 partial refreshes)
2. Inkling handles this automatically

### Slow Performance on Pi Zero

The Pi Zero 2W is sufficient but not fast. Tips:
1. Use Haiku model (fastest responses)
2. Keep conversation history short
3. Disable unused heartbeat behaviors

## Auto-Start on Boot

### Using systemd

```bash
sudo nano /etc/systemd/system/inkling.service
```

```ini
[Unit]
Description=Inkling AI Companion
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/inkling-bot
Environment="PATH=/home/pi/inkling-bot/.venv/bin"
EnvironmentFile=/home/pi/inkling-bot/.env
ExecStart=/home/pi/inkling-bot/.venv/bin/python main.py --mode web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable inkling
sudo systemctl start inkling
```

Check status:
```bash
sudo systemctl status inkling
journalctl -u inkling -f  # View logs
```

## Thermal Management

The Pi Zero 2W can get warm during AI calls. Consider:

1. **Heatsink**: Small aluminum heatsink on CPU
2. **Ventilated case**: Ensure airflow
3. **Throttling**: Pi auto-throttles at 80°C

Monitor temperature:
```bash
# In Inkling
/system

# Or via command line
vcgencmd measure_temp
```

## Next Steps

- [Build an Enclosure](../hardware/enclosures.md)
- [Add Battery Power](../hardware/battery-portable.md)
- [Configure Personality](../configuration/personality-tuning.md)
- [Set Up Task Management](../features/task-management.md)
