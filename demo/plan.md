# cctop Pipeline Demo — Translate-a-Post (1 → 4 → 4 → 1)

## Context

`cctop` already shines on flat parallel fan-out, but its strongest story is **monitoring a multi-stage pipeline** — watching a "wave" of running pulses roll down the table as each stage completes and the next ignites. Today there is no recorded demo that shows this. We want a short, screen-recordable terminal demo, starting from a clean state, that drives Claude Code through a 4-stage pipeline (Extract → Translate → Review → Stitch, fan-out 1 → 4 → 4 → 1) with `cctop` watching live in a split pane.

Decisions:
- **Layout:** tmux, two panes side-by-side
- **Source text:** Paul Graham's *Maker's Schedule, Manager's Schedule* (a 2-paragraph excerpt)
- **Narration:** none — pure visual, captions in post if ever needed

## Artifacts to create

All under a single scratch dir, e.g. `~/Demos/cctop-pipeline-demo/`:

| Path | Purpose |
| --- | --- |
| `seed.md` | 2 short paragraphs from Paul Graham's essay (the input) |
| `prompt.md` | The orchestrator prompt pasted into Claude Code |
| `tmux-layout.sh` | One-shot script that opens the split-pane recording layout |
| `out/{es,ja,de,fr}/` | Created at runtime by Stage 2 / Stage 3 subagents |
| `final.md` | Created at runtime by Stage 4 |

No source files in the cctop repo are modified by this plan — this is a demo asset, not a code change.

## The pipeline (what `prompt.md` makes Claude do)

The wording of `prompt.md` is the load-bearing piece — it has to produce the exact fan-out shape on cctop's table. Critical phrasing: each stage that fans out must be dispatched **in a single message with N parallel `Task` tool calls**, otherwise Claude will sequence them and the wave effect is lost.

| Stage | Fan-out | Subagent type | Job |
| --- | --- | --- | --- |
| 1. Extract | 1 | Explore | Read `seed.md`, write `notes/keypoints.md` (3–5 bullets) |
| 2. Translate | 4 | general-purpose | One agent per language `{es, ja, de, fr}`, reads `seed.md` + `notes/keypoints.md`, writes `out/<lang>/translation.md` |
| 3. Review | 4 | general-purpose | One agent per language, reads its translation, rewrites idiomatic issues to `out/<lang>/review.md` (≤5 bullets) |
| 4. Stitch | 1 | general-purpose | Reads all 4 translations + reviews, writes side-by-side `final.md` |

Total cctop rows visible by end: 1 + 4 + 4 + 1 = **10 agent rows** plus the totals/session header. Costs telescope nicely (cheap → chunky → thinner → cheap). Tool mix differs per stage so the `t` toggle is rewarding.

## Recording sequence (from 0)

### A. Pre-flight (off-camera, once)

1. Ensure `cctop` is on PATH: `uv tool install git+https://github.com/artisanal-ai/cctop` (or `uv run cctop` from the repo).
2. `mkdir -p ~/Demos/cctop-pipeline-demo && cd ~/Demos/cctop-pipeline-demo`
3. Drop `seed.md` (2 paragraphs of *Maker's Schedule*) and `prompt.md` (the orchestrator prompt) into the dir.
4. Drop `tmux-layout.sh`. It should:
   - kill any session named `cctop-demo`
   - create a new session, set `default-directory` to the demo dir
   - split `-h` (50/50)
   - left pane: `claude` (Claude Code CLI)
   - right pane: `cctop --refresh 1.0` (faster reload than the 2.0 default makes the wave feel live)
   - attach
5. Resize the terminal window to ~**250 cols × 55 rows** *before* attaching tmux — cctop has 13 columns and needs ≥120 cols per pane to render without wrap.
6. Dry-run the whole thing once to confirm timing (~2–3 minutes wall clock) and that fan-out renders correctly.

### B. Recording (on-camera)

1. Start screen recording (QuickTime → New Screen Recording, or `Cmd+Shift+5`). Capture only the terminal window.
2. Run `./tmux-layout.sh`. The viewer sees:
   - Left: empty Claude Code prompt
   - Right: cctop session picker (the previous demo's session is at the top, or "no sessions found" on a truly fresh box)
3. **Left pane:** paste contents of `prompt.md`, press Enter.
4. Within ~1 s, a new session appears at the top of the picker on the right ("just now").
5. **Right pane:** `↑` to top, `Enter` to drill into the new session. Now in monitor view.
6. **Stage 1** fires — one Explore row appears, pulses `●`, completes `✓`. ~10–20 s.
7. **Stage 2** fires — 4 rows appear simultaneously, all pulse. *This is the headline shot.* ~30–60 s.
8. While Stage 2 is mid-flight, press `t` once to expand tool breakdowns. Lets the viewer see Read/Grep/Write differences. Press `t` again to collapse before Stage 3.
9. **Stage 3** fires — another bar of 4 pulses. ~20–40 s.
10. **Stage 4** fires — single stitcher row. ~10–20 s.
11. Totals row hits final ✓; total cost is visible. Hold ~3 s.
12. Stop recording.

### C. Post (optional)

- Trim head/tail.
- If you want title cards, add overlays at: t≈0 ("cctop — pipeline monitoring"), at Stage 2 entry ("4 translators in parallel"), at Stage 3 entry ("4 reviewers in parallel"), at end ($X total).

## Critical files referenced (read-only context)

- `src/cctop/views/monitor.py` — confirms the `t` keybinding toggles tools view and `↑/↓` scroll work as the demo assumes (`monitor.py:16-22`, `monitor.py:68-77`).
- `src/cctop/views/picker.py` — confirms picker keys (`Enter`/`→` select) the demo uses (`picker.py:14-21`).
- `src/cctop/app.py` — confirms `--refresh` flag flows through to `SessionMonitor` (`app.py:18-26`).
- `src/cctop/core/session.py` — confirms sessions are discovered from `~/.claude/projects/` and ordered by mtime, so the demo's new session lands at the top (`session.py:104-114`).

## Verification

End-to-end, before recording for real:

1. `tmux-layout.sh` opens cleanly and both panes are usable.
2. Pasting `prompt.md` in the left pane creates exactly **1 then 4 then 4 then 1** agent rows in cctop on the right (count the rows during each stage). If Stage 2 or 3 shows agents arriving one-by-one rather than as a batch, the prompt needs stronger "in a single message, dispatch 4 parallel Task calls" wording.
3. `t` expands and re-collapses tool sub-rows under each agent.
4. `out/{es,ja,de,fr}/translation.md`, `out/{es,ja,de,fr}/review.md`, and `final.md` all exist on disk after the run.
5. Totals row shows a non-zero cost and the success-rate column stays green.

If any of those fail, iterate on `prompt.md` (most common failure) or the dry-run terminal size (second most common — wrapping ruins the visual) before recording.
