"""Home screen with banner, search input, and results list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from kakitui.data import source
from kakitui.data.models import KanjiResult, WordResult
from kakitui.widgets.banner import Banner


@dataclass
class _ResultEntry:
    """Wrapper so we can track both result type and index in the option list."""

    item: Union[KanjiResult, WordResult]


class HomeScreen(Screen):
    """The main landing screen with search."""

    BINDINGS = []

    def __init__(self) -> None:
        super().__init__()
        self._results: list[_ResultEntry] = []

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="home-container"):
                yield Banner()
                yield Label(
                    "Search by kanji, kana, or English meaning",
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
        query = event.value.strip()
        if query:
            self._run_search(query)

    @work(thread=True)
    def _run_search(self, query: str) -> None:
        kanji_results, word_results = source.search(query)
        self.app.call_from_thread(self._display_results, kanji_results, word_results)

    def _display_results(
        self,
        kanji_results: list[KanjiResult],
        word_results: list[WordResult],
    ) -> None:
        self._results = []
        option_list = self.query_one("#results-list", OptionList)
        option_list.clear_options()
        no_results_label = self.query_one("#no-results", Label)

        if not kanji_results and not word_results:
            no_results_label.update("No results found.")
            no_results_label.styles.display = "block"
            return

        no_results_label.styles.display = "none"

        for r in kanji_results:
            self._results.append(_ResultEntry(item=r))
            label = f"[dim]漢[/dim]  {r.kanji}  —  {r.meaning}" if r.meaning else f"[dim]漢[/dim]  {r.kanji}"
            option_list.add_option(Option(label))

        for r in word_results:
            self._results.append(_ResultEntry(item=r))
            meanings_str = ", ".join(r.meanings[:3])
            reading_part = f" ({r.reading})" if r.reading and r.reading != r.text else ""
            label = f"[dim]語[/dim]  {r.text}{reading_part}  —  {meanings_str}"
            option_list.add_option(Option(label))

        option_list.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        idx = event.option_index
        if idx < 0 or idx >= len(self._results):
            return

        entry = self._results[idx]
        from kakitui.screens.kanji import KanjiScreen

        if isinstance(entry.item, KanjiResult):
            self.app.push_screen(
                KanjiScreen(kanji_chars=[entry.item.kanji])
            )
        elif isinstance(entry.item, WordResult):
            from kakitui.data.jamdict_source import extract_japanese_chars

            kanji_chars = extract_japanese_chars(entry.item.text)
            if not kanji_chars:
                kanji_chars = [entry.item.text[0]] if entry.item.text else []
            self.app.push_screen(
                KanjiScreen(
                    kanji_chars=kanji_chars,
                    word=entry.item.text,
                    word_reading=entry.item.reading,
                    word_meanings=entry.item.meanings,
                )
            )
