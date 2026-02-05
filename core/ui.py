"""
Project Inkling - UI Components

Pwnagotchi-inspired UI components for the e-ink display:
- Drawing primitives (boxes, lines)
- Widget classes for layout regions
- Face rendering with large Unicode characters

Layout (250x122 pixels):
┌─────────────────────────────────────────────────────┐
│ inkling>█              Curious          UP 00:15:32 │  <- Header (14px)
├─────────────────────────────────────────────────────┤
│                                                     │
│  Hey there! I'm feeling pretty curious about       │  <- Message (86px)
│  the world today. What's on your mind?             │
│                                                     │
├─────────────────────────────────────────────────────┤
│ (^_^) │ L1 NEWB │ 54%mem 1%cpu 43° │ CHAT3 │ SSH  │  <- Footer (22px)
└─────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List, Sequence
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

# Extended Unicode faces (cleaner, more compatible)
# These use well-supported Unicode characters that render correctly
# in browsers, terminals, and e-ink displays
UNICODE_FACES = {
    # Looking directions
    "look_r": "( ◉_◉)",
    "look_l": "(◉_◉ )",
    "look_r_happy": "( ◉‿◉)",
    "look_l_happy": "(◉‿◉ )",

    # Sleep states
    "sleep": "(ᴗ﹏ᴗ)",
    "sleep2": "(•﹏•)",
    "sleepy": "(-‿‿-)",

    # Basic emotions
    "awake": "(◉‿◉)",
    "bored": "(-__-)",
    "intense": "(•_•)",
    "cool": "(⌐■_■)",
    "happy": "(•‿‿•)",
    "excited": "(◕‿◕)",
    "grateful": "(◕‿◕)",
    "motivated": "(◉‿◉)",
    "demotivated": "(•__•)",

    # Moods
    "smart": "(◉_◉)",
    "lonely": "(·•·)",
    "sad": "(╥﹏╥)",
    "angry": "(ಠ_ಠ)",
    "curious": "(ಠ‿ಠ)?",
    "thinking": "(◕.◕)",
    "confused": "(•_•)?",
    "surprised": "(◉_◉)!",

    # Special
    "friend": "(◕‿◕✿)",
    "broken": "(✖╭╮✖)",
    "debug": "(◈‿◈)",
    "love": "(♥‿♥)",

    # Upload/working states
    "upload": "(⌐◉‿◉)",
    "upload1": "(◉‿•)",
    "upload2": "(•‿◉)",
    "working": "(◉_•)",
    "searching": "(◉_◉)",
    "success": "(◕‿◕)v",
}


# ============================================================================
# Layout Constants
# ============================================================================

# Layout constants for 250x122 display
DISPLAY_WIDTH = 250
DISPLAY_HEIGHT = 122

# Region heights
HEADER_HEIGHT = 14
FOOTER_HEIGHT = 30  # Taller footer for less crowded stats + clock
MESSAGE_HEIGHT = DISPLAY_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT - 2

# Full-width message panel (no side stats panel anymore)
MESSAGE_PANEL_WIDTH = DISPLAY_WIDTH - 4  # Full width with small margins
MESSAGE_LINE_HEIGHT = 13
MESSAGE_MAX_LINES = max(1, MESSAGE_HEIGHT // MESSAGE_LINE_HEIGHT)


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
                    face=ImageFont.truetype(path, 38),  # Larger face (was 22)
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
    clock_time: str = "--:--"

    # Social stats
    dream_count: int = 0
    telegram_count: int = 0
    chat_count: int = 0
    friend_nearby: bool = False

    # Progression
    level: int = 1
    level_name: str = "Newborn"
    xp_progress: float = 0.0  # 0.0-1.0
    prestige: int = 0

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
        name_text = ctx.name[:8]
        cursor_text = ">_"
        name_x = 3
        name_y = self.y + 2
        draw_text_bold(draw, (name_x, name_y), name_text, font=self.fonts.small, fill=0)
        cursor_x = name_x + text_width(draw, name_text, self.fonts.small)
        draw.text((cursor_x, name_y), cursor_text, font=self.fonts.small, fill=0)

        # Mood text (centered-ish)
        mood_x = 80
        draw_text_bold(
            draw,
            (mood_x, self.y + 2),
            ctx.mood_text[:12],
            font=self.fonts.small,
            fill=0,
        )

        # Uptime (right-aligned)
        uptime_prefix = "UP"
        uptime_suffix = f" {ctx.uptime}"
        uptime_width = text_width(draw, uptime_prefix + uptime_suffix, self.fonts.tiny)
        uptime_x = DISPLAY_WIDTH - uptime_width - 6
        uptime_y = self.y + 3
        draw_text_bold(draw, (uptime_x, uptime_y), uptime_prefix, font=self.fonts.tiny, fill=0)
        draw_text_bold(
            (uptime_x + text_width(draw, uptime_prefix, self.fonts.tiny), uptime_y),
            uptime_suffix,
            font=self.fonts.tiny,
            fill=0,
        )


class MessagePanel:
    """
    Left panel showing AI message responses (was FacePanel).

    Renders multi-line text with word wrapping.
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.x = 2  # Small margin
        self.y = HEADER_HEIGHT
        self.width = MESSAGE_PANEL_WIDTH
        self.height = MESSAGE_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the message panel with word-wrapped text."""
        if not ctx.message:
            return

        # Word wrap to fit panel (approx 40 chars per line at font size 11, full width)
        max_chars_per_line = 40
        lines = word_wrap(ctx.message, max_chars_per_line)

        # Calculate starting Y to vertically center text block
        line_height = MESSAGE_LINE_HEIGHT
        total_text_height = len(lines) * line_height
        start_y = self.y + (self.height - total_text_height) // 2

        # Draw each line centered horizontally
        text_y = start_y
        for line in lines[:MESSAGE_MAX_LINES]:
            # Calculate width of this line to center it
            bbox = draw.textbbox((0, 0), line, font=self.fonts.normal)
            text_width = bbox[2] - bbox[0]
            # Center horizontally within the message panel
            text_x = self.x + (self.width - text_width) // 2
            draw.text((text_x, text_y), line, font=self.fonts.normal, fill=0)
            text_y += line_height


# NOTE: StatsPanel and FaceBox are no longer used in the new layout.
# All stats and face are now rendered in the compact FooterBar.
# Keeping these commented out for reference.

# class StatsPanel:
#     """
#     Right panel showing system and social stats.
#     DEPRECATED: Functionality moved to FooterBar in new layout.
#     """
#     pass

