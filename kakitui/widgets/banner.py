"""Banner widget displaying the kakitui title."""

from __future__ import annotations

from textual.widgets import Static

# ASCII-art banner with Rich markup for the catppuccin mocha palette.
BANNER_TEXT = """\
[bold #f5c2e7]
  ┌─────────────────────────────────────────┐
  │                                         │
  │   [bold #cba6f7]「 書  き 」[/bold #cba6f7]  [bold #89b4fa]T  U  I[/bold #89b4fa]              │
  │                                         │
  │       [dim #a6adc8]k  a  k  i  t  u  i[/dim #a6adc8]           │
  │                                         │
  └─────────────────────────────────────────┘
[/bold #f5c2e7]"""


class Banner(Static):
    """The application banner shown on the home screen."""

    def __init__(self) -> None:
        super().__init__(BANNER_TEXT)
