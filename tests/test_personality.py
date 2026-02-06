"""
Project Inkling - Personality Tests

Tests for core/personality.py - mood state machine and personality traits.
"""

import time
import pytest


class TestMood:
    """Tests for the Mood enum."""

    def test_mood_values(self):
        """Test that all moods have expected values."""
        from core.personality import Mood

        assert Mood.HAPPY.value == "happy"
        assert Mood.EXCITED.value == "excited"
        assert Mood.CURIOUS.value == "curious"
        assert Mood.BORED.value == "bored"
        assert Mood.SAD.value == "sad"
        assert Mood.SLEEPY.value == "sleepy"
        assert Mood.GRATEFUL.value == "grateful"
        assert Mood.LONELY.value == "lonely"
        assert Mood.INTENSE.value == "intense"
        assert Mood.COOL.value == "cool"

    def test_mood_face(self):
        """Test that moods have face expressions."""
        from core.personality import Mood

        assert Mood.HAPPY.face == "happy"
        assert Mood.SLEEPY.face == "sleep"  # Note: sleepy -> sleep

    def test_mood_energy(self):
        """Test that moods have energy levels."""
        from core.personality import Mood

        # High energy moods
        assert Mood.EXCITED.energy == 0.9
        assert Mood.INTENSE.energy == 0.85

        # Low energy moods
        assert Mood.SLEEPY.energy == 0.1
        assert Mood.SAD.energy == 0.2


class TestPersonalityTraits:
    """Tests for PersonalityTraits dataclass."""

    def test_default_traits(self):
        """Test default trait values."""
        from core.personality import PersonalityTraits

        traits = PersonalityTraits()

        assert traits.curiosity == 0.7
        assert traits.cheerfulness == 0.6
        assert traits.verbosity == 0.5
        assert traits.playfulness == 0.6
        assert traits.empathy == 0.7
        assert traits.independence == 0.4

    def test_traits_to_dict(self):
        """Test serialization of traits."""
        from core.personality import PersonalityTraits

        traits = PersonalityTraits(curiosity=0.9, cheerfulness=0.8)
        d = traits.to_dict()

        assert d["curiosity"] == 0.9
        assert d["cheerfulness"] == 0.8
        assert "verbosity" in d
        assert "playfulness" in d

    def test_traits_from_dict(self):
        """Test deserialization of traits."""
        from core.personality import PersonalityTraits

        data = {"curiosity": 0.5, "empathy": 0.9, "unknown_trait": 1.0}
        traits = PersonalityTraits.from_dict(data)

        assert traits.curiosity == 0.5
        assert traits.empathy == 0.9
        # Unknown trait should be ignored
        assert not hasattr(traits, "unknown_trait")


class TestMoodState:
    """Tests for MoodState dataclass."""

    def test_set_mood(self):
        """Test changing mood state."""
        from core.personality import MoodState, Mood

        state = MoodState()
        assert state.current == Mood.HAPPY

        state.set_mood(Mood.EXCITED, 0.8)
        assert state.current == Mood.EXCITED
        assert state.intensity == 0.8

    def test_mood_history(self):
        """Test that mood history is tracked."""
        from core.personality import MoodState, Mood

        state = MoodState()
        original_time = state.last_change

        state.set_mood(Mood.CURIOUS, 0.5)
        state.set_mood(Mood.EXCITED, 0.7)

        assert len(state.history) == 2
        assert state.history[0][0] == Mood.HAPPY
        assert state.history[1][0] == Mood.CURIOUS

    def test_mood_history_limit(self):
        """Test that mood history is limited to 20 entries."""
        from core.personality import MoodState, Mood

        state = MoodState()

        # Make 25 mood changes
        moods = [Mood.HAPPY, Mood.SAD, Mood.CURIOUS, Mood.EXCITED, Mood.BORED]
        for i in range(25):
            state.set_mood(moods[i % len(moods)], 0.5)

        # Should only keep last 20
        assert len(state.history) <= 20

    def test_intensity_clamped(self):
        """Test that intensity is clamped to 0-1."""
        from core.personality import MoodState, Mood

        state = MoodState()

        state.set_mood(Mood.HAPPY, 1.5)  # Too high
        assert state.intensity == 1.0

        state.set_mood(Mood.SAD, -0.5)  # Too low
        assert state.intensity == 0.0


