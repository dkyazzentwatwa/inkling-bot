"""
Project Inkling - Web Chat Mode

Local web UI for phone/browser access to the Inkling.
Runs a Bottle server on http://inkling.local:8081
"""

import asyncio
import json
import os
import threading
import hashlib
import hmac
import secrets
import time
from pathlib import Path
from typing import Optional, Dict, Any
from queue import Queue
from collections import defaultdict

from bottle import Bottle, request, response, static_file, template, redirect

from core.brain import Brain, AllProvidersExhaustedError, QuotaExceededError
from core.display import DisplayManager
from core.personality import Personality, Mood
from core.progression import XPSource
from core.commands import COMMANDS, get_command, get_commands_by_category
from core.tasks import TaskManager, Task, TaskStatus, Priority
from core.crypto import Identity


# Template loading
TEMPLATE_DIR = Path(__file__).parent / "web" / "templates"


def _load_template(name: str) -> str:
    """Load template from file."""
    template_path = TEMPLATE_DIR / name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text()


# HTML template for the web UI
HTML_TEMPLATE = _load_template("main.html")


# Settings page template
SETTINGS_TEMPLATE = _load_template("settings.html")


TASKS_TEMPLATE = _load_template("tasks.html")

LOGIN_TEMPLATE = _load_template("login.html")


