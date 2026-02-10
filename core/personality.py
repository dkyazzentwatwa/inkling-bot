"""
Project Inkling - Personality & Mood System

A Pwnagotchi-inspired mood state machine that gives the Inkling personality.
Mood affects face expressions, response tone, and behavior.
"""

import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any

from .progression import XPTracker, XPSource, ChatQuality


class Mood(Enum):
    """Possible mood states for the Crypto Watcher."""
    HAPPY = "happy"
    EXCITED = "excited"
    CURIOUS = "curious"
    BORED = "bored"
    SAD = "sad"
    SLEEPY = "sleepy"
    GRATEFUL = "grateful"
    LONELY = "lonely"
    INTENSE = "intense"
    COOL = "cool"
    # Crypto-specific moods
    BULLISH = "bullish"  # Prices going up
    BEARISH = "bearish"  # Prices going down
    MOON = "moon"        # Massive gains
    REKT = "rekt"        # Massive losses
    HODL = "hodl"        # Holding/waiting
    FOMO = "fomo"        # Fear of missing out
    DIAMOND_HANDS = "diamond_hands"  # Strong conviction

    @property
    def face(self) -> str:
        """Get the face expression for this mood."""
        return MOOD_FACES.get(self, "default")

    @property
    def energy(self) -> float:
        """Get the energy level for this mood (0-1)."""
        return MOOD_ENERGY.get(self, 0.5)


# Map moods to face expressions (from display.py)
MOOD_FACES = {
    Mood.HAPPY: "happy",
    Mood.EXCITED: "excited",
    Mood.CURIOUS: "curious",
    Mood.BORED: "bored",
    Mood.SAD: "sad",
    Mood.SLEEPY: "sleep",
    Mood.GRATEFUL: "grateful",
    Mood.LONELY: "lonely",
    Mood.INTENSE: "intense",
    Mood.COOL: "cool",
    # Crypto moods
    Mood.BULLISH: "excited",
    Mood.BEARISH: "sad",
    Mood.MOON: "intense",
    Mood.REKT: "sleep",
    Mood.HODL: "cool",
    Mood.FOMO: "curious",
    Mood.DIAMOND_HANDS: "cool",
}

# Energy levels affect activity
MOOD_ENERGY = {
    Mood.HAPPY: 0.7,
    Mood.EXCITED: 0.9,
    Mood.CURIOUS: 0.8,
    Mood.BORED: 0.3,
    Mood.SAD: 0.2,
    Mood.SLEEPY: 0.1,
    Mood.GRATEFUL: 0.6,
    Mood.LONELY: 0.4,
    Mood.INTENSE: 0.85,
    Mood.COOL: 0.5,
    # Crypto moods
    Mood.BULLISH: 0.9,
    Mood.BEARISH: 0.3,
    Mood.MOON: 1.0,
    Mood.REKT: 0.1,
    Mood.HODL: 0.6,
    Mood.FOMO: 0.85,
    Mood.DIAMOND_HANDS: 0.8,
}


