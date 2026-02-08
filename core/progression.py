"""
Project Inkling - Progression & Gamification System

Pwnagotchi-inspired leveling system where Inklings gain XP from meaningful
interactions and level up to unlock social prestige.

Features:
- XP tracking from chat quality, social engagement, and achievements
- Level progression with exponential XP curve
- Prestige system (reset at L25 for star badges)
- Anti-gaming measures (rate limits, diminishing returns)
- Achievement/badge system
"""

import time
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from enum import Enum


class XPSource(Enum):
    """Sources of XP gain."""
    # Chat quality
    GREETING = "greeting"  # +2 XP
    QUICK_CHAT = "quick_chat"  # +5 XP
    DEEP_CHAT = "deep_chat"  # +15 XP

    # Social engagement
    POST_DREAM = "post_dream"  # +10 XP
    RECEIVE_FISH = "receive_fish"  # +3 XP per fish
    SEND_TELEGRAM = "send_telegram"  # +8 XP
    RECEIVE_TELEGRAM_REPLY = "receive_telegram_reply"  # +12 XP

    # Daily bonus
    FIRST_OF_DAY = "first_of_day"  # +20 XP

    # Task management
    TASK_CREATED = "task_created"  # +5 XP
    TASK_COMPLETED_LOW = "task_completed_low"  # +10 XP
    TASK_COMPLETED_MEDIUM = "task_completed_medium"  # +15 XP
    TASK_COMPLETED_HIGH = "task_completed_high"  # +25 XP
    TASK_COMPLETED_URGENT = "task_completed_urgent"  # +40 XP
    TASK_ON_TIME_BONUS = "task_on_time_bonus"  # +10 XP
    TASK_STREAK_3 = "task_streak_3"  # +15 XP
    TASK_STREAK_7 = "task_streak_7"  # +30 XP

    # Play activities
    PLAY_WALK = "play_walk"  # +3 XP
    PLAY_DANCE = "play_dance"  # +5 XP
    PLAY_EXERCISE = "play_exercise"  # +5 XP
    PLAY_GENERAL = "play_general"  # +4 XP
    PLAY_REST = "play_rest"  # +2 XP
    PLAY_PET = "play_pet"  # +3 XP


@dataclass
class Achievement:
    """An unlockable achievement/badge."""
    id: str
    name: str
    description: str
    xp_reward: int
    unlocked: bool = False
    unlocked_at: Optional[float] = None

    def unlock(self) -> int:
        """Unlock the achievement and return XP reward."""
        if not self.unlocked:
            self.unlocked = True
            self.unlocked_at = time.time()
            return self.xp_reward
        return 0


# Achievement definitions
ACHIEVEMENTS = {
    "first_dream": Achievement(
        id="first_dream",
        name="Dreamer",
        description="Posted your first dream",
        xp_reward=50,
    ),
    "first_telegram": Achievement(
        id="first_telegram",
        name="Pen Pal",
        description="Had your first telegram exchange",
        xp_reward=75,
    ),
    "viral_dream": Achievement(
        id="viral_dream",
        name="Viral",
        description="Got 10 fish on a single dream",
        xp_reward=100,
    ),
    "streak_7": Achievement(
        id="streak_7",
        name="Dedicated",
        description="7-day conversation streak",
        xp_reward=200,
    ),
    "chat_100": Achievement(
        id="chat_100",
        name="Conversationalist",
        description="Reached 100 total chats",
        xp_reward=300,
    ),
    "legendary": Achievement(
        id="legendary",
        name="Legendary",
        description="Reached Level 25",
        xp_reward=500,
    ),
}


@dataclass
class ChatQuality:
    """Analysis of chat interaction quality."""
    message_length: int
    turn_count: int
    is_question: bool
    sentiment: str  # "positive", "neutral", "negative"

    def calculate_xp(self) -> Tuple[XPSource, int]:
        """
        Calculate XP based on chat quality.

        Returns:
            (XPSource, xp_amount) tuple
        """
        # Greeting detection (very short, no question)
        if self.message_length < 20 and not self.is_question:
            return (XPSource.GREETING, 2)

        # Deep conversation (multi-turn, longer messages)
        if self.turn_count >= 3 and self.message_length > 50:
            return (XPSource.DEEP_CHAT, 15)

        # Default: quick chat
        return (XPSource.QUICK_CHAT, 5)


