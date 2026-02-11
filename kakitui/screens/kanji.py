"""Kanji detail screen with persistent kanji sidebar and tabbed content."""

from __future__ import annotations

import subprocess
import threading
import webbrowser

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Label,
    TabbedContent,
    TabPane,
)

from kakitui.data import source
from kakitui.data.models import KanjiDetail


class KanjiScreen(Screen):
    """Detail view for a single kanji."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("b", "go_back", "Back"),
    ]

    # Styling is in kakitui.tcss

    def __init__(self, kanji_char: str) -> None:
        super().__init__()
        self._kanji_char = kanji_char
        self._detail: KanjiDetail | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="kanji-sidebar"):
                yield Label(self._kanji_char, id="kanji-big")
                yield Label("loading...", id="kanji-meaning-sidebar")
                yield Label("", id="kanji-reading-sidebar")
            with Vertical(id="detail-tabs"):
                with TabbedContent(id="kanji-tabs"):
                    with TabPane("Strokes", id="tab-strokes"):
                        yield Label(
                            "Loading stroke data...", id="strokes-loading"
                        )
                    with TabPane("Animation", id="tab-animation"):
                        yield Label(
                            "Loading animation data...", id="anim-loading"
                        )
                    with TabPane("Info", id="tab-info"):
                        yield Label(
                            "Loading info...", id="info-loading"
                        )
                    with TabPane("Pronunciation", id="tab-pron"):
                        yield Label(
                            "Loading pronunciation...", id="pron-loading"
                        )
        yield Footer()

    def on_mount(self) -> None:
        self._load_detail()

    @work(thread=True)
    def _load_detail(self) -> None:
        detail = source.detail(self._kanji_char)
        self.app.call_from_thread(self._populate, detail)

    def _populate(self, detail: KanjiDetail | None) -> None:
        if detail is None:
            for lid in (
                "#strokes-loading",
                "#anim-loading",
                "#info-loading",
                "#pron-loading",
            ):
                try:
                    self.query_one(lid, Label).update(
                        "Could not load details for this kanji."
                    )
                except Exception:
                    pass
            return

        self._detail = detail

        # Update sidebar
        self.query_one("#kanji-big", Label).update(
            f"[bold]{detail.kanji}[/bold]"
        )
        self.query_one("#kanji-meaning-sidebar", Label).update(detail.meaning)

        readings = []
        if detail.onyomi_ja:
            readings.append(detail.onyomi_ja)
        if detail.kunyomi_ja:
            readings.append(detail.kunyomi_ja)
        self.query_one("#kanji-reading-sidebar", Label).update(
            " / ".join(readings)
        )

        # Populate each tab
        self._populate_strokes(detail)
        self._populate_animation(detail)
        self._populate_info(detail)
        self._populate_pronunciation(detail)

    # ------------------------------------------------------------------
    # Tab population helpers
    # ------------------------------------------------------------------

    def _populate_strokes(self, detail: KanjiDetail) -> None:
        """Populate the Strokes tab pane."""
        pane = self.query_one("#tab-strokes", TabPane)
        # Remove loading label
        pane.query_one("#strokes-loading", Label).remove()

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label("[bold]Stroke Order Diagram[/bold]", classes="info-heading")
        )
        content.mount(Label(f"Total strokes: {detail.strokes}"))

        if detail.stroke_diagram_url:
            content.mount(
                Label(
                    f"\nFull diagram URL:\n  {detail.stroke_diagram_url}",
                    classes="stroke-url-label",
                    markup=False,
                )
            )
            content.mount(Button("Open in browser", id="btn-open-stroke"))
        else:
            content.mount(Label("\nNo stroke diagram URL available."))

        # Individual stroke URLs
        if detail.strokes > 0 and detail.kname:
            from kakitui.data.local import stroke_diagram_url

            content.mount(Label("\n[bold]Individual strokes:[/bold]"))
            for i in range(1, detail.strokes + 1):
                url = stroke_diagram_url(detail.kname, i)
                content.mount(
                    Label(f"  Stroke {i}: {url}", markup=False)
                )

    def _populate_animation(self, detail: KanjiDetail) -> None:
        """Populate the Animation tab pane."""
        pane = self.query_one("#tab-animation", TabPane)
        pane.query_one("#anim-loading", Label).remove()

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label(
                "[bold]Stroke Order Animation[/bold]", classes="info-heading"
            )
        )

        if detail.animation_url:
            content.mount(
                Label(
                    f"\nAnimation URL:\n  {detail.animation_url}",
                    markup=False,
                )
            )
            content.mount(
                Button("Open in browser / player", id="btn-open-anim")
            )
        else:
            content.mount(Label("\nNo animation URL available."))

    def _populate_info(self, detail: KanjiDetail) -> None:
        """Populate the Info tab pane."""
        pane = self.query_one("#tab-info", TabPane)
        pane.query_one("#info-loading", Label).remove()

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label("[bold]Kanji Information[/bold]", classes="info-heading")
        )
        content.mount(Label(f"  Grade: {detail.grade}", classes="info-row"))
        content.mount(
            Label(f"  Strokes: {detail.strokes}", classes="info-row")
        )

        # Radical
        rad = detail.radical
        if rad.character or rad.name:
            content.mount(Label(""))
            content.mount(
                Label("[bold]Radical[/bold]", classes="info-heading")
            )
            if rad.character:
                content.mount(
                    Label(
                        f"  Character: {rad.character}", classes="info-row"
                    )
                )
            if rad.name:
                content.mount(
                    Label(
                        f"  Name: {rad.name} ({rad.name_ja})",
                        classes="info-row",
                    )
                )
            if rad.meaning:
                content.mount(
                    Label(
                        f"  Meaning: {rad.meaning}", classes="info-row"
                    )
                )
            if rad.position:
                content.mount(
                    Label(
                        f"  Position: {rad.position} ({rad.position_ja})",
                        classes="info-row",
                    )
                )
            content.mount(
                Label(f"  Strokes: {rad.strokes}", classes="info-row")
            )

        # Hint (only from API)
        if detail.hint:
            content.mount(Label(""))
            content.mount(
                Label("[bold]Mnemonic Hint[/bold]", classes="info-heading")
            )
            content.mount(Label(f"  {detail.hint}"))

    def _populate_pronunciation(self, detail: KanjiDetail) -> None:
        """Populate the Pronunciation tab pane."""
        pane = self.query_one("#tab-pron", TabPane)
        pane.query_one("#pron-loading", Label).remove()

        scroll = VerticalScroll()
        pane.mount(scroll)

        content = Vertical()
        scroll.mount(content)

        content.mount(
            Label("[bold]Pronunciation[/bold]", classes="pron-heading")
        )

        # Onyomi
        if detail.onyomi_ja or detail.onyomi:
            content.mount(Label("[bold]On'yomi (Chinese reading):[/bold]"))
            display = detail.onyomi_ja
            if detail.onyomi:
                display += f"  ({detail.onyomi})"
            content.mount(Label(f"  {display}", classes="pron-reading"))

        # Kunyomi
        if detail.kunyomi_ja or detail.kunyomi:
            content.mount(Label("[bold]Kun'yomi (Japanese reading):[/bold]"))
            display = detail.kunyomi_ja
            if detail.kunyomi:
                display += f"  ({detail.kunyomi})"
            content.mount(Label(f"  {display}", classes="pron-reading"))

        # Examples
        if detail.examples:
            content.mount(Label(""))
            content.mount(
                Label("[bold]Example Words[/bold]", classes="pron-heading")
            )
            for i, ex in enumerate(detail.examples):
                has_audio = (
                    i < len(detail.audio_urls) and detail.audio_urls[i]
                )
                audio_indicator = " [dim]♪[/dim]" if has_audio else ""
                content.mount(
                    Label(
                        f"  {ex.japanese}  —  {ex.english}{audio_indicator}",
                        classes="example-item",
                    )
                )

            if any(detail.audio_urls):
                content.mount(Label(""))
                content.mount(
                    Label(
                        "[dim]♪ indicates audio available. "
                        "Press 'p' to play the first example audio.[/dim]"
                    )
                )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_go_back(self) -> None:
        """Return to the home screen."""
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for opening URLs."""
        if self._detail is None:
            return

        if (
            event.button.id == "btn-open-stroke"
            and self._detail.stroke_diagram_url
        ):
            webbrowser.open(self._detail.stroke_diagram_url)
        elif (
            event.button.id == "btn-open-anim"
            and self._detail.animation_url
        ):
            webbrowser.open(self._detail.animation_url)

    def key_p(self) -> None:
        """Play the first available example audio."""
        if self._detail is None:
            return
        for url in self._detail.audio_urls:
            if url:
                self._play_audio(url)
                break

    def _play_audio(self, url: str) -> None:
        """Attempt to play audio via mpv, ffplay, or open in browser."""

        def _try_play() -> None:
            for player in ("mpv", "ffplay", "xdg-open"):
                try:
                    cmd = [player]
                    if player == "mpv":
                        cmd.extend(["--no-video", "--really-quiet"])
                    elif player == "ffplay":
                        cmd.extend(
                            ["-nodisp", "-autoexit", "-loglevel", "quiet"]
                        )
                    cmd.append(url)
                    subprocess.run(cmd, timeout=15)  # noqa: S603
                    return
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            # Last resort
            webbrowser.open(url)

        threading.Thread(target=_try_play, daemon=True).start()
