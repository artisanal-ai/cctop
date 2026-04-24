# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cctop is an interactive CLI monitoring tool for Claude Code sessions — htop for Claude Code. It parses JSONL session files from `~/.claude/projects/` and shows per-subagent token usage, cost, and tool call breakdowns in a live terminal dashboard.

The project uses `uv` as its package manager and build tool, with Python 3.13+ as the minimum version requirement. Runtime dependencies: `rich>=13.0`, `typer>=0.9`.

## Key Commands

```bash
make check      # Run all quality checks (lint, typecheck, tests with coverage)
make lint       # Run ruff linter
make fix        # Auto-fix linting issues
make typecheck  # Run mypy strict
make test       # Run pytest with 80% minimum coverage
```

## Code Quality Standards

- Linting: ruff (E, F, I, N, W, B, C4, UP, PLE, PLW, RUF rules)
- Line length: 120 characters maximum
- Type checking: mypy strict mode; all functions must have type annotations
- Test coverage: minimum 80%
- Python version: 3.13

## Development Guidelines

**Core Principles:**
- Elegance over complexity — minimize code while preserving clarity and quality
- Single responsibility — each module, class, and function should do one thing well
- Pythonic, functional style — prefer pure functions, immutability, composition over inheritance
- Self-documenting code — no comments, no docstrings; let structure and naming convey intent
- Fail fast — minimal exception handling; let errors surface rather than hide them

**Models & Data:**
- All domain dataclasses are `frozen=True, slots=True` — immutability enforced at the type level
- No bad defaults — required fields have no defaults; optional fields use `None` not `""`
- Parse at the boundary — convert raw data (timestamps, model strings) to typed values at parse time, not in model properties
- Models should never need defensive guards for missing data — the parser must construct valid instances
- `SessionMonitor` and `SessionPicker` in views/ are the only mutable dataclasses (UI state by design)

**Code Style:**
- Type annotations required on all functions
- Modern Python patterns — union types (`str | None`), pattern matching where appropriate
- Constants colocated with usage, marked private with `_` prefix
- Flat structure — avoid deep nesting in code and directories
- All files must end with a newline character
- Test only public interfaces — if coverage drops on private code, it may be dead code

**Testing:**
- Test structure mirrors source — `tests/core/`, `tests/views/`
- Flat pytest style — functions, not classes
- Type-annotated test functions
- Clear, descriptive naming — `test_feature_scenario`
- Test our logic, not Python's — no tests for dataclass defaults, frozen enforcement, StrEnum values, or stdlib behavior
- Shared record builders in `tests/core/conftest.py`; mock helpers in `tests/conftest.py`

**Workflow:**
- Start fresh from main branch
- Research before implementing
- Self-review before committing
- Never commit broken tests
- Update CLAUDE.md when new patterns emerge

**Security & Privacy:**
- Everything is private by default
- Never commit secrets, API keys, or credentials to version control

## Architecture

**Module Structure:**
```
src/cctop/
  core/
    usage.py         # Usage dataclass (tokens, tools)
    models.py        # Model enum (pricing), ModelUsage type alias
    records.py       # Record parsing — AssistantRecord, UserRecord, ToolInvocation, etc.
    agents.py        # Agent dataclass, AgentStatus enum
    session.py       # Session, SessionRef — discovery, JSONL I/O, session assembly
  views/
    protocols.py     # View[T] protocol, Action enum, type aliases
    style.py         # Color constants
    keys.py          # Key enum, KeyListener (terminal raw mode)
    monitor.py       # SessionMonitor — session detail view
    picker.py        # SessionPicker — session list view
  app.py             # Typer entry point, wires core + views
```

**Dependency Chain:**
```
core/usage → core/models → core/records → core/agents → core/session → app
              views/protocols → views/keys → views/monitor, views/picker → app
```

No circular imports. `core/usage` and `views/protocols` are leaf modules.

**Key Design Decisions:**
- `core/` is pure domain logic — parsing, models, data; only `session.py` touches the filesystem
- `views/` owns all rendering and keyboard interaction
- `app.py` wires core and views together — no business logic
- No circular imports; leaf modules have no internal dependencies
- Return values over exceptions for control flow
- All behavior encapsulated in classes — no module-level functions