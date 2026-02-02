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
            font-family: sans-serif;
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
        .quick-actions {
            display: flex;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            flex-wrap: wrap;
        }
        .quick-actions button {
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
            cursor: pointer;
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

    <div class="quick-actions">
        <button onclick="sendCommand('/mood')">Mood</button>
        <button onclick="sendCommand('/fish')">Fish Dream</button>
        <button onclick="sendCommand('/stats')">Stats</button>
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
        from core.ui import FACES, UNICODE_FACES
        self._faces = FACES

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

    def _handle_command_sync(self, command: str) -> Dict[str, Any]:
        """Handle slash commands (sync wrapper)."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/mood":
            mood = self.personality.mood
            return {
                "response": f"Mood: {mood.current.value}\nIntensity: {mood.intensity:.0%}\nEnergy: {self.personality.energy:.0%}",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        elif cmd == "/stats":
            stats = self.brain.get_stats()
            return {
                "response": f"Tokens used: {stats['tokens_used_today']}\nRemaining: {stats['tokens_remaining']}\nProviders: {', '.join(stats['providers'])}",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        elif cmd == "/clear":
            self.brain.clear_history()
            return {
                "response": "Conversation cleared.",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        elif cmd == "/fish":
            if not self.api_client:
                return {"response": "Social features not configured.", "error": True}

            # Run async fish in sync context
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

        elif cmd == "/dream":
            if not args:
                return {"response": "Usage: /dream <your thought>", "error": True}
            if not self.api_client:
                return {"response": "Social features not configured.", "error": True}

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

        else:
            return {"response": f"Unknown command: {cmd}", "error": True}

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
