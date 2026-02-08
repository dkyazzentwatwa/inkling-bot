#!/usr/bin/env python3
"""
Download sprites from PixelLab URLs and convert to 1-bit PNG.
"""

import requests
from PIL import Image
from pathlib import Path
import io
import sys


def download_and_convert_sprite(url: str, output_path: Path, size: int = 48) -> None:
    """Download sprite from URL and convert to 1-bit PNG.

    Args:
        url: Image URL from PixelLab
        output_path: Where to save converted sprite
        size: Expected sprite size (default 48x48)
    """
    print(f"Downloading: {url}")

    # Download image
    response = requests.get(url)
    response.raise_for_status()

    # Open image
    img = Image.open(io.BytesIO(response.content))

    # Resize to exactly 48x48 if needed (center crop)
    if img.size != (size, size):
        width, height = img.size
        left = (width - size) / 2
        top = (height - size) / 2
        right = (width + size) / 2
        bottom = (height + size) / 2
        img = img.crop((left, top, right, bottom))

    # Convert to grayscale
    if img.mode != 'L':
        img = img.convert('L')

    # Apply Floyd-Steinberg dithering
    img = img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)

    # Check if we need to invert (ensure white background)
    pixels = img.load()
    width, height = img.size

    # Sample corners to determine if inverted
    corners = [
        pixels[0, 0],
        pixels[width-1, 0],
        pixels[0, height-1],
        pixels[width-1, height-1]
    ]

    # If most corners are black, likely inverted
    if sum(1 for c in corners if c == 0) >= 3:
        img = Image.eval(img, lambda px: 255 - px)

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as 1-bit PNG
    img.save(output_path, 'PNG', optimize=True)
    print(f"Saved: {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python download_pixellab_sprites.py <url> <output_path>")
        sys.exit(1)

    url = sys.argv[1]
    output_path = Path(sys.argv[2])

    download_and_convert_sprite(url, output_path)
