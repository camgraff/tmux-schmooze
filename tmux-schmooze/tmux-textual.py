from .tmux import GridArea, parse_layout
from logging import PlaceHolder
from typing import Iterable, List
import rich
from rich.console import RenderableType
from rich.markdown import Markdown
from rich.padding import PaddingDimensions
from rich.style import StyleType
from rich.text import Text
import subprocess
from textual import events
from textual.app import App
from textual.geometry import Offset, Region, Size
from textual.layout import Layout, WidgetPlacement
from textual.view import View
from textual.widget import Widget
from textual.widgets import Static
from textual.widgets import Placeholder

class Pane(Static):
    def __init__(self, pos: GridArea, text: Text) -> None:
        super().__init__(text)
        self.pos = pos

class PaneLayout(Layout):
    def __init__(self) -> None:
        super().__init__()
        self.panes: List[Pane] = []

    def add_pane(self, pane: Pane):
        self.panes.append(pane)

    def get_widgets(self) -> Iterable[Widget]:
        return self.panes

    def arrange(self, size: Size, scroll: Offset) -> Iterable[WidgetPlacement]:
        placements = []
        for pane in self.panes:
            region = Region.from_corners(pane.pos.col_start, pane.pos.row_start, pane.pos.col_end, pane.pos.row_end)
            placements.append(WidgetPlacement(region, pane))
        return placements

class MyApp(App):
    async def on_load(self, event: events.Load) -> None:
        """Bind keys with the app loads (but before entering application mode)"""
        await self.bind("b", "view.toggle('sidebar')", "Toggle sidebar")
        await self.bind("q", "quit", "Quit")

    async def on_mount(self, event: events.Mount) -> None:
        layout = PaneLayout()
        layout_str = subprocess.getoutput("tmux display-message -p -F '#{window_visible_layout}' -t lila:0")
        layouts = parse_layout(layout_str)
        for l in layouts:
            pane_content = subprocess.getoutput(f"tmux capture-pane -t {l.pane_id} -epN")
            layout.add_pane(Pane(l, Text.from_ansi(pane_content)))
        layout.require_update()
        view = View(layout, name="panes")
        await self.view.dock(view, edge="right", size=50)
        # await self.view.dock(Placeholder(), edge="left", size=50)

MyApp.run(title="Simple App", log="textual.log")
