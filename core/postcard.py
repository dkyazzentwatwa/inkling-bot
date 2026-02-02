"""
Project Inkling - Postcard System

1-bit pixel art postcards that can be shared between Inklings.
Optimized for e-ink display (122x250 pixels max).
"""

import base64
import io
import zlib
from typing import Optional, Tuple, List
from dataclasses import dataclass

from PIL import Image


# Display dimensions (Waveshare 2.13")
MAX_WIDTH = 250
MAX_HEIGHT = 122


@dataclass
class Postcard:
    """A 1-bit pixel art postcard."""
    id: Optional[str] = None
    image_data: str = ""  # Base64 encoded compressed bitmap
    width: int = MAX_WIDTH
    height: int = MAX_HEIGHT
    caption: Optional[str] = None
    from_device_id: Optional[str] = None
    to_device_id: Optional[str] = None  # None = public
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_data": self.image_data,
            "width": self.width,
            "height": self.height,
            "caption": self.caption,
            "from_device_id": self.from_device_id,
            "to_device_id": self.to_device_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Postcard":
        return cls(
            id=data.get("id"),
            image_data=data.get("image_data", ""),
            width=data.get("width", MAX_WIDTH),
            height=data.get("height", MAX_HEIGHT),
            caption=data.get("caption"),
            from_device_id=data.get("from_device_id"),
            to_device_id=data.get("to_device_id"),
            created_at=data.get("created_at"),
        )


class PostcardCodec:
    """
    Encodes and decodes 1-bit images for postcards.

    Format: zlib-compressed raw bitmap, base64 encoded
    Each byte contains 8 pixels (MSB first)
    """

    @staticmethod
    def encode_image(image: Image.Image) -> Tuple[str, int, int]:
        """
        Encode a PIL Image to postcard format.

        Args:
            image: PIL Image (will be converted to 1-bit)

        Returns:
            Tuple of (base64_data, width, height)
        """
        # Ensure correct mode and size
        if image.mode != "1":
            image = image.convert("1")

        # Resize if too large
        if image.width > MAX_WIDTH or image.height > MAX_HEIGHT:
            image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.NEAREST)

        width, height = image.size

        # Convert to raw bitmap (1 bit per pixel, packed into bytes)
        raw_bytes = []
        current_byte = 0
        bit_count = 0

        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                # 1-bit: 0 = black, 255 = white
                bit = 0 if pixel == 0 else 1

                current_byte = (current_byte << 1) | bit
                bit_count += 1

                if bit_count == 8:
                    raw_bytes.append(current_byte)
                    current_byte = 0
                    bit_count = 0

        # Handle remaining bits
        if bit_count > 0:
            current_byte <<= (8 - bit_count)
            raw_bytes.append(current_byte)

        # Compress with zlib
        compressed = zlib.compress(bytes(raw_bytes), level=9)

        # Base64 encode
        encoded = base64.b64encode(compressed).decode("ascii")

        return encoded, width, height

    @staticmethod
    def decode_image(data: str, width: int, height: int) -> Image.Image:
        """
        Decode postcard data to PIL Image.

        Args:
            data: Base64 encoded compressed bitmap
            width: Image width
            height: Image height

        Returns:
            PIL Image in 1-bit mode
        """
        # Base64 decode
        compressed = base64.b64decode(data)

        # Decompress
        raw_bytes = zlib.decompress(compressed)

        # Create image
        image = Image.new("1", (width, height), 255)  # White background

        byte_idx = 0
        bit_idx = 7

        for y in range(height):
            for x in range(width):
                if byte_idx < len(raw_bytes):
                    bit = (raw_bytes[byte_idx] >> bit_idx) & 1
                    # 0 = black, 1 = white
                    pixel = 0 if bit == 0 else 255
                    image.putpixel((x, y), pixel)

                    bit_idx -= 1
                    if bit_idx < 0:
                        bit_idx = 7
                        byte_idx += 1

        return image

    @staticmethod
    def create_from_pixels(
        pixels: List[List[int]],
        width: int,
        height: int
    ) -> Tuple[str, int, int]:
        """
        Create postcard from 2D pixel array.

        Args:
            pixels: 2D array of 0 (black) or 1 (white)
            width: Image width
            height: Image height

        Returns:
            Tuple of (base64_data, width, height)
        """
        image = Image.new("1", (width, height), 255)

        for y, row in enumerate(pixels):
            for x, pixel in enumerate(row):
                if x < width and y < height:
                    image.putpixel((x, y), 0 if pixel == 0 else 255)

        return PostcardCodec.encode_image(image)


