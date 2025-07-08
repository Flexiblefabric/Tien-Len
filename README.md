# Tiến Lên
[![CI](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml/badge.svg)](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Flexiblefabric/Tien-Len/branch/main/graph/badge.svg)](https://codecov.io/gh/Flexiblefabric/Tien-Len)

This repository contains a simple command line implementation of the
Vietnamese card game **Tiến Lên**. It comes with a Pygame graphical
interface implemented in the `tienlen_gui` package and can be launched
with `python -m tienlen_gui`.

This project requires **Python 3.8** or later.

## Installation

Install the project with `pip` to make the Pygame GUI entry point available:

```bash
pip install .
```

For development you can use the editable mode instead:

```bash
pip install -e .
```

After installation launch the Pygame GUI with `tien-len` or start the CLI via `tien-len-cli`.

## CLI version

To play in the terminal run:

```bash
python3 tien_len_full.py [--ai Easy|Normal|Hard|Expert|Master] \
                        [--personality aggressive|defensive|balanced|random] \
                        [--lookahead] [--depth N]
```
After installation the same game can be started with the `tien-len-cli` command.

The optional `--ai` flag selects the AI difficulty (default is `Normal`).
Use `--personality` to choose how boldly opponents play and `--lookahead`
to enable the extra search step used by the AI.  The game logs actions to
`tien_len_game.log`. Log rotation keeps the file from growing
indefinitely by capping it at roughly 1&nbsp;MB with a few backups.

## Card notation

Cards are written as ``<rank><symbol>`` (e.g. ``7♣``). When creating a
``Card`` instance, supply the arguments as ``(suit, rank)``.

## Pygame GUI

The graphical interface implemented in the `tienlen_gui` package renders the
table using sprites and simple animations.

Start the Pygame interface with:

```bash
python -m tienlen_gui
```

Select cards by clicking them and then press **Play Selected**. Press
**Pass** to skip your turn (subject to the first‑turn rule). AI turns
are handled automatically.

### Pygame GUI features

- Sprite-based interface with simple animations.
- Animated card dealing at the start of each game.
- Press **F11** to toggle full-screen.
- Sprites and layout adapt automatically when the window is resized.
- Press **Enter** or **Space** for the usual shortcuts.
- Settings and menu overlays are provided.
- A dedicated *House Rules* screen lets you toggle optional rules.
  The *Flip Suit Rank* rule reverses suit ordering and can only be
  enabled from the main menu.
- On-screen **Play**, **Pass** and **Undo** buttons between your hand and the pile.
- Optional player avatars loaded from `assets/avatars/`.
- A small scoreboard at the top centre lists each player's remaining card count
  and ranking in a 14&nbsp;pt font.
- A game log beside the scoreboard records the last four actions using a 12&nbsp;pt
  font and highlights the newest entry.
- A compact score panel showing total wins can be toggled with the **S** button
  in the top-left corner.

### AI personality and lookahead

The **Options** menu exposes additional AI behaviour settings.  The
*AI Personality* selector cycles through **aggressive**, **defensive**,
**balanced** and **random** styles, altering how boldly opponents play.
The *Lookahead* toggle makes the AI consider the next turn before
committing to a move.

### House Rules

The *House Rules* screen contains optional rule switches:

- **Allow 2 in straights** – permits sequences containing the rank 2.
- **“Chặt” bomb** – four-of-a-kind bombs can always beat a single 2.
- **Chain cutting** – lets a higher sequence interrupt an existing one.
- **Tứ Quý hierarchy** – bombs outrank each other by rank.
- **Flip Suit Rank** – reverses suit order so Hearts outranks Spades.

All of these preferences persist between sessions via the `options.json`
file.

Displaying card images requires the **Pillow** library, which is
included in `requirements.txt`. Install dependencies (including Pillow
for image support) with:

```bash
pip install -r requirements.txt
```

### Showing card images

If an `assets/cards` directory containing PNG card images is present next to
the `tienlen_gui` package, the interface will show graphical cards instead of simple
text buttons. The repository ships with the required files (stored in
`assets/cards/`):

- `card_back.png` for the back of a card
- `red_joker.png` and `black_joker.png` for jokers (optional)
- 52 images named like `ace_of_spades.png` or `10_of_hearts.png`

Run the Pygame GUI from the project root so it can locate `assets/`. If any
images are missing, the program will fall back to text and print a list
of missing files.

Additional assets can be organised in subdirectories:

- `assets/card_backs/` for alternative card backs.
- `assets/tables/` for table textures.
- `assets/music/` for background tracks.
- `assets/avatars/` for optional player avatars (initials are shown if no image is found).

Table textures will be tiled to fill the screen and can be switched at
runtime from the graphics settings menu.

## Optional sound effects

Simple sound support is provided via the `pygame` mixer. Install
`pygame` to enable it. If the mixer fails to initialise, the game
silently skips all audio. Set the environment variable
`SDL_AUDIODRIVER=dummy` (or any invalid driver) before launching to
disable sound explicitly. Place additional `.mp3` files in
`assets/music/` to make them selectable as background tracks.


## TODO

- Networked multiplayer mode for remote games.
- Replay system to review finished rounds.
- Achievements and statistics tracking.
- More house rules and customisable card sets.
- Mobile-friendly controls and interface scaling.
- Animated bomb and combo effects.
- Online leaderboards for high scores.
- Hot-seat local multiplayer support.

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
`tienlen_gui/*.py` under the `omit` section.

## Debugging

Launch the CLI or Pygame GUI under the Python debugger to step through
game logic:

```bash
python -m pdb tien_len_full.py
# or for the graphical version
python -m pdb -m tienlen_gui
```

If the optional `pgdb` package is installed, it may be used in the same
way to get a prettier interface.

## License

This project is licensed under the [MIT License](LICENSE).

