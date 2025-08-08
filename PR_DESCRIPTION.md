### What
Docs/templates PR to make the project more contributor-friendly and pave the way for AI personality refactors.

**Adds**
- `ARCHITECTURE.md` with high-level diagram and data-flow.
- `docs/AI_PERSONALITY_STRATEGY.md` describing the weighted-bias design (Evaluator vs Selector).
- `docs/RELEASE_CHECKLIST.md` for tagging `v0.1.0` and shipping a Windows EXE.
- Issue templates: bug, feature, rule clarification.
- `pull_request_template.md`.

**Does not change code paths** (safe to merge anytime).

### Why
- Lowers onboarding friction for contributors (and Future You).
- Locks in the AI personality approach (weighted biases) without coupling to current code.
- Preps the repo for screenshots/GIFs and a first tagged release.

### Follow-ups (separate PRs)
- Inject `weights` into the existing evaluator; split difficulty (search budget) from personality (bias).
- Add `"schema": 1` to save files and a migration shim.
- Add small UX touches: "thinking" pulse, last-move summary overlay, reduced-motion toggle.
