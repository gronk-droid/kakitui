"""Unified data source: jamdict for text data, animCJK for stroke SVGs."""

from __future__ import annotations

from kakitui.data import animcjk
from kakitui.data.models import KanjiDetail, KanjiResult, WordResult


def search(query: str) -> tuple[list[KanjiResult], list[WordResult]]:
    """Search for both kanji and words in a single call.

    Returns (kanji_results, word_results) from jamdict (KANJIDIC2 + JMdict).
    """
    from kakitui.data import jamdict_source

    kanji_results = jamdict_source.search_kanji(query)
    word_results = jamdict_source.search_words(query)

    return kanji_results, word_results


def detail(kanji_char: str) -> KanjiDetail | None:
    """Get full details for a kanji or kana character.

    Text data from KANJIDIC2 via jamdict; stroke SVG path from animCJK assets.
    For kana (not in KANJIDIC2), a minimal KanjiDetail is created if animCJK
    has stroke data for it.
    """
    from kakitui.data import jamdict_source

    result = jamdict_source.get_kanji_detail(kanji_char)

    svg_path = animcjk.get_svg_path(kanji_char)

    if result is not None:
        if svg_path:
            result.animcjk_svg_path = str(svg_path)
        return result

    if svg_path is not None:
        return KanjiDetail(
            kanji=kanji_char,
            meaning="",
            animcjk_svg_path=str(svg_path),
        )

    return None
