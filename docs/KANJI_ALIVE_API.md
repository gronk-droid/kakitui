# Kanji Alive API — Integration Reference

This document describes how kakitui integrates with the
[Kanji Alive](https://kanjialive.com/) data and API. It is the single
source of truth for the API layer in this project and is intended for
both human contributors and AI agents working on the codebase.

---

## Data sources overview

kakitui supports **two** data sources, selected automatically:

| Source | When used | Module |
|--------|-----------|--------|
| **Kanji Alive API** (RapidAPI) | `KANJI_ALIVE_API_KEY` env var is set | `kakitui/data/api.py` |
| **Local CSV** (`ka_data.csv`) | No API key, or API request fails | `kakitui/data/local.py` |

The unified facade in `kakitui/data/source.py` tries the API first and
falls back to local transparently.

---

## 1. Kanji Alive API (RapidAPI)

### Base URL and authentication

| Field | Value |
|-------|-------|
| Host | `kanjialive-kanjialive.p.rapidapi.com` |
| Base URL | `https://kanjialive-kanjialive.p.rapidapi.com/api/public` |
| Auth header | `X-RapidAPI-Key: <your-key>` |
| Host header | `X-RapidAPI-Host: kanjialive-kanjialive.p.rapidapi.com` |
| Docs | <https://app.kanjialive.com/api/docs> |

The key is read from the environment variable **`KANJI_ALIVE_API_KEY`**.
When the variable is absent or empty the app silently skips the API and
uses the local CSV.

### Endpoints used

#### Search — `GET /api/public/search/{query}`

Searches kanji by character, reading (kana or romaji), or English
meaning.

**Parameters:**

| Name | In | Description |
|------|----|-------------|
| `query` | path | Search term (URL-encoded). Accepts kanji, kana, romaji, or English. |

**Response** — JSON array of objects, each representing a matching kanji:

```json
[
  {
    "kanji": {
      "character": "水",
      "kname": "mizu",
      "meaning": { "english": "water" },
      "strokes": { "count": 4 },
      "grade": 1
    }
  }
]
```

Key fields extracted by `api.search_kanji()`:

- `kanji.character` — the kanji character
- `kanji.kname` — romanized name (used as media filename key)
- `kanji.meaning.english` — English meaning
- `kanji.strokes.count` — stroke count
- `kanji.grade` — school grade level

#### Kanji detail — `GET /api/public/kanji/{character}`

Returns full data for a single kanji, including media URLs, readings,
examples (with audio), radical, and mnemonic hint.

**Parameters:**

| Name | In | Description |
|------|----|-------------|
| `character` | path | Single kanji character (URL-encoded). |

**Response** — JSON object:

```json
{
  "kanji": {
    "character": "水",
    "kname": "mizu",
    "meaning": { "english": "water" },
    "strokes": {
      "count": 4,
      "images": [
        "https://media.kanjialive.com/kanji_strokes/mizu_00001.svg",
        "https://media.kanjialive.com/kanji_strokes/mizu_00002.svg",
        "https://media.kanjialive.com/kanji_strokes/mizu_00003.svg",
        "https://media.kanjialive.com/kanji_strokes/mizu_00004.svg"
      ]
    },
    "grade": 1,
    "kunyomi": { "hiragana": "みず", "romaji": "mizu" },
    "onyomi":  { "katakana": "スイ", "romaji": "sui" },
    "video": { "mp4": "https://media.kanjialive.com/kanji_animations/mizu_00.mp4" }
  },
  "radical": {
    "character": "⽔",
    "order": 109,
    "strokes": 4,
    "name": { "hiragana": "みず", "romaji": "mizu" },
    "meaning": { "english": "water" },
    "position": { "hiragana": "", "romaji": "" }
  },
  "references": {
    "hint": "..." 
  },
  "examples": [
    {
      "japanese": "水曜日（すいようび）",
      "meaning": { "english": "Wednesday" },
      "audio": { "mp3": "https://media.kanjialive.com/examples_audio/mizu_06_a.mp3" }
    }
  ]
}
```

Key fields extracted by `api.get_kanji_detail()`:

- `kanji.strokes.images` — array of SVG URLs for each stroke (ascending order). The last image shows all strokes complete.
- `kanji.video.mp4` — stroke-order animation video.
- `examples[].audio.mp3` — pronunciation audio for each example word.
- `references.hint` — mnemonic hint (copyright-restricted; only available via the API, not in the CSV).

---

## 2. Local CSV fallback

### Data file

`kakitui/data/ka_data.csv` is a copy of
[`ka_data.csv`](https://github.com/kanjialive/kanji-data-media/blob/master/language-data/ka_data.csv)
from the [kanji-data-media](https://github.com/kanjialive/kanji-data-media)
repository (CC-BY 4.0 license). It contains 1,234 kanji rows.

### CSV columns

| Column | Type | Description |
|--------|------|-------------|
| `kanji` | str | The kanji character |
| `kname` | str | Romanized filename key for media (e.g. `mizu`, `jutsu-no(beru)`) |
| `kstroke` | int | Stroke count |
| `kmeaning` | str | English meaning(s) |
| `kgrade` | int | School grade (1–6, or higher) |
| `kunyomi_ja` | str | Kun'yomi in hiragana (e.g. `みず`) |
| `kunyomi` | str | Kun'yomi in romaji (e.g. `mizu`) |
| `onyomi_ja` | str | On'yomi in katakana (e.g. `スイ`) |
| `onyomi` | str | On'yomi in romaji (e.g. `sui`) |
| `examples` | JSON | Array of `[japanese, english]` pairs |
| `radical` | str | Radical character |
| `rad_order` | int | Radical order number |
| `rad_stroke` | int | Radical stroke count |
| `rad_name_ja` | str | Radical name in hiragana |
| `rad_name` | str | Radical name in romaji |
| `rad_meaning` | str | Radical meaning in English |
| `rad_position_ja` | str | Position name in Japanese |
| `rad_position` | str | Position name in romaji |

### Media URL construction

When the API is not used, media URLs are constructed from `kname`:

| Media type | URL pattern |
|------------|-------------|
| Stroke SVG (individual) | `https://media.kanjialive.com/kanji_strokes/{kname}_{stroke_num:05d}.svg` |
| Animation video | `https://media.kanjialive.com/kanji_animations/{kname}_00.mp4` |
| Example audio | `https://media.kanjialive.com/examples_audio/{kname}_06_{letter}.mp3` where `letter` = `a`, `b`, `c`, ... matching example order |

These functions are in `kakitui/data/local.py`:

- `stroke_diagram_url(kname, stroke_num)` — individual stroke SVG
- `animation_url(kname)` — animation MP4
- `example_audio_url(kname, index)` — example audio by index

### What's NOT in the CSV

- **Mnemonic hint** — copyright-restricted; only returned by the API
  (`references.hint` field).
- **Textbook/chapter data** — not included for copyright reasons.

---

## 3. Code structure

### Public functions

**`kakitui/data/source.py`** (unified facade):

- `search(query: str) -> list[KanjiResult]` — search by kanji, kana,
  romaji, or English meaning. Tries API, falls back to CSV.
- `detail(kanji_char: str) -> KanjiDetail | None` — get full details
  for a single kanji character.

**`kakitui/data/api.py`** (API client):

- `api_available() -> bool` — check if API key is configured.
- `search_kanji(query) -> list[KanjiResult] | None` — API search.
  Returns `None` on failure (caller should fall back).
- `get_kanji_detail(character) -> KanjiDetail | None` — API detail lookup.

**`kakitui/data/local.py`** (local CSV):

- `search_kanji(query) -> list[KanjiResult]` — local search on CSV data.
- `get_kanji_detail(kanji_char) -> KanjiDetail | None` — detail from CSV.
- `get_kanji_detail_by_kname(kname) -> KanjiDetail | None` — detail by kname.

### Data models (`kakitui/data/models.py`)

- `KanjiResult` — lightweight search result (kanji, kname, meaning, grade, strokes).
- `KanjiDetail` — full detail (all readings, examples, radical, media URLs, hint).
- `ExampleWord` — single example (japanese, english).
- `RadicalInfo` — radical metadata.

---

## 4. Adding a new API endpoint

1. Add the request function in `kakitui/data/api.py` using `_get(path)`.
2. Parse the response into the appropriate model from `models.py` (add
   new fields to models if needed).
3. Wire it through `kakitui/data/source.py` with API-first + local
   fallback.
4. **Update this document** with the endpoint details.

---

## 5. External references

- API docs: <https://app.kanjialive.com/api/docs>
- RapidAPI listing: <https://rapidapi.com/kanjialive/api/learn-to-read-and-write-japanese-kanji/>
- Media repository: <https://github.com/kanjialive/kanji-data-media>
- Web app source: <https://github.com/kanjialive/kanji-web-app>
- License: [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) for data/media
