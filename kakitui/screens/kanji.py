"""Kanji detail screen with multi-kanji navigation and tabbed content."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    Label,
    TabbedContent,
    TabPane,
)

from kakitui.data import source
from kakitui.data.models import KanjiDetail
from kakitui.media import DEFAULT_STROKE_COLOR, animcjk_svg_to_frames

if TYPE_CHECKING:
    from PIL import Image


class _StrokesKeyHandler(Widget):
    """Focusable widget that captures arrow keys in the Strokes tab."""

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
            if event.key == "left":
                self.screen.action_stroke_prev()
            elif event.key == "right":
                self.screen.action_stroke_next()
            elif event.key == "up":
                self.screen.action_kanji_prev()
            elif event.key == "down":
                self.screen.action_kanji_next()
        event.stop()


class KanjiScreen(Screen):
    """Detail view for one or more kanji characters."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "prev_tab", "Prev tab"),
    ]

    TAB_ORDER = ("tab-strokes", "tab-info", "tab-pron")

    def __init__(
        self,
        kanji_chars: list[str],
        word: str | None = None,
        word_reading: str | None = None,
        word_meanings: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._kanji_list = kanji_chars
        self._kanji_index = 0
        self._word = word
        self._word_reading = word_reading
        self._word_meanings = word_meanings or []

        self._details: dict[str, KanjiDetail | None] = {}
        self._stroke_images_cache: dict[str, list[Image.Image]] = {}

        self._stroke_images: list[Image.Image] = []
        self._stroke_index = 0
        self._stroke_image_widget = None
        self._stroke_index_label: Label | None = None
        self._kanji_nav_label: Label | None = None

    @property
    def _current_kanji(self) -> str:
        return self._kanji_list[self._kanji_index]

    @property
    def _is_multi(self) -> bool:
        return len(self._kanji_list) > 1

    @property
    def _detail(self) -> KanjiDetail | None:
        return self._details.get(self._current_kanji)

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        initial_display = self._current_kanji
        with Horizontal():
            with Vertical(id="kanji-sidebar"):
                if self._word:
                    yield Label(self._word, id="kanji-word-label")
                yield Label(initial_display, id="kanji-big")
                if self._is_multi:
                    yield Label(
                        f"Kanji 1 of {len(self._kanji_list)}  ↑↓",
                        id="kanji-nav-label",
                    )
                yield Label("loading...", id="kanji-meaning-sidebar")
                yield Label("", id="kanji-reading-sidebar")
            with Vertical(id="detail-tabs"):
                with TabbedContent(id="kanji-tabs"):
                    with TabPane("Strokes", id="tab-strokes"):
                        yield Label(
                            "Loading stroke data...", id="strokes-loading"
                        )
                    with TabPane("Info", id="tab-info"):
                        yield Label("Loading info...", id="info-loading")
                    with TabPane("Pronunciation", id="tab-pron"):
                        yield Label(
                            "Loading pronunciation...", id="pron-loading"
                        )

    def on_mount(self) -> None:
        if self._is_multi:
            self._kanji_nav_label = self.query_one("#kanji-nav-label", Label)
        self._load_current_kanji()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @work(thread=True)
    def _load_current_kanji(self) -> None:
        kanji = self._current_kanji
        if kanji not in self._details:
            detail = source.detail(kanji)
            self._details[kanji] = detail
        self.app.call_from_thread(self._populate, self._details[kanji])

    def _populate(self, detail: KanjiDetail | None) -> None:
        if detail is None:
            for lid in ("#strokes-loading", "#info-loading", "#pron-loading"):
                try:
                    self.query_one(lid, Label).update(
                        "Could not load details for this kanji."
                    )
                except Exception:
                    pass
            return

        self._update_sidebar(detail)
        self._populate_strokes(detail)
        self._populate_info(detail)
        self._populate_pronunciation(detail)

    def _update_sidebar(self, detail: KanjiDetail) -> None:
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

        if self._kanji_nav_label is not None:
            self._kanji_nav_label.update(
                f"Kanji {self._kanji_index + 1} of {len(self._kanji_list)}  ↑↓"
            )

    # ------------------------------------------------------------------
    # Kanji navigation (Up / Down)
    # ------------------------------------------------------------------

    def action_kanji_prev(self) -> None:
        if not self._is_multi or not self._is_strokes_tab_active():
            return
        self._kanji_index = (self._kanji_index - 1) % len(self._kanji_list)
        self._switch_to_kanji()

    def action_kanji_next(self) -> None:
        if not self._is_multi or not self._is_strokes_tab_active():
            return
        self._kanji_index = (self._kanji_index + 1) % len(self._kanji_list)
        self._switch_to_kanji()

    def _switch_to_kanji(self) -> None:
        """Reload the entire screen content for the newly selected kanji."""
        self._stroke_images = []
        self._stroke_index = 0
        self._stroke_image_widget = None
        self._stroke_index_label = None

        self._reset_tab_pane("tab-strokes", "strokes-loading", "Loading stroke data...")
        self._reset_tab_pane("tab-info", "info-loading", "Loading info...")
        self._reset_tab_pane("tab-pron", "pron-loading", "Loading pronunciation...")

        detail = self._details.get(self._current_kanji)
        if detail is not None:
            self._populate(detail)
        else:
            self._update_sidebar_loading()
            self._load_current_kanji()

    def _update_sidebar_loading(self) -> None:
        self.query_one("#kanji-big", Label).update(
            f"[bold]{self._current_kanji}[/bold]"
        )
        self.query_one("#kanji-meaning-sidebar", Label).update("loading...")
        self.query_one("#kanji-reading-sidebar", Label).update("")
        if self._kanji_nav_label is not None:
            self._kanji_nav_label.update(
                f"Kanji {self._kanji_index + 1} of {len(self._kanji_list)}  ↑↓"
            )

    def _reset_tab_pane(self, pane_id: str, loading_id: str, loading_text: str) -> None:
        """Clear a tab pane back to its loading state."""
        try:
            pane = self.query_one(f"#{pane_id}", TabPane)
        except Exception:
            return
        for child in list(pane.children):
            if hasattr(child, "id") and child.id == loading_id:
                child.update(loading_text)
            else:
                child.remove()
        if not any(
            hasattr(c, "id") and c.id == loading_id for c in pane.children
        ):
            pane.mount(Label(loading_text, id=loading_id))

    # ------------------------------------------------------------------
    # Strokes tab
    # ------------------------------------------------------------------

    def _populate_strokes(self, detail: KanjiDetail) -> None:
        pane = self.query_one("#tab-strokes", TabPane)
        try:
            pane.query_one("#strokes-loading", Label).remove()
        except Exception:
            pass

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label("[bold]Stroke Order[/bold]", classes="info-heading")
        )
        if detail.strokes > 0:
            content.mount(Label(f"Total strokes: {detail.strokes}"))

        media_container = Vertical(id="stroke-media-container")
        content.mount(media_container)

        if detail.animcjk_svg_path:
            cached = self._stroke_images_cache.get(detail.kanji)
            if cached:
                self._mount_stroke_grid_result(cached, media_container)
            else:
                self._fetch_and_show_stroke_grid(
                    detail.animcjk_svg_path, detail.kanji
                )
        else:
            media_container.mount(Label("\nNo stroke data available."))

    @work(thread=True)
    def _fetch_and_show_stroke_grid(self, svg_path: str, kanji_char: str) -> None:
        images = animcjk_svg_to_frames(svg_path, stroke_color=DEFAULT_STROKE_COLOR)
        if images:
            self._stroke_images_cache[kanji_char] = images
        self.app.call_from_thread(
            self._mount_stroke_grid_callback, images, kanji_char
        )

    def _mount_stroke_grid_callback(
        self, images: list[Image.Image], kanji_char: str
    ) -> None:
        """Worker callback — only mount if the user hasn't navigated away."""
        if self._current_kanji != kanji_char:
            return
        try:
            container = self.query_one("#stroke-media-container", Vertical)
        except Exception:
            return
        self._mount_stroke_grid_result(images, container)

    def _mount_stroke_grid_result(
        self, images: list[Image.Image], container: Vertical
    ) -> None:
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

        nav_hint = "←/→ strokes"
        if self._is_multi:
            nav_hint += "  |  ↑/↓ kanji"
        container.mount(Label(f"[dim]{nav_hint}[/dim]", id="stroke-nav-hint"))

        try:
            if (
                self.query_one("#kanji-tabs", TabbedContent).active
                == "tab-strokes"
            ):
                key_handler.focus()
        except Exception:
            pass

    def _is_strokes_tab_active(self) -> bool:
        try:
            tabs = self.query_one("#kanji-tabs", TabbedContent)
            return tabs.active == "tab-strokes"
        except Exception:
            return False

    def _update_stroke_display(self) -> None:
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
        if not self._is_strokes_tab_active() or not self._stroke_images:
            return
        if self._stroke_image_widget is None:
            return
        self._stroke_index = (self._stroke_index - 1) % len(self._stroke_images)
        self._update_stroke_display()

    def action_stroke_next(self) -> None:
        if not self._is_strokes_tab_active() or not self._stroke_images:
            return
        if self._stroke_image_widget is None:
            return
        self._stroke_index = (self._stroke_index + 1) % len(self._stroke_images)
        self._update_stroke_display()

    # ------------------------------------------------------------------
    # Tab navigation
    # ------------------------------------------------------------------

    def _focus_tab_content(self, pane: TabPane) -> None:
        try:
            if pane.id == "tab-strokes":
                pane.query_one(
                    "#strokes-key-handler", _StrokesKeyHandler
                ).focus()
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
        self._focus_tab_content(event.pane)

    def action_next_tab(self) -> None:
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
        if event.key == "shift+tab":
            self.action_prev_tab()
            event.stop()
            return
        if event.key == "tab":
            self.action_next_tab()
            event.stop()
            return
        if event.key in ("left", "right", "up", "down"):
            if self._is_strokes_tab_active():
                if event.key == "left":
                    self.action_stroke_prev()
                elif event.key == "right":
                    self.action_stroke_next()
                elif event.key == "up":
                    self.action_kanji_prev()
                elif event.key == "down":
                    self.action_kanji_next()
                event.stop()

    # ------------------------------------------------------------------
    # Info tab
    # ------------------------------------------------------------------

    def _populate_info(self, detail: KanjiDetail) -> None:
        pane = self.query_one("#tab-info", TabPane)
        try:
            pane.query_one("#info-loading", Label).remove()
        except Exception:
            pass

        content = Vertical()
        pane.mount(content)

        if self._word and self._word_meanings:
            content.mount(
                Label("[bold]Word[/bold]", classes="info-heading")
            )
            reading_part = (
                f" ({self._word_reading})" if self._word_reading else ""
            )
            content.mount(
                Label(
                    f"  {self._word}{reading_part}",
                    classes="info-row",
                )
            )
            content.mount(
                Label(
                    f"  {', '.join(self._word_meanings[:5])}",
                    classes="info-row",
                )
            )
            content.mount(Label(""))

        content.mount(
            Label("[bold]Kanji Information[/bold]", classes="info-heading")
        )
        content.mount(Label(f"  Grade: {detail.grade}", classes="info-row"))
        content.mount(
            Label(f"  Strokes: {detail.strokes}", classes="info-row")
        )

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

    # ------------------------------------------------------------------
    # Pronunciation tab
    # ------------------------------------------------------------------

    def _populate_pronunciation(self, detail: KanjiDetail) -> None:
        pane = self.query_one("#tab-pron", TabPane)
        try:
            pane.query_one("#pron-loading", Label).remove()
        except Exception:
            pass

        scroll = VerticalScroll()
        pane.mount(scroll)

        content = Vertical()
        scroll.mount(content)

        content.mount(
            Label("[bold]Pronunciation[/bold]", classes="pron-heading")
        )

        if detail.onyomi_ja or detail.onyomi:
            content.mount(Label("[bold]On'yomi (Chinese reading):[/bold]"))
            display = detail.onyomi_ja
            if detail.onyomi:
                display += f"  ({detail.onyomi})"
            content.mount(Label(f"  {display}", classes="pron-reading"))

        if detail.kunyomi_ja or detail.kunyomi:
            content.mount(Label("[bold]Kun'yomi (Japanese reading):[/bold]"))
            display = detail.kunyomi_ja
            if detail.kunyomi:
                display += f"  ({detail.kunyomi})"
            content.mount(Label(f"  {display}", classes="pron-reading"))

        if detail.examples:
            content.mount(Label(""))
            content.mount(
                Label("[bold]Example Words[/bold]", classes="pron-heading")
            )
            for ex in detail.examples:
                content.mount(
                    Label(
                        f"  {ex.japanese}  —  {ex.english}",
                        classes="example-item",
                    )
                )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_go_back(self) -> None:
        self.app.pop_screen()

