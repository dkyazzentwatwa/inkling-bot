#!/usr/bin/env python3
"""Test screensaver page cycling."""

import asyncio
import time
from core.display import DisplayManager

async def test_screensaver_cycling():
    """Test that screensaver cycles through all pages."""

    # Create display manager
    display = DisplayManager(
        display_type="mock",
        width=250,
        height=122,
        min_refresh_interval=0.5,
        device_name="TestInkling",
    )

    # Configure screensaver with SHORT duration for testing
    display.configure_screensaver(
        enabled=True,
        idle_minutes=0.1,  # Very short idle time
        page_duration=2.0,  # 2 seconds per page (short for testing)
        pages=[
            {"type": "stats"},
            {"type": "quote"},
            {"type": "faces"},
            {"type": "progression"},
        ]
    )

    print("Starting screensaver test...")
    print("Expected behavior: Cycle through 4 pages, 2 seconds each")
    print("="*60)

    # Start screensaver
    await display.start_screensaver()

    # Let it run for 12 seconds (enough for 1.5 full cycles through 4 pages)
    print("\nWatching screensaver for 12 seconds...")
    await asyncio.sleep(12)

    # Stop screensaver
    print("\nStopping screensaver...")
    await display.stop_screensaver()

    print("\n" + "="*60)
    print("✓ Test complete!")
    print("Check the logs above - you should see all 4 page types displayed multiple times")

if __name__ == "__main__":
    asyncio.run(test_screensaver_cycling())
