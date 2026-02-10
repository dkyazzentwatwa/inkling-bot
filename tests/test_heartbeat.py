"""
Project Inkling - Heartbeat Tests

Tests for core/heartbeat.py - proactive behavior system.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestBehaviorType:
    """Tests for BehaviorType enum."""

    def test_behavior_types(self):
        """Test all behavior types exist."""
        from core.heartbeat import BehaviorType

        assert BehaviorType.MOOD_DRIVEN.value == "mood"
        assert BehaviorType.TIME_BASED.value == "time"
        assert BehaviorType.SOCIAL.value == "social"
        assert BehaviorType.MAINTENANCE.value == "maint"


class TestProactiveBehavior:
    """Tests for ProactiveBehavior dataclass."""

    def test_can_trigger_fresh(self):
        """Test that fresh behavior can trigger."""
        from core.heartbeat import ProactiveBehavior, BehaviorType

        async def dummy():
            return None

        behavior = ProactiveBehavior(
            name="test",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=dummy,
            cooldown_seconds=60,
        )

        assert behavior.can_trigger() is True

    def test_can_trigger_on_cooldown(self):
        """Test that behavior on cooldown cannot trigger."""
        from core.heartbeat import ProactiveBehavior, BehaviorType
        import time

        async def dummy():
            return None

        behavior = ProactiveBehavior(
            name="test",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=dummy,
            cooldown_seconds=60,
            last_triggered=time.time(),  # Just triggered
        )

        assert behavior.can_trigger() is False

    def test_should_trigger_respects_probability(self):
        """Test that should_trigger respects probability."""
        from core.heartbeat import ProactiveBehavior, BehaviorType
        import random

        async def dummy():
            return None

        behavior = ProactiveBehavior(
            name="test",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=dummy,
            probability=0.0,  # Never trigger
        )

        # With 0% probability, should never trigger
        random.seed(42)
        results = [behavior.should_trigger() for _ in range(100)]
        assert not any(results)

    def test_should_trigger_high_probability(self):
        """Test that high probability triggers often."""
        from core.heartbeat import ProactiveBehavior, BehaviorType
        import random

        async def dummy():
            return None

        behavior = ProactiveBehavior(
            name="test",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=dummy,
            probability=1.0,  # Always trigger
        )

        # With 100% probability, should always trigger
        random.seed(42)
        results = [behavior.should_trigger() for _ in range(100)]
        assert all(results)


class TestHeartbeatConfig:
    """Tests for HeartbeatConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from core.heartbeat import HeartbeatConfig

        config = HeartbeatConfig()

        assert config.tick_interval_seconds == 60
        assert config.enable_mood_behaviors is True
        assert config.enable_time_behaviors is True
        assert config.enable_social_behaviors is True
        assert config.enable_maintenance is True
        assert config.quiet_hours_start == 23
        assert config.quiet_hours_end == 7

    def test_custom_config(self):
        """Test custom configuration."""
        from core.heartbeat import HeartbeatConfig

        config = HeartbeatConfig(
            tick_interval_seconds=30,
            enable_social_behaviors=False,
            quiet_hours_start=22,
            quiet_hours_end=8,
        )

        assert config.tick_interval_seconds == 30
        assert config.enable_social_behaviors is False
        assert config.quiet_hours_start == 22


