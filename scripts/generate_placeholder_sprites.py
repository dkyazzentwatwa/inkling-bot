#!/usr/bin/env python3
"""
Generate placeholder sprites for testing the sprite system.

These are simple geometric shapes in 1-bit PNG format (48x48 pixels).
They will be replaced with Tamagotchi-quality pixel art later.
"""

from PIL import Image, ImageDraw
from pathlib import Path


def create_placeholder_idle(mood: str, output_path: Path):
    """Create a simple idle sprite for a mood."""
    img = Image.new('1', (48, 48), 1)  # White background
    draw = ImageDraw.Draw(img)

    # Draw a simple face based on mood
    # Head outline (circle)
    draw.ellipse([8, 8, 40, 40], fill=0, outline=0)
    draw.ellipse([10, 10, 38, 38], fill=1, outline=0)  # Inner white

    # Eyes
    if mood in ("sleepy", "bored"):
        # Closed eyes (horizontal lines)
        draw.line([16, 20, 20, 20], fill=0, width=2)
        draw.line([28, 20, 32, 20], fill=0, width=2)
    elif mood == "excited":
        # Wide open eyes
        draw.ellipse([16, 18, 20, 22], fill=0)
        draw.ellipse([28, 18, 32, 22], fill=0)
        # Sparkles
        draw.point((17, 17), fill=0)
        draw.point((29, 17), fill=0)
    else:
        # Normal eyes (dots)
        draw.ellipse([17, 19, 19, 21], fill=0)
        draw.ellipse([29, 19, 31, 21], fill=0)

    # Mouth
    if mood in ("happy", "excited"):
        # Smile
        draw.arc([18, 22, 30, 32], 0, 180, fill=0, width=2)
    elif mood in ("sad", "bored"):
        # Frown
        draw.arc([18, 26, 30, 36], 180, 360, fill=0, width=2)
    elif mood == "curious":
        # Small "o" mouth
        draw.ellipse([22, 28, 26, 32], fill=0)
        draw.ellipse([23, 29, 25, 31], fill=1)  # Inner white
    else:
        # Neutral line
        draw.line([20, 28, 28, 28], fill=0, width=2)

    img.save(output_path)
    print(f"Created: {output_path}")


