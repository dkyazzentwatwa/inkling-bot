#!/usr/bin/env python3
"""
Test script for screen saver and dark mode features.

Usage:
    python test_screensaver.py
"""

import asyncio
import time
from core.display import DisplayManager
from core.personality import Personality

async def test_dark_mode():
    """Test dark mode functionality."""
    print("\n=== Testing Dark Mode ===")

    # Create display with dark mode OFF
    personality = Personality.load()
    display = DisplayManager(
        display_type="mock",
        width=250,
        height=122,
        device_name="test",
        personality=personality,
        dark_mode=False,
    )
    display.init()

    # Show normal mode
    print("\n1. Normal mode (black-on-white):")
    await display.update(face="happy", text="Normal mode test", force=True)
    await asyncio.sleep(2)

    # Enable dark mode
    print("\n2. Enabling dark mode (white-on-black):")
    display._dark_mode = True
    await display.update(face="happy", text="Dark mode test", force=True)
    await asyncio.sleep(2)

    # Disable dark mode
    print("\n3. Disabling dark mode:")
    display._dark_mode = False
    await display.update(face="happy", text="Back to normal", force=True)
    await asyncio.sleep(2)

    print("\n✓ Dark mode test completed")

async def test_screensaver():
    """Test screen saver functionality."""
    print("\n=== Testing Screen Saver ===")

    # Create display with screen saver configured
    personality = Personality.load()
    personality._last_interaction = time.time() - 400  # Simulate 6+ minutes idle

    display = DisplayManager(
        display_type="mock",
        width=250,
        height=122,
        device_name="test",
        personality=personality,
        dark_mode=False,
    )
    display.init()

    # Configure screen saver
    display.configure_screensaver(
        enabled=True,
        idle_minutes=5.0,
        page_duration=3.0,  # 3 seconds per page for testing
        pages=[
            {"type": "stats"},
            {"type": "quote"},
            {"type": "faces"},
            {"type": "progression"},
        ]
    )

    print("\n1. Checking if screen saver should activate:")
    should_activate = display.should_activate_screensaver()
    print(f"   Should activate: {should_activate}")

    if should_activate:
        print("\n2. Starting screen saver (will cycle for 15 seconds):")
        await display.start_screensaver()

        # Let it run for 15 seconds (will cycle through ~5 pages)
        await asyncio.sleep(15)

        print("\n3. Stopping screen saver:")
        await display.stop_screensaver()

        print("\n4. Simulating user interaction (should not re-activate):")
        personality._last_interaction = time.time()  # Reset to now
        should_activate_again = display.should_activate_screensaver()
        print(f"   Should activate: {should_activate_again} (should be False)")

    print("\n✓ Screen saver test completed")

async def test_screensaver_commands():
    """Test screen saver command toggles."""
    print("\n=== Testing Screen Saver Commands ===")

    personality = Personality.load()
    display = DisplayManager(
        display_type="mock",
        width=250,
        height=122,
        device_name="test",
        personality=personality,
    )
    display.init()

    # Test enable
    print("\n1. Enable screen saver:")
    display.configure_screensaver(enabled=True)
    print(f"   Enabled: {display._screensaver_enabled}")

    # Test disable
    print("\n2. Disable screen saver:")
    display.configure_screensaver(enabled=False)
    print(f"   Enabled: {display._screensaver_enabled}")

    # Test toggle
    print("\n3. Toggle screen saver:")
    current = display._screensaver_enabled
    display.configure_screensaver(enabled=not current)
    print(f"   Enabled: {display._screensaver_enabled}")

    print("\n✓ Command test completed")

async def main():
    """Run all tests."""
    print("Starting screen saver and dark mode tests...\n")

    try:
        await test_dark_mode()
        await test_screensaver()
        await test_screensaver_commands()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
