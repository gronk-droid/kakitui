"""Unified data source: jamdict primary, with API/CSV fallbacks for strokes."""

from __future__ import annotations

from kakitui.data import api, local
from kakitui.data.config import get_use_api
from kakitui.data.models import KanjiDetail, KanjiResult, WordResult


def search(query: str) -> tuple[list[KanjiResult], list[WordResult]]:
    """Search for both kanji and words in a single call.

    Returns (kanji_results, word_results). Tries jamdict first, then
    falls back to local CSV / API for the kanji list.
    """
    from kakitui.data import jamdict_source

    kanji_results = jamdict_source.search_kanji(query)
    word_results = jamdict_source.search_words(query)

    if not kanji_results:
        kanji_results = _search_kanji_fallback(query)

    return kanji_results, word_results


def _search_kanji_fallback(query: str) -> list[KanjiResult]:
    """Fallback kanji search via API / local CSV."""
    use = get_use_api()
    if use == "local":
        return local.search_kanji(query)
    if use in ("api", "auto") and api.api_available():
        results = api.search_kanji(query)
        if results is not None:
            return results
        if use == "api":
            return []
    return local.search_kanji(query)


def detail(kanji_char: str) -> KanjiDetail | None:
    """Get full details for a kanji character.

    Tries jamdict (KANJIDIC2) first — stroke URLs come from local CSV.
    Falls back to API / local CSV for characters not in KANJIDIC2.
    """
    from kakitui.data import jamdict_source

    result = jamdict_source.get_kanji_detail(kanji_char)
    if result is not None:
        return result

    use = get_use_api()
    if use == "local":
        return local.get_kanji_detail(kanji_char)
    if use in ("api", "auto") and api.api_available():
        api_result = api.get_kanji_detail(kanji_char)
        if api_result is not None:
            return api_result
        if use == "api":
            return None
    return local.get_kanji_detail(kanji_char)
