# Mock & Roll

*by Lumostage* — the stage configurator.

Browser-based planner for the Lumostage LED volume: lay out sets and vehicles, look through a
virtual camera, check reflections, and print shot sheets.

- **Run locally:** `pythonw serve.py` → http://127.0.0.1:8137/
- **Deploy:** push to GitHub → Cloudflare Pages + Access. See [docs/deploy.md](docs/deploy.md).
- **Spec / as-built notes:** [docs/brief.md](docs/brief.md)

The app is `index.html` (vanilla Three.js r128, bundled in `vendor/`); brand assets in `brand/`.

---

## Original build kit

Everything from the planning conversation, packaged for a Claude Code session.
Unpack this into the folder the session will run in — `docs/` and `.claude/`
should sit at the project root, alongside wherever `index.html` gets created.

## What's in here

```
docs/
  brief.md                              — the build brief. Source of truth. Read this first.
  reference/
    measurement-verification.xlsx       — every measurement, as-written vs. interpreted, flagged items
    measurement-sheet-blank.pdf         — the blank field sheet (for reference / re-measuring)
    measurement-sheet-filled-by-darcy.pdf — Darcy's completed scan (source for the numbers in the brief)
    photos/                             — 17 labeled reference photos of the physical stage/pieces
.claude/
  agents/
    spec-auditor.md                     — read-only subagent: checks the build against docs/brief.md
    qa-reviewer.md                      — read-only subagent: checks for bugs + the performance guardrails
```

## Before you start

1. **Permission mode**: use `acceptEdits` (`Shift+Tab` twice, or
   `claude --permission-mode acceptEdits`), not full bypass. This project only
   ever touches one HTML file — no reason to disable all safety checks for it.
2. **`git init`** the project and commit after each clean pass. Cheap insurance
   for an unattended run.

## Kickoff prompt

Paste something close to this rather than just "build the brief":

```
Read docs/brief.md. Build Phase 1 only (see "Feature set, by phase") —
don't start Phase 2/3 work even if there's time left.

After the initial build, and after any significant change:
1. Use the spec-auditor subagent against docs/brief.md
2. Use the qa-reviewer subagent for bugs and the performance guardrails
3. Fix what they flag yourself — don't let them edit
4. Run a headless-browser smoke test: load index.html, confirm it
   renders with no console errors
5. Repeat 1-4 until both subagents report clean and the smoke test passes
6. Stop there. Report what was built and any open questions.
```

## Known open items (not blocking Phase 1)

See the "Open items" section at the bottom of `docs/brief.md` for the full,
current list. As of this kit:
- Gap distance from the station platform edge to the subway car (v1 pairing) — not pinned down
- Whether any existing CAD/Blender/Unreal models exist for the pieces above — unconfirmed
- Rooftop set (all versions) and door box v2/v3 — deliberately deferred, not needed for Phase 1
