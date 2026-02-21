"""Help overlay — LazyVim-style key bindings hints (triggered by ?)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


# Curated hints: (key_display, description) per section
GLOBAL_HINTS = [
    ("?", "Show this help"),
    ("Ctrl+q", "Quit"),
]

HOME_HINTS = [
    ("Enter", "Search / submit"),
    ("↑ / ↓", "Move through results"),
    ("Enter", "Open selected kanji"),
]

KANJI_HINTS = [
    ("Esc", "Back to search"),
    ("Tab", "Switch tab (Strokes / Info / Pronunciation)"),
    ("← / → or ↑ / ↓", "Step through strokes (Strokes tab)"),
]


class HelpScreen(ModalScreen[None]):
    """Modal overlay showing key bindings in a LazyVim-style hints box."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(classes="help-box"):
                yield Label("Key bindings", classes="help-title")
                yield Static("")
                yield Label("Global", classes="help-section")
                for key, desc in GLOBAL_HINTS:
                    yield Static(self._row(key, desc), classes="help-row")
                yield Static("")
                yield Label("Home (search)", classes="help-section")
                for key, desc in HOME_HINTS:
                    yield Static(self._row(key, desc), classes="help-row")
                yield Static("")
                yield Label("Kanji detail", classes="help-section")
                for key, desc in KANJI_HINTS:
                    yield Static(self._row(key, desc), classes="help-row")
                yield Static("")
                yield Label("Press Esc or q to close", classes="help-footer")

    @staticmethod
    def _row(key: str, description: str) -> str:
        # Key in a pill-like style, description after
        return f"[bold #89b4fa]{key:12}[/bold #89b4fa]  {description}"

    def action_dismiss(self) -> None:
        self.dismiss(None)
