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
│ Hey there! I'm feeling   │ mem  cpu  temp       │
│ pretty curious about     │ 42%  18%   41°       │  <- Main (70px)
│ the world today. What's  │                      │
│ on your mind?            │ DRM 5    TLG 2       │
├──────────────────────────┴──────────────────────────┤
│                     (  ◉  ‿  ◉  )                   │  <- Face (20px)
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
FOOTER_HEIGHT = 14
MESSAGE_HEIGHT = 18
MAIN_HEIGHT = DISPLAY_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT - MESSAGE_HEIGHT - 4  # 72px

# Divider positions
STATS_PANEL_WIDTH = 70  # Right panel width for stats
MESSAGE_PANEL_WIDTH = DISPLAY_WIDTH - STATS_PANEL_WIDTH - 2  # Left panel width for messages (178px)


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


class MessagePanel:
    """
    Left panel showing AI message responses (was FacePanel).

    Renders multi-line text with word wrapping.
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.x = 0
        self.y = HEADER_HEIGHT
        self.width = MESSAGE_PANEL_WIDTH
        self.height = MAIN_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the message panel with word-wrapped text."""
        if not ctx.message:
            return

        # Word wrap to fit panel (approx 28 chars per line at font size 11)
        max_chars_per_line = 28
        lines = word_wrap(ctx.message, max_chars_per_line)

        # Calculate starting Y to vertically center text block
        line_height = 13
        total_text_height = len(lines) * line_height
        start_y = self.y + (self.height - total_text_height) // 2

        # Draw each line
        text_x = self.x + 4
        text_y = start_y
        for line in lines[:5]:  # Max 5 lines to fit in panel
            draw.text((text_x, text_y), line, font=self.fonts.normal, fill=0)
            text_y += line_height


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
        self.x = MESSAGE_PANEL_WIDTH + 1
        self.y = HEADER_HEIGHT
        self.width = STATS_PANEL_WIDTH
        self.height = MAIN_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the stats panel."""
        # Vertical separator
        draw_vline(draw, self.x, self.y, self.height, color=0)

        # System stats section (compact layout for narrower panel)
        stats_x = self.x + 3
        stats_y = self.y + 4

        # Labels row (tighter spacing for 70px width)
        draw.text((stats_x, stats_y), "mem", font=self.fonts.tiny, fill=0)
        draw.text((stats_x + 22, stats_y), "cpu", font=self.fonts.tiny, fill=0)
        draw.text((stats_x + 44, stats_y), "tmp", font=self.fonts.tiny, fill=0)

        # Values row
        stats_y += 10
        mem_str = f"{ctx.memory_percent}%"
        cpu_str = f"{ctx.cpu_percent}%"
        temp_str = f"{ctx.temperature}°" if ctx.temperature > 0 else "--°"

        draw.text((stats_x, stats_y), mem_str, font=self.fonts.small, fill=0)
        draw.text((stats_x + 22, stats_y), cpu_str, font=self.fonts.small, fill=0)
        draw.text((stats_x + 44, stats_y), temp_str, font=self.fonts.small, fill=0)

        # Level section (middle area)
        level_y = self.y + 30

        # Level badge
        level_display = f"L{ctx.level}"
        if ctx.prestige > 0:
            stars = "⭐" * min(ctx.prestige, 3)  # Max 3 stars to fit
            level_display = f"L{ctx.level} {stars}"

        draw.text((stats_x, level_y), level_display, font=self.fonts.small, fill=0)

        # Level name (abbreviated)
        level_name_short = ctx.level_name.split()[0][:4].upper()  # "NEWB", "CURI", "CHAT", "WISE", "SAGE", "ANCI", "LEGE"
        draw.text((stats_x, level_y + 11), level_name_short, font=self.fonts.tiny, fill=0)

        # XP progress bar (60px wide, 4px tall)
        bar_width = 60
        bar_height = 4
        bar_x = stats_x
        bar_y = level_y + 22

        # Draw bar outline
        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_width - 1, bar_y + bar_height - 1],
            fill=255,
            outline=0,
            width=1
        )

        # Draw progress fill
        fill_width = int((bar_width - 2) * ctx.xp_progress)
        if fill_width > 0:
            draw.rectangle(
                [bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 2],
                fill=0
            )

        # Social stats section (bottom)
        social_y = self.y + self.height - 14

        # Dream count
        drm_str = f"DRM {ctx.dream_count}"
        draw.text((stats_x, social_y), drm_str, font=self.fonts.tiny, fill=0)

        # Telegram count (below dreams)
        tlg_str = f"TLG {ctx.telegram_count}"
        draw.text((stats_x + 34, social_y), tlg_str, font=self.fonts.tiny, fill=0)


class FaceBox:
    """
    Face expression area (was MessageBox).

    Shows the face expression centered in the bottom bar.
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.y = HEADER_HEIGHT + MAIN_HEIGHT
        self.height = MESSAGE_HEIGHT

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the face box."""
        # Separator line
        draw_hline(draw, 0, self.y, DISPLAY_WIDTH, color=0)

        # Draw face centered using the larger face font
        if ctx.face_str:
            face_text = ctx.face_str
            # Use face font for better rendering (38px)
            bbox = draw.textbbox((0, 0), face_text, font=self.fonts.face)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Center horizontally and vertically in the face box
            face_x = (DISPLAY_WIDTH - text_width) // 2
            face_y = self.y + (self.height - text_height) // 2

            draw.text((face_x, face_y), face_text, font=self.fonts.face, fill=0)


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
        self.message_panel = MessagePanel(self.fonts)
        self.stats_panel = StatsPanel(self.fonts)
        self.face_box = FaceBox(self.fonts)
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
        self.stats_panel.render(draw, ctx)
        self.face_box.render(draw, ctx)
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
