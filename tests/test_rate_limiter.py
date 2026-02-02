"""
Project Inkling - Rate Limiter Tests

Tests for core/rate_limiter.py - usage tracking and throttling.
"""

import time
import pytest


class TestOperationType:
    """Tests for OperationType enum."""

    def test_operation_types_exist(self):
        """Test all expected operation types exist."""
        from core.rate_limiter import OperationType

        assert OperationType.ORACLE_CALL.value == "oracle_calls"
        assert OperationType.DREAM_POST.value == "dream_posts"
        assert OperationType.TELEGRAM_SEND.value == "telegram_sends"
        assert OperationType.POSTCARD_SEND.value == "postcard_sends"
        assert OperationType.TOKENS_USED.value == "tokens_used"


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_config_defaults(self):
        """Test RateLimitConfig default values."""
        from core.rate_limiter import RateLimitConfig

        config = RateLimitConfig(limit=100)

        assert config.limit == 100
        assert config.period_seconds == 86400  # Default: daily
        assert config.cost == 0.0


class TestUsageRecord:
    """Tests for UsageRecord dataclass."""

    def test_usage_record_defaults(self):
        """Test UsageRecord default values."""
        from core.rate_limiter import UsageRecord, OperationType

        record = UsageRecord(operation=OperationType.ORACLE_CALL)

        assert record.count == 0
        assert record.period_seconds == 86400

    def test_is_expired_false(self):
        """Test that fresh record is not expired."""
        from core.rate_limiter import UsageRecord, OperationType

        record = UsageRecord(operation=OperationType.ORACLE_CALL)

        assert record.is_expired() is False

    def test_is_expired_true(self):
        """Test that old record is expired."""
        from core.rate_limiter import UsageRecord, OperationType

        record = UsageRecord(
            operation=OperationType.ORACLE_CALL,
            period_start=time.time() - 100000,  # Old
            period_seconds=86400,
        )

        assert record.is_expired() is True

    def test_reset_if_expired(self):
        """Test resetting an expired record."""
        from core.rate_limiter import UsageRecord, OperationType

        record = UsageRecord(
            operation=OperationType.ORACLE_CALL,
            count=50,
            period_start=time.time() - 100000,  # Old
        )

        was_reset = record.reset_if_expired()

        assert was_reset is True
        assert record.count == 0


class TestCostTracker:
    """Tests for CostTracker dataclass."""

    def test_add_cost(self):
        """Test adding costs."""
        from core.rate_limiter import CostTracker

        tracker = CostTracker()
        tracker.add_cost(0.01)
        tracker.add_cost(0.02)

        assert tracker.daily_cost == 0.03
        assert tracker.monthly_cost == 0.03
        assert tracker.total_cost == 0.03


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_initialization(self, rate_limiter):
        """Test RateLimiter initialization."""
        assert rate_limiter.limits is not None
        assert rate_limiter._usage is not None

    def test_check_allowed(self, rate_limiter):
        """Test checking an allowed operation."""
        from core.rate_limiter import OperationType

        allowed, remaining, reset_in = rate_limiter.check(OperationType.ORACLE_CALL)

        assert allowed is True
        assert remaining > 0

    def test_check_and_record(self, rate_limiter):
        """Test recording operations."""
        from core.rate_limiter import OperationType

        # Check initial
        allowed1, remaining1, _ = rate_limiter.check(OperationType.ORACLE_CALL)
        assert allowed1 is True

        # Record
        rate_limiter.record(OperationType.ORACLE_CALL, amount=1)

        # Check again
        allowed2, remaining2, _ = rate_limiter.check(OperationType.ORACLE_CALL)
        assert remaining2 == remaining1 - 1

    def test_check_blocked_at_limit(self, rate_limiter):
        """Test that operations are blocked at limit."""
        from core.rate_limiter import OperationType, RateLimitConfig

        # Set a low limit
        rate_limiter.set_limit(OperationType.DREAM_POST, 2)

        # Record up to limit
        rate_limiter.record(OperationType.DREAM_POST, amount=2)

        # Should be blocked
        allowed, remaining, _ = rate_limiter.check(OperationType.DREAM_POST)
        assert allowed is False
        assert remaining == 0

    def test_get_usage(self, rate_limiter):
        """Test getting usage info."""
        from core.rate_limiter import OperationType

        rate_limiter.record(OperationType.ORACLE_CALL, amount=5)

        usage = rate_limiter.get_usage(OperationType.ORACLE_CALL)

        assert usage["operation"] == "oracle_calls"
        assert usage["count"] == 5
        assert "limit" in usage
        assert "remaining" in usage
        assert "reset_in" in usage

    def test_get_all_usage(self, rate_limiter):
        """Test getting usage for all operations."""
        usage_list = rate_limiter.get_all_usage()

        assert len(usage_list) > 0
        assert all("operation" in u for u in usage_list)

    def test_get_costs(self, rate_limiter):
        """Test getting cost info."""
        costs = rate_limiter.get_costs()

        assert "daily_cost" in costs
        assert "monthly_cost" in costs
        assert "total_cost" in costs

    def test_cost_tracking(self, rate_limiter):
        """Test that costs are tracked for operations with cost."""
        from core.rate_limiter import OperationType

        # Oracle calls have cost
        rate_limiter.record(OperationType.ORACLE_CALL, amount=10)

        costs = rate_limiter.get_costs()

        # 10 calls * 0.001 cost per call = 0.01
        assert costs["daily_cost"] > 0

    def test_set_limit(self, rate_limiter):
        """Test setting a custom limit."""
        from core.rate_limiter import OperationType

        rate_limiter.set_limit(OperationType.DREAM_POST, 500)

        usage = rate_limiter.get_usage(OperationType.DREAM_POST)
        assert usage["limit"] == 500

    def test_reset_single_operation(self, rate_limiter):
        """Test resetting a single operation counter."""
        from core.rate_limiter import OperationType

        rate_limiter.record(OperationType.ORACLE_CALL, amount=50)
        rate_limiter.reset(OperationType.ORACLE_CALL)

        usage = rate_limiter.get_usage(OperationType.ORACLE_CALL)
        assert usage["count"] == 0

    def test_reset_all_operations(self, rate_limiter):
        """Test resetting all operation counters."""
        from core.rate_limiter import OperationType

        rate_limiter.record(OperationType.ORACLE_CALL, amount=10)
        rate_limiter.record(OperationType.DREAM_POST, amount=5)

        rate_limiter.reset()

        assert rate_limiter.get_usage(OperationType.ORACLE_CALL)["count"] == 0
        assert rate_limiter.get_usage(OperationType.DREAM_POST)["count"] == 0

    def test_get_status_summary(self, rate_limiter):
        """Test getting status summary string."""
        status = rate_limiter.get_status_summary()

        assert "AI:" in status
        assert "Tokens:" in status
        assert "/day" in status

    def test_persistence(self, temp_data_dir):
        """Test that state persists across instances."""
        from core.rate_limiter import RateLimiter, OperationType

        # First instance
        limiter1 = RateLimiter(data_dir=temp_data_dir)
        limiter1.record(OperationType.ORACLE_CALL, amount=25)

        # Second instance (should load state)
        limiter2 = RateLimiter(data_dir=temp_data_dir)

        usage = limiter2.get_usage(OperationType.ORACLE_CALL)
        assert usage["count"] == 25


