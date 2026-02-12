"""Unified data source: API, local CSV, or auto (API then fallback)."""

from __future__ import annotations

from kakitui.data import api, local
from kakitui.data.config import get_use_api
from kakitui.data.models import KanjiDetail, KanjiResult


def search(query: str) -> list[KanjiResult]:
    """Search for kanji. Respects use_api setting (api / local / auto)."""
    use = get_use_api()
    if use == "local":
        return local.search_kanji(query)
    if use == "api" and api.api_available():
        results = api.search_kanji(query)
        if results is not None:
            return results
        if use == "api":
            return []  # API-only but request failed
    if use in ("api", "auto") and api.api_available():
        results = api.search_kanji(query)
        if results is not None:
            return results
    return local.search_kanji(query)


def detail(kanji_char: str) -> KanjiDetail | None:
    """Get full details for a kanji character. Respects use_api setting."""
    use = get_use_api()
    if use == "local":
        return local.get_kanji_detail(kanji_char)
    if use == "api" and api.api_available():
        result = api.get_kanji_detail(kanji_char)
        if result is not None:
            return result
        return None  # API-only but request failed
    if use in ("api", "auto") and api.api_available():
        result = api.get_kanji_detail(kanji_char)
        if result is not None:
            return result
    return local.get_kanji_detail(kanji_char)
