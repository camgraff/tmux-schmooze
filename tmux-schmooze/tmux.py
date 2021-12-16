import re
import subprocess
from typing import List, NamedTuple

class GridArea(NamedTuple):
    col_start: int
    col_end: int
    row_start: int
    row_end: int
    pane_id: str


def parse_layout(s: str) -> List[GridArea]:
    # First item is the layout ID which we don't need
    layout_str = s.split(",", 1)[1]
    # print(layout_str)
    # _parse_layout(layout_str)
    # pass
    groups = []
    layout_strs = [[[]]]
    layouts = []

    def check_layout_found():
        if layout_strs and len(layout_strs[-1]) == 5:
            layouts.append(layout_strs[-1])
            layout_strs.pop()
            layout_strs.append([[]])
            return True
        return False

    for c in layout_str:
        if c in ("[", "{"):
            layout_strs.append([[]])
            groups.append(c)
        elif c in ("]", "}"):
            check_layout_found()
            groups.pop()
        elif c == "," or c == "x":
            if not check_layout_found():
                layout_strs[-1].append([])
        else:
            layout_strs[-1][-1].append(c)
    res = []
    for layout in layouts:
        int_layout = [int("".join(x)) for x in layout]
        cols, rows, x, y, pane_id = int_layout
        res.append(GridArea(x, x+cols, y, y+rows, f"%{pane_id}"))
    return res

if __name__ == "__main__":
    layout = subprocess.getoutput("tmux display-message -p -F '#{window_visible_layout}' -t lila:0")
    print(parse_layout(layout))
