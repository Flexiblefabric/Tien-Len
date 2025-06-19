# Tiến Lên
[![CI](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml/badge.svg)](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Flexiblefabric/Tien-Len/branch/main/graph/badge.svg)](https://codecov.io/gh/Flexiblefabric/Tien-Len)

This repository contains a simple command line implementation of the
Vietnamese card game **Tiến Lên**. It comes with a Pygame graphical
interface implemented in `pygame_gui.py`.

## Installation

Install the project with `pip` to make the Pygame GUI entry point available:

```bash
pip install .
```

For development you can use the editable mode instead:

```bash
pip install -e .
```

After installation launch the Pygame GUI with `tien-len`.

## CLI version

To play in the terminal run:

```bash
python3 tien_len_full.py [--ai Easy|Normal|Hard]
```

The optional `--ai` flag selects the AI difficulty (default is `Normal`).
The game logs actions to `tien_len_game.log`.

## Card notation

Cards are written as ``<rank><symbol>`` (e.g. ``7♣``). When creating a
``Card`` instance, supply the arguments as ``(suit, rank)``.

## Pygame GUI

The graphical interface implemented in `pygame_gui.py` renders the
table using sprites and simple animations.

Start the Pygame interface with:

```bash
python3 pygame_gui.py
```

Select cards by clicking them and then press **Play Selected**. Press
**Pass** to skip your turn (subject to the first‑turn rule). AI turns
are handled automatically.

### Pygame GUI features

- Sprite-based interface with simple animations.
- Press **F11** to toggle full-screen.
- Sprites and layout adapt automatically when the window is resized.
- Press **Enter** or **Space** for the usual shortcuts.
- Settings and menu overlays are provided.
- On-screen **Play**, **Pass** and **Undo** buttons between your hand and the pile.

Displaying card images requires the **Pillow** library, which is
included in `requirements.txt`. Install dependencies (including Pillow
for image support) with:

```bash
pip install -r requirements.txt
```

### Showing card images

If an `assets` directory containing PNG card images is present next to
`pygame_gui.py`, the interface will show graphical cards instead of simple
text buttons. The repository ships with the required files:

- `card_back.png` for the back of a card
- `red_joker.png` and `black_joker.png` for jokers (optional)
- 52 images named like `ace_of_spades.png` or `10_of_hearts.png`

Run the Pygame GUI from the project root so it can locate `assets/`. If any
images are missing, the program will fall back to text and print a list
of missing files.

Optionally place a small image `table_img.png` in the `assets` directory
to serve as the background of the playing area. The GUI will load this
file automatically and tile the texture to fill the screen, resizing it
whenever the window size changes.

## Optional sound effects

Simple sound support is provided via the `pygame` mixer. Install
`pygame` to enable it. If the mixer fails to initialise, the game
silently skips all audio. Set the environment variable
`SDL_AUDIODRIVER=dummy` (or any invalid driver) before launching to
disable sound explicitly.


## Running tests

Install requirements first:

```bash
pip install -r requirements.txt
```

Run the test suite with coverage enabled:

```bash
coverage run -m pytest
coverage xml
```

Tests that exercise the graphical interfaces require the optional
`Pillow` and `pygame` libraries. Pytest will automatically skip these
tests when the dependencies are not available.

Coverage statistics exclude the GUI module because automated testing of
its interface is impractical. The `.coveragerc` file lists
`pygame_gui.py` under the `omit` section.

## Debugging

Launch the CLI or Pygame GUI under the Python debugger to step through
game logic:

```bash
python -m pdb tien_len_full.py
# or for the graphical version
python -m pdb pygame_gui.py
```

If the optional `pgdb` package is installed, it may be used in the same
way to get a prettier interface.

## License

This project is licensed under the [MIT License](LICENSE).

