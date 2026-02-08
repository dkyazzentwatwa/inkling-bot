#!/usr/bin/env python3
"""
Test script for sprite system.

Verifies sprite loading, caching, and rendering pipeline.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sprites import SpriteManager, AnimationState
from core.ui import PwnagotchiUI, DisplayContext
from PIL import Image


def test_sprite_manager():
    """Test SpriteManager basic functionality."""
    print("Testing SpriteManager...")

    manager = SpriteManager(sprite_dir="assets/sprites", enabled=True)

    # Check if enabled
    assert manager.is_enabled(), "SpriteManager should be enabled"
    print("  ✓ SpriteManager enabled")

    # Test loading idle sprite
    happy_sprite = manager.get_idle_sprite("happy")
    assert happy_sprite is not None, "Should load happy idle sprite"
    assert happy_sprite.mode == "1", "Sprite should be 1-bit"
    assert happy_sprite.size == (48, 48), f"Sprite should be 48x48, got {happy_sprite.size}"
    print("  ✓ Loaded idle sprite (happy)")

    # Test loading animation frames
    walk_frames = manager.load_animation("walk", "happy")
    assert len(walk_frames) > 0, "Should load walk animation frames"
    assert len(walk_frames) == 4, f"Walk animation should have 4 frames, got {len(walk_frames)}"
    print(f"  ✓ Loaded walk animation ({len(walk_frames)} frames)")

    # Test frame access
    frame = manager.get_animation_frame("walk", "happy", 0)
    assert frame is not None, "Should get animation frame"
    print("  ✓ Retrieved animation frame")

    # Test frame count
    count = manager.get_frame_count("walk", "happy")
    assert count == 4, f"Should have 4 walk frames, got {count}"
    print(f"  ✓ Frame count correct ({count})")

    # Test cache stats
    stats = manager.get_cache_stats()
    print(f"  ✓ Cache stats: {stats['sprite_count']} sprites, {stats['animation_count']} animations")

    print("✓ SpriteManager tests passed!\n")


def test_animation_state():
    """Test AnimationState functionality."""
    print("Testing AnimationState...")

    state = AnimationState()

    # Check defaults
    assert state.action == "idle", "Default action should be idle"
    assert state.mood == "happy", "Default mood should be happy"
    assert state.frame_index == 0, "Default frame should be 0"
    print("  ✓ Default state correct")

    # Test set_action
    state.set_action("walk", "excited")
    assert state.action == "walk", "Action should be walk"
    assert state.mood == "excited", "Mood should be excited"
    assert state.frame_index == 0, "Frame should reset to 0"
    print("  ✓ Set action works")

    # Test update
    state.frames_per_update = 1  # Update every frame
    changed = state.update()
    assert changed, "Should advance frame"
    assert state.frame_index == 1, "Frame should advance to 1"
    print("  ✓ Frame advancement works")

    # Test reset
    state.reset()
    assert state.action == "idle", "Action should reset to idle"
    assert state.frame_index == 0, "Frame should reset to 0"
    print("  ✓ Reset works")

    print("✓ AnimationState tests passed!\n")


def test_ui_integration():
    """Test UI integration with sprites."""
    print("Testing UI integration...")

    manager = SpriteManager(sprite_dir="assets/sprites", enabled=True)
    ui = PwnagotchiUI(sprite_manager=manager)

    # Check UI components
    assert ui.face_sprite is not None, "UI should have FaceSprite"
    assert ui.face_sprite.sprite_manager == manager, "FaceSprite should have manager"
    print("  ✓ UI has FaceSprite component")

    # Test rendering with sprite
    ctx = DisplayContext(
        name="test",
        mood_text="Happy",
        message="Testing sprites!",
        animation_action="idle",
        mood_key="happy",
    )

    image = ui.render(ctx)
    assert image is not None, "Should render image"
    assert image.mode == "1", "Image should be 1-bit"
    assert image.size == (250, 122), f"Image should be 250x122, got {image.size}"
    print("  ✓ Rendered UI with sprite")

    # Save test image
    test_output = Path("test_sprite_render.png")
    image.save(test_output)
    print(f"  ✓ Saved test render to {test_output}")

    print("✓ UI integration tests passed!\n")


def test_sprite_fallback():
    """Test fallback to text when sprite not found."""
    print("Testing sprite fallback...")

    manager = SpriteManager(sprite_dir="assets/sprites", enabled=True)
    ui = PwnagotchiUI(sprite_manager=manager)

    # Try to render with non-existent sprite
    ctx = DisplayContext(
        name="test",
        mood_text="Unknown",
        message="Testing fallback",
        animation_action="nonexistent",
        mood_key="nonexistent",
        face_str="(^_^)",
    )

    image = ui.render(ctx)
    assert image is not None, "Should still render with fallback"
    print("  ✓ Fallback to text face works")

    print("✓ Sprite fallback tests passed!\n")


def test_disabled_sprites():
    """Test behavior when sprites are disabled."""
    print("Testing disabled sprites...")

    manager = SpriteManager(sprite_dir="assets/sprites", enabled=False)
    assert not manager.is_enabled(), "SpriteManager should be disabled"
    print("  ✓ SpriteManager disabled")

    # Should return None for sprites
    sprite = manager.get_idle_sprite("happy")
    assert sprite is None, "Should return None when disabled"
    print("  ✓ Returns None when disabled")

    # UI should still work with disabled sprites
    ui = PwnagotchiUI(sprite_manager=manager)
    ctx = DisplayContext(
        name="test",
        mood_text="Happy",
        message="No sprites",
        face_str="(^_^)",
    )

    image = ui.render(ctx)
    assert image is not None, "Should render without sprites"
    print("  ✓ UI works without sprites")

    print("✓ Disabled sprite tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Sprite System Tests")
    print("=" * 60 + "\n")

    try:
        test_sprite_manager()
        test_animation_state()
        test_ui_integration()
        test_sprite_fallback()
        test_disabled_sprites()

        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
