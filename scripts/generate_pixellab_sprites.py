#!/usr/bin/env python3
"""
Generate professional Tamagotchi-quality sprites using PixelLab MCP.

This script:
1. Generates 6 base character sprites (one per mood)
2. Generates animation frames using character animations
3. Downloads and converts all sprites to 1-bit PNG format
4. Saves sprites to the existing directory structure

Requires PixelLab MCP server to be available.

Usage:
    python scripts/generate_pixellab_sprites.py [--force]

Options:
    --force    Automatically backup and replace existing sprites without prompting
"""

import asyncio
import aiohttp
import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import io
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mcp_client import MCPClientManager


# Sprite generation configurations
SPRITE_SIZE = 48

# Base character descriptions for each mood
MOOD_DESCRIPTIONS = {
    "happy": "Cute chibi blob creature with big smile, cheerful round eyes, small antenna, friendly pose",
    "sad": "Cute chibi blob creature with downturned mouth, sad droopy eyes, small antenna, slumped posture",
    "excited": "Cute chibi blob creature with wide open eyes, big smile, small antenna, energetic bouncing pose",
    "curious": "Cute chibi blob creature with wide wondering eyes, small 'o' mouth, small antenna, tilted head",
    "sleepy": "Cute chibi blob creature with closed eyes, tiny mouth, small antenna, relaxed tired pose",
    "bored": "Cute chibi blob creature with half-closed eyes, flat line mouth, small antenna, slouched pose",
}

# Animation configurations
ANIMATIONS = {
    "walk": [
        ("happy", 4),    # mood, frame_count
        ("sad", 4),
        ("excited", 4),
    ],
    "dance": [
        ("happy", 6),
        ("excited", 6),
    ],
    "sleep": [
        ("sleepy", 3),
    ],
    "pet": [
        ("happy", 3),
        ("excited", 3),
    ],
    "exercise": [
        ("happy", 4),
    ],
}


