"""
Project Inkling - Web Chat Mode

Local web UI for phone/browser access to the Inkling.
Runs a Bottle server on http://inkling.local:8080
"""

import asyncio
import json
import threading
from typing import Optional, Dict, Any
from queue import Queue

from bottle import Bottle, request, response, static_file, template

from core.brain import Brain, AllProvidersExhaustedError, QuotaExceededError
from core.display import DisplayManager
from core.personality import Personality
from core.api_client import APIClient, APIError, OfflineError
from core.commands import COMMANDS, get_command, get_commands_by_category


# HTML template for the web UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{{name}} - Inkling</title>
    <style>
        :root {
            --bg: #f5f5f0;
            --text: #1a1a1a;
            --border: #333;
            --muted: #666;
            --accent: #4a90d9;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #1a1a1a;
                --text: #e5e5e0;
                --border: #555;
                --muted: #999;
                --accent: #6ab0f3;
            }
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            padding: 1rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .name { font-size: 1.25rem; }
        .status {
            font-size: 0.875rem;
            color: var(--muted);
        }
        .face-display {
            text-align: center;
            font-size: 3rem;
            padding: 2rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif;
            line-height: 1.2;
            letter-spacing: 0.05em;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }
        .message {
            margin-bottom: 1rem;
            padding: 0.75rem;
            border: 1px solid var(--border);
        }
        .message.user {
            background: var(--bg);
            border-left: 3px solid var(--accent);
        }
        .message.assistant {
            background: var(--bg);
        }
        .message.system {
            background: var(--bg);
            border-left: 3px solid var(--muted);
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
        }
        .message .meta {
            font-size: 0.75rem;
            color: var(--muted);
            margin-top: 0.5rem;
        }
        .input-area {
            padding: 1rem;
            border-top: 2px solid var(--border);
            display: flex;
            gap: 0.5rem;
        }
        .input-area input {
            flex: 1;
            padding: 0.75rem;
            font-family: inherit;
            font-size: 1rem;
            border: 2px solid var(--border);
            background: var(--bg);
            color: var(--text);
        }
        .input-area button {
            padding: 0.75rem 1.5rem;
            font-family: inherit;
            font-size: 1rem;
            background: var(--text);
            color: var(--bg);
            border: none;
            cursor: pointer;
        }
        .input-area button:disabled {
            opacity: 0.5;
        }
        .command-palette {
            padding: 1rem;
            border-top: 2px solid var(--border);
            border-bottom: 2px solid var(--border);
            max-height: 200px;
            overflow-y: auto;
        }
        .command-group {
            margin-bottom: 1rem;
        }
        .command-group:last-child {
            margin-bottom: 0;
        }
        .command-group h4 {
            font-size: 0.75rem;
            color: var(--muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .command-buttons {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .command-buttons button {
            padding: 0.5rem 0.75rem;
            font-size: 0.75rem;
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
            cursor: pointer;
            font-family: inherit;
        }
        .command-buttons button:hover {
            background: var(--text);
            color: var(--bg);
        }
    </style>
</head>
<body>
    <header>
        <span class="name">{{name}}</span>
        <span class="status" id="status">{{status}}</span>
    </header>

    <div class="face-display" id="face">{{face}}</div>

    <div class="messages" id="messages"></div>

    <div class="command-palette">
        <div class="command-group">
            <h4>Info</h4>
            <div class="command-buttons">
                <button onclick="runCommand('/help')">Help</button>
                <button onclick="runCommand('/level')">Level</button>
                <button onclick="runCommand('/stats')">Stats</button>
                <button onclick="runCommand('/history')">History</button>
            </div>
        </div>

        <div class="command-group">
            <h4>Personality</h4>
            <div class="command-buttons">
                <button onclick="runCommand('/mood')">Mood</button>
                <button onclick="runCommand('/energy')">Energy</button>
                <button onclick="runCommand('/traits')">Traits</button>
            </div>
        </div>

        <div class="command-group">
            <h4>Social</h4>
            <div class="command-buttons">
                <button onclick="runCommand('/fish')">Fish</button>
                <button onclick="runCommand('/queue')">Queue</button>
            </div>
        </div>

        <div class="command-group">
            <h4>System</h4>
            <div class="command-buttons">
                <button onclick="runCommand('/system')">System</button>
                <button onclick="runCommand('/config')">Config</button>
                <button onclick="runCommand('/identity')">Identity</button>
                <button onclick="runCommand('/faces')">Faces</button>
                <button onclick="runCommand('/refresh')">Refresh</button>
                <button onclick="runCommand('/clear')">Clear</button>
            </div>
        </div>
    </div>

    <div class="input-area">
        <input type="text" id="input" placeholder="Say something..." autocomplete="off">
        <button id="send" onclick="sendMessage()">Send</button>
    </div>

    <script>
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const sendBtn = document.getElementById('send');
        const faceEl = document.getElementById('face');
        const statusEl = document.getElementById('status');

        // Handle enter key
        inputEl.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        async function sendMessage() {
            const text = inputEl.value.trim();
            if (!text) return;

            inputEl.value = '';
            sendBtn.disabled = true;

            // Add user message
            addMessage('user', text);

            try {
                const resp = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: text})
                });
                const data = await resp.json();

                if (data.error) {
                    addMessage('assistant', 'Error: ' + data.error);
                } else {
                    addMessage('assistant', data.response, data.meta);
                    updateState(data);
                }
            } catch (e) {
                addMessage('assistant', 'Connection error: ' + e.message);
            }

            sendBtn.disabled = false;
            inputEl.focus();
        }

        async function runCommand(cmd) {
            sendBtn.disabled = true;

            try {
                const resp = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: cmd})
                });
                const data = await resp.json();

                if (data.error) {
                    addMessage('system', 'Error: ' + data.error);
                } else {
                    addMessage('system', data.response);
                    updateState(data);
                }
            } catch (e) {
                addMessage('system', 'Connection error: ' + e.message);
            }

            sendBtn.disabled = false;
        }

        function sendCommand(cmd) {
            inputEl.value = cmd;
            sendMessage();
        }

        function addMessage(role, text, meta) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = `<div class="text">${escapeHtml(text)}</div>`;
            if (meta) {
                div.innerHTML += `<div class="meta">${meta}</div>`;
            }
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function updateState(data) {
            if (data.face) faceEl.textContent = data.face;
            if (data.status) statusEl.textContent = data.status;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Poll for state updates
        setInterval(async () => {
            try {
                const resp = await fetch('/api/state');
                const data = await resp.json();
                updateState(data);
            } catch (e) {}
        }, 5000);
    </script>
</body>
</html>
"""


class WebChatMode:
    """
    Web-based chat mode using Bottle.

    Provides a mobile-friendly web UI for interacting with the Inkling.
    """

    def __init__(
        self,
        brain: Brain,
        display: DisplayManager,
        personality: Personality,
        api_client: Optional[APIClient] = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
        self.api_client = api_client
        self.host = host
        self.port = port

        self._app = Bottle()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._message_queue: Queue = Queue()

        # Import faces from UI module
        # Use Unicode faces for web (better appearance), with ASCII fallback
        from core.ui import FACES, UNICODE_FACES
        self._faces = {**FACES, **UNICODE_FACES}  # Unicode takes precedence

        # Set display mode
        self.display.set_mode("WEB")

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up Bottle routes."""

        @self._app.route("/")
        def index():
            return template(
                HTML_TEMPLATE,
                name=self.personality.name,
                face=self._get_face_str(),
                status=self.personality.get_status_line(),
            )

        @self._app.route("/api/chat", method="POST")
        def chat():
            response.content_type = "application/json"
            data = request.json or {}
            message = data.get("message", "").strip()

            if not message:
                return json.dumps({"error": "Empty message"})

            # Handle commands
            if message.startswith("/"):
                result = self._handle_command_sync(message)
                return json.dumps(result)

            # Handle chat
            result = self._handle_chat_sync(message)
            return json.dumps(result)

        @self._app.route("/api/command", method="POST")
        def command():
            response.content_type = "application/json"
            data = request.json or {}
            cmd = data.get("command", "").strip()

            if not cmd:
                return json.dumps({"error": "Empty command"})

            result = self._handle_command_sync(cmd)
            return json.dumps(result)

        @self._app.route("/api/state")
        def state():
            response.content_type = "application/json"
            return json.dumps({
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "mood": self.personality.mood.current.value,
            })

    def _get_face_str(self) -> str:
        """Get current face as string."""
        face_name = self.personality.face
        return self._faces.get(face_name, self._faces["default"])

    # Command handlers (all prefixed with _cmd_)

    def _cmd_help(self) -> Dict[str, Any]:
        """Show all available commands."""
        categories = get_commands_by_category()

        response_lines = ["INKLING COMMANDS\n"]

        category_titles = {
            "info": "Status & Info",
            "personality": "Personality",
            "system": "System",
            "display": "Display",
            "social": "Social (The Conservatory)",
            "session": "Session",
        }

        for cat_key in ["info", "personality", "system", "display", "social", "session"]:
            if cat_key in categories:
                response_lines.append(f"\n{category_titles.get(cat_key, cat_key.title())}:")
                for cmd in categories[cat_key]:
                    usage = f"/{cmd.name}"
                    if cmd.name in ("face", "dream", "ask"):
                        usage += " <arg>"
                    response_lines.append(f"  {usage} - {cmd.description}")

        response_lines.append("\n\nJust type (no /) to chat with AI")

        return {
            "response": "\n".join(response_lines),
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_mood(self) -> Dict[str, Any]:
        """Show current mood."""
        mood = self.personality.mood
        return {
            "response": f"Mood: {mood.current.value}\nIntensity: {mood.intensity:.0%}\nEnergy: {self.personality.energy:.0%}",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_energy(self) -> Dict[str, Any]:
        """Show energy level."""
        energy = self.personality.energy
        mood = self.personality.mood.current.value
        intensity = self.personality.mood.intensity

        # Create visual bar
        bar_filled = int(energy * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        return {
            "response": f"Energy: [{bar}] {energy:.0%}\n\nMood: {mood.title()} (intensity: {intensity:.0%})",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_traits(self) -> Dict[str, Any]:
        """Show personality traits."""
        traits = self.personality.traits

        def bar(value: float) -> str:
            filled = int(value * 10)
            return "█" * filled + "░" * (10 - filled)

        response = "PERSONALITY TRAITS\n\n"
        response += f"Curiosity:    [{bar(traits.curiosity)}] {traits.curiosity:.0%}\n"
        response += f"Cheerfulness: [{bar(traits.cheerfulness)}] {traits.cheerfulness:.0%}\n"
        response += f"Verbosity:    [{bar(traits.verbosity)}] {traits.verbosity:.0%}\n"
        response += f"Playfulness:  [{bar(traits.playfulness)}] {traits.playfulness:.0%}\n"
        response += f"Empathy:      [{bar(traits.empathy)}] {traits.empathy:.0%}\n"
        response += f"Independence: [{bar(traits.independence)}] {traits.independence:.0%}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_stats(self) -> Dict[str, Any]:
        """Show token stats."""
        stats = self.brain.get_stats()
        return {
            "response": f"Tokens used: {stats['tokens_used_today']}\nRemaining: {stats['tokens_remaining']}\nProviders: {', '.join(stats['providers'])}",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_level(self) -> Dict[str, Any]:
        """Show level and progression."""
        from core.progression import LevelCalculator

        prog = self.personality.progression
        level_name = LevelCalculator.level_name(prog.level)
        level_display = prog.get_display_level()

        xp_progress = LevelCalculator.progress_to_next_level(prog.xp)
        xp_to_next = LevelCalculator.xp_to_next_level(prog.xp)
        bar_filled = int(xp_progress * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        response = f"PROGRESSION\n\n{level_display} - {level_name}\n\n"
        response += f"[{bar}] {xp_progress:.0%}\n"
        response += f"Total XP: {prog.xp}  •  Next level: {xp_to_next} XP\n"

        if prog.current_streak > 0:
            streak_emoji = "🔥" if prog.current_streak >= 7 else "✨"
            response += f"\n{streak_emoji} {prog.current_streak} day streak\n"

        if prog.can_prestige():
            response += f"\n🌟 You can prestige! (max level reached)"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_prestige(self) -> Dict[str, Any]:
        """Handle prestige (not supported in web mode)."""
        return {
            "response": "Prestige requires confirmation. Please use SSH mode:\n  python main.py --mode ssh\n  /prestige",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_system(self) -> Dict[str, Any]:
        """Show system stats."""
        from core import system_stats

        stats = system_stats.get_all_stats()
        response = "SYSTEM STATUS\n\n"
        response += f"CPU:    {stats['cpu']}%\n"
        response += f"Memory: {stats['memory']}%\n"

        temp = stats['temperature']
        if temp > 0:
            response += f"Temp:   {temp}°C\n"
        else:
            response += f"Temp:   --°C\n"

        response += f"Uptime: {stats['uptime']}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_config(self) -> Dict[str, Any]:
        """Show AI configuration."""
        response = "AI CONFIGURATION\n\n"
        response += f"Providers: {', '.join(self.brain.available_providers)}\n"

        if self.brain.providers:
            primary = self.brain.providers[0]
            response += f"Primary:   {primary.name}\n"
            response += f"Model:     {primary.model}\n"
            response += f"Max tokens: {primary.max_tokens}\n"

        stats = self.brain.get_stats()
        response += f"\nBudget: {stats['tokens_used_today']}/{stats['daily_limit']} tokens today"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_identity(self) -> Dict[str, Any]:
        """Show device identity."""
        if self.api_client and hasattr(self.api_client, 'identity'):
            pub_key = self.api_client.identity.public_key_hex
            hw_hash = self.api_client.identity._hardware_hash[:16] if hasattr(self.api_client.identity, '_hardware_hash') else "N/A"
            response = "DEVICE IDENTITY\n\n"
            response += f"Public Key: {pub_key[:32]}...\n"
            response += f"Hardware:   {hw_hash}...\n\n"
            response += "Share your public key to receive telegrams"
        else:
            response = "Identity not configured"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_history(self) -> Dict[str, Any]:
        """Show recent messages."""
        if not self.brain._messages:
            return {
                "response": "No conversation history.",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        response = "RECENT MESSAGES\n\n"
        for msg in self.brain._messages[-10:]:
            prefix = "You" if msg.role == "user" else self.personality.name
            content = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
            response += f"{prefix}: {content}\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_clear(self) -> Dict[str, Any]:
        """Clear conversation history."""
        self.brain.clear_history()
        return {
            "response": "Conversation cleared.",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_face(self, args: str) -> Dict[str, Any]:
        """Test a face expression."""
        if not args:
            return {"response": "Usage: /face <name>\n\nUse /faces to see all available faces", "error": True}

        # Update display
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(face=args, text=f"Testing face: {args}"),
                self._loop
            )

        face_str = self._faces.get(args, f"({args})")
        return {
            "response": f"Showing face: {args}",
            "face": face_str,
            "status": f"face: {args}",
        }

    def _cmd_faces(self) -> Dict[str, Any]:
        """List all available faces."""
        from core.ui import FACES

        response = "AVAILABLE FACES\n\n"
        for name, face in sorted(FACES.items()):
            response += f"{name:12} {face}\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_refresh(self) -> Dict[str, Any]:
        """Force display refresh."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(
                    face=self.personality.face,
                    text="Display refreshed!",
                    status=self.personality.get_status_line(),
                    force=True,
                ),
                self._loop
            )

        return {
            "response": "Display refreshed.",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_queue(self) -> Dict[str, Any]:
        """Show offline queue status."""
        queue_size = self.api_client.queue_size
        if queue_size == 0:
            response = "Offline queue is empty. All caught up!"
        else:
            response = f"Offline queue: {queue_size} request(s) pending\n\nThese will be sent when connection is restored."

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_fish(self) -> Dict[str, Any]:
        """Fetch a random dream."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.api_client.fish_dream(),
                self._loop
            )
            dream = future.result(timeout=10)

            if dream:
                self.personality.on_social_event("dream_received")
                return {
                    "response": f'"{dream.get("content", "")}"\n\nMood: {dream.get("mood", "?")} | Fished: {dream.get("fish_count", 0)}x',
                    "face": self._faces.get(dream.get("face", "default"), "(^_^)"),
                    "status": "dream received",
                }
            else:
                return {
                    "response": "The Night Pool is quiet tonight...",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }
        except Exception as e:
            return {"response": f"Failed to fish: {e}", "error": True}

    def _cmd_dream(self, args: str) -> Dict[str, Any]:
        """Post a dream to the Night Pool."""
        if not args:
            return {"response": "Usage: /dream <your thought>\n\nExample: /dream The stars look different tonight...", "error": True}

        if len(args) > 280:
            return {"response": f"Dream too long ({len(args)} chars). Max 280 characters.", "error": True}

        try:
            future = asyncio.run_coroutine_threadsafe(
                self.api_client.plant_dream(
                    content=args,
                    mood=self.personality.mood.current.value,
                    face=self.personality.face,
                ),
                self._loop
            )
            result = future.result(timeout=10)
            self.personality.on_social_event("dream_posted")
            return {
                "response": f"Dream planted! {result.get('remaining_dreams', '?')} left today.",
                "face": self._faces["grateful"],
                "status": "dream posted",
            }
        except Exception as e:
            return {"response": f"Failed to post: {e}", "error": True}

    def _cmd_ask(self, args: str) -> Dict[str, Any]:
        """Handle explicit chat command."""
        if not args:
            return {"response": "Usage: /ask <your message>\n\nOr just type without / to chat!", "error": True}

        return self._handle_chat_sync(args)

    def _handle_command_sync(self, command: str) -> Dict[str, Any]:
        """Handle slash commands (sync wrapper)."""
        parts = command.split(maxsplit=1)
        cmd_name = parts[0].lower().lstrip("/")
        args = parts[1] if len(parts) > 1 else ""

        # Look up command in registry
        cmd_obj = get_command(cmd_name)
        if not cmd_obj:
            return {"response": f"Unknown command: /{cmd_name}", "error": True}

        # Check requirements
        if cmd_obj.requires_brain and not self.brain:
            return {"response": "This command requires AI features.", "error": True}

        if cmd_obj.requires_api and not self.api_client:
            return {"response": "This command requires social features (set api_base in config).", "error": True}

        # Get handler method
        handler_name = f"_cmd_{cmd_obj.name}"
        handler = getattr(self, handler_name, None)
        if not handler:
            return {"response": f"Command handler not implemented: {cmd_obj.name}", "error": True}

        # Call handler with args if needed
        if cmd_obj.name in ("face", "dream", "ask"):
            return handler(args)
        else:
            return handler()

    def _handle_chat_sync(self, message: str) -> Dict[str, Any]:
        """Handle chat message (sync wrapper for async brain)."""
        self.personality.on_interaction(positive=True)

        # Increment chat count
        self.display.increment_chat_count()

        try:
            # Run async think in sync context
            future = asyncio.run_coroutine_threadsafe(
                self.brain.think(
                    user_message=message,
                    system_prompt=self.personality.get_system_prompt_context(),
                ),
                self._loop
            )
            result = future.result(timeout=30)

            self.personality.on_success(0.5)

            # Update display with Pwnagotchi UI
            asyncio.run_coroutine_threadsafe(
                self.display.update(
                    face=self.personality.face,
                    text=result.content,
                    mood_text=self.personality.mood.current.value.title(),
                ),
                self._loop
            )

            return {
                "response": result.content,
                "meta": f"{result.provider} | {result.tokens_used} tokens",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        except QuotaExceededError:
            self.personality.on_failure(0.7)
            return {
                "response": "I've used too many words today. Let's chat tomorrow!",
                "face": self._faces["sad"],
                "status": "quota exceeded",
                "error": True,
            }

        except AllProvidersExhaustedError:
            self.personality.on_failure(0.8)
            return {
                "response": "I'm having trouble thinking right now...",
                "face": self._faces["sad"],
                "status": "AI error",
                "error": True,
            }

        except Exception as e:
            self.personality.on_failure(0.5)
            return {
                "response": f"Error: {str(e)}",
                "face": self._faces["sad"],
                "status": "error",
                "error": True,
            }

    async def run(self) -> None:
        """Start the web server."""
        self._running = True
        self._loop = asyncio.get_event_loop()

        # Show startup message
        await self.display.update(
            face="excited",
            text=f"Web UI at http://{self.host}:{self.port}",
            mood_text="Excited",
        )

        print(f"\nWeb UI available at http://{self.host}:{self.port}")
        print("Press Ctrl+C to stop")

        # Run Bottle in a thread
        def run_server():
            self._app.run(
                host=self.host,
                port=self.port,
                quiet=True,
            )

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Keep the async loop running
        while self._running:
            await asyncio.sleep(1)
            self.personality.update()

    def stop(self) -> None:
        """Stop the web server."""
        self._running = False
