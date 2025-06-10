# Tiến Lên

This repository contains a simple command line implementation of the 
Vietnamese card game **Tiến Lên** and a small GUI prototype.

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
