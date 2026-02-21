<img src="resources/kakitui.svg" width="50%"/>

 A terminal-based kanji stroke-order lookup app.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

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

| Key        | Action                         |
| ---------- | ------------------------------ |
| `?`        | **Show key bindings**          |
| `Enter`    | Submit search / select result  |
| `↑` / `↓`  | Navigate search results / tabs |
| `Escape`   | Go back / quit                 |
| ctrl + `q` | Quit                           |


## Development

```bash
# Install with dev dependencies
uv sync

# Run linter
uv run ruff check kakitui/

# Run with Textual dev tools
uv run textual run --dev kakitui.app:KakiTUIApp
```

## Credits

- Stroke order data from [animCJK](https://github.com/parsimonhi/animCJK)
- Kanji dictionary data from [KANJIDIC2](http://www.edrdg.org/wiki/index.php/KANJIDIC_Project) via [jamdict](https://github.com/neocl/jamdict)
