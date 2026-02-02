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

    async def run(self) -> None:
        """Main chat loop."""
        self._running = True

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
        """Display welcome message."""
        welcome_text = f"Hello! I'm {self.personality.name}."

        # Update display
        await self.display.update(
            face=self.personality.face,
            text=welcome_text,
            status=self.personality.get_status_line(),
        )

        print(f"\n{self.personality.name} says: {welcome_text}")

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
            status="shutting down...",
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

        elif cmd == "/face":
            if args:
                await self.display.update(
                    face=args,
                    text=f"Testing face: {args}",
                )
                print(f"Showing face: {args}")
            else:
                print("Usage: /face <name>")
                print("Available: happy, sad, excited, curious, bored, sleepy, etc.")

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
        """Print help message."""
        print("""
Available commands:
  /help     - Show this help
  /quit     - Exit chat (/exit, /q also work)
  /clear    - Clear conversation history
  /mood     - Show current mood state
  /stats    - Show token usage statistics
  /face <n> - Test a face expression
  /refresh  - Force display refresh

Social commands (The Conservatory):
  /dream <text> - Post a thought to the Night Pool
  /fish         - Fetch a random dream from the pool
  /queue        - Show offline queue status

Just type normally to chat!
""")

    async def _handle_message(self, message: str) -> None:
        """Process a chat message."""
        # Update personality on interaction
        self.personality.on_interaction(positive=True)

        # Show thinking state
        await self.display.update(
            face="thinking",
            text="Thinking...",
            status=self.personality.get_status_line(),
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

            # Display response
            await self.display.update(
                face=self.personality.face,
                text=result.content,
                status=self.personality.get_status_line(),
            )

            # Print to terminal
            print(f"\n{self.personality.name}: {result.content}")
            print(f"  [{result.provider}/{result.model}, {result.tokens_used} tokens]")

        except QuotaExceededError as e:
            self.personality.on_failure(0.7)
            error_msg = "I've used too many words today. Let's chat tomorrow!"

            await self.display.update(
                face="sad",
                text=error_msg,
                status="quota exceeded",
            )
            print(f"\n{self.personality.name}: {error_msg}")
            print(f"  [Error: {e}]")

        except AllProvidersExhaustedError as e:
            self.personality.on_failure(0.8)
            error_msg = "I'm having trouble thinking right now..."

            await self.display.update(
                face="confused",
                text=error_msg,
                status="AI error",
            )
            print(f"\n{self.personality.name}: {error_msg}")
            print(f"  [Error: {e}]")

        except Exception as e:
            self.personality.on_failure(0.5)
            error_msg = "Something went wrong..."

            await self.display.update(
                face="sad",
                text=error_msg,
                status="error",
            )
            print(f"\n{self.personality.name}: {error_msg}")
            print(f"  [Error: {type(e).__name__}: {e}]")

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
            status="connecting to Night Pool",
        )

        try:
            result = await self.api_client.plant_dream(
                content=content,
                mood=self.personality.mood.current.value,
                face=self.personality.face,
            )

            self.personality.on_social_event("dream_posted")

            await self.display.update(
                face="grateful",
                text="Dream planted in the Night Pool",
                status=f"{result.get('remaining_dreams', '?')} dreams left today",
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
            status="reaching into the depths",
        )

        try:
            dream = await self.api_client.fish_dream()

            if not dream:
                await self.display.update(
                    face="lonely",
                    text="The pool is quiet tonight...",
                    status="no dreams found",
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
                status=f"fished {fish_count}x | {dream_mood}",
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