class TestHeartbeat:
    """Tests for Heartbeat class."""

    @pytest.fixture
    def heartbeat(self, personality):
        """Create a Heartbeat instance for testing."""
        from core.heartbeat import Heartbeat, HeartbeatConfig

        config = HeartbeatConfig(
            tick_interval_seconds=1,  # Fast for testing
            quiet_hours_start=3,  # Unlikely to hit during tests
            quiet_hours_end=4,
        )
        return Heartbeat(personality, config=config)

    def test_initialization(self, heartbeat):
        """Test Heartbeat initialization."""
        assert heartbeat.personality is not None
        assert heartbeat._running is False
        assert len(heartbeat._behaviors) > 0

    def test_register_behavior(self, heartbeat):
        """Test registering a custom behavior."""
        from core.heartbeat import ProactiveBehavior, BehaviorType

        async def custom_handler():
            return "Custom message"

        behavior = ProactiveBehavior(
            name="custom",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=custom_handler,
        )

        initial_count = len(heartbeat._behaviors)
        heartbeat.register_behavior(behavior)

        assert len(heartbeat._behaviors) == initial_count + 1

    def test_get_stats(self, heartbeat):
        """Test getting heartbeat statistics."""
        stats = heartbeat.get_stats()

        assert "running" in stats
        assert "tick_count" in stats
        assert "behaviors_registered" in stats
        assert "config" in stats
        assert stats["running"] is False
        assert stats["behaviors_registered"] > 0

    def test_on_message_callback(self, heartbeat):
        """Test registering message callback."""
        callback = AsyncMock()
        heartbeat.on_message(callback)

        assert heartbeat._on_message is callback

    @pytest.mark.asyncio
    async def test_force_tick(self, heartbeat):
        """Test manually triggering a tick."""
        initial_count = heartbeat._tick_count

        await heartbeat.force_tick()

        assert heartbeat._tick_count == initial_count + 1
        assert heartbeat._last_tick > 0

    @pytest.mark.asyncio
    async def test_tick_updates_mood(self, heartbeat):
        """Test that tick updates personality."""
        # Just verify it doesn't crash
        await heartbeat.force_tick()

    def test_stop(self, heartbeat):
        """Test stopping the heartbeat."""
        heartbeat._running = True
        heartbeat.stop()

        assert heartbeat._running is False


class TestHeartbeatQuietHours:
    """Tests for quiet hours functionality."""

    def test_is_quiet_hours_normal_range(self, personality):
        """Test quiet hours detection with normal range."""
        from core.heartbeat import Heartbeat, HeartbeatConfig

        config = HeartbeatConfig(quiet_hours_start=22, quiet_hours_end=6)
        heartbeat = Heartbeat(personality, config=config)

        # 10 PM - 6 AM should be quiet
        assert heartbeat._is_quiet_hours(22) is True
        assert heartbeat._is_quiet_hours(23) is True
        assert heartbeat._is_quiet_hours(0) is True
        assert heartbeat._is_quiet_hours(5) is True
        assert heartbeat._is_quiet_hours(6) is False
        assert heartbeat._is_quiet_hours(12) is False

    def test_is_quiet_hours_midnight_wrap(self, personality):
        """Test quiet hours that wrap around midnight."""
        from core.heartbeat import Heartbeat, HeartbeatConfig

        config = HeartbeatConfig(quiet_hours_start=23, quiet_hours_end=7)
        heartbeat = Heartbeat(personality, config=config)

        assert heartbeat._is_quiet_hours(23) is True
        assert heartbeat._is_quiet_hours(0) is True
        assert heartbeat._is_quiet_hours(6) is True
        assert heartbeat._is_quiet_hours(7) is False
        assert heartbeat._is_quiet_hours(22) is False


class TestHeartbeatBehaviors:
    """Tests for built-in behaviors."""

    @pytest.fixture
    def heartbeat(self, personality):
        from core.heartbeat import Heartbeat, HeartbeatConfig

        config = HeartbeatConfig(tick_interval_seconds=1)
        return Heartbeat(personality, config=config)

    @pytest.mark.asyncio
    async def test_lonely_reach_out(self, heartbeat):
        """Test lonely behavior produces a message."""
        from core.personality import Mood

        heartbeat.personality.mood.set_mood(Mood.LONELY, 0.5)

        result = await heartbeat._behavior_lonely_reach_out()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_bored_suggest(self, heartbeat):
        """Test bored behavior produces a suggestion."""
        result = await heartbeat._behavior_bored_suggest()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_happy_share(self, heartbeat):
        """Test happy behavior produces a thought."""
        result = await heartbeat._behavior_happy_share()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_curious_browse_no_api(self, heartbeat):
        """Test curious browse with no API returns None."""
        result = await heartbeat._behavior_curious_browse()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_telegrams_no_api(self, heartbeat):
        """Test telegram check with no API returns None."""
        result = await heartbeat._behavior_check_telegrams()

        assert result is None

    @pytest.mark.asyncio
    async def test_prune_memories_no_memory(self, heartbeat):
        """Test memory prune with no memory store."""
        result = await heartbeat._behavior_prune_memories()

        assert result is None

    @pytest.mark.asyncio
    async def test_sync_queue_no_api(self, heartbeat):
        """Test queue sync with no API returns None."""
        result = await heartbeat._behavior_sync_queue()

        assert result is None


