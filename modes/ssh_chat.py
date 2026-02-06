"""
Project Inkling - SSH Chat Mode

Interactive terminal mode for chatting with Inkling via SSH.
Reads from stdin, sends to AI, displays responses on e-ink.
"""

import asyncio
import inspect
import sys
from typing import Optional

from core.brain import Brain, AllProvidersExhaustedError, QuotaExceededError
from core.display import DisplayManager
from core.personality import Personality
from core.ui import FACES, UNICODE_FACES
from core.commands import COMMANDS, get_command, get_commands_by_category
from core.tasks import TaskManager, Task, TaskStatus, Priority
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
        scheduler=None,
        config: Optional[dict] = None,
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
        self.task_manager = task_manager
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
            "tasks": "Task Management",
            "system": "System",
            "display": "Display",
        }

        for cat_key in ["session", "info", "personality", "tasks", "system", "display"]:
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

    async def cmd_bash(self, args: str) -> None:
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

    async def cmd_face(self, args: str) -> None:
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

    async def cmd_ask(self, args: str) -> None:
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
            # Check if message needs pagination (> 6 lines worth of text)
            from core.ui import word_wrap, MESSAGE_MAX_LINES
            lines = word_wrap(result.content, 40)
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

    async def cmd_task(self, args: str) -> None:
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

    async def cmd_done(self, args: str) -> None:
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

    async def cmd_cancel(self, args: str) -> None:
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

    async def cmd_delete(self, args: str) -> None:
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
