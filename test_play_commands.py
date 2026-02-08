#!/usr/bin/env python3
"""
Test play commands implementation.

This test verifies that:
1. Play XP sources are defined correctly
2. Play commands are registered
3. Energy calculation works as expected
"""

import sys
from core.progression import XPSource, XPTracker
from core.commands import get_command
from core.personality import Personality, Mood, PersonalityTraits


def test_xp_sources():
    """Test that all play XP sources are defined."""
    print("Testing XP sources...")

    play_sources = [
        XPSource.PLAY_WALK,
        XPSource.PLAY_DANCE,
        XPSource.PLAY_EXERCISE,
        XPSource.PLAY_GENERAL,
        XPSource.PLAY_REST,
        XPSource.PLAY_PET,
    ]

    for source in play_sources:
        assert source in XPSource, f"Missing XP source: {source}"
        print(f"  ✓ {source.value}")

    print("  All play XP sources defined!\n")


def test_commands_registered():
    """Test that all play commands are registered."""
    print("Testing command registration...")

    commands = [
        "walk",
        "dance",
        "exercise",
        "play",
        "pet",
        "rest",
    ]

    for cmd_name in commands:
        cmd = get_command(cmd_name)
        assert cmd is not None, f"Command not found: {cmd_name}"
        assert cmd.category == "play", f"Wrong category for {cmd_name}: {cmd.category}"
        print(f"  ✓ /{cmd_name} - {cmd.description}")

    print("  All play commands registered!\n")


def test_energy_calculation():
    """Test energy calculation from mood and intensity."""
    print("Testing energy calculation...")

    # Create a personality
    traits = PersonalityTraits(
        curiosity=0.7,
        cheerfulness=0.6,
        verbosity=0.5,
        playfulness=0.6,
        empathy=0.7,
        independence=0.4,
    )
    personality = Personality(name="TestInkling", traits=traits)

    # Test different moods
    test_cases = [
        (Mood.SLEEPY, 0.5, 0.05, "Low energy when sleepy"),
        (Mood.EXCITED, 0.9, 0.81, "High energy when excited"),
        (Mood.HAPPY, 0.7, 0.49, "Medium energy when happy"),
        (Mood.BORED, 0.3, 0.09, "Low energy when bored"),
    ]

    for mood, intensity, expected_energy, description in test_cases:
        personality.mood.set_mood(mood, intensity)
        energy = personality.energy

        # Allow for small floating point differences
        assert abs(energy - expected_energy) < 0.01, \
            f"{description}: expected {expected_energy}, got {energy}"

        print(f"  ✓ {description}: {energy:.0%}")

    print("  Energy calculation working!\n")


def test_xp_awards():
    """Test that XP can be awarded for play actions."""
    print("Testing XP awards...")

    tracker = XPTracker()
    initial_xp = tracker.xp

    # Award XP for a walk
    awarded, amount = tracker.award_xp(XPSource.PLAY_WALK, 3)
    assert awarded, "XP should be awarded"
    assert amount == 3, f"Expected 3 XP, got {amount}"
    assert tracker.xp == initial_xp + 3, "XP not added correctly"

    print(f"  ✓ Awarded {amount} XP for walk (total: {tracker.xp})")

    # Award XP for dance
    awarded, amount = tracker.award_xp(XPSource.PLAY_DANCE, 5)
    assert awarded, "XP should be awarded"
    assert amount == 5, f"Expected 5 XP, got {amount}"

    print(f"  ✓ Awarded {amount} XP for dance (total: {tracker.xp})")
    print("  XP awards working!\n")


def test_mood_effects():
    """Test that play actions boost mood and energy."""
    print("Testing mood effects...")

    personality = Personality(name="TestInkling")

    # Set initial low energy state
    personality.mood.set_mood(Mood.BORED, 0.3)
    initial_energy = personality.energy
    print(f"  Initial energy (bored): {initial_energy:.0%}")

    # Simulate a walk (curious mood, 0.7 intensity)
    personality.mood.set_mood(Mood.CURIOUS, 0.7)
    new_energy = personality.energy
    energy_boost = new_energy - initial_energy

    assert new_energy > initial_energy, "Energy should increase after walk"
    print(f"  After walk (curious): {new_energy:.0%} ({energy_boost:+.0%})")

    # Simulate dance (excited mood, 0.9 intensity)
    personality.mood.set_mood(Mood.EXCITED, 0.9)
    dance_energy = personality.energy

    assert dance_energy > new_energy, "Energy should increase further after dance"
    print(f"  After dance (excited): {dance_energy:.0%} ({dance_energy - new_energy:+.0%})")
    print("  Mood effects working!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Play Commands Test Suite")
    print("=" * 50)
    print()

    try:
        test_xp_sources()
        test_commands_registered()
        test_energy_calculation()
        test_xp_awards()
        test_mood_effects()

        print("=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
