"""Main Textual application for kakitui."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from kakitui.screens.home import HomeScreen

CSS_PATH = Path(__file__).parent / "kakitui.tcss"


class KakiTUIApp(App):
    """Kanji stroke-order lookup TUI, powered by Kanji Alive."""

    TITLE = "kakitui"
    SUB_TITLE = "「書き」TUI — Kanji Stroke Order Lookup"

    CSS_PATH = "kakitui.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Push the home screen on startup."""
        self.push_screen(HomeScreen())
