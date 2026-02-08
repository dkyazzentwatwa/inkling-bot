#!/usr/bin/env python3
"""
Project Inkling - E-Ink Image Converter

Convert images to 1-bit monochrome format optimized for Waveshare 2.13" e-ink
displays (250x122 pixels). Supports multiple dithering algorithms, batch
processing, and raw bitmap export for ESP32/MicroPython.

Usage:
    # Single file with Floyd-Steinberg dithering (default)
    python tools/eink_convert.py input.jpg -o output.png

    # Batch convert a directory with Atkinson dithering
    python tools/eink_convert.py images/ -o converted/ --dither atkinson

    # Boost contrast and invert for dark backgrounds
    python tools/eink_convert.py photo.png -o result.png --contrast 50 --invert

    # Fit image with letterboxing, export raw bitmap too
    python tools/eink_convert.py logo.png -o logo_eink.png --resize fit --raw

    # Preview before/after in terminal (no file write)
    python tools/eink_convert.py face.png --preview

    # Custom target size (e.g. 48x48 sprites)
    python tools/eink_convert.py sprite.png -o sprite_1bit.png --width 48 --height 48

Import for custom workflows:
    from tools.eink_convert import (
        load_image, resize_image, adjust_contrast,
        dither_floyd_steinberg, dither_atkinson, dither_ordered,
        dither_threshold, convert_to_eink, export_raw_bitmap,
    )
"""

import argparse
import logging
import struct
import sys
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EINK_WIDTH = 250
EINK_HEIGHT = 122

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}

# 4x4 Bayer matrix for ordered dithering, normalized to 0-1 range
BAYER_MATRIX_4X4 = (
    np.array(
        [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ],
        dtype=np.float64,
    )
    / 16.0
)

logger = logging.getLogger("eink_convert")

# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------


def load_image(path: str) -> Image.Image:
    """Load an image from *path* and return it as an RGB PIL Image.

    Handles RGBA by compositing onto a white background so transparency
    doesn't become black after grayscale conversion.
    """
    img = Image.open(path)

    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg

    return img.convert("RGB")


# ---------------------------------------------------------------------------
# Resizing
# ---------------------------------------------------------------------------


