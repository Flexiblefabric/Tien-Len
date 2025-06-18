# Tiến Lên
[![CI](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml/badge.svg)](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Flexiblefabric/Tien-Len/branch/main/graph/badge.svg)](https://codecov.io/gh/Flexiblefabric/Tien-Len)

This repository contains a simple command line implementation of the
Vietnamese card game **Tiến Lên**.

Two graphical front-ends are available:

- A legacy Tkinter prototype in `gui.py`.
- A new Pygame interface in `pygame_gui.py`.

## Installation

Install the project with `pip` to make the GUI entry point available:

```bash
pip install .
```

For development you can use the editable mode instead:

```bash
pip install -e .
```

After installation launch the Tkinter GUI with `tien-len` or the new
Pygame version with `tien-len-pg`.

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

## GUI prototype

Two implementations exist. The original Tkinter version in `gui.py`
displays your hand as clickable buttons. A new Pygame rewrite in
`pygame_gui.py` renders the table using sprites and simple animations.

Start the Tkinter version with:

```bash
python3 gui.py
```

Launch the Pygame GUI with:

```bash
python3 pygame_gui.py
```

Select cards by clicking them and then press **Play Selected**. Press
**Pass** to skip your turn (subject to the first‑turn rule). AI turns
are handled automatically.

The GUI supports a few convenience features:

- Press **Enter** to play the currently selected cards or **Space** to pass.
- In the Tkinter version the card buttons resize when you resize the window
  or press **F11** for full‑screen. The Pygame interface now rebuilds its
  sprites whenever the window size changes or full‑screen is toggled.
- Adjust AI difficulty (Easy/Normal/Hard) from the **Options > Settings** dialog.
- Pick an AI personality (Aggressive/Defensive/Random) and toggle lookahead for
  Hard difficulty from the same dialog.

Displaying card images requires the **Pillow** library, which is
included in `requirements.txt`. Install dependencies (including Pillow
for image support) with:

```bash
pip install -r requirements.txt
```

### Showing card images

If an `assets` directory containing PNG card images is present next to
`gui.py`, the interface will show graphical cards instead of simple
text buttons. The repository ships with the required files:

- `card_back.png` for the back of a card
- `red_joker.png` and `black_joker.png` for jokers (optional)
- 52 images named like `ace_of_spades.png` or `10_of_hearts.png`

Run the GUI from the project root so it can locate `assets/`. If any
images are missing, the program will fall back to text and print a list
of missing files.

Optionally place a small image `table_bg.png` in the `assets` directory
to serve as the background of the playing area. The GUI will tile and
resize this image when the window is resized.

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

## License

This project is licensed under the [MIT License](LICENSE).

