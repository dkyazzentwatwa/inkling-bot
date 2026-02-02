"""
Project Inkling - Postcard Tests

Tests for core/postcard.py - 1-bit image encoding/decoding and drawing canvas.
"""

import pytest
from PIL import Image


class TestPostcardDataclass:
    """Tests for Postcard dataclass."""

    def test_postcard_defaults(self):
        """Test Postcard default values."""
        from core.postcard import Postcard, MAX_WIDTH, MAX_HEIGHT

        postcard = Postcard()

        assert postcard.id is None
        assert postcard.image_data == ""
        assert postcard.width == MAX_WIDTH
        assert postcard.height == MAX_HEIGHT
        assert postcard.caption is None

    def test_postcard_to_dict(self):
        """Test Postcard serialization."""
        from core.postcard import Postcard

        postcard = Postcard(
            id="test123",
            image_data="abc123",
            width=100,
            height=50,
            caption="Hello!",
            from_device_id="device1",
            to_device_id="device2",
        )

        d = postcard.to_dict()

        assert d["id"] == "test123"
        assert d["image_data"] == "abc123"
        assert d["width"] == 100
        assert d["height"] == 50
        assert d["caption"] == "Hello!"
        assert d["from_device_id"] == "device1"
        assert d["to_device_id"] == "device2"

    def test_postcard_from_dict(self):
        """Test Postcard deserialization."""
        from core.postcard import Postcard

        data = {
            "id": "test456",
            "image_data": "xyz789",
            "width": 80,
            "height": 40,
            "caption": "Test",
        }

        postcard = Postcard.from_dict(data)

        assert postcard.id == "test456"
        assert postcard.image_data == "xyz789"
        assert postcard.width == 80
        assert postcard.height == 40
        assert postcard.caption == "Test"


class TestPostcardCodec:
    """Tests for PostcardCodec encoding/decoding."""

    def test_encode_simple_image(self):
        """Test encoding a simple 1-bit image."""
        from core.postcard import PostcardCodec

        # Create a simple black and white image
        image = Image.new("1", (10, 10), 255)  # White
        image.putpixel((5, 5), 0)  # One black pixel

        data, width, height = PostcardCodec.encode_image(image)

        assert isinstance(data, str)
        assert width == 10
        assert height == 10
        assert len(data) > 0

    def test_encode_decode_roundtrip(self):
        """Test that encoding then decoding preserves the image."""
        from core.postcard import PostcardCodec

        # Create a test pattern
        original = Image.new("1", (20, 20), 255)
        for i in range(20):
            original.putpixel((i, i), 0)  # Diagonal line

        # Encode and decode
        data, width, height = PostcardCodec.encode_image(original)
        decoded = PostcardCodec.decode_image(data, width, height)

        # Compare pixels
        assert decoded.size == original.size
        for y in range(height):
            for x in range(width):
                assert decoded.getpixel((x, y)) == original.getpixel((x, y))

    def test_encode_resizes_large_image(self):
        """Test that oversized images are resized."""
        from core.postcard import PostcardCodec, MAX_WIDTH, MAX_HEIGHT

        # Create oversized image
        large_image = Image.new("1", (500, 300), 255)

        data, width, height = PostcardCodec.encode_image(large_image)

        assert width <= MAX_WIDTH
        assert height <= MAX_HEIGHT

    def test_encode_converts_color_to_1bit(self):
        """Test that color images are converted to 1-bit."""
        from core.postcard import PostcardCodec

        # Create RGB image
        color_image = Image.new("RGB", (10, 10), (128, 128, 128))

        data, width, height = PostcardCodec.encode_image(color_image)

        # Should succeed without error
        assert len(data) > 0

    def test_create_from_pixels(self):
        """Test creating postcard from pixel array."""
        from core.postcard import PostcardCodec

        # 5x5 checkerboard pattern
        pixels = [
            [0, 1, 0, 1, 0],
            [1, 0, 1, 0, 1],
            [0, 1, 0, 1, 0],
            [1, 0, 1, 0, 1],
            [0, 1, 0, 1, 0],
        ]

        data, width, height = PostcardCodec.create_from_pixels(pixels, 5, 5)

        assert width == 5
        assert height == 5
        assert len(data) > 0

        # Decode and verify
        decoded = PostcardCodec.decode_image(data, width, height)
        assert decoded.getpixel((0, 0)) == 0  # Black
        assert decoded.getpixel((1, 0)) == 255  # White


