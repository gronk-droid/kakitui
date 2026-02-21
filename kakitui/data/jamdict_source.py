"""Data source backed by jamdict (JMdict + KANJIDIC2).

Provides word search via JMdict and kanji detail via KANJIDIC2.
Stroke image URLs are resolved from the local CSV's kname column.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache

from kakitui.data.models import (
    ExampleWord,
    KanjiDetail,
    KanjiResult,
    RadicalInfo,
    WordResult,
)

# ---------------------------------------------------------------------------
# Lazy singleton — jamdict DB is ~80 MB, only open once.
# ---------------------------------------------------------------------------

_jam = None


def _get_jam():
    global _jam  # noqa: PLW0603
    if _jam is None:
        from jamdict import Jamdict

        _jam = Jamdict()
    return _jam


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_cjk(char: str) -> bool:
    """Return True if the character is a CJK unified ideograph (kanji)."""
    try:
        return "CJK UNIFIED IDEOGRAPH" in unicodedata.name(char, "")
    except ValueError:
        return False


def _is_kana(char: str) -> bool:
    """Return True if the character is hiragana or katakana."""
    try:
        name = unicodedata.name(char, "")
    except ValueError:
        return False
    return "HIRAGANA" in name or "KATAKANA" in name


def extract_japanese_chars(text: str) -> list[str]:
    """Return unique kanji, hiragana, and katakana from *text*, in order.

    Kana are included so the navigation list is complete even before
    kana stroke data is available — the detail screen handles missing
    data gracefully.
    """
    seen: set[str] = set()
    result: list[str] = []
    for ch in text:
        if ch in seen:
            continue
        if _is_cjk(ch) or _is_kana(ch):
            seen.add(ch)
            result.append(ch)
    return result


@lru_cache(maxsize=1)
def _kname_map() -> dict[str, str]:
    """Build a kanji→kname mapping from the local CSV (needed for stroke URLs)."""
    from kakitui.data.local import _load_csv

    return {
        row["kanji"]: row["kname"]
        for row in _load_csv()
        if row.get("kanji") and row.get("kname")
    }


def _kname_for(kanji_char: str) -> str:
    return _kname_map().get(kanji_char, "")


# ---------------------------------------------------------------------------
# Word search (JMdict)
# ---------------------------------------------------------------------------


def search_words(query: str) -> list[WordResult]:
    """Search JMdict for words matching *query* (kanji, kana, or wildcard)."""
    jam = _get_jam()
    result = jam.lookup(query)
    words: list[WordResult] = []
    for entry in result.entries:
        text = entry.kanji_forms[0].text if entry.kanji_forms else ""
        reading = entry.kana_forms[0].text if entry.kana_forms else ""
        display_text = text or reading
        if not display_text:
            continue
        meanings: list[str] = []
        for sense in entry.senses:
            for gloss in sense.gloss:
                if gloss.text:
                    meanings.append(gloss.text)
        words.append(WordResult(text=display_text, reading=reading, meanings=meanings))
    return words


# ---------------------------------------------------------------------------
# Kanji search (KANJIDIC2 via jamdict)
# ---------------------------------------------------------------------------


def search_kanji(query: str) -> list[KanjiResult]:
    """Search KANJIDIC2 for kanji characters matching *query*."""
    jam = _get_jam()
    result = jam.lookup(query)
    results: list[KanjiResult] = []
    for char in result.chars:
        if not char.literal:
            continue
        rmg = char.rm_groups[0] if char.rm_groups else None
        eng = (
            [m.value for m in rmg.meanings if m.m_lang in ("", "eng")]
            if rmg
            else []
        )
        results.append(
            KanjiResult(
                kanji=char.literal,
                kname=_kname_for(char.literal),
                meaning=", ".join(eng),
                grade=char.grade or 0,
                strokes=char.stroke_count or 0,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Kanji detail (KANJIDIC2 text + CSV kname for stroke URLs)
# ---------------------------------------------------------------------------


def get_kanji_detail(kanji_char: str) -> KanjiDetail | None:
    """Return full detail for a single kanji character.

    Text data comes from KANJIDIC2 via jamdict.
    Stroke image URLs come from the local CSV's kname mapping.
    """
    jam = _get_jam()
    result = jam.lookup(kanji_char)

    char = None
    for c in result.chars:
        if c.literal == kanji_char:
            char = c
            break
    if char is None:
        return None

    rmg = char.rm_groups[0] if char.rm_groups else None

    eng_meanings = (
        [m.value for m in rmg.meanings if m.m_lang in ("", "eng")]
        if rmg
        else []
    )
    on_readings = [r.value for r in rmg.on_readings] if rmg else []
    kun_readings = [r.value for r in rmg.kun_readings] if rmg else []

    kname = _kname_for(kanji_char)
    strokes = char.stroke_count or 0

    # Build stroke image URLs from the kname (Kanji Alive assets)
    stroke_image_urls: list[str] = []
    if kname and strokes:
        from kakitui.data.local import stroke_diagram_url

        stroke_image_urls = [
            stroke_diagram_url(kname, i) for i in range(1, strokes + 1)
        ]

    # Build example words from JMdict entries in the same lookup result
    examples: list[ExampleWord] = []
    for entry in result.entries[:6]:
        jp = entry.kanji_forms[0].text if entry.kanji_forms else ""
        rd = entry.kana_forms[0].text if entry.kana_forms else ""
        display = f"{jp}（{rd}）" if jp and rd else (jp or rd)
        en_parts = [g.text for s in entry.senses[:1] for g in s.gloss]
        if display and en_parts:
            examples.append(ExampleWord(japanese=display, english=", ".join(en_parts)))

    # Audio URLs from kname (Kanji Alive)
    audio_urls: list[str] = []
    if kname:
        from kakitui.data.local import example_audio_url

        audio_urls = [example_audio_url(kname, i) for i in range(len(examples))]

    return KanjiDetail(
        kanji=kanji_char,
        kname=kname,
        meaning=", ".join(eng_meanings),
        grade=char.grade or 0,
        strokes=strokes,
        onyomi_ja=" ".join(on_readings),
        onyomi="",
        kunyomi_ja=" ".join(kun_readings),
        kunyomi="",
        examples=examples,
        radical=RadicalInfo(),
        stroke_image_urls=stroke_image_urls,
        audio_urls=audio_urls,
    )
