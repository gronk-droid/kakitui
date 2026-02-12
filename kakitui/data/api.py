"""Kanji Alive API client.

Uses the public Kanji Alive API (via RapidAPI) when an API key is
configured.  Falls back to local CSV data when the key is absent or
on request failure.

Configuration (highest priority first):
    - Environment variable KANJI_ALIVE_API_KEY
    - Config file ~/.config/kakitui/config.ini section [kanji_alive] key api_key

See docs/KANJI_ALIVE_API.md for full endpoint documentation.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from kakitui.data.config import get_api_key
from kakitui.data.models import ExampleWord, KanjiDetail, KanjiResult, RadicalInfo

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAPIDAPI_HOST = "kanjialive-kanjialive.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}/api/public"


def _api_key() -> str | None:
    """Read the Kanji Alive RapidAPI key from config or environment."""
    return get_api_key()


def api_available() -> bool:
    """Return True if an API key is configured."""
    return bool(_api_key())


def _headers() -> dict[str, str]:
    key = _api_key()
    if not key:
        return {}
    return {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(path: str, params: dict[str, str] | None = None) -> Any:
    """Issue a GET request to the Kanji Alive API.

    Returns the parsed JSON, or None on failure.
    """
    url = f"{BASE_URL}/{path}"
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        log.warning("Kanji Alive API request failed: %s", exc)
        return None


def _parse_examples(raw: list[list[str]] | None) -> list[ExampleWord]:
    if not raw:
        return []
    return [
        ExampleWord(japanese=pair[0], english=pair[1])
        for pair in raw
        if isinstance(pair, list) and len(pair) >= 2
    ]


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def search_kanji(query: str) -> list[KanjiResult] | None:
    """Search for kanji via the Kanji Alive API.

    The API ``/search/{query}`` endpoint accepts kanji characters,
    kana, romaji readings, or English meanings.

    Returns a list of KanjiResult on success, or None if the API
    is unavailable / returned an error (caller should fall back to local).
    """
    if not api_available():
        return None

    data = _get(f"search/{requests.utils.quote(query)}")
    if data is None or not isinstance(data, list):
        return None

    results: list[KanjiResult] = []
    for item in data:
        kanji_info = item.get("kanji", {})
        char = kanji_info.get("character", "")
        if not char:
            continue
        results.append(
            KanjiResult(
                kanji=char,
                kname=kanji_info.get("kname", ""),
                meaning=kanji_info.get("meaning", {}).get("english", ""),
                grade=_safe_int(kanji_info.get("grade")),
                strokes=_safe_int(kanji_info.get("strokes", {}).get("count")),
            )
        )
    return results


def get_kanji_detail(character: str) -> KanjiDetail | None:
    """Get full kanji details from the Kanji Alive API.

    Uses ``/kanji/{character}`` to retrieve a single kanji's data
    including media URLs, readings, examples, radical, and hint.

    Returns KanjiDetail on success, or None on failure.
    """
    if not api_available():
        return None

    data = _get(f"kanji/{requests.utils.quote(character)}")
    if data is None or not isinstance(data, dict):
        return None

    kanji_info = data.get("kanji", {})
    radical_info = data.get("radical", {})
    examples_raw = data.get("examples", [])
    references = data.get("references", {})

    # Media
    stroke_url = ""
    stroke_urls: list[str] = []
    strokes_info = kanji_info.get("strokes", {})
    if isinstance(strokes_info, dict):
        images = strokes_info.get("images", [])
        if images and isinstance(images, list):
            stroke_urls = [u for u in images if isinstance(u, str) and u]
            stroke_url = stroke_urls[-1] if stroke_urls else ""

    # Examples with audio
    examples: list[ExampleWord] = []
    audio_urls: list[str] = []
    if isinstance(examples_raw, list):
        for ex in examples_raw:
            if isinstance(ex, dict):
                jp = ex.get("japanese", "")
                en = ex.get("meaning", {}).get("english", "") if isinstance(ex.get("meaning"), dict) else ""
                examples.append(ExampleWord(japanese=jp, english=en))
                audio_info = ex.get("audio", {})
                if isinstance(audio_info, dict):
                    audio_urls.append(audio_info.get("mp3", "") or "")
                else:
                    audio_urls.append("")

    return KanjiDetail(
        kanji=kanji_info.get("character", ""),
        kname=kanji_info.get("kname", ""),
        meaning=kanji_info.get("meaning", {}).get("english", "") if isinstance(kanji_info.get("meaning"), dict) else str(kanji_info.get("meaning", "")),
        grade=_safe_int(kanji_info.get("grade")),
        strokes=_safe_int(strokes_info.get("count") if isinstance(strokes_info, dict) else 0),
        kunyomi_ja=kanji_info.get("kunyomi", {}).get("hiragana", "") if isinstance(kanji_info.get("kunyomi"), dict) else "",
        kunyomi=kanji_info.get("kunyomi", {}).get("romaji", "") if isinstance(kanji_info.get("kunyomi"), dict) else "",
        onyomi_ja=kanji_info.get("onyomi", {}).get("katakana", "") if isinstance(kanji_info.get("onyomi"), dict) else "",
        onyomi=kanji_info.get("onyomi", {}).get("romaji", "") if isinstance(kanji_info.get("onyomi"), dict) else "",
        examples=examples,
        radical=RadicalInfo(
            character=radical_info.get("character", ""),
            order=_safe_int(radical_info.get("order")),
            strokes=_safe_int(radical_info.get("strokes")),
            name_ja=radical_info.get("name", {}).get("hiragana", "") if isinstance(radical_info.get("name"), dict) else "",
            name=radical_info.get("name", {}).get("romaji", "") if isinstance(radical_info.get("name"), dict) else "",
            meaning=radical_info.get("meaning", {}).get("english", "") if isinstance(radical_info.get("meaning"), dict) else "",
            position_ja=radical_info.get("position", {}).get("hiragana", "") if isinstance(radical_info.get("position"), dict) else "",
            position=radical_info.get("position", {}).get("romaji", "") if isinstance(radical_info.get("position"), dict) else "",
        ),
        hint=references.get("hint", "") or "",
        stroke_diagram_url=stroke_url,
        stroke_image_urls=stroke_urls,
        audio_urls=audio_urls,
    )