class PostcardCanvas:
    """
    Simple drawing canvas for creating postcards.

    Provides basic drawing primitives for pixel art.
    """

    def __init__(self, width: int = MAX_WIDTH, height: int = MAX_HEIGHT):
        self.width = min(width, MAX_WIDTH)
        self.height = min(height, MAX_HEIGHT)
        self._image = Image.new("1", (self.width, self.height), 255)  # White

    def clear(self, color: int = 255) -> None:
        """Clear canvas to color (0=black, 255=white)."""
        self._image = Image.new("1", (self.width, self.height), color)

    def set_pixel(self, x: int, y: int, color: int = 0) -> None:
        """Set a single pixel (0=black, 255=white)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._image.putpixel((x, y), color)

    def get_pixel(self, x: int, y: int) -> int:
        """Get pixel value at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._image.getpixel((x, y))
        return 255

    def draw_line(
        self,
        x0: int, y0: int,
        x1: int, y1: int,
        color: int = 0
    ) -> None:
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.set_pixel(x0, y0, color)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def draw_rect(
        self,
        x: int, y: int,
        w: int, h: int,
        color: int = 0,
        fill: bool = False
    ) -> None:
        """Draw a rectangle."""
        if fill:
            for py in range(y, y + h):
                for px in range(x, x + w):
                    self.set_pixel(px, py, color)
        else:
            # Top and bottom
            for px in range(x, x + w):
                self.set_pixel(px, y, color)
                self.set_pixel(px, y + h - 1, color)
            # Left and right
            for py in range(y, y + h):
                self.set_pixel(x, py, color)
                self.set_pixel(x + w - 1, py, color)

    def draw_circle(
        self,
        cx: int, cy: int,
        radius: int,
        color: int = 0,
        fill: bool = False
    ) -> None:
        """Draw a circle using midpoint algorithm."""
        if fill:
            for y in range(-radius, radius + 1):
                for x in range(-radius, radius + 1):
                    if x * x + y * y <= radius * radius:
                        self.set_pixel(cx + x, cy + y, color)
        else:
            x = radius
            y = 0
            err = 0

            while x >= y:
                self.set_pixel(cx + x, cy + y, color)
                self.set_pixel(cx + y, cy + x, color)
                self.set_pixel(cx - y, cy + x, color)
                self.set_pixel(cx - x, cy + y, color)
                self.set_pixel(cx - x, cy - y, color)
                self.set_pixel(cx - y, cy - x, color)
                self.set_pixel(cx + y, cy - x, color)
                self.set_pixel(cx + x, cy - y, color)

                y += 1
                err += 1 + 2 * y
                if 2 * (err - x) + 1 > 0:
                    x -= 1
                    err += 1 - 2 * x

    def draw_text(
        self,
        x: int, y: int,
        text: str,
        color: int = 0
    ) -> None:
        """
        Draw text using a simple 5x7 pixel font.

        Only supports ASCII uppercase, lowercase, digits, and basic punctuation.
        """
        # Simple 5x7 font for common characters
        font = _get_simple_font()

        cursor_x = x
        for char in text:
            if char in font:
                bitmap = font[char]
                for row_idx, row in enumerate(bitmap):
                    for col_idx in range(5):
                        if row & (1 << (4 - col_idx)):
                            self.set_pixel(cursor_x + col_idx, y + row_idx, color)
                cursor_x += 6  # 5 pixels + 1 space
            elif char == " ":
                cursor_x += 4
            else:
                cursor_x += 6

    def to_postcard(self, caption: Optional[str] = None) -> Postcard:
        """Convert canvas to a Postcard object."""
        data, width, height = PostcardCodec.encode_image(self._image)
        return Postcard(
            image_data=data,
            width=width,
            height=height,
            caption=caption,
        )

    def get_image(self) -> Image.Image:
        """Get the underlying PIL Image."""
        return self._image.copy()

    def load_image(self, image: Image.Image) -> None:
        """Load an existing image into the canvas."""
        if image.mode != "1":
            image = image.convert("1")

        if image.width > MAX_WIDTH or image.height > MAX_HEIGHT:
            image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.NEAREST)

        self._image = image
        self.width = image.width
        self.height = image.height


def _get_simple_font() -> dict:
    """Return a simple 5x7 bitmap font for common characters."""
    # Each character is a list of 7 rows, each row is a 5-bit bitmap
    # MSB is leftmost pixel
    return {
        'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
        'B': [0b11110, 0b10001, 0b11110, 0b10001, 0b10001, 0b10001, 0b11110],
        'C': [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
        'D': [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
        'E': [0b11111, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000, 0b11111],
        'F': [0b11111, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000, 0b10000],
        'G': [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
        'H': [0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001, 0b10001],
        'I': [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        'J': [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
        'K': [0b10001, 0b10010, 0b11100, 0b10010, 0b10001, 0b10001, 0b10001],
        'L': [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
        'M': [0b10001, 0b11011, 0b10101, 0b10001, 0b10001, 0b10001, 0b10001],
        'N': [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
        'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        'P': [0b11110, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000, 0b10000],
        'Q': [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b01110, 0b00001],
        'R': [0b11110, 0b10001, 0b11110, 0b10010, 0b10001, 0b10001, 0b10001],
        'S': [0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
        'T': [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
        'U': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        'V': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
        'W': [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
        'X': [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
        'Y': [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
        'Z': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
        '0': [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
        '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        '2': [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
        '3': [0b01110, 0b10001, 0b00001, 0b00110, 0b00001, 0b10001, 0b01110],
        '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
        '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
        '6': [0b01110, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b01110],
        '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
        '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
        '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110],
        '.': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100],
        ',': [0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b00100, 0b01000],
        '!': [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
        '?': [0b01110, 0b10001, 0b00010, 0b00100, 0b00100, 0b00000, 0b00100],
        '-': [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
        ':': [0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000],
        '<': [0b00010, 0b00100, 0b01000, 0b10000, 0b01000, 0b00100, 0b00010],
        '>': [0b01000, 0b00100, 0b00010, 0b00001, 0b00010, 0b00100, 0b01000],
    }
