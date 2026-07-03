# Changelog

All notable changes to this project are documented here.

## 0.1.1 - 2026-07-03

### Fixed
- Facts stored via `remember` now reach the system prompt on the next step of
  the same run — previously memory was only read once at run start, so the
  prompt's promise of "durable observations that survive later steps"
  overstated within-run behavior.
- `--demo` outside a git clone (e.g. after a wheel install, which doesn't ship
  `examples/`) now exits with instructions instead of failing confusingly.

### Added
- Tests for the raw HTTP model client: every failure mode (auth error, network
  failure, unexpected response shape) must map to an error naming the setting
  to check.
- `scripts/render_demo_svg.py`: the README demo image is now generated from a
  real `--demo` run instead of being hand-drawn, so it cannot drift from
  actual behavior.

### Changed
- Made relative `.env` discovery check the current directory first, then the target `--repo`.
- Expanded lint and compile checks to cover examples and scripts.
- Added explicit build-system metadata for editable installs.

## 0.1.0 - 2026-07-03

- Initial release of a stdlib-only terminal agent loop.
- Added raw OpenAI-compatible chat client, JSON action protocol, working memory,
  safe local tools, deterministic demo mode, tests, and GitHub Actions CI.
