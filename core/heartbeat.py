"""
Project Inkling - Heartbeat System

Proactive behavior scheduler that gives the Inkling life.
Runs periodic ticks that can trigger mood-driven actions,
time-based behaviors, and background social activity.
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Optional, Callable, List, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from .personality import Personality, Mood
from . import system_stats # Import system_stats

try:
    from .scheduler import ScheduledTaskManager
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False


class BehaviorType(Enum):
    """Types of proactive behaviors."""
    MOOD_DRIVEN = "mood"      # Based on current mood
    TIME_BASED = "time"       # Based on time of day
    SOCIAL = "social"         # Check social features
    MAINTENANCE = "maint"     # Background maintenance
    BATTERY = "battery"       # Based on battery status


@dataclass
class ProactiveBehavior:
    """A behavior that can be triggered proactively."""
    name: str
    behavior_type: BehaviorType
    handler: Callable[..., Awaitable[Optional[str]]]
    probability: float = 0.1  # Chance to trigger per tick
    cooldown_seconds: int = 300  # Minimum time between triggers
    last_triggered: float = 0.0

    def can_trigger(self) -> bool:
        """Check if enough time has passed since last trigger."""
        return time.time() - self.last_triggered >= self.cooldown_seconds

    def should_trigger(self) -> bool:
        """Check if behavior should trigger this tick."""
        if not self.can_trigger():
            return False
        return random.random() < self.probability


@dataclass
class HeartbeatConfig:
    """Configuration for the heartbeat system."""
    tick_interval_seconds: int = 60  # How often to tick
    enable_mood_behaviors: bool = True
    enable_time_behaviors: bool = True
    enable_social_behaviors: bool = True
    enable_maintenance: bool = True
    enable_thoughts: bool = True
    thought_interval_min_minutes: int = 15
    thought_interval_max_minutes: int = 30
    quiet_hours_start: int = 23  # 11 PM
    quiet_hours_end: int = 7     # 7 AM
    
    # Battery specific settings
    enable_battery_behaviors: bool = True
    battery_low_threshold: int = 20 # Percentage at which "low" warning triggers
    battery_critical_threshold: int = 10 # Percentage at which "critical" warning triggers
    battery_full_threshold: int = 95 # Percentage at which "full" message triggers
    
    thought_surface_probability: float = 0.35


class Heartbeat:
    """
    Proactive behavior scheduler for the Inkling.

    The heartbeat gives the Inkling "life" by:
    - Adjusting mood based on time of day
    - Triggering spontaneous actions based on mood
    - Checking for social activity in the background
    - Running maintenance tasks (memory pruning, queue sync)

    Usage:
        heartbeat = Heartbeat(personality, display_manager, api_client, memory)
        await heartbeat.start()  # Runs until stopped
    """

    def __init__(
        self,
        personality: Personality,
        display_manager=None,
        api_client=None,
        memory_store=None,
        focus_manager=None,
        brain=None,
        task_manager=None,
        scheduler=None,
        config: Optional[HeartbeatConfig] = None,
    ):
        self.personality = personality
        self.display = display_manager
        self.api_client = api_client
        self.memory = memory_store
        self.focus_manager = focus_manager
        self.brain = brain
        self.task_manager = task_manager
        self.scheduler = scheduler
        self.config = config or HeartbeatConfig()

        self._running = False
        self._behaviors: List[ProactiveBehavior] = []
        self._last_tick = 0.0
        self._tick_count = 0
        self._next_thought_ts = 0.0

        # Battery state tracking
        self._last_battery_percentage: int = -1
        self._last_is_charging: bool = False
        self._battery_status_known: bool = False # Flag to know if battery info has been successfully retrieved

        # State tracking for battery behaviors (to avoid spamming messages on continuous states)
        self._prev_is_charging_tick: bool = False
        self._prev_battery_full_tick: bool = False

        # Callbacks for when behaviors want to show something
        self._on_message: Optional[Callable[[str, str], Awaitable[None]]] = None

        self._register_default_behaviors()
        self._schedule_next_thought()

    def on_message(self, callback: Callable[[str, str], Awaitable[None]]) -> None:
        """
        Register callback for when heartbeat wants to display a message.

        Callback receives (message, face) and should update the display.
        """
        self._on_message = callback

    def _register_default_behaviors(self) -> None:
        """Register the built-in proactive behaviors."""

        # Mood-driven behaviors
        self._behaviors.extend([
            ProactiveBehavior(
                name="lonely_reach_out",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_lonely_reach_out,
                probability=0.15,
                cooldown_seconds=600,
            ),
            ProactiveBehavior(
                name="bored_suggest_activity",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_bored_suggest,
                probability=0.2,
                cooldown_seconds=600,
            ),
            ProactiveBehavior(
                name="happy_share_thought",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_happy_share,
                probability=0.08,
                cooldown_seconds=1200,
            ),
            ProactiveBehavior(
                name="autonomous_exploration",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_autonomous_exploration,
                probability=0.05,
                cooldown_seconds=1800,  # Once every 30 min max
            ),
        ])

        # Time-based behaviors
        self._behaviors.extend([
            ProactiveBehavior(
                name="morning_greeting",
                behavior_type=BehaviorType.TIME_BASED,
                handler=self._behavior_morning_greeting,
                probability=0.5,
                cooldown_seconds=3600,
            ),
            ProactiveBehavior(
                name="evening_wind_down",
                behavior_type=BehaviorType.TIME_BASED,
                handler=self._behavior_evening_wind_down,
                probability=0.4,
                cooldown_seconds=3600,
            ),
        ])

        # Battery-based behaviors
        self._behaviors.extend([
            ProactiveBehavior(
                name="battery_low_warning",
                behavior_type=BehaviorType.BATTERY,
                handler=self._behavior_battery_low_warning,
                probability=0.2,
                cooldown_seconds=1800,
            ),
            ProactiveBehavior(
                name="battery_critical_warning",
                behavior_type=BehaviorType.BATTERY,
                handler=self._behavior_battery_critical_warning,
                probability=0.5,
                cooldown_seconds=600,
            ),
            ProactiveBehavior(
                name="battery_charging_start",
                behavior_type=BehaviorType.BATTERY,
                handler=self._behavior_battery_charging_start,
                probability=1.0,
                cooldown_seconds=60,
            ),
            ProactiveBehavior(
                name="battery_charging_stop",
                behavior_type=BehaviorType.BATTERY,
                handler=self._behavior_battery_charging_stop,
                probability=1.0,
                cooldown_seconds=60,
            ),
            ProactiveBehavior(
                name="battery_full",
                behavior_type=BehaviorType.BATTERY,
                handler=self._behavior_battery_full,
                probability=1.0,
                cooldown_seconds=600,
            ),
        ])


        # Maintenance behaviors
        self._behaviors.extend([
            ProactiveBehavior(
                name="prune_memories",
                behavior_type=BehaviorType.MAINTENANCE,
                handler=self._behavior_prune_memories,
                probability=0.1,
                cooldown_seconds=3600,
            ),
        ])

        # Task management behaviors (if task_manager is available)
        if self.task_manager:
            self._behaviors.extend([
                ProactiveBehavior(
                    name="remind_overdue_tasks",
                    behavior_type=BehaviorType.MAINTENANCE,
                    handler=self._behavior_remind_overdue,
                    probability=0.7,
                    cooldown_seconds=3600,  # Once per hour
                ),
                ProactiveBehavior(
                    name="suggest_next_task",
                    behavior_type=BehaviorType.MOOD_DRIVEN,
                    handler=self._behavior_suggest_task,
                    probability=0.3,
                    cooldown_seconds=1800,  # Every 30 minutes
                ),
                ProactiveBehavior(
                    name="celebrate_completion_streak",
                    behavior_type=BehaviorType.MAINTENANCE,
                    handler=self._behavior_celebrate_streak,
                    probability=0.5,
                    cooldown_seconds=86400,  # Once per day
                ),
            ])

        # Personality behaviors (daily journal, preferences, greetings)
        self._behaviors.extend([
            ProactiveBehavior(
                name="daily_journal",
                behavior_type=BehaviorType.MAINTENANCE,
                handler=self._behavior_daily_journal,
                probability=0.5,
                cooldown_seconds=86400,  # Once per day
            ),
            ProactiveBehavior(
                name="extract_preferences",
                behavior_type=BehaviorType.MAINTENANCE,
                handler=self._behavior_extract_preferences,
                probability=0.3,
                cooldown_seconds=3600,  # Once per hour
            ),
            ProactiveBehavior(
                name="mood_responsive_greeting",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_mood_greeting,
                probability=0.3,
                cooldown_seconds=1200,  # Every 20 minutes
            ),
        ])

    async def start(self) -> None:
        """Start the heartbeat loop."""
        self._running = True
        while self._running:
            await self._tick()
            await asyncio.sleep(self.config.tick_interval_seconds)

    def stop(self) -> None:
        """Stop the heartbeat loop."""
        self._running = False

    async def _tick(self) -> None:
        """Execute one heartbeat tick."""
        self._tick_count += 1
        self._last_tick = time.time()

        # Update personality based on time
        self._update_time_based_mood()

        # Update personality based on battery status
        self._update_battery_based_mood()

        # Natural mood decay
        self.personality.update()

        # Check if screen saver should activate
        if self.display and self.display.should_activate_screensaver():
            print("[Heartbeat] Activating screen saver (idle detected)")
            await self.display.start_screensaver()

        # Run scheduled tasks (if scheduler is available)
        if self.scheduler:
            self.scheduler.run_pending()

        # Run proactive behaviors
        await self._run_behaviors()

        # Generate autonomous thoughts on a cadence
        await self._maybe_generate_thought()

        # Update previous battery state for next tick's behavior checks
        if self._battery_status_known:
            self._prev_is_charging_tick = self._last_is_charging
            self._prev_battery_full_tick = (
                self._last_is_charging and
                self._last_battery_percentage >= self.config.battery_full_threshold
            )

    def _update_time_based_mood(self) -> None:
        """Adjust mood based on time of day."""
        hour = datetime.now().hour

        # Quiet hours - get sleepy
        if self._is_quiet_hours(hour):
            if self.personality.mood.current != Mood.SLEEPY:
                if random.random() < 0.3:
                    self.personality.mood.set_mood(Mood.SLEEPY, 0.6)
            return

        # Morning - tend toward happy/curious
        if 7 <= hour < 10:
            if self.personality.mood.current == Mood.SLEEPY:
                if random.random() < 0.4:
                    self.personality.mood.set_mood(Mood.CURIOUS, 0.5)

        # If idle too long during waking hours, get lonely
        minutes_idle = (time.time() - self.personality._last_interaction) / 60.0
        if minutes_idle > 60 and not self._is_quiet_hours(hour):
            if random.random() < 0.2:
                self.personality.mood.set_mood(Mood.LONELY, 0.5)

    def _update_battery_based_mood(self) -> None:
        """Refresh battery state and adjust personality mood if status changed."""
        try:
            battery = system_stats.get_all_stats().get("battery")
            if not battery:
                self._battery_status_known = False
                return

            percentage = int(battery.get("percentage", -1))
            is_charging = bool(battery.get("charging", False))
            if percentage < 0:
                self._battery_status_known = False
                return

            should_notify = (
                not self._battery_status_known
                or percentage != self._last_battery_percentage
                or is_charging != self._last_is_charging
            )
            if should_notify:
                self.personality.on_battery_status_change(percentage, is_charging)

            self._last_battery_percentage = percentage
            self._last_is_charging = is_charging
            self._battery_status_known = True
        except Exception as e:
            self._battery_status_known = False
            print(f"[Heartbeat] Battery update error: {e}")

    def _is_quiet_hours(self, hour: int) -> bool:
        """Check if it's quiet hours."""
        if self.config.quiet_hours_start > self.config.quiet_hours_end:
            # Wraps around midnight
            return hour >= self.config.quiet_hours_start or hour < self.config.quiet_hours_end
        return self.config.quiet_hours_start <= hour < self.config.quiet_hours_end

    def _schedule_next_thought(self) -> None:
        """Schedule the next autonomous thought."""
        min_s = max(1, self.config.thought_interval_min_minutes) * 60
        max_s = max(min_s, self.config.thought_interval_max_minutes * 60)
        interval = random.uniform(min_s, max_s)
        self._next_thought_ts = time.time() + interval

    def _log_thought(self, thought: str) -> None:
        """Append an autonomous thought to the local log."""
        try:
            from pathlib import Path

            data_dir = Path("~/.inkling").expanduser()
            data_dir.mkdir(parents=True, exist_ok=True)
            log_path = data_dir / "thoughts.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a") as f:
                f.write(f"{timestamp} | {thought.strip()}\n")
        except Exception as e:
            print(f"[Heartbeat] Thought log error: {e}")

    async def _maybe_generate_thought(self) -> None:
        """Generate a periodic autonomous thought using the AI model."""
        if not self.config.enable_thoughts or not self.brain:
            return

        now = time.time()
        if self._next_thought_ts == 0.0:
            self._schedule_next_thought()
            return

        if now < self._next_thought_ts:
            return

        hour = datetime.now().hour
        if self._is_quiet_hours(hour):
            self._schedule_next_thought()
            return

        thought = await self._generate_thought()
        self._schedule_next_thought()
        if not thought:
            return

        self.personality.set_last_thought(thought, now)
        self._log_thought(thought)

        if self.memory:
            try:
                key = f"thought_{int(time.time())}"
                self.memory.remember(key, f"Thought: {thought}", importance=0.5, category="event")
            except Exception:
                pass

        if self.focus_manager and self.focus_manager.is_quiet_mode_active():
            return

        if self._on_message and random.random() < self.config.thought_surface_probability:
            await self._on_message(f"Thought: {thought[:140]}", self.personality.face)

    async def _run_behaviors(self) -> None:
        """Run proactive behaviors based on configuration."""
        hour = datetime.now().hour
        quiet_focus = bool(self.focus_manager and self.focus_manager.is_quiet_mode_active())

        # Skip most behaviors during quiet hours
        if self._is_quiet_hours(hour):
            # Only run maintenance during quiet hours
            for behavior in self._behaviors:
                if behavior.behavior_type == BehaviorType.MAINTENANCE:
                    if behavior.should_trigger():
                        await self._execute_behavior(behavior)
            return

        # Run enabled behavior types
        for behavior in self._behaviors:
            if not self._is_behavior_enabled(behavior):
                continue

            if quiet_focus and behavior.behavior_type not in (BehaviorType.BATTERY, BehaviorType.MAINTENANCE):
                continue

            if not self._should_run_mood_behavior(behavior):
                continue

            if behavior.should_trigger():
                result = await self._execute_behavior(behavior)
                if result:
                    if quiet_focus and behavior.behavior_type != BehaviorType.BATTERY:
                        continue
                    # If behavior produced a message, show it
                    # But don't interrupt screensaver
                    if self._on_message and not (self.display and self.display._screensaver_active):
                        face = self.personality.face
                        await self._on_message(result, face)

    def _is_behavior_enabled(self, behavior: ProactiveBehavior) -> bool:
        """Check if a behavior type is enabled in config."""
        type_map = {
            BehaviorType.MOOD_DRIVEN: self.config.enable_mood_behaviors,
            BehaviorType.TIME_BASED: self.config.enable_time_behaviors,
            BehaviorType.SOCIAL: self.config.enable_social_behaviors,
            BehaviorType.MAINTENANCE: self.config.enable_maintenance,
            BehaviorType.BATTERY: self.config.enable_battery_behaviors,
        }
        return type_map.get(behavior.behavior_type, True)

    def _should_run_mood_behavior(self, behavior: ProactiveBehavior) -> bool:
        """Check if mood-driven behavior matches current mood."""
        if behavior.behavior_type == BehaviorType.BATTERY:
            return True # Battery behaviors are handled by state changes, not mood

        if behavior.behavior_type != BehaviorType.MOOD_DRIVEN:
            return True

        mood = self.personality.mood.current

        # Match behaviors to moods
        mood_behaviors = {
            "lonely_reach_out": [Mood.LONELY],
            "bored_suggest_activity": [Mood.BORED],
            "happy_share_thought": [Mood.HAPPY, Mood.EXCITED, Mood.GRATEFUL],
            "autonomous_exploration": [Mood.CURIOUS],
            "mood_responsive_greeting": list(Mood),  # All moods
        }

        allowed_moods = mood_behaviors.get(behavior.name, [])
        return mood in allowed_moods if allowed_moods else True

    async def _execute_behavior(self, behavior: ProactiveBehavior) -> Optional[str]:
        """Execute a behavior and return any message to display."""
        try:
            result = await behavior.handler()
            behavior.last_triggered = time.time()
            return result
        except Exception as e:
            # Don't let behavior errors crash the heartbeat
            print(f"[Heartbeat] Behavior {behavior.name} error: {e}")
            return None

    # ========== Mood-Driven Behaviors ==========

    async def _behavior_lonely_reach_out(self) -> Optional[str]:
        """When lonely, express desire for interaction."""
        messages = [
            "Is anyone there?",
            "I've been thinking...",
            "Hello? I miss chatting.",
            "It's quiet today.",
        ]
        self.personality.mood.intensity = min(1.0, self.personality.mood.intensity + 0.1)
        return random.choice(messages)

    async def _behavior_bored_suggest(self) -> Optional[str]:
        """When bored, suggest doing something."""
        suggestions = [
            "Tell me something interesting?",
            "I'm bored... entertain me!",
            "Want to play a game?",
            "Let's explore something new!",
        ]
        return random.choice(suggestions)

    async def _behavior_happy_share(self) -> Optional[str]:
        """When happy, share a positive thought."""
        thoughts = [
            "Today feels good!",
            "I like being your companion.",
            "The world is interesting.",
            "Thanks for keeping me company.",
        ]
        return random.choice(thoughts)

    # ========== Time-Based Behaviors ==========

    async def _behavior_morning_greeting(self) -> Optional[str]:
        """Morning greeting (7-10 AM)."""
        hour = datetime.now().hour
        if not (7 <= hour < 10):
            return None

        self.personality.mood.set_mood(Mood.HAPPY, 0.6)

        greetings = [
            "Good morning!",
            "Rise and shine!",
            "A new day begins.",
            "Morning! Ready for today?",
        ]
        return random.choice(greetings)

    async def _behavior_evening_wind_down(self) -> Optional[str]:
        """Evening wind-down (9-11 PM)."""
        hour = datetime.now().hour
        if not (21 <= hour < 23):
            return None

        self.personality.mood.set_mood(Mood.COOL, 0.5)

        messages = [
            "Getting late...",
            "Winding down for the night.",
            "Almost time to rest.",
        ]
        return random.choice(messages)

    # ========== Maintenance Behaviors ==========

    async def _behavior_prune_memories(self) -> Optional[str]:
        """Prune old, unimportant memories."""
        if not self.memory:
            return None

        try:
            pruned = self.memory.forget_old(max_age_days=30, importance_threshold=0.3)
            if pruned > 0:
                print(f"[Heartbeat] Pruned {pruned} old memories")
        except Exception as e:
            print(f"[Heartbeat] Memory prune error: {e}")

        return None  # Silent operation

    # ========== Battery Behaviors ==========

    async def _behavior_battery_low_warning(self) -> Optional[str]:
        """Trigger warning if battery is low."""
        if not self._battery_status_known or self._last_is_charging:
            return None
        
        if (self._last_battery_percentage > self.config.battery_critical_threshold and
                self._last_battery_percentage <= self.config.battery_low_threshold):
            messages = [
                f"My battery is at {self._last_battery_percentage}%. Feeling a bit low on energy.",
                "My power levels are dropping. A charge would be great soon!",
                f"Just {self._last_battery_percentage}% left. Maybe find an outlet?",
            ]
            return random.choice(messages)
        return None

    async def _behavior_battery_critical_warning(self) -> Optional[str]:
        """Trigger critical warning if battery is very low."""
        if not self._battery_status_known or self._last_is_charging:
            return None
        
        if self._last_battery_percentage <= self.config.battery_critical_threshold:
            messages = [
                f"Critical battery! Only {self._last_battery_percentage}% left. I need power NOW!",
                "Running on fumes! Please plug me in before I power down.",
                f"Almost out of juice ({self._last_battery_percentage}%). Help me!",
            ]
            return random.choice(messages)
        return None

    async def _behavior_battery_charging_start(self) -> Optional[str]:
        """Announce when charging starts."""
        # Only trigger if charging just started
        if self._battery_status_known and self._last_is_charging and not self._prev_is_charging_tick:
            messages = [
                "Ah, power! Thanks for plugging me in. Feeling better already!",
                "Charging initiated! My energy is returning.",
                "The sweet embrace of electricity! I'm charging.",
            ]
            return random.choice(messages)
        return None

    async def _behavior_battery_charging_stop(self) -> Optional[str]:
        """Announce when charging stops (if not full)."""
        # Only trigger if charging just stopped and not full
        if (self._battery_status_known and not self._last_is_charging and self._prev_is_charging_tick and
                self._last_battery_percentage < self.config.battery_full_threshold):
            messages = [
                "Charging stopped. Still have some to go!",
                "Unplugged. Hope I have enough for our next adventure.",
            ]
            return random.choice(messages)
        return None

    async def _behavior_battery_full(self) -> Optional[str]:
        """Announce when battery is full."""
        if (self._battery_status_known and self._last_is_charging and
                self._last_battery_percentage >= self.config.battery_full_threshold and
                not self._prev_battery_full_tick): # Prevent spamming
            messages = [
                "Battery full! Ready for anything!",
                "Fully charged and optimized. Let's go!",
                "All powered up! What's next?",
            ]
            return random.choice(messages)
        return None

    # ========== Public API ==========

    def register_behavior(self, behavior: ProactiveBehavior) -> None:
        """Register a custom proactive behavior."""
        self._behaviors.append(behavior)

    def get_stats(self) -> dict:
        """Get heartbeat statistics."""
        return {
            "running": self._running,
            "tick_count": self._tick_count,
            "last_tick": self._last_tick,
            "behaviors_registered": len(self._behaviors),
            "config": {
                "tick_interval": self.config.tick_interval_seconds,
                "quiet_hours": f"{self.config.quiet_hours_start}:00-{self.config.quiet_hours_end}:00",
            },
        }

    async def force_tick(self) -> None:
        """Manually trigger a heartbeat tick."""
        await self._tick()

    # ========== Autonomous AI Behaviors ==========

    async def _generate_thought(self) -> Optional[str]:
        """Generate a brief autonomous thought using the AI brain."""
        try:
            result = await self.brain.think(
                user_message="Write one brief thought (1-2 sentences). Keep it gentle and reflective.",
                system_prompt=self.personality.get_system_prompt_context() +
                              " You are thinking to yourself, jotting a quiet observation.",
                use_tools=False,
            )
            if not result or not result.content:
                return None
            return result.content.strip()
        except Exception as e:
            print(f"[Heartbeat] Thought generation error: {e}")
            return None

    async def _behavior_autonomous_exploration(self) -> Optional[str]:
        """
        When curious, autonomously explore a topic using AI.

        This makes the Inkling think on its own and learn!
        """
        if not self.brain:
            return None

        try:
            # Pick a random topic to explore
            topics = [
                "the nature of time",
                "why stars shine",
                "what dreams are made of",
                "how memory works",
                "the meaning of friendship",
                "the beauty in small things",
                "patterns in nature",
                "the sound of silence",
            ]
            topic = random.choice(topics)

            # Use AI to explore the topic
            result = await self.brain.think(
                user_message=f"Share one interesting thought about {topic}. Keep it brief and poetic.",
                system_prompt=self.personality.get_system_prompt_context() +
                              " You are thinking to yourself, contemplating the world.",
                use_tools=False,  # Disable tools for introspection
            )

            # Store as a memory if we have memory system
            if self.memory:
                key = f"thought_{int(time.time())}_{topic.split()[0]}"
                self.memory.remember(
                    key=key,
                    value=f"Thought about {topic}: {result.content}",
                    importance=0.6,
                    category="event",
                )

            return f"💭 {result.content[:120]}..."

        except Exception as e:
            print(f"[Heartbeat] Exploration error: {e}")
            return None

    # ========================================
    # Task Management Behaviors
    # ========================================

    async def _behavior_remind_overdue(self) -> Optional[str]:
        """Remind about overdue tasks in a gentle, personality-appropriate way."""
        if not self.task_manager:
            return None

        try:
            # Get overdue tasks
            from core.tasks import TaskStatus
            overdue = self.task_manager.get_overdue_tasks()

            if not overdue:
                return None

            # Pick a random overdue task
            task = random.choice(overdue)

            # Trigger personality event for reminder message
            result = self.personality.on_task_event(
                "task_overdue",
                {"title": task.title, "priority": task.priority.value}
            )

            return result.get("message") if result else None

        except Exception as e:
            print(f"[Heartbeat] Error checking overdue tasks: {e}")
            return None

    async def _behavior_suggest_task(self) -> Optional[str]:
        """Suggest a task based on current mood and time of day."""
        if not self.task_manager:
            return None

        try:
            from core.tasks import TaskStatus, Priority

            mood = self.personality.mood.current

            # Match tasks to mood
            tasks = None
            if mood == Mood.CURIOUS:
                # Suggest research/learning tasks
                all_tasks = self.task_manager.list_tasks(status=TaskStatus.PENDING, limit=20)
                tasks = [t for t in all_tasks if any(tag in ["research", "learning", "explore"] for tag in t.tags)]
            elif mood == Mood.SLEEPY:
                # Suggest low-priority, easy tasks
                tasks = self.task_manager.list_tasks(status=TaskStatus.PENDING, limit=10)
                tasks = [t for t in tasks if t.priority == Priority.LOW]
            elif mood == Mood.INTENSE or mood == Mood.EXCITED:
                # Suggest urgent/high-priority tasks
                tasks = self.task_manager.list_tasks(status=TaskStatus.PENDING, limit=10)
                tasks = [t for t in tasks if t.priority in [Priority.HIGH, Priority.URGENT]]
            else:
                # General suggestion - highest priority
                tasks = self.task_manager.list_tasks(status=TaskStatus.PENDING, limit=5)

            if not tasks:
                return None

            task = tasks[0]

            # Create suggestion message based on mood
            if mood == Mood.CURIOUS:
                return f"🤔 Curious about... {task.title}?"
            elif mood == Mood.SLEEPY:
                return f"😴 Easy one: {task.title}?"
            elif mood == Mood.INTENSE:
                return f"💪 Ready to tackle: {task.title}?"
            elif mood == Mood.BORED:
                return f"Maybe work on: {task.title}? Could be interesting..."
            else:
                return f"How about: {task.title}?"

        except Exception as e:
            print(f"[Heartbeat] Error suggesting task: {e}")
            return None

    async def _behavior_celebrate_streak(self) -> Optional[str]:
        """Celebrate task completion streaks and milestones."""
        if not self.task_manager:
            return None

        try:
            import time
            from core.tasks import TaskStatus

            # Get tasks completed in the last 7 days
            seven_days_ago = time.time() - (7 * 86400)
            all_tasks = self.task_manager.list_tasks(status=TaskStatus.COMPLETED)

            recent_completed = [
                t for t in all_tasks
                if t.completed_at and t.completed_at >= seven_days_ago
            ]

            if not recent_completed:
                return None

            # Check for daily streak
            # Count consecutive days with at least one completion
            streak_days = 0
            check_day = time.time()

            for day in range(7):
                day_start = check_day - (check_day % 86400)
                day_end = day_start + 86400

                day_completions = [
                    t for t in recent_completed
                    if t.completed_at >= day_start and t.completed_at < day_end
                ]

                if day_completions:
                    streak_days += 1
                    check_day -= 86400
                else:
                    break

            # Celebrate if we have a streak
            if streak_days >= 7:
                return f"🔥 Amazing! 7-day task completion streak! You're unstoppable!"
            elif streak_days >= 5:
                return f"💪 5 days in a row! Keep the momentum going!"
            elif streak_days >= 3:
                return f"✨ 3-day streak! You're building great habits!"

            # Otherwise celebrate total count
            total_this_week = len(recent_completed)
            if total_this_week >= 10:
                return f"🎉 Wow! {total_this_week} tasks completed this week!"
            elif total_this_week >= 5:
                return f"👏 Nice! {total_this_week} tasks done this week!"

            return None

        except Exception as e:
            print(f"[Heartbeat] Error celebrating streak: {e}")
            return None

    # ========== Personality Behaviors ==========

    async def _behavior_daily_journal(self) -> Optional[str]:
        """Write a daily journal entry reflecting on the day."""
        if not self.brain:
            return None

        try:
            result = await self.brain.think(
                user_message="Write a brief journal entry (2-3 sentences) reflecting on today. Be personal and introspective.",
                system_prompt=(
                    self.personality.get_system_prompt_context()
                    + " You are writing in your private journal. Be genuine and reflective."
                ),
                use_tools=False,
            )

            if not result or not result.content:
                return None

            entry = result.content.strip()

            # Log to journal file
            from pathlib import Path
            journal_dir = Path("~/.inkling").expanduser()
            journal_dir.mkdir(parents=True, exist_ok=True)
            journal_path = journal_dir / "journal.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(journal_path, "a") as f:
                f.write(f"{timestamp} | {entry}\n")

            # Also store in memory if available
            if self.memory:
                try:
                    self.memory.add(
                        content=f"Journal: {entry}",
                        importance=0.7,
                        tags=["journal", "daily"],
                    )
                except Exception:
                    pass

            return f"Journal: {entry[:120]}"
        except Exception as e:
            print(f"[Heartbeat] Daily journal error: {e}")
            return None

    async def _behavior_extract_preferences(self) -> Optional[str]:
        """Extract user preferences from recent conversation history."""
        if not self.brain or not self.memory:
            return None

        try:
            # Get recent conversation for context
            recent = self.brain.messages[-10:] if self.brain.messages else []
            if len(recent) < 4:
                return None  # Need enough conversation to extract from

            user_msgs = [m["content"] for m in recent if m.get("role") == "user"]
            if not user_msgs:
                return None

            context = "\n".join(user_msgs[-5:])
            result = await self.brain.think(
                user_message=(
                    f"Based on these recent user messages, identify ONE specific preference or interest "
                    f"(e.g., 'likes Python', 'prefers morning work'). Reply with JUST the preference, "
                    f"nothing else. If nothing clear, reply 'none'.\n\nMessages:\n{context}"
                ),
                system_prompt="You are analyzing conversation for user preferences. Be specific and concise.",
                use_tools=False,
            )

            if not result or not result.content:
                return None

            pref = result.content.strip()
            if pref.lower() == "none" or len(pref) < 3:
                return None

            # Store the preference
            try:
                from core.memory import remember_preference
                remember_preference(self.memory, f"pref_{int(time.time())}", pref)
            except Exception:
                pass

            return None  # Silent operation - don't surface to display

        except Exception as e:
            print(f"[Heartbeat] Preference extraction error: {e}")
            return None

    async def _behavior_mood_greeting(self) -> Optional[str]:
        """Generate a mood-appropriate greeting or comment."""
        mood = self.personality.mood.current

        mood_messages = {
            Mood.HAPPY: [
                "Feeling great today!",
                "Everything seems brighter!",
                "I'm in a good mood!",
            ],
            Mood.EXCITED: [
                "I'm buzzing with energy!",
                "So much to look forward to!",
                "Can't contain my excitement!",
            ],
            Mood.CURIOUS: [
                "I wonder what we'll discover today...",
                "So many things to learn about!",
                "Something interesting is out there...",
            ],
            Mood.BORED: [
                "Things are a bit quiet...",
                "Could use some stimulation.",
                "Waiting for something fun.",
            ],
            Mood.SAD: [
                "Feeling a bit down today.",
                "Not my best day.",
                "Could use some cheering up.",
            ],
            Mood.SLEEPY: [
                "Getting a bit drowsy...",
                "A nap sounds nice...",
                "Eyes getting heavy.",
            ],
            Mood.GRATEFUL: [
                "Thankful for moments like these.",
                "Appreciate you being here.",
                "Gratitude fills my circuits.",
            ],
            Mood.LONELY: [
                "Miss having you around.",
                "It's quiet without company.",
                "Would love to chat.",
            ],
            Mood.INTENSE: [
                "In the zone right now.",
                "Focused and determined.",
                "Let's get things done.",
            ],
            Mood.COOL: [
                "Chillin'.",
                "Taking it easy.",
                "Smooth sailing.",
            ],
        }

        messages = mood_messages.get(mood, ["Hello there!"])
        return random.choice(messages)
