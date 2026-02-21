"""Generate per-stroke-step PNG frames from animCJK SVGs."""

from __future__ import annotations

import copy
import io
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

log = logging.getLogger(__name__)

DEFAULT_STROKE_COLOR = "#cdd6f4"
_GUIDE_COLOR = "#555555"

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)

_TAG_PATH = f"{{{_SVG_NS}}}path"
_TAG_STYLE = f"{{{_SVG_NS}}}style"
_TAG_DEFS = f"{{{_SVG_NS}}}defs"

# Inline style applied to median paths that should appear fully drawn.
# stroke-width/linecap match the animCJK CSS defaults.
_MEDIAN_DRAWN_STYLE = (
    "stroke-width:128;stroke-linecap:round;fill:none;stroke:{color};"
)


def _parse_animcjk_svg(
    svg_path: str | Path,
) -> tuple[ET.Element, list[ET.Element], list[ET.Element]]:
    """Parse an animCJK SVG.

    Returns (root, shape_paths, median_paths) where:
    - shape_paths: <path> elements with an ``id`` (stroke outlines, gray guide)
    - median_paths: <path> elements with a ``clip-path`` (animated center-lines)
    Both lists are in document order (stroke 1 first).
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    shape_paths: list[ET.Element] = []
    median_paths: list[ET.Element] = []

    for child in list(root):
        if child.tag == _TAG_STYLE:
            root.remove(child)
        elif child.tag == _TAG_PATH:
            if child.get("id"):
                shape_paths.append(child)
            elif child.get("clip-path"):
                median_paths.append(child)

    return root, shape_paths, median_paths


def animcjk_svg_to_frames(
    svg_path: str | Path,
    stroke_color: str | None = None,
) -> list["Image.Image"]:
    """Generate N cumulative stroke-step PNG frames from an animCJK SVG.

    Each frame shows:
    - All stroke outlines as a dim gray guide (the full character silhouette)
    - Strokes 1..k rendered via their median paths clipped to the stroke
      shapes, filled in stroke direction with the theme color

    Returns a list of Pillow Images (one per stroke step).
    """
    try:
        root, shape_paths, median_paths = _parse_animcjk_svg(svg_path)
    except Exception as e:
        log.warning("Failed to parse animCJK SVG %s: %s", svg_path, e)
        return []

    n = len(median_paths)
    if n == 0:
        log.warning("No median (stroke) paths found in %s", svg_path)
        return []

    color = stroke_color or DEFAULT_STROKE_COLOR
    drawn_style = _MEDIAN_DRAWN_STYLE.format(color=color)

    for sp in shape_paths:
        sp.set("fill", _GUIDE_COLOR)

    try:
        import cairosvg
        from PIL import Image as PILImage
    except Exception as e:
        log.warning("Missing dependency for SVG rendering: %s", e)
        return []

    frames: list["Image.Image"] = []

    for k in range(1, n + 1):
        frame_root = copy.deepcopy(root)

        median_idx = 0
        for child in frame_root:
            if child.tag != _TAG_PATH or not child.get("clip-path"):
                continue
            median_idx += 1
            if median_idx <= k:
                child.set("style", drawn_style)
                child.attrib.pop("pathLength", None)
            else:
                child.set("display", "none")

        svg_bytes = ET.tostring(frame_root, encoding="unicode").encode("utf-8")

        try:
            png_bytes = cairosvg.svg2png(bytestring=svg_bytes)
            img = PILImage.open(io.BytesIO(png_bytes)).copy()
            frames.append(img)
        except Exception as e:
            log.warning("Failed to render frame %d of %s: %s", k, svg_path, e)

    return frames
