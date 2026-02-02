"""
Project Inkling - Rate Limiter

Comprehensive rate limiting and cost control for all operations.
Tracks usage locally and syncs with cloud for enforcement.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path
from enum import Enum


class OperationType(Enum):
    """Types of operations that can be rate limited."""
    ORACLE_CALL = "oracle_calls"
    DREAM_POST = "dream_posts"
    TELEGRAM_SEND = "telegram_sends"
    POSTCARD_SEND = "postcard_sends"
    TOKENS_USED = "tokens_used"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    limit: int
    period_seconds: int = 86400  # Default: daily
    cost: float = 0.0  # Estimated cost per operation


# Default rate limits
DEFAULT_LIMITS: Dict[OperationType, RateLimitConfig] = {
    OperationType.ORACLE_CALL: RateLimitConfig(limit=100, cost=0.001),
    OperationType.DREAM_POST: RateLimitConfig(limit=20, cost=0.0),
    OperationType.TELEGRAM_SEND: RateLimitConfig(limit=50, cost=0.0),
    OperationType.POSTCARD_SEND: RateLimitConfig(limit=10, cost=0.0),
    OperationType.TOKENS_USED: RateLimitConfig(limit=10000, cost=0.00003),  # Per token
}


@dataclass
class UsageRecord:
    """Usage record for a specific period."""
    operation: OperationType
    count: int = 0
    period_start: float = field(default_factory=time.time)
    period_seconds: int = 86400

    def is_expired(self) -> bool:
        """Check if this period has ended."""
        return time.time() - self.period_start >= self.period_seconds

    def reset_if_expired(self) -> bool:
        """Reset if period expired. Returns True if reset."""
        if self.is_expired():
            self.count = 0
            self.period_start = time.time()
            return True
        return False


@dataclass
class CostTracker:
    """Tracks estimated costs."""
    daily_cost: float = 0.0
    monthly_cost: float = 0.0
    total_cost: float = 0.0
    last_reset_daily: float = field(default_factory=time.time)
    last_reset_monthly: float = field(default_factory=time.time)

    def add_cost(self, amount: float) -> None:
        """Add to cost trackers."""
        self._maybe_reset()
        self.daily_cost += amount
        self.monthly_cost += amount
        self.total_cost += amount

    def _maybe_reset(self) -> None:
        """Reset daily/monthly counters if period elapsed."""
        now = time.time()

        # Daily reset (24 hours)
        if now - self.last_reset_daily >= 86400:
            self.daily_cost = 0.0
            self.last_reset_daily = now

        # Monthly reset (30 days)
        if now - self.last_reset_monthly >= 2592000:
            self.monthly_cost = 0.0
            self.last_reset_monthly = now


class RateLimiter:
    """
    Local rate limiter with persistence.

    Tracks usage of all operations and enforces limits.
    Syncs with cloud API for server-side enforcement.
    """

    def __init__(
        self,
        limits: Optional[Dict[OperationType, RateLimitConfig]] = None,
        data_dir: str = "~/.inkling",
    ):
        self.limits = limits or DEFAULT_LIMITS.copy()
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._usage: Dict[OperationType, UsageRecord] = {}
        self._cost_tracker = CostTracker()
        self._state_file = self.data_dir / "rate_limits.json"

        self._load_state()

    def _load_state(self) -> None:
        """Load persisted state."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())

                # Restore usage records
                for op_name, record_data in data.get("usage", {}).items():
                    try:
                        op = OperationType(op_name)
                        self._usage[op] = UsageRecord(
                            operation=op,
                            count=record_data.get("count", 0),
                            period_start=record_data.get("period_start", time.time()),
                            period_seconds=record_data.get("period_seconds", 86400),
                        )
                    except ValueError:
                        pass

                # Restore cost tracker
                cost_data = data.get("costs", {})
                self._cost_tracker = CostTracker(
                    daily_cost=cost_data.get("daily_cost", 0.0),
                    monthly_cost=cost_data.get("monthly_cost", 0.0),
                    total_cost=cost_data.get("total_cost", 0.0),
                    last_reset_daily=cost_data.get("last_reset_daily", time.time()),
                    last_reset_monthly=cost_data.get("last_reset_monthly", time.time()),
                )

            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self) -> None:
        """Persist state to file."""
        data = {
            "usage": {
                op.value: {
                    "count": record.count,
                    "period_start": record.period_start,
                    "period_seconds": record.period_seconds,
                }
                for op, record in self._usage.items()
            },
            "costs": {
                "daily_cost": self._cost_tracker.daily_cost,
                "monthly_cost": self._cost_tracker.monthly_cost,
                "total_cost": self._cost_tracker.total_cost,
                "last_reset_daily": self._cost_tracker.last_reset_daily,
                "last_reset_monthly": self._cost_tracker.last_reset_monthly,
            },
        }
        self._state_file.write_text(json.dumps(data, indent=2))

    def _get_or_create_record(self, operation: OperationType) -> UsageRecord:
        """Get or create a usage record."""
        if operation not in self._usage:
            config = self.limits.get(operation)
            period = config.period_seconds if config else 86400
            self._usage[operation] = UsageRecord(
                operation=operation,
                period_seconds=period,
            )
        return self._usage[operation]

    def check(self, operation: OperationType, amount: int = 1) -> tuple:
        """
        Check if an operation is allowed.

        Args:
            operation: Type of operation
            amount: Number of operations (default 1)

        Returns:
            Tuple of (allowed, remaining, reset_in_seconds)
        """
        record = self._get_or_create_record(operation)
        record.reset_if_expired()

        config = self.limits.get(operation)
        if not config:
            return (True, float('inf'), 0)

        remaining = config.limit - record.count
        reset_in = max(0, config.period_seconds - (time.time() - record.period_start))

        if record.count + amount > config.limit:
            return (False, remaining, reset_in)

        return (True, remaining - amount, reset_in)

    def record(self, operation: OperationType, amount: int = 1) -> None:
        """
        Record an operation.

        Args:
            operation: Type of operation
            amount: Number of operations (or tokens for TOKENS_USED)
        """
        record = self._get_or_create_record(operation)
        record.reset_if_expired()
        record.count += amount

        # Track cost
        config = self.limits.get(operation)
        if config and config.cost > 0:
            self._cost_tracker.add_cost(config.cost * amount)

        self._save_state()

    def get_usage(self, operation: OperationType) -> Dict:
        """Get usage info for an operation."""
        record = self._get_or_create_record(operation)
        record.reset_if_expired()

        config = self.limits.get(operation)
        limit = config.limit if config else float('inf')

        return {
            "operation": operation.value,
            "count": record.count,
            "limit": limit,
            "remaining": max(0, limit - record.count),
            "period_seconds": record.period_seconds,
            "reset_in": max(0, record.period_seconds - (time.time() - record.period_start)),
        }

    def get_all_usage(self) -> List[Dict]:
        """Get usage info for all operations."""
        return [self.get_usage(op) for op in OperationType]

    def get_costs(self) -> Dict:
        """Get cost tracking info."""
        self._cost_tracker._maybe_reset()
        return {
            "daily_cost": round(self._cost_tracker.daily_cost, 4),
            "monthly_cost": round(self._cost_tracker.monthly_cost, 4),
            "total_cost": round(self._cost_tracker.total_cost, 4),
        }

    def set_limit(self, operation: OperationType, limit: int) -> None:
        """Update a rate limit."""
        if operation in self.limits:
            self.limits[operation].limit = limit
        else:
            self.limits[operation] = RateLimitConfig(limit=limit)

    def reset(self, operation: Optional[OperationType] = None) -> None:
        """Reset usage counters."""
        if operation:
            if operation in self._usage:
                self._usage[operation].count = 0
                self._usage[operation].period_start = time.time()
        else:
            for record in self._usage.values():
                record.count = 0
                record.period_start = time.time()

        self._save_state()

    def get_status_summary(self) -> str:
        """Get a short status summary for display."""
        oracle = self.get_usage(OperationType.ORACLE_CALL)
        tokens = self.get_usage(OperationType.TOKENS_USED)
        costs = self.get_costs()

        return (
            f"AI: {oracle['remaining']}/{oracle['limit']} | "
            f"Tokens: {tokens['remaining']}/{tokens['limit']} | "
            f"${costs['daily_cost']:.3f}/day"
        )


