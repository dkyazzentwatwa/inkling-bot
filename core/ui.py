"""
Project Inkling - UI Components

Pwnagotchi-inspired UI components for the e-ink display:
- Drawing primitives (boxes, lines)
- Widget classes for layout regions
- Face rendering with large Unicode characters

Layout (250x122 pixels):
┌─────────────────────────────────────────────────────┐
│ inkling>█              Curious          UP 00:15:32 │  <- Header (12px)
├─────────────────────────────────────────────────────┤
│                              │ mem  cpu  temp       │
│      (  ◉  ‿  ◉  )          │ 42%  18%   41°       │  <- Main (70px)
│                              │                      │
│                              │ DRM 5    TLG 2       │
├──────────────────────────────┴──────────────────────┤
│ "Today feels pretty good!"                          │  <- Message (20px)
├─────────────────────────────────────────────────────┤
│ ♥ friend nearby │ CHAT 142 │                   AUTO │  <- Footer (12px)
└─────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont


# ============================================================================
# Face Expressions
# ============================================================================

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
    # Tool use faces
    "working": "(._.)>",
    "searching": "(o_o)",
    "fetching": "(>.<)",
    "writing": "(._.)",
    "success": "(^_^)v",
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


# ============================================================================
# Layout Constants
# ============================================================================

# Layout constants for 250x122 display
DISPLAY_WIDTH = 250
DISPLAY_HEIGHT = 122

# Region heights
HEADER_HEIGHT = 14
FOOTER_HEIGHT = 14
MESSAGE_HEIGHT = 18
MAIN_HEIGHT = DISPLAY_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT - MESSAGE_HEIGHT - 4  # 72px

# Divider positions
STATS_PANEL_WIDTH = 90  # Right panel width
FACE_PANEL_WIDTH = DISPLAY_WIDTH - STATS_PANEL_WIDTH - 2  # Left panel width


@dataclass
class Fonts:
    """Font collection for different UI elements."""
    tiny: ImageFont.FreeTypeFont  # 8px - stats labels
    small: ImageFont.FreeTypeFont  # 10px - footer
    normal: ImageFont.FreeTypeFont  # 12px - status, messages
    large: ImageFont.FreeTypeFont  # 16px - unused currently
    face: ImageFont.FreeTypeFont  # 24px - face rendering

    @classmethod
    def load(cls, font_paths: Optional[List[str]] = None) -> "Fonts":
        """
        Load fonts from available paths.

        Args:
            font_paths: Optional list of font file paths to try

        Returns:
            Fonts instance with loaded fonts
        """
        if font_paths is None:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
                "/System/Library/Fonts/Menlo.ttc",
                "/System/Library/Fonts/Monaco.ttf",
                "/usr/share/fonts/truetype/unifont/unifont.ttf",
            ]

        # Try each path until one works
        for path in font_paths:
            try:
                return cls(
                    tiny=ImageFont.truetype(path, 8),
                    small=ImageFont.truetype(path, 10),
                    normal=ImageFont.truetype(path, 11),
                    large=ImageFont.truetype(path, 14),
                    face=ImageFont.truetype(path, 22),
                )
            except (OSError, IOError):
                continue

        # Fall back to default bitmap font
        default = ImageFont.load_default()
        return cls(
            tiny=default,
            small=default,
            normal=default,
            large=default,
            face=default,
        )


# ============================================================================
# Drawing Primitives
# ============================================================================

def draw_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: int = 255,
    outline: int = 0,
    width: int = 1,
) -> None:
    """
    Draw a rectangle with optional fill and outline.

    Args:
        draw: PIL ImageDraw object
        x, y: Top-left corner coordinates
        w, h: Width and height
        fill: Fill color (0=black, 255=white)
        outline: Outline color
        width: Line width
    """
    draw.rectangle(
        [x, y, x + w - 1, y + h - 1],
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_hline(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    color: int = 0,
) -> None:
    """
    Draw a horizontal line.

    Args:
        draw: PIL ImageDraw object
        x, y: Start coordinates
        w: Width (length) of line
        color: Line color (0=black, 255=white)
    """
    draw.line([(x, y), (x + w - 1, y)], fill=color, width=1)


def draw_vline(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    h: int,
    color: int = 0,
) -> None:
    """
    Draw a vertical line.

    Args:
        draw: PIL ImageDraw object
        x, y: Start coordinates
        h: Height (length) of line
        color: Line color (0=black, 255=white)
    """
    draw.line([(x, y), (x, y + h - 1)], fill=color, width=1)


def draw_dashed_hline(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    dash_len: int = 3,
    gap_len: int = 2,
    color: int = 0,
) -> None:
    """Draw a dashed horizontal line."""
    pos = x
    while pos < x + w:
        end = min(pos + dash_len, x + w)
        draw.line([(pos, y), (end, y)], fill=color, width=1)
        pos += dash_len + gap_len


# ============================================================================
# UI Components
# ============================================================================

@dataclass
class DisplayContext:
    """
    Context data for rendering the display.

    Contains all the information needed to render a complete frame.
    """
    # Device info
    name: str = "inkling"
    mood_text: str = "Happy"
    uptime: str = "00:00:00"

    # Face
    face_str: str = "(^_^)"

    # System stats
    memory_percent: int = 0
    cpu_percent: int = 0
    temperature: int = 0

    # Social stats
    dream_count: int = 0
    telegram_count: int = 0
    chat_count: int = 0
    friend_nearby: bool = False

    # Message
    message: str = ""

    # Mode indicator
    mode: str = "AUTO"


class HeaderBar:
    """
    Top header bar with name prompt, mood, and uptime.

    Format: "name>█  [mood]  UP HH:MM:SS"
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.height = HEADER_HEIGHT
        self.y = 0

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the header bar."""
        # Background
        draw_box(draw, 0, self.y, DISPLAY_WIDTH, self.height, fill=255, outline=0)

        # Name prompt with cursor
        prompt = f"{ctx.name[:8]}>_"
        draw.text((3, self.y + 2), prompt, font=self.fonts.small, fill=0)

        # Mood text (centered-ish)
        mood_x = 80
        draw.text((mood_x, self.y + 2), ctx.mood_text[:12], font=self.fonts.small, fill=0)

        # Uptime (right-aligned)
        uptime_text = f"UP {ctx.uptime}"
        bbox = draw.textbbox((0, 0), uptime_text, font=self.fonts.tiny)
        uptime_width = bbox[2] - bbox[0]
        draw.text(
            (DISPLAY_WIDTH - uptime_width - 3, self.y + 3),
            uptime_text,
            font=self.fonts.tiny,
            fill=0,
        )


class FacePanel:
    """
    Left panel showing the large face expression.

    Renders Unicode face characters at large size, centered in the panel.
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.x = 0
        self.y = HEADER_HEIGHT
        self.width = FACE_PANEL_WIDTH
        self.height = MAIN_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the face panel."""
        # Get face text
        face_str = ctx.face_str

        # Calculate text dimensions for centering
        bbox = draw.textbbox((0, 0), face_str, font=self.fonts.face)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center in panel
        text_x = self.x + (self.width - text_width) // 2
        text_y = self.y + (self.height - text_height) // 2 - 2

        # Draw face
        draw.text((text_x, text_y), face_str, font=self.fonts.face, fill=0)


class StatsPanel:
    """
    Right panel showing system and social stats.

    Layout:
        mem  cpu  temp
        42%  18%   41°

        DRM 5    TLG 2
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.x = FACE_PANEL_WIDTH + 1
        self.y = HEADER_HEIGHT
        self.width = STATS_PANEL_WIDTH
        self.height = MAIN_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the stats panel."""
        # Vertical separator
        draw_vline(draw, self.x, self.y, self.height, color=0)

        # System stats section
        stats_x = self.x + 4
        stats_y = self.y + 4

        # Labels row
        draw.text((stats_x, stats_y), "mem", font=self.fonts.tiny, fill=0)
        draw.text((stats_x + 28, stats_y), "cpu", font=self.fonts.tiny, fill=0)
        draw.text((stats_x + 56, stats_y), "temp", font=self.fonts.tiny, fill=0)

        # Values row
        stats_y += 10
        mem_str = f"{ctx.memory_percent}%"
        cpu_str = f"{ctx.cpu_percent}%"
        temp_str = f"{ctx.temperature}°" if ctx.temperature > 0 else "--°"

        draw.text((stats_x, stats_y), mem_str, font=self.fonts.small, fill=0)
        draw.text((stats_x + 28, stats_y), cpu_str, font=self.fonts.small, fill=0)
        draw.text((stats_x + 56, stats_y), temp_str, font=self.fonts.small, fill=0)

        # Social stats section
        social_y = self.y + self.height - 24

        # Dream count
        drm_str = f"DRM {ctx.dream_count}"
        draw.text((stats_x, social_y), drm_str, font=self.fonts.tiny, fill=0)

        # Telegram count
        tlg_str = f"TLG {ctx.telegram_count}"
        draw.text((stats_x + 44, social_y), tlg_str, font=self.fonts.tiny, fill=0)


class MessageBox:
    """
    Message area for AI responses and status text.

    Shows a single line of text with word wrapping to fit.
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.y = HEADER_HEIGHT + MAIN_HEIGHT
        self.height = MESSAGE_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the message box."""
        # Separator line
        draw_hline(draw, 0, self.y, DISPLAY_WIDTH, color=0)

        # Message text with quotes
        if ctx.message:
            # Truncate to fit
            max_chars = 38
            msg = ctx.message[:max_chars]
            if len(ctx.message) > max_chars:
                msg = msg[:-3] + "..."

            # Add decorative quotes
            display_msg = f'"{msg}"'
        else:
            display_msg = ""

        draw.text((4, self.y + 4), display_msg, font=self.fonts.normal, fill=0)


class FooterBar:
    """
    Bottom footer bar with friend indicator, lifetime stats, and mode.

    Format: "♥ friend nearby | CHAT 142 |              AUTO"
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.y = DISPLAY_HEIGHT - FOOTER_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the footer bar."""
        # Top separator
        draw_hline(draw, 0, self.y, DISPLAY_WIDTH, color=0)

        footer_y = self.y + 3

        # Friend indicator (left)
        if ctx.friend_nearby:
            friend_text = "* friend nearby"
        else:
            friend_text = ""
        draw.text((4, footer_y), friend_text, font=self.fonts.tiny, fill=0)

        # Lifetime chat count (center)
        chat_text = f"CHAT {ctx.chat_count}"
        bbox = draw.textbbox((0, 0), chat_text, font=self.fonts.tiny)
        chat_width = bbox[2] - bbox[0]
        chat_x = (DISPLAY_WIDTH - chat_width) // 2
        draw.text((chat_x, footer_y), chat_text, font=self.fonts.tiny, fill=0)

        # Mode indicator (right)
        mode_text = ctx.mode
        bbox = draw.textbbox((0, 0), mode_text, font=self.fonts.tiny)
        mode_width = bbox[2] - bbox[0]
        draw.text(
            (DISPLAY_WIDTH - mode_width - 4, footer_y),
            mode_text,
            font=self.fonts.tiny,
            fill=0,
        )


class PwnagotchiUI:
    """
    Complete Pwnagotchi-style UI renderer.

    Combines all components into a single render call.
    """

    def __init__(self):
        self.fonts = Fonts.load()
        self.header = HeaderBar(self.fonts)
        self.face_panel = FacePanel(self.fonts)
        self.stats_panel = StatsPanel(self.fonts)
        self.message_box = MessageBox(self.fonts)
        self.footer = FooterBar(self.fonts)

    def render(self, ctx: DisplayContext) -> Image.Image:
        """
        Render a complete UI frame.

        Args:
            ctx: DisplayContext with all the data to show

        Returns:
            PIL Image ready for display (1-bit, 250x122)
        """
        # Create blank white image
        image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 255)
        draw = ImageDraw.Draw(image)

        # Draw outer border
        draw_box(draw, 0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=255, outline=0)

        # Render all components
        self.header.render(draw, ctx)
        self.face_panel.render(draw, ctx)
        self.stats_panel.render(draw, ctx)
        self.message_box.render(draw, ctx)
        self.footer.render(draw, ctx)

        return image


# ============================================================================
# Utility Functions
# ============================================================================

def word_wrap(text: str, max_chars: int = 35) -> List[str]:
    """
    Wrap text to fit within max_chars per line.

    Args:
        text: Text to wrap
        max_chars: Maximum characters per line

    Returns:
        List of wrapped lines
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line += (" " if current_line else "") + word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word[:max_chars]

    if current_line:
        lines.append(current_line)

    return lines
