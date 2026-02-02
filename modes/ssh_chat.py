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
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
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

        try:
            # Get AI response
            result = await self.brain.think(
                user_message=message,
                system_prompt=self.personality.get_system_prompt_context(),
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