def create_placeholder_animation(action: str, mood: str, frame: int, output_path: Path):
    """Create a simple animation frame."""
    img = Image.new('1', (48, 48), 1)  # White background
    draw = ImageDraw.Draw(img)

    if action == "walk":
        # Simple walking animation (body moves up/down, legs move)
        offset_y = 2 if frame % 2 == 0 else 0

        # Head
        draw.ellipse([14, 4 + offset_y, 34, 24 + offset_y], fill=0, outline=0)
        draw.ellipse([16, 6 + offset_y, 32, 22 + offset_y], fill=1, outline=0)

        # Eyes
        draw.ellipse([19, 12 + offset_y, 21, 14 + offset_y], fill=0)
        draw.ellipse([27, 12 + offset_y, 29, 14 + offset_y], fill=0)

        # Mouth (mood dependent)
        if mood == "happy":
            draw.arc([20, 14 + offset_y, 28, 20 + offset_y], 0, 180, fill=0, width=2)
        elif mood == "sad":
            draw.arc([20, 16 + offset_y, 28, 22 + offset_y], 180, 360, fill=0, width=2)

        # Body
        draw.rectangle([18, 24 + offset_y, 30, 34 + offset_y], fill=0, outline=0)
        draw.rectangle([20, 26 + offset_y, 28, 32 + offset_y], fill=1, outline=0)

        # Legs (alternate)
        if frame % 4 < 2:
            # Left leg forward, right leg back
            draw.rectangle([18, 34 + offset_y, 22, 44], fill=0)
            draw.rectangle([28, 34 + offset_y, 32, 40], fill=0)
        else:
            # Right leg forward, left leg back
            draw.rectangle([18, 34 + offset_y, 22, 40], fill=0)
            draw.rectangle([28, 34 + offset_y, 32, 44], fill=0)

    elif action == "dance":
        # Dancing animation (body tilts, arms move)
        tilt = 4 if frame % 2 == 0 else -4

        # Head (tilted)
        center_x = 24 + tilt // 2
        draw.ellipse([center_x - 8, 6, center_x + 8, 22], fill=0, outline=0)
        draw.ellipse([center_x - 6, 8, center_x + 6, 20], fill=1, outline=0)

        # Eyes
        draw.ellipse([center_x - 4, 12, center_x - 2, 14], fill=0)
        draw.ellipse([center_x + 2, 12, center_x + 4, 14], fill=0)

        # Happy mouth
        draw.arc([center_x - 4, 14, center_x + 4, 18], 0, 180, fill=0, width=2)

        # Body
        draw.rectangle([center_x - 6, 22, center_x + 6, 36], fill=0, outline=0)
        draw.rectangle([center_x - 4, 24, center_x + 4, 34], fill=1, outline=0)

        # Arms (raised)
        if frame % 4 < 2:
            draw.rectangle([center_x - 10, 24, center_x - 6, 30], fill=0)
            draw.rectangle([center_x + 6, 24, center_x + 10, 30], fill=0)
        else:
            draw.rectangle([center_x - 10, 26, center_x - 6, 32], fill=0)
            draw.rectangle([center_x + 6, 26, center_x + 10, 32], fill=0)

        # Legs
        draw.rectangle([center_x - 6, 36, center_x - 2, 44], fill=0)
        draw.rectangle([center_x + 2, 36, center_x + 6, 44], fill=0)

    elif action == "sleep":
        # Sleeping animation (gentle breathing)
        scale = 0.9 + (frame * 0.05)  # Subtle size change for breathing

        # Head (larger for sleep)
        w = int(20 * scale)
        h = int(16 * scale)
        x_center = 24
        y_center = 20
        draw.ellipse([x_center - w, y_center - h, x_center + w, y_center + h], fill=0, outline=0)
        draw.ellipse([x_center - w + 2, y_center - h + 2, x_center + w - 2, y_center + h - 2], fill=1, outline=0)

        # Closed eyes
        draw.line([16, 18, 22, 18], fill=0, width=2)
        draw.line([26, 18, 32, 18], fill=0, width=2)

        # Sleeping mouth
        draw.ellipse([22, 24, 26, 26], fill=0)

        # Body (curled up)
        draw.ellipse([10, 28, 38, 44], fill=0, outline=0)
        draw.ellipse([12, 30, 36, 42], fill=1, outline=0)

        # "zzZ" text
        if frame == 2:
            draw.text((36, 10), "z", fill=0)

    elif action == "pet":
        # Being petted reaction (happy bounce)
        bounce = -2 if frame % 2 == 0 else 0

        # Head
        draw.ellipse([12, 8 + bounce, 36, 32 + bounce], fill=0, outline=0)
        draw.ellipse([14, 10 + bounce, 34, 30 + bounce], fill=1, outline=0)

        # Happy eyes (closed)
        draw.arc([17, 16 + bounce, 21, 20 + bounce], 180, 360, fill=0, width=2)
        draw.arc([27, 16 + bounce, 31, 20 + bounce], 180, 360, fill=0, width=2)

        # Big smile
        draw.arc([18, 20 + bounce, 30, 28 + bounce], 0, 180, fill=0, width=2)

        # Body
        draw.rectangle([16, 32 + bounce, 32, 42], fill=0, outline=0)
        draw.rectangle([18, 34 + bounce, 30, 40], fill=1, outline=0)

        # Heart if frame 1
        if frame == 1:
            draw.text((36, 8 + bounce), "♥", fill=0)

    elif action == "exercise":
        # Exercise animation (jumping jacks)
        if frame % 2 == 0:
            # Arms down
            arms_y = 28
            legs_spread = 0
        else:
            # Arms up
            arms_y = 20
            legs_spread = 4

        # Head
        draw.ellipse([16, 8, 32, 24], fill=0, outline=0)
        draw.ellipse([18, 10, 30, 22], fill=1, outline=0)

        # Eyes
        draw.ellipse([20, 14, 22, 16], fill=0)
        draw.ellipse([26, 14, 28, 16], fill=0)

        # Mouth
        draw.ellipse([22, 18, 26, 20], fill=0)

        # Body
        draw.rectangle([20, 24, 28, 34], fill=0, outline=0)
        draw.rectangle([22, 26, 26, 32], fill=1, outline=0)

        # Arms
        draw.rectangle([14, arms_y, 18, arms_y + 6], fill=0)
        draw.rectangle([30, arms_y, 34, arms_y + 6], fill=0)

        # Legs
        draw.rectangle([18 - legs_spread, 34, 22 - legs_spread, 44], fill=0)
        draw.rectangle([26 + legs_spread, 34, 30 + legs_spread, 44], fill=0)

    img.save(output_path)
    print(f"Created: {output_path}")


def main():
    """Generate all placeholder sprites."""
    base_dir = Path("assets/sprites")

    # Moods for idle sprites
    moods = ["happy", "sad", "excited", "curious", "sleepy", "bored"]

    # Create idle sprites
    print("\nGenerating idle sprites...")
    idle_dir = base_dir / "idle"
    idle_dir.mkdir(parents=True, exist_ok=True)
    for mood in moods:
        create_placeholder_idle(mood, idle_dir / f"{mood}.png")

    # Create walk animations
    print("\nGenerating walk animations...")
    for mood in ["happy", "sad", "excited"]:
        walk_dir = base_dir / "walk" / mood
        walk_dir.mkdir(parents=True, exist_ok=True)
        for i in range(4):
            create_placeholder_animation("walk", mood, i, walk_dir / f"frame_{i+1:02d}.png")

    # Create dance animations
    print("\nGenerating dance animations...")
    for mood in ["happy", "excited"]:
        dance_dir = base_dir / "dance" / mood
        dance_dir.mkdir(parents=True, exist_ok=True)
        for i in range(6):
            create_placeholder_animation("dance", mood, i, dance_dir / f"frame_{i+1:02d}.png")

    # Create sleep animation
    print("\nGenerating sleep animation...")
    sleep_dir = base_dir / "sleep"
    sleep_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        create_placeholder_animation("sleep", "sleepy", i, sleep_dir / f"frame_{i+1:02d}.png")

    # Create pet reaction
    print("\nGenerating pet reaction...")
    for mood in ["happy", "excited"]:
        pet_dir = base_dir / "pet" / mood
        pet_dir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            create_placeholder_animation("pet", mood, i, pet_dir / f"frame_{i+1:02d}.png")

    # Create exercise animation
    print("\nGenerating exercise animation...")
    exercise_dir = base_dir / "exercise"
    exercise_dir.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        create_placeholder_animation("exercise", "happy", i, exercise_dir / f"frame_{i+1:02d}.png")

    print("\n✓ All placeholder sprites generated!")
    print(f"Total sprites created: {len(list(base_dir.rglob('*.png')))}")


if __name__ == "__main__":
    main()