# class FaceBox:
#     """
#     Face expression area (was MessageBox).
#     DEPRECATED: Face now shown in FooterBar in new layout.
#     """
#     pass


class FooterBar:
    """
    Bottom footer bar with all stats in compact format.

    Two-line format to reduce crowding:
    Line 1: "(^_^) | L1 NEWB | SSH"
    Line 2: "54%mem 1%cpu 43° | CH3 | 10:42"
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.y = DISPLAY_HEIGHT - FOOTER_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the footer bar with compact stats."""
        # Top separator
        draw_hline(draw, 0, self.y, DISPLAY_WIDTH, color=0)

        line1_y = self.y + 3
        line2_y = self.y + 16

        # Line 1 components
        line1 = []

        # 1. Face
        line1.append(ctx.face_str)

        # 2. Level and rank
        level_name_short = ctx.level_name.split()[0][:4].upper()  # "NEWB", "CURI", etc.
        level_str = f"L{ctx.level}"
        if ctx.prestige > 0:
            level_str += "*" * min(ctx.prestige, 3)
        line1.append(f"{level_str} {level_name_short}")

        # 3. Mode
        line1.append(ctx.mode)

        # Line 2 components
        line2 = []

        # 1. System stats (memory, cpu, temp)
        temp_str = f"{ctx.temperature}°" if ctx.temperature > 0 else "--°"
        line2.append(f"{ctx.memory_percent}%mem {ctx.cpu_percent}%cpu {temp_str}")

        # 2. Chat count
        line2.append(f"CH{ctx.chat_count}")

        # 3. Clock
        line2.append(ctx.clock_time)

        # Join with vertical bar separator (render separators in bold)
        separator = "   |   "
        line1_segments = interleave_with_separator(line1, separator)
        line2_segments = interleave_with_separator(line2, separator)

        # Center line 1
        line1_width = sum(text_width(draw, seg.text, self.fonts.small) for seg in line1_segments)
        line1_x = (DISPLAY_WIDTH - line1_width) // 2

        # Center line 2
        line2_width = sum(text_width(draw, seg.text, self.fonts.small) for seg in line2_segments)
        line2_x = (DISPLAY_WIDTH - line2_width) // 2

        # Draw line 1
        x = line1_x
        for seg in line1_segments:
            draw_text_bold(draw, (x, line1_y), seg.text, font=self.fonts.small, fill=0)
            x += text_width(draw, seg.text, self.fonts.small)

        # Draw line 2
        x = line2_x
        for seg in line2_segments:
            draw_text_bold(draw, (x, line2_y), seg.text, font=self.fonts.small, fill=0)
            x += text_width(draw, seg.text, self.fonts.small)


class PwnagotchiUI:
    """
    Complete Pwnagotchi-style UI renderer.

    Combines all components into a single render call.
    New layout: Full-width message area with compact footer containing all stats.
    """

    def __init__(self):
        self.fonts = Fonts.load()
        self.header = HeaderBar(self.fonts)
        self.message_panel = MessagePanel(self.fonts)
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
        self.message_panel.render(draw, ctx)
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


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """Measure text width in pixels for a given font."""
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def draw_text_bold(
    draw: ImageDraw.ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: int = 0,
) -> None:
    """Simulate bold text by drawing twice with a 1px offset."""
    x, y = position
    draw.text((x, y), text, font=font, fill=fill)
    draw.text((x + 1, y), text, font=font, fill=fill)


class TextSegment:
    """Segment of text with an optional bold flag."""

    def __init__(self, text: str, bold: bool = False):
        self.text = text
        self.bold = bold


def interleave_with_separator(parts: Sequence[str], sep: str) -> List[TextSegment]:
    """Interleave parts with a bold separator segment."""
    segments: List[TextSegment] = []
    for idx, part in enumerate(parts):
        if idx > 0:
            segments.append(TextSegment(sep, bold=True))
        segments.append(TextSegment(part, bold=False))
    return segments
