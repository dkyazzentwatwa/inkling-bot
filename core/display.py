"""
Project Inkling - E-ink Display Manager

Handles the Waveshare 2.13" e-ink display with support for:
- V3 (partial refresh) and V4 (full refresh only)
- Mock mode for development without hardware
- Pwnagotchi-style UI with panels and stats
- Text rendering with word wrap
"""

import asyncio
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple, Dict, Any
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from .ui import PwnagotchiUI, DisplayContext, FACES, UNICODE_FACES
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
        device_name: str = "inkling",
    ):
        self.width = width
        self.height = height
        self.min_refresh_interval = min_refresh_interval
        self.device_name = device_name

        self._driver: Optional[DisplayDriver] = None
        self._display_type = display_type
        self._last_refresh = 0.0
        self._refresh_count = 0
        self._lock = asyncio.Lock()

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

    def init(self) -> None:
        """Initialize the display driver and UI."""
        self._driver = self._create_driver()
        self._driver.init()
        self._load_fonts()
        self._ui = PwnagotchiUI()

    def _create_driver(self) -> DisplayDriver:
        """Create appropriate display driver based on type."""
        if self._display_type == "mock":
            return MockDisplay(self.width, self.height)

        if self._display_type == "v3":
            return WaveshareV3Display(self.width, self.height)

        if self._display_type == "v4":
            return WaveshareV4Display(self.width, self.height)

        if self._display_type == "auto":
            return self._auto_detect_display()

        # Default to mock
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

    def _can_refresh(self) -> bool:
        """Check if enough time has passed since last refresh."""
        elapsed = time.time() - self._last_refresh
        return elapsed >= self.min_refresh_interval

    def _wait_for_refresh(self) -> float:
        """Get seconds to wait before next refresh is allowed."""
        elapsed = time.time() - self._last_refresh
        remaining = self.min_refresh_interval - elapsed
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
        # Get face string
        face_str = UNICODE_FACES.get(face, FACES.get(face, FACES["default"]))

        # Get mood display text
        if mood_text is None:
            mood_text = MOOD_DISPLAY_TEXT.get(face, MOOD_DISPLAY_TEXT["default"])

        # Get system stats
        stats = system_stats.get_all_stats()

        # Build display context
        ctx = DisplayContext(
            name=self.device_name,
            mood_text=mood_text,
            uptime=stats["uptime"],
            face_str=face_str,
            memory_percent=stats["memory"],
            cpu_percent=stats["cpu"],
            temperature=stats["temperature"],
            dream_count=self._dream_count,
            telegram_count=self._telegram_count,
            chat_count=self._chat_count,
            friend_nearby=self._friend_nearby,
            message=text,
            mode=self._mode if not status else status[:10].upper(),
        )

        # Render using Pwnagotchi UI
        if self._ui:
            return self._ui.render(ctx)

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

    async def update(
        self,
        face: str = "default",
        text: str = "",
        status: str = "",
        force: bool = False,
        mood_text: Optional[str] = None,
    ) -> bool:
        """
        Update the display asynchronously.

        Args:
            face: Face expression key
            text: Main message text (shown in message box)
            status: Status/mode indicator
            force: Bypass rate limiting (use sparingly)
            mood_text: Optional mood text override for header

        Returns:
            True if display was updated, False if rate-limited
        """
        async with self._lock:
            if not force and not self._can_refresh():
                wait_time = self._wait_for_refresh()
                print(f"[Display] Rate limited, wait {wait_time:.1f}s")
                return False

            # Render the frame
            image = self.render_frame(face, text, status, mood_text)

            # Update display
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
