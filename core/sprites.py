"""
Sprite management system for e-ink display animations.

Loads and caches 1-bit PNG sprites for Tamagotchi-style animations.
Supports mood-based sprite variants and multi-frame animations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    from PIL import Image
except ImportError:
    Image = None  # Graceful fallback if PIL not available

logger = logging.getLogger(__name__)


@dataclass
class AnimationState:
    """Track current animation state for sprite cycling."""

    action: str = "idle"           # Current action (idle, walk, dance, etc.)
    mood: str = "happy"            # Current mood from Personality
    frame_index: int = 0           # Current frame in animation
    frame_counter: int = 0         # Counter for frame timing
    frames_per_update: int = 3     # Display N refreshes per animation frame
    loop: bool = True              # Whether animation loops

    def update(self) -> bool:
        """
        Update animation state.

        Returns:
            True if frame changed, False otherwise
        """
        self.frame_counter += 1
        if self.frame_counter >= self.frames_per_update:
            self.frame_counter = 0
            self.frame_index += 1
            return True
        return False

    def set_action(self, action: str, mood: str, loop: bool = True):
        """Change to a new action/mood animation."""
        if self.action != action or self.mood != mood:
            self.action = action
            self.mood = mood
            self.frame_index = 0
            self.frame_counter = 0
            self.loop = loop
            logger.debug(f"Animation changed to {action}/{mood}")

    def reset(self):
        """Reset to idle animation."""
        self.set_action("idle", self.mood)


class SpriteManager:
    """
    Load and cache monochrome sprites for e-ink display with animation support.

    Sprites are 1-bit PNG images (pure black/white) optimized for e-ink displays.
    Supports mood-based sprite variants and multi-frame animations.
    """

    def __init__(self, sprite_dir: str = "assets/sprites", enabled: bool = True):
        """
        Initialize sprite manager.

        Args:
            sprite_dir: Path to sprite asset directory
            enabled: Whether sprite loading is enabled (fallback to text if False)
        """
        self._cache: Dict[str, Image.Image] = {}
        self._animation_cache: Dict[str, List[Image.Image]] = {}
        self._sprite_dir = Path(sprite_dir)
        self._enabled = enabled

        if not self._enabled:
            logger.info("Sprite system disabled - will use text fallback")
        elif not self._sprite_dir.exists():
            logger.warning(f"Sprite directory not found: {self._sprite_dir}")
            self._enabled = False
        else:
            logger.info(f"Sprite system initialized: {self._sprite_dir}")

    def is_enabled(self) -> bool:
        """Check if sprite system is enabled and available."""
        return self._enabled and Image is not None

    def load_sprite(self, path: Path) -> Optional[Image.Image]:
        """
        Load a single sprite image from disk.

        Args:
            path: Path to sprite PNG file

        Returns:
            PIL Image in 1-bit mode, or None if load failed
        """
        if not self.is_enabled():
            return None

        # Check cache first
        cache_key = str(path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load PNG file
        try:
            if not path.exists():
                logger.debug(f"Sprite not found: {path}")
                return None

            img = Image.open(path)

            # Convert to 1-bit if needed
            if img.mode != '1':
                logger.debug(f"Converting {path.name} from {img.mode} to 1-bit")
                img = img.convert('1')

            # Cache and return
            self._cache[cache_key] = img
            logger.debug(f"Loaded sprite: {path.name} ({img.size[0]}x{img.size[1]})")
            return img

        except Exception as e:
            logger.warning(f"Failed to load sprite {path}: {e}")
            return None

    def get_idle_sprite(self, mood: str) -> Optional[Image.Image]:
        """
        Get static idle sprite for a mood.

        Args:
            mood: Mood name (happy, sad, excited, etc.)

        Returns:
            PIL Image or None if not found
        """
        if not self.is_enabled():
            return None

        path = self._sprite_dir / "idle" / f"{mood}.png"
        return self.load_sprite(path)

    def load_animation(self, action: str, mood: str) -> List[Image.Image]:
        """
        Load all frames for an animated action+mood combination.

        Args:
            action: Action name (walk, dance, sleep, etc.)
            mood: Mood name (happy, sad, excited, etc.)

        Returns:
            List of PIL Images (frames), empty list if not found
        """
        if not self.is_enabled():
            return []

        cache_key = f"{action}_{mood}"
        if cache_key in self._animation_cache:
            return self._animation_cache[cache_key]

        # Try mood-specific animation first
        anim_dir = self._sprite_dir / action / mood
        if not anim_dir.exists():
            # Fallback: try mood-agnostic animation
            anim_dir = self._sprite_dir / action
            logger.debug(f"No {mood} variant for {action}, trying generic")

        frames = []
        if anim_dir.exists():
            # Load frame_01.png, frame_02.png, etc.
            frame_files = sorted(anim_dir.glob("frame_*.png"))
            for frame_file in frame_files:
                frame = self.load_sprite(frame_file)
                if frame:
                    frames.append(frame)

            if frames:
                logger.info(f"Loaded {len(frames)} frames for {action}/{mood}")

        # Cache even if empty (avoid repeated lookups)
        self._animation_cache[cache_key] = frames
        return frames

    def get_animation_frame(self, action: str, mood: str, frame_idx: int) -> Optional[Image.Image]:
        """
        Get specific frame from an animation.

        Args:
            action: Action name (walk, dance, sleep, etc.)
            mood: Mood name (happy, sad, excited, etc.)
            frame_idx: Frame index (wraps around if > frame count)

        Returns:
            PIL Image or None if animation not found
        """
        if not self.is_enabled():
            return None

        frames = self.load_animation(action, mood)
        if not frames:
            # Fallback to idle sprite
            if action != "idle":
                return self.get_idle_sprite(mood)
            return None

        # Loop frames
        return frames[frame_idx % len(frames)]

    def get_frame_count(self, action: str, mood: str) -> int:
        """
        Get total number of frames in an animation.

        Args:
            action: Action name (walk, dance, sleep, etc.)
            mood: Mood name (happy, sad, excited, etc.)

        Returns:
            Number of frames (0 if animation not found)
        """
        if not self.is_enabled():
            return 0

        frames = self.load_animation(action, mood)
        return len(frames)

    def clear_cache(self):
        """Clear all cached sprites (for memory management)."""
        self._cache.clear()
        self._animation_cache.clear()
        logger.info("Sprite cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with sprite_count and animation_count
        """
        return {
            "sprite_count": len(self._cache),
            "animation_count": len(self._animation_cache)
        }