class TestThrottleController:
    """Tests for ThrottleController class."""

    def test_get_delay_under_half(self, rate_limiter):
        """Test no delay when under 50% usage."""
        from core.rate_limiter import ThrottleController, OperationType

        controller = ThrottleController(rate_limiter)

        delay = controller.get_delay(OperationType.ORACLE_CALL)

        assert delay == 0.0

    def test_get_delay_high_usage(self, rate_limiter):
        """Test delay when usage is high."""
        from core.rate_limiter import ThrottleController, OperationType

        # Use 75% of limit
        limit = rate_limiter.limits[OperationType.ORACLE_CALL].limit
        rate_limiter.record(OperationType.ORACLE_CALL, amount=int(limit * 0.75))

        controller = ThrottleController(rate_limiter)
        delay = controller.get_delay(OperationType.ORACLE_CALL)

        assert delay > 0

    def test_get_delay_at_limit(self, rate_limiter):
        """Test delay when at limit."""
        from core.rate_limiter import ThrottleController, OperationType

        # Use full limit
        limit = rate_limiter.limits[OperationType.ORACLE_CALL].limit
        rate_limiter.record(OperationType.ORACLE_CALL, amount=limit)

        controller = ThrottleController(rate_limiter)
        delay = controller.get_delay(OperationType.ORACLE_CALL)

        # Should suggest waiting for reset
        assert delay > 0

    def test_should_warn_none(self, rate_limiter):
        """Test no warning when usage is low."""
        from core.rate_limiter import ThrottleController, OperationType

        controller = ThrottleController(rate_limiter)

        warning = controller.should_warn(OperationType.ORACLE_CALL)

        assert warning is None

    def test_should_warn_high_usage(self, rate_limiter):
        """Test warning when usage is high."""
        from core.rate_limiter import ThrottleController, OperationType

        # Use 80% of limit
        limit = rate_limiter.limits[OperationType.ORACLE_CALL].limit
        rate_limiter.record(OperationType.ORACLE_CALL, amount=int(limit * 0.8))

        controller = ThrottleController(rate_limiter)
        warning = controller.should_warn(OperationType.ORACLE_CALL)

        assert warning is not None
        assert "remaining" in warning

    def test_should_warn_at_limit(self, rate_limiter):
        """Test warning when at limit."""
        from core.rate_limiter import ThrottleController, OperationType

        limit = rate_limiter.limits[OperationType.ORACLE_CALL].limit
        rate_limiter.record(OperationType.ORACLE_CALL, amount=limit)

        controller = ThrottleController(rate_limiter)
        warning = controller.should_warn(OperationType.ORACLE_CALL)

        assert warning is not None
        assert "Limit reached" in warning


class TestThrottleControllerAsync:
    """Async tests for ThrottleController."""

    @pytest.mark.asyncio
    async def test_wait_if_needed_proceeds(self, rate_limiter):
        """Test that wait_if_needed proceeds when allowed."""
        from core.rate_limiter import ThrottleController, OperationType

        controller = ThrottleController(rate_limiter)

        can_proceed = await controller.wait_if_needed(OperationType.ORACLE_CALL)

        assert can_proceed is True

    @pytest.mark.asyncio
    async def test_wait_if_needed_blocked(self, rate_limiter):
        """Test that wait_if_needed blocks when at limit."""
        from core.rate_limiter import ThrottleController, OperationType

        # Set very short period and use up limit
        rate_limiter.set_limit(OperationType.ORACLE_CALL, 1)
        rate_limiter.record(OperationType.ORACLE_CALL, amount=1)

        controller = ThrottleController(rate_limiter)

        # Should return False (blocked) since reset time > 60s
        can_proceed = await controller.wait_if_needed(OperationType.ORACLE_CALL)

        assert can_proceed is False
