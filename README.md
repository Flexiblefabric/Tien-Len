# Tiến Lên
[![CI](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml/badge.svg)](https://github.com/Flexiblefabric/Tien-Len/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Flexiblefabric/Tien-Len/branch/main/graph/badge.svg)](https://codecov.io/gh/Flexiblefabric/Tien-Len)

This repository contains a simple command line implementation of the
Vietnamese card game **Tiến Lên**. It comes with a Pygame graphical
interface implemented in the `tienlen_gui` package. Launch the GUI after
installation with the `tien-len` command or run `python -m
tienlen_gui.view` while developing.

This project requires **Python 3.10** or later.

## Overview

Tiến Lên is a shedding‑type card game popular in Vietnam. Players take
turns discarding valid combinations until one person empties their hand.
This repository provides both a terminal version and a Pygame powered
GUI with simple animations, sound effects and optional house rules.

## Quick Start

Create a fresh virtual environment and install the project in editable mode:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

Install the pinned runtime libraries from `requirements.txt` (generated
from [requirements.md](requirements.md)) if you prefer manual
dependency management:

```bash
pip install -r requirements.txt
```

Launch the GUI or CLI using the provided entry points:

```bash
tien-len       # graphical interface
tien-len-cli   # command line version
```

The `examples/` directory contains small scripts demonstrating both modes.

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
tien-len  # or `python -m tienlen_gui.view`
```

Select cards by clicking them and then press **Play Selected**. Press
**Pass** to skip your turn (subject to the first‑turn rule). AI turns
are handled automatically.

### Pygame GUI features

- Sprite-based interface with simple animations.
- Animated card dealing at the start of each game.
- Press **F11** to toggle full-screen.
- Sprites and layout adapt automatically when the window is resized.
- Cards shrink slightly with smaller windows to prevent overlap.
- Press **Enter** or **Space** for the usual shortcuts.
- Settings and menu overlays are provided. Press **Esc** to open the menu,
  **M** for the main menu and **O** for the options screen.
- A dedicated *House Rules* screen lets you toggle optional rules.
  The *Flip Suit Rank* rule reverses suit ordering and can only be
  enabled from the main menu.
- On-screen **Play**, **Pass**, **Hint** and **Undo** buttons between your hand and the pile.
- Click **Hint** to automatically highlight a suggested play.
- Optional player avatars loaded from `assets/avatars/`.
- Player profiles with persistent win counts. Select a profile or create a new
  one from the **Switch Profile** button on the main menu. Profile data is
  stored alongside other settings in `~/.tien_len/options.json`.
- Per-player HUD panels show remaining cards, the last move and whose turn it is.
- Enable **Developer Mode** from the Options menu or press **F3** to reveal AI hands and move evaluations in these panels.
- A small scoreboard at the top centre lists each player's remaining card count
  and ranking in a 14&nbsp;pt font.
- A game log beside the scoreboard records the last four actions using a 12&nbsp;pt
  font and highlights the newest entry.
- A compact score panel showing total wins can be toggled with the **S** button
  in the top-left corner. The panel tracks wins separately for each profile.

### Saving and loading

Press the **Settings** button (or hit **Esc**) during a game to open the in-game
menu. Here you can **Save Game** to write the current match to
`~/.tien_len/saved_game.json` – the same directory that stores
`options.json`. Selecting **Load Game** from this menu restores the last saved
state so you can resume where you left off.

### AI personality and lookahead

The **Options** menu exposes additional AI behaviour settings.  The
*AI Personality* selector cycles through **aggressive**, **defensive**,
**balanced** and **random** styles, altering how boldly opponents play.
These styles now modify how scoring weights factor rank and finishing position, making each AI behave more distinctly.
The *Lookahead* toggle makes the AI consider the next turn before
committing to a move. A **Use Global AI** toggle at the bottom of this
screen decides whether the chosen difficulty and personality apply to
every opponent. Disabling it reveals an **AI Setup** button that opens a
panel listing each CPU player so you can configure their difficulty and
personality individually. Re-enabling the global option clears any
per-player overrides and hides the setup panel.

### House Rules

The *House Rules* screen contains optional rule switches:

- **Allow 2 in straights** – permits sequences containing the rank 2.
- **Chặt bomb** – bombs can trump any non-bomb hand.
- **Chain cutting** – longer sequences may interrupt a smaller one.
- **Tứ Quý hierarchy** – higher ranked bombs beat lower ones.
- **Flip Suit Rank** – reverses suit order so Hearts outranks Spades.

All of these preferences persist between sessions via the `options.json`
file.

Displaying card images requires the **Pillow** library, which is
included in `requirements.txt`. That file pins compatible versions of
all dependencies. Install them (including Pillow for image support) with:

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

## Building a standalone executable

The repository provides a `build_exe.sh` script that wraps PyInstaller. Run it from the project root after installing PyInstaller:

```bash
pip install pyinstaller
./build_exe.sh
```

The executable along with its assets will appear in the `dist/` directory.



## TODO

See [ROADMAP.md](ROADMAP.md) for status updates.

- Dynamic card spacing with responsive scaling implemented.
 - Card fan/arc layout for large hands (in progress).
- Improved AI personalities with distinct scoring; lookahead and hint system.
- Additional house rule toggles and custom card sets.
- Replay and save/resume systems.
- Player stats tracking, achievements and online leaderboards.
- Rendering performance optimizations with integrated animations.
- Animated bomb/combo effects with audio and music.
- Networked and hot-seat multiplayer support.

## Running tests

Install the pinned requirements first:

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

When running the tests on systems without a display, set the environment
variables ``SDL_VIDEODRIVER=dummy`` and ``SDL_AUDIODRIVER=dummy`` to
initialise Pygame in headless mode. The values used by the CI workflow
and provided in ``conftest.py`` ensure consistent behaviour.

### Continuous integration

All pull requests are validated by the **CI** workflow in
`.github/workflows/ci.yml`. Tests run on Ubuntu using Python 3.11 and
3.12 with Pygame configured for headless mode. Coverage results are
uploaded to Codecov.

## Project layout

```
src/           Python packages ``tienlen`` (CLI game logic) and ``tienlen_gui``
tests/         Unit tests for both modules
examples/      Small scripts showcasing the CLI and GUI
```

Assets for the GUI live under ``src/tienlen_gui/assets`` and are included
when building a wheel.

## Development

Install optional development tools and linters with:

```bash
pip install -e .[dev,test]
```

Run `pre-commit` once to set up the git hooks and format the code base:

```bash
pre-commit install
pre-commit run --all-files
```

## Debugging

Launch the CLI or Pygame GUI under the Python debugger to step through
game logic:

```bash
python -m pdb tien_len_full.py
# or for the graphical version
python -m pdb -m tienlen_gui.view
```

If the optional `pgdb` package is installed, it may be used in the same
way to get a prettier interface.

## Packaging & Distribution

Build a wheel using the standard `build` module:

```bash
python -m build
```

All GUI assets are included under `tienlen_gui/assets` thanks to the
``package-data`` setting in *pyproject.toml*. Inspect the wheel to verify:

```bash
unzip -l dist/tien_len-*.whl | grep assets | head
```

Install the wheel in a clean virtual environment and run both entry
points:

```bash
python -m venv venv
source venv/bin/activate
pip install dist/tien_len-*.whl
tien-len --help
tien-len-gui --help
```
## Contributing

Community contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on setting up a development environment, coding standards and the preferred workflow. The project uses **pre-commit** with Black, isort, flake8 and mypy to enforce style consistency.

## License

This project is licensed under the [MIT License](LICENSE).

