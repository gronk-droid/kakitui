"""Kanji detail screen with persistent kanji sidebar and tabbed content."""

from __future__ import annotations

import subprocess
import threading
import webbrowser
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Label,
    TabbedContent,
    TabPane,
)

from kakitui.data import source
from kakitui.data.models import KanjiDetail
from kakitui.media import DEFAULT_STROKE_COLOR, fetch_stroke_images

if TYPE_CHECKING:
    from PIL import Image


class _StrokesKeyHandler(Widget):
    """Focusable widget that captures left/right/up/down in Strokes tab to step stroke."""

    DEFAULT_CSS = """
    _StrokesKeyHandler {
        height: 0;
        min-height: 0;
    }
    """

    def on_key(self, event: Key) -> None:
        if event.key not in ("left", "right", "up", "down"):
            return
        if isinstance(self.screen, KanjiScreen):
            if event.key in ("left", "up"):
                self.screen.action_stroke_prev()
            else:
                self.screen.action_stroke_next()
        event.stop()


class KanjiScreen(Screen):
    """Detail view for a single kanji."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "prev_tab", "Prev tab"),
    ]

    TAB_ORDER = ("tab-strokes", "tab-info", "tab-pron")

    # Styling is in kakitui.tcss

    def __init__(self, kanji_char: str) -> None:
        super().__init__()
        self._kanji_char = kanji_char
        self._detail: KanjiDetail | None = None
        self._stroke_images: list["Image.Image"] = []
        self._stroke_index = 0
        self._stroke_image_widget = None
        self._stroke_index_label = None  # "Stroke N of M"

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
                    with TabPane("Info", id="tab-info"):
                        yield Label(
                            "Loading info...", id="info-loading"
                        )
                    with TabPane("Pronunciation", id="tab-pron"):
                        yield Label(
                            "Loading pronunciation...", id="pron-loading"
                        )

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
        self._populate_info(detail)
        self._populate_pronunciation(detail)

    # ------------------------------------------------------------------
    # Tab population helpers
    # ------------------------------------------------------------------

    def _populate_strokes(self, detail: KanjiDetail) -> None:
        """Populate the Strokes tab pane with each stroke SVG in a grid (theme-colored)."""
        pane = self.query_one("#tab-strokes", TabPane)
        pane.query_one("#strokes-loading", Label).remove()

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label("[bold]Stroke Order[/bold]", classes="info-heading")
        )
        content.mount(Label(f"Total strokes: {detail.strokes}"))

        media_container = Vertical(id="stroke-media-container")
        content.mount(media_container)

        if detail.strokes > 0 and (detail.stroke_image_urls or detail.kname):
            stroke_urls = list(detail.stroke_image_urls) if detail.stroke_image_urls else []
            if not stroke_urls and detail.kname:
                from kakitui.data.local import stroke_diagram_url

                stroke_urls = [
                    stroke_diagram_url(detail.kname, i)
                    for i in range(1, detail.strokes + 1)
                ]
            if stroke_urls:
                self._fetch_and_show_stroke_grid(stroke_urls)
            else:
                media_container.mount(Label("\nNo stroke URLs available."))
        else:
            media_container.mount(Label("\nNo stroke data available."))

    @work(thread=True)
    def _fetch_and_show_stroke_grid(self, urls: list[str]) -> None:
        images = fetch_stroke_images(urls, stroke_color=DEFAULT_STROKE_COLOR)
        self.app.call_from_thread(self._mount_stroke_grid_result, images)

    def _mount_stroke_grid_result(self, images: list[Image.Image]) -> None:
        try:
            container = self.query_one("#stroke-media-container", Vertical)
        except Exception:
            return
        if not images:
            container.mount(Label("\nCould not load stroke images."))
            return
        from textual_image.widget import Image as TUIImage

        self._stroke_images = images
        self._stroke_index = 0
        total = len(images)

        key_handler = _StrokesKeyHandler(id="strokes-key-handler")
        container.mount(key_handler)
        self._stroke_index_label = Label(
            f"Stroke 1 of {total}",
            id="stroke-index-label",
            classes="info-row",
        )
        container.mount(self._stroke_index_label)
        self._stroke_image_widget = TUIImage(images[0])
        container.mount(self._stroke_image_widget)
        try:
            if self.query_one("#kanji-tabs", TabbedContent).active == "tab-strokes":
                key_handler.focus()
        except Exception:
            pass

    def _is_strokes_tab_active(self) -> bool:
        try:
            tabs = self.query_one("#kanji-tabs", TabbedContent)
            return tabs.active == "tab-strokes"
        except Exception:
            return False

    def _focus_tab_content(self, pane: TabPane) -> None:
        """Focus the main content of a tab pane (key handler or first focusable)."""
        try:
            if pane.id == "tab-strokes":
                pane.query_one("#strokes-key-handler", _StrokesKeyHandler).focus()
                return
        except Exception:
            pass
        try:
            for child in pane.walk_children(Widget):
                if child.can_focus:
                    child.focus()
                    return
        except Exception:
            pass

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """When a tab becomes active, focus its content so arrow keys work without tabbing to it."""
        self._focus_tab_content(event.pane)

    def action_next_tab(self) -> None:
        """Switch to the next tab (Tab key)."""
        tabs = self.query_one("#kanji-tabs", TabbedContent)
        order = self.TAB_ORDER
        try:
            idx = order.index(tabs.active) if tabs.active else -1
        except ValueError:
            idx = -1
        next_idx = (idx + 1) % len(order)
        tabs.active = order[next_idx]
        pane = tabs.active_pane
        if pane is not None:
            self._focus_tab_content(pane)

    def action_prev_tab(self) -> None:
        """Switch to the previous tab (Shift+Tab)."""
        tabs = self.query_one("#kanji-tabs", TabbedContent)
        order = self.TAB_ORDER
        try:
            idx = order.index(tabs.active) if tabs.active else 0
        except ValueError:
            idx = 0
        prev_idx = (idx - 1) % len(order)
        tabs.active = order[prev_idx]
        pane = tabs.active_pane
        if pane is not None:
            self._focus_tab_content(pane)

    def on_key(self, event: Key) -> None:
        """Capture Tab/Shift+Tab to switch tabs; arrow keys step in Strokes/Animation tab."""
        if event.key == "shift+tab":
            self.action_prev_tab()
            event.stop()
            return
        if event.key == "tab":
            self.action_next_tab()
            event.stop()
            return
        # When Strokes tab is active, arrow keys step (don't switch tabs)
        if event.key in ("left", "right", "up", "down"):
            if self._is_strokes_tab_active() and self._stroke_images:
                if event.key in ("left", "up"):
                    self.action_stroke_prev()
                else:
                    self.action_stroke_next()
                event.stop()

    def _update_stroke_display(self) -> None:
        """Update the displayed stroke image and index label."""
        if not self._stroke_images or self._stroke_image_widget is None:
            return
        n = len(self._stroke_images)
        self._stroke_index = self._stroke_index % n
        self._stroke_image_widget.image = self._stroke_images[self._stroke_index]
        if self._stroke_index_label is not None:
            self._stroke_index_label.update(
                f"Stroke {self._stroke_index + 1} of {n}"
            )

    def action_stroke_prev(self) -> None:
        """Step to previous stroke in Strokes tab."""
        if not self._is_strokes_tab_active() or not self._stroke_images:
            return
        if self._stroke_image_widget is None:
            return
        self._stroke_index = (self._stroke_index - 1) % len(self._stroke_images)
        self._update_stroke_display()

    def action_stroke_next(self) -> None:
        """Step to next stroke in Strokes tab."""
        if not self._is_strokes_tab_active() or not self._stroke_images:
            return
        if self._stroke_image_widget is None:
            return
        self._stroke_index = (self._stroke_index + 1) % len(self._stroke_images)
        self._update_stroke_display()

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