def resize_image(
    img: Image.Image,
    width: int = EINK_WIDTH,
    height: int = EINK_HEIGHT,
    mode: str = "fit",
) -> Image.Image:
    """Resize *img* to *width* x *height* using the given *mode*.

    Modes:
        crop    - Scale so the image fills the target, then center-crop.
        fit     - Scale to fit within the target, pad with white (letterbox).
        stretch - Stretch to exact target dimensions (distorts aspect ratio).
    """
    if mode == "stretch":
        return img.resize((width, height), Image.LANCZOS)

    src_w, src_h = img.size
    scale_w = width / src_w
    scale_h = height / src_h

    if mode == "crop":
        scale = max(scale_w, scale_h)
        new_w = round(src_w * scale)
        new_h = round(src_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        return img.crop((left, top, left + width, top + height))

    # fit (letterbox)
    scale = min(scale_w, scale_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    paste_x = (width - new_w) // 2
    paste_y = (height - new_h) // 2
    canvas.paste(img, (paste_x, paste_y))
    return canvas


# ---------------------------------------------------------------------------
# Contrast adjustment
# ---------------------------------------------------------------------------


def adjust_contrast(img: Image.Image, level: int = 0) -> Image.Image:
    """Boost contrast by *level* (0-100).

    0 = no change, 100 = maximum contrast boost (factor 3.0).
    Also applies auto-level (histogram stretch) at any level > 0.
    """
    if level <= 0:
        return img

    level = min(level, 100)

    # Auto-level: stretch histogram to full range
    img = ImageOps.autocontrast(img, cutoff=1)

    # Additional contrast boost: map 0-100 to enhancement factor 1.0-3.0
    factor = 1.0 + (level / 100.0) * 2.0
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(factor)


# ---------------------------------------------------------------------------
# Dithering algorithms
# ---------------------------------------------------------------------------


def _to_gray(img: Image.Image) -> np.ndarray:
    """Convert an RGB PIL Image to a float64 grayscale numpy array (0-255)."""
    return np.array(img.convert("L"), dtype=np.float64)


def dither_floyd_steinberg(img: Image.Image) -> Image.Image:
    """Floyd-Steinberg error-diffusion dithering.

    The classic dithering algorithm. Distributes quantization error to
    neighboring pixels with weights 7/16, 3/16, 5/16, 1/16.  Produces
    high-quality results for photographs and continuous-tone images.
    """
    gray = _to_gray(img)
    h, w = gray.shape

    for y in range(h):
        for x in range(w):
            old = gray[y, x]
            new = 255.0 if old >= 128.0 else 0.0
            gray[y, x] = new
            err = old - new

            if x + 1 < w:
                gray[y, x + 1] += err * 7.0 / 16.0
            if y + 1 < h:
                if x - 1 >= 0:
                    gray[y + 1, x - 1] += err * 3.0 / 16.0
                gray[y + 1, x] += err * 5.0 / 16.0
                if x + 1 < w:
                    gray[y + 1, x + 1] += err * 1.0 / 16.0

    return Image.fromarray((gray >= 128).astype(np.uint8) * 255, mode="L").convert("1")


def dither_atkinson(img: Image.Image) -> Image.Image:
    """Atkinson dithering (used by classic Macintosh).

    Distributes only 6/8 of the error, giving a lighter, higher-contrast
    look than Floyd-Steinberg.  Excellent for line art and text on e-ink.
    """
    gray = _to_gray(img)
    h, w = gray.shape

    for y in range(h):
        for x in range(w):
            old = gray[y, x]
            new = 255.0 if old >= 128.0 else 0.0
            gray[y, x] = new
            err = (old - new) / 8.0  # spread 1/8 to each of 6 neighbors

            if x + 1 < w:
                gray[y, x + 1] += err
            if x + 2 < w:
                gray[y, x + 2] += err
            if y + 1 < h:
                if x - 1 >= 0:
                    gray[y + 1, x - 1] += err
                gray[y + 1, x] += err
                if x + 1 < w:
                    gray[y + 1, x + 1] += err
            if y + 2 < h:
                gray[y + 2, x] += err

    return Image.fromarray((gray >= 128).astype(np.uint8) * 255, mode="L").convert("1")


def dither_ordered(img: Image.Image) -> Image.Image:
    """Ordered (Bayer 4x4) dithering.

    Applies a repeating threshold pattern. Produces a cross-hatch texture
    rather than the organic noise of error-diffusion methods.  Good for
    icons and stylized artwork.
    """
    gray = _to_gray(img)
    h, w = gray.shape

    # Tile the Bayer matrix across the image and scale to 0-255
    threshold = np.tile(BAYER_MATRIX_4X4, (h // 4 + 1, w // 4 + 1))[:h, :w] * 255.0

    result = (gray > threshold).astype(np.uint8) * 255
    return Image.fromarray(result, mode="L").convert("1")


def dither_threshold(img: Image.Image, cutoff: int = 128) -> Image.Image:
    """Simple binary threshold — no dithering.

    Pixels above *cutoff* become white, all others black.  Best for images
    that are already high-contrast (logos, text, line art).
    """
    gray = np.array(img.convert("L"), dtype=np.uint8)
    result = (gray >= cutoff).astype(np.uint8) * 255
    return Image.fromarray(result, mode="L").convert("1")


# Map of name -> dithering function
DITHER_METHODS = {
    "floyd-steinberg": dither_floyd_steinberg,
    "atkinson": dither_atkinson,
    "ordered": dither_ordered,
    "threshold": dither_threshold,
}


# ---------------------------------------------------------------------------
# High-level conversion
# ---------------------------------------------------------------------------


def convert_to_eink(
    img: Image.Image,
    width: int = EINK_WIDTH,
    height: int = EINK_HEIGHT,
    resize_mode: str = "fit",
    dither: str = "floyd-steinberg",
    contrast: int = 0,
    invert: bool = False,
) -> Image.Image:
    """Full pipeline: resize -> contrast -> dither -> optional invert.

    Parameters:
        img          Source PIL Image (any mode).
        width        Target width in pixels.
        height       Target height in pixels.
        resize_mode  One of "crop", "fit", "stretch".
        dither       Dithering algorithm name.
        contrast     Contrast boost 0-100.
        invert       Swap black and white after conversion.

    Returns:
        A 1-bit PIL Image ready for e-ink display.
    """
    # Ensure RGB
    if img.mode != "RGB":
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        else:
            img = img.convert("RGB")

    img = resize_image(img, width, height, resize_mode)
    img = adjust_contrast(img, contrast)

    dither_fn = DITHER_METHODS.get(dither)
    if dither_fn is None:
        raise ValueError(
            f"Unknown dither method '{dither}'. "
            f"Choose from: {', '.join(DITHER_METHODS)}"
        )
    result = dither_fn(img)

    if invert:
        result = ImageOps.invert(result.convert("L")).convert("1")

    return result


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def save_png(img: Image.Image, path: str) -> None:
    """Save a 1-bit image as an optimized PNG."""
    img.save(path, "PNG", optimize=True)
    logger.info("Saved PNG: %s (%dx%d)", path, img.width, img.height)


def export_raw_bitmap(img: Image.Image, path: str) -> None:
    """Export a 1-bit image as a raw packed-bit bitmap.

    Format: each byte packs 8 horizontal pixels, MSB first (left-most pixel
    is bit 7).  Rows are padded to byte boundaries.  A 4-byte little-endian
    header stores width and height.

    Compatible with common ESP32/MicroPython display libraries:
        import framebuf
        with open('image.bin', 'rb') as f:
            w = int.from_bytes(f.read(2), 'little')
            h = int.from_bytes(f.read(2), 'little')
            data = f.read()
        fb = framebuf.FrameBuffer(bytearray(data), w, h, framebuf.MONO_HLSB)
        display.blit(fb, 0, 0)
    """
    if img.mode != "1":
        img = img.convert("1")

    w, h = img.size
    pixels = np.array(img, dtype=np.uint8)  # 0=black, 255=white in mode "1"

    row_bytes = (w + 7) // 8
    buf = bytearray(row_bytes * h)

    for y in range(h):
        for x in range(w):
            if pixels[y, x]:  # white pixel = bit set
                byte_idx = y * row_bytes + x // 8
                bit_idx = 7 - (x % 8)
                buf[byte_idx] |= 1 << bit_idx

    with open(path, "wb") as f:
        f.write(struct.pack("<HH", w, h))
        f.write(buf)

    logger.info("Saved raw bitmap: %s (%d bytes, %dx%d)", path, len(buf) + 4, w, h)


def export_c_array(img: Image.Image, var_name: str = "image_data") -> str:
    """Return a C-style byte array string for embedding in firmware.

    Useful for including converted images directly in ESP32/Arduino code.

    Example output:
        const uint8_t image_data[] = {
            0xFF, 0x00, 0x3C, ...
        };
        const uint16_t image_width = 250;
        const uint16_t image_height = 122;
    """
    if img.mode != "1":
        img = img.convert("1")

    w, h = img.size
    pixels = np.array(img, dtype=np.uint8)

    row_bytes = (w + 7) // 8
    data_bytes: List[int] = []

    for y in range(h):
        for bx in range(row_bytes):
            byte_val = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < w and pixels[y, x]:
                    byte_val |= 1 << (7 - bit)
            data_bytes.append(byte_val)

    lines = []
    lines.append(f"const uint8_t {var_name}[] = {{")
    for i in range(0, len(data_bytes), 12):
        chunk = data_bytes[i : i + 12]
        lines.append("    " + ", ".join(f"0x{b:02X}" for b in chunk) + ",")
    lines.append("};")
    lines.append(f"const uint16_t {var_name}_width = {w};")
    lines.append(f"const uint16_t {var_name}_height = {h};")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Terminal preview (ASCII art)
# ---------------------------------------------------------------------------


def preview_ascii(img: Image.Image, max_width: int = 80) -> str:
    """Render a 1-bit image as ASCII art for terminal preview.

    Uses unicode half-blocks to get ~2:1 vertical compression so the image
    looks roughly proportional in a terminal.
    """
    if img.mode != "1":
        img = img.convert("1")

    # Scale to fit terminal width (each char = 1 pixel wide, 2 pixels tall)
    scale = min(1.0, max_width / img.width)
    w = max(1, round(img.width * scale))
    h = max(1, round(img.height * scale))
    # Make height even for half-block pairing
    if h % 2:
        h += 1

    img = img.resize((w, h), Image.NEAREST)
    pixels = np.array(img, dtype=np.uint8)

    lines = []
    for y in range(0, h, 2):
        row = []
        for x in range(w):
            top = bool(pixels[y, x]) if y < pixels.shape[0] else True
            bot = bool(pixels[y + 1, x]) if y + 1 < pixels.shape[0] else True
            # Using unicode half blocks: top-half and bottom-half
            if top and bot:
                row.append(" ")       # both white
            elif top and not bot:
                row.append("\u2584")  # bottom black -> lower half block
            elif not top and bot:
                row.append("\u2580")  # top black -> upper half block
            else:
                row.append("\u2588")  # both black -> full block
        lines.append("".join(row))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def find_images(path: Path) -> List[Path]:
    """Recursively find all supported image files under *path*."""
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [path]
        return []

    found = []
    for ext in SUPPORTED_EXTENSIONS:
        found.extend(path.rglob(f"*{ext}"))
    return sorted(found)


def batch_convert(
    input_path: Path,
    output_path: Path,
    width: int = EINK_WIDTH,
    height: int = EINK_HEIGHT,
    resize_mode: str = "fit",
    dither: str = "floyd-steinberg",
    contrast: int = 0,
    invert: bool = False,
    raw: bool = False,
) -> List[Path]:
    """Convert all images in *input_path* and write results to *output_path*.

    Returns list of output file paths created.
    """
    images = find_images(input_path)
    if not images:
        logger.warning("No supported images found in %s", input_path)
        return []

    output_path.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    for src in images:
        try:
            img = load_image(str(src))
            result = convert_to_eink(
                img,
                width=width,
                height=height,
                resize_mode=resize_mode,
                dither=dither,
                contrast=contrast,
                invert=invert,
            )

            # Preserve relative directory structure for recursive finds
            if input_path.is_dir():
                rel = src.relative_to(input_path)
                dest = output_path / rel.with_suffix(".png")
            else:
                dest = output_path / src.with_suffix(".png").name

            dest.parent.mkdir(parents=True, exist_ok=True)
            save_png(result, str(dest))
            created.append(dest)

            if raw:
                raw_dest = dest.with_suffix(".bin")
                export_raw_bitmap(result, str(raw_dest))
                created.append(raw_dest)

            logger.info("Converted: %s -> %s", src, dest)

        except Exception as exc:
            logger.error("Failed to convert %s: %s", src, exc)

    return created


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert images to 1-bit monochrome for e-ink displays.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s photo.jpg -o photo_eink.png
  %(prog)s photo.jpg -o photo_eink.png --dither atkinson --contrast 30
  %(prog)s images/ -o converted/ --dither ordered --resize crop
  %(prog)s face.png --preview
  %(prog)s sprite.png -o out.png --width 48 --height 48 --dither threshold
  %(prog)s logo.png -o logo.png --invert --raw
  %(prog)s artwork.png -o art.png --c-array art_bitmap
        """,
    )

    parser.add_argument(
        "input",
        help="Input image file or directory for batch processing.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file or directory. Required unless --preview is used.",
    )
    parser.add_argument(
        "--dither",
        choices=list(DITHER_METHODS.keys()),
        default="floyd-steinberg",
        help="Dithering algorithm (default: floyd-steinberg).",
    )
    parser.add_argument(
        "--contrast",
        type=int,
        default=0,
        metavar="0-100",
        help="Contrast boost level, 0=none, 100=maximum (default: 0).",
    )
    parser.add_argument(
        "--resize",
        choices=["crop", "fit", "stretch"],
        default="fit",
        help="Resize mode (default: fit with letterboxing).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=EINK_WIDTH,
        help=f"Target width in pixels (default: {EINK_WIDTH}).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=EINK_HEIGHT,
        help=f"Target height in pixels (default: {EINK_HEIGHT}).",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert colors (swap black and white).",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also export raw packed-bit bitmap (.bin) for ESP32/MicroPython.",
    )
    parser.add_argument(
        "--c-array",
        metavar="VAR_NAME",
        help="Print a C byte array to stdout (for embedding in firmware).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show ASCII art preview in terminal (no file output required).",
    )
    parser.add_argument(
        "--preview-width",
        type=int,
        default=80,
        help="Terminal width for ASCII preview (default: 80).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input not found: %s", args.input)
        return 1

    # Single-file mode
    if input_path.is_file():
        try:
            img = load_image(str(input_path))
        except Exception as exc:
            logger.error("Cannot open image: %s", exc)
            return 1

        result = convert_to_eink(
            img,
            width=args.width,
            height=args.height,
            resize_mode=args.resize,
            dither=args.dither,
            contrast=args.contrast,
            invert=args.invert,
        )

        if args.preview:
            print(preview_ascii(result, max_width=args.preview_width))
            print(
                f"\n[{result.width}x{result.height}, 1-bit, "
                f"dither={args.dither}, contrast={args.contrast}]"
            )

        if args.c_array:
            print(export_c_array(result, var_name=args.c_array))

        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            save_png(result, str(out))

            if args.raw:
                export_raw_bitmap(result, str(out.with_suffix(".bin")))

        if not args.output and not args.preview and not args.c_array:
            logger.error("No output specified. Use -o, --preview, or --c-array.")
            return 1

        return 0

    # Directory batch mode
    if not args.output:
        logger.error("Output directory required for batch processing (-o).")
        return 1

    created = batch_convert(
        input_path=input_path,
        output_path=Path(args.output),
        width=args.width,
        height=args.height,
        resize_mode=args.resize,
        dither=args.dither,
        contrast=args.contrast,
        invert=args.invert,
        raw=args.raw,
    )

    logger.info("Converted %d image(s).", len(created))
    return 0


if __name__ == "__main__":
    sys.exit(main())
