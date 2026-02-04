# Battery & Portable Setup Guide

Make Inkling mobile with battery power, solar charging, and low-power optimizations.

## Overview

A portable Inkling setup needs:
- **Battery**: LiPo or USB power bank
- **Charging circuit**: Safe charging while running
- **Power management**: Clean shutdown, low battery warning
- **Optimization**: Maximize battery life

## Battery Options

### Option 1: USB Power Bank (Easiest)

**Pros:**
- No soldering required
- Built-in protection circuits
- Easy to replace/upgrade
- Pass-through charging

**Cons:**
- Bulky
- May auto-shutoff on low current
- No integrated form factor

**Recommended:**
- 5000mAh power bank (~10+ hours)
- With pass-through charging
- Compact form factor

**Setup:**
1. Connect power bank to Pi via USB
2. That's it!

**Battery Life:**
```
5000mAh @ 5V = 25Wh
Pi Zero 2W idle: ~0.5W
Pi Zero 2W AI call: ~1.5W
Average: ~0.8W

Estimated: 25Wh / 0.8W ≈ 30 hours idle
                       ≈ 15 hours with usage
```

### Option 2: LiPo Battery + SHIM (Recommended)

**Hardware:**
- Pimoroni LiPo SHIM (or Adafruit PowerBoost)
- 3.7V LiPo battery (1000-3000mAh)
- JST connector

**Pros:**
- Compact, integrated solution
- Clean power management
- Low battery detection
- Proper charging circuit

**Cons:**
- Requires soldering (SHIM to Pi)
- More expensive
- Need to handle LiPo safely

**Wiring (Pimoroni LiPo SHIM):**

```
LiPo Battery → [SHIM] → Pi Zero GPIO
     3.7V    →  5V out → 5V (Pin 2)
     GND     →  GND    → GND (Pin 6)
             →  BAT    → GPIO 4 (low battery signal)
```

### Option 3: PiSugar (Premium)

**Hardware:**
- PiSugar S or PiSugar 2
- Included 1200mAh battery

**Pros:**
- Designed for Pi Zero
- Integrated RTC (real-time clock)
- Software support for shutdown
- Web interface for monitoring
- Wireless charging option

**Cons:**
- Most expensive option (~$30-40)
- Adds thickness to build

**Setup:**
1. Attach PiSugar to Pi (pogo pins or solder)
2. Install software:
   ```bash
   curl http://cdn.pisugar.com/release/pisugar-power-manager.sh | sudo bash
   ```
3. Access web interface at port 8421

## Battery Sizing

### Power Consumption

| State | Current (5V) | Power |
|-------|--------------|-------|
| Idle (display off) | 100mA | 0.5W |
| Idle (display on) | 120mA | 0.6W |
| AI call (active) | 300mA | 1.5W |
| Display refresh | 200mA | 1.0W |

### Battery Life Estimates

| Battery | Idle | Light Use | Heavy Use |
|---------|------|-----------|-----------|
| 1000mAh | 8h | 5h | 3h |
| 2000mAh | 16h | 10h | 6h |
| 3000mAh | 24h | 15h | 9h |
| 5000mAh | 40h | 25h | 15h |

*Light use: occasional interactions
Heavy use: frequent AI calls*

## Charging Solutions

### USB Charging

Most battery solutions charge via USB:
- Connect USB power source
- Battery charges while running
- Remove USB for portable mode

### Solar Charging

For outdoor or window placement:

**Components:**
- 5V solar panel (5-10W)
- Solar charge controller (optional, some SHIMs include)
- 3.7V LiPo battery

**Setup:**
```
Solar Panel → Charge Controller → LiPo → Pi
    5V     →    3.7V charge    →  5V  → USB
```

**Recommended panels:**
- 5W panel (150x150mm): ~500mA output
- 10W panel (200x200mm): ~1A output

**Notes:**
- Solar alone may not power Pi directly
- Use as trickle charger to extend battery
- Indoor window placement works with larger panels

## Power Management

### Low Battery Detection

**With LiPo SHIM:**

```python
# Check battery status
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN)  # BAT pin

def check_battery():
    if GPIO.input(4) == 0:
        print("Low battery!")
        return False
    return True
```

**With PiSugar:**

```python
import requests

def get_battery():
    r = requests.get('http://localhost:8421/api/battery')
    data = r.json()
    return data['battery']  # Percentage
```

### Safe Shutdown

When battery is low, shutdown cleanly:

