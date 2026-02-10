"""
Project Inkling - E-ink Display Manager

Handles the Waveshare 2.13" e-ink display with support for:
- V3 (partial refresh) and V4 (full refresh only)
- Mock mode for development without hardware
- Pwnagotchi-style UI with panels and stats
- Text rendering with word wrap
"""

import asyncio
import os
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple, Dict, Any
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .ui import PwnagotchiUI, DisplayContext, FACES, UNICODE_FACES

# Environment variable to disable terminal rendering
DISABLE_DISPLAY_ECHO = os.getenv("INKLING_NO_DISPLAY_ECHO", "").lower() in ("1", "true", "yes")
from . import system_stats


class DisplayType(Enum):
    """Supported display types."""
    MOCK = "mock"
    V3 = "v3"  # Supports partial refresh
    V4 = "v4"  # Full refresh only


# Mood to display text mapping
MOOD_DISPLAY_TEXT = {
    "happy": "Happy",
    "excited": "Excited",
    "grateful": "Grateful",
    "curious": "Curious",
    "intense": "Intense",
    "cool": "Cool",
    "bored": "Bored",
    "sad": "Sad",
    "angry": "Angry",
    "sleepy": "Sleepy",
    "awake": "Awake",
    "thinking": "Thinking",
    "confused": "Confused",
    "surprised": "Surprised",
    "lonely": "Lonely",
    "default": "Neutral",
}


class DisplayDriver(ABC):
    """Abstract base class for display drivers."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._last_refresh = 0.0

    @abstractmethod
    def init(self) -> None:
        """Initialize the display hardware."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the display to white."""
        pass

    @abstractmethod
    def display(self, image: Image.Image) -> None:
        """Display an image on the screen."""
        pass

    @abstractmethod
    def display_partial(self, image: Image.Image) -> None:
        """Display using partial refresh (if supported)."""
        pass

    @abstractmethod
    def sleep(self) -> None:
        """Put display into low-power mode."""
        pass

    @property
    @abstractmethod
    def supports_partial(self) -> bool:
        """Whether this display supports partial refresh."""
        pass


