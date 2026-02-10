"""
Project Inkling - SSH Chat Mode

Interactive terminal mode for chatting with Inkling via SSH.
Reads from stdin, sends to AI, displays responses on e-ink.
"""

import asyncio
import inspect
import sys
import time
from typing import Optional

from core.brain import Brain, AllProvidersExhaustedError, QuotaExceededError
from core.display import DisplayManager
from core.personality import Personality, Mood
from core.ui import FACES, UNICODE_FACES
from core.commands import COMMANDS, get_command, get_commands_by_category
from core.tasks import TaskManager, Task, TaskStatus, Priority
from core.memory import MemoryStore
from core.focus import FocusManager
from core.progression import XPSource
from core.shell_utils import run_bash_command


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
    EMOTE = "\033[3;35m"    # Italic magenta for emotes

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
    """

    def __init__(
        self,
        brain: Brain,
        display: DisplayManager,
        personality: Personality,
        task_manager: Optional[TaskManager] = None,
        memory_store: Optional[MemoryStore] = None,
        focus_manager: Optional[FocusManager] = None,
        scheduler=None,
        config: Optional[dict] = None,
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
        self.task_manager = task_manager
        self.memory_store = memory_store
        self.focus_manager = focus_manager
        self.scheduler = scheduler
        self._running = False
        self._config = config or {}
        self._allow_bash = self._config.get("ble", {}).get("allow_bash", True)
        self._bash_timeout_seconds = self._config.get("ble", {}).get("command_timeout_seconds", 8)
        self._bash_max_output_bytes = self._config.get("ble", {}).get("max_output_bytes", 8192)

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

    async def _handle_command(self, command: str) -> bool:
        """Handle slash commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Handle quit commands (not in registry)
        if cmd in ("/quit", "/exit", "/q"):
            self._running = False
            return True

        # Look up command in registry
        cmd_obj = get_command(cmd)
        if not cmd_obj:
            print(f"Unknown command: {cmd}")
            print("Type /help for available commands.")
            return False

        # Check requirements
        if cmd_obj.requires_brain and not self.brain:
            print("This command requires AI features to be enabled.")
            return False

        # Get handler method
        handler = getattr(self, cmd_obj.handler, None)
        if not handler:
            print(f"Command handler not implemented: {cmd_obj.handler}")
            return False

        # Call handler with args if needed (auto-detect using inspect)
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())

        # Check if handler has an 'args' parameter (after 'self')
        # and if it doesn't have a default value
        needs_args = False
        if len(params) > 1:  # Has params beyond 'self'
            second_param = params[1]
            if second_param.name == "args" and second_param.default == inspect.Parameter.empty:
                needs_args = True

        if needs_args:
            await handler(args)
        else:
            await handler()
        return True

    async def cmd_help(self) -> None:
        """Print categorized help message."""
        categories = get_commands_by_category()

        print(f"""
{Colors.HEADER}═══════════════════════════════════════════{Colors.RESET}
{Colors.BOLD}  INKLING{Colors.RESET} - Type anything to chat!
{Colors.HEADER}═══════════════════════════════════════════{Colors.RESET}
""")

        # Display commands by category (skip social in SSH mode)
        category_titles = {
            "session": "Session",
            "info": "Status & Info",
            "personality": "Personality",
            "play": "Play & Energy",
            "tasks": "Task Management",
            "system": "System",
            "display": "Display",
        }

        for cat_key in ["session", "info", "personality", "play", "tasks", "system", "display"]:
            if cat_key in categories:
                print(f"{Colors.BOLD}{category_titles.get(cat_key, cat_key.title())}:{Colors.RESET}")
                for cmd in categories[cat_key]:
                    usage = f"/{cmd.name}"
                    if cmd.name in ("face", "ask", "task", "done", "cancel", "delete", "schedule", "bash"):
                        usage += " <arg>"
                    print(f"  {usage:14} {cmd.description}")
                print()

        print(f"{Colors.BOLD}Special:{Colors.RESET}")
        print(f"  /quit         Exit chat (/q, /exit)")
        print(f"\n{Colors.DIM}Just type (no /) to chat with AI{Colors.RESET}")
        print(f"{Colors.HEADER}═══════════════════════════════════════════{Colors.RESET}")

    # Command handlers (called from registry)

    async def cmd_clear(self) -> None:
        """Clear conversation history."""
        self.brain.clear_history()
        print("Conversation history cleared.")

        # Update display to show idle face (clear any message text)
        if self.display:
            await self.display.update(
                face="happy",
                text="",  # Empty text - idle face will show
                force=True,
            )

    async def cmd_mood(self) -> None:
        """Show current mood."""
        mood = self.personality.mood
        print(f"Current mood: {mood.current.value}")
        print(f"Intensity: {mood.intensity:.1%}")
        print(f"Energy: {self.personality.energy:.1%}")

    async def cmd_stats(self) -> None:
        """Show token usage stats."""
        stats = self.brain.get_stats()
        print(f"Tokens used today: {stats['tokens_used_today']}")
        print(f"Tokens remaining: {stats['tokens_remaining']}")
        print(f"Providers: {', '.join(stats['providers'])}")

    async def cmd_level(self) -> None:
        """Show level and progression."""
        self._print_progression()

    async def cmd_prestige(self) -> None:
        """Handle prestige reset."""
        await self._handle_prestige()

    async def cmd_bash(self, args: str = "") -> None:
        """Run a shell command."""
        if not self._allow_bash:
            print("bash is disabled.")
            return
        if not args:
            print("Usage: /bash <command>")
            return

        try:
            exit_code, output = run_bash_command(
                args,
                timeout_seconds=self._bash_timeout_seconds,
                max_output_bytes=self._bash_max_output_bytes,
            )
        except Exception as exc:
            print(f"Error: {exc}")
            return

        if output:
            print(output.rstrip("\n"))
        print(f"[exit {exit_code}]")

    async def cmd_face(self, args: str = "") -> None:
        """Test a face expression."""
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

    async def cmd_faces(self) -> None:
        """List all available faces."""
        self._print_faces()

    async def cmd_ask(self, args: str = "") -> None:
        """Explicit chat command."""
        if not args:
            print("Usage: /ask <your message>")
            print(f"{Colors.DIM}Or just type without / to chat!{Colors.RESET}")
        else:
            await self._handle_message(args)

    async def cmd_system(self) -> None:
        """Show system stats."""
        self._print_system()

    async def cmd_traits(self) -> None:
        """Show personality traits."""
        self._print_traits()

    async def cmd_energy(self) -> None:
        """Show energy level."""
        self._print_energy()

    async def cmd_history(self) -> None:
        """Show conversation history."""
        self._print_history()

    async def cmd_config(self) -> None:
        """Show AI config."""
        self._print_config()

    async def cmd_refresh(self) -> None:
        """Force display refresh."""
        await self.display.update(
            face=self.personality.face,
            text="Display refreshed!",
            status=self.personality.get_status_line(),
            force=True,
        )
        print("Display refreshed.")

    async def cmd_screensaver(self, args: str = "") -> None:
        """Toggle screen saver."""
        if args.lower() == "on":
            self.display.configure_screensaver(enabled=True)
            print("✓ Screen saver enabled")
        elif args.lower() == "off":
            self.display.configure_screensaver(enabled=False)
            if self.display._screensaver_active:
                await self.display.stop_screensaver()
            print("✓ Screen saver disabled")
        else:
            # Toggle
            current = self.display._screensaver_enabled
            self.display.configure_screensaver(enabled=not current)
            status = "enabled" if not current else "disabled"
            print(f"✓ Screen saver {status}")

    async def cmd_darkmode(self, args: str = "") -> None:
        """Toggle dark mode."""
        if args.lower() == "on":
            self.display._dark_mode = True
            await self.display.update(force=True)
            print("✓ Dark mode enabled")
        elif args.lower() == "off":
            self.display._dark_mode = False
            await self.display.update(force=True)
            print("✓ Dark mode disabled")
        else:
            # Toggle
            self.display._dark_mode = not self.display._dark_mode
            await self.display.update(force=True)
            status = "enabled" if self.display._dark_mode else "disabled"
            print(f"✓ Dark mode {status}")

    # Helper methods for printing info

    def _print_faces(self) -> None:
        """Print all available face expressions."""
        print(f"\n{Colors.BOLD}Available Faces{Colors.RESET}")

        print(f"\n{Colors.DIM}ASCII:{Colors.RESET}")
        for name, face in sorted(FACES.items()):
            print(f"  {name:12} {Colors.FACE}{face}{Colors.RESET}")

        print(f"\n{Colors.DIM}Unicode:{Colors.RESET}")
        for name, face in sorted(UNICODE_FACES.items()):
            print(f"  {name:12} {Colors.FACE}{face}{Colors.RESET}")

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
        print(f"  Mood base energy: {self.personality.mood.current.energy:.0%}")
        print()
        print(f"{Colors.DIM}Tip: Play commands (/walk, /dance, /exercise) boost energy!{Colors.RESET}")

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

    async def _handle_message(self, message: str) -> bool:
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

            # Display response (with pagination for long messages)
            # Check if message needs pagination (> MESSAGE_MAX_LINES)
            from core.ui import word_wrap, MESSAGE_MAX_LINES
            # Use 32 chars/line to better match pixel-based rendering (250px display ~32-35 chars)
            lines = word_wrap(result.content, 32)
            if len(lines) > MESSAGE_MAX_LINES:
                # Use paginated display for long responses
                pages = await self.display.show_message_paginated(
                    text=result.content,
                    face=self.personality.face,
                    page_delay=self.display.pagination_loop_seconds,
                    loop=True,
                )
                print(f"{Colors.DIM}  (Displayed {pages} pages on e-ink){Colors.RESET}")
            else:
                # Single page display
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
            return True

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
            return False

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
            return False

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
            return False

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

    # ========================================
    # Task Management Commands
    # ========================================

    async def cmd_tasks(self, args: str = "") -> None:
        """List tasks with optional filters."""
        if not self.task_manager:
            print("Task manager not available.")
            return

        # Parse arguments for filters
        status_filter = None
        project_filter = None

        if args:
            args_lower = args.lower()
            if "pending" in args_lower:
                status_filter = TaskStatus.PENDING
            elif "progress" in args_lower or "in-progress" in args_lower:
                status_filter = TaskStatus.IN_PROGRESS
            elif "done" in args_lower or "completed" in args_lower:
                status_filter = TaskStatus.COMPLETED

        # Get tasks
        tasks = self.task_manager.list_tasks(
            status=status_filter,
            project=project_filter
        )

        if not tasks:
            print(f"\n{Colors.INFO}No tasks found.{Colors.RESET}")
            if not status_filter:
                print("  Use '/task <title>' to create a new task!")
            return

        # Display tasks grouped by status
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]

        print(f"\n{Colors.HEADER}═══ TASKS ═══{Colors.RESET}\n")

        if pending:
            print(f"{Colors.BOLD}To Do ({len(pending)}):{Colors.RESET}")
            for task in pending[:10]:  # Limit to 10
                self._print_task_summary(task)
            print()

        if in_progress:
            print(f"{Colors.BOLD}In Progress ({len(in_progress)}):{Colors.RESET}")
            for task in in_progress[:10]:
                self._print_task_summary(task)
            print()

        if completed and not status_filter:
            print(f"{Colors.DIM}Completed today ({len(completed)}):{Colors.RESET}")
            # Show only today's completions
            import time
            today_start = time.time() - (time.time() % 86400)
            today_completed = [t for t in completed if t.completed_at and t.completed_at >= today_start]
            for task in today_completed[:5]:
                self._print_task_summary(task)

        print(f"\n{Colors.INFO}Use '/task <id>' to view details or '/done <id>' to complete{Colors.RESET}")

    def _print_task_summary(self, task: Task) -> None:
        """Print a one-line task summary."""
        # Priority indicator
        priority_icons = {
            Priority.LOW: "○",
            Priority.MEDIUM: "●",
            Priority.HIGH: f"{Colors.ERROR}●{Colors.RESET}",
            Priority.URGENT: f"{Colors.ERROR}‼{Colors.RESET}",
        }
        priority_icon = priority_icons.get(task.priority, "●")

        # Status indicator
        if task.status == TaskStatus.COMPLETED:
            status_icon = f"{Colors.SUCCESS}✓{Colors.RESET}"
        elif task.status == TaskStatus.IN_PROGRESS:
            status_icon = f"{Colors.EXCITED}⏳{Colors.RESET}"
        else:
            status_icon = "□"

        # Overdue indicator
        overdue = ""
        if task.is_overdue:
            overdue = f" {Colors.ERROR}[OVERDUE]{Colors.RESET}"

        # Tags
        tags_str = ""
        if task.tags:
            tags_str = f" {Colors.DIM}#{', #'.join(task.tags)}{Colors.RESET}"

        print(f"  {status_icon} {priority_icon} [{task.id[:8]}] {task.title}{overdue}{tags_str}")

    async def cmd_task(self, args: str = "") -> None:
        """Create or show a task."""
        if not self.task_manager:
            print("Task manager not available.")
            return

        if not args:
            print(f"{Colors.INFO}Usage:{Colors.RESET}")
            print("  /task <title>           - Create a new task")
            print("  /task <id>              - Show task details")
            print("  /task <title> !high     - Create high-priority task")
            print("  /task <title> #tag      - Create task with tag")
            return

        # Check if it's a task ID (8 or 36 characters UUID)
        if len(args) in [8, 36] and "-" in args or args.count("-") >= 3:
            # Show task details
            task = self.task_manager.get_task(args)
            if not task:
                # Try to find by partial ID
                all_tasks = self.task_manager.list_tasks()
                matching = [t for t in all_tasks if t.id.startswith(args)]
                if len(matching) == 1:
                    task = matching[0]
                elif len(matching) > 1:
                    print(f"{Colors.ERROR}Multiple tasks match '{args}'. Be more specific:{Colors.RESET}")
                    for t in matching[:5]:
                        print(f"  {t.id[:16]} - {t.title}")
                    return
                else:
                    print(f"{Colors.ERROR}Task not found: {args}{Colors.RESET}")
                    return

            self._print_task_details(task)
            return

        # Create new task - parse priority and tags
        title = args
        priority = Priority.MEDIUM
        tags = []

        # Extract priority markers
        if "!urgent" in args.lower() or "!!" in args:
            priority = Priority.URGENT
            title = title.replace("!urgent", "").replace("!!", "").strip()
        elif "!high" in args.lower() or "!" in args:
            priority = Priority.HIGH
            title = title.replace("!high", "").replace("!", "").strip()
        elif "!low" in args.lower():
            priority = Priority.LOW
            title = title.replace("!low", "").strip()

        # Extract tags (#tag)
        import re
        tag_matches = re.findall(r'#(\w+)', title)
        tags.extend(tag_matches)
        title = re.sub(r'#\w+', '', title).strip()

        if not title:
            print(f"{Colors.ERROR}Task title cannot be empty{Colors.RESET}")
            return

        # Create task
        task = self.task_manager.create_task(
            title=title,
            priority=priority,
            mood=self.personality.mood.current.value,
            tags=tags
        )

        # Trigger personality event
        result = self.personality.on_task_event(
            "task_created",
            {"priority": task.priority.value, "title": task.title}
        )

        # Update display
        await self.display.update(
            face=self.personality.face,
            text=result.get('message', 'Task created!') if result else 'Task created!',
            mood_text=self.personality.mood.current.value.title()
        )

        # Print confirmation
        print(f"\n{Colors.SUCCESS}✓ Task created!{Colors.RESET}")
        self._print_task_details(task)

        if result and result.get('xp_awarded'):
            print(f"{Colors.EXCITED}+{result['xp_awarded']} XP{Colors.RESET}")

    def _print_task_details(self, task: Task) -> None:
        """Print detailed task information."""
        print(f"\n{Colors.HEADER}═══ TASK DETAILS ═══{Colors.RESET}")
        print(f"ID:       {task.id}")
        print(f"Title:    {Colors.BOLD}{task.title}{Colors.RESET}")

        if task.description:
            print(f"Details:  {task.description}")

        print(f"Status:   {task.status.value}")
        print(f"Priority: {task.priority.value}")

        if task.due_date:
            from datetime import datetime
            due_str = datetime.fromtimestamp(task.due_date).strftime("%Y-%m-%d %H:%M")
            days_until = task.days_until_due
            if task.is_overdue:
                print(f"Due:      {Colors.ERROR}{due_str} (OVERDUE by {abs(days_until)} days){Colors.RESET}")
            elif days_until is not None and days_until <= 3:
                print(f"Due:      {Colors.EXCITED}{due_str} ({days_until} days){Colors.RESET}")
            else:
                print(f"Due:      {due_str}")

        if task.tags:
            print(f"Tags:     #{', #'.join(task.tags)}")

        if task.project:
            print(f"Project:  {task.project}")

        if task.subtasks:
            print(f"Subtasks: {sum(task.subtasks_completed)}/{len(task.subtasks)} complete")
            for i, subtask in enumerate(task.subtasks):
                status = "✓" if task.subtasks_completed[i] else "□"
                print(f"  {status} {subtask}")

        from datetime import datetime
        created = datetime.fromtimestamp(task.created_at).strftime("%Y-%m-%d %H:%M")
        print(f"Created:  {created}")

        if task.completed_at:
            completed = datetime.fromtimestamp(task.completed_at).strftime("%Y-%m-%d %H:%M")
            print(f"Completed: {completed}")

    async def cmd_done(self, args: str = "") -> None:
        """Mark a task as complete."""
        if not self.task_manager:
            print("Task manager not available.")
            return

        if not args:
            print(f"{Colors.INFO}Usage: /done <task_id>{Colors.RESET}")
            print("  Use '/tasks' to see task IDs")
            return

        # Find task
        task = self.task_manager.get_task(args)
        if not task:
            # Try partial match
            all_tasks = self.task_manager.list_tasks()
            matching = [t for t in all_tasks if t.id.startswith(args)]
            if len(matching) == 1:
                task = matching[0]
            elif len(matching) > 1:
                print(f"{Colors.ERROR}Multiple tasks match. Be more specific:{Colors.RESET}")
                for t in matching[:5]:
                    print(f"  {t.id[:16]} - {t.title}")
                return
            else:
                print(f"{Colors.ERROR}Task not found: {args}{Colors.RESET}")
                return

        if task.status == TaskStatus.COMPLETED:
            print(f"{Colors.INFO}Task already completed!{Colors.RESET}")
            return

        # Complete the task
        task = self.task_manager.complete_task(task.id)

        # Calculate if on-time
        was_on_time = (
            not task.due_date or
            task.completed_at <= task.due_date
        )

        # Trigger personality event
        result = self.personality.on_task_event(
            "task_completed",
            {
                "priority": task.priority.value,
                "title": task.title,
                "was_on_time": was_on_time
            }
        )

        # Update display
        celebration = result.get('message', 'Task completed!') if result else 'Task completed!'
        await self.display.update(
            face=self.personality.face,
            text=celebration,
            mood_text=self.personality.mood.current.value.title()
        )

        # Print celebration
        print(f"\n{Colors.SUCCESS}✓ {celebration}{Colors.RESET}")
        print(f"  {task.title}")

        if result and result.get('xp_awarded'):
            xp = result['xp_awarded']
            print(f"\n{Colors.EXCITED}+{xp} XP earned!{Colors.RESET}")

        # Show level up if it happened
        level = self.personality.progression.level
        xp_current = self.personality.progression.xp
        print(f"{Colors.DIM}Level {level} | {xp_current} XP{Colors.RESET}")

    async def cmd_cancel(self, args: str = "") -> None:
        """Cancel a task."""
        if not self.task_manager:
            print("Task manager not available.")
            return

        if not args:
            print(f"{Colors.INFO}Usage: /cancel <task_id>{Colors.RESET}")
            print("  Use '/tasks' to see task IDs")
            return

        # Find task
        task = self.task_manager.get_task(args)
        if not task:
            # Try partial match
            all_tasks = self.task_manager.list_tasks()
            matching = [t for t in all_tasks if t.id.startswith(args)]
            if len(matching) == 1:
                task = matching[0]
            elif len(matching) > 1:
                print(f"{Colors.ERROR}Multiple tasks match. Be more specific:{Colors.RESET}")
                for t in matching[:5]:
                    print(f"  {t.id[:16]} - {t.title}")
                return
            else:
                print(f"{Colors.ERROR}Task not found: {args}{Colors.RESET}")
                return

        if task.status == TaskStatus.CANCELLED:
            print(f"{Colors.INFO}Task already cancelled!{Colors.RESET}")
            return

        # Cancel the task
        task.status = TaskStatus.CANCELLED
        self.task_manager.update_task(task)

        print(f"\n{Colors.SUCCESS}✗ Task cancelled{Colors.RESET}")
        print(f"  {task.title}")

    async def cmd_delete(self, args: str = "") -> None:
        """Delete a task permanently."""
        if not self.task_manager:
            print("Task manager not available.")
            return

        if not args:
            print(f"{Colors.INFO}Usage: /delete <task_id>{Colors.RESET}")
            print("  Use '/tasks' to see task IDs")
            print(f"  {Colors.ERROR}WARNING: This permanently deletes the task!{Colors.RESET}")
            return

        # Find task
        task = self.task_manager.get_task(args)
        if not task:
            # Try partial match
            all_tasks = self.task_manager.list_tasks()
            matching = [t for t in all_tasks if t.id.startswith(args)]
            if len(matching) == 1:
                task = matching[0]
            elif len(matching) > 1:
                print(f"{Colors.ERROR}Multiple tasks match. Be more specific:{Colors.RESET}")
                for t in matching[:5]:
                    print(f"  {t.id[:16]} - {t.title}")
                return
            else:
                print(f"{Colors.ERROR}Task not found: {args}{Colors.RESET}")
                return

        # Delete the task
        success = self.task_manager.delete_task(task.id)

        if success:
            print(f"\n{Colors.SUCCESS}🗑 Task deleted permanently{Colors.RESET}")
            print(f"  {task.title}")
        else:
            print(f"{Colors.ERROR}Failed to delete task{Colors.RESET}")

    async def cmd_taskstats(self) -> None:
        """Show task statistics."""
        if not self.task_manager:
            print("Task manager not available.")
            return

        stats = self.task_manager.get_stats()

        print(f"\n{Colors.HEADER}═══ TASK STATISTICS ═══{Colors.RESET}\n")

        print(f"{Colors.BOLD}Overview:{Colors.RESET}")
        print(f"  Total tasks:     {stats['total']}")
        print(f"  Pending:         {stats['pending']}")
        print(f"  In Progress:     {stats['in_progress']}")
        print(f"  Completed:       {stats['completed']}")

        if stats['overdue'] > 0:
            print(f"  {Colors.ERROR}Overdue:         {stats['overdue']}{Colors.RESET}")

        if stats['due_soon'] > 0:
            print(f"  {Colors.EXCITED}Due soon (3d):   {stats['due_soon']}{Colors.RESET}")

        print(f"\n{Colors.BOLD}30-Day Performance:{Colors.RESET}")
        completion_rate = stats['completion_rate_30d'] * 100
        if completion_rate >= 80:
            color = Colors.SUCCESS
        elif completion_rate >= 50:
            color = Colors.EXCITED
        else:
            color = Colors.INFO
        print(f"  Completion rate: {color}{completion_rate:.0f}%{Colors.RESET}")

        # Show current streak if available
        level = self.personality.progression.level
        xp = self.personality.progression.xp
        print(f"\n{Colors.DIM}Level {level} | {xp} XP from tasks{Colors.RESET}")

    # Scheduler Commands
    # ================

    async def cmd_schedule(self, args: str = "") -> None:
        """Manage scheduled tasks."""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            print(f"{Colors.ERROR}Scheduler not available.{Colors.RESET}")
            print("Enable in config.yml under 'scheduler.enabled: true'")
            return

        if not args:
            # List all scheduled tasks
            tasks = self.scheduler.list_tasks()

            if not tasks:
                print(f"\n{Colors.INFO}No scheduled tasks configured.{Colors.RESET}")
                print("\nAdd tasks in config.yml under 'scheduler.tasks'")
                return

            print(f"\n{Colors.HEADER}═══ SCHEDULED TASKS ═══{Colors.RESET}\n")

            next_runs = self.scheduler.get_next_run_times()

            for task in tasks:
                status_icon = "✓" if task.enabled else "✗"
                status_color = Colors.SUCCESS if task.enabled else Colors.DIM

                print(f"{status_color}{status_icon} {task.name}{Colors.RESET}")
                print(f"   Schedule: {task.schedule_expr}")
                print(f"   Action:   {task.action}")

                if task.enabled:
                    next_run = next_runs.get(task.name, "Unknown")
                    print(f"   Next run: {Colors.INFO}{next_run}{Colors.RESET}")

                if task.last_run > 0:
                    import time
                    from datetime import datetime
                    last_run_dt = datetime.fromtimestamp(task.last_run)
                    print(f"   Last run: {last_run_dt.strftime('%Y-%m-%d %H:%M:%S')} ({task.run_count} times)")

                if task.last_error:
                    print(f"   {Colors.ERROR}Error: {task.last_error}{Colors.RESET}")

                print()

            return

        # Parse subcommands
        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()

        if subcmd == "list":
            # Redirect to list (same as no args)
            await self.cmd_schedule()

        elif subcmd == "enable":
            if len(parts) < 2:
                print(f"{Colors.ERROR}Usage: /schedule enable <task_name>{Colors.RESET}")
                return

            task_name = parts[1]
            if self.scheduler.enable_task(task_name):
                print(f"{Colors.SUCCESS}✓ Enabled: {task_name}{Colors.RESET}")
            else:
                print(f"{Colors.ERROR}Task not found: {task_name}{Colors.RESET}")

        elif subcmd == "disable":
            if len(parts) < 2:
                print(f"{Colors.ERROR}Usage: /schedule disable <task_name>{Colors.RESET}")
                return

            task_name = parts[1]
            if self.scheduler.disable_task(task_name):
                print(f"{Colors.SUCCESS}✓ Disabled: {task_name}{Colors.RESET}")
            else:
                print(f"{Colors.ERROR}Task not found: {task_name}{Colors.RESET}")

        else:
            print(f"{Colors.ERROR}Unknown subcommand: {subcmd}{Colors.RESET}")
            print("\nAvailable commands:")
            print("  /schedule           - List all scheduled tasks")
            print("  /schedule list      - List all scheduled tasks")
            print("  /schedule enable <name>  - Enable a task")
            print("  /schedule disable <name> - Disable a task")

    # ================
    # WiFi Commands
    # ================

    async def cmd_wifi(self) -> None:
        """Show WiFi status and saved networks."""
        from core.wifi_utils import get_current_wifi, get_saved_networks, is_btcfg_running, get_wifi_bars

        print(f"\n{Colors.HEADER}═══ WIFI STATUS ═══{Colors.RESET}\n")

        # Current connection status
        status = get_current_wifi()

        if status.connected and status.ssid:
            bars = get_wifi_bars(status.signal_strength)
            print(f"{Colors.SUCCESS}✓ Connected to: {status.ssid}{Colors.RESET}")
            print(f"  Signal: {bars} {status.signal_strength}%")

            if status.ip_address:
                print(f"  IP: {status.ip_address}")

            if status.frequency:
                print(f"  Band: {status.frequency}")
        else:
            print(f"{Colors.ERROR}✗ Not connected{Colors.RESET}")

        print()

        # BTBerryWifi service status
        if is_btcfg_running():
            print(f"{Colors.SUCCESS}🔵 BLE Configuration: Running (15 min window){Colors.RESET}")
            print(f"   Use BTBerryWifi app to configure WiFi")
        else:
            print(f"{Colors.DIM}🔵 BLE Configuration: Stopped{Colors.RESET}")
            print(f"   Use /btcfg to start configuration service")

        print()

        # Saved networks
        saved = get_saved_networks()
        if saved:
            print(f"{Colors.BOLD}Saved Networks ({len(saved)}):{Colors.RESET}")
            for ssid in saved:
                icon = "●" if status.connected and status.ssid == ssid else "○"
                print(f"  {icon} {ssid}")
        else:
            print(f"{Colors.DIM}No saved networks{Colors.RESET}")

        print()
        print(f"{Colors.DIM}Tip: Use /wifiscan to find nearby networks{Colors.RESET}")

    async def cmd_btcfg(self) -> None:
        """Start BTBerryWifi BLE configuration service."""
        from core.wifi_utils import start_btcfg

        print(f"\n{Colors.INFO}Starting BLE WiFi configuration...{Colors.RESET}\n")

        success, message = start_btcfg()

        if success:
            print(f"{Colors.SUCCESS}{message}{Colors.RESET}")
        else:
            print(f"{Colors.ERROR}{message}{Colors.RESET}")

    async def cmd_wifiscan(self) -> None:
        """Scan for nearby WiFi networks."""
        from core.wifi_utils import scan_networks, get_current_wifi

        print(f"\n{Colors.INFO}Scanning for WiFi networks...{Colors.RESET}\n")

        networks = scan_networks()
        current = get_current_wifi()

        if not networks:
            print(f"{Colors.ERROR}No networks found or permission denied{Colors.RESET}")
            print(f"\n{Colors.DIM}Tip: Scanning requires sudo access{Colors.RESET}")
            return

        print(f"{Colors.HEADER}═══ NEARBY NETWORKS ({len(networks)}) ═══{Colors.RESET}\n")

        for net in networks:
            # Visual signal indicator
            if net.signal_strength >= 80:
                signal_icon = "▂▄▆█"
                signal_color = Colors.SUCCESS
            elif net.signal_strength >= 60:
                signal_icon = "▂▄▆"
                signal_color = Colors.SUCCESS
            elif net.signal_strength >= 40:
                signal_icon = "▂▄"
                signal_color = Colors.EXCITED
            elif net.signal_strength >= 20:
                signal_icon = "▂"
                signal_color = Colors.ERROR
            else:
                signal_icon = "○"
                signal_color = Colors.DIM

            # Connection indicator
            connected = current.connected and current.ssid == net.ssid
            conn_icon = "●" if connected else " "

            # Security badge
            if net.security == "Open":
                security_badge = f"{Colors.ERROR}[OPEN]{Colors.RESET}"
            elif net.security == "WPA3":
                security_badge = f"{Colors.SUCCESS}[WPA3]{Colors.RESET}"
            elif net.security == "WPA2":
                security_badge = f"{Colors.INFO}[WPA2]{Colors.RESET}"
            else:
                security_badge = f"{Colors.DIM}[{net.security}]{Colors.RESET}"

            print(f"{conn_icon} {signal_color}{signal_icon}{Colors.RESET} {net.signal_strength:3}% {security_badge} {net.ssid}")

        print()
        print(f"{Colors.DIM}Use /btcfg to start BLE configuration service{Colors.RESET}")

    # ================
    # Play Commands
    # ================

    async def _play_action(
        self,
        action_name: str,
        emote_text: str,
        mood: Mood,
        intensity: float,
        xp_source: XPSource,
    ) -> None:
        """
        Execute a play action with emoji face animation and rewards.

        Args:
            action_name: Name of action (e.g., "walk")
            emote_text: SSH emote text (e.g., "goes for a walk...")
            mood: Target mood to set
            intensity: Mood intensity boost
            xp_source: XP source for reward
        """
        from core.ui import ACTION_FACE_SEQUENCES

        # Update interaction time (prevents boredom/sleepy)
        self.personality._last_interaction = time.time()

        # Print SSH emote
        print(f"{Colors.EMOTE}*{self.personality.name} {emote_text}*{Colors.RESET}")

        # Get emoji face sequence for this action
        face_sequence = ACTION_FACE_SEQUENCES.get(
            action_name,
            ["(^_^)", "(^_~)", "(^_^)"]  # Default fallback
        )

        # Show emoji animation on display (if available)
        # Display each emoji face from the sequence without text
        if self.display:
            for i, emoji_face in enumerate(face_sequence):
                is_last = (i == len(face_sequence) - 1)

                # Show just the emoji face (no text, so face won't hide)
                await self.display.update(
                    face="happy",
                    text="",  # Empty text - face will show
                    force=True,
                )

                # Manually render the action face by updating the UI
                if self.display._ui and self.display._ui.animated_face:
                    # Temporarily override to show action face
                    self.display._ui.animated_face._current_action_face = emoji_face

                if not is_last:
                    await asyncio.sleep(0.8)  # Animation delay between faces

            # Clear action face override when done
            if self.display._ui and self.display._ui.animated_face:
                self.display._ui.animated_face._current_action_face = None

        # Boost mood and intensity
        old_mood = self.personality.mood.current
        old_intensity = self.personality.mood.intensity
        self.personality.mood.set_mood(mood, intensity)

        # Award XP
        xp_amounts = {
            XPSource.PLAY_WALK: 3,
            XPSource.PLAY_DANCE: 5,
            XPSource.PLAY_EXERCISE: 5,
            XPSource.PLAY_GENERAL: 4,
            XPSource.PLAY_REST: 2,
            XPSource.PLAY_PET: 3,
        }
        awarded, xp_gained = self.personality.progression.award_xp(
            xp_source,
            xp_amounts.get(xp_source, 3)
        )

        # Show results
        old_energy = old_mood.energy * old_intensity
        new_energy = self.personality.energy
        energy_change = new_energy - old_energy

        if awarded:
            print(f"{Colors.SUCCESS}+{xp_gained} XP  Energy: {old_energy:.0%} → {new_energy:.0%} ({energy_change:+.0%}){Colors.RESET}")
        else:
            print(f"{Colors.DIM}Energy: {old_energy:.0%} → {new_energy:.0%} ({energy_change:+.0%}){Colors.RESET}")

    async def cmd_walk(self) -> None:
        """Go for a walk."""
        await self._play_action(
            action_name="walk",
            emote_text="goes for a walk around the neighborhood",
            mood=Mood.CURIOUS,
            intensity=0.7,
            xp_source=XPSource.PLAY_WALK,
        )

    async def cmd_dance(self) -> None:
        """Dance around."""
        await self._play_action(
            action_name="dance",
            emote_text="dances enthusiastically",
            mood=Mood.EXCITED,
            intensity=0.9,
            xp_source=XPSource.PLAY_DANCE,
        )

    async def cmd_exercise(self) -> None:
        """Exercise and stretch."""
        await self._play_action(
            action_name="exercise",
            emote_text="does some stretches and exercises",
            mood=Mood.HAPPY,
            intensity=0.8,
            xp_source=XPSource.PLAY_EXERCISE,
        )

    async def cmd_play(self) -> None:
        """Play with a toy."""
        await self._play_action(
            action_name="play",
            emote_text="plays with a toy",
            mood=Mood.HAPPY,
            intensity=0.8,
            xp_source=XPSource.PLAY_GENERAL,
        )

    async def cmd_pet(self) -> None:
        """Get petted."""
        await self._play_action(
            action_name="pet",
            emote_text="enjoys being petted",
            mood=Mood.GRATEFUL,
            intensity=0.7,
            xp_source=XPSource.PLAY_PET,
        )

    async def cmd_rest(self) -> None:
        """Take a short rest."""
        await self._play_action(
            action_name="rest",
            emote_text="takes a short rest",
            mood=Mood.COOL,
            intensity=0.4,
            xp_source=XPSource.PLAY_REST,
        )

    async def cmd_thoughts(self) -> None:
        """Show recent autonomous thoughts from the thought log."""
        from pathlib import Path

        log_path = Path("~/.inkling/thoughts.log").expanduser()
        if not log_path.exists():
            print(f"\n{Colors.DIM}No thoughts yet. Thoughts are generated automatically over time.{Colors.RESET}")
            return

        lines = log_path.read_text().strip().splitlines()
        recent = lines[-10:]  # Last 10 thoughts

        print(f"\n{Colors.HEADER}═══ RECENT THOUGHTS ({len(recent)} of {len(lines)}) ═══{Colors.RESET}\n")

        for line in recent:
            parts = line.split(" | ", 1)
            if len(parts) == 2:
                ts, thought = parts
                print(f"{Colors.DIM}{ts}{Colors.RESET}")
                print(f"  {thought}")
            else:
                print(f"  {line}")
            print()

        if self.personality.last_thought:
            print(f"{Colors.INFO}Latest: {self.personality.last_thought}{Colors.RESET}")

    async def cmd_find(self, args: str = "") -> None:
        """Search tasks by keyword."""
        if not args.strip():
            print(f"{Colors.ERROR}Usage: /find <keyword>{Colors.RESET}")
            return

        if not self.task_manager:
            print(f"{Colors.ERROR}Task manager not available.{Colors.RESET}")
            return

        query = args.strip().lower()
        all_tasks = self.task_manager.list_tasks()
        matches = [
            t for t in all_tasks
            if query in t.title.lower()
            or (t.description and query in t.description.lower())
            or any(query in tag.lower() for tag in t.tags)
        ]

        if not matches:
            print(f"\n{Colors.DIM}No tasks found matching '{args.strip()}'.{Colors.RESET}")
            return

        print(f"\n{Colors.HEADER}═══ SEARCH RESULTS ({len(matches)}) ═══{Colors.RESET}\n")

        for task in matches:
            status_icon = {"pending": "📋", "in_progress": "⏳", "completed": "✅", "cancelled": "❌"}.get(task.status.value, "·")
            priority_str = {"low": "", "medium": "◆", "high": "◆◆", "urgent": "🔥"}.get(task.priority.value, "")
            tags_str = " ".join(f"#{t}" for t in task.tags) if task.tags else ""
            print(f"  {status_icon} [{task.id[:8]}] {task.title} {priority_str}")
            if task.description:
                print(f"     {Colors.DIM}{task.description[:60]}{Colors.RESET}")
            if tags_str:
                print(f"     {Colors.INFO}{tags_str}{Colors.RESET}")
            print()

    async def cmd_memory(self) -> None:
        """Show memory stats and recent entries."""
        store = self.memory_store or MemoryStore()
        owns_store = self.memory_store is None
        try:
            if owns_store:
                store.initialize()

            total = store.count()
            user_count = store.count(MemoryStore.CATEGORY_USER)
            pref_count = store.count(MemoryStore.CATEGORY_PREFERENCE)
            fact_count = store.count(MemoryStore.CATEGORY_FACT)
            event_count = store.count(MemoryStore.CATEGORY_EVENT)

            print(f"\n{Colors.HEADER}═══ MEMORY STORE ═══{Colors.RESET}\n")
            print(f"  Total memories: {Colors.INFO}{total}{Colors.RESET}")
            print(f"  User info:      {user_count}")
            print(f"  Preferences:    {pref_count}")
            print(f"  Facts:          {fact_count}")
            print(f"  Events:         {event_count}")

            recent = store.recall_recent(limit=5)
            if recent:
                print(f"\n{Colors.HEADER}Recent memories:{Colors.RESET}")
                for mem in recent:
                    print(f"  {Colors.DIM}[{mem.category}]{Colors.RESET} {mem.key}: {mem.value[:60]}")

            important = store.recall_important(limit=3)
            if important:
                print(f"\n{Colors.HEADER}Most important:{Colors.RESET}")
                for mem in important:
                    print(f"  {Colors.INFO}★ {mem.importance:.1f}{Colors.RESET} [{mem.category}] {mem.key}: {mem.value[:60]}")

            print()
        finally:
            if owns_store:
                store.close()

    async def cmd_focus(self, args: str) -> None:
        """Manage focus/pomodoro sessions."""
        if not self.focus_manager or not self.focus_manager.is_enabled:
            print(f"{Colors.ERROR}Focus manager is not available.{Colors.RESET}")
            return

        parts = args.split() if args else []
        sub = parts[0].lower() if parts else "status"

        if sub == "start":
            minutes = None
            task_ref = None
            if len(parts) >= 2:
                try:
                    minutes = int(parts[1])
                except ValueError:
                    task_ref = " ".join(parts[1:])
            if len(parts) >= 3:
                task_ref = " ".join(parts[2:])

            task_id = None
            task_title = None
            if task_ref:
                task = self._resolve_task_ref(task_ref)
                if task:
                    task_id = task.id
                    task_title = task.title
                else:
                    print(f"{Colors.INFO}Task reference not found; starting unlinked focus session.{Colors.RESET}")

            result = self.focus_manager.start(minutes=minutes, task_id=task_id, task_title=task_title)
            if not result.get("ok"):
                print(f"{Colors.ERROR}{result.get('error', 'Could not start focus session')}{Colors.RESET}")
                status = result.get("status")
                if status:
                    self._print_focus_status(status)
                return
            status = result["status"]
            self._print_focus_status(status)
            await self.display.update(face="intense", text="Focus session started", mood_text="Intense")
            return

        if sub == "stop":
            result = self.focus_manager.stop(stopped_early=True)
            if not result.get("ok"):
                print(f"{Colors.ERROR}{result.get('error', 'No active session')}{Colors.RESET}")
            else:
                print(f"{Colors.SUCCESS}Focus session stopped.{Colors.RESET}")
                await self.display.update(face="cool", text="Focus session stopped", mood_text="Cool")
            return

        if sub == "pause":
            result = self.focus_manager.pause()
            if not result.get("ok"):
                print(f"{Colors.ERROR}{result.get('error', 'Unable to pause')}{Colors.RESET}")
            else:
                self._print_focus_status(result["status"])
            return

        if sub == "resume":
            result = self.focus_manager.resume()
            if not result.get("ok"):
                print(f"{Colors.ERROR}{result.get('error', 'Unable to resume')}{Colors.RESET}")
            else:
                self._print_focus_status(result["status"])
            return

        if sub == "break":
            result = self.focus_manager.start_break()
            if not result.get("ok"):
                print(f"{Colors.ERROR}{result.get('error', 'Unable to start break')}{Colors.RESET}")
            else:
                self._print_focus_status(result["status"])
            return

        if sub == "stats":
            stats = self.focus_manager.stats_today()
            print(f"\n{Colors.HEADER}═══ FOCUS TODAY ═══{Colors.RESET}")
            print(f"Sessions: {stats['sessions']}")
            print(f"Completed: {stats['completed_count']}")
            print(f"Total time: {stats['total_sec'] // 60}m")
            print(f"Work time: {stats['work_sec'] // 60}m")
            return

        if sub == "week":
            week = self.focus_manager.stats_week()
            print(f"\n{Colors.HEADER}═══ FOCUS WEEK ═══{Colors.RESET}")
            for day in week["days"]:
                print(f"{day['date']}: {day['sessions']} sessions ({day['total_sec'] // 60}m)")
            print(f"Total: {week['total_sessions']} sessions ({week['total_sec'] // 60}m)")
            return

        if sub == "config":
            cfg = self.focus_manager.config
            print(f"\n{Colors.HEADER}═══ FOCUS CONFIG ═══{Colors.RESET}")
            print(f"Work: {cfg.default_work_minutes}m")
            print(f"Short break: {cfg.short_break_minutes}m")
            print(f"Long break: {cfg.long_break_minutes}m")
            print(f"Long break cadence: every {cfg.sessions_until_long_break} sessions")
            print(f"Quiet mode: {'on' if cfg.quiet_mode_during_focus else 'off'}")
            return

        status = self.focus_manager.status()
        self._print_focus_status(status)

    def _print_focus_status(self, status: dict) -> None:
        if not status.get("active"):
            print(f"{Colors.INFO}No active focus session.{Colors.RESET}")
            return
        mm = int(status["remaining_sec"]) // 60
        ss = int(status["remaining_sec"]) % 60
        label = status.get("phase_label", "FOCUS")
        task = status.get("task_title")
        task_line = f" | Task: {task}" if task else ""
        pause_line = " [PAUSED]" if status.get("paused") else ""
        print(f"{Colors.SUCCESS}{label}{pause_line} {mm:02d}:{ss:02d}{task_line}{Colors.RESET}")

    def _resolve_task_ref(self, task_ref: str) -> Optional[Task]:
        if not self.task_manager:
            return None
        task = self.task_manager.get_task(task_ref)
        if task:
            return task
        ref = task_ref.lower()
        matches = [
            t for t in self.task_manager.list_tasks()
            if t.id.startswith(task_ref) or ref in t.title.lower()
        ]
        return matches[0] if len(matches) == 1 else None

    async def cmd_settings(self) -> None:
        """Show current settings."""
        import yaml

        print(f"\n{Colors.HEADER}═══ CURRENT SETTINGS ═══{Colors.RESET}\n")

        # AI config
        ai_config = self._config.get("ai", {})
        provider = ai_config.get("primary", "anthropic")
        model = ai_config.get(provider, {}).get("model", "unknown")
        budget = ai_config.get("budget", {})
        daily_tokens = budget.get("daily_tokens", 10000)
        per_request = budget.get("per_request_max", 500)

        print(f"  {Colors.HEADER}AI Provider:{Colors.RESET} {provider}")
        print(f"  {Colors.HEADER}Model:{Colors.RESET} {model}")
        print(f"  {Colors.HEADER}Daily token budget:{Colors.RESET} {daily_tokens}")
        print(f"  {Colors.HEADER}Per-request max:{Colors.RESET} {per_request}")

        # Personality
        traits = self.personality.traits
        print(f"\n  {Colors.HEADER}Personality Traits:{Colors.RESET}")
        for name, val in traits.to_dict().items():
            bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
            print(f"    {name:14s} [{bar}] {val:.1f}")

        # Heartbeat
        hb_config = self._config.get("heartbeat", {})
        print(f"\n  {Colors.HEADER}Heartbeat:{Colors.RESET} {'enabled' if hb_config.get('enabled', True) else 'disabled'}")
        print(f"    Tick interval:     {hb_config.get('tick_interval', 60)}s")
        print(f"    Mood behaviors:    {'on' if hb_config.get('enable_mood_behaviors', True) else 'off'}")
        print(f"    Time behaviors:    {'on' if hb_config.get('enable_time_behaviors', True) else 'off'}")
        print(f"    Quiet hours:       {hb_config.get('quiet_hours_start', 23)}:00 - {hb_config.get('quiet_hours_end', 7)}:00")

        # Device
        device_config = self._config.get("device", {})
        print(f"\n  {Colors.HEADER}Device:{Colors.RESET} {device_config.get('name', self.personality.name)}")
        print(f"  {Colors.HEADER}Display:{Colors.RESET} {self._config.get('display', {}).get('type', 'auto')}")
        print()

    async def cmd_backup(self) -> None:
        """Create a backup of Inkling data."""
        import shutil
        from pathlib import Path
        from datetime import datetime

        data_dir = Path("~/.inkling").expanduser()
        if not data_dir.exists():
            print(f"{Colors.ERROR}No data directory found at {data_dir}{Colors.RESET}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"inkling_backup_{timestamp}"
        backup_path = data_dir.parent / f"{backup_name}.tar.gz"

        print(f"\n{Colors.INFO}Creating backup...{Colors.RESET}")

        try:
            shutil.make_archive(
                str(data_dir.parent / backup_name),
                'gztar',
                root_dir=str(data_dir.parent),
                base_dir='.inkling'
            )
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            print(f"{Colors.SUCCESS}Backup created: {backup_path}{Colors.RESET}")
            print(f"  Size: {size_mb:.1f} MB")
        except Exception as e:
            print(f"{Colors.ERROR}Backup failed: {e}{Colors.RESET}")

    async def cmd_journal(self) -> None:
        """Show recent journal entries."""
        from pathlib import Path

        journal_path = Path("~/.inkling/journal.log").expanduser()
        if not journal_path.exists():
            print(f"\n{Colors.DIM}No journal entries yet. Journal entries are written daily by the heartbeat system.{Colors.RESET}")
            return

        lines = journal_path.read_text().strip().splitlines()
        recent = lines[-10:]

        print(f"\n{Colors.HEADER}═══ JOURNAL ({len(recent)} of {len(lines)} entries) ═══{Colors.RESET}\n")

        for line in recent:
            parts = line.split(" | ", 1)
            if len(parts) == 2:
                ts, entry = parts
                print(f"{Colors.DIM}{ts}{Colors.RESET}")
                print(f"  {entry}")
            else:
                print(f"  {line}")
            print()

    # ========================================
    # Crypto Watcher Commands
    # ========================================

    async def cmd_price(self, args: str = "") -> None:
        """Check cryptocurrency price."""
        if not args:
            print(f"{Colors.INFO}Usage: /price <symbol>{Colors.RESET}")
            print("  Example: /price BTC")
            return

        symbol = args.upper().strip()

        try:
            from core.crypto_watcher import CryptoWatcher

            async with CryptoWatcher() as watcher:
                price = await watcher.get_price(symbol)

                if not price:
                    print(f"{Colors.ERROR}Failed to fetch price for {symbol}{Colors.RESET}")
                    return

                # Format with color based on change
                if price.price_change_24h > 0:
                    change_color = Colors.SUCCESS
                else:
                    change_color = Colors.ERROR

                print(f"\n{Colors.HEADER}═══ {symbol} PRICE ═══{Colors.RESET}\n")
                print(f"  {watcher.format_price(price)}")
                print(f"  Volume 24h: ${price.volume_24h:,.0f}")
                if price.market_cap:
                    print(f"  Market Cap: ${price.market_cap:,.0f}")
                print(f"  Mood: {price.mood} {'🚀' if price.is_pumping else '💀' if price.is_dumping else '📊'}")
                print()

        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_chart(self, args: str = "") -> None:
        """Show TA indicators for a cryptocurrency."""
        if not args:
            print(f"{Colors.INFO}Usage: /chart <symbol> [timeframe]{Colors.RESET}")
            print("  Example: /chart BTC")
            print("  Example: /chart ETH 4h")
            return

        parts = args.upper().split()
        symbol = parts[0]
        timeframe = parts[1] if len(parts) > 1 else "1h"

        try:
            from core.crypto_watcher import CryptoWatcher
            from core.crypto_ta import CryptoTA

            print(f"\n{Colors.INFO}Fetching chart data for {symbol}...{Colors.RESET}")

            async with CryptoWatcher() as watcher:
                ohlcv = await watcher.get_ohlcv(symbol, timeframe, 100)

                if not ohlcv:
                    print(f"{Colors.ERROR}Failed to fetch chart data for {symbol}{Colors.RESET}")
                    return

                ta = CryptoTA()
                indicators = ta.calculate_indicators(ohlcv)
                patterns = ta.detect_patterns(ohlcv)
                supports, resistances = ta.get_support_resistance(ohlcv)

                signal = indicators.get_signal()

                print(f"\n{Colors.HEADER}═══ {symbol} TA ({timeframe}) ═══{Colors.RESET}\n")
                print(f"  {Colors.BOLD}Signal: {signal.crypto_bro_text} {signal.emoji}{Colors.RESET}\n")

                print(f"  {Colors.BOLD}Indicators:{Colors.RESET}")
                if indicators.rsi:
                    rsi_status = "oversold" if indicators.rsi < 30 else "overbought" if indicators.rsi > 70 else "neutral"
                    print(f"    RSI: {indicators.rsi:.1f} ({rsi_status})")
                if indicators.macd:
                    macd_trend = "bullish" if indicators.macd > indicators.macd_signal else "bearish"
                    print(f"    MACD: {macd_trend} ({indicators.macd:.2f})")
                if indicators.sma_20 and indicators.sma_50:
                    trend = "golden cross" if indicators.sma_20 > indicators.sma_50 else "death cross"
                    print(f"    Trend: {trend}")
                if indicators.atr:
                    print(f"    ATR: {indicators.atr:.2f} (volatility)")

                if patterns:
                    print(f"\n  {Colors.BOLD}Patterns:{Colors.RESET}")
                    for pattern in patterns:
                        print(f"    {pattern}")

                if supports and resistances:
                    print(f"\n  {Colors.BOLD}Levels:{Colors.RESET}")
                    print(f"    Support: {', '.join([f'${s:,.0f}' for s in supports[:3]])}")
                    print(f"    Resistance: {', '.join([f'${r:,.0f}' for r in resistances[:3]])}")

                print()

        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_watch(self) -> None:
        """Show watchlist with current prices."""
        try:
            from core.crypto_watcher import CryptoWatcher

            # Load watchlist from config or MCP storage
            config = self.config or {}
            crypto_config = config.get("crypto", {})
            watchlist = crypto_config.get("watchlist", ["BTC", "ETH", "SOL"])

            print(f"\n{Colors.HEADER}═══ WATCHLIST ═══{Colors.RESET}\n")
            print(f"{Colors.INFO}Fetching prices...{Colors.RESET}\n")

            async with CryptoWatcher() as watcher:
                prices = await watcher.get_multiple_prices(watchlist)

                if not prices:
                    print(f"{Colors.ERROR}Failed to fetch prices{Colors.RESET}")
                    return

                for symbol in watchlist:
                    if symbol in prices:
                        price = prices[symbol]
                        print(f"  {watcher.format_price(price)}")

                print()

        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_portfolio(self) -> None:
        """Show portfolio value and holdings."""
        try:
            from core.crypto_watcher import CryptoWatcher
            from pathlib import Path
            import json

            # Load portfolio from storage
            portfolio_file = Path.home() / ".inkling" / "crypto_portfolio.json"
            if not portfolio_file.exists():
                print(f"\n{Colors.INFO}Portfolio is empty. Use /add to add holdings.{Colors.RESET}")
                print(f"  Example: /add BTC 0.5")
                print()
                return

            with open(portfolio_file) as f:
                holdings = json.load(f)

            if not holdings:
                print(f"\n{Colors.INFO}Portfolio is empty. Use /add to add holdings.{Colors.RESET}")
                return

            print(f"\n{Colors.HEADER}═══ PORTFOLIO ═══{Colors.RESET}\n")
            print(f"{Colors.INFO}Calculating value...{Colors.RESET}\n")

            async with CryptoWatcher() as watcher:
                symbols = list(holdings.keys())
                prices = await watcher.get_multiple_prices(symbols)

                total_value = 0.0

                for symbol, amount in holdings.items():
                    if symbol in prices:
                        price = prices[symbol]
                        value = amount * price.price_usd
                        total_value += value

                        change_color = Colors.SUCCESS if price.price_change_24h > 0 else Colors.ERROR
                        emoji = "🚀" if price.price_change_24h > 5 else "📈" if price.price_change_24h > 0 else "📉" if price.price_change_24h > -5 else "💀"

                        print(f"  {symbol}: {amount} × ${price.price_usd:,.2f} = {change_color}${value:,.2f}{Colors.RESET} ({price.price_change_24h:+.1f}%) {emoji}")

                print(f"\n  {Colors.BOLD}💎 Total: ${total_value:,.2f}{Colors.RESET}")
                print()

        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_add(self, args: str = "") -> None:
        """Add coin to watchlist or portfolio."""
        if not args:
            print(f"{Colors.INFO}Usage:{Colors.RESET}")
            print("  /add <symbol>         - Add to watchlist")
            print("  /add <symbol> <amount> - Add to portfolio")
            print("  Example: /add DOGE")
            print("  Example: /add BTC 0.5")
            return

        parts = args.upper().split()
        symbol = parts[0]

        try:
            from pathlib import Path
            import json

            if len(parts) == 1:
                # Add to watchlist
                config = self.config or {}
                crypto_config = config.get("crypto", {})
                watchlist = crypto_config.get("watchlist", [])

                if symbol in watchlist:
                    print(f"{Colors.INFO}{symbol} already in watchlist{Colors.RESET}")
                    return

                print(f"{Colors.INFO}Note: Add {symbol} to config.yml watchlist for persistence{Colors.RESET}")
                print(f"{Colors.SUCCESS}Would add {symbol} to watchlist{Colors.RESET}")

            else:
                # Add to portfolio
                amount = float(parts[1])

                portfolio_file = Path.home() / ".inkling" / "crypto_portfolio.json"
                portfolio_file.parent.mkdir(parents=True, exist_ok=True)

                if portfolio_file.exists():
                    with open(portfolio_file) as f:
                        holdings = json.load(f)
                else:
                    holdings = {}

                holdings[symbol] = holdings.get(symbol, 0) + amount

                with open(portfolio_file, 'w') as f:
                    json.dump(holdings, f, indent=2)

                print(f"{Colors.SUCCESS}Added {amount} {symbol} to portfolio (total: {holdings[symbol]}){Colors.RESET}")

        except ValueError:
            print(f"{Colors.ERROR}Invalid amount. Use a number (e.g., 0.5){Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_remove(self, args: str = "") -> None:
        """Remove coin from portfolio."""
        if not args:
            print(f"{Colors.INFO}Usage: /remove <symbol> <amount>{Colors.RESET}")
            print("  Example: /remove BTC 0.1")
            return

        parts = args.upper().split()
        if len(parts) < 2:
            print(f"{Colors.ERROR}Please specify amount{Colors.RESET}")
            return

        symbol = parts[0]

        try:
            amount = float(parts[1])

            from pathlib import Path
            import json

            portfolio_file = Path.home() / ".inkling" / "crypto_portfolio.json"
            if not portfolio_file.exists():
                print(f"{Colors.ERROR}Portfolio is empty{Colors.RESET}")
                return

            with open(portfolio_file) as f:
                holdings = json.load(f)

            if symbol not in holdings:
                print(f"{Colors.ERROR}{symbol} not in portfolio{Colors.RESET}")
                return

            holdings[symbol] = max(0, holdings[symbol] - amount)

            if holdings[symbol] == 0:
                del holdings[symbol]
                print(f"{Colors.SUCCESS}Removed all {symbol} from portfolio{Colors.RESET}")
            else:
                print(f"{Colors.SUCCESS}Removed {amount} {symbol} (remaining: {holdings[symbol]}){Colors.RESET}")

            with open(portfolio_file, 'w') as f:
                json.dump(holdings, f, indent=2)

        except ValueError:
            print(f"{Colors.ERROR}Invalid amount{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_alert(self, args: str = "") -> None:
        """Set a price alert."""
        if not args:
            print(f"{Colors.INFO}Usage: /alert <symbol> <price> <above|below>{Colors.RESET}")
            print("  Example: /alert BTC 70000 above")
            print("  Example: /alert ETH 3000 below")
            return

        parts = args.split()
        if len(parts) < 3:
            print(f"{Colors.ERROR}Please specify symbol, price, and condition{Colors.RESET}")
            return

        symbol = parts[0].upper()

        try:
            target_price = float(parts[1])
            condition = parts[2].lower()

            if condition not in ["above", "below"]:
                print(f"{Colors.ERROR}Condition must be 'above' or 'below'{Colors.RESET}")
                return

            from pathlib import Path
            import json

            alerts_file = Path.home() / ".inkling" / "crypto_alerts.json"
            alerts_file.parent.mkdir(parents=True, exist_ok=True)

            if alerts_file.exists():
                with open(alerts_file) as f:
                    alerts = json.load(f)
            else:
                alerts = []

            alert = {
                "symbol": symbol,
                "target_price": target_price,
                "condition": condition,
                "active": True
            }

            alerts.append(alert)

            with open(alerts_file, 'w') as f:
                json.dump(alerts, f, indent=2)

            print(f"{Colors.SUCCESS}🔔 Alert set: {symbol} {condition} ${target_price:,.0f}{Colors.RESET}")

        except ValueError:
            print(f"{Colors.ERROR}Invalid price{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

    async def cmd_alerts(self) -> None:
        """List all active price alerts."""
        try:
            from pathlib import Path
            import json

            alerts_file = Path.home() / ".inkling" / "crypto_alerts.json"
            if not alerts_file.exists():
                print(f"\n{Colors.INFO}No alerts set. Use /alert to create one.{Colors.RESET}")
                return

            with open(alerts_file) as f:
                alerts = json.load(f)

            active_alerts = [a for a in alerts if a.get("active", True)]

            if not active_alerts:
                print(f"\n{Colors.INFO}No active alerts.{Colors.RESET}")
                return

            print(f"\n{Colors.HEADER}═══ PRICE ALERTS ═══{Colors.RESET}\n")

            for alert in active_alerts:
                symbol = alert["symbol"]
                price = alert["target_price"]
                condition = alert["condition"]
                emoji = "⬆️" if condition == "above" else "⬇️"

                print(f"  {emoji} {symbol} {condition} ${price:,.0f}")

            print()

        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")