```python
import os

def low_battery_shutdown():
    print("Battery critical - shutting down...")
    os.system("sudo shutdown -h now")
```

### Power Saving Tips

1. **Reduce display refreshes**
   ```yaml
   display:
     min_refresh_interval: 10.0  # Longer delay
   ```

2. **Lower tick frequency**
   ```yaml
   heartbeat:
     tick_interval: 120  # Every 2 minutes
   ```

3. **Disable WiFi when not needed**
   ```bash
   sudo rfkill block wifi
   ```

4. **Reduce AI calls**
   ```yaml
   ai:
     budget:
       daily_tokens: 5000  # Lower limit
   ```

5. **Use sleep mode during quiet hours**
   ```yaml
   heartbeat:
     quiet_hours_start: 22
     quiet_hours_end: 8
   ```

## Portable Build Guide

### Parts List

| Component | Example | Price |
|-----------|---------|-------|
| Pi Zero 2W | Raspberry Pi | $15 |
| E-Ink HAT | Waveshare 2.13" V3 | $20 |
| LiPo SHIM | Pimoroni | $12 |
| LiPo Battery | 2000mAh 3.7V | $10 |
| Case | 3D printed | $5 |
| **Total** | | **~$62** |

### Assembly Steps

1. **Solder LiPo SHIM to Pi**
   - Solder header pins to SHIM
   - Attach to Pi GPIO

2. **Connect battery**
   - Plug JST connector into SHIM
   - Battery immediately powers Pi

3. **Stack display HAT**
   - Align with remaining GPIO pins
   - Press firmly to seat

4. **Install in case**
   - Position battery in case
   - Secure Pi with standoffs or tape
   - Route USB port to case opening

5. **Configure software**
   - Enable low battery detection
   - Configure quiet hours
   - Optimize refresh rates

### Wiring Diagram

```
                   ┌─────────────────┐
                   │   E-Ink HAT     │
                   │  (on top)       │
                   └────────┬────────┘
                            │ GPIO
┌─────────────┐    ┌────────┴────────┐
│  LiPo       │    │   Pi Zero 2W    │
│  Battery    │────│                 │
│  3.7V       │    │  LiPo SHIM      │
│  2000mAh    │    │  (underneath)   │
└─────────────┘    └─────────────────┘
                            │ USB
                   ┌────────┴────────┐
                   │  Charging Port  │
                   └─────────────────┘
```

## Case Considerations

### Battery Compartment

- Size for your chosen battery
- Leave room for JST connector
- Include charging port access

### Ventilation

Battery + Pi generates heat:
- Add ventilation holes
- Don't fully enclose battery
- Monitor temperature

### Mounting

Options for portable use:
- Belt clip
- Lanyard hole
- Magnetic back

## Status Monitoring

### Battery Widget

Add battery status to display:

```python
def get_battery_status():
    # Read from SHIM or PiSugar
    level = read_battery_level()  # 0-100

    if level > 75:
        return "█████"
    elif level > 50:
        return "████░"
    elif level > 25:
        return "███░░"
    elif level > 10:
        return "██░░░"
    else:
        return "█░░░░"
```

### Low Battery Face

Show warning face when low:

```python
if battery_level < 20:
    face = "(@_@)⚡"  # Low battery face
```

## Troubleshooting

### Pi Won't Boot on Battery

1. Check battery is charged
2. Verify SHIM connections
3. Test with multimeter (should read 5V at GPIO)
4. Try different battery

### Battery Drains Quickly

1. Check for shorts
2. Reduce display refreshes
3. Disable unused features
4. Check WiFi usage

### Charging Not Working

1. Verify USB cable (data cables may not carry enough current)
2. Check charge LED on SHIM
3. Try different power source
4. Inspect battery connector

### Pi Shuts Down Randomly

1. Battery may be near empty
2. Check voltage with multimeter
3. Enable low battery warnings
4. Use larger battery

## Safety Notes

### LiPo Battery Safety

- Never puncture or crush
- Don't expose to extreme heat
- Use proper charging circuit (never direct voltage)
- Store at ~50% charge if not using
- Replace if swollen or damaged

### Charging Best Practices

- Use quality charger/SHIM
- Don't leave charging unattended overnight initially
- Charge at room temperature
- Disconnect when not needed long-term

## Next Steps

- [Build an Enclosure](enclosures.md)
- [Display Options](display-options.md)
- [Autonomous Behaviors](../features/autonomous-behaviors.md) for power-aware scheduling
