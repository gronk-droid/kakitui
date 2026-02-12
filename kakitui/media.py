"""Fetch SVG media and convert to PNG for in-app display."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from PIL import Image

log = logging.getLogger(__name__)


def fetch_svg_as_pillow(url_or_path: str) -> "Image.Image | None":
    """Load an SVG from a URL or local file path; return a Pillow Image (PNG), or None on failure."""
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

    try:
        import cairosvg
        from PIL import Image as PILImage

        png_bytes = cairosvg.svg2png(bytestring=svg_bytes)
        return PILImage.open(io.BytesIO(png_bytes)).copy()
    except Exception as e:
        log.warning("Failed to convert SVG to PNG: %s", e)
        return None


def fetch_stroke_images(urls: list[str]) -> list["Image.Image"]:
    """Fetch multiple SVG URLs and return list of Pillow Images (skips failures)."""
    result: list["Image.Image"] = []
    for url in urls:
        img = fetch_svg_as_pillow(url)
        if img is not None:
            result.append(img)
    return result
