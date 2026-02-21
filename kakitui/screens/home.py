"""Home screen with banner, search input, and results list."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from kakitui.data import source
from kakitui.data.models import KanjiResult
from kakitui.widgets.banner import Banner


class HomeScreen(Screen):
    """The main landing screen with search."""

    BINDINGS = []

    # Styling is in kakitui.tcss

    def __init__(self) -> None:
        super().__init__()
        self._results: list[KanjiResult] = []

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="home-container"):
                yield Banner()
                yield Label(
                    "Search by kanji, hiragana, romaji, or English meaning",
                    id="search-label",
                )
                yield Input(
                    placeholder="Type to search...",
                    id="search-box",
                )
                yield Label("", id="no-results")
                with VerticalScroll(can_focus=False):
                    yield OptionList(id="results-list")

    def on_mount(self) -> None:
        self.query_one("#search-box", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Run search when the user presses Enter."""
        query = event.value.strip()
        if query:
            self._run_search(query)

    @work(thread=True)
    def _run_search(self, query: str) -> None:
        """Search in a worker thread to keep the UI responsive."""
        results = source.search(query)
        self.app.call_from_thread(self._display_results, results)

    def _display_results(self, results: list[KanjiResult]) -> None:
        """Update the option list with search results."""
        self._results = results
        option_list = self.query_one("#results-list", OptionList)
        option_list.clear_options()

        no_results_label = self.query_one("#no-results", Label)

        if not results:
            no_results_label.update("No results found.")
            no_results_label.styles.display = "block"
            return

        no_results_label.styles.display = "none"

        for r in results:
            readings = []
            if r.meaning:
                readings.append(r.meaning)
            label = f"{r.kanji}  —  {', '.join(readings)}"
            option_list.add_option(Option(label, id=r.kanji))

        option_list.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        """Navigate to the kanji detail screen."""
        # Find the selected result
        idx = event.option_index
        if 0 <= idx < len(self._results):
            selected = self._results[idx]
            from kakitui.screens.kanji import KanjiScreen

            self.app.push_screen(KanjiScreen(selected.kanji))