class TestHeartbeatMoodBehaviors:
    """Tests for mood-driven behavior selection."""

    @pytest.fixture
    def heartbeat(self, personality):
        from core.heartbeat import Heartbeat, HeartbeatConfig

        config = HeartbeatConfig(tick_interval_seconds=1)
        return Heartbeat(personality, config=config)

    def test_mood_behavior_matches_lonely(self, heartbeat):
        """Test that lonely behavior only runs when lonely."""
        from core.heartbeat import ProactiveBehavior, BehaviorType
        from core.personality import Mood

        async def dummy():
            return None

        behavior = ProactiveBehavior(
            name="lonely_reach_out",
            behavior_type=BehaviorType.MOOD_DRIVEN,
            handler=dummy,
        )

        heartbeat.personality.mood.set_mood(Mood.LONELY, 0.5)
        assert heartbeat._should_run_mood_behavior(behavior) is True

        heartbeat.personality.mood.set_mood(Mood.HAPPY, 0.5)
        assert heartbeat._should_run_mood_behavior(behavior) is False

    def test_non_mood_behavior_always_runs(self, heartbeat):
        """Test that non-mood behaviors aren't filtered."""
        from core.heartbeat import ProactiveBehavior, BehaviorType
        from core.personality import Mood

        async def dummy():
            return None

        behavior = ProactiveBehavior(
            name="maintenance_task",
            behavior_type=BehaviorType.MAINTENANCE,
            handler=dummy,
        )

        heartbeat.personality.mood.set_mood(Mood.SAD, 0.5)
        assert heartbeat._should_run_mood_behavior(behavior) is True


class TestHeartbeatIntegration:
    """Integration tests for heartbeat with other components."""

    @pytest.fixture
    def memory_store(self, temp_data_dir):
        from core.memory import MemoryStore

        store = MemoryStore(data_dir=temp_data_dir)
        store.initialize()
        yield store
        store.close()

    @pytest.mark.asyncio
    async def test_heartbeat_with_memory(self, personality, memory_store):
        """Test heartbeat with memory store integration."""
        from core.heartbeat import Heartbeat, HeartbeatConfig

        config = HeartbeatConfig(tick_interval_seconds=1)
        heartbeat = Heartbeat(
            personality,
            memory_store=memory_store,
            config=config,
        )

        # Should not crash when pruning with real memory
        result = await heartbeat._behavior_prune_memories()
        assert result is None

    @pytest.mark.asyncio
    async def test_autonomous_exploration_stores_memory(self, personality, memory_store):
        """Autonomous exploration should write a memory entry when memory is available."""
        from core.heartbeat import Heartbeat, HeartbeatConfig

        class FakeBrain:
            async def think(self, *args, **kwargs):
                class Result:
                    content = "A tiny reflective thought."
                return Result()

        config = HeartbeatConfig(tick_interval_seconds=1)
        heartbeat = Heartbeat(
            personality,
            memory_store=memory_store,
            brain=FakeBrain(),
            config=config,
        )

        message = await heartbeat._behavior_autonomous_exploration()

        assert message is not None
        assert memory_store.count() >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_message_callback(self, personality):
        """Test that behaviors trigger message callback."""
        from core.heartbeat import Heartbeat, HeartbeatConfig, ProactiveBehavior, BehaviorType

        config = HeartbeatConfig(tick_interval_seconds=1)
        heartbeat = Heartbeat(personality, config=config)

        messages_received = []

        async def on_message(msg, face):
            messages_received.append((msg, face))

        heartbeat.on_message(on_message)

        # Register a behavior that always triggers
        async def always_message():
            return "Test message"

        behavior = ProactiveBehavior(
            name="test_always",
            behavior_type=BehaviorType.MAINTENANCE,  # Not mood-filtered
            handler=always_message,
            probability=1.0,
            cooldown_seconds=0,
        )
        heartbeat.register_behavior(behavior)

        # Execute the behavior directly
        result = await heartbeat._execute_behavior(behavior)
        if result and heartbeat._on_message:
            await heartbeat._on_message(result, heartbeat.personality.face)

        assert len(messages_received) == 1
        assert messages_received[0][0] == "Test message"
