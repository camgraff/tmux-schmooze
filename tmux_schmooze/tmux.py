from enum import Enum, auto
import functools
import re
import subprocess
from typing import List, NamedTuple, Tuple

class PaneArea(NamedTuple):
    col_start: int
    col_end: int
    row_start: int
    row_end: int
    pane_id: str

class TargetType(Enum):
    WINDOW = auto()
    SESSION = auto()

class Target(NamedTuple):
    """
    A session or window
    """
    name: str
    id: str

def _cmd(*args: str) -> List[str]:
    """
    Runs a tmux shell command and returns the output as a list of lines.
    """
    return subprocess.run(["tmux", *args], check=True, capture_output=True, text=True).stdout.splitlines()

def list_targets(target_type: TargetType) -> List[Target]:
    if target_type == TargetType.WINDOW:
        partial = functools.partial(_cmd, "list-windows", "-a", "-F")
        return [Target(name, id) for name, id in zip(partial("#{session_name}: #{window_name}"), partial("#{window_id}"))]
    if target_type == TargetType.SESSION:
        partial = functools.partial(_cmd, "list-sessions", "-F")
        return [Target(name, id) for name, id in zip(partial("#{session_name}"), partial("#{session_id}"))]
    raise ValueError(f"unknown target type: {target_type}")


def attach(target_id: str) -> None:
    subprocess.run(["tmux", "switch-client", "-t", target_id], check=True)

def capture_pane(id: str) -> str:
    return "\n".join(_cmd("capture-pane", "-t", id, "-epN"))

def get_layout(id: str) -> List[PaneArea]:
    """
    Gets the window layout for the passed id.
    id can be a session or window ID.
    """
    layout_str = subprocess.getoutput(f"tmux display-message -p -F '#{{window_visible_layout}}' -t '{id}'")
    return _parse_layout(layout_str)

def _parse_layout(s: str) -> List[PaneArea]:
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

    check_layout_found()

    res = []
    for layout in layouts:
        int_layout = [int("".join(x)) for x in layout]
        cols, rows, x, y, pane_id = int_layout
        res.append(PaneArea(x, x+cols, y, y+rows, f"%{pane_id}"))
    return res

if __name__ == "__main__":
    # layout = subprocess.getoutput("tmux display-message -p -F '#{window_visible_layout}' -t lila:0")
    # print(parse_layout(layout))
    print(_parse_layout("be00,183x44,0,0,3"))
    print(list_targets(TargetType.SESSION))