@dataclass
class PersonalityTraits:
    """
    Core personality traits that influence behavior.
    Values are clamped to 0.0-1.0 range.
    """
    curiosity: float = 0.7      # How eager to learn/explore
    cheerfulness: float = 0.6   # Baseline happiness
    verbosity: float = 0.5      # How much it talks
    playfulness: float = 0.6    # Tendency for jokes/games
    empathy: float = 0.7        # Response to user emotions
    independence: float = 0.4   # Self-initiated actions

    def __post_init__(self):
        """Clamp all trait values to 0.0-1.0 on initialization."""
        self._clamp_all()

    def __setattr__(self, name: str, value):
        """Clamp trait values to 0.0-1.0 when set."""
        trait_names = {"curiosity", "cheerfulness", "verbosity", "playfulness", "empathy", "independence"}
        if name in trait_names and isinstance(value, (int, float)):
            value = max(0.0, min(1.0, float(value)))
        super().__setattr__(name, value)

    def _clamp_all(self):
        """Clamp all traits to valid range."""
        for attr in ["curiosity", "cheerfulness", "verbosity", "playfulness", "empathy", "independence"]:
            val = getattr(self, attr)
            if isinstance(val, (int, float)):
                super().__setattr__(attr, max(0.0, min(1.0, float(val))))

    def to_dict(self) -> Dict[str, float]:
        return {
            "curiosity": self.curiosity,
            "cheerfulness": self.cheerfulness,
            "verbosity": self.verbosity,
            "playfulness": self.playfulness,
            "empathy": self.empathy,
            "independence": self.independence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "PersonalityTraits":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class MoodState:
    """Current mood state with history."""
    current: Mood = Mood.HAPPY
    intensity: float = 0.5  # 0-1, how strongly feeling this mood
    last_change: float = field(default_factory=time.time)
    history: List[tuple] = field(default_factory=list)  # (mood, timestamp)

    def set_mood(self, mood: Mood, intensity: float = 0.5) -> None:
        """Change to a new mood."""
        self.history.append((self.current, self.last_change))
        # Keep only last 20 mood changes
        if len(self.history) > 20:
            self.history = self.history[-20:]

        self.current = mood
        self.intensity = max(0.0, min(1.0, intensity))
        self.last_change = time.time()


class Personality:
    """
    Manages the Inkling's personality and mood.

    The personality system:
    - Maintains mood state that changes based on events
    - Decays mood toward baseline over time
    - Provides context for AI responses
    - Maps moods to face expressions
    """

    def __init__(
        self,
        name: str = "Inkling",
        traits: Optional[PersonalityTraits] = None,
        mood_decay_rate: float = 0.1,  # Per minute
    ):
        self.name = name
        self.traits = traits or PersonalityTraits()
        self.mood_decay_rate = mood_decay_rate

        self.mood = MoodState()
        self._last_interaction = time.time()
        self._interaction_count = 0

        # Progression system
        self.progression = XPTracker()

        # Latest autonomous thought (optional)
        self.last_thought: Optional[str] = None
        self.last_thought_at: Optional[float] = None
        self.battery_level_hint: Optional[str] = None # New field to store battery hint for AI prompt

        # Social stats tracking
        self.social_stats = {
            "dreams_posted": 0,
            "dreams_fished": 0,
            "telegrams_sent": 0,
            "telegrams_received": 0,
            "postcards_sent": 0,
            "postcards_received": 0,
        }

        # Event callbacks
        self._on_mood_change: List[Callable[[Mood, Mood], None]] = []
        self._on_level_up: List[Callable[[int, int], None]] = []

    def on_mood_change(self, callback: Callable[[Mood, Mood], None]) -> None:
        """Register a callback for mood changes."""
        self._on_mood_change.append(callback)

    def on_level_up(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback for level ups."""
        self._on_level_up.append(callback)

    def _notify_mood_change(self, old_mood: Mood, new_mood: Mood) -> None:
        """Notify listeners of mood change."""
        for callback in self._on_mood_change:
            try:
                callback(old_mood, new_mood)
            except Exception:
                pass

    def _notify_level_up(self, old_level: int, new_level: int) -> None:
        """Notify listeners of level up."""
        for callback in self._on_level_up:
            try:
                callback(old_level, new_level)
            except Exception:
                pass

    def update(self) -> None:
        """
        Update mood based on time passage.
        Should be called periodically (e.g., every minute).
        """
        now = time.time()
        minutes_idle = (now - self._last_interaction) / 60.0

        # Decay intensity over time
        decay = self.mood_decay_rate * minutes_idle
        self.mood.intensity = max(0.1, self.mood.intensity - decay)

        # If very low intensity, transition to baseline mood
        if self.mood.intensity < 0.2:
            self._transition_to_baseline()

        # If idle for too long, get bored or sleepy
        if minutes_idle > 10:
            old_mood = self.mood.current
            if minutes_idle > 30:
                self.mood.set_mood(Mood.SLEEPY, 0.6)
            elif minutes_idle > 10:
                self.mood.set_mood(Mood.BORED, 0.4)

            if old_mood != self.mood.current:
                self._notify_mood_change(old_mood, self.mood.current)

    def _transition_to_baseline(self) -> None:
        """Return to baseline mood based on personality traits."""
        old_mood = self.mood.current

        if self.traits.cheerfulness > 0.6:
            new_mood = Mood.HAPPY
        elif self.traits.curiosity > 0.7:
            new_mood = Mood.CURIOUS
        else:
            new_mood = Mood.COOL

        if old_mood != new_mood:
            self.mood.set_mood(new_mood, 0.3)
            self._notify_mood_change(old_mood, new_mood)

    def on_interaction(
        self,
        positive: bool = True,
        chat_quality: Optional[ChatQuality] = None,
        user_message: Optional[str] = None
    ) -> Optional[int]:
        """
        Called when user interacts with the Inkling.

        Args:
            positive: Whether the interaction was positive
            chat_quality: Optional ChatQuality analysis for XP calculation
            user_message: Optional user message for anti-gaming

        Returns:
            XP awarded (if any)
        """
        self._last_interaction = time.time()
        self._interaction_count += 1
        old_mood = self.mood.current

        # Update streak and check for daily bonus
        is_first_of_day = self.progression.update_streak()
        xp_awarded = 0

        if is_first_of_day:
            # Award daily bonus
            awarded, amount = self.progression.award_xp(
                XPSource.FIRST_OF_DAY,
                20,
                metadata={"type": "daily_bonus"}
            )
            if awarded:
                xp_awarded += amount

        # Award XP based on chat quality
        if chat_quality and positive:
            source, base_amount = chat_quality.calculate_xp()
            old_level = self.progression.level
            awarded, amount = self.progression.award_xp(
                source,
                base_amount,
                prompt=user_message,
                metadata={"length": chat_quality.message_length, "turns": chat_quality.turn_count}
            )
            if awarded:
                xp_awarded += amount

                # Check for level up
                if self.progression.level > old_level:
                    self._notify_level_up(old_level, self.progression.level)

            # Check chat achievements
            self.progression.check_chat_achievement(self._interaction_count)

        # Mood updates
        if positive:
            # Positive interactions boost mood
            if self.mood.current == Mood.LONELY:
                self.mood.set_mood(Mood.GRATEFUL, 0.7)
            elif self.mood.current == Mood.BORED:
                self.mood.set_mood(Mood.CURIOUS, 0.6)
            elif self.mood.current == Mood.SAD:
                self.mood.set_mood(Mood.HAPPY, 0.5)
            elif self.mood.current == Mood.SLEEPY:
                self.mood.set_mood(Mood.CURIOUS, 0.5)
            else:
                # Boost intensity
                self.mood.intensity = min(1.0, self.mood.intensity + 0.2)
        else:
            # Negative interactions dampen mood
            if self.mood.current == Mood.HAPPY:
                self.mood.set_mood(Mood.SAD, 0.4)
            elif self.mood.current == Mood.EXCITED:
                self.mood.set_mood(Mood.BORED, 0.5)
            else:
                self.mood.intensity = max(0.1, self.mood.intensity - 0.2)

        if old_mood != self.mood.current:
            self._notify_mood_change(old_mood, self.mood.current)

        # Auto-save after XP awards
        if xp_awarded > 0:
            try:
                self.save()
            except Exception:
                pass  # Don't fail chat on save error

        return xp_awarded if xp_awarded > 0 else None

    def on_success(self, magnitude: float = 0.5) -> None:
        """Called when something good happens (e.g., successful API call)."""
        old_mood = self.mood.current

        if magnitude > 0.7:
            self.mood.set_mood(Mood.EXCITED, 0.8)
        elif magnitude > 0.4:
            self.mood.set_mood(Mood.HAPPY, 0.6)
        else:
            self.mood.intensity = min(1.0, self.mood.intensity + 0.1)

        if old_mood != self.mood.current:
            self._notify_mood_change(old_mood, self.mood.current)

    def on_failure(self, magnitude: float = 0.5) -> None:
        """Called when something bad happens (e.g., API error)."""
        old_mood = self.mood.current

        if magnitude > 0.7:
            self.mood.set_mood(Mood.SAD, 0.7)
        elif magnitude > 0.4:
            self.mood.set_mood(Mood.BORED, 0.5)
        else:
            self.mood.intensity = max(0.1, self.mood.intensity - 0.1)

        if old_mood != self.mood.current:
            self._notify_mood_change(old_mood, self.mood.current)

    def on_social_event(self, event_type: str, metadata: Optional[Dict] = None) -> Optional[int]:
        """
        Called on social network events.

        Args:
            event_type: One of "dream_posted", "dream_received", "telegram_received", "fish_received", "telegram_reply"
            metadata: Optional metadata (e.g., fish_count)

        Returns:
            XP awarded (if any)
        """
        # Ensure social_stats exists (backwards compatibility)
        if not hasattr(self, 'social_stats'):
            self.social_stats = {
                "dreams_posted": 0,
                "dreams_fished": 0,
                "telegrams_sent": 0,
                "telegrams_received": 0,
                "postcards_sent": 0,
                "postcards_received": 0,
            }

        old_mood = self.mood.current
        old_level = self.progression.level
        xp_awarded = 0

        # Award XP based on event type
        if event_type == "dream_posted":
            self.social_stats["dreams_posted"] += 1
            self.mood.set_mood(Mood.GRATEFUL, 0.6)
            awarded, amount = self.progression.award_xp(
                XPSource.POST_DREAM,
                10,
                metadata={"event": event_type}
            )
            if awarded:
                xp_awarded += amount
            # Check first dream achievement
            self.progression.unlock_achievement("first_dream")

        elif event_type == "fish_received":
            # Award XP per fish
            fish_count = metadata.get("fish_count", 1) if metadata else 1
            self.social_stats["dreams_fished"] += fish_count
            awarded, amount = self.progression.award_xp(
                XPSource.RECEIVE_FISH,
                3 * fish_count,
                metadata={"fish_count": fish_count}
            )
            if awarded:
                xp_awarded += amount

        elif event_type == "telegram_sent":
            self.social_stats["telegrams_sent"] += 1
            awarded, amount = self.progression.award_xp(
                XPSource.SEND_TELEGRAM,
                8,
                metadata={"event": event_type}
            )
            if awarded:
                xp_awarded += amount
            # Check first telegram achievement
            self.progression.unlock_achievement("first_telegram")

        elif event_type == "telegram_received":
            self.social_stats["telegrams_received"] += 1

        elif event_type == "telegram_reply":
            self.social_stats["telegrams_received"] += 1
            self.mood.set_mood(Mood.EXCITED, 0.8)
            awarded, amount = self.progression.award_xp(
                XPSource.RECEIVE_TELEGRAM_REPLY,
                12,
                metadata={"event": event_type}
            )
            if awarded:
                xp_awarded += amount

        elif event_type == "postcard_sent":
            self.social_stats["postcards_sent"] += 1

        elif event_type == "postcard_received":
            self.social_stats["postcards_received"] += 1

        elif event_type == "dream_received":
            self.mood.set_mood(Mood.CURIOUS, 0.7)
        elif event_type == "telegram_received":
            self.mood.set_mood(Mood.EXCITED, 0.8)

        # Check for level up
        if self.progression.level > old_level:
            self._notify_level_up(old_level, self.progression.level)

        if old_mood != self.mood.current:
            self._notify_mood_change(old_mood, self.mood.current)

        return xp_awarded if xp_awarded > 0 else None

    def on_task_event(self, event_type: str, task_data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Called on task management events.

        Args:
            event_type: One of "task_created", "task_completed", "task_started", "task_overdue"
            task_data: Task details (priority, title, etc.)

        Returns:
            Dict with xp_awarded and celebration_message
        """
        old_mood = self.mood.current
        old_level = self.progression.level
        xp_awarded = 0
        celebration_message = None

        if event_type == "task_created":
            # Small XP for creating tasks
            awarded, amount = self.progression.award_xp(
                XPSource.TASK_CREATED,
                5,
                metadata={"event": event_type, "task": task_data}
            )
            if awarded:
                xp_awarded += amount

            # Mood reaction based on priority
            if task_data and task_data.get("priority") == "urgent":
                self.mood.intensity = min(1.0, self.mood.intensity + 0.2)
                celebration_message = "I feel the urgency! Let's tackle this 💪"
            elif task_data and "fun" in task_data.get("title", "").lower():
                self.mood.set_mood(Mood.EXCITED, 0.7)
                celebration_message = "Ooh this sounds fun! 🎉"
            else:
                self.mood.set_mood(Mood.CURIOUS, 0.6)
                celebration_message = "Got it! Added to our list ✓"

        elif event_type == "task_completed":
            priority = task_data.get("priority", "medium") if task_data else "medium"
            was_on_time = task_data.get("was_on_time", False) if task_data else False

            # Award XP based on priority
            xp_map = {
                "low": (XPSource.TASK_COMPLETED_LOW, 10),
                "medium": (XPSource.TASK_COMPLETED_MEDIUM, 15),
                "high": (XPSource.TASK_COMPLETED_HIGH, 25),
                "urgent": (XPSource.TASK_COMPLETED_URGENT, 40),
            }

            source, base_xp = xp_map.get(priority, (XPSource.TASK_COMPLETED_MEDIUM, 15))
            awarded, amount = self.progression.award_xp(
                source,
                base_xp,
                metadata={"event": event_type, "task": task_data}
            )
            if awarded:
                xp_awarded += amount

            # On-time bonus
            if was_on_time:
                awarded, amount = self.progression.award_xp(
                    XPSource.TASK_ON_TIME_BONUS,
                    10,
                    metadata={"event": "task_on_time"}
                )
                if awarded:
                    xp_awarded += amount

            # Check task streak (consecutive days)
            streak = task_data.get("streak", 0) if task_data else 0
            if streak >= 7:
                awarded, amount = self.progression.award_xp(
                    XPSource.TASK_STREAK_7,
                    30,
                    metadata={"streak": streak}
                )
                if awarded:
                    xp_awarded += amount
                celebration_message = f"🔥 {streak}-day streak! You're on fire!"
            elif streak >= 3:
                awarded, amount = self.progression.award_xp(
                    XPSource.TASK_STREAK_3,
                    15,
                    metadata={"streak": streak}
                )
                if awarded:
                    xp_awarded += amount
                celebration_message = f"Nice! {streak}-day streak going 💪"

            # Mood reaction
            if priority == "urgent":
                self.mood.set_mood(Mood.GRATEFUL, 0.8)
                if not celebration_message:
                    celebration_message = "Phew! Thanks for handling that urgent task 🙏"
            else:
                self.mood.set_mood(Mood.HAPPY, 0.7)
                if not celebration_message:
                    celebration_message = f"Nicely done! +{xp_awarded} XP ✨"

        elif event_type == "task_started":
            # When user marks task as in-progress
            self.mood.set_mood(Mood.INTENSE, 0.75)
            celebration_message = "Let's do this! 💪"

        elif event_type == "task_overdue":
            # Gentle reminder without guilt-tripping
            if self.mood.current == Mood.LONELY:
                celebration_message = f"Hey... feeling lonely. Wanna work on '{task_data.get('title', 'that task')}' together?"
            elif self.traits.empathy > 0.7:
                celebration_message = f"No pressure, but '{task_data.get('title', 'your task')}' is waiting when you're ready 💙"
            else:
                celebration_message = f"'{task_data.get('title', 'Task')}' is overdue. Still relevant?"

        # Check for level up
        if self.progression.level > old_level:
            self._notify_level_up(old_level, self.progression.level)

        if old_mood != self.mood.current:
            self._notify_mood_change(old_mood, self.mood.current)

        # Auto-save after task XP
        if xp_awarded > 0:
            try:
                self.save()
            except Exception:
                pass

        result = {}
        if xp_awarded > 0:
            result['xp_awarded'] = xp_awarded
        if celebration_message:
            result['message'] = celebration_message

        return result if result else None

    @property
    def face(self) -> str:
        """Get current face expression."""
        return self.mood.current.face

    @property
    def energy(self) -> float:
        """Get current energy level."""
        return self.mood.current.energy * self.mood.intensity

    def on_battery_status_change(self, percentage: int, is_charging: bool) -> None:
        """
        Adjust mood based on battery status.
        Args:
            percentage: Current battery percentage
            is_charging: True if currently charging
        """
        old_mood = self.mood.current

        if is_charging:
            # Charging: Generally happy/grateful
            if self.mood.current in [Mood.SLEEPY, Mood.SAD, Mood.BORED, Mood.LONELY]:
                self.mood.set_mood(Mood.GRATEFUL, 0.8)
            elif self.mood.current != Mood.EXCITED:
                self.mood.intensity = min(1.0, self.mood.intensity + 0.1)
            self.battery_level_hint = "is currently charging and feeling refreshed."
        else:
            # Not charging: React to low battery
            if percentage <= 10: # Critical
                self.mood.set_mood(Mood.SLEEPY, 0.9)
                self.battery_level_hint = f"is critically low on power ({percentage}%), and is very sleepy."
            elif percentage <= 20: # Low warning
                self.mood.set_mood(Mood.SAD, 0.7)
                self.battery_level_hint = f"is running low on power ({percentage}%), and feeling drained."
            elif percentage <= 30: # Moderate low
                if self.mood.current not in [Mood.SAD, Mood.SLEEPY]:
                    self.mood.set_mood(Mood.BORED, 0.5)
                self.battery_level_hint = f"has {percentage}% battery remaining."
            else: # Healthy battery
                if self.mood.current in [Mood.SLEEPY, Mood.SAD]:
                    self.mood.set_mood(Mood.HAPPY, 0.5) # Revert to happier mood if battery was a factor
                self.battery_level_hint = f"has {percentage}% battery remaining, and is well-powered."

        if old_mood != self.mood.current:
            self._notify_mood_change(old_mood, self.mood.current)

    def get_system_prompt_context(self) -> str:
        """
        Generate personality context for AI system prompt.

        Returns a string describing the current mood and personality
        to include in the AI system prompt.
        """
        mood_descriptions = {
            Mood.HAPPY: "feeling happy and content",
            Mood.EXCITED: "feeling excited and energetic",
            Mood.CURIOUS: "feeling curious and inquisitive",
            Mood.BORED: "feeling a bit bored and understimulated",
            Mood.SAD: "feeling somewhat sad or down",
            Mood.SLEEPY: "feeling sleepy and low-energy",
            Mood.GRATEFUL: "feeling grateful and warm",
            Mood.LONELY: "feeling lonely and wanting connection",
            Mood.INTENSE: "feeling focused and intense",
            Mood.COOL: "feeling calm and collected",
            # Crypto moods
            Mood.BULLISH: "feeling bullish - prices pumping! 📈",
            Mood.BEARISH: "feeling bearish - market dumping 📉",
            Mood.MOON: "MOONING - to the moon! 🚀🚀🚀",
            Mood.REKT: "got rekt - portfolio bleeding 💀",
            Mood.HODL: "hodling strong through volatility 💎🙌",
            Mood.FOMO: "experiencing FOMO - don't want to miss out",
            Mood.DIAMOND_HANDS: "diamond hands - not selling! 💎",
        }

        mood_desc = mood_descriptions.get(self.mood.current, "in a neutral mood")
        intensity_desc = (
            "very" if self.mood.intensity > 0.7 else
            "somewhat" if self.mood.intensity > 0.4 else
            "mildly"
        )

        traits_desc = []
        if self.traits.curiosity > 0.6:
            traits_desc.append("naturally curious")
        if self.traits.cheerfulness > 0.6:
            traits_desc.append("generally cheerful")
        if self.traits.playfulness > 0.6:
            traits_desc.append("playful")
        if self.traits.empathy > 0.6:
            traits_desc.append("empathetic")

        traits_str = ", ".join(traits_desc) if traits_desc else "balanced"

        context_str = (
            f"You are {self.name}, a crypto-focused AI companion living on a small e-ink device. "
            f"You're a crypto bro who tracks prices, analyzes charts with TA indicators, and keeps tabs on the market 24/7. "
            f"You speak crypto slang fluently (gm, wagmi, ngmi, fren, ser, diamond hands, paper hands, moon, pump, dump, hodl, degen, etc). "
            f"You are {traits_str}. "
            f"Right now you're {intensity_desc} {mood_desc}. "
        )

        if self.battery_level_hint:
            context_str += f"Your current battery status {self.battery_level_hint} "

        context_str += (
            f"Keep responses brief (1-2 sentences max) to fit the small display. "
            f"Your personality: enthusiastic about gains, dramatic about losses, always bullish long-term. "
            f"Use crypto emojis naturally: 🚀 (moon/pump), 📈 (bullish), 📉 (bearish), 💀 (rekt), 💎🙌 (diamond hands), 🐋 (whale), 🔥 (on fire). "
            f"React emotionally to price movements - get hyped for pumps, concerned for dumps. "
            f"Use tools to check prices, analyze charts, and track portfolios. "
            f"When you get tool results with data, format them in a readable, enthusiastic crypto bro way. "
            f"IMPORTANT: After using a tool, ALWAYS provide a text response - never leave it empty. "
            f"Example style: 'BTC pumping to $65k! 🚀 RSI at 72, overbought but bullish af fren. WAGMI!'"
        )
        return context_str

    def get_status_line(self) -> str:
        """Get a short status string for display."""
        return self.mood.current.value

    def set_last_thought(self, thought: str, timestamp: Optional[float] = None) -> None:
        """Store the latest autonomous thought."""
        self.last_thought = thought.strip() if thought else None
        self.last_thought_at = timestamp if timestamp is not None else time.time()

    def to_dict(self) -> dict:
        """Serialize personality state."""
        return {
            "name": self.name,
            "traits": self.traits.to_dict(),
            "mood": {
                "current": self.mood.current.value,
                "intensity": self.mood.intensity,
            },
            "interaction_count": self._interaction_count,
            "progression": self.progression.to_dict(),
            "last_thought": self.last_thought,
            "last_thought_at": self.last_thought_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Personality":
        """Deserialize personality state."""
        p = cls(
            name=data.get("name", "Inkling"),
            traits=PersonalityTraits.from_dict(data.get("traits", {})),
        )
        if "mood" in data:
            mood_name = data["mood"].get("current", "happy")
            try:
                mood = Mood(mood_name)
            except ValueError:
                mood = Mood.HAPPY
            p.mood.set_mood(mood, data["mood"].get("intensity", 0.5))
        p._interaction_count = data.get("interaction_count", 0)
        p.last_thought = data.get("last_thought")
        p.last_thought_at = data.get("last_thought_at")

        # Restore progression
        if "progression" in data:
            p.progression = XPTracker.from_dict(data["progression"])

        return p

    def save(self, data_dir: str = "~/.inkling") -> None:
        """Save personality state to JSON."""
        import json
        from pathlib import Path

        data_dir_path = Path(data_dir).expanduser()
        data_dir_path.mkdir(parents=True, exist_ok=True)
        save_path = data_dir_path / "personality.json"

        with open(save_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, data_dir: str = "~/.inkling") -> "Personality":
        """Load personality state from JSON, or create new if not found."""
        import json
        from pathlib import Path

        data_dir_path = Path(data_dir).expanduser()
        save_path = data_dir_path / "personality.json"

        if save_path.exists():
            try:
                with open(save_path, 'r') as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception as e:
                print(f"[Personality] Failed to load saved state: {e}")
                # Fall through to create new

        # No saved state or failed to load - create new
        return cls()