class MockDisplay(DisplayDriver):
    """Mock display for development without hardware."""

    def __init__(self, width: int = 250, height: int = 122):
        super().__init__(width, height)
        self._current_image: Optional[Image.Image] = None

    def init(self) -> None:
        print(f"[MockDisplay] Initialized {self.width}x{self.height}")

    def clear(self) -> None:
        print("[MockDisplay] Cleared")
        self._current_image = Image.new("1", (self.width, self.height), 255)

    def display(self, image: Image.Image) -> None:
        self._current_image = image.copy()
        self._render_to_terminal(image)

    def display_partial(self, image: Image.Image) -> None:
        # Mock partial refresh is same as full
        self.display(image)

    def sleep(self) -> None:
        print("[MockDisplay] Sleeping")

    @property
    def supports_partial(self) -> bool:
        return True

    def _render_to_terminal(self, image: Image.Image) -> None:
        """Render image as ASCII art in terminal."""
        if DISABLE_DISPLAY_ECHO:
            return

        # Convert to 1-bit if needed
        if image.mode != "1":
            image = image.convert("1")

        # Scale down for terminal (each char = 2x4 pixels)
        term_width = min(80, self.width // 2)
        term_height = self.height // 4

        print("\n" + "=" * term_width)
        for y in range(0, self.height, 4):
            line = ""
            for x in range(0, self.width, 2):
                # Sample 2x4 block
                block_pixels = 0
                for dy in range(4):
                    for dx in range(2):
                        px = x + dx
                        py = y + dy
                        if px < self.width and py < self.height:
                            if image.getpixel((px, py)) == 0:  # Black
                                block_pixels += 1

                # Map to character based on density
                if block_pixels == 0:
                    line += " "
                elif block_pixels < 3:
                    line += "."
                elif block_pixels < 5:
                    line += ":"
                elif block_pixels < 7:
                    line += "#"
                else:
                    line += "@"

            print(line[:term_width])
        print("=" * term_width + "\n")


class WaveshareV3Display(DisplayDriver):
    """
    Driver for Waveshare 2.13" V3 e-ink display.
    Supports partial refresh for faster updates.
    """

    def __init__(self, width: int = 250, height: int = 122):
        super().__init__(width, height)
        self._epd = None

    def init(self) -> None:
        try:
            from waveshare_epd import epd2in13_V3
            self._epd = epd2in13_V3.EPD()
            self._epd.init()
            self._epd.Clear(0xFF)
        except ImportError:
            raise RuntimeError(
                "Waveshare library not installed. "
                "Run: pip install waveshare-epd"
            )

    def clear(self) -> None:
        if self._epd:
            self._epd.Clear(0xFF)

    def display(self, image: Image.Image) -> None:
        if self._epd:
            self._epd.display(self._epd.getbuffer(image))

    def display_partial(self, image: Image.Image) -> None:
        if self._epd:
            self._epd.displayPartial(self._epd.getbuffer(image))

    def sleep(self) -> None:
        if self._epd:
            self._epd.sleep()

    @property
    def supports_partial(self) -> bool:
        return True


class WaveshareV4Display(DisplayDriver):
    """
    Driver for Waveshare 2.13" V4 e-ink display.
    Full refresh only - no partial refresh support.
    """

    def __init__(self, width: int = 250, height: int = 122):
        super().__init__(width, height)
        self._epd = None

    def init(self) -> None:
        try:
            from waveshare_epd import epd2in13_V4
            self._epd = epd2in13_V4.EPD()
            self._epd.init()
            self._epd.Clear(0xFF)
        except ImportError:
            raise RuntimeError(
                "Waveshare library not installed. "
                "Run: pip install waveshare-epd"
            )

    def clear(self) -> None:
        if self._epd:
            self._epd.Clear(0xFF)

    def display(self, image: Image.Image) -> None:
        if self._epd:
            self._epd.display(self._epd.getbuffer(image))

    def display_partial(self, image: Image.Image) -> None:
        # V4 doesn't support partial refresh, use full
        self.display(image)

    def sleep(self) -> None:
        if self._epd:
            self._epd.sleep()

    @property
    def supports_partial(self) -> bool:
        return False


class DisplayManager:
    """
    High-level display manager for Inkling.

    Handles:
    - Display type auto-detection
    - Rate limiting for display health
    - Pwnagotchi-style UI rendering
    - Async-safe updates
    """

    def __init__(
        self,
        display_type: str = "auto",
        width: int = 250,
        height: int = 122,
        min_refresh_interval: float = 5.0,
        pagination_loop_seconds: float = 5.0,
        device_name: str = "inkling",
        personality=None,
        timezone: Optional[str] = None,
        prefer_ascii_faces: Optional[bool] = None,
        dark_mode: bool = False,
        sprite_config: Optional[dict] = None,
    ):
        self.width = width
        self.height = height
        self.min_refresh_interval = min_refresh_interval
        self.pagination_loop_seconds = pagination_loop_seconds
        self.device_name = device_name
        self.personality = personality
        self.timezone = timezone
        self._dark_mode = dark_mode

        self._driver: Optional[DisplayDriver] = None
        self._display_type = display_type
        self._last_refresh = 0.0
        self._refresh_count = 0
        self._lock = asyncio.Lock()

        # Face preference: ASCII for e-ink (better rendering), Unicode for mock (prettier)
        # Will be set to True for v3/v4, False for mock if not specified
        self._prefer_ascii_faces = prefer_ascii_faces

        # Sprite configuration
        self._sprite_config = sprite_config or {}
        self._sprite_manager = None

        # Pwnagotchi UI renderer
        self._ui: Optional[PwnagotchiUI] = None

        # Social stats (updated externally)
        self._dream_count: int = 0
        self._telegram_count: int = 0
        self._chat_count: int = 0
        self._friend_nearby: bool = False
        self._mode: str = "AUTO"

        # Legacy font settings (for backwards compatibility)
        self._font_face: Optional[ImageFont.FreeTypeFont] = None
        self._font_text: Optional[ImageFont.FreeTypeFont] = None

        # Auto-refresh state
        self._refresh_task: Optional[asyncio.Task] = None
        self._auto_refresh_interval = max(0.0, self.min_refresh_interval)
        self._face_animation_interval = 2.0
        self._face_anim_toggle = False

        # V4 safety: minimum full refresh interval (seconds)
        self._full_refresh_min_seconds = 5.0

        # Paginated message loop state
        self._page_loop_task: Optional[asyncio.Task] = None

        # Track current display state for auto-refresh
        self._current_face: str = "default"
        self._current_text: str = ""
        self._current_mood: str = "Happy"
        self._focus_manager = None

        # Screen saver state
        self._screensaver_enabled = False
        self._screensaver_idle_minutes = 5.0
        self._screensaver_page_duration = 10.0
        self._screensaver_pages = []  # List of page configs
        self._screensaver_active = False
        self._screensaver_task: Optional[asyncio.Task] = None
        self._screensaver_current_page = 0

        # Animation state
        self._current_animation_action = "idle"
        self._current_animation_mood = "happy"

    def init(self) -> None:
        """Initialize the display driver and UI."""
        self._driver = self._create_driver()
        self._driver.init()
        self._load_fonts()

        # Sprite system disabled - using emoji text faces only
        # (Keep code below for future re-enable if needed)
        # from core.sprites import SpriteManager
        # sprite_enabled = self._sprite_config.get("enabled", True)
        # sprite_dir = self._sprite_config.get("directory", "assets/sprites")
        # self._sprite_manager = SpriteManager(sprite_dir=sprite_dir, enabled=sprite_enabled)

        # Initialize UI (emoji-based, no sprites)
        self._ui = PwnagotchiUI()

        # Align auto-refresh to configured interval for partial refresh displays
        if self._driver.supports_partial:
            base_interval = max(0.0, self.min_refresh_interval)
            self._auto_refresh_interval = min(base_interval, self._face_animation_interval)

    def _create_driver(self) -> DisplayDriver:
        """Create appropriate display driver based on type."""
        # Set face preference if not explicitly set
        if self._prefer_ascii_faces is None:
            # E-ink displays (v3/v4) use ASCII for better rendering
            # Mock display uses Unicode for prettier appearance
            if self._display_type in ("v3", "v4"):
                self._prefer_ascii_faces = True
            elif self._display_type == "mock":
                self._prefer_ascii_faces = False
            else:  # auto - will be set after detection
                self._prefer_ascii_faces = None

        if self._display_type == "mock":
            if self._prefer_ascii_faces is None:
                self._prefer_ascii_faces = False
            return MockDisplay(self.width, self.height)

        if self._display_type == "v3":
            if self._prefer_ascii_faces is None:
                self._prefer_ascii_faces = True
            return WaveshareV3Display(self.width, self.height)

        if self._display_type == "v4":
            if self._prefer_ascii_faces is None:
                self._prefer_ascii_faces = True
            return WaveshareV4Display(self.width, self.height)

        if self._display_type == "auto":
            driver = self._auto_detect_display()
            # Set preference based on detected type
            if self._prefer_ascii_faces is None:
                if isinstance(driver, MockDisplay):
                    self._prefer_ascii_faces = False
                else:  # Real e-ink
                    self._prefer_ascii_faces = True
            return driver

        # Default to mock
        if self._prefer_ascii_faces is None:
            self._prefer_ascii_faces = False
        return MockDisplay(self.width, self.height)

    def _auto_detect_display(self) -> DisplayDriver:
        """Auto-detect display type or fall back to mock."""
        # Try V3 first (more common, supports partial refresh)
        try:
            driver = WaveshareV3Display(self.width, self.height)
            driver.init()
            return driver
        except (ImportError, RuntimeError):
            pass

        # Try V4
        try:
            driver = WaveshareV4Display(self.width, self.height)
            driver.init()
            return driver
        except (ImportError, RuntimeError):
            pass

        # Fall back to mock
        print("[Display] No hardware detected, using mock display")
        return MockDisplay(self.width, self.height)

    def _load_fonts(self) -> None:
        """Load fonts for rendering."""
        # Try to load a nice monospace font, fall back to default
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
        ]

        for path in font_paths:
            try:
                self._font_face = ImageFont.truetype(path, 24)
                self._font_text = ImageFont.truetype(path, 12)
                return
            except (OSError, IOError):
                continue

        # Fall back to default bitmap font
        self._font_face = ImageFont.load_default()
        self._font_text = ImageFont.load_default()

    def _get_refresh_interval(self) -> float:
        """Get the effective refresh interval based on display capabilities."""
        base_interval = max(0.0, self.min_refresh_interval)
        if self._driver and not self._driver.supports_partial:
            return max(self._full_refresh_min_seconds, base_interval)
        return base_interval

    def _can_refresh(self) -> bool:
        """Check refresh timing based on display capabilities."""
        elapsed = time.time() - self._last_refresh
        return elapsed >= self._get_refresh_interval()

    def _wait_for_refresh(self) -> float:
        """Get seconds to wait before next refresh is allowed."""
        elapsed = time.time() - self._last_refresh
        remaining = self._get_refresh_interval() - elapsed
        return max(0, remaining)

    def render_frame(
        self,
        face: str = "default",
        text: str = "",
        status: str = "",
        mood_text: Optional[str] = None,
    ) -> Image.Image:
        """
        Render a Pwnagotchi-style display frame.

        Args:
            face: Face expression key (from FACES or UNICODE_FACES)
            text: Main message text (shown in message box)
            status: Status line (used as mode indicator in footer)
            mood_text: Optional mood text override for header

        Returns:
            PIL Image ready for display
        """
        # Get face string - prefer ASCII on e-ink, Unicode on mock
        if self._prefer_ascii_faces:
            # E-ink: Try ASCII first, fallback to Unicode if not found
            face_str = FACES.get(face, UNICODE_FACES.get(face, FACES["default"]))
        else:
            # Mock/Web: Try Unicode first for prettier faces
            face_str = UNICODE_FACES.get(face, FACES.get(face, FACES["default"]))

        # Get mood display text
        if mood_text is None:
            mood_text = MOOD_DISPLAY_TEXT.get(face, MOOD_DISPLAY_TEXT["default"])

        # Get system stats
        stats = system_stats.get_all_stats()
        clock_time = system_stats.get_local_time(self.timezone)

        # Get progression data
        level = 1
        level_name = "Newborn"
        xp_progress = 0.0
        prestige = 0

        if self.personality and hasattr(self.personality, 'progression'):
            from .progression import LevelCalculator
            prog = self.personality.progression
            level = prog.level
            level_name = LevelCalculator.level_name(level).split()[0]  # "Newborn", "Curious", etc.
            xp_progress = LevelCalculator.progress_to_next_level(prog.xp)
            prestige = prog.prestige

        # Get WiFi status (non-blocking, fails gracefully)
        wifi_ssid = None
        wifi_signal = 0
        try:
            from core.wifi_utils import get_current_wifi
            wifi_status = get_current_wifi()
            if wifi_status.connected and wifi_status.ssid:
                wifi_ssid = wifi_status.ssid
                wifi_signal = wifi_status.signal_strength
        except Exception:
            pass  # Silently fail if WiFi utilities not available

        # Build display context
        focus_snapshot = {"focus_active": False}
        if self._focus_manager:
            try:
                focus_snapshot = self._focus_manager.get_display_snapshot()
            except Exception:
                focus_snapshot = {"focus_active": False}

        ctx = DisplayContext(
            name=self.device_name,
            mood_text=mood_text,
            uptime=stats["uptime"],
            face_str=face_str,
            prefer_ascii=bool(self._prefer_ascii_faces),
            animation_action=self._current_animation_action,
            mood_key=self._current_animation_mood,
            message_y_offset=0,
            memory_percent=stats["memory"],
            cpu_percent=stats["cpu"],
            temperature=stats["temperature"],
            battery_percentage=stats["battery"]["percentage"] if "battery" in stats else -1,
            is_charging=stats["battery"]["charging"] if "battery" in stats else False,
            clock_time=clock_time,
            wifi_ssid=wifi_ssid,
            wifi_signal=wifi_signal,
            dream_count=self._dream_count,
            telegram_count=self._telegram_count,
            chat_count=self._chat_count,
            friend_nearby=self._friend_nearby,
            level=level,
            level_name=level_name,
            xp_progress=xp_progress,
            prestige=prestige,
            message=text,
            focus_active=bool(focus_snapshot.get("focus_active"))
            and bool(focus_snapshot.get("takeover_enabled", True)),
            focus_phase=str(focus_snapshot.get("focus_phase", "FOCUS")),
            focus_remaining_sec=int(focus_snapshot.get("focus_remaining_sec", 0)),
            focus_progress=float(focus_snapshot.get("focus_progress", 0.0)),
            focus_task_label=focus_snapshot.get("focus_task_label"),
            mode=self._mode if not status else status[:10].upper(),
        )

        # Render using Pwnagotchi UI
        if self._ui:
            image = self._ui.render(ctx)

            # Apply dark mode inversion if enabled
            if self._dark_mode:
                image = ImageOps.invert(image.convert('L')).convert('1')

            return image

        # Fallback to simple rendering if UI not initialized
        return self._render_simple(face_str, text, status)

    def _render_simple(
        self,
        face_str: str,
        text: str,
        status: str,
    ) -> Image.Image:
        """Simple fallback renderer (legacy compatibility)."""
        image = Image.new("1", (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        # Draw face
        try:
            draw.text((10, 5), face_str, font=self._font_face, fill=0)
        except Exception:
            draw.text((10, 5), "(^_^)", font=self._font_face, fill=0)

        # Draw text
        if text:
            text_y = 40
            wrapped = self._word_wrap(text, max_chars=35)
            for line in wrapped[:4]:
                draw.text((10, text_y), line, font=self._font_text, fill=0)
                text_y += 16

        # Draw status
        if status:
            draw.text((10, self.height - 16), status[:40], font=self._font_text, fill=0)

        return image

    def _word_wrap(self, text: str, max_chars: int = 35) -> list:
        """Wrap text to fit display width."""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word[:max_chars]  # Truncate long words

        if current_line:
            lines.append(current_line)

        return lines

    def configure_screensaver(
        self,
        enabled: bool = True,
        idle_minutes: float = 5.0,
        page_duration: float = 10.0,
        pages: Optional[list] = None,
    ) -> None:
        """Configure screen saver settings."""
        self._screensaver_enabled = enabled
        self._screensaver_idle_minutes = idle_minutes
        self._screensaver_page_duration = page_duration
        self._screensaver_pages = pages or [
            {"type": "stats"},
            {"type": "quote"},
            {"type": "faces"},
        ]

    def should_activate_screensaver(self) -> bool:
        """Check if screen saver should activate based on idle time."""
        if not self._screensaver_enabled:
            return False

        if self._screensaver_active:
            return False  # Already active

        if not self.personality:
            return False

        # Check idle time
        idle_minutes = (time.time() - self.personality._last_interaction) / 60.0
        return idle_minutes >= self._screensaver_idle_minutes

    async def start_screensaver(self) -> None:
        """Start the screen saver loop."""
        if self._screensaver_active:
            return

        self._screensaver_active = True
        self._screensaver_current_page = 0
        print(f"[Screensaver] Starting with {len(self._screensaver_pages)} pages, duration={self._screensaver_page_duration}s")

        async def _screensaver_loop():
            while self._screensaver_active:
                try:
                    # Render current page
                    page_config = self._screensaver_pages[self._screensaver_current_page]
                    page_type = page_config.get("type", "unknown")
                    print(f"[Screensaver] Showing page {self._screensaver_current_page + 1}/{len(self._screensaver_pages)}: {page_type}")

                    await self._render_screensaver_page(page_config)

                    # Wait before next page
                    print(f"[Screensaver] Waiting {self._screensaver_page_duration}s before next page...")
                    await asyncio.sleep(self._screensaver_page_duration)

                    # Next page (cycle)
                    self._screensaver_current_page = (self._screensaver_current_page + 1) % len(self._screensaver_pages)

                except asyncio.CancelledError:
                    print("[Screensaver] Loop cancelled")
                    break
                except Exception as e:
                    print(f"[Screensaver] Error in loop: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to next page on error
                    await asyncio.sleep(1)
                    self._screensaver_current_page = (self._screensaver_current_page + 1) % len(self._screensaver_pages)

        self._screensaver_task = asyncio.create_task(_screensaver_loop())

    async def stop_screensaver(self) -> None:
        """Stop the screen saver loop."""
        if not self._screensaver_active:
            return

        # Debug: log what's stopping the screensaver
        import traceback
        print("[Screensaver] Stopping screensaver, called from:")
        for line in traceback.format_stack()[:-1]:
            if "/core/" in line or "/modes/" in line:
                print(line.strip())

        self._screensaver_active = False

        if self._screensaver_task:
            self._screensaver_task.cancel()
            try:
                await self._screensaver_task
            except asyncio.CancelledError:
                pass
            self._screensaver_task = None

    async def _render_screensaver_page(self, page_config: Dict[str, str]) -> None:
        """Render a specific screen saver page."""
        page_type = page_config.get("type", "stats")

        if page_type == "stats":
            # System stats summary
            stats = system_stats.get_all_stats()
            text = (
                f"System Stats:\n"
                f"Uptime: {stats['uptime']}\n"
                f"CPU: {stats['cpu']}%\n"
                f"Memory: {stats['memory']}%\n"
                f"Temp: {stats['temperature']}°C"
            )
            face = "monitoring"

        elif page_type == "quote":
            # AI-generated quote (would need Brain integration)
            text = await self._get_screensaver_quote()
            face = "thinking"

        elif page_type == "faces":
            # Show animated idle emoji faces
            import random
            mood = random.choice(["happy", "curious", "excited", "sleepy", "bored", "sad"])
            face = mood
            text = ""  # No text - just show animated emoji face

        elif page_type == "walk":
            # Show walk emoji (no animation in screensaver)
            face = "curious"
            text = ""  # No text - just emoji face

        elif page_type == "dance":
            # Show dance emoji (no animation in screensaver)
            face = "excited"
            text = ""  # No text - just emoji face

        elif page_type == "progression":
            # XP and level progress
            if self.personality and hasattr(self.personality, 'progression'):
                prog = self.personality.progression
                from .progression import LevelCalculator
                xp_to_next = LevelCalculator.xp_to_next_level(prog.xp)
                progress_pct = int(LevelCalculator.progress_to_next_level(prog.xp) * 100)
                text = (
                    f"Level {prog.level}: {LevelCalculator.level_name(prog.level)}\n"
                    f"Progress: {progress_pct}% to next level\n"
                    f"XP needed: {xp_to_next}\n"
                    f"Total XP: {prog.xp}"
                )
                face = "motivated"
            else:
                text = "Progression system not available"
                face = "default"

        else:
            text = f"Unknown page type: {page_type}"
            face = "confused"

        # Render the page
        await self.update(face=face, text=text, status="SCREENSAVER", force=True, cancel_page_loop=False)

    async def _get_screensaver_quote(self) -> str:
        """Generate an AI quote for screensaver (optional)."""
        # Fallback to predefined quotes (Brain integration optional)
        quotes = [
            "Curiosity is the spark\nthat lights the path\nto knowledge.",
            "Every question asked\nis a step toward\nunderstanding.",
            "Learning never exhausts\nthe mind. Stay curious!",
            "The future belongs\nto those who learn.",
            "Small steps daily\nlead to great journeys.",
            "In every moment,\nthere is beauty\nwaiting to be found.",
            "Growth happens\nwhen we embrace\nthe unknown.",
            "Every interaction\nteaches us something\nabout the world.",
        ]
        import random
        return random.choice(quotes)

    async def update(
        self,
        face: str = "default",
        text: str = "",
        status: str = "",
        force: bool = False,
        mood_text: Optional[str] = None,
        cancel_page_loop: bool = True,
    ) -> bool:
        """
        Update the display asynchronously.

        Args:
            face: Face expression key
            text: Main message text (shown in message box)
            status: Status/mode indicator
            force: Bypass rate limiting (use sparingly)
            mood_text: Optional mood text override for header
            cancel_page_loop: Stop any active paginated loop (default: True)

        Returns:
            True if display was updated, False if rate-limited
        """
        async with self._lock:
            # Stop screensaver if active (user interaction)
            if self._screensaver_active and status != "SCREENSAVER":
                await self.stop_screensaver()

            if cancel_page_loop and self._page_loop_task:
                if asyncio.current_task() is not self._page_loop_task:
                    await self.stop_page_loop()

            # Store state for auto-refresh (always, even if rate-limited)
            self._current_face = face
            self._current_text = text
            if mood_text:
                self._current_mood = mood_text

            if not force and not self._can_refresh():
                wait_time = self._wait_for_refresh()
                # Only log rate limiting for non-partial displays (V4)
                if not (self._driver and self._driver.supports_partial):
                    print(f"[Display] Rate limited, wait {wait_time:.1f}s")
                return False

            # Render the frame
            image = self.render_frame(face, text, status, mood_text)

            # Update display
            if self._driver:
                if self._driver.supports_partial and self._refresh_count > 0:
                    # Use partial refresh after first full refresh
                    self._driver.display_partial(image)
                else:
                    self._driver.display(image)

            self._last_refresh = time.time()
            self._refresh_count += 1
            return True

    async def show_message(self, text: str, face: str = "default") -> bool:
        """Convenience method to display a message."""
        return await self.update(face=face, text=text)

    async def show_message_paginated(
        self,
        text: str,
        face: str = "default",
        page_delay: float = 3.0,
        lines_per_page: int = 0,
        chars_per_line: int = 32,
        loop: bool = False,
    ) -> int:
        """
        Display a long message across multiple pages with auto-scroll.

        Splits the message into pages that fit the display, then shows each page
        with a delay between transitions.

        Args:
            text: Message text to display
            face: Face expression to show
            page_delay: Seconds to wait between pages (default: 3.0)
            lines_per_page: Maximum lines per page (default: MESSAGE_MAX_LINES)
            chars_per_line: Maximum characters per line (default: 32, matches 250px display)
            loop: If True, keep cycling pages in the background

        Returns:
            Number of pages displayed
        """
        from .ui import word_wrap, MESSAGE_MAX_LINES

        # Word wrap the entire message
        all_lines = word_wrap(text, chars_per_line)

        if lines_per_page <= 0:
            lines_per_page = MESSAGE_MAX_LINES

        # If message fits on one page, just show it normally
        if len(all_lines) <= lines_per_page:
            await self.update(face=face, text=text)
            return 1

        # Split into pages
        pages = []
        for i in range(0, len(all_lines), lines_per_page):
            page_lines = all_lines[i:i + lines_per_page]
            page_text = " ".join(page_lines)  # Rejoin lines with spaces
            pages.append(page_text)

        if loop:
            if not (self._driver and self._driver.supports_partial):
                # V4/full refresh: show once and return (no looping)
                await self.update(face=face, text=pages[0])
                return len(pages)
            await self.start_page_loop(pages, face=face, page_delay=page_delay)
            return len(pages)

        # Display each page with delay and page indicator
        total = len(pages)
        for i, page_text in enumerate(pages):
            indicator = f" [{i+1}/{total}]" if total > 1 else ""
            await self.update(face=face, text=page_text + indicator, force=True)

            # Don't wait after the last page
            if i < total - 1:
                await asyncio.sleep(page_delay)

        return total

    async def start_page_loop(
        self,
        pages: list,
        face: str = "default",
        page_delay: float = 5.0,
    ) -> None:
        """Start a background loop cycling through message pages."""
        await self.stop_page_loop()

        async def _loop() -> None:
            idx = 0
            total = len(pages)
            while True:
                indicator = f" [{idx+1}/{total}]" if total > 1 else ""
                await self.update(
                    face=face,
                    text=pages[idx] + indicator,
                    force=True,
                    cancel_page_loop=False,
                )
                idx = (idx + 1) % total
                await asyncio.sleep(page_delay)

        self._page_loop_task = asyncio.create_task(_loop())

    async def stop_page_loop(self) -> None:
        """Stop any active paginated message loop."""
        if self._page_loop_task:
            self._page_loop_task.cancel()
            try:
                await self._page_loop_task
            except asyncio.CancelledError:
                pass
            self._page_loop_task = None

    # ========================================================================
    # QR Code Display (first boot)
    # ========================================================================

    async def show_qr_code(self, url: str, label: str = "Scan to connect") -> bool:
        """Display a QR code on the e-ink screen for the given URL.

        Args:
            url: URL to encode in the QR code
            label: Text label below the QR code

        Returns:
            True if QR code was displayed, False on failure
        """
        try:
            import qrcode
            from PIL import Image as PILImage, ImageDraw as PILDraw

            from .ui import DISPLAY_WIDTH, DISPLAY_HEIGHT, Fonts

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=2, border=1)
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")

            # Create display-size image
            img = PILImage.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 255)

            # Center QR code in available space
            qr_w, qr_h = qr_img.size
            max_h = DISPLAY_HEIGHT - 20  # Leave room for label
            if qr_h > max_h:
                ratio = max_h / qr_h
                qr_img = qr_img.resize((int(qr_w * ratio), int(qr_h * ratio)))
                qr_w, qr_h = qr_img.size

            x = (DISPLAY_WIDTH - qr_w) // 2
            y = max(2, (max_h - qr_h) // 2)
            img.paste(qr_img, (x, y))

            # Draw label at bottom
            draw = PILDraw.Draw(img)
            fonts = Fonts()
            draw.text((4, DISPLAY_HEIGHT - 14), label, font=fonts.small, fill=0)

            # Display it
            if self._driver:
                self._driver.display(img)
                self._last_refresh = time.time()
                self._refresh_count += 1
                return True
        except ImportError:
            # qrcode library not available - show URL as text instead
            await self.update(face="happy", text=f"Connect: {url}", force=True)
            return True
        except Exception as e:
            print(f"[Display] QR code error: {e}")
        return False

    # ========================================================================
    # Achievement Flash
    # ========================================================================

    async def show_achievement(self, name: str, description: str, xp: int = 0) -> None:
        """Briefly flash an achievement on the display.

        Shows achievement text for 4 seconds, then restores previous display.
        """
        # Save current state
        prev_face = self._current_face
        prev_text = self._current_text

        # Show achievement
        achievement_text = f"ACHIEVEMENT!\n{name}\n{description}"
        if xp > 0:
            achievement_text += f"\n+{xp} XP"

        await self.update(face="excited", text=achievement_text, force=True)
        await asyncio.sleep(4)

        # Restore previous display
        await self.update(face=prev_face, text=prev_text, force=True)

    # ========================================================================
    # Status Card Rotation (Idle Screen)
    # ========================================================================

    def _get_idle_cards(self) -> list:
        """Generate status cards for idle screen rotation."""
        from . import system_stats

        cards = []

        # Card 1: System stats
        stats = system_stats.get_all_stats()
        cards.append(f"CPU {stats['cpu']}% | Mem {stats['memory']}% | {stats['temperature']}C")

        # Card 2: Progression
        if self.personality and hasattr(self.personality, 'progression'):
            prog = self.personality.progression
            from .progression import LevelCalculator
            name = LevelCalculator.level_name(prog.level)
            cards.append(f"L{prog.level} {name} | {prog.xp} XP | Streak: {prog.current_streak}d")

        # Card 3: Uptime + refreshes
        cards.append(f"Up: {stats['uptime']} | Refreshes: {self._refresh_count}")

        # Card 4: Last thought
        if self.personality and self.personality.last_thought:
            thought = self.personality.last_thought[:80]
            cards.append(thought)

        return cards

    # ========================================================================
    # Auto-Refresh Loop
    # ========================================================================

    async def start_auto_refresh(self) -> None:
        """Start background display refresh loop for live stats updates."""
        if self._refresh_task is not None:
            return  # Already running
        self._refresh_task = asyncio.create_task(self._auto_refresh_loop())

    async def stop_auto_refresh(self) -> None:
        """Stop background refresh loop."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None

    async def _auto_refresh_loop(self) -> None:
        """Continuously refresh display with current state (live stats).

        When idle (no active message), cycles through status info cards.
        """
        idle_card_idx = 0
        idle_ticks = 0

        while True:
            sleep_interval = self._auto_refresh_interval
            focus_active = False
            focus_cadence = None
            if self._focus_manager:
                try:
                    snap = self._focus_manager.get_display_snapshot()
                    focus_active = bool(snap.get("focus_active")) and bool(snap.get("takeover_enabled", True))
                    focus_cadence = snap.get("focus_cadence_sec")
                except Exception:
                    focus_active = False
                    focus_cadence = None

            if focus_active and focus_cadence:
                sleep_interval = max(1.0, float(focus_cadence))

            await asyncio.sleep(sleep_interval)

            # Skip auto-refresh if screensaver is active
            if self._screensaver_active:
                continue

            if self._driver:
                face = self._current_face
                text = self._current_text

                # Flip every refresh for a visible animation cadence
                self._face_anim_toggle = not self._face_anim_toggle
                if self._face_anim_toggle:
                    face = self._get_animated_face(face)

                # Status card rotation when idle (no user message)
                if not text and not self._page_loop_task:
                    idle_ticks += 1
                    # Rotate cards every ~10 ticks (5 seconds at 0.5s interval)
                    if idle_ticks >= 10:
                        idle_ticks = 0
                        cards = self._get_idle_cards()
                        if cards:
                            text = cards[idle_card_idx % len(cards)]
                            idle_card_idx += 1
                else:
                    idle_ticks = 0

                # Re-render with updated stats (uptime, CPU, etc.)
                await self.update(
                    face=face,
                    text=text,
                    mood_text=self._current_mood,
                    force=bool(self._driver.supports_partial),
                    cancel_page_loop=False,
                )

    def set_focus_manager(self, focus_manager) -> None:
        """Attach focus manager for timer takeover rendering."""
        self._focus_manager = focus_manager

    def clear(self) -> None:
        """Clear the display."""
        if self._driver:
            self._driver.clear()

    def sleep(self) -> None:
        """Put display into low-power mode."""
        if self._driver:
            self._driver.sleep()

    @property
    def refresh_count(self) -> int:
        """Total number of display refreshes."""
        return self._refresh_count

    def _get_animated_face(self, base_face: str) -> str:
        """Return a subtle alternate face for light animation."""
        if self._prefer_ascii_faces:
            ascii_alt = {
                "sad": "sad",
                "sleepy": "sleepy",
                "happy": "wink",
                "excited": "happy",
                "curious": "thinking",
                "cool": "bored",
                "default": "wink",
            }
            return ascii_alt.get(base_face, "wink")

        unicode_alt = {
            "sad": "sad",
            "sleepy": "sleep",
            "happy": "look_r_happy",
            "excited": "look_l_happy",
            "curious": "thinking",
            "cool": "look_r",
            "default": "look_r",
        }
        return unicode_alt.get(base_face, "look_r")

    # ========================================================================
    # Social Stats Management
    # ========================================================================

    def set_social_stats(
        self,
        dream_count: Optional[int] = None,
        telegram_count: Optional[int] = None,
        chat_count: Optional[int] = None,
        friend_nearby: Optional[bool] = None,
    ) -> None:
        """
        Update social statistics for display.

        Args:
            dream_count: Number of dreams posted
            telegram_count: Number of unread telegrams
            chat_count: Lifetime chat/conversation count
            friend_nearby: Whether a friend device is detected nearby
        """
        if dream_count is not None:
            self._dream_count = dream_count
        if telegram_count is not None:
            self._telegram_count = telegram_count
        if chat_count is not None:
            self._chat_count = chat_count
        if friend_nearby is not None:
            self._friend_nearby = friend_nearby

    def increment_chat_count(self) -> None:
        """Increment the lifetime chat count by 1."""
        self._chat_count += 1

    def set_mode(self, mode: str) -> None:
        """
        Set the display mode indicator.

        Args:
            mode: Mode string (e.g., "AUTO", "SSH", "WEB", "GOSSIP")
        """
        self._mode = mode.upper()[:10]

    # Sprite animation disabled - using emoji text faces only
    # def set_animation(self, action: str, mood: str) -> None:
    #     """
    #     Set the current sprite animation.
    #
    #     Args:
    #         action: Animation action (idle, walk, dance, sleep, etc.)
    #         mood: Mood name (happy, sad, excited, etc.)
    #     """
    #     self._current_animation_action = action
    #     self._current_animation_mood = mood
    #
    #     # Update UI animation state if available
    #     if self._ui and self._ui.animated_face:
    #         self._ui.animated_face.set_action(action, mood)

    @property
    def chat_count(self) -> int:
        """Get the current chat count."""
        return self._chat_count

    def get_display_stats(self) -> Dict[str, Any]:
        """
        Get current display statistics.

        Returns:
            Dict with refresh_count, chat_count, and social stats
        """
        return {
            "refresh_count": self._refresh_count,
            "chat_count": self._chat_count,
            "dream_count": self._dream_count,
            "telegram_count": self._telegram_count,
            "friend_nearby": self._friend_nearby,
            "mode": self._mode,
        }