class TestPersonality:
    """Tests for the Personality class."""

    def test_initialization(self, personality):
        """Test personality initialization."""
        assert personality.name == "TestInkling"
        assert personality.mood.current is not None
        assert personality.traits is not None

    def test_on_interaction_positive(self, personality):
        """Test positive interaction effects."""
        from core.personality import Mood

        # Set to bored first
        personality.mood.set_mood(Mood.BORED, 0.5)

        personality.on_interaction(positive=True)

        # Should transition from BORED to CURIOUS
        assert personality.mood.current == Mood.CURIOUS

    def test_first_interaction_awards_daily_and_chat_xp(self, personality):
        """First interaction of the day should include daily + chat XP."""
        from core.progression import ChatQuality

        quality = ChatQuality(
            message_length=80,
            turn_count=3,
            is_question=True,
            sentiment="positive",
        )
        xp_awarded = personality.on_interaction(
            positive=True,
            chat_quality=quality,
            user_message="Can we go deeper on this topic?",
        )

        assert xp_awarded is not None
        assert xp_awarded > 20

    def test_on_interaction_negative(self, personality):
        """Test negative interaction effects."""
        from core.personality import Mood

        personality.mood.set_mood(Mood.HAPPY, 0.5)

        personality.on_interaction(positive=False)

        # Should transition from HAPPY to SAD
        assert personality.mood.current == Mood.SAD

    def test_on_success(self, personality):
        """Test success event effects."""
        from core.personality import Mood

        personality.on_success(magnitude=0.8)
        assert personality.mood.current == Mood.EXCITED

        personality.on_success(magnitude=0.5)
        assert personality.mood.current == Mood.HAPPY

    def test_on_failure(self, personality):
        """Test failure event effects."""
        from core.personality import Mood

        personality.on_failure(magnitude=0.8)
        assert personality.mood.current == Mood.SAD

        personality.on_failure(magnitude=0.5)
        assert personality.mood.current == Mood.BORED

    def test_on_social_event(self, personality):
        """Test social event effects."""
        from core.personality import Mood

        personality.on_social_event("dream_received")
        assert personality.mood.current == Mood.CURIOUS

        personality.on_social_event("telegram_received")
        assert personality.mood.current == Mood.EXCITED

        personality.on_social_event("dream_posted")
        assert personality.mood.current == Mood.GRATEFUL

    def test_face_property(self, personality):
        """Test getting current face expression."""
        from core.personality import Mood

        personality.mood.set_mood(Mood.HAPPY, 0.5)
        assert personality.face == "happy"

        personality.mood.set_mood(Mood.SLEEPY, 0.5)
        assert personality.face == "sleep"

    def test_energy_property(self, personality):
        """Test getting current energy level."""
        from core.personality import Mood

        personality.mood.set_mood(Mood.EXCITED, 1.0)
        assert personality.energy == 0.9  # 0.9 * 1.0

        personality.mood.set_mood(Mood.SLEEPY, 0.5)
        assert personality.energy == 0.05  # 0.1 * 0.5

    def test_mood_change_callback(self, personality):
        """Test mood change callbacks."""
        from core.personality import Mood

        callback_called = []

        def on_change(old_mood, new_mood):
            callback_called.append((old_mood, new_mood))

        personality.on_mood_change(on_change)
        personality.on_success(magnitude=0.8)

        assert len(callback_called) == 1
        assert callback_called[0][1] == Mood.EXCITED

    def test_get_system_prompt_context(self, personality):
        """Test generating AI system prompt context."""
        context = personality.get_system_prompt_context()

        assert "TestInkling" in context
        assert "AI companion" in context
        assert "e-ink device" in context

    def test_get_status_line(self, personality):
        """Test generating status line."""
        status = personality.get_status_line()

        assert "[" in status
        assert "]" in status
        # Should contain mood name
        assert personality.mood.current.value in status

    def test_serialization(self, personality):
        """Test personality serialization."""
        from core.personality import Personality, Mood

        personality.mood.set_mood(Mood.CURIOUS, 0.7)

        data = personality.to_dict()

        assert data["name"] == "TestInkling"
        assert data["mood"]["current"] == "curious"
        assert data["mood"]["intensity"] == 0.7
        assert "traits" in data

    def test_deserialization(self):
        """Test personality deserialization."""
        from core.personality import Personality, Mood

        data = {
            "name": "RestoredInkling",
            "mood": {"current": "excited", "intensity": 0.8},
            "traits": {"curiosity": 0.9, "cheerfulness": 0.5},
            "interaction_count": 42,
        }

        p = Personality.from_dict(data)

        assert p.name == "RestoredInkling"
        assert p.mood.current == Mood.EXCITED
        assert p.mood.intensity == 0.8
        assert p.traits.curiosity == 0.9
        assert p._interaction_count == 42

    def test_invalid_mood_deserialization(self):
        """Test that invalid mood in data falls back to HAPPY."""
        from core.personality import Personality, Mood

        data = {
            "name": "TestInkling",
            "mood": {"current": "invalid_mood", "intensity": 0.5},
        }

        p = Personality.from_dict(data)
        assert p.mood.current == Mood.HAPPY
