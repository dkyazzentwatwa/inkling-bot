"""
Tests for the progression system.
"""

import pytest
from core.progression import (
    XPTracker,
    XPSource,
    LevelCalculator,
    ChatQuality,
    XPRateLimiter,
)


def test_level_calculator():
    """Test XP-to-level calculations."""
    # Level 1 starts at 0 XP
    assert LevelCalculator.xp_for_level(1) == 0

    # Level 2 requires 100 XP
    assert LevelCalculator.xp_for_level(2) == 100

    # Test level from XP
    assert LevelCalculator.level_from_xp(0) == 1
    assert LevelCalculator.level_from_xp(50) == 1
    assert LevelCalculator.level_from_xp(100) == 2
    assert LevelCalculator.level_from_xp(5000) == 10

    # Test XP to next level
    assert LevelCalculator.xp_to_next_level(0) == 100
    assert LevelCalculator.xp_to_next_level(50) == 50
    assert LevelCalculator.xp_to_next_level(100) == LevelCalculator.xp_for_level(3) - 100

    # Test progress percentage
    assert LevelCalculator.progress_to_next_level(0) == 0.0
    assert LevelCalculator.progress_to_next_level(50) == 0.5
    assert LevelCalculator.progress_to_next_level(100) == 0.0

    # Test max level (25)
    max_xp = LevelCalculator.xp_for_level(25)
    assert LevelCalculator.level_from_xp(max_xp) == 25
    assert LevelCalculator.xp_to_next_level(max_xp) == 0
    assert LevelCalculator.progress_to_next_level(max_xp) == 1.0


def test_level_names():
    """Test level tier names."""
    assert LevelCalculator.level_name(1) == "Newborn Inkling"
    assert LevelCalculator.level_name(2) == "Newborn Inkling"
    assert LevelCalculator.level_name(3) == "Curious Inkling"
    assert LevelCalculator.level_name(10) == "Chatty Inkling"
    assert LevelCalculator.level_name(15) == "Wise Inkling"
    assert LevelCalculator.level_name(20) == "Sage Inkling"
    assert LevelCalculator.level_name(25) == "Legendary Inkling"


def test_chat_quality_xp():
    """Test XP calculation from chat quality."""
    # Greeting (short, no question)
    quality = ChatQuality(
        message_length=10,
        turn_count=1,
        is_question=False,
        sentiment="neutral"
    )
    source, xp = quality.calculate_xp()
    assert source == XPSource.GREETING
    assert xp == 2

    # Quick chat (normal)
    quality = ChatQuality(
        message_length=30,
        turn_count=1,
        is_question=True,
        sentiment="neutral"
    )
    source, xp = quality.calculate_xp()
    assert source == XPSource.QUICK_CHAT
    assert xp == 5

    # Deep chat (multi-turn, long)
    quality = ChatQuality(
        message_length=100,
        turn_count=5,
        is_question=True,
        sentiment="positive"
    )
    source, xp = quality.calculate_xp()
    assert source == XPSource.DEEP_CHAT
    assert xp == 15


def test_xp_tracker_basic():
    """Test basic XP tracking."""
    tracker = XPTracker()

    # Start at level 1
    assert tracker.level == 1
    assert tracker.xp == 0

    # Award some XP
    awarded, amount = tracker.award_xp(XPSource.QUICK_CHAT, 5)
    assert awarded is True
    assert amount == 5
    assert tracker.xp == 5

    # Still level 1
    assert tracker.level == 1


def test_xp_tracker_level_up():
    """Test leveling up."""
    tracker = XPTracker()

    # Award enough XP to reach level 2
    awarded, amount = tracker.award_xp(XPSource.DEEP_CHAT, 100)
    assert awarded is True
    assert tracker.xp == 100
    assert tracker.level == 2


def test_xp_rate_limiter():
    """Test XP rate limiting."""
    limiter = XPRateLimiter(max_xp_per_hour=100)

    # First award should work
    can_award, amount = limiter.can_award_xp(XPSource.QUICK_CHAT, 5)
    assert can_award is True
    assert amount == 5

    limiter.record_xp(XPSource.QUICK_CHAT, 5)

    # Award up to the limit
    for _ in range(18):  # 18 * 5 = 90, total 95
        can_award, amount = limiter.can_award_xp(XPSource.QUICK_CHAT, 5)
        if can_award:
            limiter.record_xp(XPSource.QUICK_CHAT, amount)

    # Should be near/at limit
    can_award, amount = limiter.can_award_xp(XPSource.QUICK_CHAT, 10)
    assert amount <= 5  # Capped by remaining budget


def test_xp_tracker_prestige():
    """Test prestige system."""
    tracker = XPTracker()

    # Can't prestige at level 1
    assert tracker.can_prestige() is False

    # Level up to 25
    tracker.xp = LevelCalculator.xp_for_level(25)
    tracker.level = 25

    # Now can prestige
    assert tracker.can_prestige() is True

    # Do prestige
    assert tracker.do_prestige() is True
    assert tracker.level == 1
    assert tracker.xp == 0
    assert tracker.prestige == 1
    assert "prestige_1" in tracker.badges

    # XP multiplier should be 2x
    assert tracker._xp_multiplier == 2.0

    # Award XP should be doubled
    awarded, amount = tracker.award_xp(XPSource.QUICK_CHAT, 5)
    assert amount == 10  # 5 * 2x


def test_achievement_unlock():
    """Test achievement unlocking."""
    tracker = XPTracker()

    # Start with no badges
    assert len(tracker.badges) == 0

    # Unlock first dream achievement
    xp_reward = tracker.unlock_achievement("first_dream")
    assert xp_reward == 50
    assert "first_dream" in tracker.badges
    assert tracker.achievements["first_dream"].unlocked is True

    # Should have gained XP
    assert tracker.xp == 50

    # Re-unlocking should do nothing
    xp_reward = tracker.unlock_achievement("first_dream")
    assert xp_reward == 0
    assert tracker.xp == 50


def test_streak_tracking():
    """Test daily streak tracking."""
    tracker = XPTracker()

    # First day
    is_first = tracker.update_streak()
    assert is_first is True
    assert tracker.current_streak == 1

    # Same day again
    is_first = tracker.update_streak()
    assert is_first is False
    assert tracker.current_streak == 1


def test_display_level():
    """Test display level formatting."""
    tracker = XPTracker()

    # No prestige
    assert tracker.get_display_level() == "L1"

    # With prestige
    tracker.prestige = 2
    assert "⭐" in tracker.get_display_level()
    assert tracker.get_display_level().startswith("L1")


def test_xp_tracker_serialization():
    """Test saving and loading progression."""
    tracker = XPTracker()

    # Award some XP and unlock achievement
    tracker.award_xp(XPSource.DEEP_CHAT, 100)
    tracker.unlock_achievement("first_dream")

    # Serialize
    data = tracker.to_dict()

    # Deserialize
    new_tracker = XPTracker.from_dict(data)

    assert new_tracker.xp == tracker.xp
    assert new_tracker.level == tracker.level
    assert new_tracker.badges == tracker.badges
    assert new_tracker.achievements["first_dream"].unlocked is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
