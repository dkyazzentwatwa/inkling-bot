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
from core.personality import Personality
from core.commands import COMMANDS, get_command, get_commands_by_category
from core.tasks import TaskManager, Task, TaskStatus, Priority
from core.crypto import Identity
from core.memory import MemoryStore
from core.focus import FocusManager

# Command handlers
from modes.web.commands.play import PlayCommands
from modes.web.commands.info import InfoCommands
from modes.web.commands.session import SessionCommands
from modes.web.commands.tasks import TaskCommands
from modes.web.commands.system import SystemCommands
from modes.web.commands.scheduler import SchedulerCommands
from modes.web.commands.display import DisplayCommands
from modes.web.commands.utilities import UtilityCommands
from modes.web.commands.focus import FocusCommands


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
        memory_store: Optional[MemoryStore] = None,
        focus_manager: Optional[FocusManager] = None,
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
        self.memory_store = memory_store
        self.focus_manager = focus_manager
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

        # Initialize command handlers
        self._play_cmds = PlayCommands(self)
        self._info_cmds = InfoCommands(self)
        self._session_cmds = SessionCommands(self)
        self._task_cmds = TaskCommands(self)
        self._system_cmds = SystemCommands(self)
        self._scheduler_cmds = SchedulerCommands(self)
        self._display_cmds = DisplayCommands(self)
        self._utility_cmds = UtilityCommands(self)
        self._focus_cmds = FocusCommands(self)

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
                face=self._get_face_str(),
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
                face=self._get_face_str(),
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
                face=self._get_face_str(),
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
                "focus": self.focus_manager.get_display_snapshot() if self.focus_manager else {"focus_active": False},
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
        return self._info_cmds.help()

    def _cmd_mood(self) -> Dict[str, Any]:
        """Show current mood."""
        return self._info_cmds.mood()

    def _cmd_energy(self) -> Dict[str, Any]:
        """Show energy level."""
        return self._play_cmds.energy()

    def _cmd_traits(self) -> Dict[str, Any]:
        """Show personality traits."""
        return self._info_cmds.traits()

    def _cmd_stats(self) -> Dict[str, Any]:
        """Show token stats."""
        return self._info_cmds.stats()

    def _cmd_level(self) -> Dict[str, Any]:
        """Show level and progression."""
        return self._info_cmds.level()

    def _cmd_prestige(self) -> Dict[str, Any]:
        """Handle prestige (not supported in web mode)."""
        return self._info_cmds.prestige()

    def _cmd_tasks(self, args: str = "") -> Dict[str, Any]:
        """List tasks with optional filters."""
        return self._task_cmds.tasks(args)

    def _cmd_task(self, args: str) -> Dict[str, Any]:
        """Create or show a task."""
        return self._task_cmds.task(args)

    def _cmd_done(self, args: str) -> Dict[str, Any]:
        """Mark a task as complete."""
        return self._task_cmds.done(args)

    def _cmd_cancel(self, args: str) -> Dict[str, Any]:
        """Cancel a task."""
        return self._task_cmds.cancel(args)

    def _cmd_delete(self, args: str) -> Dict[str, Any]:
        """Delete a task permanently."""
        return self._task_cmds.delete(args)

    def _cmd_taskstats(self) -> Dict[str, Any]:
        """Show task statistics."""
        return self._task_cmds.taskstats()

    def _cmd_system(self) -> Dict[str, Any]:
        """Show system stats."""
        return self._system_cmds.system()

    def _cmd_config(self) -> Dict[str, Any]:
        """Show AI configuration."""
        return self._system_cmds.config()

    def _cmd_history(self) -> Dict[str, Any]:
        """Show recent messages."""
        return self._session_cmds.history()

    def _cmd_clear(self) -> Dict[str, Any]:
        """Clear conversation history."""
        return self._session_cmds.clear()

    def _cmd_face(self, args: str) -> Dict[str, Any]:
        """Test a face expression."""
        return self._display_cmds.face(args)

    def _cmd_faces(self) -> Dict[str, Any]:
        """List all available faces."""
        return self._display_cmds.faces()

    def _cmd_refresh(self) -> Dict[str, Any]:
        """Force display refresh."""
        return self._display_cmds.refresh()

    def _cmd_screensaver(self, args: str = "") -> Dict[str, Any]:
        """Toggle screen saver."""
        return self._display_cmds.screensaver(args)

    def _cmd_darkmode(self, args: str = "") -> Dict[str, Any]:
        """Toggle dark mode."""
        return self._display_cmds.darkmode(args)

    def _cmd_schedule(self, args: str = "") -> Dict[str, Any]:
        """Manage scheduled tasks."""
        return self._scheduler_cmds.schedule(args)

    def _cmd_ask(self, args: str) -> Dict[str, Any]:
        """Handle explicit chat command."""
        return self._session_cmds.ask(args)

    def _cmd_bash(self, args: str) -> Dict[str, Any]:
        """Disable bash execution in web UI."""
        return self._system_cmds.bash(args)

    def _cmd_wifi(self) -> Dict[str, Any]:
        """Show WiFi status and saved networks."""
        return self._system_cmds.wifi()

    def _cmd_btcfg(self) -> Dict[str, Any]:
        """Start BTBerryWifi BLE configuration service."""
        return self._system_cmds.btcfg()

    def _cmd_wifiscan(self) -> Dict[str, Any]:
        """Scan for nearby WiFi networks."""
        return self._system_cmds.wifiscan()

    # ================
    # Play Commands
    # ================

    def _cmd_walk(self) -> Dict[str, Any]:
        """Go for a walk."""
        return self._play_cmds.walk()

    def _cmd_dance(self) -> Dict[str, Any]:
        """Dance around."""
        return self._play_cmds.dance()

    def _cmd_exercise(self) -> Dict[str, Any]:
        """Exercise and stretch."""
        return self._play_cmds.exercise()

    def _cmd_play(self) -> Dict[str, Any]:
        """Play with a toy."""
        return self._play_cmds.play()

    def _cmd_pet(self) -> Dict[str, Any]:
        """Get petted."""
        return self._play_cmds.pet()

    def _cmd_rest(self) -> Dict[str, Any]:
        """Take a short rest."""
        return self._play_cmds.rest()

    def _cmd_thoughts(self) -> Dict[str, Any]:
        """Show recent autonomous thoughts."""
        return self._utility_cmds.thoughts()

    def _cmd_find(self, args: str = "") -> Dict[str, Any]:
        """Search tasks by keyword."""
        return self._utility_cmds.find(args)

    def _cmd_memory(self) -> Dict[str, Any]:
        """Show memory stats and recent entries."""
        return self._utility_cmds.memory()

    def _cmd_settings(self) -> Dict[str, Any]:
        """Show current settings (redirects to settings page in web mode)."""
        return self._utility_cmds.settings()

    def _cmd_backup(self) -> Dict[str, Any]:
        """Create a backup of Inkling data."""
        return self._utility_cmds.backup()

    def _cmd_journal(self) -> Dict[str, Any]:
        """Show recent journal entries."""
        return self._utility_cmds.journal()

    def _cmd_focus(self, args: str = "") -> Dict[str, Any]:
        """Manage focus sessions."""
        return self._focus_cmds.focus(args)

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
        try:
            if cmd_obj.name in ("face", "dream", "ask", "schedule", "bash", "task", "done", "cancel", "delete", "tasks", "find", "focus"):
                return handler(args) if args or cmd_obj.name in ("tasks", "schedule", "find") else handler()
            else:
                return handler()
        except Exception as e:
            import traceback
            error_msg = f"Command error: {str(e)}"
            traceback.print_exc()  # Print to server logs
            return {"response": error_msg, "error": True}

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
        # Get the currently running event loop
        self._loop = asyncio.get_running_loop()

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

    # ========================================
    # Crypto Watcher Commands
    # ========================================

    def _cmd_price(self, args: str = "") -> Dict[str, Any]:
        """Check cryptocurrency price."""
        if not args:
            return {
                "response": "Usage: /price <symbol>\nExample: /price BTC",
                "face": "curious",
                "status": "info"
            }

        symbol = args.upper().strip()

        try:
            # Run async function in thread pool
            import asyncio
            from core.crypto_watcher import CryptoWatcher

            async def fetch_price():
                async with CryptoWatcher() as watcher:
                    return await watcher.get_price(symbol), watcher

            price, watcher = asyncio.run(fetch_price())

            if not price:
                return {
                    "response": f"Failed to fetch price for {symbol}",
                    "face": "sad",
                    "status": "error"
                }

            response = f"**{symbol} PRICE**\n\n"
            response += f"{watcher.format_price(price)}\n"
            response += f"Volume 24h: ${price.volume_24h:,.0f}\n"
            if price.market_cap:
                response += f"Market Cap: ${price.market_cap:,.0f}\n"
            response += f"Mood: {price.mood}"

            # Set face based on mood
            face = "excited" if price.is_pumping else "sad" if price.is_dumping else "cool"

            return {
                "response": response,
                "face": face,
                "status": "success"
            }

        except Exception as e:
            return {
                "response": f"Error fetching price: {str(e)}",
                "face": "confused",
                "status": "error"
            }

    def _cmd_chart(self, args: str = "") -> Dict[str, Any]:
        """Show TA indicators for a cryptocurrency."""
        if not args:
            return {
                "response": "Usage: /chart <symbol> [timeframe]\nExample: /chart BTC\nExample: /chart ETH 4h",
                "face": "curious",
                "status": "info"
            }

        parts = args.upper().split()
        symbol = parts[0]
        timeframe = parts[1] if len(parts) > 1 else "1h"

        try:
            import asyncio
            from core.crypto_watcher import CryptoWatcher
            from core.crypto_ta import CryptoTA

            async def fetch_chart():
                async with CryptoWatcher() as watcher:
                    ohlcv = await watcher.get_ohlcv(symbol, timeframe, 100)
                    return ohlcv

            ohlcv = asyncio.run(fetch_chart())

            if not ohlcv:
                return {
                    "response": f"Failed to fetch chart data for {symbol}",
                    "face": "sad",
                    "status": "error"
                }

            ta = CryptoTA()
            indicators = ta.calculate_indicators(ohlcv)
            patterns = ta.detect_patterns(ohlcv)
            supports, resistances = ta.get_support_resistance(ohlcv)

            signal = indicators.get_signal()

            response = f"**{symbol} TA ({timeframe})**\n\n"
            response += f"**Signal:** {signal.crypto_bro_text} {signal.emoji}\n\n"

            response += "**Indicators:**\n"
            if indicators.rsi:
                rsi_status = "oversold" if indicators.rsi < 30 else "overbought" if indicators.rsi > 70 else "neutral"
                response += f"• RSI: {indicators.rsi:.1f} ({rsi_status})\n"
            if indicators.macd:
                macd_trend = "bullish" if indicators.macd > indicators.macd_signal else "bearish"
                response += f"• MACD: {macd_trend} ({indicators.macd:.2f})\n"
            if indicators.sma_20 and indicators.sma_50:
                trend = "golden cross" if indicators.sma_20 > indicators.sma_50 else "death cross"
                response += f"• Trend: {trend}\n"

            if patterns:
                response += "\n**Patterns:**\n"
                for pattern in patterns[:3]:
                    response += f"• {pattern}\n"

            if supports and resistances:
                response += "\n**Levels:**\n"
                response += f"• Support: {', '.join([f'${s:,.0f}' for s in supports[:3]])}\n"
                response += f"• Resistance: {', '.join([f'${r:,.0f}' for r in resistances[:3]])}\n"

            face = "excited" if signal.value in ["STRONG_BUY", "BUY"] else "sad" if signal.value in ["STRONG_SELL", "SELL"] else "cool"

            return {
                "response": response,
                "face": face,
                "status": "success"
            }

        except Exception as e:
            return {
                "response": f"Error analyzing chart: {str(e)}",
                "face": "confused",
                "status": "error"
            }

    def _cmd_watch(self) -> Dict[str, Any]:
        """Show watchlist with current prices."""
        try:
            import asyncio
            from core.crypto_watcher import CryptoWatcher

            # Load watchlist from config
            config = self._config or {}
            crypto_config = config.get("crypto", {})
            watchlist = crypto_config.get("watchlist", ["BTC", "ETH", "SOL"])

            async def fetch_watchlist():
                async with CryptoWatcher() as watcher:
                    prices = await watcher.get_multiple_prices(watchlist)
                    return prices, watcher

            prices, watcher = asyncio.run(fetch_watchlist())

            if not prices:
                return {
                    "response": "Failed to fetch watchlist prices",
                    "face": "sad",
                    "status": "error"
                }

            response = "**WATCHLIST**\n\n"
            for symbol in watchlist:
                if symbol in prices:
                    price = prices[symbol]
                    response += f"{watcher.format_price(price)}\n"

            return {
                "response": response,
                "face": "cool",
                "status": "success"
            }

        except Exception as e:
            return {
                "response": f"Error fetching watchlist: {str(e)}",
                "face": "confused",
                "status": "error"
            }

    def _cmd_portfolio(self) -> Dict[str, Any]:
        """Show portfolio value and holdings."""
        try:
            import asyncio
            from core.crypto_watcher import CryptoWatcher
            from pathlib import Path
            import json

            portfolio_file = Path.home() / ".inkling" / "crypto_portfolio.json"
            if not portfolio_file.exists():
                return {
                    "response": "Portfolio is empty. Use /add to add holdings.\nExample: /add BTC 0.5",
                    "face": "curious",
                    "status": "info"
                }

            with open(portfolio_file) as f:
                holdings = json.load(f)

            if not holdings:
                return {
                    "response": "Portfolio is empty. Use /add to add holdings.",
                    "face": "curious",
                    "status": "info"
                }

            async def fetch_portfolio():
                async with CryptoWatcher() as watcher:
                    symbols = list(holdings.keys())
                    prices = await watcher.get_multiple_prices(symbols)
                    return prices

            prices = asyncio.run(fetch_portfolio())

            total_value = 0.0
            response = "**PORTFOLIO** 💎\n\n"

            for symbol, amount in holdings.items():
                if symbol in prices:
                    price = prices[symbol]
                    value = amount * price.price_usd
                    total_value += value

                    emoji = "🚀" if price.price_change_24h > 5 else "📈" if price.price_change_24h > 0 else "📉" if price.price_change_24h > -5 else "💀"
                    response += f"**{symbol}:** {amount} × ${price.price_usd:,.2f} = ${value:,.2f} ({price.price_change_24h:+.1f}%) {emoji}\n"

            response += f"\n**Total:** ${total_value:,.2f}"

            return {
                "response": response,
                "face": "excited" if total_value > 0 else "cool",
                "status": "success"
            }

        except Exception as e:
            return {
                "response": f"Error loading portfolio: {str(e)}",
                "face": "confused",
                "status": "error"
            }

    def _cmd_add(self, args: str = "") -> Dict[str, Any]:
        """Add coin to portfolio."""
        if not args:
            return {
                "response": "Usage: /add <symbol> <amount>\nExample: /add BTC 0.5",
                "face": "curious",
                "status": "info"
            }

        parts = args.upper().split()
        if len(parts) < 2:
            return {
                "response": "Please specify both symbol and amount",
                "face": "confused",
                "status": "error"
            }

        symbol = parts[0]

        try:
            amount = float(parts[1])

            from pathlib import Path
            import json

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

            return {
                "response": f"Added {amount} {symbol} to portfolio (total: {holdings[symbol]})",
                "face": "excited",
                "status": "success"
            }

        except ValueError:
            return {
                "response": "Invalid amount. Use a number (e.g., 0.5)",
                "face": "confused",
                "status": "error"
            }
        except Exception as e:
            return {
                "response": f"Error adding to portfolio: {str(e)}",
                "face": "sad",
                "status": "error"
            }

    def _cmd_remove(self, args: str = "") -> Dict[str, Any]:
        """Remove coin from portfolio."""
        if not args:
            return {
                "response": "Usage: /remove <symbol> <amount>\nExample: /remove BTC 0.1",
                "face": "curious",
                "status": "info"
            }

        parts = args.upper().split()
        if len(parts) < 2:
            return {
                "response": "Please specify both symbol and amount",
                "face": "confused",
                "status": "error"
            }

        symbol = parts[0]

        try:
            amount = float(parts[1])

            from pathlib import Path
            import json

            portfolio_file = Path.home() / ".inkling" / "crypto_portfolio.json"
            if not portfolio_file.exists():
                return {
                    "response": "Portfolio is empty",
                    "face": "sad",
                    "status": "error"
                }

            with open(portfolio_file) as f:
                holdings = json.load(f)

            if symbol not in holdings:
                return {
                    "response": f"{symbol} not in portfolio",
                    "face": "confused",
                    "status": "error"
                }

            holdings[symbol] = max(0, holdings[symbol] - amount)

            if holdings[symbol] == 0:
                del holdings[symbol]
                message = f"Removed all {symbol} from portfolio"
            else:
                message = f"Removed {amount} {symbol} (remaining: {holdings[symbol]})"

            with open(portfolio_file, 'w') as f:
                json.dump(holdings, f, indent=2)

            return {
                "response": message,
                "face": "cool",
                "status": "success"
            }

        except ValueError:
            return {
                "response": "Invalid amount",
                "face": "confused",
                "status": "error"
            }
        except Exception as e:
            return {
                "response": f"Error removing from portfolio: {str(e)}",
                "face": "sad",
                "status": "error"
            }

    def _cmd_alert(self, args: str = "") -> Dict[str, Any]:
        """Set a price alert."""
        if not args:
            return {
                "response": "Usage: /alert <symbol> <price> <above|below>\nExample: /alert BTC 70000 above",
                "face": "curious",
                "status": "info"
            }

        parts = args.split()
        if len(parts) < 3:
            return {
                "response": "Please specify symbol, price, and condition (above/below)",
                "face": "confused",
                "status": "error"
            }

        symbol = parts[0].upper()

        try:
            target_price = float(parts[1])
            condition = parts[2].lower()

            if condition not in ["above", "below"]:
                return {
                    "response": "Condition must be 'above' or 'below'",
                    "face": "confused",
                    "status": "error"
                }

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

            return {
                "response": f"🔔 Alert set: {symbol} {condition} ${target_price:,.0f}",
                "face": "excited",
                "status": "success"
            }

        except ValueError:
            return {
                "response": "Invalid price",
                "face": "confused",
                "status": "error"
            }
        except Exception as e:
            return {
                "response": f"Error setting alert: {str(e)}",
                "face": "sad",
                "status": "error"
            }

    def _cmd_alerts(self) -> Dict[str, Any]:
        """List all active price alerts."""
        try:
            from pathlib import Path
            import json

            alerts_file = Path.home() / ".inkling" / "crypto_alerts.json"
            if not alerts_file.exists():
                return {
                    "response": "No alerts set. Use /alert to create one.",
                    "face": "curious",
                    "status": "info"
                }

            with open(alerts_file) as f:
                alerts = json.load(f)

            active_alerts = [a for a in alerts if a.get("active", True)]

            if not active_alerts:
                return {
                    "response": "No active alerts.",
                    "face": "curious",
                    "status": "info"
                }

            response = "**PRICE ALERTS** 🔔\n\n"

            for alert in active_alerts:
                symbol = alert["symbol"]
                price = alert["target_price"]
                condition = alert["condition"]
                emoji = "⬆️" if condition == "above" else "⬇️"

                response += f"{emoji} {symbol} {condition} ${price:,.0f}\n"

            return {
                "response": response,
                "face": "cool",
                "status": "success"
            }

        except Exception as e:
            return {
                "response": f"Error loading alerts: {str(e)}",
                "face": "confused",
                "status": "error"
            }