class PixelLabSpriteGenerator:
    """Generates sprites using PixelLab MCP and converts them to 1-bit PNG."""

    def __init__(self, mcp_client: MCPClientManager, output_dir: Path):
        self.mcp_client = mcp_client
        self.output_dir = output_dir
        self.session = None
        self.total_sprites = 0
        self.generated_sprites = 0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def calculate_total_sprites(self) -> int:
        """Calculate total number of sprites to generate."""
        # 6 idle moods
        total = 6

        # All animation frames
        for action, configs in ANIMATIONS.items():
            for mood, frame_count in configs:
                total += frame_count

        return total

    async def create_character(self, mood: str, description: str) -> str:
        """Create a base character for a specific mood.

        Returns:
            character_id for use in animations
        """
        print(f"\n🎨 Generating {mood} character...")

        params = {
            "description": description,
            "size": SPRITE_SIZE,
            "proportions": "chibi",
            "shading": "basic",
            "outline": "single color black",
            "n_directions": 4,
            "detail": "medium",
        }

        # Call PixelLab MCP tool
        result = await self.mcp_client.call_tool(
            "mcp__pixellab__create_character",
            params
        )

        # Extract job_id from result
        job_id = result.get("job_id")
        if not job_id:
            raise ValueError(f"No job_id in create_character result: {result}")

        print(f"  ⏳ Job created: {job_id}")

        # Poll for completion
        character_data = await self.poll_job(job_id, "character")

        # Extract character_id
        character_id = character_data.get("character_id")
        if not character_id:
            raise ValueError(f"No character_id in result: {character_data}")

        print(f"  ✅ Character created: {character_id}")

        # Download and save idle sprite (front-facing direction)
        image_url = character_data.get("image_url")
        if image_url:
            await self.download_and_save_sprite(
                image_url,
                self.output_dir / "idle" / f"{mood}.png"
            )
            self.generated_sprites += 1
            print(f"  📥 Saved idle sprite ({self.generated_sprites}/{self.total_sprites})")

        return character_id

    async def animate_character(self, character_id: str, animation_type: str,
                               mood: str, frame_count: int) -> None:
        """Generate animation frames for a character.

        Args:
            character_id: ID from create_character
            animation_type: walk, dance, sleep, etc.
            mood: Character mood
            frame_count: Expected number of frames
        """
        print(f"\n🎬 Generating {animation_type} animation for {mood}...")

        params = {
            "character_id": character_id,
            "animation_type": animation_type,
            "n_frames": frame_count,
        }

        # Call PixelLab MCP tool
        result = await self.mcp_client.call_tool(
            "mcp__pixellab__animate_character",
            params
        )

        # Extract job_id
        job_id = result.get("job_id")
        if not job_id:
            raise ValueError(f"No job_id in animate_character result: {result}")

        print(f"  ⏳ Job created: {job_id}")

        # Poll for completion
        animation_data = await self.poll_job(job_id, "animation")

        # Download all frames
        frames = animation_data.get("frames", [])
        if not frames:
            print(f"  ⚠️  No frames returned for {animation_type}/{mood}")
            return

        print(f"  📥 Downloading {len(frames)} frames...")

        # Create output directory
        anim_dir = self.output_dir / animation_type / mood
        anim_dir.mkdir(parents=True, exist_ok=True)

        for i, frame_url in enumerate(frames):
            output_path = anim_dir / f"frame_{i:02d}.png"
            await self.download_and_save_sprite(frame_url, output_path)
            self.generated_sprites += 1
            print(f"    Frame {i+1}/{len(frames)} ({self.generated_sprites}/{self.total_sprites})")

        print(f"  ✅ Animation complete")

    async def poll_job(self, job_id: str, job_type: str,
                       poll_interval: int = 30, max_wait: int = 600) -> dict:
        """Poll PixelLab job until completion.

        Args:
            job_id: Job ID to poll
            job_type: 'character' or 'animation'
            poll_interval: Seconds between polls
            max_wait: Maximum wait time in seconds

        Returns:
            Job result data
        """
        tool_name = f"mcp__pixellab__get_{job_type}"
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")

            # Get job status
            result = await self.mcp_client.call_tool(
                tool_name,
                {f"{job_type}_id": job_id}
            )

            status = result.get("status")

            if status == "completed":
                return result
            elif status == "failed":
                error = result.get("error", "Unknown error")
                raise RuntimeError(f"Job {job_id} failed: {error}")
            elif status in ["pending", "processing"]:
                # Still working
                print(f"  ⏳ Status: {status} (waited {int(elapsed)}s)")
                await asyncio.sleep(poll_interval)
            else:
                raise ValueError(f"Unknown job status: {status}")

    async def download_and_save_sprite(self, url: str, output_path: Path) -> None:
        """Download sprite from URL and convert to 1-bit PNG.

        Args:
            url: Image URL from PixelLab
            output_path: Where to save converted sprite
        """
        # Download image
        async with self.session.get(url) as response:
            response.raise_for_status()
            image_data = await response.read()

        # Convert to 1-bit PNG
        self.convert_to_1bit(image_data, output_path)

    def convert_to_1bit(self, image_data: bytes, output_path: Path) -> None:
        """Convert color PNG to 1-bit PNG with Floyd-Steinberg dithering.

        Args:
            image_data: Raw image bytes
            output_path: Where to save converted image
        """
        # Open image
        img = Image.open(io.BytesIO(image_data))

        # Resize to exactly 48x48 (center crop if needed)
        if img.size != (SPRITE_SIZE, SPRITE_SIZE):
            # Calculate crop box for center crop
            width, height = img.size
            left = (width - SPRITE_SIZE) / 2
            top = (height - SPRITE_SIZE) / 2
            right = (width + SPRITE_SIZE) / 2
            bottom = (height + SPRITE_SIZE) / 2
            img = img.crop((left, top, right, bottom))

        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')

        # Apply Floyd-Steinberg dithering
        img = img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)

        # Ensure white background (invert if needed)
        # In 1-bit mode: 0 = black, 255 = white
        # We want black foreground on white background
        pixels = img.load()
        width, height = img.size

        # Check corner pixel to determine if inverted
        if pixels[0, 0] == 0:  # If top-left is black, likely inverted
            # Invert entire image
            img = Image.eval(img, lambda px: 255 - px)

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as 1-bit PNG
        img.save(output_path, 'PNG', optimize=True)

    async def generate_all_sprites(self) -> None:
        """Generate all sprites: idle moods and animations."""
        self.total_sprites = self.calculate_total_sprites()
        print(f"\n🚀 Starting sprite generation: {self.total_sprites} total sprites")
        print(f"   Output directory: {self.output_dir}")

        # Track character IDs for animations
        character_ids = {}

        # Phase 1: Generate base characters (6 idle moods)
        print("\n" + "="*60)
        print("PHASE 1: Base Characters (6 idle moods)")
        print("="*60)

        for mood, description in MOOD_DESCRIPTIONS.items():
            try:
                character_id = await self.create_character(mood, description)
                character_ids[mood] = character_id
            except Exception as e:
                print(f"  ❌ Failed to generate {mood}: {e}")
                # Continue with other moods

        # Phase 2-5: Generate animations
        phases = {
            2: ("walk", "Walk Animations"),
            3: ("dance", "Dance Animations"),
            4: ("sleep", "Sleep Animation"),
            5: ("pet + exercise", "Pet & Exercise Animations"),
        }

        for phase_num, (actions, title) in phases.items():
            print("\n" + "="*60)
            print(f"PHASE {phase_num}: {title}")
            print("="*60)

            # Handle multiple actions in phase 5
            action_list = actions.split(" + ")

            for action in action_list:
                if action not in ANIMATIONS:
                    continue

                for mood, frame_count in ANIMATIONS[action]:
                    # Check if we have the character ID
                    if mood not in character_ids:
                        print(f"\n⚠️  Skipping {action}/{mood}: character not generated")
                        continue

                    try:
                        await self.animate_character(
                            character_ids[mood],
                            action,
                            mood,
                            frame_count
                        )
                    except Exception as e:
                        print(f"  ❌ Failed to generate {action}/{mood}: {e}")
                        # Continue with other animations

        # Summary
        print("\n" + "="*60)
        print(f"✅ Generation complete: {self.generated_sprites}/{self.total_sprites} sprites")
        print("="*60)

        if self.generated_sprites < self.total_sprites:
            missing = self.total_sprites - self.generated_sprites
            print(f"\n⚠️  {missing} sprites were not generated (likely due to errors)")
            print("   Existing geometric placeholders will be used as fallback")


