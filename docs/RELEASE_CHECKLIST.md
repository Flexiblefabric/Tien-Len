# Tiến Lên 1.0 Release Checklist

Use this checklist for the first stable `v1.0.0` release.

## Required gates

- [ ] Default Tiến Lên ruleset is documented.
- [ ] Required automated tests pass on supported Python versions.
- [ ] CI is green on the release commit.
- [ ] Repeated complete-game playtests pass without turn-state or game-over failures.
- [ ] Visual redesign/QA is signed off at supported window sizes.
- [ ] Asset provenance and attribution have been reviewed.
- [ ] Windows packaging has been smoke-tested on a clean environment.

## Prep

- [ ] Set project version to `1.0.0`.
- [ ] Confirm README launch/install instructions match package entry points.
- [ ] Confirm Python version declarations are consistent.
- [ ] Confirm save/options locations and schema behavior.
- [ ] Run the complete test suite.
- [ ] Run lint/format/type checks required for the release.
- [ ] Refresh screenshots and player-facing instructions.

## Build

- [ ] Build the Windows executable from the approved release commit.
- [ ] Launch the packaged executable on a clean Windows environment.
- [ ] Start and complete at least one full packaged game.
- [ ] Verify card, table, avatar, button, font, sound, and music assets.
- [ ] Verify the game works when audio initialization is unavailable.
- [ ] Verify save/load after relaunch.

## Tag and release

- [ ] Create tag `v1.0.0`.
- [ ] Push the tag.
- [ ] Create the GitHub release from the approved commit.
- [ ] Attach the verified Windows build.
- [ ] Publish concise release notes including known limitations.

## Final

- [ ] Verify the release download launches successfully.
- [ ] Move deferred features to the post-1.0 backlog.
- [ ] Record the release commit and build artifact details.
