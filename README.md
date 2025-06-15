# Tiến Lên
[![CI](https://github.com/YOUR_GITHUB_USERNAME/Tien-Len/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/Tien-Len/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/YOUR_GITHUB_USERNAME/Tien-Len/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_GITHUB_USERNAME/Tien-Len)

This repository contains a simple command line implementation of the
Vietnamese card game **Tiến Lên** and a small Tkinter-based GUI.

## CLI version

To play in the terminal run:

```bash
python3 tien_len_full.py
```

The game logs actions to `tien_len_game.log`.

## GUI prototype

A very small graphical interface built with `tkinter` is provided in
`gui.py`. It displays your hand as clickable buttons and shows the last
combo on the pile. Opponents are played by the built‑in AI.

Start it with:

```bash
python3 gui.py
```

Select cards by clicking them and then press **Play Selected**. Press
**Pass** to skip your turn (subject to the first‑turn rule). AI turns
are handled automatically.

The GUI supports a few convenience features:

- Press **Enter** to play the currently selected cards or **Space** to pass.
- Resize the window or press **F11** to toggle full‑screen mode and the
  card buttons will scale accordingly.


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

