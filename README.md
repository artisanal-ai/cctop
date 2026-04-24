# cctop

htop for Claude Code sessions — per-agent token usage, cost, and tool call monitoring.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (tested with v0.11.7)
- [Claude Code](https://claude.com/product/claude-code) (tested with v2.1.119)

## Install

```bash
uv tool install git+https://github.com/artisanal-ai/cctop
```

## Usage

```
Usage: cctop [OPTIONS]

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --refresh        FLOAT    Data reload interval in seconds [default: 2.0]     │
│ --fps            INTEGER  View render frames per second [default: 10]        │
│ --version                 Show version and exit                              │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Development

```bash
git clone git@github.com:artisanal-ai/cctop.git
cd cctop
uv run cctop            # run locally
make check              # lint + typecheck + tests
make fix                # auto-fix linting issues
```
