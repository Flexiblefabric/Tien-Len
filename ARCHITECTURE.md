# Tiến Lên – Architecture Overview

This document summarizes the current high-level architecture and proposed seams for future work.

## Modules (high level)

```text
+--------------------+        +--------------------+
|  CLI (tienlen)     |        |  GUI (tienlen_gui) |
|  - argparse / I/O  |        |  - Pygame view     |
|  - game loop glue  |        |  - sprites/layout  |
+----------+---------+        +----------+---------+
           |                             |
           v                             v
       +---+-----------------------------+---+
       |           Game Engine               |
       |  - State (players, hands, pile)     |
       |  - Rules (validation, compare)      |
       |  - Turn/round sequencing            |
       +---+-----------------------------+---+
           |                             |
           v                             v
      +----+----+                   +----+----+
      |   AI    |                   |  Assets |
      | - policy|                   |  images |
      | - eval  |                   |  audio  |
      +---------+                   +---------+
```

## Data flow
1. **Input** (mouse/keyboard or CLI args) → controller logic maps events to **engine** actions.
2. **Engine** mutates a single authoritative **GameState**.
3. **Renderer** (GUI) observes state and redraws; **CLI** prints summaries.
4. **AI** requests a view of legal moves from **Rules**, evaluates them, selects one.
5. **Persistence**: options & profiles at `~/.tien_len/options.json`; saves at `~/.tien_len/saved_game.json` (add a `"schema": 1` field for migrations).

## Extension points
- **AI strategy**: separate *Evaluator* (scoring) from *Selector* (risk appetite via weighted biases).
- **Layout**: keep **linear row + responsive spacing** now; add optional fan/arc later for large hands.
- **Animations/SFX**: time-based animations (delta-ms), cache pre-rendered card surfaces (front/back, glow).

## Performance tips
- Call `convert()`/`convert_alpha()` on images at load.
- Cache card surfaces (including glow variants) instead of rebuilding each frame.
- Pre-render static text surfaces and reuse.

## Testing boundaries
- High-coverage unit tests for **Rules** and **Engine** (pure logic).
- Golden tests for AI: fixed hands → expected *distribution* of move classes.
- GUI smoke tests under headless Pygame (`SDL_VIDEODRIVER=dummy`); exclude from coverage.
