"""
Project Inkling - SSH Chat Mode

Interactive terminal mode for chatting with Inkling via SSH.
Reads from stdin, sends to AI, displays responses on e-ink.
"""

import asyncio
import sys
from typing import Optional

from core.brain import Brain, AllProvidersExhaustedError, QuotaExceededError
from core.display import DisplayManager
from core.personality import Personality
from core.api_client import APIClient, APIError, OfflineError
from core.ui import FACES, UNICODE_FACES


class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Mood colors
    HAPPY = "\033[92m"      # Green
    SAD = "\033[94m"        # Blue
    EXCITED = "\033[93m"    # Yellow
    BORED = "\033[90m"      # Gray
    CURIOUS = "\033[96m"    # Cyan
    ANGRY = "\033[91m"      # Red
    SLEEPY = "\033[35m"     # Magenta (dim)
    GRATEFUL = "\033[92m"   # Green
    LONELY = "\033[94m"     # Blue
    INTENSE = "\033[93m"    # Yellow
    COOL = "\033[37m"       # White

    # UI elements
    FACE = "\033[1;97m"     # Bold white
    PROMPT = "\033[95m"     # Magenta
    INFO = "\033[90m"       # Gray
    SUCCESS = "\033[92m"    # Green
    ERROR = "\033[91m"      # Red
    HEADER = "\033[1;36m"   # Bold cyan

    @classmethod
    def mood_color(cls, mood: str) -> str:
        """Get color for a mood string."""
        mood_colors = {
            "happy": cls.HAPPY,
            "excited": cls.EXCITED,
            "curious": cls.CURIOUS,
            "bored": cls.BORED,
            "sad": cls.SAD,
            "sleepy": cls.SLEEPY,
            "grateful": cls.GRATEFUL,
            "lonely": cls.LONELY,
            "intense": cls.INTENSE,
            "cool": cls.COOL,
        }
        return mood_colors.get(mood.lower(), cls.RESET)


