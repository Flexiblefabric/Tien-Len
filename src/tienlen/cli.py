"""Command line interface entry point for Tiến Lên."""

from .game import main as _game_main


def main() -> None:
    """Run the game via the CLI."""
    _game_main()


if __name__ == "__main__":
    main()
