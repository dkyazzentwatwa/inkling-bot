# Enclosures Guide

Protect and display your Inkling with custom cases, from 3D printed designs to simple DIY options.

## Overview

A good enclosure:
- Protects the Pi and display
- Allows viewing the e-ink screen
- Provides access to ports (USB, power)
- Optionally houses a battery
- Looks cool on your desk!

## Design Considerations

### Display Orientation

The Waveshare 2.13" display is 250x122 pixels (landscape):

```
┌─────────────────────────────────────┐
│     122px                           │
│  ┌─────────────────────────────┐    │
│  │                             │    │ 250px
│  │      E-Ink Display          │    │
│  │                             │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### Pi Zero 2W Dimensions

```
┌────────────────────────────────────────┐
│  65mm x 30mm x 5mm                     │
│  ┌──────────────────────────────────┐  │
│  │ ○  USB  HDMI  USB  SD           │  │
│  │    PWR  mini  data  slot        │  │
│  └──────────────────────────────────┘  │
│                                        │
│  GPIO Header (40 pins)                 │
└────────────────────────────────────────┘
```

### Ventilation

The Pi Zero 2W runs warm during AI calls:
- Include ventilation slots
- Leave gap around processor
- Optional: small heatsink

## 3D Printed Cases

### Minimal Desktop Stand

Simple stand that shows the display and hides the Pi:

```
Front View:          Side View:
┌─────────────┐     ┌─────┐
│ ┌─────────┐ │     │    /│
│ │ Display │ │     │   / │
│ └─────────┘ │     │  /  │
│             │     │ /   │
└─────────────┘     └─────┘
      Angled 15-20°
```

**Design features:**
- 15-20° viewing angle
- Open back for ventilation
- Slot for USB power cable
- Friction-fit display

### Pwnagotchi-Style Case

Inspired by the Pwnagotchi project:

```
┌───────────────────────────┐
│  ┌───────────────────┐   │
│  │                   │   │
│  │     E-Ink Face    │   │
│  │       (^_^)       │   │
│  └───────────────────┘   │
│                          │
│  ○ LED  ○ Button         │
└──────────────────────────┘
```

**Features:**
- Rounded corners
- Activity LED cutout
- Optional button for interactions
- Belt clip or lanyard hole

### Pocket-Size Portable

Minimal case for carrying around:

```
Top View:
┌────────────────────┐
│ ┌────────────────┐ │
│ │    Display     │ │
│ └────────────────┘ │
│   USB-C  Power    │
└────────────────────┘

Side View:
┌────────────────────┐
│░░░░░░░░░░░░░░░░░░░│ ~15mm thick
└────────────────────┘
```

**Features:**
- Thin profile
- Internal battery slot
- Rubber feet

## STL Files

### Community Designs

Search these resources for printable files:

| Source | Search Terms |
|--------|--------------|
| Thingiverse | "Pi Zero e-ink case", "Pwnagotchi" |
| Printables | "Waveshare 2.13 case" |
| Cults3D | "Raspberry Pi e-ink" |

### Design Your Own

Recommended software:
- **Fusion 360** (free for hobbyists)
- **FreeCAD** (open source)
- **TinkerCAD** (browser-based, beginner-friendly)

Key measurements:
```
Pi Zero 2W:
  65mm x 30mm x 5mm
  Mounting holes: 58mm x 23mm (M2.5)

Waveshare 2.13" HAT:
  65mm x 30mm x 12mm (stacked on Pi)
  Display active area: 48.55mm x 23.71mm
```

## Print Settings

### Recommended Settings

| Setting | Value |
|---------|-------|
| Layer Height | 0.2mm |
| Infill | 20-30% |
| Material | PLA or PETG |
| Supports | Usually not needed |
| Wall Thickness | 1.2-1.6mm |

### Material Comparison

| Material | Pros | Cons |
|----------|------|------|
| PLA | Easy to print, cheap | Low heat resistance |
| PETG | Durable, heat resistant | Strings more |
| ABS | Very durable | Requires enclosure, warps |
| TPU | Flexible, shock absorbing | Difficult to print |

**Recommendation:** PETG for durability, PLA for ease.

## DIY Enclosures

### Simple Cardboard Prototype

Quick prototype before printing:

1. Cut cardboard to Pi + HAT dimensions
2. Cut window for display
3. Fold into box shape
4. Tape together

Great for testing fit and angles!

### Wooden Case

For a more premium look:

**Materials:**
- 3mm plywood or MDF
- Wood glue
- Wood stain/paint

**Tools:**
- Laser cutter (ideal)
- Scroll saw
- Dremel

**Design:**
1. Cut top piece with display cutout
2. Cut sides and bottom
3. Assemble with glue
4. Add magnets for removable top

### Laser-Cut Acrylic

```
Layers (bottom to top):
1. Solid base (3mm)
2. Spacer with Pi cutout (3mm)
3. Spacer (3mm)
4. Top with display window (3mm)
```

**Materials:**
- 3mm acrylic (clear or colored)
- M2.5 standoffs and screws
- Rubber feet

## Assembly Tips

### Securing the Pi

Options:
1. **Friction fit**: Design case to hold Pi snugly
2. **Standoffs**: M2.5 screws into brass standoffs
3. **Mounting tape**: 3M VHB tape (removable)

### Display Window

Options:
1. **Open cutout**: Simple, allows touch if needed
2. **Acrylic cover**: Protects display, adds glare
3. **Recessed**: Display sits flush with case

### Cable Management

Consider:
- Power cable entry point
- Internal cable routing
- Strain relief for power cable

## Example Builds

### Desktop Companion

```
Components:
- Pi Zero 2W
- Waveshare 2.13" V3
- 3D printed case (angled)
- USB-C power

Cost: ~$50 total
Build time: 2-3 hours
```

### Portable Pwnagotchi

```
Components:
- Pi Zero 2W
- Waveshare 2.13" V3
- 3D printed case
- 3.7V 2000mAh LiPo
- Pimoroni LiPo SHIM

Cost: ~$70 total
Build time: 3-4 hours
Battery life: 4-6 hours
```

### Premium Wooden Stand

```
Components:
- Pi Zero 2W
- Waveshare 2.13" V4
- Laser-cut walnut case
- Brass accents
- Felt base

Cost: ~$100 total
Build time: 5+ hours
```

## Accessory Ideas

### LED Indicators

Add status LEDs:
- GPIO 26: Activity (AI processing)
- GPIO 19: Power status
- GPIO 13: Error indicator

### Physical Buttons

Add interaction buttons:
- GPIO 5: Mood button (cycle moods)
- GPIO 6: Command button (trigger action)
- GPIO 12: Sleep/wake toggle

### Sound

Add a small speaker:
- PWM audio through GPIO 18
- I2S audio with DAC board
- USB audio adapter

## Community Gallery

Share your builds!
- Post photos with #InklingBot
- Submit to project discussions
- Create build guides for others

## Troubleshooting

### Display Not Visible Through Window

- Window opening too small
- Acrylic too thick/tinted
- Try anti-glare acrylic

### Pi Overheating

- Add ventilation holes
- Include heatsink
- Increase case height for airflow

### Case Doesn't Fit

- Check printer calibration
- Adjust tolerance in design (0.2-0.4mm gap)
- File/sand tight spots

## Next Steps

- [Add Battery Power](battery-portable.md)
- [Hardware Assembly Guide](../getting-started/hardware-assembly.md)
- [Display Options](display-options.md)
