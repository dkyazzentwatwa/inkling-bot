#!/usr/bin/env python3
"""Test battery display in header with correct format."""

import sys
from PIL import Image
from core.ui import PwnagotchiUI, DisplayContext, Fonts

def test_battery_in_header():
    """Test battery display with BAT%92 format."""

    # Create UI
    ui = PwnagotchiUI()

    # Test cases with different battery states
    test_cases = [
        {"name": "Battery 92% (not charging)", "battery": 92, "charging": False},
        {"name": "Battery 45% (charging)", "battery": 45, "charging": True},
        {"name": "Battery 15% (low)", "battery": 15, "charging": False},
        {"name": "No battery", "battery": -1, "charging": False},
    ]

    for i, test in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {test['name']}")
        print('='*60)

        ctx = DisplayContext(
            name="Inkling",
            mood_text="Happy",
            uptime="02:15:30",
            face_str="(^_^)",
            prefer_ascii=True,
            memory_percent=54,
            cpu_percent=1,
            temperature=43,
            battery_percentage=test['battery'],
            is_charging=test['charging'],
            clock_time="14:23",
            wifi_ssid="MyWiFi" if i % 2 == 0 else None,  # Alternate WiFi on/off
            wifi_signal=75 if i % 2 == 0 else 0,
            dream_count=0,
            telegram_count=0,
            chat_count=3,
            friend_nearby=False,
            level=1,
            level_name="Newborn",
            xp_progress=0.54,
            prestige=0,
            message="Testing battery display format!",
            mode="SSH",
        )

        # Render
        image = ui.render(ctx)

        # Show ASCII art of top line
        print("\nExpected header format:")
        if test['battery'] != -1:
            battery_text = f"CHG%{test['battery']}" if test['charging'] else f"BAT%{test['battery']}"
            wifi_text = "▂▄▆ " if i % 2 == 0 else ""
            print(f"Inkling> Happy  {wifi_text}{battery_text} UP 02:15:30")
        else:
            wifi_text = "▂▄▆ " if i % 2 == 0 else ""
            print(f"Inkling> Happy  {wifi_text}UP 02:15:30")

        # Save image
        filename = f"/tmp/battery_test_{i+1}.png"
        image.save(filename)
        print(f"Saved: {filename}")

if __name__ == "__main__":
    test_battery_in_header()
    print("\n✓ Battery format test complete!")
    print("  Format should be: BAT%92 (not BAT92%)")