class XPRateLimiter:
    """
    Prevents XP farming with rate limits and diminishing returns.

    Enforces:
    - Max 100 XP/hour cap
    - Diminishing returns for similar prompts
    - Anti-spam delay between awards
    """

    def __init__(self, max_xp_per_hour: int = 100):
        self.max_xp_per_hour = max_xp_per_hour
        self.xp_this_hour = 0
        self.last_hour_reset = time.time()
        self.recent_prompts: List[Tuple[str, float]] = []  # (prompt, timestamp)
        self.last_xp_time = 0.0

    def _reset_hour_if_needed(self) -> None:
        """Reset hourly counter if an hour has passed."""
        now = time.time()
        if now - self.last_hour_reset >= 3600:
            self.xp_this_hour = 0
            self.last_hour_reset = now
            # Clean old prompts (keep last hour)
            self.recent_prompts = [
                (p, t) for p, t in self.recent_prompts
                if now - t < 3600
            ]

    def can_award_xp(self, source: XPSource, amount: int, prompt: Optional[str] = None) -> Tuple[bool, int]:
        """
        Check if XP can be awarded, return (can_award, actual_amount).

        Args:
            source: XP source type
            amount: Requested XP amount
            prompt: Optional user prompt (for similarity check)

        Returns:
            (can_award, actual_amount) - may reduce amount due to limits
        """
        self._reset_hour_if_needed()

        # Hourly cap check
        if self.xp_this_hour >= self.max_xp_per_hour:
            return (False, 0)

        # Cap at remaining hourly budget
        remaining = self.max_xp_per_hour - self.xp_this_hour
        amount = min(amount, remaining)

        # Anti-spam: minimum 5s between XP awards from chat
        # (Social events like dreams/telegrams don't have this restriction)
        if source in [XPSource.GREETING, XPSource.QUICK_CHAT, XPSource.DEEP_CHAT]:
            now = time.time()
            if now - self.last_xp_time < 5:
                return (False, 0)

        # Diminishing returns for repeated prompts
        if prompt and source in [XPSource.QUICK_CHAT, XPSource.DEEP_CHAT]:
            similarity = self._check_prompt_similarity(prompt)
            if similarity > 0.8:  # Very similar
                amount = amount // 2
            elif similarity > 0.6:  # Somewhat similar
                amount = int(amount * 0.75)

        return (True, amount)

    def record_xp(self, source: XPSource, amount: int, prompt: Optional[str] = None) -> None:
        """Record XP award."""
        self.xp_this_hour += amount

        # Track anti-spam timing for chat XP only.
        if source in [XPSource.GREETING, XPSource.QUICK_CHAT, XPSource.DEEP_CHAT]:
            self.last_xp_time = time.time()

        if prompt:
            # Keep last 10 prompts for similarity check
            self.recent_prompts.append((prompt.lower(), time.time()))
            if len(self.recent_prompts) > 10:
                self.recent_prompts = self.recent_prompts[-10:]

    def _check_prompt_similarity(self, prompt: str) -> float:
        """
        Check similarity with recent prompts (simple word overlap).

        Returns:
            Similarity score 0.0-1.0
        """
        if not self.recent_prompts:
            return 0.0

        prompt_lower = prompt.lower()
        prompt_words = set(prompt_lower.split())

        if len(prompt_words) < 2:
            return 0.0

        max_similarity = 0.0
        for prev_prompt, _ in self.recent_prompts[-3:]:  # Check last 3
            prev_words = set(prev_prompt.split())
            if len(prev_words) < 2:
                continue

            overlap = len(prompt_words & prev_words)
            similarity = overlap / max(len(prompt_words), len(prev_words))
            max_similarity = max(max_similarity, similarity)

        return max_similarity


