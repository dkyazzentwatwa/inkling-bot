"""
Storage location detection and management.

Provides utilities for detecting and accessing multiple storage locations,
particularly SD cards on Raspberry Pi.
"""

import os
import subprocess
from typing import Optional, List


def get_sd_card_path() -> Optional[str]:
    """
    Auto-detect SD card mount point on Raspberry Pi.

    Searches common mount locations for removable media:
    - /media/pi/* (auto-mounted USB/SD)
    - /mnt/* (manual mounts)

    Returns:
        Path to first detected SD card mount point, or None if not found
    """
    # Check /media/pi/* first (most common auto-mount location)
    media_dir = "/media/pi"
    if os.path.exists(media_dir):
        for entry in os.listdir(media_dir):
            path = os.path.join(media_dir, entry)
            if os.path.isdir(path) and is_storage_available(path):
                return path

    # Check /mnt/* for manual mounts
    mnt_dir = "/mnt"
    if os.path.exists(mnt_dir):
        for entry in os.listdir(mnt_dir):
            path = os.path.join(mnt_dir, entry)
            if os.path.isdir(path) and is_storage_available(path):
                return path

    return None


def is_storage_available(path: str) -> bool:
    """
    Check if storage path exists and is writable.

    Args:
        path: Directory path to check

    Returns:
        True if path exists and is writable
    """
    if not os.path.exists(path):
        return False

    if not os.path.isdir(path):
        return False

    # Check write permissions
    return os.access(path, os.W_OK)


def get_storage_info(path: str) -> dict:
    """
    Get storage information (size, free space) for a path.

    Args:
        path: Directory path to check

    Returns:
        Dict with keys: total, used, free (in bytes), or empty dict on error
    """
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free

        return {
            "total": total,
            "used": used,
            "free": free,
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "percent_used": round((used / total) * 100, 1) if total > 0 else 0
        }
    except Exception:
        return {}


def list_mounted_storage() -> List[dict]:
    """
    List all mounted storage devices.

    Returns:
        List of dicts with keys: device, mount_point, filesystem, size
    """
    devices = []

    try:
        # Use lsblk to get block device info
        result = subprocess.run(
            ["lsblk", "-o", "NAME,MOUNTPOINT,SIZE,FSTYPE", "-n"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "":  # Has mount point
                    mount_point = parts[1]
                    # Filter to user-accessible locations
                    if mount_point.startswith(("/media/", "/mnt/")):
                        devices.append({
                            "device": parts[0],
                            "mount_point": mount_point,
                            "size": parts[2] if len(parts) > 2 else "?",
                            "filesystem": parts[3] if len(parts) > 3 else "?"
                        })
    except Exception:
        pass

    return devices
