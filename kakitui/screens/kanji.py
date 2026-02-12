"""Kanji detail screen with persistent kanji sidebar and tabbed content."""

from __future__ import annotations

import subprocess
import threading
import webbrowser
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Label,
    TabbedContent,
    TabPane,
)

from kakitui.data import source
from kakitui.data.models import KanjiDetail
from kakitui.media import fetch_stroke_images, fetch_svg_as_pillow

if TYPE_CHECKING:
    from PIL import Image


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
        self._anim_frames: list["Image.Image"] = []
        self._anim_index = 0
        self._anim_timer: object | None = None
        self._anim_image_widget = None  # set when animation tab shows in-app frames

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
        """Populate the Strokes tab pane; load diagram in-app when possible."""
        pane = self.query_one("#tab-strokes", TabPane)
        pane.query_one("#strokes-loading", Label).remove()

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label("[bold]Stroke Order Diagram[/bold]", classes="info-heading")
        )
        content.mount(Label(f"Total strokes: {detail.strokes}"))

        media_container = Vertical(id="stroke-media-container")
        content.mount(media_container)

        diagram_url = detail.stroke_diagram_url or (
            detail.stroke_image_urls[-1] if detail.stroke_image_urls else ""
        )
        if diagram_url:
            self._fetch_and_show_stroke_diagram(diagram_url)
        else:
            media_container.mount(Label("\nNo stroke diagram URL available."))

        # Individual stroke URLs (when we have kname), below diagram or fallback
        if detail.strokes > 0 and detail.kname:
            from kakitui.data.local import stroke_diagram_url

            content.mount(Label("\n[bold]Individual strokes:[/bold]"))
            for i in range(1, detail.strokes + 1):
                url = stroke_diagram_url(detail.kname, i)
                content.mount(Label(f"  Stroke {i}: {url}", markup=False))

    @work(thread=True)
    def _fetch_and_show_stroke_diagram(self, url: str) -> None:
        img = fetch_svg_as_pillow(url)
        self.app.call_from_thread(self._mount_stroke_diagram_result, img, url)

    def _mount_stroke_diagram_result(
        self, img: Image.Image | None, url: str
    ) -> None:
        try:
            container = self.query_one("#stroke-media-container", Vertical)
        except Exception:
            return
        if img is not None:
            from textual_image.widget import Image as TUIImage

            container.mount(TUIImage(img))
            container.mount(
                Button("Open in browser", id="btn-open-stroke"),
            )
        else:
            container.mount(
                Label(
                    f"\nFull diagram URL:\n  {url}",
                    classes="stroke-url-label",
                    markup=False,
                )
            )
            container.mount(Button("Open in browser", id="btn-open-stroke"))

    def _populate_animation(self, detail: KanjiDetail) -> None:
        """Populate the Animation tab pane; show stroke sequence in-app when possible."""
        pane = self.query_one("#tab-animation", TabPane)
        pane.query_one("#anim-loading", Label).remove()

        content = Vertical()
        pane.mount(content)

        content.mount(
            Label(
                "[bold]Stroke Order Animation[/bold]", classes="info-heading"
            )
        )

        media_container = Vertical(id="anim-media-container")
        content.mount(media_container)

        if detail.stroke_image_urls:
            self._fetch_and_show_animation(detail.stroke_image_urls, detail.animation_url)
        elif detail.animation_url:
            media_container.mount(
                Label(
                    f"\nAnimation URL:\n  {detail.animation_url}",
                    markup=False,
                )
            )
            media_container.mount(
                Button("Open in browser / player", id="btn-open-anim")
            )
        else:
            media_container.mount(Label("\nNo animation URL available."))

    @work(thread=True)
    def _fetch_and_show_animation(
        self, urls: list[str], fallback_animation_url: str
    ) -> None:
        frames = fetch_stroke_images(urls)
        self.app.call_from_thread(
            self._mount_animation_result, frames, fallback_animation_url
        )

    def _mount_animation_result(
        self,
        frames: list[Image.Image],
        fallback_animation_url: str,
    ) -> None:
        try:
            container = self.query_one("#anim-media-container", Vertical)
        except Exception:
            return
        if frames:
            from textual_image.widget import Image as TUIImage

            self._anim_frames = frames
            self._anim_index = 0
            self._anim_image_widget = TUIImage(frames[0])
            container.mount(self._anim_image_widget)
            if fallback_animation_url:
                container.mount(
                    Button("Open full video in browser", id="btn-open-anim")
                )
            self._anim_timer = self.set_interval(
                0.45, self._advance_animation, pause=False
            )
        else:
            if fallback_animation_url:
                container.mount(
                    Label(
                        f"\nAnimation URL:\n  {fallback_animation_url}",
                        markup=False,
                    )
                )
                container.mount(
                    Button("Open in browser / player", id="btn-open-anim")
                )
            else:
                container.mount(Label("\nNo animation URL available."))

    def _advance_animation(self) -> None:
        if not self._anim_frames or not hasattr(self, "_anim_image_widget"):
            return
        self._anim_index = (self._anim_index + 1) % len(self._anim_frames)
        self._anim_image_widget.image = self._anim_frames[self._anim_index]

    def on_unmount(self) -> None:
        if self._anim_timer is not None:
            self._anim_timer.stop()

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
