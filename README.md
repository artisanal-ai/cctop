# cctop

*Per-agent token usage, cost, and tool call monitoring for any Claude Code session.*

A Claude Code session can fan out into a swarm of subagents in seconds, and the meter starts spinning. cctop tails the live session log and breaks it down agent by agent — tokens in, tokens out, cache hits, dollars, tools called. So when the bill arrives, you know where it went.

![cctop demo](demo/cctop_demo.gif)

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (tested with v0.11.7)
- [Claude Code](https://claude.com/product/claude-code) (tested with v2.1.119)
- macOS/Linux

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
