"""
Project Inkling - E-ink Display Manager

Handles the Waveshare 2.13" e-ink display with support for:
- V3 (partial refresh) and V4 (full refresh only)
- Mock mode for development without hardware
- Pwnagotchi-style ASCII faces
- Text rendering with word wrap
"""

import asyncio
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


class DisplayType(Enum):
    """Supported display types."""
    MOCK = "mock"
    V3 = "v3"  # Supports partial refresh
    V4 = "v4"  # Full refresh only


# Pwnagotchi-inspired ASCII faces
# Reference: https://github.com/evilsocket/pwnagotchi/blob/master/pwnagotchi/ui/faces.py
FACES = {
    "happy": "(^_^)",
    "excited": "(*^_^*)",
    "grateful": "(^_^)b",
    "curious": "(o_O)?",
    "intense": "(>_<)",
    "cool": "( -_-)",
    "bored": "(-_-)",
    "sad": "(;_;)",
    "angry": "(>_<#)",
    "sleepy": "(-.-)zzZ",
    "awake": "(O_O)",
    "thinking": "(@_@)",
    "confused": "(?_?)",
    "surprised": "(O_o)",
    "love": "(*^3^)",
    "wink": "(^_~)",
    "debug": "[DEBUG]",
    "default": "(^_^)",
}

# Extended Unicode faces (Pwnagotchi style)
UNICODE_FACES = {
    "look_r": "( \u2686_\u2686)",
    "look_l": "(\u2609_\u2609 )",
    "look_r_happy": "( \u2686\u203f\u2686)",
    "look_l_happy": "(\u2609\u203f\u2609 )",
    "sleep": "(\u21c0\u203f\u203f\u21bc)",
    "sleep2": "(\u2022\u203f\u203f\u2022)",
    "awake": "(\u2609\u203f\u2609)",
    "bored": "(-__-)",
    "intense": "(\u2022_\u2022)",
    "cool": "(\u2312_\u2312)",
    "happy": "(\u2022\u203f\u203f\u2022)",
    "excited": "(\u1d52\u25e1\u25e1\u1d52)",
    "grateful": "(\u1d3c\u203f\u203f\u1d3c)",
    "motivated": "(\u2686\u203f\u203f\u2686)",
    "demotivated": "(\u2022__\u2022)",
    "smart": "(\u2686_\u2686)",
    "lonely": "(\u22c5\u2022\u22c5)",
    "sad": "(\u2565\u2601\u2565 )",
    "angry": "(\u2565\u203f\u2565)",
    "friend": "(\u0361\u00b0 \u035c\u0296 \u0361\u00b0)",
    "broken": "(\u2686_\u2686\u0029\u20e0",
    "debug": "(\u25b8\u203f\u25c2)",
    "upload": "(\u0029\u20d2\u2022\u203f\u203f\u2022\u0028\u20d2",
    "upload1": "(\u0029\u203f\u2022\u203f\u203f\u2022\u203f\u0028",
    "upload2": "(\u0029\u2022\u203f\u203f\u2022\u0028",
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
    - Face and text rendering
    - Async-safe updates
    """

    def __init__(
        self,
        display_type: str = "auto",
        width: int = 250,
        height: int = 122,
        min_refresh_interval: float = 5.0,
    ):
        self.width = width
        self.height = height
        self.min_refresh_interval = min_refresh_interval

        self._driver: Optional[DisplayDriver] = None
        self._display_type = display_type
        self._last_refresh = 0.0
        self._refresh_count = 0
        self._lock = asyncio.Lock()

        # Font settings
        self._font_face: Optional[ImageFont.FreeTypeFont] = None
        self._font_text: Optional[ImageFont.FreeTypeFont] = None

    def init(self) -> None:
        """Initialize the display driver."""
        self._driver = self._create_driver()
        self._driver.init()
        self._load_fonts()

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
    ) -> Image.Image:
        """
        Render a display frame with face and text.

        Args:
            face: Face expression key (from FACES or UNICODE_FACES)
            text: Main message text (will be word-wrapped)
            status: Status line at bottom

        Returns:
            PIL Image ready for display
        """
        # Create blank white image
        image = Image.new("1", (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)

        # Get face string
        face_str = UNICODE_FACES.get(face, FACES.get(face, FACES["default"]))

        # Layout:
        # - Face at top-left (large)
        # - Text below face (wrapped)
        # - Status at bottom

        # Draw face
        face_y = 5
        try:
            draw.text((10, face_y), face_str, font=self._font_face, fill=0)
        except Exception:
            # Fall back if Unicode rendering fails
            face_str = FACES.get(face, FACES["default"])
            draw.text((10, face_y), face_str, font=self._font_face, fill=0)

        # Word wrap and draw text
        if text:
            text_y = 40
            wrapped = self._word_wrap(text, max_chars=35)
            for line in wrapped[:4]:  # Max 4 lines
                draw.text((10, text_y), line, font=self._font_text, fill=0)
                text_y += 16

        # Draw status line at bottom
        if status:
            status_y = self.height - 16
            draw.text((10, status_y), status[:40], font=self._font_text, fill=0)

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
    ) -> bool:
        """
        Update the display asynchronously.

        Args:
            face: Face expression key
            text: Main message text
            status: Status line
            force: Bypass rate limiting (use sparingly)

        Returns:
            True if display was updated, False if rate-limited
        """
        async with self._lock:
            if not force and not self._can_refresh():
                wait_time = self._wait_for_refresh()
                print(f"[Display] Rate limited, wait {wait_time:.1f}s")
                return False

            # Render the frame
            image = self.render_frame(face, text, status)

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
