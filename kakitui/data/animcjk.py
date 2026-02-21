"""animCJK SVG lookup by Unicode codepoint.

SVG files are stored under kakitui/data/assets/ in the standard animCJK
directory layout (svgsJa, svgsJaKana, svgsJaSpecial).
"""

from __future__ import annotations

from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"

_SEARCH_FOLDERS = ("svgsJa", "svgsJaKana", "svgsJaSpecial")


def get_svg_path(char: str) -> Path | None:
    """Find animCJK SVG by Unicode codepoint.

    Checks svgsJa first, then svgsJaKana, then svgsJaSpecial as a last resort.
    svgsJaSpecial contains split-stroke alternates already present in svgsJa,
    so it is only reached for characters absent from the other two folders.
    """
    codepoint = ord(char)
    for folder in _SEARCH_FOLDERS:
        p = _ASSETS_DIR / folder / f"{codepoint}.svg"
        if p.is_file():
            return p
    return None
