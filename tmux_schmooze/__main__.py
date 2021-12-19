import click
from .ui import UI

def validate_target(ctx, param, value):
    if value not in ("sessions", "windows"):
        raise click.BadParameter(f"must be either 'sessions' or 'windows'")
    return value

@click.command()
@click.argument('target_type', callback=validate_target)
def entry_point(target_type: str):
    UI.run(target_type=target_type)

if __name__ == '__main__':
    entry_point()
