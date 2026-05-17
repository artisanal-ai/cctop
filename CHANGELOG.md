# Changelog

All notable changes to cctop are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-17

### Added
- Display Anthropic 5-hour and 7-day usage quota bars in the monitor header,
  fetched via the OAuth usage endpoint (token resolved from
  `CLAUDE_CODE_OAUTH_TOKEN`, macOS keychain, or `~/.claude/.credentials.json`).
- `--quota-refresh` CLI option to control the quota poll interval
  (default `120.0` seconds).

### Changed
- Renamed `--refresh` to `--data-refresh` for clarity now that two reload
  intervals exist. Update any scripts that pass `--refresh`.

## [0.1.1] - 2026-04-29

### Added
- Windows support via the cross-platform `blessed` library; cctop now runs on
  macOS, Linux, and Windows. CI runs `make check` on `windows-latest`.

### Fixed
- JSONL and meta files are now read with `encoding="utf-8"` so Windows no
  longer falls back to cp1252 and corrupts non-ASCII content.
- Session picker no longer crashes on JSONL stubs without a `cwd` record;
  `Session.Ref.project` falls back to the parent directory name.

## [0.1.0] - 2026-04-24

### Added
- Initial release: interactive CLI monitoring tool for Claude Code sessions
  that parses JSONL files from `~/.claude/projects/` and renders a live
  terminal dashboard.
- Per-subagent breakdown of token usage (input, output, cache write, cache
  read), cost, and tool calls with success rate.
- Session picker with scroll/windowing for long lists and a `(cursor/total)`
  position counter.
- Project name resolution from JSONL `cwd` rather than the encoded directory
  name, preserving project names that contain `.`.
- Polished README with demo GIF.
