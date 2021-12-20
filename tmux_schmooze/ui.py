import string
from rich.control import Control
from rich.segment import ControlType, Segment, Segments
from textual.driver import Driver
from textual.layouts.dock import Dock
from textual.message import Message
from . import tmux
from logging import PlaceHolder
from typing import Iterable, List, Optional, Type, cast
from rich.console import Console, RenderableType
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

class SelectedEntryChanged(Message):
    def __init__(self, sender: MessageTarget, value: tmux.Target) -> None:
        self.value = value
        super().__init__(sender)

class FuzzyFinder(DockView):
    def __init__(self, candidates: List[tmux.Target], name: str | None = None) -> None:
        super().__init__(name=name)
        self.picker = Picker()
        self.input = TextInput()
        self.candidates = candidates

    async def on_key(self, event: events.Key):
        await self.input.on_key(event)
        await self.picker.on_key(event)

    async def handle_input_changed(self, event: InputChanged):
        res = fuzzyfinder(event.value, self.candidates, accessor=lambda x : x.name)
        await self.picker.set_entries(list(res))

    async def on_mount(self, event: events.Mount) -> None:
        await super().on_mount(event)
        await self.focus()
        await self.dock(self.picker, edge="top", size=round(self.console.height*0.9))
        await self.dock(self.input, edge="bottom")
        await self.picker.set_entries(self.candidates)


class Picker(Widget):
    def __init__(self, name: str | None = None) -> None:
        super().__init__(name=name)
        self._entries: List[tmux.Target] = []
        self._selected_entry_index = 0

    @property
    def selected_entry(self) -> tmux.Target:
        return self._entries[self._selected_entry_index]

    async def on_key(self, event: events.Key):
        if event.key == "up":
            self._selected_entry_index = (self._selected_entry_index-1) % len(self._entries)
            await self.emit(SelectedEntryChanged(self, self.selected_entry))
        elif event.key == "down":
            self._selected_entry_index = (self._selected_entry_index+1) % len(self._entries)
            await self.emit(SelectedEntryChanged(self, self.selected_entry))
        elif event.key == "enter":
            tmux.attach_session(self.selected_entry.id)

        self.refresh()

    async def set_entries(self, entries: List[tmux.Target]):
        # TODO: Test with 0 entries, I think things will break
        self._entries = entries
        self._selected_entry_index = 0
        await self.emit(SelectedEntryChanged(self, self.selected_entry))
        self.refresh()

    def render(self) -> RenderableType:
        # TODO: Change bgcolor to something more visisble
        texts = [Text(x.name, Style(bgcolor="white") if i == self._selected_entry_index else "") for i, x in enumerate(self._entries)]
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
    def __init__(self, pos: tmux.PaneArea, text: Text) -> None:
        super().__init__(text)
        self.pos = pos

class PaneLayout(Layout):
    def __init__(self, scale: float) -> None:
        super().__init__()
        self.panes: List[Pane] = []
        self.scale = scale
    
    def reset(self) -> None:
        self.panes = []
        return super().reset()

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

class UI(App):
    def __init__(self, target_type: tmux.TargetType, console: Console | None = None, screen: bool = True, driver_class: Type[Driver] | None = None, log: str = "", log_verbosity: int = 1, title: str = "Textual Application"):
        super().__init__(console=console, screen=screen, driver_class=driver_class, log=log, log_verbosity=log_verbosity, title=title)
        targets = tmux.list_targets(target_type)
        self.fuzzy_finder = FuzzyFinder(targets)
        self.panes = View(PaneLayout(0.8), name="panes")
        
    async def handle_selected_entry_changed(self, event: SelectedEntryChanged):
        self.panes.layout.reset()
        self.set_layout(event.value.id)
        await self.panes.refresh_layout()

    def set_layout(self, id: str):
        layout = tmux.get_layout(id)
        for area in layout:
            pane_content = subprocess.getoutput(f"tmux capture-pane -t {area.pane_id} -epN")
            cast(PaneLayout, self.panes.layout).add_pane(Pane(area, Text.from_ansi(pane_content, no_wrap=True, end="")))

    async def on_mount(self, event: events.Mount) -> None:
        # TODO: Figure out how to keep the proportions on window resize
        await self.view.dock(self.fuzzy_finder, edge="left", size=round(self.console.size.width * 0.2))
        await self.view.dock(self.panes, edge="right")

if __name__ == "__main__":
    UI.run(title="tmux schmooze", log="textual.log")
