# cctop

htop for Claude Code sessions — per-agent token usage, cost, and tool call monitoring.

## Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/)
- macOS or Linux
- Claude Code installed (~/.claude/projects/)

## Install

```bash
uv tool install git+https://github.com/artizanal-ai/cctop
```

## Usage

```
Usage: cctop [OPTIONS]

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --refresh        FLOAT    Data reload interval in seconds [default: 2.0]     │
│ --fps            INTEGER  View render frames per second [default: 10]        │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Development

```bash
git clone git@github.com:artizanal-ai/cctop.git
cd cctop
uv run cctop            # run locally
make check              # lint + typecheck + tests
make fix                # auto-fix linting issues
```
