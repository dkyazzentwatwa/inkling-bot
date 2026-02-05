# BLE Terminal (iPhone + Pi)

This guide enables a BLE command terminal that accepts the same slash-commands as SSH mode.

## Requirements

```bash
sudo apt update
sudo apt install -y bluez python3-bluezero
```

## Enable BLE in config

Edit `config.local.yml`:

```yaml
ble:
  enabled: true
  device_name: "Inkling BLE"
  allow_bash: true
  command_timeout_seconds: 8
  max_output_bytes: 8192
```

Restart Inkling after saving.

## Bluetooth pairing (one-time)

```bash
bluetoothctl
power on
agent on
default-agent
discoverable on
pairable on
```

On iPhone, open a BLE terminal app (LightBlue, BLE Terminal, Bluefruit Connect),
find the device name, and pair/connect.

## Usage

In your BLE terminal app:

- Subscribe to TX notifications
- Send commands to RX (each command must end with a newline)

Examples:

```
/help
/tasks
/task buy milk
/done 1
/bash uptime
```

## Notes

- BLE runs inside the Inkling process, so it shares state with SSH/Web.
- `/bash` is disabled in the web UI but allowed in SSH and BLE (if enabled).
