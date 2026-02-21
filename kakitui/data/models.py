"""Data models for kanji information."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExampleWord:
    """A compound word example with Japanese and English."""

    japanese: str
    english: str


@dataclass
class RadicalInfo:
    """Information about a kanji's radical."""

    character: str = ""
    order: int = 0
    strokes: int = 0
    name_ja: str = ""
    name: str = ""
    meaning: str = ""
    position_ja: str = ""
    position: str = ""


@dataclass
class KanjiResult:
    """A kanji search result (lightweight, for listing)."""

    kanji: str
    kname: str  # romanized filename key for media
    meaning: str
    grade: int = 0
    strokes: int = 0


@dataclass
class KanjiDetail:
    """Full kanji detail for the detail screen."""

    kanji: str
    kname: str
    meaning: str
    grade: int = 0
    strokes: int = 0
    kunyomi_ja: str = ""
    kunyomi: str = ""
    onyomi_ja: str = ""
    onyomi: str = ""
    examples: list[ExampleWord] = field(default_factory=list)
    radical: RadicalInfo = field(default_factory=RadicalInfo)
    hint: str = ""  # mnemonic hint (only from API, not in CSV)

    # Media URLs (populated by data source)
    stroke_diagram_url: str = ""
    stroke_image_urls: list[str] = field(default_factory=list)  # ordered stroke SVGs for in-app display
    audio_urls: list[str] = field(default_factory=list)


@dataclass
class WordResult:
    """A word search result from JMdict (lightweight, for listing)."""

    text: str  # e.g. "食べる"
    reading: str  # e.g. "たべる"
    meanings: list[str] = field(default_factory=list)


@dataclass
class WordDetail:
    """Full word detail with its constituent kanji characters."""

    text: str
    reading: str
    meanings: list[str] = field(default_factory=list)
    kanji_chars: list[str] = field(default_factory=list)  # kanji + kana characters from the word