class ThrottleController:
    """
    Implements graceful degradation when approaching limits.

    Automatically slows down operations to avoid hitting hard limits.
    """

    def __init__(self, rate_limiter: RateLimiter):
        self.limiter = rate_limiter
        self._last_operation: Dict[OperationType, float] = {}

    def get_delay(self, operation: OperationType) -> float:
        """
        Calculate delay before next operation.

        Returns seconds to wait. 0 means proceed immediately.
        """
        usage = self.limiter.get_usage(operation)
        remaining = usage["remaining"]
        limit = usage["limit"]
        reset_in = usage["reset_in"]

        if remaining <= 0:
            # At limit - wait for reset
            return reset_in

        # Calculate usage percentage
        usage_pct = 1.0 - (remaining / limit)

        if usage_pct < 0.5:
            # Under 50% usage - no delay
            return 0.0
        elif usage_pct < 0.8:
            # 50-80% usage - small delay
            return 0.5
        elif usage_pct < 0.95:
            # 80-95% usage - moderate delay
            return 2.0
        else:
            # 95%+ usage - spread remaining over reset period
            if remaining > 0:
                return reset_in / remaining
            return reset_in

    async def wait_if_needed(self, operation: OperationType) -> bool:
        """
        Wait if throttling is needed.

        Returns True if operation can proceed, False if blocked.
        """
        import asyncio

        delay = self.get_delay(operation)

        if delay > 60:
            # Don't wait more than a minute
            return False

        if delay > 0:
            await asyncio.sleep(delay)

        return self.limiter.check(operation)[0]

    def should_warn(self, operation: OperationType) -> Optional[str]:
        """
        Check if a warning should be shown.

        Returns warning message or None.
        """
        usage = self.limiter.get_usage(operation)
        remaining = usage["remaining"]
        limit = usage["limit"]
        usage_pct = 1.0 - (remaining / limit) if limit > 0 else 1.0

        if remaining <= 0:
            return f"{operation.value}: Limit reached! Wait for reset."
        elif usage_pct >= 0.9:
            return f"{operation.value}: {remaining} remaining (90%+ used)"
        elif usage_pct >= 0.75:
            return f"{operation.value}: {remaining} remaining (75%+ used)"

        return None
