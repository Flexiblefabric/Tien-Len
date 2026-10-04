# Tiến Lên Current-State Audit

**Audit date:** 2026-10-04  
**Baseline:** `main` at `cb93fd132bff0a72b498ec1bad4283eff1b1c068`

## Executive summary

Tiến Lên is not an early prototype. It is a feature-rich pre-1.0 game with a working rules engine, CLI, Pygame GUI, AI, persistence, options, animation systems, audio support, profiles, and a substantial automated test suite.

The project is not yet release-ready. The current priorities are:

1. restore a consistently green test/CI baseline;
2. review game-rule fidelity and choose a canonical default ruleset;
3. complete a full visual/interaction redesign pass rather than treating the current assets as final;
4. verify packaging and distribution from a clean Windows environment;
5. reconcile documentation, configuration, asset attribution, and release metadata.

The goal for 1.0 is a polished single-player Tiến Lên game against three AI opponents. Multiplayer, online services, and other expansion features are post-1.0.

## Status legend

- **Implemented** — substantial working code exists.
- **Implemented / verify** — code and tests exist, but the project-wide failing CI baseline means release behavior still needs verification.
- **Partial** — infrastructure exists but the feature is incomplete or not presented as a finished player-facing system.
- **Deferred** — intentionally outside the 1.0 scope.

## Current feature inventory

| Area | Feature | Current state | 1.0 disposition |
| --- | --- | --- | --- |
| Core | 52-card deck, dealing, sorting | Implemented / verify | Keep |
| Core | Singles, pairs, triples, four-of-a-kind, straights | Implemented / verify | Keep; rules review required |
| Core | Opening-card logic | Implemented / verify | Keep; rules review required |
| Core | Passing and trick reset | Implemented but rules fidelity needs review | Rework if canonical rules require it |
| Core | Bomb / house-rule behavior | Partial / simplified | Define canonical behavior before rework |
| Core | Multiple rounds/trick history | Partial | Keep only what supports gameplay and UI |
| AI | Easy through Master difficulty tiers | Implemented / verify | Keep |
| AI | Personalities | Implemented / verify | Keep; calibrate by playtest |
| AI | Per-opponent configuration | Implemented / verify | Keep |
| AI | Lookahead / minimax path | Implemented / verify | Keep; calibrate and performance-test |
| Player aids | Hint system | Implemented / verify | Keep |
| Player aids | Undo | Implemented / verify | Keep |
| Persistence | JSON game-state serialization | Implemented / verify | Keep |
| Persistence | Save/load | Implemented / verify | Keep |
| Persistence | Profiles and win counts | Implemented / verify | Keep |
| Replay | Round-state and move-log infrastructure | Partial | Post-1.0 unless cheap to expose cleanly |
| GUI | Pygame desktop interface | Implemented / verify | Keep |
| GUI | Resizable layout and fullscreen | Implemented / verify | Keep |
| GUI | Human fan/arc hand layout | Implemented / verify | Keep; redesign may replace presentation |
| GUI | AI seating/layout | Implemented / verify | Keep |
| GUI | HUD, turn state, scoreboard, game log | Implemented / verify | Rework as part of visual system |
| GUI | Menus, settings, rules, profiles | Implemented / verify | Rework as part of visual system |
| GUI | Tutorial / how-to-play overlays | Implemented / verify | Keep; rewrite after rules signoff |
| Feedback | Animations | Implemented / verify | Rework and simplify where useful |
| Feedback | Sound effects | Implemented / verify | Keep; stabilize mixer behavior |
| Feedback | Background music | Implemented / verify | Keep only after attribution audit |
| Visual assets | Cards, card backs, tables, avatars, buttons, menus | Implemented asset library | Treat current set as source material, not final 1.0 design |
| Packaging | Python package entry points | Implemented with documentation drift | Fix and verify |
| Packaging | PyInstaller build script | Exists, not release-verified | Clean-machine smoke test required |
| Testing | Unit and GUI tests | 32 test modules | Keep |
| Testing | CI | Present but current `main` is failing | Blocker |
| Multiplayer | Hot-seat / network play | Not implemented | Deferred |
| Online | Leaderboards / online services | Not implemented | Deferred |
| Progression | Achievements / expanded stats | Not implemented | Deferred |

## Release blockers and risks

### 1. CI is not green

The two most recent CI runs on `main` both failed on Python 3.11 and 3.12. Historical pull-request notes repeatedly mention a hang around the deal-animation GUI test. The exact old Actions logs are no longer available, so the current failure must be reproduced in a fresh development environment.

