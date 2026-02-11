# kakitui

**「書き」TUI** — A terminal-based kanji stroke-order lookup app powered
by [Kanji Alive](https://kanjialive.com/).

Search for kanji by character, hiragana, romaji, or English meaning and
view stroke order diagrams, animations, readings, radical info, and
example words — all from your terminal.

## Features

- Banner with 「書き」TUI branding
- Centered search box supporting kanji, hiragana, romaji, and English
- Selectable search results
- Kanji detail view with four tabs:
  - **Strokes** — stroke order diagram URLs (individual + complete)
  - **Animation** — stroke order animation URL
  - **Info** — grade, stroke count, radical (name, meaning, position), mnemonic hint (API only)
  - **Pronunciation** — on'yomi, kun'yomi, example words with audio indicators
- Persistent kanji sidebar on the detail screen
- Audio playback for example words (via `mpv`, `ffplay`, or browser)
- Dark catppuccin-mocha inspired theme

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended for project management)

## Installation

```bash
# Clone the repository
git clone https://github.com/gronk-droid/kakitui.git
cd kakitui

# Install dependencies and run
uv sync
uv run kakitui
```

## Usage

```bash
# Run the app
uv run kakitui

# Or via the Python module
uv run python -m kakitui
```

### Key bindings

| Key | Action |
|-----|--------|
| `Enter` | Submit search / select result |
| `↑` / `↓` | Navigate search results / tabs |
| `Escape` | Go back / quit |
| `b` | Go back (detail screen) |
| `p` | Play first example audio (detail screen) |
| `q` | Quit |

## Kanji Alive API (optional)

By default, kakitui uses a bundled copy of `ka_data.csv` from
[kanji-data-media](https://github.com/kanjialive/kanji-data-media) for
offline search and metadata. This works without any API key.

For richer data (including mnemonic hints and verified media URLs), you
can optionally set a [Kanji Alive RapidAPI](https://rapidapi.com/kanjialive/api/learn-to-read-and-write-japanese-kanji/)
key:

```bash
export KANJI_ALIVE_API_KEY="your-rapidapi-key-here"
uv run kakitui
```

See [`docs/KANJI_ALIVE_API.md`](docs/KANJI_ALIVE_API.md) for full API
integration details.

## Audio playback

Example pronunciations can be played from the Pronunciation tab.
kakitui tries these players in order:

1. `mpv` (recommended)
2. `ffplay` (from FFmpeg)
3. `xdg-open` (opens in default handler)

Install one of these for audio support:

```bash
# Arch Linux
sudo pacman -S mpv

# Debian/Ubuntu
sudo apt install mpv
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run linter
uv run ruff check kakitui/

# Run with Textual dev tools
uv run textual run --dev kakitui.app:KakiTUIApp
```

## Project structure

```
kakitui/
├── __init__.py
├── __main__.py          # Entry point
├── app.py               # Textual App
├── kakitui.tcss         # Theme / stylesheet
├── data/
│   ├── __init__.py
│   ├── api.py           # Kanji Alive API client
│   ├── local.py         # Local CSV search + media URLs
│   ├── models.py        # Data models (KanjiResult, KanjiDetail, etc.)
│   ├── source.py        # Unified data facade (API → CSV fallback)
│   └── ka_data.csv      # Bundled kanji data (1,234 kanji)
├── screens/
│   ├── __init__.py
│   ├── home.py          # Home screen (banner + search + results)
│   └── kanji.py         # Kanji detail screen (sidebar + tabs)
└── widgets/
    ├── __init__.py
    └── banner.py        # 「書き」TUI banner widget
docs/
└── KANJI_ALIVE_API.md   # API integration reference
```

## Credits

- Kanji data and media from [Kanji Alive](https://kanjialive.com/)
  ([CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/))
- Built with [Textual](https://textual.textualize.io/)
- Design inspired by [smassh](https://github.com/kraanzu/smassh)

## License

See [Kanji Alive credits](https://kanjialive.com/credits/) for data
licensing. The application code is provided as-is.
