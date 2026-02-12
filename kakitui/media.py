"""Fetch SVG media and convert to PNG for in-app display."""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from PIL import Image

log = logging.getLogger(__name__)

# Default stroke color for theme contrast (catppuccin text color)
DEFAULT_STROKE_COLOR = "#cdd6f4"


def _apply_stroke_color(svg_bytes: bytes, color_hex: str) -> bytes:
    """Replace black fill/stroke in SVG with theme color for contrast."""
    # Normalize to 6-char hex without leading #
    hex_only = color_hex.lstrip("#")
    if len(hex_only) == 6:
        color_attr = f"#{hex_only}"
    else:
        color_attr = DEFAULT_STROKE_COLOR
    try:
        text = svg_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return svg_bytes
    # Replace common black fill and stroke used in kanji stroke SVGs
    text = re.sub(r'fill="#000000"', f'fill="{color_attr}"', text, flags=re.IGNORECASE)
    text = re.sub(r'stroke="none"', f'stroke="{color_attr}"', text, flags=re.IGNORECASE)
    text = re.sub(r'fill="#000"(\s|>)', rf'fill="{color_attr}"\1', text, flags=re.IGNORECASE)
    return text.encode("utf-8")


def fetch_svg_as_pillow(
    url_or_path: str,
    stroke_color: str | None = None,
) -> "Image.Image | None":
    """Load an SVG from a URL or local file path; return a Pillow Image (PNG), or None on failure.

    If stroke_color is set (e.g. theme foreground hex like "#cdd6f4"), black fill/stroke
    in the SVG are replaced with that color for better contrast on the theme background.
    """
    path = Path(url_or_path)
    if path.is_file():
        try:
            svg_bytes = path.read_bytes()
        except OSError as e:
            log.warning("Failed to read %s: %s", url_or_path, e)
            return None
    elif url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        try:
            resp = requests.get(url_or_path, timeout=10)
            resp.raise_for_status()
            svg_bytes = resp.content
        except requests.RequestException as e:
            log.warning("Failed to fetch %s: %s", url_or_path, e)
            return None
    else:
        log.warning("Not a file or URL: %s", url_or_path)
        return None

    if stroke_color:
        svg_bytes = _apply_stroke_color(svg_bytes, stroke_color)

    try:
        import cairosvg
        from PIL import Image as PILImage

        png_bytes = cairosvg.svg2png(bytestring=svg_bytes)
        return PILImage.open(io.BytesIO(png_bytes)).copy()
    except Exception as e:
        log.warning("Failed to convert SVG to PNG: %s", e)
        return None


def fetch_stroke_images(
    urls: list[str],
    stroke_color: str | None = None,
) -> list["Image.Image"]:
    """Fetch multiple SVG URLs and return list of Pillow Images (skips failures).

    If stroke_color is set, stroke SVGs are recolored for theme contrast.
    """
    result: list["Image.Image"] = []
    for url in urls:
        img = fetch_svg_as_pillow(url, stroke_color=stroke_color)
        if img is not None:
            result.append(img)
    return result
