"""
Project Inkling - System Statistics

Provides system stats for the Pwnagotchi-style UI:
- Memory usage percentage
- CPU usage percentage
- CPU temperature
- System uptime

Works on Raspberry Pi and gracefully degrades on other systems.
"""

import os
import time
from datetime import datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - fallback for older Python
    ZoneInfo = None

from .battery import get_battery_info

# Track when the application started for uptime calculation
_start_time: float = time.time()


def get_memory_percent() -> int:
    """
    Get memory usage as a percentage (0-100).

    Returns:
        Memory usage percentage, or 0 if unavailable
    """
    # Try /proc/meminfo (Linux)
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    value = int(parts[1])
                    meminfo[key] = value

            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)

            if total > 0:
                used = total - available
                return int((used / total) * 100)
    except (FileNotFoundError, KeyError, ValueError, PermissionError):
        pass

    # Try psutil as fallback
    try:
        import psutil
        return int(psutil.virtual_memory().percent)
    except ImportError:
        pass

    return 0


def get_cpu_percent() -> int:
    """
    Get CPU usage as a percentage (0-100).

    Uses a simple calculation based on /proc/stat.
    Note: This is a snapshot, not an average over time.

    Returns:
        CPU usage percentage, or 0 if unavailable
    """
    # Try /proc/stat (Linux)
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
            if line.startswith("cpu "):
                parts = line.split()[1:]
                values = [int(x) for x in parts[:7]]
                # user, nice, system, idle, iowait, irq, softirq
                idle = values[3] + values[4]  # idle + iowait
                total = sum(values)

                # Store for next calculation with timestamp
                import time
                current_time = time.time()

                if not hasattr(get_cpu_percent, "_prev"):
                    get_cpu_percent._prev = (idle, total, current_time)
                    # Return a reasonable default on first call
                    return 10

                prev_idle, prev_total, prev_time = get_cpu_percent._prev
                time_delta = current_time - prev_time

                # Only calculate if enough time has passed (min 0.5 seconds)
                # This prevents incorrect readings from rapid successive calls
                if time_delta < 0.5:
                    # Return last calculated value if available
                    if hasattr(get_cpu_percent, "_last_value"):
                        return get_cpu_percent._last_value
                    return 10

                get_cpu_percent._prev = (idle, total, current_time)

                idle_delta = idle - prev_idle
                total_delta = total - prev_total

                if total_delta > 0:
                    cpu_percent = 100 * (1 - idle_delta / total_delta)
                    result = int(max(0, min(100, cpu_percent)))
                    get_cpu_percent._last_value = result
                    return result
    except (FileNotFoundError, ValueError, PermissionError):
        pass

    # Try psutil as fallback
    try:
        import psutil
        return int(psutil.cpu_percent(interval=None))
    except ImportError:
        pass

    return 0


def get_temperature() -> int:
    """
    Get CPU temperature in Celsius.

    Returns:
        Temperature in Celsius, or 0 if unavailable
    """
    # Try Raspberry Pi thermal zone
    thermal_paths = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
    ]

    for path in thermal_paths:
        try:
            with open(path, "r") as f:
                # Value is in millidegrees Celsius
                temp_milli = int(f.read().strip())
                return temp_milli // 1000
        except (FileNotFoundError, ValueError, PermissionError):
            continue

    # Try psutil as fallback (may not work everywhere)
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            # Try common sensor names
            for name in ["cpu_thermal", "coretemp", "cpu-thermal"]:
                if name in temps and temps[name]:
                    return int(temps[name][0].current)
            # Fall back to first available
            for sensors in temps.values():
                if sensors:
                    return int(sensors[0].current)
    except (ImportError, AttributeError):
        pass

    return 0


def get_uptime() -> str:
    """
    Get system uptime in HH:MM:SS format.

    This returns the application uptime, not system uptime,
    which is more relevant for the Inkling device.

    Returns:
        Uptime string in "HH:MM:SS" format
    """
    elapsed = time.time() - _start_time

    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_system_uptime() -> str:
    """
    Get actual system uptime (how long the device has been running).

    Returns:
        Uptime string in "HH:MM:SS" format, or "??:??:??" if unavailable
    """
    # Try /proc/uptime (Linux)
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except (FileNotFoundError, ValueError, PermissionError):
        pass

    # Fall back to application uptime
    return get_uptime()


def reset_uptime() -> None:
    """Reset the application uptime counter."""
    global _start_time
    _start_time = time.time()


def get_all_stats() -> dict:
    """
    Get all system stats in a single call.

    Returns:
        Dict with keys: memory, cpu, temperature, uptime, battery
    """
    stats = {
        "memory": get_memory_percent(),
        "cpu": get_cpu_percent(),
        "temperature": get_temperature(),
        "uptime": get_uptime(),
    }
    
    # Add battery if available
    battery = get_battery_info()
    if battery:
        stats["battery"] = battery
        
    return stats


def get_local_time(timezone: Optional[str] = None) -> str:
    """
    Get local time as HH:MM.

    Args:
        timezone: Optional IANA timezone (e.g., "America/Los_Angeles")

    Returns:
        Time string in "HH:MM" 24-hour format
    """
    if timezone and ZoneInfo:
        try:
            tz = ZoneInfo(timezone)
            return datetime.now(tz).strftime("%H:%M")
        except Exception:
            pass

    # Fall back to system local time
    return time.strftime("%H:%M")
