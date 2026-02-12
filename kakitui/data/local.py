"""Local CSV-based data source for kanji lookup.

Uses ka_data.csv from kanjialive/kanji-data-media and constructs media
URLs from the kname (romanized filename) column.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from kakitui.data.models import ExampleWord, KanjiDetail, KanjiResult, RadicalInfo

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Local assets (unzipped kanji_strokes from kanji-data-media)
# ---------------------------------------------------------------------------

_ASSETS_STROKES_DIR = Path(__file__).resolve().parent / "assets" / "kanji_strokes"


def _stroke_local_path(kname: str, stroke_num: int) -> Path | None:
    """Return path to local stroke SVG if it exists. Filenames: {kname}_{n}.svg (no zero-pad)."""
    if not kname:
        return None
    path = _ASSETS_STROKES_DIR / f"{kname}_{stroke_num}.svg"
    return path if path.is_file() else None


# ---------------------------------------------------------------------------
# Media URL / path helpers
# ---------------------------------------------------------------------------

_MEDIA_BASE = "https://media.kanjialive.com"


def _media_safe_kname(kname: str) -> str:
    """Convert kname for remote media.kanjialive.com (parentheses -> hyphen, then encode)."""
    normalized = re.sub(r"\(([^)]*)\)", r"-\1", kname)
    return quote(normalized, safe="-._~")


def stroke_diagram_path_or_url(kname: str, stroke_num: int) -> str:
    """Local path (if assets exist) or remote URL for one stroke SVG."""
    local = _stroke_local_path(kname, stroke_num)
    if local is not None:
        return str(local.resolve())
    safe = _media_safe_kname(kname)
    return f"{_MEDIA_BASE}/kanji_strokes/{safe}_{stroke_num:05d}.svg"


def stroke_diagram_url(kname: str, stroke_num: int) -> str:
    """Build stroke-order SVG path or URL. Prefers local assets when present."""
    return stroke_diagram_path_or_url(kname, stroke_num)


def example_audio_url(kname: str, index: int) -> str:
    """Build an example audio URL.

    Example audio files are named: {kname}_06_{letter}.mp3
    where letter goes a, b, c, ... matching the example order.
    """
    safe = _media_safe_kname(kname)
    letter = chr(ord("a") + index)
    return f"{_MEDIA_BASE}/examples_audio/{safe}_06_{letter}.mp3"


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

_KANJI_DATA: list[dict[str, str]] | None = None


def _load_csv() -> list[dict[str, str]]:
    """Load and cache the ka_data.csv rows."""
    global _KANJI_DATA  # noqa: PLW0603
    if _KANJI_DATA is not None:
        return _KANJI_DATA

    csv_ref = resources.files("kakitui.data").joinpath("ka_data.csv")
    with resources.as_file(csv_ref) as csv_path:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            _KANJI_DATA = list(reader)
    return _KANJI_DATA


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _parse_examples(raw: str) -> list[ExampleWord]:
    """Parse the JSON-ish examples column from ka_data.csv."""
    if not raw or raw.strip() == "":
        return []
    try:
        parsed = json.loads(raw)
        return [
            ExampleWord(japanese=pair[0], english=pair[1])
            for pair in parsed
            if isinstance(pair, list) and len(pair) >= 2
        ]
    except (json.JSONDecodeError, IndexError, TypeError):
        return []


def _row_to_result(row: dict[str, str]) -> KanjiResult:
    """Convert a CSV row to a lightweight KanjiResult."""
    return KanjiResult(
        kanji=row.get("kanji", ""),
        kname=row.get("kname", ""),
        meaning=row.get("kmeaning", ""),
        grade=_safe_int(row.get("kgrade", "")),
        strokes=_safe_int(row.get("kstroke", "")),
    )


def _row_to_detail(row: dict[str, str]) -> KanjiDetail:
    """Convert a CSV row to a full KanjiDetail."""
    kname = row.get("kname", "")
    examples = _parse_examples(row.get("examples", ""))
    strokes = _safe_int(row.get("kstroke", ""))

    return KanjiDetail(
        kanji=row.get("kanji", ""),
        kname=kname,
        meaning=row.get("kmeaning", ""),
        grade=_safe_int(row.get("kgrade", "")),
        strokes=strokes,
        kunyomi_ja=row.get("kunyomi_ja", ""),
        kunyomi=row.get("kunyomi", ""),
        onyomi_ja=row.get("onyomi_ja", ""),
        onyomi=row.get("onyomi", ""),
        examples=examples,
        radical=RadicalInfo(
            character=row.get("radical", ""),
            order=_safe_int(row.get("rad_order", "")),
            strokes=_safe_int(row.get("rad_stroke", "")),
            name_ja=row.get("rad_name_ja", ""),
            name=row.get("rad_name", ""),
            meaning=row.get("rad_meaning", ""),
            position_ja=row.get("rad_position_ja", ""),
            position=row.get("rad_position", ""),
        ),
        stroke_diagram_url=stroke_diagram_url(kname, strokes) if strokes else "",
        stroke_image_urls=[
            stroke_diagram_url(kname, i) for i in range(1, strokes + 1)
        ]
        if strokes
        else [],
        audio_urls=[example_audio_url(kname, i) for i in range(len(examples))],
    )


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

_ROMAJI_CLEAN_RE = re.compile(r"[^a-z]")


def _normalize_romaji(text: str) -> str:
    """Lowercase and strip non-alpha for romaji comparison."""
    return _ROMAJI_CLEAN_RE.sub("", text.lower())


def _is_japanese(char: str) -> bool:
    """Check if a character is CJK, Hiragana, or Katakana."""
    try:
        name = unicodedata.name(char, "")
    except ValueError:
        return False
    return any(
        kw in name
        for kw in ("CJK", "HIRAGANA", "KATAKANA", "KANGXI", "RADICAL")
    )


def _query_is_japanese(query: str) -> bool:
    """Return True if the query contains Japanese characters."""
    return any(_is_japanese(c) for c in query)


# ---------------------------------------------------------------------------
# Public search / detail functions
# ---------------------------------------------------------------------------


def search_kanji(query: str) -> list[KanjiResult]:
    """Search the local CSV for kanji matching the query.

    Supports:
    - Kanji character (exact match on 'kanji' column)
    - Hiragana/Katakana (substring match on kunyomi_ja / onyomi_ja)
    - Romaji (substring match on kunyomi / onyomi / kname)
    - English meaning (substring match on kmeaning)
    """
    data = _load_csv()
    query = query.strip()
    if not query:
        return []

    results: list[KanjiResult] = []

    if _query_is_japanese(query):
        # Japanese query: match kanji, kunyomi_ja, onyomi_ja
        for row in data:
            if query == row.get("kanji", ""):
                results.append(_row_to_result(row))
            elif query in row.get("kunyomi_ja", "") or query in row.get("onyomi_ja", ""):
                results.append(_row_to_result(row))
    else:
        # Romaji / English query
        q_norm = _normalize_romaji(query)
        q_lower = query.strip().lower()
        for row in data:
            kname_norm = _normalize_romaji(row.get("kname", ""))
            kun_norm = _normalize_romaji(row.get("kunyomi", ""))
            on_norm = _normalize_romaji(row.get("onyomi", ""))
            meaning_lower = row.get("kmeaning", "").lower()

            if (
                q_norm in kname_norm
                or q_norm in kun_norm
                or q_norm in on_norm
                or q_lower in meaning_lower
            ):
                results.append(_row_to_result(row))

    return results


def get_kanji_detail(kanji_char: str) -> KanjiDetail | None:
    """Get full details for a kanji character from local CSV."""
    data = _load_csv()
    for row in data:
        if row.get("kanji", "") == kanji_char:
            return _row_to_detail(row)
    return None


def get_kanji_detail_by_kname(kname: str) -> KanjiDetail | None:
    """Get full details by kname (romanized filename)."""
    data = _load_csv()
    for row in data:
        if row.get("kname", "") == kname:
            return _row_to_detail(row)
    return None
