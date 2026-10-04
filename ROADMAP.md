# Tiến Lên 1.0 Roadmap

This roadmap supersedes the June 2025 roadmaps for pre-1.0 work. The detailed audit is in [docs/CURRENT_STATE_AUDIT.md](docs/CURRENT_STATE_AUDIT.md).

## 1.0 product definition

Tiến Lên 1.0 is a polished single-player desktop game against three AI opponents. "Polished" includes correctness, stability, distribution, and a coherent visual redesign. Existing visual assets are not automatically considered final.

Multiplayer, online services, leaderboards, achievements, and other expansion systems are post-1.0.

## Phase 0 — Baseline and stabilization

| Task | Status | Complexity |
| --- | --- | --- |
| Reapply PR #350 mixer guard to current main | Ready | Routine |
| Reproduce current CI failures | Next | Complex |
| Fix GUI/deal-animation test hang | Next | Complex |
| Normalize Python version declarations | Ready | Routine |
| Normalize test/dev dependency declarations | Ready | Routine |
| Consolidate coverage configuration | Ready | Routine |
| Correct package/README entry points | Done on audit branch | Routine |
| Verify PyInstaller entry path | Planned | Moderate |
| Establish clean Windows build smoke test | Planned | Moderate |

**Exit gate:** required CI is consistently green.

## Phase 1 — Rules conformance

| Task | Status |
| --- | --- |
| Choose and document the default Tiến Lên ruleset | Planned |
| Document optional house rules separately | Planned |
| Add pass-lockout/trick-state tests | Planned |
| Review bomb/slam behavior | Planned |
| Review double-sequence combinations | Planned |
| Review opening-card and subsequent-game behavior | Planned |
| Add deterministic full-game conformance tests | Planned |

**Exit gate:** the engine behavior is documented and covered by tests.

## Phase 2 — Gameplay and AI verification

| Task | Status |
| --- | --- |
| Repeated full-game playtests | Planned |
| AI difficulty calibration | Planned |
| AI personality differentiation review | Planned |
| Lookahead/minimax performance review | Planned |
| Hint quality review | Planned |
| Save/load/undo edge-case review | Planned |
| Game-over and restart-flow review | Planned |

**Exit gate:** complete games are reliable and AI behavior is credible.

## Phase 3 — Visual and interaction redesign

Treat this as a design-system project, not a collection of isolated cosmetic changes.

| Area | 1.0 objective |
| --- | --- |
| Table | Establish final table composition, hierarchy, and responsive zones |
| Cards | Finalize card scale, fan geometry, selection state, shadows, pile presentation |
| Opponents | Rework seating, avatars, hand presentation, status indicators |
| HUD | Simplify turn, card-count, score, and last-action information |
| Menus | Unify menu hierarchy, buttons, typography, spacing, and backgrounds |
| Controls | Make Play, Pass, Hint, Undo, Settings immediately legible |
| Feedback | Standardize hover, press, valid/invalid play, pass, win, and bomb feedback |
| Animation | Keep only animations that improve clarity or feel |
| Audio | Normalize effects/music behavior and volume controls |
| Game over | Create a polished end-of-game summary and restart path |
| Accessibility | Review readable type sizes, contrast, color-only indicators, and scaling |

**Exit gate:** the game has a coherent visual language at supported window sizes and visual regression tests are updated.

## Phase 4 — Packaging and release candidate

| Task | Status |
| --- | --- |
| Audit bundled asset provenance and attribution | Planned |
| Build Windows executable from clean environment | Planned |
| Verify bundled assets | Planned |
| Verify save/options paths | Planned |
| Verify audio-disabled fallback | Planned |
| Update screenshots and player-facing documentation | Planned |
| Run release checklist | Planned |

**Exit gate:** a clean machine can install/launch and complete a game.

## Phase 5 — Tiến Lên 1.0

- Version package as `1.0.0`.
- Tag `v1.0.0`.
- Publish the Windows build.
- Publish release notes.
- Move deferred ideas to the post-1.0 backlog.

## Post-1.0 backlog

- hot-seat multiplayer;
- network multiplayer;
- online leaderboards;
- achievements and deeper statistics;
- expanded replay tooling;
- additional AI experimentation;
- additional themes/card sets after the 1.0 visual system is stable.
