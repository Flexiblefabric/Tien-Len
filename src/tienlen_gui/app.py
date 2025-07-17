"""Entry point for launching the Pygame GUI."""

from .view import GameView


def main() -> None:
    """Run the graphical version of the game."""
    GameView().run()


if __name__ == "__main__":
    main()
