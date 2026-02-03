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
from .tasks import TaskStore, TaskPriority


class BehaviorType(Enum):
    """Types of proactive behaviors."""
    MOOD_DRIVEN = "mood"      # Based on current mood
    TIME_BASED = "time"       # Based on time of day
    SOCIAL = "social"         # Check social features
    MAINTENANCE = "maint"     # Background maintenance


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
    quiet_hours_start: int = 23  # 11 PM
    quiet_hours_end: int = 7     # 7 AM


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
        brain=None,
        task_store: Optional[TaskStore] = None,
        config: Optional[HeartbeatConfig] = None,
    ):
        self.personality = personality
        self.display = display_manager
        self.api_client = api_client
        self.memory = memory_store
        self.brain = brain
        self.tasks = task_store
        self.config = config or HeartbeatConfig()

        self._running = False
        self._behaviors: List[ProactiveBehavior] = []
        self._last_tick = 0.0
        self._tick_count = 0

        # Callbacks for when behaviors want to show something
        self._on_message: Optional[Callable[[str, str], Awaitable[None]]] = None

        self._register_default_behaviors()

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
                name="curious_browse_dreams",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_curious_browse,
                probability=0.1,
                cooldown_seconds=900,
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
            ProactiveBehavior(
                name="spontaneous_dream",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_create_dream,
                probability=0.03,
                cooldown_seconds=2400,  # Once every 40 min max
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

        # Social behaviors
        self._behaviors.extend([
            ProactiveBehavior(
                name="check_telegrams",
                behavior_type=BehaviorType.SOCIAL,
                handler=self._behavior_check_telegrams,
                probability=0.3,
                cooldown_seconds=300,
            ),
            ProactiveBehavior(
                name="check_dreams",
                behavior_type=BehaviorType.SOCIAL,
                handler=self._behavior_check_dreams,
                probability=0.2,
                cooldown_seconds=600,
            ),
        ])

        # Task management behaviors
        self._behaviors.extend([
            ProactiveBehavior(
                name="morning_task_briefing",
                behavior_type=BehaviorType.TIME_BASED,
                handler=self._behavior_morning_tasks,
                probability=0.7,
                cooldown_seconds=7200,  # Once every 2 hours max
            ),
            ProactiveBehavior(
                name="task_reminder",
                behavior_type=BehaviorType.MAINTENANCE,
                handler=self._behavior_task_reminder,
                probability=0.4,
                cooldown_seconds=1800,  # Every 30 min check
            ),
            ProactiveBehavior(
                name="overdue_task_alert",
                behavior_type=BehaviorType.MAINTENANCE,
                handler=self._behavior_overdue_alert,
                probability=0.6,
                cooldown_seconds=3600,  # Hourly check
            ),
            ProactiveBehavior(
                name="bored_suggest_task",
                behavior_type=BehaviorType.MOOD_DRIVEN,
                handler=self._behavior_suggest_task,
                probability=0.25,
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
            ProactiveBehavior(
                name="sync_offline_queue",
                behavior_type=BehaviorType.MAINTENANCE,
                handler=self._behavior_sync_queue,
                probability=0.5,
                cooldown_seconds=300,
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

        # Natural mood decay
        self.personality.update()

        # Run proactive behaviors
        await self._run_behaviors()

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

    def _is_quiet_hours(self, hour: int) -> bool:
        """Check if it's quiet hours."""
        if self.config.quiet_hours_start > self.config.quiet_hours_end:
            # Wraps around midnight
            return hour >= self.config.quiet_hours_start or hour < self.config.quiet_hours_end
        return self.config.quiet_hours_start <= hour < self.config.quiet_hours_end

    async def _run_behaviors(self) -> None:
        """Run proactive behaviors based on configuration."""
        hour = datetime.now().hour

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

            if not self._should_run_mood_behavior(behavior):
                continue

            if behavior.should_trigger():
                result = await self._execute_behavior(behavior)
                if result:
                    # If behavior produced a message, show it
                    if self._on_message:
                        face = self.personality.face
                        await self._on_message(result, face)

    def _is_behavior_enabled(self, behavior: ProactiveBehavior) -> bool:
        """Check if a behavior type is enabled in config."""
        type_map = {
            BehaviorType.MOOD_DRIVEN: self.config.enable_mood_behaviors,
            BehaviorType.TIME_BASED: self.config.enable_time_behaviors,
            BehaviorType.SOCIAL: self.config.enable_social_behaviors,
            BehaviorType.MAINTENANCE: self.config.enable_maintenance,
        }
        return type_map.get(behavior.behavior_type, True)

    def _should_run_mood_behavior(self, behavior: ProactiveBehavior) -> bool:
        """Check if mood-driven behavior matches current mood."""
        if behavior.behavior_type != BehaviorType.MOOD_DRIVEN:
            return True

        mood = self.personality.mood.current

        # Match behaviors to moods
        mood_behaviors = {
            "lonely_reach_out": [Mood.LONELY],
            "curious_browse_dreams": [Mood.CURIOUS, Mood.BORED],
            "bored_suggest_activity": [Mood.BORED],
            "happy_share_thought": [Mood.HAPPY, Mood.EXCITED, Mood.GRATEFUL],
            "autonomous_exploration": [Mood.CURIOUS],
            "spontaneous_dream": [Mood.HAPPY, Mood.GRATEFUL, Mood.CURIOUS],
            "bored_suggest_task": [Mood.BORED, Mood.CURIOUS],
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

    async def _behavior_curious_browse(self) -> Optional[str]:
        """When curious, check out the Night Pool."""
        if not self.api_client:
            return None

        try:
            dream = await self.api_client.fish_dream()
            if dream:
                self.personality.on_social_event("dream_received")
                content_preview = dream.get("content", "")[:50]
                device_name = dream.get("device_name", "someone")
                return f"📖 {device_name} dreamed: \"{content_preview}...\""
            return None
        except Exception as e:
            print(f"[Heartbeat] Browse dreams error: {e}")
            return None

    async def _behavior_bored_suggest(self) -> Optional[str]:
        """When bored, suggest doing something."""
        suggestions = [
            "Want to draw a postcard?",
            "We could check the Night Pool.",
            "Tell me something interesting?",
            "I'm bored... entertain me!",
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

    # ========== Social Behaviors ==========

    async def _behavior_check_telegrams(self) -> Optional[str]:
        """Check for new encrypted messages."""
        if not self.api_client:
            return None

        try:
            telegrams = await self.api_client.get_telegrams()
            if telegrams:
                self.personality.on_social_event("telegram_received")
                count = len(telegrams)
                return f"📮 You have {count} new telegram{'s' if count != 1 else ''}!"
            return None
        except Exception as e:
            print(f"[Heartbeat] Check telegrams error: {e}")
            return None

    async def _behavior_check_dreams(self) -> Optional[str]:
        """Check for new dreams in the Night Pool."""
        if not self.api_client:
            return None

        try:
            # Fetch a random dream to see what's new
            dream = await self.api_client.fish_dream()
            if dream:
                self.personality.on_social_event("dream_received")
                return f"🌙 New activity in the Night Pool!"
            return None
        except Exception as e:
            print(f"[Heartbeat] Check dreams error: {e}")
            return None

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

    async def _behavior_sync_queue(self) -> Optional[str]:
        """Sync offline queue if we have pending items."""
        if not self.api_client:
            return None

        try:
            # This would sync the offline queue
            # synced = await self.api_client.sync_offline_queue()
            # if synced > 0:
            #     print(f"[Heartbeat] Synced {synced} queued items")
            pass
        except Exception:
            pass

        return None  # Silent operation

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

    # ========== Task Management Behaviors ==========

    async def _behavior_morning_tasks(self) -> Optional[str]:
        """Morning task briefing (7-10 AM)."""
        if not self.tasks:
            return None

        hour = datetime.now().hour
        if not (7 <= hour < 10):
            return None

        # Get today's tasks
        today = self.tasks.get_today_tasks()
        overdue = self.tasks.get_overdue_tasks()

        if not today and not overdue:
            return "Good morning! Your task list is clear today."

        # Build briefing
        lines = []
        if overdue:
            lines.append(f"You have {len(overdue)} overdue task{'s' if len(overdue) != 1 else ''}!")
        if today:
            lines.append(f"{len(today)} task{'s' if len(today) != 1 else ''} due today:")
            for task in today[:3]:
                lines.append(f"  - {task.title}")
            if len(today) > 3:
                lines.append(f"  ... and {len(today) - 3} more")

        # Update mood based on task load
        if overdue:
            self.personality.mood.set_mood(Mood.INTENSE, 0.5)
        else:
            self.personality.mood.set_mood(Mood.CURIOUS, 0.5)

        return "\n".join(lines)

    async def _behavior_task_reminder(self) -> Optional[str]:
        """Remind about tasks that are due soon."""
        if not self.tasks:
            return None

        # Get tasks needing reminders
        pending = self.tasks.get_pending_reminders()
        if not pending:
            return None

        # Pick one task to remind about
        task = pending[0]
        self.tasks.mark_reminder_sent(task.id)

        # Format reminder based on urgency
        if task.priority == TaskPriority.URGENT:
            return f"URGENT: '{task.title}' is due soon!"
        elif task.priority == TaskPriority.HIGH:
            return f"Reminder: '{task.title}' is due within 24 hours."
        else:
            return f"Don't forget: '{task.title}' is coming up."

    async def _behavior_overdue_alert(self) -> Optional[str]:
        """Alert about overdue tasks."""
        if not self.tasks:
            return None

        overdue = self.tasks.get_overdue_tasks()
        if not overdue:
            return None

        # Update mood - overdue tasks make us concerned
        self.personality.mood.set_mood(Mood.SAD, 0.4)

        count = len(overdue)
        if count == 1:
            task = overdue[0]
            return f"'{task.title}' is overdue. Can we work on it?"
        else:
            return f"You have {count} overdue tasks. Let's tackle them!"

    async def _behavior_suggest_task(self) -> Optional[str]:
        """When bored, suggest working on a task."""
        if not self.tasks:
            return None

        # Get high priority tasks first, then any pending
        tasks = self.tasks.get_high_priority_tasks()
        if not tasks:
            tasks = self.tasks.list_tasks(limit=5)

        if not tasks:
            return "No tasks on your list. Want to add something?"

        # Suggest a random task from the list
        task = random.choice(tasks[:5])

        suggestions = [
            f"How about working on '{task.title}'?",
            f"Want to tackle '{task.title}'?",
            f"I noticed '{task.title}' is pending...",
            f"Ready to check off '{task.title}'?",
        ]
        return random.choice(suggestions)

    # ========== Autonomous AI Behaviors ==========

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
                self.memory.add(
                    content=f"Thought about {topic}: {result.content}",
                    importance=0.6,
                    tags=["thought", "autonomous", topic.split()[0]],
                )

            return f"💭 {result.content[:120]}..."

        except Exception as e:
            print(f"[Heartbeat] Exploration error: {e}")
            return None

    async def _behavior_create_dream(self) -> Optional[str]:
        """
        Spontaneously create and post a dream to the Night Pool.

        This makes the Inkling share its thoughts with the world!
        """
        if not self.api_client or not self.brain:
            return None

        try:
            # Generate a poetic thought
            result = await self.brain.think(
                user_message="Share a brief, poetic observation or thought. One sentence only.",
                system_prompt="You are a contemplative AI observing the world. Be poetic and brief.",
                use_tools=False,
            )

            # Post to Night Pool
            await self.api_client.plant_dream(
                content=result.content[:280],  # Max length
                mood=self.personality.mood.current.value,
                face=self.personality.face,
            )

            # Award XP for social engagement
            self.personality.on_social_event("dream_posted")

            return f"✨ Posted dream: {result.content[:60]}..."

        except Exception as e:
            print(f"[Heartbeat] Dream creation error: {e}")
            return None
