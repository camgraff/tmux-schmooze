import string
from rich.control import Control
from rich.segment import ControlType
from .tmux import GridArea, parse_layout
from logging import PlaceHolder
from typing import Iterable, List
from rich.console import RenderableType
from rich.markdown import Markdown
from rich.padding import PaddingDimensions
from rich.style import StyleType
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

class TextInput(Widget):
    def __init__(self, name: str | None = None) -> None:
        super().__init__(name=name)
        self.prompt = ">> "
        self.value = ""
        self._cursor_position = 0

    def render(self) -> RenderableType:
        return Panel(self.prompt + self.value)

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
        elif event.key == "delete":
            if self.value and self._cursor_position < len(self.value):
                self.value = self.value[:self._cursor_position] + self.value[self._cursor_position+1:]
        elif event.key in string.printable:
            self.value += event.key
            self._cursor_position += 1
        self.refresh()

    def __rich__(self) -> RenderableType:
        self.console.show_cursor()
        # FIXME: Not working
        self.console.control(Control.move_to(0, 0))
        return super().__rich__()


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
        await self.input.on_key(event)

    async def on_load(self, event: events.Load) -> None:
        """Bind keys with the app loads (but before entering application mode)"""
        await self.bind("b", "view.toggle('sidebar')", "Toggle sidebar")
        await self.bind("q", "quit", "Quit")
        self.input = TextInput()

    async def on_mount(self, event: events.Mount) -> None:
        left = round(self.console.size.width * 0.2)
        grid = await self.view.dock_grid()
        grid.add_column("left", size=left)
        grid.add_column("right")
        grid.add_row("top", size=round(self.console.height*0.9))
        grid.add_row("bottom")

        grid.add_areas(
            picker="left,top",
            text_input="left,bottom",
            panes="right,top-start|bottom-end"
        )

        layout = PaneLayout(0.8)
        layout_str = subprocess.getoutput("tmux display-message -p -F '#{window_visible_layout}' -t lila:0")
        layouts = parse_layout(layout_str)
        for l in layouts:
            pane_content = subprocess.getoutput(f"tmux capture-pane -t {l.pane_id} -epN")
            layout.add_pane(Pane(l, Text.from_ansi(pane_content, no_wrap=True, end="")))
        panes = View(layout, name="panes")
        # TODO: Figure out how to keep the proportions on window resize
        grid.place(
            picker=Placeholder(),
            text_input=self.input,
            panes=panes
        )

MyApp.run(title="Simple App", log="textual.log")
