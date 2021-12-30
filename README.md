# Tmux-schmooze
A `tmux choose-tree` replacement with fuzzy finding and enchanced configuration options.

## The Problem
tmux does not provide a great built-in method for previewing, searching, and managing sessions/windows. `tmux choose-tree` is decent but:
- there's no fuzzy finder
- the pane preview is different from the actual window layout
- remapping keys is cumbersome

## The Solution
`tmux-schmooze` provides a clean, highly configurable (or at least it will be soon) interface for interacting with tmux targets.

![demo](https://github.com/camgraff/tmux-schmooze/raw/master/demo.gif)


## Installation
Install via [pipx](https://pypa.github.io/pipx/)
```
pipx install tmux-schmooze
```

## Getting Started
Currently, `tmux-schmooze` provides the following commands:

```
tmux-schmooze windows
```
Choose from a list of windows

```
tmux-schmooze sessions
```
Choose from a list of sessions

## TODOS:
- [ ] more configurability for entry formats
- [ ] add mappings for deleting/renaming
- [ ] add ability to override mappings
- [ ] enable searching fields that don't appear in the picker (e.g. current directory)
- [ ] enable searching pane content and scrollback
- [ ] make available as a tmux plugin via tpm?
