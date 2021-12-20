import click
from .ui import UI
from . import tmux

def validate_target(ctx, param, value) -> tmux.TargetType:
    if value == "sessions":
        return tmux.TargetType.SESSION
    if value == "windows":
        return tmux.TargetType.WINDOW
    raise click.BadParameter(f"must be either 'sessions' or 'windows'")

@click.command()
@click.argument('target_type', callback=validate_target)
def entry_point(target_type: tmux.TargetType):
    UI.run(target_type=target_type)

if __name__ == '__main__':
    entry_point()