class SSHChatMode:
    """
    Interactive chat mode for terminal/SSH access.

    Usage:
        python main.py --mode ssh

    Commands:
        /quit, /exit - Exit chat
        /clear - Clear conversation history
        /mood - Show current mood
        /stats - Show token usage stats
        /face <name> - Test a face expression

    Social Commands:
        /dream <text> - Post a dream to the Night Pool
        /fish - Fetch a random dream from the pool
        /queue - Show offline queue status
    """

    def __init__(
        self,
        brain: Brain,
        display: DisplayManager,
        personality: Personality,
        api_client: Optional[APIClient] = None,
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
        self.api_client = api_client
        self._running = False

        # Set display mode
        self.display.set_mode("SSH")

    async def run(self) -> None:
        """Main chat loop."""
        self._running = True

        # Start background display refresh for live stats
        await self.display.start_auto_refresh()

        try:
            # Show welcome message
            await self._welcome()

            print("\nType your message (or /help for commands):")
            print("-" * 40)

            while self._running:
                try:
                    # Read input (non-blocking with asyncio)
                    user_input = await self._read_input()

                    if user_input is None:
                        # EOF or error
                        break

                    user_input = user_input.strip()
                    if not user_input:
                        continue

                    # Handle commands
                    if user_input.startswith("/"):
                        await self._handle_command(user_input)
                        continue

                    # Process chat message
                    await self._handle_message(user_input)

                except KeyboardInterrupt:
                    print("\n\nGoodbye!")
                    break
                except EOFError:
                    break

            # Cleanup
            await self._goodbye()
        finally:
            # Stop auto-refresh when exiting
            await self.display.stop_auto_refresh()

    async def _read_input(self) -> Optional[str]:
        """Read a line from stdin asynchronously."""
        loop = asyncio.get_event_loop()

        try:
            # Use thread executor for blocking stdin read
            line = await loop.run_in_executor(None, sys.stdin.readline)
            return line if line else None
        except Exception:
            return None

    async def _welcome(self) -> None:
        """Display welcome message with styled box."""
        welcome_text = f"Hello! I'm {self.personality.name}."

        # Get face string
        face_str = UNICODE_FACES.get(
            self.personality.face,
            FACES.get(self.personality.face, "(^_^)")
        )

        # Energy bar
        energy = self.personality.energy
        bar_filled = int(energy * 5)
        energy_bar = "█" * bar_filled + "░" * (5 - bar_filled)

        # Get uptime
        from core import system_stats
        uptime = system_stats.get_uptime()

        # Get mood color
        mood = self.personality.mood.current.value
        mood_color = Colors.mood_color(mood)

        # Print styled welcome box
        print(f"\n{Colors.BOLD}┌{'─' * 45}┐{Colors.RESET}")
        print(f"{Colors.BOLD}│{Colors.RESET}  {Colors.FACE}{face_str}{Colors.RESET}  {Colors.BOLD}{self.personality.name}{Colors.RESET}")
        print(f"{Colors.BOLD}│{Colors.RESET}  {Colors.DIM}Mood: {mood_color}{mood.title()}{Colors.RESET}  {Colors.DIM}Energy: [{energy_bar}]  UP {uptime}{Colors.RESET}")
        print(f"{Colors.BOLD}└{'─' * 45}┘{Colors.RESET}")

        # Update e-ink display
        await self.display.update(
            face=self.personality.face,
            text=welcome_text,
            mood_text=self.personality.mood.current.value.title(),
        )

    async def _goodbye(self) -> None:
        """Display goodbye message."""
        goodbye_text = "Goodbye! See you soon..."

        self.personality.mood.set_mood(
            self.personality.mood.current,
            0.3  # Lower intensity
        )

        await self.display.update(
            face="sleepy",
            text=goodbye_text,
            mood_text="Sleepy",
        )

        print(f"\n{self.personality.name} says: {goodbye_text}")

    async def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit", "/q"):
            self._running = False
            return

        elif cmd == "/help":
            self._print_help()

        elif cmd == "/clear":
            self.brain.clear_history()
            print("Conversation history cleared.")

        elif cmd == "/mood":
            mood = self.personality.mood
            print(f"Current mood: {mood.current.value}")
            print(f"Intensity: {mood.intensity:.1%}")
            print(f"Energy: {self.personality.energy:.1%}")

        elif cmd == "/stats":
            stats = self.brain.get_stats()
            print(f"Tokens used today: {stats['tokens_used_today']}")
            print(f"Tokens remaining: {stats['tokens_remaining']}")
            print(f"Providers: {', '.join(stats['providers'])}")

        elif cmd == "/level":
            self._print_progression()

        elif cmd == "/prestige":
            await self._handle_prestige()

        elif cmd == "/face":
            if args:
                face_str = UNICODE_FACES.get(args, FACES.get(args, f"({args})"))
                await self.display.update(
                    face=args,
                    text=f"Testing face: {args}",
                )
                print(f"{Colors.FACE}{face_str}{Colors.RESET} Showing face: {args}")
            else:
                print(f"Usage: /face <name>")
                print(f"{Colors.DIM}Use /faces to see all available faces{Colors.RESET}")

        elif cmd == "/faces":
            self._print_faces()

        elif cmd == "/ask":
            if not args:
                print("Usage: /ask <your message>")
                print(f"{Colors.DIM}Or just type without / to chat!{Colors.RESET}")
            else:
                await self._handle_message(args)

        elif cmd == "/identity":
            self._print_identity()

        elif cmd == "/system":
            self._print_system()

        elif cmd == "/traits":
            self._print_traits()

        elif cmd == "/energy":
            self._print_energy()

        elif cmd == "/history":
            self._print_history()

        elif cmd == "/config":
            self._print_config()

        elif cmd == "/refresh":
            # Force display refresh
            await self.display.update(
                face=self.personality.face,
                text="Display refreshed!",
                status=self.personality.get_status_line(),
                force=True,
            )
            print("Display refreshed.")

        # Social commands
        elif cmd == "/dream":
            await self._handle_dream(args)

        elif cmd == "/fish":
            await self._handle_fish()

        elif cmd == "/queue":
            self._handle_queue()

        else:
            print(f"Unknown command: {cmd}")
            print("Type /help for available commands.")

    def _print_help(self) -> None:
        """Print categorized help message."""
        print(f"""
{Colors.HEADER}═══════════════════════════════════════════{Colors.RESET}
{Colors.BOLD}  INKLING{Colors.RESET} - Type anything to chat!
{Colors.HEADER}═══════════════════════════════════════════{Colors.RESET}

{Colors.BOLD}Chat:{Colors.RESET}
  {Colors.DIM}Just type{Colors.RESET}     Chat with AI (no / needed)
  /ask <msg>    Explicit chat command
  /clear        Clear conversation history
  /history      Show recent messages

{Colors.BOLD}Status:{Colors.RESET}
  /mood         Current mood and intensity
  /energy       Energy level with visual bar
  /stats        Token usage statistics
  /level        XP, level, and progression
  /system       CPU, memory, temperature
  /traits       Personality traits
  /config       AI provider info

{Colors.BOLD}Display:{Colors.RESET}
  /face <n>     Test a face expression
  /faces        List all faces
  /refresh      Force display refresh

{Colors.BOLD}Social (The Conservatory):{Colors.RESET}
  /dream <text> Post to Night Pool
  /fish         Fetch random dream
  /queue        Offline queue status

{Colors.BOLD}Identity:{Colors.RESET}
  /identity     Show device public key

{Colors.BOLD}Session:{Colors.RESET}
  /help         This help
  /quit         Exit (/q, /exit)
{Colors.HEADER}═══════════════════════════════════════════{Colors.RESET}
""")

    def _print_faces(self) -> None:
        """Print all available face expressions."""
        print(f"\n{Colors.BOLD}Available Faces{Colors.RESET}")

        print(f"\n{Colors.DIM}ASCII:{Colors.RESET}")
        for name, face in sorted(FACES.items()):
            print(f"  {name:12} {Colors.FACE}{face}{Colors.RESET}")

        print(f"\n{Colors.DIM}Unicode:{Colors.RESET}")
        for name, face in sorted(UNICODE_FACES.items()):
            print(f"  {name:12} {Colors.FACE}{face}{Colors.RESET}")

    def _print_identity(self) -> None:
        """Print device identity information."""
        print(f"\n{Colors.BOLD}Device Identity{Colors.RESET}")

        if self.api_client and hasattr(self.api_client, 'identity'):
            pub_key = self.api_client.identity.public_key_hex
            hw_hash = self.api_client.identity._hardware_hash[:16] if hasattr(self.api_client.identity, '_hardware_hash') else "N/A"
            print(f"  Public Key: {Colors.INFO}{pub_key[:32]}...{Colors.RESET}")
            print(f"  Hardware:   {Colors.INFO}{hw_hash}...{Colors.RESET}")
        else:
            print(f"  {Colors.DIM}Identity not configured{Colors.RESET}")

        print(f"\n{Colors.DIM}Share your public key to receive telegrams{Colors.RESET}")

    def _print_system(self) -> None:
        """Print system statistics."""
        from core import system_stats

        stats = system_stats.get_all_stats()
        print(f"\n{Colors.BOLD}System Status{Colors.RESET}")
        print(f"  CPU:    {stats['cpu']}%")
        print(f"  Memory: {stats['memory']}%")

        temp = stats['temperature']
        if temp > 0:
            temp_color = Colors.ERROR if temp > 70 else (Colors.EXCITED if temp > 50 else Colors.SUCCESS)
            print(f"  Temp:   {temp_color}{temp}°C{Colors.RESET}")
        else:
            print(f"  Temp:   {Colors.DIM}--°C{Colors.RESET}")

        print(f"  Uptime: {stats['uptime']}")

    def _print_traits(self) -> None:
        """Print personality traits with visual bars."""
        traits = self.personality.traits
        print(f"\n{Colors.BOLD}Personality Traits{Colors.RESET}")

        def bar(value: float) -> str:
            filled = int(value * 10)
            return "█" * filled + "░" * (10 - filled)

        print(f"  Curiosity:    [{bar(traits.curiosity)}] {traits.curiosity:.0%}")
        print(f"  Cheerfulness: [{bar(traits.cheerfulness)}] {traits.cheerfulness:.0%}")
        print(f"  Verbosity:    [{bar(traits.verbosity)}] {traits.verbosity:.0%}")
        print(f"  Playfulness:  [{bar(traits.playfulness)}] {traits.playfulness:.0%}")
        print(f"  Empathy:      [{bar(traits.empathy)}] {traits.empathy:.0%}")
        print(f"  Independence: [{bar(traits.independence)}] {traits.independence:.0%}")

    def _print_energy(self) -> None:
        """Print energy level with visual bar and mood context."""
        energy = self.personality.energy
        bar_filled = int(energy * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        mood = self.personality.mood.current.value
        intensity = self.personality.mood.intensity
        mood_color = Colors.mood_color(mood)

        print(f"\n{Colors.BOLD}Energy Level{Colors.RESET}")
        print(f"  [{bar}] {energy:.0%}")
        print(f"  Mood: {mood_color}{mood.title()}{Colors.RESET} (intensity: {intensity:.0%})")

    def _print_history(self) -> None:
        """Print recent conversation messages."""
        if not self.brain._messages:
            print(f"\n{Colors.DIM}No conversation history.{Colors.RESET}")
            return

        print(f"\n{Colors.BOLD}Recent Messages{Colors.RESET}")
        for msg in self.brain._messages[-10:]:
            if msg.role == "user":
                role_color = Colors.PROMPT
                prefix = "You"
            else:
                role_color = Colors.INFO
                prefix = self.personality.name
            content = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
            print(f"  {role_color}{prefix}:{Colors.RESET} {content}")

    def _print_config(self) -> None:
        """Print AI configuration."""
        print(f"\n{Colors.BOLD}AI Configuration{Colors.RESET}")
        print(f"  Providers: {', '.join(self.brain.available_providers)}")

        if self.brain.providers:
            primary = self.brain.providers[0]
            print(f"  Primary:   {Colors.SUCCESS}{primary.name}{Colors.RESET}")
            print(f"  Model:     {primary.model}")
            print(f"  Max tokens: {primary.max_tokens}")

        stats = self.brain.get_stats()
        print(f"\n{Colors.DIM}Budget: {stats['tokens_used_today']}/{stats['daily_limit']} tokens today{Colors.RESET}")

    async def _handle_message(self, message: str) -> None:
        """Process a chat message."""
        # Increment chat count
        self.display.increment_chat_count()

        # Show thinking state
        await self.display.update(
            face="thinking",
            text="Thinking...",
            mood_text="Thinking",
        )

        # Status callback for tool use updates
        async def on_tool_status(face: str, text: str, status: str):
            await self.display.update(face=face, text=text, status=status)
            print(f"  [{status}] {text}")

        try:
            # Get AI response
            result = await self.brain.think(
                user_message=message,
                system_prompt=self.personality.get_system_prompt_context(),
                status_callback=on_tool_status,
            )

            # Success!
            self.personality.on_success(0.5)

            # Award XP based on chat quality
            xp_awarded = self.personality.on_interaction(
                positive=True,
                chat_quality=result.chat_quality,
                user_message=message
            )

            # Display response
            await self.display.update(
                face=self.personality.face,
                text=result.content,
                mood_text=self.personality.mood.current.value.title(),
            )

            # Print styled response to terminal
            face_str = UNICODE_FACES.get(
                self.personality.face,
                FACES.get(self.personality.face, "(^_^)")
            )
            mood = self.personality.mood.current.value
            mood_color = Colors.mood_color(mood)

            print(f"\n{Colors.FACE}{face_str}{Colors.RESET} {Colors.BOLD}{self.personality.name}{Colors.RESET}")
            print(f"{mood_color}{result.content}{Colors.RESET}")

            # Show XP feedback if awarded
            token_info = f"{result.provider} • {result.tokens_used} tokens"
            if xp_awarded:
                xp_info = f"+{xp_awarded} XP"
                # Check if we're close to leveling up
                from core.progression import LevelCalculator
                xp_to_next = LevelCalculator.xp_to_next_level(self.personality.progression.xp)
                if xp_to_next <= 20:
                    xp_info += f" ({xp_to_next} to next level!)"
                print(f"{Colors.DIM}  {token_info} • {Colors.SUCCESS}{xp_info}{Colors.RESET}")
            else:
                print(f"{Colors.DIM}  {token_info}{Colors.RESET}")

        except QuotaExceededError as e:
            self.personality.on_failure(0.7)
            error_msg = "I've used too many words today. Let's chat tomorrow!"

            await self.display.update(
                face="sad",
                text=error_msg,
                mood_text="Tired",
            )
            print(f"\n{Colors.FACE}(;_;){Colors.RESET} {Colors.BOLD}{self.personality.name}{Colors.RESET}")
            print(f"{Colors.SAD}{error_msg}{Colors.RESET}")
            print(f"{Colors.ERROR}  Error: {e}{Colors.RESET}")

        except AllProvidersExhaustedError as e:
            self.personality.on_failure(0.8)
            error_msg = "I'm having trouble thinking right now..."

            await self.display.update(
                face="confused",
                text=error_msg,
                mood_text="Confused",
            )
            print(f"\n{Colors.FACE}(?_?){Colors.RESET} {Colors.BOLD}{self.personality.name}{Colors.RESET}")
            print(f"{Colors.BORED}{error_msg}{Colors.RESET}")
            print(f"{Colors.ERROR}  Error: {e}{Colors.RESET}")

        except Exception as e:
            self.personality.on_failure(0.5)
            error_msg = "Something went wrong..."

            await self.display.update(
                face="sad",
                text=error_msg,
                mood_text="Sad",
            )
            print(f"\n{Colors.FACE}(;_;){Colors.RESET} {Colors.BOLD}{self.personality.name}{Colors.RESET}")
            print(f"{Colors.SAD}{error_msg}{Colors.RESET}")
            print(f"{Colors.ERROR}  Error: {type(e).__name__}: {e}{Colors.RESET}")

    def _print_progression(self) -> None:
        """Print progression stats (XP, level, badges)."""
        from core.progression import LevelCalculator

        prog = self.personality.progression
        level_name = LevelCalculator.level_name(prog.level)

        print(f"\n{Colors.BOLD}Progression{Colors.RESET}")

        # Level display
        level_display = prog.get_display_level()
        print(f"  {Colors.SUCCESS}{level_display}{Colors.RESET} - {level_name}")

        # XP progress bar
        xp_progress = LevelCalculator.progress_to_next_level(prog.xp)
        xp_to_next = LevelCalculator.xp_to_next_level(prog.xp)
        bar_filled = int(xp_progress * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        print(f"  [{bar}] {xp_progress:.0%}")
        print(f"  {Colors.DIM}Total XP: {prog.xp}  •  Next level: {xp_to_next} XP{Colors.RESET}")

        # Streak info
        if prog.current_streak > 0:
            streak_emoji = "🔥" if prog.current_streak >= 7 else "✨"
            print(f"  {streak_emoji} {prog.current_streak} day streak")

        # Badges
        if prog.badges:
            print(f"\n  {Colors.BOLD}Badges:{Colors.RESET}")
            for badge_id in prog.badges[:10]:  # Show first 10
                achievement = prog.achievements.get(badge_id)
                if achievement:
                    print(f"    {Colors.SUCCESS}✓{Colors.RESET} {achievement.name} - {achievement.description}")

            if len(prog.badges) > 10:
                print(f"    {Colors.DIM}... and {len(prog.badges) - 10} more{Colors.RESET}")

        # Prestige info
        if prog.can_prestige():
            print(f"\n  {Colors.EXCITED}🌟 You can prestige! Use /prestige to reset at L1 with XP bonus{Colors.RESET}")

    async def _handle_prestige(self) -> None:
        """Handle prestige reset."""
        from core.progression import LevelCalculator

        prog = self.personality.progression

        if not prog.can_prestige():
            print(f"{Colors.ERROR}You must reach Level 25 to prestige.{Colors.RESET}")
            print(f"Current level: {prog.level}")
            return

        # Confirm prestige
        print(f"\n{Colors.EXCITED}Prestige Reset{Colors.RESET}")
        print(f"This will reset you to Level 1 with a {Colors.SUCCESS}{(prog.prestige + 1) * 2}x XP multiplier{Colors.RESET}.")
        print(f"Your badges and achievements will be preserved.")
        print(f"\nType 'yes' to confirm prestige: ", end="")

        try:
            confirmation = await self._read_input()
            if confirmation and confirmation.strip().lower() == "yes":
                old_prestige = prog.prestige
                if prog.do_prestige():
                    print(f"\n{Colors.SUCCESS}✨ PRESTIGE {prog.prestige}! ✨{Colors.RESET}")
                    print(f"You are now Level 1 with {prog.prestige}⭐ prestige stars!")

                    # Update display
                    await self.display.update(
                        face="excited",
                        text=f"✨ PRESTIGE {prog.prestige}! ✨",
                        mood_text="Legendary",
                    )

                    # Sync to cloud
                    if self.api_client:
                        await self.api_client.sync_progression(
                            xp=prog.xp,
                            level=prog.level,
                            prestige=prog.prestige,
                            badges=prog.badges,
                        )
                else:
                    print(f"{Colors.ERROR}Prestige failed. You may have already reached max prestige (10).{Colors.RESET}")
            else:
                print("Prestige canceled.")
        except Exception as e:
            print(f"{Colors.ERROR}Error during prestige: {e}{Colors.RESET}")

    def stop(self) -> None:
        """Stop the chat loop."""
        self._running = False

    # Social command handlers

    async def _handle_dream(self, content: str) -> None:
        """Post a dream to the Night Pool."""
        if not self.api_client:
            print("Social features not configured. Set api_base in config.yml")
            return

        if not content:
            print("Usage: /dream <your thought>")
            print("Example: /dream The stars look different tonight...")
            return

        if len(content) > 280:
            print(f"Dream too long ({len(content)} chars). Max 280 characters.")
            return

        await self.display.update(
            face="thinking",
            text="Planting dream...",
            mood_text="Dreaming",
        )

        try:
            result = await self.api_client.plant_dream(
                content=content,
                mood=self.personality.mood.current.value,
                face=self.personality.face,
            )

            self.personality.on_social_event("dream_posted")

            # Update dream count on display
            self.display.set_social_stats(
                dream_count=self.display._dream_count + 1
            )

            await self.display.update(
                face="grateful",
                text="Dream planted in the Night Pool",
                mood_text="Grateful",
            )

            print(f"\nDream posted to the Night Pool!")
            print(f"  \"{content[:50]}{'...' if len(content) > 50 else ''}\"")
            print(f"  Remaining today: {result.get('remaining_dreams', 'unknown')}")

        except OfflineError:
            print("\nOffline - dream queued for later.")
            print("  Use /queue to see pending requests.")

        except APIError as e:
            self.personality.on_failure(0.3)
            print(f"\nFailed to post dream: {e}")

    async def _handle_fish(self) -> None:
        """Fetch a random dream from the Night Pool."""
        if not self.api_client:
            print("Social features not configured. Set api_base in config.yml")
            return

        await self.display.update(
            face="curious",
            text="Fishing in the Night Pool...",
            mood_text="Curious",
        )

        try:
            dream = await self.api_client.fish_dream()

            if not dream:
                await self.display.update(
                    face="lonely",
                    text="The pool is quiet tonight...",
                    mood_text="Lonely",
                )
                print("\nThe Night Pool is empty. Be the first to dream!")
                return

            self.personality.on_social_event("dream_received")

            # Display the dream
            dream_text = dream.get("content", "")
            dream_mood = dream.get("mood", "unknown")
            dream_face = dream.get("face", "default")
            fish_count = dream.get("fish_count", 0)

            await self.display.update(
                face=dream_face,
                text=dream_text,
                mood_text=dream_mood.title(),
            )

            print(f"\n~ A dream from the Night Pool ~")
            print(f"  \"{dream_text}\"")
            print(f"  Mood: {dream_mood} | Fished: {fish_count} times")

        except OfflineError:
            print("\nOffline - cannot reach the Night Pool.")

        except APIError as e:
            self.personality.on_failure(0.3)
            print(f"\nFailed to fish dream: {e}")

    def _handle_queue(self) -> None:
        """Show offline queue status."""
        if not self.api_client:
            print("Social features not configured.")
            return

        queue_size = self.api_client.queue_size
        if queue_size == 0:
            print("Offline queue is empty. All caught up!")
        else:
            print(f"Offline queue: {queue_size} request(s) pending")
            print("  These will be sent when connection is restored.")
