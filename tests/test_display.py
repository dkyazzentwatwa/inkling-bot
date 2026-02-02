"""
Project Inkling - Display Tests

Tests for core/display.py - e-ink display management and rendering.
"""

import pytest
from PIL import Image


class TestDisplayType:
    """Tests for DisplayType enum."""

    def test_display_types(self):
        """Test display type values."""
        from core.display import DisplayType

        assert DisplayType.MOCK.value == "mock"
        assert DisplayType.V3.value == "v3"
        assert DisplayType.V4.value == "v4"


class TestFaces:
    """Tests for face expressions."""

    def test_ascii_faces_exist(self):
        """Test that all expected ASCII faces exist."""
        from core.display import FACES

        expected = [
            "happy", "excited", "grateful", "curious", "intense",
            "cool", "bored", "sad", "angry", "sleepy", "awake",
            "thinking", "confused", "surprised", "love", "wink",
            "debug", "default"
        ]

        for face in expected:
            assert face in FACES, f"Missing face: {face}"

    def test_unicode_faces_exist(self):
        """Test that Unicode faces exist."""
        from core.display import UNICODE_FACES

        expected = [
            "look_r", "look_l", "sleep", "awake", "bored",
            "intense", "cool", "happy", "excited", "grateful",
            "lonely", "sad", "friend", "debug"
        ]

        for face in expected:
            assert face in UNICODE_FACES, f"Missing Unicode face: {face}"


class TestMockDisplay:
    """Tests for MockDisplay driver."""

    def test_mock_display_init(self):
        """Test MockDisplay initialization."""
        from core.display import MockDisplay

        display = MockDisplay(width=250, height=122)
        display.init()

        assert display.width == 250
        assert display.height == 122
        assert display.supports_partial is True

    def test_mock_display_clear(self):
        """Test MockDisplay clear."""
        from core.display import MockDisplay

        display = MockDisplay()
        display.init()
        display.clear()

        assert display._current_image is not None
        assert display._current_image.size == (250, 122)

    def test_mock_display_display(self, capsys):
        """Test MockDisplay rendering."""
        from core.display import MockDisplay

        display = MockDisplay(width=50, height=20)
        display.init()

        # Create a simple test image
        image = Image.new("1", (50, 20), 255)
        display.display(image)

        assert display._current_image is not None

    def test_mock_display_partial(self):
        """Test MockDisplay partial refresh (same as full for mock)."""
        from core.display import MockDisplay

        display = MockDisplay()
        display.init()

        image = Image.new("1", (250, 122), 255)
        display.display_partial(image)

        assert display._current_image is not None


class TestDisplayManager:
    """Tests for DisplayManager."""

    def test_display_manager_init_mock(self):
        """Test DisplayManager initialization with mock display."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        assert dm.width == 250
        assert dm.height == 122
        assert dm._driver is not None

    def test_display_manager_auto_fallback(self):
        """Test DisplayManager auto-detection falls back to mock."""
        from core.display import DisplayManager, MockDisplay

        dm = DisplayManager(display_type="auto")
        dm.init()

        # Without hardware, should fall back to mock
        assert isinstance(dm._driver, MockDisplay)

    def test_render_frame_basic(self):
        """Test rendering a basic frame."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        image = dm.render_frame(face="happy", text="Hello!", status="OK")

        assert image is not None
        assert image.size == (250, 122)
        assert image.mode == "1"

    def test_render_frame_with_text_wrap(self):
        """Test rendering with long text that wraps."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        long_text = "This is a very long message that should be wrapped across multiple lines on the display"
        image = dm.render_frame(face="curious", text=long_text)

        assert image is not None
        assert image.size == (250, 122)

    def test_word_wrap(self):
        """Test word wrapping function."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        text = "Hello world this is a test"
        wrapped = dm._word_wrap(text, max_chars=12)

        assert len(wrapped) > 1
        for line in wrapped:
            assert len(line) <= 12

    def test_word_wrap_single_long_word(self):
        """Test word wrap with a single very long word."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        text = "Supercalifragilisticexpialidocious"
        wrapped = dm._word_wrap(text, max_chars=10)

        # Long word should be truncated
        assert len(wrapped) >= 1
        assert len(wrapped[0]) <= 10

    def test_rate_limiting(self):
        """Test display refresh rate limiting."""
        from core.display import DisplayManager
        import time

        dm = DisplayManager(display_type="mock", min_refresh_interval=0.1)
        dm.init()

        # First refresh should work
        assert dm._can_refresh() is True

        # Simulate a refresh
        dm._last_refresh = time.time()

        # Immediate second refresh should be blocked
        assert dm._can_refresh() is False

        # After interval, should be allowed again
        time.sleep(0.15)
        assert dm._can_refresh() is True

    def test_wait_for_refresh(self):
        """Test getting wait time for next refresh."""
        from core.display import DisplayManager
        import time

        dm = DisplayManager(display_type="mock", min_refresh_interval=1.0)
        dm.init()

        # Before any refresh, no wait needed
        dm._last_refresh = time.time() - 2.0
        wait = dm._wait_for_refresh()
        assert wait == 0

        # After recent refresh, should wait
        dm._last_refresh = time.time()
        wait = dm._wait_for_refresh()
        assert wait > 0
        assert wait <= 1.0

    def test_refresh_count(self):
        """Test refresh counter."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        assert dm.refresh_count == 0

    def test_clear(self):
        """Test clearing the display."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        # Should not raise
        dm.clear()

    def test_sleep(self):
        """Test putting display to sleep."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock")
        dm.init()

        # Should not raise
        dm.sleep()


class TestDisplayManagerAsync:
    """Async tests for DisplayManager."""

    @pytest.mark.asyncio
    async def test_update_async(self):
        """Test async display update."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock", min_refresh_interval=0.0)
        dm.init()

        result = await dm.update(face="happy", text="Hello!")
        assert result is True
        assert dm.refresh_count == 1

    @pytest.mark.asyncio
    async def test_update_rate_limited(self):
        """Test that async update respects rate limiting."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock", min_refresh_interval=10.0)
        dm.init()

        # First update
        result1 = await dm.update(face="happy", text="First")
        assert result1 is True

        # Second update should be rate limited
        result2 = await dm.update(face="sad", text="Second")
        assert result2 is False

    @pytest.mark.asyncio
    async def test_update_force_bypass(self):
        """Test forcing update to bypass rate limiting."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock", min_refresh_interval=10.0)
        dm.init()

        # First update
        await dm.update(face="happy", text="First")

        # Forced update should work
        result = await dm.update(face="sad", text="Forced", force=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_show_message_convenience(self):
        """Test show_message convenience method."""
        from core.display import DisplayManager

        dm = DisplayManager(display_type="mock", min_refresh_interval=0.0)
        dm.init()

        result = await dm.show_message("Test message", face="curious")
        assert result is True
