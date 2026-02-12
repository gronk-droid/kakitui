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
  - **Strokes** — stroke order diagram shown in-app (or open in browser)
  - **Animation** — stroke-by-stroke animation in-app (or open video in browser)
  - **Info** — grade, stroke count, radical (name, meaning, position), mnemonic hint (API only)
  - **Pronunciation** — on'yomi, kun'yomi, example words with audio indicators
- Persistent kanji sidebar on the detail screen
- Audio playback for example words (via `mpv`, `ffplay`, or browser)
- Dark catppuccin-mocha inspired theme

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended for project management)

### Optional: local stroke diagrams (offline / no 404s)

Stroke order SVGs are loaded from **media.kanjialive.com** by default. To use local files instead (e.g. after unzipping [kanji-data-media/kanji_strokes.zip](https://github.com/kanjialive/kanji-data-media/raw/master/kanji-strokes/kanji_strokes.zip)):

1. Unzip the archive.
2. Put the contents inside **`kakitui/data/assets/kanji_strokes/`** (so that files like `koku(motsu)_1.svg` live directly in that folder).

The app will use these files when present and fall back to the remote URLs otherwise. Animations and example audio still use the remote server unless you add those assets too.

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
| `?` | **Show key bindings** (LazyVim-style help overlay) |
| `Enter` | Submit search / select result |
| `↑` / `↓` | Navigate search results / tabs |
| `Escape` | Go back / quit |
| `b` | Go back (detail screen) |
| `p` | Play first example audio (detail screen) |
| `q` | Quit |

## Configuration

Configuration is read from **`~/.config/kakitui/config.ini`** (Linux/macOS)
or **`%APPDATA%\\kakitui\\config.ini`** (Windows). Environment variables
override config file values.

Copy the template and edit:

```bash
mkdir -p ~/.config/kakitui
cp config_template.ini ~/.config/kakitui/config.ini
```

### Config file format

```ini
[kanji_alive]
# RapidAPI key for Kanji Alive (optional)
api_key = your_rapidapi_key_here

[kakitui]
# Data source: api | local | auto (default: auto)
use_api = auto
```

- **`use_api`**
  - `auto` — Use API if key is set, otherwise fall back to local CSV.
  - `api` — Use API only (no results if key missing or request fails).
  - `local` — Use bundled CSV only; no API calls.

Environment overrides:

- `KANJI_ALIVE_API_KEY` — API key (overrides `[kanji_alive] api_key`).
- `KAKITUI_USE_API` — One of `api`, `local`, `auto` (overrides `[kakitui] use_api`).

## Kanji Alive API (optional)

By default, kakitui uses a bundled copy of `ka_data.csv` from
[kanji-data-media](https://github.com/kanjialive/kanji-data-media) for
offline search and metadata. This works without any API key.

For richer data (including mnemonic hints and verified media URLs), set
a [Kanji Alive RapidAPI](https://rapidapi.com/kanjialive/api/learn-to-read-and-write-japanese-kanji/)
key in your config file or environment:

```bash
# Option 1: config file ~/.config/kakitui/config.ini
# [kanji_alive]
# api_key = your_rapidapi_key_here

# Option 2: environment
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
│   ├── config.py        # Config loader (~/.config/kakitui/config.ini)
│   ├── local.py         # Local CSV search + media URLs
│   ├── models.py        # Data models (KanjiResult, KanjiDetail, etc.)
│   ├── source.py        # Unified data facade (API / local / auto)
│   └── ka_data.csv      # Bundled kanji data (1,234 kanji)
├── media.py             # Fetch SVG media, convert to PNG for in-app display
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