FILES_TEMPLATE = _load_template("files.html")


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
        task_manager: Optional[TaskManager] = None,
        scheduler=None,
        identity: Optional[Identity] = None,
        config: Optional[Dict] = None,
        host: str = "0.0.0.0",
        port: int = 8081,
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
        self.task_manager = task_manager
        self.scheduler = scheduler
        self.identity = identity
        self.host = host
        self.port = port

        # Authentication setup
        self._config = config or {}
        self._web_password = self._config.get("network", {}).get("web_password", "")
        if not self._web_password:
            self._web_password = os.environ.get("SERVER_PW", "")
        self._auth_enabled = bool(self._web_password)
        # Generate a secret key for signing cookies (persistent per session)
        self._secret_key = secrets.token_hex(32)

        # Rate limiting for login attempts
        self._login_attempts: Dict[str, list] = defaultdict(list)
        self._login_max_attempts = 5
        self._login_window_seconds = 300  # 5 minutes

        # Detect HTTPS (ngrok always uses HTTPS)
        ngrok_config = self._config.get("network", {}).get("ngrok", {})
        self._use_secure_cookies = ngrok_config.get("enabled", False)

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

    def _create_auth_token(self) -> str:
        """Create a signed authentication token."""
        # Simple HMAC-based token
        message = f"authenticated:{secrets.token_hex(16)}"
        signature = hmac.new(
            self._secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{message}|{signature}"

    def _verify_auth_token(self, token: str) -> bool:
        """Verify an authentication token."""
        if not token:
            return False
        try:
            message, signature = token.rsplit("|", 1)
            expected_signature = hmac.new(
                self._secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    def _check_auth(self) -> bool:
        """Check if the user is authenticated."""
        if not self._auth_enabled:
            return True  # Auth disabled, allow access

        token = request.get_cookie("auth_token")
        return self._verify_auth_token(token)

    def _require_auth(self):
        """Decorator/check that requires authentication for page routes."""
        if not self._check_auth():
            return redirect("/login")
        return None

    def _require_api_auth(self):
        """Check authentication for API routes. Returns error JSON or None."""
        if not self._check_auth():
            response.status = 401
            response.content_type = "application/json"
            return json.dumps({"error": "Authentication required"})
        return None

    @staticmethod
    def _safe_resolve_path(base_dir: str, path: str) -> Optional[str]:
        """Safely resolve a path within a base directory.
        Uses realpath to resolve symlinks and commonpath for containment check.
        Returns the resolved path or None if it escapes the base directory.
        """
        try:
            base_real = os.path.realpath(base_dir)
            full_path = os.path.realpath(os.path.normpath(os.path.join(base_real, path)))
            if os.path.commonpath([base_real, full_path]) != base_real:
                return None
            return full_path
        except (ValueError, OSError):
            return None

    def _check_rate_limit(self, ip: str) -> bool:
        """Check if IP is rate-limited for login. Returns True if allowed."""
        now = time.time()
        # Prune old attempts outside window
        self._login_attempts[ip] = [
            t for t in self._login_attempts[ip]
            if now - t < self._login_window_seconds
        ]
        return len(self._login_attempts[ip]) < self._login_max_attempts

    def _record_login_attempt(self, ip: str):
        """Record a failed login attempt."""
        self._login_attempts[ip].append(time.time())

    def _setup_routes(self) -> None:
        """Set up Bottle routes."""

        @self._app.route("/login")
        def login_page():
            """Show login page."""
            if self._check_auth():
                return redirect("/")
            return template(LOGIN_TEMPLATE, error=None)

        @self._app.route("/login", method="POST")
        def login_post():
            """Handle login form submission."""
            ip = request.remote_addr or "unknown"

            # Rate limiting
            if not self._check_rate_limit(ip):
                return template(LOGIN_TEMPLATE, error="Too many attempts. Try again later.")

            password = request.forms.get("password", "")

            if hmac.compare_digest(password, self._web_password):
                # Correct password
                response.set_cookie("auth_token", self._create_auth_token(),
                                   max_age=86400 * 7,  # 7 days
                                   httponly=True,
                                   secure=self._use_secure_cookies,
                                   samesite="Strict")
                return redirect("/")
            else:
                # Wrong password — record attempt
                self._record_login_attempt(ip)
                return template(LOGIN_TEMPLATE, error="Invalid password")

        @self._app.route("/logout")
        def logout():
            """Log out and clear session."""
            response.delete_cookie("auth_token")
            return redirect("/login")

        @self._app.route("/")
        def index():
            auth_check = self._require_auth()
            if auth_check:
                return auth_check
            return template(
                HTML_TEMPLATE,
                name=self.personality.name,
                face=self._get_face_str(),
                status=self.personality.get_status_line(),
                thought=self.personality.last_thought or "",
            )

        @self._app.route("/settings")
        def settings_page():
            auth_check = self._require_auth()
            if auth_check:
                return auth_check
            return template(
                SETTINGS_TEMPLATE,
                name=self.personality.name,
                traits=self.personality.traits.to_dict(),
                status=self.personality.get_status_line(),
                thought=self.personality.last_thought or "",
            )

        @self._app.route("/tasks")
        def tasks_page():
            auth_check = self._require_auth()
            if auth_check:
                return auth_check
            return template(
                TASKS_TEMPLATE,
                name=self.personality.name,
                status=self.personality.get_status_line(),
                thought=self.personality.last_thought or "",
            )

        @self._app.route("/files")
        def files_page():
            auth_check = self._require_auth()
            if auth_check:
                return auth_check

            # Check if SD card storage is available
            sd_available = False
            sd_config = self._config.get("storage", {}).get("sd_card", {})
            if sd_config.get("enabled", False):
                sd_path = sd_config.get("path")
                if sd_path == "auto":
                    from core.storage import get_sd_card_path
                    sd_available = get_sd_card_path() is not None
                else:
                    from core.storage import is_storage_available
                    sd_available = is_storage_available(sd_path) if sd_path else False

            return template(
                FILES_TEMPLATE,
                name=self.personality.name,
                sd_available=sd_available,
                status=self.personality.get_status_line(),
                thought=self.personality.last_thought or "",
            )

        @self._app.route("/api/chat", method="POST")
        def chat():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
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
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"
            data = request.json or {}
            cmd = data.get("command", "").strip()

            if not cmd:
                return json.dumps({"error": "Empty command"})

            result = self._handle_command_sync(cmd)
            return json.dumps(result)

        @self._app.route("/api/state")
        def state():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"
            return json.dumps({
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "mood": self.personality.mood.current.value,
                "thought": self.personality.last_thought or "",
            })

        @self._app.route("/api/settings", method="GET")
        def get_settings():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            # Get AI config from Brain
            ai_config = {
                "primary": self.brain.config.get("primary", "anthropic"),
                "anthropic": {
                    "model": self.brain.config.get("anthropic", {}).get("model", "claude-3-haiku-20240307"),
                },
                "openai": {
                    "model": self.brain.config.get("openai", {}).get("model", "gpt-4o-mini"),
                },
                "gemini": {
                    "model": self.brain.config.get("gemini", {}).get("model", "gemini-2.0-flash-exp"),
                },
                "ollama": {
                    "model": self.brain.config.get("ollama", {}).get("model", "qwen3-coder-next"),
                },
                "budget": {
                    "daily_tokens": self.brain.budget.daily_limit,
                    "max_tokens": self.brain.config.get("budget", {}).get("per_request_max", 150),
                }
            }

            # Get display config
            display_config = {
                "dark_mode": self.display._dark_mode,
                "screensaver": {
                    "enabled": self.display._screensaver_enabled,
                    "idle_timeout_minutes": self.display._screensaver_idle_minutes,
                }
            }

            return json.dumps({
                "name": self.personality.name,
                "traits": self.personality.traits.to_dict(),
                "ai": ai_config,
                "display": display_config,
            })

        @self._app.route("/api/settings", method="POST")
        def save_settings():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"
            data = request.json or {}

            try:
                # Update personality name
                if "name" in data:
                    name = data["name"].strip()
                    if not name:
                        return json.dumps({"success": False, "error": "Name cannot be empty"})
                    if len(name) > 20:
                        return json.dumps({"success": False, "error": "Name too long (max 20 characters)"})
                    self.personality.name = name

                # Update traits (validate 0.0-1.0 range)
                if "traits" in data:
                    for trait, value in data["traits"].items():
                        if hasattr(self.personality.traits, trait):
                            # Clamp value to 0.0-1.0
                            value = max(0.0, min(1.0, float(value)))
                            setattr(self.personality.traits, trait, value)

                # Update display settings (apply immediately)
                if "display" in data:
                    display_settings = data["display"]

                    # Apply dark mode
                    if "dark_mode" in display_settings:
                        self.display._dark_mode = display_settings["dark_mode"]
                        if self._loop:
                            asyncio.run_coroutine_threadsafe(
                                self.display.update(force=True),
                                self._loop
                            )

                    # Apply screensaver settings
                    if "screensaver" in display_settings:
                        ss = display_settings["screensaver"]
                        self.display.configure_screensaver(
                            enabled=ss.get("enabled", False),
                            idle_minutes=ss.get("idle_timeout_minutes", 5.0)
                        )

                # AI settings are saved to config but not applied until restart
                # (no validation needed - Brain will reinitialize on restart)

                # Save to config.local.yml
                self._save_config_file(data)

                return json.dumps({"success": True})

            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        # Task Management API Routes
        @self._app.route("/api/tasks", method="GET")
        def get_tasks():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            # Parse query parameters
            status_param = request.query.get("status")
            project_param = request.query.get("project")

            status_filter = None
            if status_param:
                try:
                    status_filter = TaskStatus(status_param)
                except ValueError:
                    pass

            tasks = self.task_manager.list_tasks(
                status=status_filter,
                project=project_param
            )

            return json.dumps({
                "tasks": [self._task_to_dict(t) for t in tasks]
            })

        @self._app.route("/api/tasks", method="POST")
        def create_task():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            data = request.json or {}
            title = data.get("title", "").strip()

            if not title:
                return json.dumps({"error": "Task title is required"})

            try:
                priority = Priority(data.get("priority", "medium"))
            except ValueError:
                priority = Priority.MEDIUM

            # Parse due date if provided
            due_date = None
            if "due_in_days" in data:
                import time
                days = float(data["due_in_days"])
                due_date = time.time() + (days * 86400)

            task = self.task_manager.create_task(
                title=title,
                description=data.get("description"),
                priority=priority,
                due_date=due_date,
                mood=self.personality.mood.current.value,
                tags=data.get("tags", []),
                project=data.get("project")
            )

            # Trigger personality event
            result = self.personality.on_task_event(
                "task_created",
                {"priority": task.priority.value, "title": task.title}
            )

            return json.dumps({
                "success": True,
                "task": self._task_to_dict(task),
                "celebration": result.get("message") if result else None,
                "xp_awarded": result.get("xp_awarded", 0) if result else 0
            })

        @self._app.route("/api/tasks/<task_id>", method="GET")
        def get_task(task_id):
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            task = self.task_manager.get_task(task_id)

            if not task:
                response.status = 404
                return json.dumps({"error": "Task not found"})

            return json.dumps({
                "task": self._task_to_dict(task)
            })

        @self._app.route("/api/tasks/<task_id>/complete", method="POST")
        def complete_task(task_id):
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            task = self.task_manager.complete_task(task_id)

            if not task:
                response.status = 404
                return json.dumps({"error": "Task not found"})

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

            return json.dumps({
                "success": True,
                "task": self._task_to_dict(task),
                "celebration": result.get("message") if result else None,
                "xp_awarded": result.get("xp_awarded", 0) if result else 0
            })

        @self._app.route("/api/tasks/<task_id>", method="PUT")
        def update_task(task_id):
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            task = self.task_manager.get_task(task_id)

            if not task:
                response.status = 404
                return json.dumps({"error": "Task not found"})

            data = request.json or {}

            # Update fields
            if "title" in data:
                task.title = data["title"]
            if "description" in data:
                task.description = data["description"]
            if "priority" in data:
                try:
                    task.priority = Priority(data["priority"])
                except ValueError:
                    pass
            if "status" in data:
                try:
                    task.status = TaskStatus(data["status"])
                except ValueError:
                    pass
            if "due_date" in data:
                if data["due_date"]:
                    from datetime import datetime as dt
                    try:
                        task.due_date = dt.fromisoformat(data["due_date"]).timestamp()
                    except (ValueError, TypeError):
                        pass
                else:
                    task.due_date = None
            if "tags" in data:
                task.tags = data["tags"]
            if "project" in data:
                task.project = data["project"]

            self.task_manager.update_task(task)

            return json.dumps({
                "success": True,
                "task": self._task_to_dict(task)
            })

        @self._app.route("/api/tasks/<task_id>", method="DELETE")
        def delete_task(task_id):
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            deleted = self.task_manager.delete_task(task_id)

            if not deleted:
                response.status = 404
                return json.dumps({"error": "Task not found"})

            return json.dumps({"success": True})

        @self._app.route("/api/tasks/stats", method="GET")
        def get_task_stats():
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            if not self.task_manager:
                return json.dumps({"error": "Task manager not available"})

            stats = self.task_manager.get_stats()

            # Include streak from progression
            try:
                stats["current_streak"] = self.personality.progression.current_streak
            except Exception:
                stats["current_streak"] = 0

            return json.dumps({
                "stats": stats
            })

        def get_base_dir(storage: str) -> Optional[str]:
            """Get base directory for storage location."""
            if storage == "inkling":
                home = os.path.expanduser("~")
                return os.path.join(home, ".inkling")
            elif storage == "sd":
                # Get SD card path from config
                sd_config = self._config.get("storage", {}).get("sd_card", {})
                if not sd_config.get("enabled", False):
                    return None

                sd_path = sd_config.get("path")
                if sd_path == "auto":
                    # Auto-detect SD card
                    from core.storage import get_sd_card_path
                    detected_path = get_sd_card_path()
                    return detected_path
                else:
                    # Use configured path
                    return sd_path if sd_path else None
            return None

        @self._app.route("/api/files/list", method="GET")
        def list_files():
            """List files in storage directory (inkling or SD card)."""
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            # Get storage and path from query params
            storage = request.query.get("storage", "inkling")
            path = request.query.get("path", "")

            try:
                # Get base directory for storage location
                base_dir = get_base_dir(storage)
                if not base_dir:
                    return json.dumps({"error": f"Storage '{storage}' not available"})
                base_dir_real = os.path.realpath(base_dir)

                if path:
                    full_path = self._safe_resolve_path(base_dir, path)
                    if not full_path:
                        return json.dumps({"error": "Invalid path"})
                else:
                    full_path = base_dir_real

                if not os.path.exists(full_path):
                    return json.dumps({"error": "Path not found"})

                # List files and directories
                items = []
                for entry in os.scandir(full_path):
                    # Only show user files (skip system files, .db, __pycache__, etc.)
                    if entry.name.startswith('.') or entry.name.endswith(('.db', '.pyc')):
                        continue

                    # For files, show all types (filtering handled by view endpoint)
                    # Skip system files only
                    if entry.is_file():
                        pass  # Allow all file types to be listed

                    stat = entry.stat()
                    items.append({
                        "name": entry.name,
                        "type": "dir" if entry.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "path": os.path.relpath(os.path.realpath(entry.path), base_dir_real),
                    })

                # Sort: directories first, then by name
                items.sort(key=lambda x: (x["type"] != "dir", x["name"]))

                return json.dumps({
                    "success": True,
                    "path": os.path.relpath(full_path, base_dir_real) if full_path != base_dir_real else "",
                    "items": items,
                })

            except Exception as e:
                return json.dumps({"error": "Failed to list files"})

        @self._app.route("/api/files/view", method="GET")
        def view_file():
            """Read file contents for viewing."""
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            response.content_type = "application/json"

            storage = request.query.get("storage", "inkling")
            path = request.query.get("path", "")
            if not path:
                return json.dumps({"error": "No path specified"})

            try:
                # Get base directory for storage location
                base_dir = get_base_dir(storage)
                if not base_dir:
                    return json.dumps({"error": f"Storage '{storage}' not available"})

                full_path = self._safe_resolve_path(base_dir, path)
                if not full_path:
                    return json.dumps({"error": "Invalid path"})

                if not os.path.isfile(full_path):
                    return json.dumps({"error": "Not a file"})

                # Check file extension - support common code and text files
                SUPPORTED_EXTENSIONS = {
                    # Text/Docs
                    '.txt', '.md', '.rst', '.log',
                    # Data
                    '.json', '.yaml', '.yml', '.csv', '.xml', '.toml',
                    # Code
                    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.sass',
                    '.sh', '.bash', '.zsh', '.fish',
                    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.rb', '.php',
                    # Config
                    '.conf', '.ini', '.cfg', '.env',
                    # Other
                    '.sql', '.graphql', '.vue', '.svelte'
                }

                ext = os.path.splitext(full_path)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS and ext != '':  # Allow extensionless files
                    return json.dumps({"error": f"File type '{ext}' not supported for viewing"})

                # Read file (limit size to prevent memory issues)
                max_size = 1024 * 1024  # 1MB
                file_size = os.path.getsize(full_path)

                if file_size > max_size:
                    return json.dumps({"error": f"File too large ({file_size} bytes, max 1MB)"})

                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                return json.dumps({
                    "success": True,
                    "content": content,
                    "name": os.path.basename(full_path),
                    "ext": ext,
                })

            except Exception as e:
                return json.dumps({"error": "Failed to read file"})

        @self._app.route("/api/files/download")
        def download_file():
            """Download a file."""
            auth_err = self._require_api_auth()
            if auth_err:
                return auth_err
            storage = request.query.get("storage", "inkling")
            path = request.query.get("path", "")
            if not path:
                return "No path specified"

            try:
                # Get base directory for storage location
                base_dir = get_base_dir(storage)
                if not base_dir:
                    return f"Storage '{storage}' not available"

                full_path = self._safe_resolve_path(base_dir, path)
                if not full_path:
                    return "Invalid path"

                if not os.path.isfile(full_path):
                    return "Not a file"

                # Check file extension (match view endpoint restrictions)
                ext = os.path.splitext(full_path)[1].lower()
                if ext not in ['.txt', '.md', '.csv', '.json', '.log']:
                    return "File type not supported for download"

                # Use Bottle's static_file for proper download handling
                directory = os.path.dirname(full_path)
                filename = os.path.basename(full_path)
                return static_file(filename, root=directory, download=True)

            except Exception as e:
                return "An error occurred"

        @self._app.route("/api/files/edit", method="POST")
        def edit_file():
            """Edit/update file contents."""
            response.content_type = "application/json"

            storage = request.query.get("storage", "inkling")
            path = request.query.get("path", "")

            if not path:
                return json.dumps({"error": "No path specified"})

            try:
                # Get request body (new file content)
                data = request.json
                if not data or "content" not in data:
                    return json.dumps({"error": "No content provided"})

                new_content = data["content"]

                # Get base directory for storage location
                base_dir = get_base_dir(storage)
                if not base_dir:
                    return json.dumps({"error": f"Storage '{storage}' not available"})

                full_path = os.path.normpath(os.path.join(base_dir, path))

                # Security: Ensure path is within base directory
                if not full_path.startswith(base_dir):
                    return json.dumps({"error": "Invalid path"})

                if not os.path.isfile(full_path):
                    return json.dumps({"error": "Not a file"})

                # Check file extension (same as view endpoint)
                SUPPORTED_EXTENSIONS = {
                    # Text/Docs
                    '.txt', '.md', '.rst', '.log',
                    # Data
                    '.json', '.yaml', '.yml', '.csv', '.xml', '.toml',
                    # Code
                    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.sass',
                    '.sh', '.bash', '.zsh', '.fish',
                    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.rb', '.php',
                    # Config
                    '.conf', '.ini', '.cfg', '.env',
                    # Other
                    '.sql', '.graphql', '.vue', '.svelte'
                }

                ext = os.path.splitext(full_path)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS and ext != '':
                    return json.dumps({"error": f"File type '{ext}' cannot be edited"})

                # Create backup before editing
                backup_path = full_path + ".bak"
                import shutil
                shutil.copy2(full_path, backup_path)

                # Write new content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                return json.dumps({
                    "success": True,
                    "message": f"File '{os.path.basename(full_path)}' updated successfully",
                    "backup": os.path.basename(backup_path)
                })

            except Exception as e:
                return json.dumps({"error": str(e)})

        @self._app.route("/api/files/delete", method="POST")
        def delete_file():
            """Delete a file with confirmation."""
            response.content_type = "application/json"

            storage = request.query.get("storage", "inkling")
            path = request.query.get("path", "")

            if not path:
                return json.dumps({"error": "No path specified"})

            try:
                # Get request body (confirmation flag)
                data = request.json
                if not data or not data.get("confirmed", False):
                    return json.dumps({"error": "Deletion not confirmed"})

                # Get base directory for storage location
                base_dir = get_base_dir(storage)
                if not base_dir:
                    return json.dumps({"error": f"Storage '{storage}' not available"})

                full_path = os.path.normpath(os.path.join(base_dir, path))

                # Security: Ensure path is within base directory
                if not full_path.startswith(base_dir):
                    return json.dumps({"error": "Invalid path"})

                if not os.path.exists(full_path):
                    return json.dumps({"error": "File not found"})

                # Prevent deleting critical system files
                filename = os.path.basename(full_path)
                if filename in ['tasks.db', 'conversation.json', 'memory.db', 'personality.json']:
                    return json.dumps({"error": "Cannot delete system file"})

                # Delete the file
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    return json.dumps({
                        "success": True,
                        "message": f"File '{filename}' deleted successfully"
                    })
                elif os.path.isdir(full_path):
                    # Optional: Allow directory deletion (empty only)
                    if len(os.listdir(full_path)) == 0:
                        os.rmdir(full_path)
                        return json.dumps({
                            "success": True,
                            "message": f"Directory '{filename}' deleted successfully"
                        })
                    else:
                        return json.dumps({"error": "Directory not empty"})

            except Exception as e:
                return json.dumps({"error": str(e)})

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task to JSON-serializable dict."""
        from datetime import datetime

        data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": datetime.fromtimestamp(task.created_at).isoformat(),
            "tags": task.tags,
            "project": task.project,
        }

        if task.due_date:
            data["due_date"] = datetime.fromtimestamp(task.due_date).isoformat()
            data["days_until_due"] = task.days_until_due
            data["is_overdue"] = task.is_overdue

        if task.completed_at:
            data["completed_at"] = datetime.fromtimestamp(task.completed_at).isoformat()

        if task.subtasks:
            data["subtasks"] = task.subtasks
            data["subtasks_completed"] = task.subtasks_completed
            data["completion_percentage"] = task.completion_percentage

        return data

    def _get_face_str(self) -> str:
        """Get current face as string."""
        face_name = self.personality.face
        return self._faces.get(face_name, self._faces["default"])

    def _save_config_file(self, new_settings: dict) -> None:
        """Save settings to config.local.yml"""
        from pathlib import Path
        import yaml

        config_file = Path("config.local.yml")

        # Load existing config or start fresh
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update device name
        if "name" in new_settings:
            if "device" not in config:
                config["device"] = {}
            config["device"]["name"] = new_settings["name"]

        # Update personality traits
        if "traits" in new_settings:
            if "personality" not in config:
                config["personality"] = {}
            config["personality"].update(new_settings["traits"])

        # Update display settings
        if "display" in new_settings:
            if "display" not in config:
                config["display"] = {}

            display_settings = new_settings["display"]

            # Update dark mode
            if "dark_mode" in display_settings:
                config["display"]["dark_mode"] = display_settings["dark_mode"]

            # Update screensaver settings
            if "screensaver" in display_settings:
                if "screensaver" not in config["display"]:
                    config["display"]["screensaver"] = {}
                config["display"]["screensaver"].update(display_settings["screensaver"])

        # Update AI configuration
        if "ai" in new_settings:
            if "ai" not in config:
                config["ai"] = {}

            ai_settings = new_settings["ai"]

            # Update primary provider
            if "primary" in ai_settings:
                config["ai"]["primary"] = ai_settings["primary"]

            # Update provider-specific settings
            for provider in ["anthropic", "openai", "gemini", "ollama"]:
                if provider in ai_settings:
                    if provider not in config["ai"]:
                        config["ai"][provider] = {}
                    config["ai"][provider].update(ai_settings[provider])

            # Update budget settings
            if "budget" in ai_settings:
                if "budget" not in config["ai"]:
                    config["ai"]["budget"] = {}
                config["ai"]["budget"].update(ai_settings["budget"])

        # Write back to file
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

    # Command handlers (all prefixed with _cmd_)

    def _cmd_help(self) -> Dict[str, Any]:
        """Show all available commands."""
        categories = get_commands_by_category()

        response_lines = ["INKLING COMMANDS\n"]

        category_titles = {
            "info": "Status & Info",
            "personality": "Personality",
            "tasks": "Task Management",
            "scheduler": "Scheduler",
            "system": "System",
            "display": "Display",
            "session": "Session",
        }

        for cat_key in ["info", "personality", "tasks", "scheduler", "system", "display", "session"]:
            if cat_key in categories:
                response_lines.append(f"\n{category_titles.get(cat_key, cat_key.title())}:")
                for cmd in categories[cat_key]:
                    usage = f"/{cmd.name}"
                    if cmd.name in ("face", "ask", "task", "done", "cancel", "delete", "schedule", "bash"):
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
            "response": f"Energy: [{bar}] {energy:.0%}\n\nMood: {mood.title()} (intensity: {intensity:.0%})\nMood base energy: {self.personality.mood.current.energy:.0%}\n\n*Tip: Play commands (/walk, /dance, /exercise) boost energy!*",
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

    def _cmd_tasks(self, args: str = "") -> Dict[str, Any]:
        """List tasks with optional filters."""
        if not self.task_manager:
            return {
                "response": "Task manager not available.",
                "error": True
            }

        from core.tasks import TaskStatus, Priority

        # Parse arguments for filters
        status_filter = None
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
            status=status_filter
        )

        if not tasks:
            return {
                "response": "No tasks found. Use the Tasks page to create tasks, or /task <title> to create via chat.",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        # Priority icons
        priority_icons = {
            Priority.LOW: "○",
            Priority.MEDIUM: "●",
            Priority.HIGH: "●●",
            Priority.URGENT: "‼",
        }

        # Format tasks list
        response = "TASKS\n\n"
        for task in tasks:
            # Status emoji
            if task.status == TaskStatus.COMPLETED:
                status_emoji = "✅"
            elif task.status == TaskStatus.IN_PROGRESS:
                status_emoji = "⏳"
            else:
                status_emoji = "□"

            # Priority icon
            priority_icon = priority_icons.get(task.priority, "●")

            # Overdue indicator
            overdue = " [OVERDUE]" if task.is_overdue else ""

            response += f"{status_emoji} {priority_icon} [{task.id[:8]}] {task.title}{overdue}\n"
            if task.description:
                response += f"   {task.description[:60]}{'...' if len(task.description) > 60 else ''}\n"

        response += f"\nTotal: {len(tasks)} tasks"
        if status_filter:
            response += f" ({status_filter.value})"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_taskstats(self) -> Dict[str, Any]:
        """Show task statistics."""
        if not self.task_manager:
            return {
                "response": "Task manager not available.",
                "error": True
            }

        stats = self.task_manager.get_stats()

        response = "TASK STATISTICS\n\n"
        response += f"Overview:\n"
        response += f"  Total tasks:     {stats['total']}\n"
        response += f"  Pending:         {stats['pending']}\n"
        response += f"  In Progress:     {stats['in_progress']}\n"
        response += f"  Completed:       {stats['completed']}\n"

        if stats['overdue'] > 0:
            response += f"  ⚠️ Overdue:       {stats['overdue']}\n"

        if stats['due_soon'] > 0:
            response += f"  ⏰ Due soon (3d): {stats['due_soon']}\n"

        # 30-day completion rate
        completion_rate = stats['completion_rate_30d'] * 100
        response += f"\n30-Day Performance:\n"
        response += f"  Completion rate: {completion_rate:.0f}%\n"

        # Level and XP info
        level = self.personality.progression.level
        xp = self.personality.progression.xp
        streak = self.personality.progression.current_streak

        response += f"\nProgression:\n"
        response += f"  Level {level} | {xp} XP\n"

        if streak > 0:
            streak_emoji = "🔥" if streak >= 7 else "✨"
            response += f"  {streak_emoji} {streak} day streak\n"

        return {
            "response": response,
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

    def _cmd_screensaver(self, args: str = "") -> Dict[str, Any]:
        """Toggle screen saver."""
        if args.lower() == "on":
            self.display.configure_screensaver(enabled=True)
            response = "✓ Screen saver enabled"
        elif args.lower() == "off":
            self.display.configure_screensaver(enabled=False)
            if self.display._screensaver_active and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self.display.stop_screensaver(),
                    self._loop
                )
            response = "✓ Screen saver disabled"
        else:
            # Toggle
            current = self.display._screensaver_enabled
            self.display.configure_screensaver(enabled=not current)
            status = "enabled" if not current else "disabled"
            response = f"✓ Screen saver {status}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_darkmode(self, args: str = "") -> Dict[str, Any]:
        """Toggle dark mode."""
        if args.lower() == "on":
            self.display._dark_mode = True
            response = "✓ Dark mode enabled"
        elif args.lower() == "off":
            self.display._dark_mode = False
            response = "✓ Dark mode disabled"
        else:
            # Toggle
            self.display._dark_mode = not self.display._dark_mode
            status = "enabled" if self.display._dark_mode else "disabled"
            response = f"✓ Dark mode {status}"

        # Force refresh to apply dark mode change
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(force=True),
                self._loop
            )

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_schedule(self, args: str = "") -> Dict[str, Any]:
        """Manage scheduled tasks."""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return {
                "response": "Scheduler not available.\n\nEnable in config.yml under 'scheduler.enabled: true'",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "error": True
            }

        if not args:
            # List all scheduled tasks
            tasks = self.scheduler.list_tasks()

            if not tasks:
                return {
                    "response": "No scheduled tasks configured.\n\nAdd tasks in config.yml under 'scheduler.tasks'",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }

            response = "SCHEDULED TASKS\n\n"
            next_runs = self.scheduler.get_next_run_times()

            for task in tasks:
                status_icon = "✓" if task.enabled else "✗"
                response += f"{status_icon} {task.name}\n"
                response += f"   Schedule: {task.schedule_expr}\n"
                response += f"   Action:   {task.action}\n"

                if task.enabled:
                    next_run = next_runs.get(task.name, "Unknown")
                    response += f"   Next run: {next_run}\n"

                if task.last_run > 0:
                    import time
                    from datetime import datetime
                    last_run_dt = datetime.fromtimestamp(task.last_run)
                    response += f"   Last run: {last_run_dt.strftime('%Y-%m-%d %H:%M:%S')} ({task.run_count} times)\n"

                if task.last_error:
                    response += f"   Error: {task.last_error}\n"

                response += "\n"

            return {
                "response": response,
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        # Parse subcommands
        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()

        if subcmd == "list":
            # Redirect to list (same as no args)
            return self._cmd_schedule()

        elif subcmd == "enable":
            if len(parts) < 2:
                return {
                    "response": "Usage: /schedule enable <task_name>",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

            task_name = parts[1]
            if self.scheduler.enable_task(task_name):
                return {
                    "response": f"✓ Enabled: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }
            else:
                return {
                    "response": f"Task not found: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

        elif subcmd == "disable":
            if len(parts) < 2:
                return {
                    "response": "Usage: /schedule disable <task_name>",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

            task_name = parts[1]
            if self.scheduler.disable_task(task_name):
                return {
                    "response": f"✓ Disabled: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }
            else:
                return {
                    "response": f"Task not found: {task_name}",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                    "error": True
                }

        else:
            return {
                "response": f"Unknown subcommand: {subcmd}\n\nAvailable commands:\n  /schedule           - List all scheduled tasks\n  /schedule list      - List all scheduled tasks\n  /schedule enable <name>  - Enable a task\n  /schedule disable <name> - Disable a task",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "error": True
            }

    def _cmd_ask(self, args: str) -> Dict[str, Any]:
        """Handle explicit chat command."""
        if not args:
            return {"response": "Usage: /ask <your message>\n\nOr just type without / to chat!", "error": True}

        return self._handle_chat_sync(args)

    def _cmd_bash(self, args: str) -> Dict[str, Any]:
        """Disable bash execution in web UI."""
        return {
            "response": "The /bash command is disabled in the web UI.",
            "error": True,
        }

    def _cmd_wifi(self) -> Dict[str, Any]:
        """Show WiFi status and saved networks."""
        from core.wifi_utils import get_current_wifi, get_saved_networks, is_btcfg_running, get_wifi_bars

        status = get_current_wifi()
        output = ["**WiFi Status**\n"]

        # Current connection
        if status.connected and status.ssid:
            bars = get_wifi_bars(status.signal_strength)
            output.append(f"✓ Connected to: **{status.ssid}**")
            output.append(f"  Signal: {bars} {status.signal_strength}%")
            if status.ip_address:
                output.append(f"  IP: {status.ip_address}")
            if status.frequency:
                output.append(f"  Band: {status.frequency}")
        else:
            output.append("✗ Not connected")

        output.append("")

        # BLE service status
        if is_btcfg_running():
            output.append("🔵 **BLE Configuration: Running** (15 min window)")
            output.append("   Use BTBerryWifi app to configure WiFi")
        else:
            output.append("🔵 BLE Configuration: Stopped")
            output.append("   Use /btcfg to start configuration service")

        output.append("")

        # Saved networks
        saved = get_saved_networks()
        if saved:
            output.append(f"**Saved Networks ({len(saved)}):**")
            for ssid in saved:
                icon = "●" if status.connected and status.ssid == ssid else "○"
                output.append(f"  {icon} {ssid}")
        else:
            output.append("*No saved networks*")

        output.append("")
        output.append("*Tip: Use /wifiscan to find nearby networks*")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    def _cmd_btcfg(self) -> Dict[str, Any]:
        """Start BTBerryWifi BLE configuration service."""
        from core.wifi_utils import start_btcfg

        success, message = start_btcfg()

        return {
            "response": message,
            "face": self.personality.face,
            "error": not success,
        }

    def _cmd_wifiscan(self) -> Dict[str, Any]:
        """Scan for nearby WiFi networks."""
        from core.wifi_utils import scan_networks, get_current_wifi

        networks = scan_networks()
        current = get_current_wifi()

        if not networks:
            return {
                "response": "No networks found or permission denied.\n\n*Tip: Scanning requires sudo access*",
                "face": self.personality.face,
                "error": True,
            }

        output = [f"**Nearby Networks ({len(networks)})**\n"]

        for net in networks:
            # Visual signal indicator
            if net.signal_strength >= 80:
                signal_icon = "▂▄▆█"
            elif net.signal_strength >= 60:
                signal_icon = "▂▄▆"
            elif net.signal_strength >= 40:
                signal_icon = "▂▄"
            elif net.signal_strength >= 20:
                signal_icon = "▂"
            else:
                signal_icon = "○"

            # Connection indicator
            connected = current.connected and current.ssid == net.ssid
            conn_icon = "●" if connected else " "

            # Security badge
            if net.security == "Open":
                security_badge = "[OPEN]"
            elif net.security == "WPA3":
                security_badge = "[WPA3]"
            elif net.security == "WPA2":
                security_badge = "[WPA2]"
            else:
                security_badge = f"[{net.security}]"

            output.append(f"{conn_icon} {signal_icon} {net.signal_strength:3}% {security_badge} {net.ssid}")

        output.append("")
        output.append("*Use /btcfg to start BLE configuration service*")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    # ================
    # Play Commands
    # ================

    async def _play_action_web(
        self,
        action_name: str,
        emote_text: str,
        mood: Mood,
        intensity: float,
        faces: list,
        xp_source: XPSource,
    ) -> tuple:
        """
        Execute a play action with animation and rewards (web version).

        Returns:
            (xp_gained, energy_change) tuple
        """
        # Update interaction time
        self.personality._last_interaction = time.time()

        # Show animation on display
        if self.display:
            for i, face in enumerate(faces):
                is_last = (i == len(faces) - 1)
                text = f"{action_name.title()}!"
                await self.display.update(
                    face=face,
                    text=text,
                    force=True,
                )
                if not is_last:
                    await asyncio.sleep(0.8)

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

        # Calculate energy change
        old_energy = old_mood.energy * old_intensity
        new_energy = self.personality.energy
        energy_change = new_energy - old_energy

        return (xp_gained if awarded else 0, energy_change)

    def _cmd_walk(self) -> Dict[str, Any]:
        """Go for a walk."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "walk",
                "goes for a walk",
                Mood.CURIOUS,
                0.7,
                ["look_l", "look_r", "happy"],
                XPSource.PLAY_WALK,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} goes for a walk around the neighborhood*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "happy",
        }

    def _cmd_dance(self) -> Dict[str, Any]:
        """Dance around."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "dance",
                "dances enthusiastically",
                Mood.EXCITED,
                0.9,
                ["excited", "love", "wink", "excited"],
                XPSource.PLAY_DANCE,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} dances enthusiastically*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "excited",
        }

    def _cmd_exercise(self) -> Dict[str, Any]:
        """Exercise and stretch."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "exercise",
                "does some stretches",
                Mood.HAPPY,
                0.8,
                ["working", "intense", "awake", "success"],
                XPSource.PLAY_EXERCISE,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} does some stretches and exercises*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "success",
        }

    def _cmd_play(self) -> Dict[str, Any]:
        """Play with a toy."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "play",
                "plays with a toy",
                Mood.HAPPY,
                0.8,
                ["excited", "happy", "wink"],
                XPSource.PLAY_GENERAL,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} plays with a toy*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "happy",
        }

    def _cmd_pet(self) -> Dict[str, Any]:
        """Get petted."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "pet",
                "enjoys being petted",
                Mood.GRATEFUL,
                0.7,
                ["love", "happy", "grateful"],
                XPSource.PLAY_PET,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} enjoys being petted*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "grateful",
        }

    def _cmd_rest(self) -> Dict[str, Any]:
        """Take a short rest."""
        xp_gained, energy_change = asyncio.run_coroutine_threadsafe(
            self._play_action_web(
                "rest",
                "takes a short rest",
                Mood.COOL,
                0.4,
                ["cool", "sleep", "sleepy"],
                XPSource.PLAY_REST,
            ),
            self._loop
        ).result(timeout=5.0)

        response = f"*{self.personality.name} takes a short rest*\n\n"
        if xp_gained > 0:
            response += f"✨ +{xp_gained} XP | Energy {energy_change:+.0%}"
        else:
            response += f"Energy {energy_change:+.0%}"

        return {
            "response": response,
            "face": "sleepy",
        }

    def _cmd_thoughts(self) -> Dict[str, Any]:
        """Show recent autonomous thoughts."""
        from pathlib import Path

        log_path = Path("~/.inkling/thoughts.log").expanduser()
        if not log_path.exists():
            return {
                "response": "No thoughts yet. Thoughts are generated automatically over time.",
                "face": self.personality.face,
            }

        lines = log_path.read_text().strip().splitlines()
        recent = lines[-10:]

        output = [f"**Recent Thoughts** ({len(recent)} of {len(lines)})\n"]
        for line in recent:
            parts = line.split(" | ", 1)
            if len(parts) == 2:
                ts, thought = parts
                output.append(f"`{ts}` {thought}")
            else:
                output.append(line)

        if self.personality.last_thought:
            output.append(f"\n*Latest: {self.personality.last_thought}*")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    def _cmd_find(self, args: str = "") -> Dict[str, Any]:
        """Search tasks by keyword."""
        if not args.strip():
            return {"response": "Usage: `/find <keyword>`", "face": self.personality.face}

        if not self.task_manager:
            return {"response": "Task manager not available.", "face": self.personality.face, "error": True}

        query = args.strip().lower()
        all_tasks = self.task_manager.list_tasks()
        matches = [
            t for t in all_tasks
            if query in t.title.lower()
            or (t.description and query in t.description.lower())
            or any(query in tag.lower() for tag in t.tags)
        ]

        if not matches:
            return {"response": f"No tasks found matching '{args.strip()}'.", "face": self.personality.face}

        status_icons = {"pending": "📋", "in_progress": "⏳", "completed": "✅", "cancelled": "❌"}
        output = [f"**Search Results** ({len(matches)} matches)\n"]
        for task in matches:
            icon = status_icons.get(task.status.value, "·")
            tags = " ".join(f"#{t}" for t in task.tags) if task.tags else ""
            output.append(f"{icon} `{task.id[:8]}` **{task.title}** [{task.priority.value}]")
            if task.description:
                output.append(f"   {task.description[:80]}")
            if tags:
                output.append(f"   {tags}")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    def _cmd_memory(self) -> Dict[str, Any]:
        """Show memory stats and recent entries."""
        from core.memory import MemoryStore

        store = MemoryStore()
        try:
            store.initialize()

            total = store.count()
            user_count = store.count(MemoryStore.CATEGORY_USER)
            pref_count = store.count(MemoryStore.CATEGORY_PREFERENCE)
            fact_count = store.count(MemoryStore.CATEGORY_FACT)
            event_count = store.count(MemoryStore.CATEGORY_EVENT)

            output = ["**Memory Store**\n"]
            output.append(f"Total: **{total}** memories")
            output.append(f"  User info: {user_count}")
            output.append(f"  Preferences: {pref_count}")
            output.append(f"  Facts: {fact_count}")
            output.append(f"  Events: {event_count}")

            recent = store.recall_recent(limit=5)
            if recent:
                output.append("\n**Recent:**")
                for mem in recent:
                    output.append(f"  `[{mem.category}]` {mem.key}: {mem.value[:60]}")

            important = store.recall_important(limit=3)
            if important:
                output.append("\n**Most Important:**")
                for mem in important:
                    output.append(f"  ★{mem.importance:.1f} `[{mem.category}]` {mem.key}: {mem.value[:60]}")

            return {
                "response": "\n".join(output),
                "face": self.personality.face,
            }
        finally:
            store.close()

    def _cmd_settings(self) -> Dict[str, Any]:
        """Show current settings (redirects to settings page in web mode)."""
        return {
            "response": "Visit the [Settings](/settings) page to view and change settings.",
            "face": self.personality.face,
        }

    def _cmd_backup(self) -> Dict[str, Any]:
        """Create a backup of Inkling data."""
        import shutil
        from pathlib import Path
        from datetime import datetime

        data_dir = Path("~/.inkling").expanduser()
        if not data_dir.exists():
            return {"response": "No data directory found.", "face": self.personality.face, "error": True}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"inkling_backup_{timestamp}"
        backup_path = data_dir.parent / f"{backup_name}.tar.gz"

        try:
            shutil.make_archive(
                str(data_dir.parent / backup_name),
                'gztar',
                root_dir=str(data_dir.parent),
                base_dir='.inkling'
            )
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            return {
                "response": f"Backup created!\n\n**File:** `{backup_path}`\n**Size:** {size_mb:.1f} MB",
                "face": "happy",
            }
        except Exception as e:
            return {"response": f"Backup failed: {e}", "face": self.personality.face, "error": True}

    def _cmd_journal(self) -> Dict[str, Any]:
        """Show recent journal entries."""
        from pathlib import Path

        journal_path = Path("~/.inkling/journal.log").expanduser()
        if not journal_path.exists():
            return {
                "response": "No journal entries yet. Journal entries are written daily by the heartbeat system.",
                "face": self.personality.face,
            }

        lines = journal_path.read_text().strip().splitlines()
        recent = lines[-10:]

        output = [f"**Journal** ({len(recent)} of {len(lines)} entries)\n"]
        for line in recent:
            parts = line.split(" | ", 1)
            if len(parts) == 2:
                ts, entry = parts
                output.append(f"`{ts}` {entry}")
            else:
                output.append(line)

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

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
        if cmd_obj.name in ("face", "dream", "ask", "schedule", "bash", "task", "done", "cancel", "delete", "tasks", "find"):
            return handler(args) if args or cmd_obj.name in ("tasks", "schedule", "find") else handler()
        else:
            return handler()

    def _handle_chat_sync(self, message: str) -> Dict[str, Any]:
        """Handle chat message (sync wrapper for async brain)."""
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
            xp_awarded = self.personality.on_interaction(
                positive=True,
                chat_quality=result.chat_quality,
                user_message=message,
            )

            # Update display with Pwnagotchi UI (with pagination for long messages)
            from core.ui import word_wrap, MESSAGE_MAX_LINES
            # Use 32 chars/line to better match pixel-based rendering (250px display ~32-35 chars)
            lines = word_wrap(result.content, 32)
            if len(lines) > MESSAGE_MAX_LINES:
                # Use paginated display for long responses
                asyncio.run_coroutine_threadsafe(
                    self.display.show_message_paginated(
                        text=result.content,
                        face=self.personality.face,
                        page_delay=self.display.pagination_loop_seconds,
                        loop=True,
                    ),
                    self._loop
                )
            else:
                # Single page display
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
                "meta": (
                    f"{result.provider} | {result.tokens_used} tokens | +{xp_awarded} XP"
                    if xp_awarded
                    else f"{result.provider} | {result.tokens_used} tokens"
                ),
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

        # Start ngrok tunnel if enabled
        ngrok_tunnel = None
        ngrok_url = None
        if self._config.get("network", {}).get("ngrok", {}).get("enabled", False):
            try:
                from pyngrok import ngrok, conf

                # Set auth token if provided
                auth_token = self._config.get("network", {}).get("ngrok", {}).get("auth_token")
                if auth_token:
                    conf.get_default().auth_token = auth_token

                # Start tunnel
                ngrok_tunnel = ngrok.connect(self.port, "http")
                ngrok_url = ngrok_tunnel.public_url
                print(f"🌐 Ngrok tunnel: {ngrok_url}")
                if self._auth_enabled:
                    print(f"🔐 Password protection enabled (SERVER_PW)")
            except ImportError:
                print("⚠️  pyngrok not installed. Run: pip install pyngrok")
            except Exception as e:
                print(f"⚠️  Failed to start ngrok: {e}")

        # Show startup message
        display_text = f"Web UI at {ngrok_url or f'http://{self.host}:{self.port}'}"
        await self.display.update(
            face="excited",
            text=display_text,
            mood_text="Excited",
        )
        await self.display.start_auto_refresh()

        print(f"\nWeb UI available at http://{self.host}:{self.port}")
        if ngrok_url:
            print(f"Public URL: {ngrok_url}")
        if self._auth_enabled:
            print("🔐 Authentication required")
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
        try:
            while self._running:
                await asyncio.sleep(1)
                self.personality.update()
        finally:
            await self.display.stop_auto_refresh()
            # Disconnect ngrok tunnel on exit
            if ngrok_tunnel:
                try:
                    from pyngrok import ngrok
                    ngrok.disconnect(ngrok_tunnel.public_url)
                    print("Ngrok tunnel closed")
                except Exception:
                    pass

    def stop(self) -> None:
        """Stop the web server."""
        self._running = False
