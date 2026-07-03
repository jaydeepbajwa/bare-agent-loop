# Changelog

All notable changes to this project are documented here.

## Unreleased

- Made relative `.env` discovery check the current directory first, then the target `--repo`.
- Expanded lint and compile checks to cover examples and scripts.
- Added explicit build-system metadata for editable installs.

## 0.1.0 - 2026-07-03

- Initial release of a stdlib-only terminal agent loop.
- Added raw OpenAI-compatible chat client, JSON action protocol, working memory,
  safe local tools, deterministic demo mode, tests, and GitHub Actions CI.
