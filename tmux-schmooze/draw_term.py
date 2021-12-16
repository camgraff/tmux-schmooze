import subprocess
import blessed
from .tmux import parse_layout

layout_str = subprocess.getoutput("tmux display-message -p -F '#{window_visible_layout}' -t lila:0")
layouts = parse_layout(layout_str)
term = blessed.Terminal()
with term.raw(), term.fullscreen():
    # TODO: try to add borders
    for layout in layouts:
        pane_content = subprocess.getoutput(f"tmux capture-pane -t {layout.pane_id} -epN")
        lines = pane_content.split("\n")
        y = layout.row_start
        x = layout.col_start
        for i, line in enumerate(lines):
            print(term.move_xy(x, y) + line, end='' if i == len(lines)-1 else '\n')
            y += 1


    term.inkey()