class TestPostcardCanvas:
    """Tests for PostcardCanvas drawing."""

    def test_canvas_creation(self, postcard_canvas):
        """Test canvas initialization."""
        assert postcard_canvas.width == 100
        assert postcard_canvas.height == 50
        assert postcard_canvas._image is not None

    def test_canvas_max_size(self):
        """Test that canvas enforces max size."""
        from core.postcard import PostcardCanvas, MAX_WIDTH, MAX_HEIGHT

        canvas = PostcardCanvas(width=500, height=300)

        assert canvas.width <= MAX_WIDTH
        assert canvas.height <= MAX_HEIGHT

    def test_clear(self, postcard_canvas):
        """Test clearing the canvas."""
        postcard_canvas.set_pixel(10, 10, 0)  # Draw something
        postcard_canvas.clear(255)  # Clear to white

        assert postcard_canvas.get_pixel(10, 10) == 255

    def test_clear_to_black(self, postcard_canvas):
        """Test clearing to black."""
        postcard_canvas.clear(0)

        assert postcard_canvas.get_pixel(10, 10) == 0

    def test_set_pixel(self, postcard_canvas):
        """Test setting individual pixels."""
        postcard_canvas.set_pixel(25, 25, 0)  # Black

        assert postcard_canvas.get_pixel(25, 25) == 0
        assert postcard_canvas.get_pixel(26, 25) == 255  # Unchanged

    def test_set_pixel_out_of_bounds(self, postcard_canvas):
        """Test that out-of-bounds pixels are ignored."""
        # Should not raise
        postcard_canvas.set_pixel(-1, -1, 0)
        postcard_canvas.set_pixel(1000, 1000, 0)

    def test_get_pixel_out_of_bounds(self, postcard_canvas):
        """Test getting pixel outside bounds."""
        assert postcard_canvas.get_pixel(-1, -1) == 255
        assert postcard_canvas.get_pixel(1000, 1000) == 255

    def test_draw_line(self, postcard_canvas):
        """Test drawing a line."""
        postcard_canvas.draw_line(0, 0, 10, 10, color=0)

        # Check diagonal pixels
        assert postcard_canvas.get_pixel(0, 0) == 0
        assert postcard_canvas.get_pixel(5, 5) == 0
        assert postcard_canvas.get_pixel(10, 10) == 0

    def test_draw_line_horizontal(self, postcard_canvas):
        """Test drawing a horizontal line."""
        postcard_canvas.draw_line(5, 10, 50, 10, color=0)

        for x in range(5, 51):
            assert postcard_canvas.get_pixel(x, 10) == 0

    def test_draw_rect_outline(self, postcard_canvas):
        """Test drawing a rectangle outline."""
        postcard_canvas.draw_rect(10, 10, 20, 15, color=0, fill=False)

        # Corners should be drawn
        assert postcard_canvas.get_pixel(10, 10) == 0  # Top-left
        assert postcard_canvas.get_pixel(29, 10) == 0  # Top-right
        assert postcard_canvas.get_pixel(10, 24) == 0  # Bottom-left
        assert postcard_canvas.get_pixel(29, 24) == 0  # Bottom-right

        # Interior should be empty
        assert postcard_canvas.get_pixel(15, 15) == 255

    def test_draw_rect_filled(self, postcard_canvas):
        """Test drawing a filled rectangle."""
        postcard_canvas.draw_rect(10, 10, 10, 10, color=0, fill=True)

        # Interior should be filled
        assert postcard_canvas.get_pixel(15, 15) == 0

    def test_draw_circle_outline(self, postcard_canvas):
        """Test drawing a circle outline."""
        postcard_canvas.draw_circle(50, 25, 10, color=0, fill=False)

        # Points on the circle should be drawn
        assert postcard_canvas.get_pixel(60, 25) == 0  # Right
        assert postcard_canvas.get_pixel(40, 25) == 0  # Left
        assert postcard_canvas.get_pixel(50, 15) == 0  # Top
        assert postcard_canvas.get_pixel(50, 35) == 0  # Bottom

        # Center should be empty
        assert postcard_canvas.get_pixel(50, 25) == 255

    def test_draw_circle_filled(self, postcard_canvas):
        """Test drawing a filled circle."""
        postcard_canvas.draw_circle(50, 25, 10, color=0, fill=True)

        # Center should be filled
        assert postcard_canvas.get_pixel(50, 25) == 0

    def test_draw_text(self, postcard_canvas):
        """Test drawing text."""
        postcard_canvas.draw_text(10, 10, "AB", color=0)

        # Something should be drawn (hard to test exact pixels)
        # Just verify no errors
        assert postcard_canvas.get_pixel(10, 10) is not None

    def test_to_postcard(self, postcard_canvas):
        """Test converting canvas to Postcard."""
        postcard_canvas.draw_rect(10, 10, 20, 20, color=0, fill=True)

        postcard = postcard_canvas.to_postcard(caption="Test")

        assert postcard.caption == "Test"
        assert postcard.width == postcard_canvas.width
        assert postcard.height == postcard_canvas.height
        assert len(postcard.image_data) > 0

    def test_get_image(self, postcard_canvas):
        """Test getting the underlying image."""
        postcard_canvas.set_pixel(5, 5, 0)

        image = postcard_canvas.get_image()

        assert image.size == (postcard_canvas.width, postcard_canvas.height)
        # Should be a copy
        postcard_canvas.set_pixel(5, 5, 255)
        assert image.getpixel((5, 5)) == 0  # Original unchanged

    def test_load_image(self, postcard_canvas):
        """Test loading an image into canvas."""
        new_image = Image.new("1", (50, 30), 0)  # Black
        new_image.putpixel((10, 10), 255)

        postcard_canvas.load_image(new_image)

        assert postcard_canvas.width == 50
        assert postcard_canvas.height == 30
        assert postcard_canvas.get_pixel(10, 10) == 255

    def test_load_image_converts_mode(self, postcard_canvas):
        """Test that loading RGB image converts to 1-bit."""
        rgb_image = Image.new("RGB", (40, 40), (255, 255, 255))

        postcard_canvas.load_image(rgb_image)

        assert postcard_canvas._image.mode == "1"


class TestSimpleFont:
    """Tests for the simple 5x7 bitmap font."""

    def test_font_has_letters(self):
        """Test that font has uppercase letters."""
        from core.postcard import _get_simple_font

        font = _get_simple_font()

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert letter in font, f"Missing letter: {letter}"

    def test_font_has_digits(self):
        """Test that font has digits."""
        from core.postcard import _get_simple_font

        font = _get_simple_font()

        for digit in "0123456789":
            assert digit in font, f"Missing digit: {digit}"

    def test_font_has_punctuation(self):
        """Test that font has basic punctuation."""
        from core.postcard import _get_simple_font

        font = _get_simple_font()

        for char in ".,!?-:":
            assert char in font, f"Missing punctuation: {char}"

    def test_font_character_format(self):
        """Test that each character has correct format."""
        from core.postcard import _get_simple_font

        font = _get_simple_font()

        for char, bitmap in font.items():
            assert len(bitmap) == 7, f"Character '{char}' should have 7 rows"
            for row in bitmap:
                assert 0 <= row <= 0b11111, f"Row in '{char}' exceeds 5 bits"