**1.0 gate:** all required tests pass consistently on supported Python versions.

### 2. A later sound fix did not reach main

PR #350 added a defensive mixer-initialization check, but it was merged into a stale development branch rather than `main`. The branch has diverged from `main`; the four-line fix should be reapplied directly rather than merging the stale branch wholesale.

**1.0 gate:** reapply the fix with a focused regression test.

### 3. Canonical Tiến Lên rules are not yet defined

The current engine implements a specific mixture of rules and optional toggles. Some behavior is simplified. In particular, pass handling currently counts consecutive passes but does not explicitly lock a player out of the current trick after they pass. Bomb behavior is also broader/simpler than several common Tiến Lên variants, and double-sequence bombs are not represented as a distinct combination type.

This is not a routine bug fix because Tiến Lên has regional and house-rule variants.

**1.0 gate:** document the default ruleset, distinguish house rules from defaults, then write conformance tests before changing engine behavior.

### 4. The visual system should be considered unfinished

The codebase already contains a large visual asset library and multiple UI systems, but 1.0 polish may include reworking all visual elements: table, cards, menus, HUD, buttons, typography, spacing, animations, feedback, and game-over presentation.

This should be approached as a coherent visual system rather than incremental decoration.

**1.0 gate:** complete a visual design pass after core stability and rules signoff, then add/update visual regression coverage.

### 5. Packaging needs a clean-machine verification

The project defines `tien-len` as the CLI command and `tien-len-gui` as the GUI command. Earlier documentation reversed or invented entry points. The PyInstaller script directly targets `src/tienlen_gui/view.py`, a module that uses package-relative imports, so the release build path needs explicit verification.

**1.0 gate:** build and launch the Windows executable in a clean environment and verify assets, audio fallback, save paths, and startup.

### 6. Asset provenance needs a release audit

The repository includes card art, avatars, music, sound effects, table textures, and interface art. A bundled MIT license is present for at least part of the asset set, but 1.0 should not assume that one file documents the provenance and redistribution terms for every bundled asset.

**1.0 gate:** maintain an attribution/provenance record for every externally sourced asset retained in the release.

## Documentation and configuration drift

The following routine inconsistencies were found:

- README stated Python 3.10+, while `pyproject.toml` requires Python 3.11+.
- README described `tien-len` as the GUI command, but packaging defines it as the CLI command; the GUI command is `tien-len-gui`.
- README referenced the obsolete `tien_len_full.py` launch path.
- The old roadmaps still marked several implemented features as planned.
- The release checklist still targeted `v0.1.0`.
- Development dependency declarations differ between `requirements_dev.txt` and `pyproject.toml`.
- Coverage configuration is duplicated between `.coveragerc` and `pyproject.toml`.
- Formatting targets still reference Python 3.10 while runtime packaging requires 3.11+.

These should be normalized during stabilization.

## Architecture observations

The architecture is workable but concentrated in several large modules:

- `src/tienlen/game.py`: about 1,128 lines
- `src/tienlen_gui/view.py`: about 1,303 lines
- `src/tienlen_gui/overlays.py`: about 972 lines
- `src/tienlen_gui/animations.py`: about 633 lines

A broad rewrite is not required for 1.0. Refactor only where it reduces risk for rules correctness, testing, or the visual redesign. In particular, keep the game state/rules layer independent from presentation changes.

## Recommended 1.0 definition

Tiến Lên 1.0 is complete when a player can install or launch a Windows build, start a game against three AI opponents, understand the current state without developer knowledge, play repeated complete games under a documented default ruleset, use the core quality-of-life features, and reach a clear game-over state without crashes, hangs, invalid turn states, or packaging failures.

The release should feel visually intentional. Existing art and UI are not automatically considered final merely because they are implemented.

## Deferred until after 1.0

- network multiplayer;
- hot-seat multiplayer unless it proves trivial after 1.0 stabilization;
- online leaderboards;
- cloud accounts;
- achievement systems;
- major replay tooling;
- additional AI research beyond what is needed for credible opponents;
- feature additions that do not directly improve correctness, clarity, stability, or presentation.

## Recommended next task

Begin **STAB-1: Restore a trustworthy baseline**.

1. Reapply the PR #350 sound guard to `main` on a focused branch.
2. Reproduce and fix the CI/test hang.
3. Normalize Python/dependency/coverage configuration.
4. Add a packaging smoke test or release validation path.
5. Only after the baseline is green, begin the canonical-rules conformance pass.
