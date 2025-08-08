# Release Checklist

Use this guide when tagging `v0.1.0` and shipping a Windows executable.

## Prep
- [ ] Run `pytest` and ensure all tests pass.
- [ ] Update version strings (e.g. in `pyproject.toml`) and commit.
- [ ] Refresh documentation and screenshots/GIFs as needed.

## Tag
- [ ] Create a git tag: `git tag v0.1.0`.
- [ ] Push tags: `git push --tags`.

## Build
- [ ] Build the Windows EXE with PyInstaller: `bash build_exe.sh`.
- [ ] Upload the executable to the GitHub release.

## Final
- [ ] Draft release notes and publish.
- [ ] Announce the release.