async def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate sprites using PixelLab MCP")
    parser.add_argument("--force", action="store_true",
                       help="Automatically backup and replace existing sprites")
    args = parser.parse_args()

    # Determine output directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    sprites_dir = project_dir / "assets" / "sprites"

    print("="*60)
    print("PixelLab Sprite Generator")
    print("="*60)

    # Check if sprites directory exists
    if sprites_dir.exists():
        print(f"\n⚠️  Sprites directory exists: {sprites_dir}")
        if not args.force:
            response = input("   Backup and replace? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        else:
            print("   Using --force flag, will backup and replace")

        # Create backup
        backup_dir = project_dir / "assets" / "sprites.backup"
        if backup_dir.exists():
            print(f"   Removing old backup: {backup_dir}")
            import shutil
            shutil.rmtree(backup_dir)

        print(f"   Creating backup: {backup_dir}")
        import shutil
        shutil.move(str(sprites_dir), str(backup_dir))

    # Create fresh sprites directory
    sprites_dir.mkdir(parents=True, exist_ok=True)

    # Initialize MCP client
    print("\n🔌 Connecting to PixelLab MCP server...")

    # Load config to get MCP settings
    import yaml
    config_path = project_dir / "config.yml"
    config_local_path = project_dir / "config.local.yml"

    # Load base config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Overlay local config if exists
    if config_local_path.exists():
        with open(config_local_path) as f:
            local_config = yaml.safe_load(f)
            if local_config:
                # Deep merge
                def deep_merge(base, override):
                    for key, value in override.items():
                        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                            deep_merge(base[key], value)
                        else:
                            base[key] = value
                deep_merge(config, local_config)

    # Initialize MCP client (pass just the mcp section of config)
    mcp_config = config.get("mcp", {})
    if not mcp_config.get("enabled", False):
        print("\n❌ MCP is disabled in config!")
        print("   Set mcp.enabled: true in config.yml")
        return

    mcp_client = MCPClientManager(mcp_config)
    await mcp_client.start_all()

    try:
        # Check if pixellab server is available
        all_tools = mcp_client.get_tools_for_ai()
        pixellab_tools = [t for t in all_tools if t.get("name", "").startswith("mcp__pixellab__")]

        if not pixellab_tools:
            print("\n❌ PixelLab MCP server not available!")
            print("   Make sure it's configured in config.yml:")
            print("   mcp:")
            print("     servers:")
            print("       pixellab:")
            print("         command: \"npx\"")
            print("         args: [\"-y\", \"@pixelheartai/mcp-server-pixellab\"]")
            return

        print(f"   ✅ Found {len(pixellab_tools)} PixelLab tools")

        # Generate sprites
        async with PixelLabSpriteGenerator(mcp_client, sprites_dir) as generator:
            await generator.generate_all_sprites()

        print("\n✅ All done! Run the test suite to verify:")
        print(f"   python {script_dir}/test_sprites.py")

    finally:
        await mcp_client.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
