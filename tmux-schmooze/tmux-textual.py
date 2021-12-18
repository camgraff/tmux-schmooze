import string
from rich.control import Control
from rich.segment import ControlType, Segment, Segments
from textual.layouts.dock import Dock
from textual.message import Message
from .tmux import GridArea, parse_layout
from logging import PlaceHolder
from typing import Iterable, List
from rich.console import RenderableType
from rich.markdown import Markdown
from rich.padding import PaddingDimensions
from rich.style import Style, StyleType
from rich.text import Text
from rich.panel import Panel
import subprocess
from textual import events
from textual.app import App
from textual.geometry import Offset, Region, Size
from textual.layout import Layout, WidgetPlacement
from textual.view import View
from textual.widget import Widget
from textual.widgets import Static
from textual.widgets import Placeholder
from textual.views import DockView
from textual.message import MessageTarget
from fuzzyfinder.main import fuzzyfinder

class InputChanged(Message):
    def __init__(self, sender: MessageTarget, value: str) -> None:
        self.value = value
        super().__init__(sender)

class FuzzyFinder(DockView):
    def __init__(self, candidates: List[str], name: str | None = None) -> None:
        super().__init__(name=name)
        self.picker = Picker()
        self.input = TextInput()
        self.candidates = candidates
        self.picker.set_entries(candidates)

    async def handle_input_changed(self, event: InputChanged):
        res = fuzzyfinder(event.value, self.candidates)
        self.picker.set_entries(list(res))

    async def on_mount(self, event: events.Mount) -> None:
        await self.dock(self.picker, edge="top", size=round(self.console.height*0.9))
        await self.dock(self.input, edge="bottom")
        return await super().on_mount(event)


class Picker(Widget):
    def __init__(self, name: str | None = None) -> None:
        super().__init__(name=name)
        self._entries = []
        self.selected_entry = 0

    async def on_key(self, event: events.Key):
        if event.key == "up":
            self.selected_entry = (self.selected_entry-1) % len(self._entries)
        elif event.key == "down":
            self.selected_entry = (self.selected_entry+1) % len(self._entries)
        self.refresh()

    def set_entries(self, entries: Iterable[str]):
        self._entries = entries
        self.selected_entry = 0
        self.refresh()

    def render(self) -> RenderableType:
        # TODO: Change bgcolor to something more visisble
        texts = [Text(x, Style(bgcolor="white") if i == self.selected_entry else "") for i, x in enumerate(self._entries)]
        joiner = Text("\n")
        res = joiner.join(texts)
        return Panel(res)

class TextInput(Widget):
    def __init__(self, name: str | None = None) -> None:
        super().__init__(name=name)
        self.prompt = ">> "
        self.value = ""
        self._cursor_position = 0
        self.cursor = ("|", Style(blink=True, color="white", bold=True))

    def render(self) -> RenderableType:
        segments = [
            self.prompt,
            self.value[:self._cursor_position],
            self.cursor,
            self.value[self._cursor_position:]
        ]
        text = Text.assemble(*segments)
        return Panel(text)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self._cursor_position = max(0, self._cursor_position-1)
        elif event.key == "right":
            self._cursor_position = min(len(self.value), self._cursor_position+1)
        elif event.key == "home":
            self._cursor_position = 0
        elif event.key == "end":
            self._cursor_position = len(self.value)
        elif event.key == "ctrl+h":  # Backspace
            if self.value and self._cursor_position > 0:
                self.value = self.value[:self._cursor_position-1] + self.value[self._cursor_position:]
                self._cursor_position -= 1
            await self.emit(InputChanged(self, self.value))
        elif event.key == "delete":
            if self.value and self._cursor_position < len(self.value):
                self.value = self.value[:self._cursor_position] + self.value[self._cursor_position+1:]
            await self.emit(InputChanged(self, self.value))
        elif event.key in string.printable:
            self.value += event.key
            self._cursor_position += 1
            await self.emit(InputChanged(self, self.value))
        self.refresh()

class Pane(Static):
    def __init__(self, pos: GridArea, text: Text) -> None:
        super().__init__(text)
        self.pos = pos

class PaneLayout(Layout):
    def __init__(self, scale: float) -> None:
        super().__init__()
        self.panes: List[Pane] = []
        self.scale = scale

    def add_pane(self, pane: Pane):
        self.panes.append(pane)

    def get_widgets(self) -> Iterable[Widget]:
        return self.panes

    def arrange(self, size: Size, scroll: Offset) -> Iterable[WidgetPlacement]:
        placements = []
        for pane in self.panes:
            # This assumes horizontal scaling only
            x1 = round(pane.pos.col_start * self.scale)
            y1 = pane.pos.row_start
            x2 = round(pane.pos.col_end * self.scale)
            y2 = pane.pos.row_end
            # crop any overflowing content
            region = Region.from_corners(x1, y1, x2, y2).intersection(size.region)
            placements.append(WidgetPlacement(region, pane))
        return placements

class MyApp(App):
    async def on_key(self, event: events.Key) -> None:
        await super().on_key(event)
        await self.fuzzy_finder.input.on_key(event)
        await self.fuzzy_finder.picker.on_key(event)

    async def on_load(self, event: events.Load) -> None:
        """Bind keys with the app loads (but before entering application mode)"""
        await self.bind("q", "quit", "Quit")
        sessions = subprocess.getoutput("tmux list-sessions -F '#S'").splitlines()
        self.fuzzy_finder = FuzzyFinder(sessions)

    async def on_mount(self, event: events.Mount) -> None:
        layout = PaneLayout(0.8)
        layout_str = subprocess.getoutput("tmux display-message -p -F '#{window_visible_layout}' -t lila:0")
        layouts = parse_layout(layout_str)
        for l in layouts:
            pane_content = subprocess.getoutput(f"tmux capture-pane -t {l.pane_id} -epN")
            layout.add_pane(Pane(l, Text.from_ansi(pane_content, no_wrap=True, end="")))
        panes = View(layout, name="panes")
        # TODO: Figure out how to keep the proportions on window resize
        await self.view.dock(self.fuzzy_finder, edge="left", size=round(self.console.size.width * 0.2))
        await self.view.dock(panes, edge="right")

MyApp.run(title="Simple App", log="textual.log")
