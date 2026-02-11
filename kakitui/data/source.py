"""Unified data source that tries the API and falls back to local CSV."""

from __future__ import annotations

from kakitui.data import api, local
from kakitui.data.models import KanjiDetail, KanjiResult


def search(query: str) -> list[KanjiResult]:
    """Search for kanji. Uses API if available, else local CSV."""
    if api.api_available():
        results = api.search_kanji(query)
        if results is not None:
            return results
    return local.search_kanji(query)


def detail(kanji_char: str) -> KanjiDetail | None:
    """Get full details for a kanji character."""
    if api.api_available():
        detail_result = api.get_kanji_detail(kanji_char)
        if detail_result is not None:
            return detail_result
    return local.get_kanji_detail(kanji_char)
