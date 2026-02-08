"""
Project Inkling - UI Components

Pwnagotchi-inspired UI components for the e-ink display:
- Drawing primitives (boxes, lines)
- Widget classes for layout regions
- XP progress bar for visual leveling motivation

Layout (250x122 pixels):
┌─────────────────────────────────────────────────────┐
│ inkling> Cool               ▂▄▆ UP 00:15:32        │  <- Header (14px, WiFi bars)
├─────────────────────────────────────────────────────┤
│                                                     │
│  Hey there! I'm feeling pretty curious about       │  <- Message (86px)
│  the world today. What's on your mind?             │
│                                                     │
├─────────────────────────────────────────────────────┤
│        [████████░░] 80% │ L1 NEWB │ SSH            │  <- Footer Line 1 (XP bar!)
│     BAT 85% 54%m 1%c 43° │ CH3 │ 10:42            │  <- Footer Line 2
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
    prefer_ascii: bool = True

    # Animation support
    animation_action: str = "idle"  # Current action (idle, walk, dance, etc.)
    mood_key: str = "happy"         # Current mood from Personality
    message_y_offset: int = 0       # Push message down if sprite rendered above

    # System stats
    memory_percent: int = 0
    cpu_percent: int = 0
    temperature: int = 0
    clock_time: str = "--:--"

    # WiFi stats
    wifi_ssid: Optional[str] = None
    wifi_signal: int = 0

    # Social stats
    dream_count: int = 0
    telegram_count: int = 0
    chat_count: int = 0
    friend_nearby: bool = False

    # Battery stats
    battery_percentage: int = -1
    is_charging: bool = False

    # Progression
    level: int = 1
    level_name: str = "Newborn"
    xp_progress: float = 0.0  # 0.0-1.0
    prestige: int = 0

    # Message
    message: str = ""

    # Mode indicator
    mode: str = "AUTO"


class FaceSprite:
    """
    Render animated face sprite in the message area.

    Positioned above the text message, centered horizontally.
    Supports mood-based animated sprites with frame cycling.
    """

    def __init__(self, sprite_manager, fonts: Fonts, sprite_size: int = 48):
        """
        Initialize FaceSprite component.

        Args:
            sprite_manager: SpriteManager instance for loading sprites
            fonts: Fonts instance for fallback text rendering
            sprite_size: Size of sprites in pixels (default 48x48)
        """
        from core.sprites import AnimationState

        self.sprite_manager = sprite_manager
        self.fonts = fonts
        self.sprite_size = sprite_size
        self.animation_state = AnimationState()

    def set_action(self, action: str, mood: str):
        """Set current action/mood for animation."""
        self.animation_state.set_action(action, mood)

    def update_animation(self) -> bool:
        """
        Advance animation frame if needed.

        Returns:
            True if frame changed, False otherwise
        """
        return self.animation_state.update()

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> Tuple[int, int]:
        """
        Render animated face sprite.

        Args:
            draw: PIL ImageDraw instance
            ctx: Display context with animation state

        Returns:
            (x, y) position where sprite was drawn, or (0, 0) if no sprite
        """
        # Get current animation frame
        action = ctx.animation_action or self.animation_state.action
        mood = ctx.mood_key or self.animation_state.mood
        frame_idx = self.animation_state.frame_index

        # Get sprite from manager
        face_sprite = self.sprite_manager.get_animation_frame(action, mood, frame_idx)

        if not face_sprite:
            # Fallback: try idle sprite
            if action != "idle":
                face_sprite = self.sprite_manager.get_idle_sprite(mood)

        if not face_sprite:
            # Final fallback: draw text face
            return self._render_text_face(draw, ctx)

        # Calculate center position in message area
        sprite_x = (DISPLAY_WIDTH - self.sprite_size) // 2
        sprite_y = HEADER_HEIGHT + 10  # 10px below header

        # Paste sprite onto image
        try:
            draw._image.paste(face_sprite, (sprite_x, sprite_y))
        except Exception as e:
            # If paste fails, fall back to text
            return self._render_text_face(draw, ctx)

        return (sprite_x, sprite_y)

    def _render_text_face(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> Tuple[int, int]:
        """Fallback to text-based face if sprite not found."""
        text = ctx.face_str
        bbox = draw.textbbox((0, 0), text, font=self.fonts.face)
        text_width_px = bbox[2] - bbox[0]
        x = (DISPLAY_WIDTH - text_width_px) // 2
        y = HEADER_HEIGHT + 15
        draw.text((x, y), text, font=self.fonts.face, fill=0)
        return (x, y)


class HeaderBar:
    """
    Top header bar with name, mood, WiFi signal, battery, and uptime.

    Format: "name> Mood  [WiFi bars] BAT 92% UP HH:MM:SS"
    """

    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.height = HEADER_HEIGHT
        self.y = 0

    def render(self, draw: ImageDraw.ImageDraw, ctx: DisplayContext) -> None:
        """Render the header bar."""
        # Background
        draw_box(draw, 0, self.y, DISPLAY_WIDTH, self.height, fill=255, outline=0)

        # Name + mood together (left-aligned, no cursor)
        name_mood = f"{ctx.name[:8]}> {ctx.mood_text[:12]}"
        draw_text_bold(draw, (3, self.y + 2), name_mood, font=self.fonts.small, fill=0)

        # Build right-side text: WiFi + Battery + Uptime
        right_parts = []

        # WiFi bars if connected
        if ctx.wifi_ssid and ctx.wifi_signal > 0:
            from core.wifi_utils import get_wifi_bars
            wifi_bars = get_wifi_bars(ctx.wifi_signal)
            right_parts.append(wifi_bars)

        # Battery percentage if available
        if ctx.battery_percentage != -1:
            if ctx.prefer_ascii:
                battery_icon = "CHG" if ctx.is_charging else "BAT"
            else:
                battery_icon = "⚡" if ctx.is_charging else "🔋"
            right_parts.append(f"{battery_icon}%{ctx.battery_percentage}")

        # Uptime
        right_parts.append(f"UP {ctx.uptime}")

        # Join and right-align
        right_text = " ".join(right_parts)
        right_width = text_width(draw, right_text, self.fonts.tiny)
        right_x = DISPLAY_WIDTH - right_width - 6
        draw.text((right_x, self.y + 3), right_text, font=self.fonts.tiny, fill=0)


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

        # Pixel-based word wrap with actual font measurement
        max_width = self.width - 10  # Leave some margin
        lines = word_wrap_pixels(ctx.message, max_width, self.fonts.normal, draw)

        # Calculate available space accounting for footer boundary
        line_height = MESSAGE_LINE_HEIGHT

        # Adjust for sprite if present
        effective_y = self.y + ctx.message_y_offset
        effective_height = self.height - ctx.message_y_offset

        # Footer starts at DISPLAY_HEIGHT - FOOTER_HEIGHT
        footer_start = DISPLAY_HEIGHT - FOOTER_HEIGHT
        max_bottom_y = footer_start - 2  # Leave 2px gap before footer

        # Only apply vertical offset when no sprite is present (saves space with sprites)
        vertical_offset = 8 if ctx.message_y_offset == 0 else 0

        # Calculate how many lines can fit without overflowing into footer
        available_height = max_bottom_y - effective_y - vertical_offset
        max_lines = max(1, available_height // line_height)

        # Limit to calculated max or MESSAGE_MAX_LINES, whichever is smaller
        lines_to_render = min(len(lines), max_lines, MESSAGE_MAX_LINES)

        # Center the text block vertically within available space
        total_text_height = lines_to_render * line_height
        start_y = effective_y + max(0, (available_height - total_text_height) // 2)

        # Ensure we don't start below footer (safety check)
        if start_y + total_text_height > max_bottom_y:
            start_y = max_bottom_y - total_text_height

        # Draw each line centered horizontally
        text_y = start_y
        for line in lines[:lines_to_render]:
            # Stop if we would overflow into footer (additional safety)
            if text_y + line_height > max_bottom_y:
                break

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
    Bottom footer bar with system stats and info.

    Two-line format:
    Line 1: "[████████░░] 80% | L12 EXPL | SSH"
    Line 2: "54%m 1%c 43° | CH3 | 14:23"

    Note: Battery moved to header for better visibility.
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

        # 1. XP Bar (replaces face)
        xp_bar = format_xp_bar(ctx.xp_progress, bar_width=10, show_percentage=True)
        line1.append(xp_bar)

        # 2. Level and rank
        level_name_short = ctx.level_name.split()[0][:4].upper()  # "NEWB", "CURI", etc.
        level_str = f"L{ctx.level}"
        if ctx.prestige > 0:
            level_str += "*" * min(ctx.prestige, 3)
        line1.append(f"{level_str} {level_name_short}")

        # 3. Mode
        line1.append(ctx.mode)

        # Line 2 components
        line2_left = []

        # 1. System stats (memory, cpu, temp)
        temp_str = f"{ctx.temperature}°" if ctx.temperature > 0 else "--°"
        line2_left.append(f"{ctx.memory_percent}%m {ctx.cpu_percent}%c {temp_str}")

        # 2. Chat count
        line2_left.append(f"CH{ctx.chat_count}")

        # 3. Clock time
        line2_left.append(ctx.clock_time)

        # Join with vertical bar separator
        separator = "   |   "
        line1_segments = interleave_with_separator(line1, separator)
        line2_segments = interleave_with_separator(line2_left, separator)

        # Center line 1
        line1_width = sum(text_width(draw, seg.text, self.fonts.small) for seg in line1_segments)
        line1_x = (DISPLAY_WIDTH - line1_width) // 2

        # Draw line 1
        x = line1_x
        for seg in line1_segments:
            draw.text((x, line1_y), seg.text, font=self.fonts.small, fill=0)
            x += text_width(draw, seg.text, self.fonts.small)

        # Center line 2
        line2_width = sum(text_width(draw, seg.text, self.fonts.small) for seg in line2_segments)
        line2_x = (DISPLAY_WIDTH - line2_width) // 2

        # Draw line 2
        x = line2_x
        for seg in line2_segments:
            draw.text((x, line2_y), seg.text, font=self.fonts.small, fill=0)
            x += text_width(draw, seg.text, self.fonts.small)


def format_xp_bar(progress: float, bar_width: int = 10, show_percentage: bool = True) -> str:
    """
    Generate visual XP progress bar.

    Args:
        progress: Progress as 0.0-1.0
        bar_width: Number of blocks in the bar
        show_percentage: Include percentage text

    Returns:
        XP bar string like "[████████░░] 80%"
    """
    filled = int(progress * bar_width)
    empty = bar_width - filled

    # Use Unicode blocks for filled/empty
    filled_char = "█"
    empty_char = "░"

    bar = f"[{filled_char * filled}{empty_char * empty}]"

    if show_percentage:
        pct = int(progress * 100)
        bar += f" {pct}%"

    return bar


class PwnagotchiUI:
    """
    Complete Pwnagotchi-style UI renderer.

    Combines all components into a single render call.
    New layout: Full-width message area with compact footer containing all stats.
    """

    def __init__(self, sprite_manager=None):
        """
        Initialize PwnagotchiUI.

        Args:
            sprite_manager: Optional SpriteManager for animated sprites
        """
        self.fonts = Fonts.load()
        self.header = HeaderBar(self.fonts)
        self.message_panel = MessagePanel(self.fonts)
        self.footer = FooterBar(self.fonts)
        self.face_sprite = FaceSprite(sprite_manager, self.fonts) if sprite_manager else None

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

        # Render header
        self.header.render(draw, ctx)

        # Render face sprite if enabled
        sprite_y_end = 0
        if self.face_sprite and self.face_sprite.sprite_manager.is_enabled():
            sprite_pos = self.face_sprite.render(draw, ctx)
            sprite_y_end = sprite_pos[1] + self.face_sprite.sprite_size

        # Adjust message panel to start below sprite if rendered
        if sprite_y_end > 0:
            # Create adjusted context with message offset
            from dataclasses import replace as dataclass_replace
            ctx_adjusted = dataclass_replace(ctx, message_y_offset=sprite_y_end + 5)
            self.message_panel.render(draw, ctx_adjusted)
        else:
            self.message_panel.render(draw, ctx)

        # Render footer
        self.footer.render(draw, ctx)

        return image


# ============================================================================
# Utility Functions
# ============================================================================

def word_wrap(text: str, max_chars: int = 35) -> List[str]:
    """
    Wrap text to fit within max_chars per line.

    DEPRECATED: Use word_wrap_pixels() for pixel-accurate wrapping.
    This is kept for backward compatibility with non-display uses (terminal output, etc).

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


def word_wrap_pixels(
    text: str,
    max_width: int,
    font: ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw
) -> List[str]:
    """
    Wrap text based on actual pixel width using the given font.

    This is the preferred method for display text wrapping as it handles
    variable-width fonts correctly and prevents text cutoff.

    Args:
        text: Text to wrap
        max_width: Maximum width in pixels
        font: Font to use for measuring
        draw: ImageDraw object for text measurement

    Returns:
        List of wrapped lines
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # Measure width of current line + new word
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            # Fits on current line
            current_line = test_line
        else:
            # Doesn't fit - start new line
            if current_line:
                lines.append(current_line)

            # Check if single word is too long
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]

            if word_width > max_width:
                # Word is too long - break it with hyphen
                current_line = ""
                for i in range(len(word)):
                    test = current_line + word[i]
                    bbox = draw.textbbox((0, 0), test + "-", font=font)
                    if bbox[2] - bbox[0] > max_width and current_line:
                        lines.append(current_line + "-")
                        current_line = word[i]
                    else:
                        current_line = test
            else:
                current_line = word

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