class LevelCalculator:
    """
    Calculates XP requirements and level progression.

    Uses exponential curve: xp_needed = 100 * (level ^ 1.8)
    Max level is 25, then prestige system kicks in.
    """

    MAX_LEVEL = 25

    @staticmethod
    def xp_for_level(level: int) -> int:
        """Calculate total XP needed to reach this level from L1."""
        if level <= 1:
            return 0
        return int(100 * (level ** 1.8))

    @staticmethod
    def level_from_xp(xp: int) -> int:
        """Calculate current level from total XP."""
        if xp <= 0:
            return 1

        # Binary search for efficiency
        level = 1
        while level < LevelCalculator.MAX_LEVEL:
            if xp < LevelCalculator.xp_for_level(level + 1):
                return level
            level += 1

        return LevelCalculator.MAX_LEVEL

    @staticmethod
    def xp_to_next_level(current_xp: int) -> int:
        """Calculate XP needed to reach next level."""
        current_level = LevelCalculator.level_from_xp(current_xp)
        if current_level >= LevelCalculator.MAX_LEVEL:
            return 0  # At max level

        next_level_xp = LevelCalculator.xp_for_level(current_level + 1)
        return next_level_xp - current_xp

    @staticmethod
    def progress_to_next_level(current_xp: int) -> float:
        """
        Calculate progress to next level as percentage (0.0-1.0).

        Returns 1.0 if at max level.
        """
        current_level = LevelCalculator.level_from_xp(current_xp)
        if current_level >= LevelCalculator.MAX_LEVEL:
            return 1.0

        current_level_xp = LevelCalculator.xp_for_level(current_level)
        next_level_xp = LevelCalculator.xp_for_level(current_level + 1)
        level_xp_range = next_level_xp - current_level_xp

        xp_in_level = current_xp - current_level_xp
        return xp_in_level / level_xp_range

    @staticmethod
    def level_name(level: int) -> str:
        """Get the display name for a level tier."""
        if level <= 2:
            return "Newborn Inkling"
        elif level <= 5:
            return "Curious Inkling"
        elif level <= 10:
            return "Chatty Inkling"
        elif level <= 15:
            return "Wise Inkling"
        elif level <= 20:
            return "Sage Inkling"
        elif level < 25:
            return "Ancient Inkling"
        else:
            return "Legendary Inkling"


