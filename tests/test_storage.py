#!/usr/bin/env python3
"""
Test script for storage detection functionality.
"""

from core.storage import (
    get_sd_card_path,
    is_storage_available,
    get_storage_info,
    list_mounted_storage
)

def test_storage_detection():
    """Test storage detection functions."""
    print("=== Storage Detection Test ===\n")

    # Test SD card detection
    print("1. Testing SD card auto-detection:")
    sd_path = get_sd_card_path()
    if sd_path:
        print(f"   ✓ SD card found at: {sd_path}")
    else:
        print("   ✗ No SD card detected (this is expected on non-Pi systems)")

    # Test storage availability check for common paths
    print("\n2. Testing storage availability:")
    test_paths = [
        "/tmp",  # Should always be available
        "/nonexistent/path",  # Should not be available
    ]

    for path in test_paths:
        available = is_storage_available(path)
        status = "✓" if available else "✗"
        print(f"   {status} {path}: {'available' if available else 'not available'}")

    # Test storage info
    print("\n3. Testing storage info (for /tmp):")
    info = get_storage_info("/tmp")
    if info:
        print(f"   Total: {info['total_gb']} GB")
        print(f"   Used: {info['used_gb']} GB ({info['percent_used']}%)")
        print(f"   Free: {info['free_gb']} GB")
    else:
        print("   ✗ Could not get storage info")

    # Test mounted storage listing
    print("\n4. Testing mounted storage listing:")
    devices = list_mounted_storage()
    if devices:
        print(f"   Found {len(devices)} mounted storage device(s):")
        for dev in devices:
            print(f"   - {dev['device']}: {dev['mount_point']} ({dev['size']})")
    else:
        print("   ✗ No mounted storage found (may require 'lsblk' command)")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_storage_detection()