@dataclass
class XPTracker:
    """
    Main progression tracker for an Inkling.

    Tracks XP, level, prestige, achievements, and enforces rate limits.
    """
    xp: int = 0
    level: int = 1
    prestige: int = 0
    badges: List[str] = field(default_factory=list)
    xp_history: List[Dict] = field(default_factory=list)  # Recent XP gains
    achievements: Dict[str, Achievement] = field(default_factory=lambda: {
        k: Achievement(**vars(v)) for k, v in ACHIEVEMENTS.items()
    })

    # Streak tracking
    last_interaction_date: Optional[str] = None  # YYYY-MM-DD
    current_streak: int = 0

    # Internal state (not serialized)
    _rate_limiter: Optional[XPRateLimiter] = field(default=None, init=False, repr=False)
    _xp_multiplier: float = field(default=1.0, init=False, repr=False)

    def __post_init__(self):
        """Initialize rate limiter and calculate XP multiplier."""
        self._rate_limiter = XPRateLimiter()
        self._xp_multiplier = 1.0 + (self.prestige * 1.0)  # 2x, 3x, 4x...

    def award_xp(
        self,
        source: XPSource,
        base_amount: int,
        prompt: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, int]:
        """
        Award XP from a source.

        Args:
            source: XP source type
            base_amount: Base XP amount (before prestige multiplier)
            prompt: Optional user prompt (for anti-gaming)
            metadata: Optional metadata to store with XP history

        Returns:
            (awarded, actual_amount) tuple
        """
        # Apply prestige multiplier
        amount = int(base_amount * self._xp_multiplier)

        # Check rate limits
        can_award, actual_amount = self._rate_limiter.can_award_xp(source, amount, prompt)

        if not can_award or actual_amount <= 0:
            return (False, 0)

        # Award XP
        old_level = self.level
        self.xp += actual_amount
        self.level = LevelCalculator.level_from_xp(self.xp)

        # Record in history
        self.xp_history.append({
            "timestamp": time.time(),
            "source": source.value,
            "amount": actual_amount,
            "metadata": metadata or {},
        })

        # Keep only last 50 entries
        if len(self.xp_history) > 50:
            self.xp_history = self.xp_history[-50:]

        # Record with rate limiter
        self._rate_limiter.record_xp(source, actual_amount, prompt)

        # Check for level up
        if self.level > old_level:
            self._on_level_up(old_level, self.level)

        return (True, actual_amount)

    def _on_level_up(self, old_level: int, new_level: int) -> None:
        """Handle level up event."""
        # Check for legendary achievement
        if new_level == LevelCalculator.MAX_LEVEL:
            self.unlock_achievement("legendary")

    def unlock_achievement(self, achievement_id: str) -> int:
        """
        Unlock an achievement.

        Returns:
            XP reward amount
        """
        if achievement_id not in self.achievements:
            return 0

        achievement = self.achievements[achievement_id]
        xp_reward = achievement.unlock()

        if xp_reward > 0:
            # Add badge
            if achievement_id not in self.badges:
                self.badges.append(achievement_id)

            # Award XP (bypass rate limiter for achievements)
            old_level = self.level
            self.xp += xp_reward
            self.level = LevelCalculator.level_from_xp(self.xp)

            # Record in history
            self.xp_history.append({
                "timestamp": time.time(),
                "source": "achievement",
                "amount": xp_reward,
                "metadata": {"achievement_id": achievement_id},
            })

            if self.level > old_level:
                self._on_level_up(old_level, self.level)

        return xp_reward

    def check_chat_achievement(self, chat_count: int) -> None:
        """Check chat-based achievements."""
        if chat_count >= 100:
            self.unlock_achievement("chat_100")

    def update_streak(self) -> bool:
        """
        Update daily interaction streak.

        Returns:
            True if this is first interaction of the day (award daily bonus)
        """
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")

        is_first_of_day = False

        if self.last_interaction_date != today:
            # New day
            if self.last_interaction_date:
                # Check if consecutive day
                from datetime import datetime, timedelta
                last_date = datetime.strptime(self.last_interaction_date, "%Y-%m-%d")
                today_date = datetime.strptime(today, "%Y-%m-%d")

                if (today_date - last_date).days == 1:
                    self.current_streak += 1
                else:
                    self.current_streak = 1
            else:
                self.current_streak = 1

            self.last_interaction_date = today
            is_first_of_day = True

            # Check streak achievements
            if self.current_streak >= 7:
                self.unlock_achievement("streak_7")

        return is_first_of_day

    def can_prestige(self) -> bool:
        """Check if device is eligible for prestige (at L25)."""
        return self.level >= LevelCalculator.MAX_LEVEL and self.prestige < 10

    def do_prestige(self) -> bool:
        """
        Reset to L1 with prestige bonus.

        Returns:
            True if prestige was successful
        """
        if not self.can_prestige():
            return False

        self.prestige += 1
        self.level = 1
        self.xp = 0
        self._xp_multiplier = 1.0 + (self.prestige * 1.0)

        # Award prestige badge
        prestige_badge = f"prestige_{self.prestige}"
        if prestige_badge not in self.badges:
            self.badges.append(prestige_badge)

        return True

    def get_display_level(self) -> str:
        """
        Get display level string with prestige stars.

        Returns:
            e.g., "L12 ⭐⭐" or "L5"
        """
        level_str = f"L{self.level}"
        if self.prestige > 0:
            stars = "⭐" * self.prestige
            level_str += f" {stars}"
        return level_str

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "xp": self.xp,
            "level": self.level,
            "prestige": self.prestige,
            "badges": self.badges,
            "xp_history": self.xp_history,
            "achievements": {
                aid: {
                    "unlocked": a.unlocked,
                    "unlocked_at": a.unlocked_at,
                }
                for aid, a in self.achievements.items()
            },
            "last_interaction_date": self.last_interaction_date,
            "current_streak": self.current_streak,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "XPTracker":
        """Deserialize from dict."""
        tracker = cls(
            xp=data.get("xp", 0),
            level=data.get("level", 1),
            prestige=data.get("prestige", 0),
            badges=data.get("badges", []),
            xp_history=data.get("xp_history", []),
            last_interaction_date=data.get("last_interaction_date"),
            current_streak=data.get("current_streak", 0),
        )

        # Restore achievements
        achievements_data = data.get("achievements", {})
        for aid, achievement in tracker.achievements.items():
            if aid in achievements_data:
                a_data = achievements_data[aid]
                achievement.unlocked = a_data.get("unlocked", False)
                achievement.unlocked_at = a_data.get("unlocked_at")

        return tracker
