# UI pass 2: plan (from the critique of 2026-10-04, score 20/40)

Critique archive: `.impeccable/critique/2026-10-04T18-07-20Z__index-html.md`.
The user chose **all 5 issues**, **casting workflow first**, and a **top-down seat map** for the subway.
Line numbers refer to commit 58d7dbc. Re-grep the function names before editing.

Rule for every step: reuse the redesign's own parts (`details.grp`, `.seg`, `.subhead`, `.catItem`, `--focus`, `--accentFill`).
No inline styles, no new ad-hoc button styles.
Read `.claude/skills/impeccable/reference/craft-floor.md` before the first edit.

## Order of work (each step should be commit-sized)

### 1. Make cast members selectable (P1)
- `pickAt` (~L2397): when the hit object belongs to a host that has cast (`castOf(host).length`), prefer a pinned-person hit if one is on the ray.
  - Do this by raycasting the pinned figures first.
  - Alt-click picks the host.
- Name tags (`makeNameTag`, layer 1 sprites): add them to the pick list and map each one back to its person group.
- Cast panel rows (see step 2): click a filled spot to `selectObject(group)` its occupant.
  - The person inspector then shows "◂ Back to Subway Car", which reselects the host.
- Remove the "Select one to change its figure…" hint once that action is actually possible.

### 2. Seat map instead of the checkbox grid (P1)
- New `seatMapHTML(host)` replaces the checkbox body of `castHTML` (~L2808–2821).
  - Inline SVG, a top-down plan, sized to the inspector width (about 260 px).
  - Draw it from the existing spot data, so there is no new authoring: car outline from L×W, plus each spot's local x/z.
  - Subway: 6 bench bars, door gaps at ±7, standing spots as rings.
  - Car: 5 seat rectangles, with the front marked.
- **Spot states:**
  - Empty: outlined.
  - Filled: filled.
  - Filled with a role: filled in the role colour.
  - Selected occupant: focus ring.
- **Interaction:**
  - Click an empty spot: fill it.
  - Click a filled spot: select its occupant (step 1).
  - Shift-click a filled spot: empty it.
  - Hover or focus a spot: show its name ("Bench 1 · window side · 3", "Door 1 · pole").
- **Accessibility:**
  - Each spot is a `<button>` or `role=checkbox` with `aria-label` = spot name plus state.
  - Arrow keys move between spots.
  - Targets are at least 24 px (enlarge the hit area beyond the drawn shape).
- **Bulk actions:**
  - One `.seg` with three choices: **Empty · Seats · Everyone**. It shows "Custom" when the state matches none of them.
  - This replaces Fill seats / Fill all / Clear and the 14 "all/none" buttons.
  - Per-group all/none: click a group label on the map (a bench title) to toggle that bench.
- **Undo:**
  - Before any bulk change, snapshot `castOf(host)` (the spot ids plus each person's fields).
  - A toast reads "Filled 34 · Undo" (or "Cleared 34 · Undo") with an action button.
  - Keep a single undo slot only.
- **Labels:**
  - Rename the bench groups to "Bench 1 · cab side / window side". Check A/B against the geometry: A = +Z side?
  - The count line stays: "Cast · 34 of 37".
- **Keep the old checkboxes available behind `<details>` "List view"?** No: drop them, the map is the list.

### 3. Inspector with progressive disclosure (P1)
- Wrap the inspector sections in `details.grp` with a summary on the right.
- **Open by default:** the Position section.
- **Collapsed by default:** Cast, Doors, Reflections, Figure, Role, Placement, Fit (customFitHTML ~L2831).
  - Remember the open/closed state per section in `localStorage` (wrapped in try/catch).
  - If a person is selected, Role should be open by default.
- **Section summaries:**
  - "Cast · 34/37"
  - "Doors · closed"
  - "Reflections · on"
  - "Role · Hero A"
  - "Placement · auto"
- **Doors** becomes a `.seg` with Closed / Open, at the top just under Position: it is the quick state change.
- **Footer:** Duplicate / Remove sit in a sticky footer (`position:sticky; bottom:0` inside the inspector scroller).
- **Title:** drop the internal id. "Rolling Wall (rollWall_R)" becomes "Rolling wall · right" (~L2573).
- **Labels:** `fieldHTML` (~L2674) wraps label + input in a `<label>` so posX / posZ / rot get accessible names.

### 4. Role colour and name tag (P2)
- `personFieldHTML` (~L2715–2745):
  - The swatches become a `role=radiogroup`.
  - Each swatch is a `role=radio` with `aria-checked` and `aria-label` set to the colour name.
  - Selected = a checkmark glyph inside the swatch, not the focus ring.
  - Show the selected colour's name next to the swatch row ("Salmon · Hero A").
  - Swatches are 28 px or larger.
- **Name tag** is always enabled. Typing into it with no role set assigns the next unused role colour.
- 3D tags: bump the canvas font so tags read at about 12 px on screen.
- Elevation: change the label to "Height off floor", with placeholder "auto (on floor/deck)" and a small "Auto" reset button that appears when a manual value is set.

### 5. Consistency pass (P2)
- **Seat dropdown:** retire the legacy "Seat" dropdown (`seatFieldHTML` ~L2614–2631) for catalog people.
  - Keep `syncSeatedTo` only for the legacy `human_standing` entry (or migrate those to pins in `migrateConfig`).
- **Clear button:** cast "Clear" is gone (replaced by the `.seg`). Check that no other non-destructive action uses `.danger`.
- **Reflections:** the per-piece "Mirror the LED stage" sits under Reflections. Its summary shows "off (turned off in Settings)" when the global switch is off, so the two don't silently fight.
- **"This is a car" / front:**
  - "Front faces: Left (−X)" becomes "Front of car points: ◂ Left / Right ▸ / Toward camera / Away", a `.seg` with arrows.
- **Overlap banner** (~L4389):
  - Add a "Dismiss" × and a "why" line naming the two pieces.
  - Don't fire just because something was selected; fire only during or after a move.
  - Its colour gets an icon plus text (already ⚠).

### 6. LED drawer (P2), one model for each surface
- One table, one row per surface (Main wall, Ceiling, Rolling L, Rolling R). Each row has a select: **Off / Plate: … / 360° world**.
  - Today two places do this: 360° "Show on" (~L3936) and "What each surface shows" (~L3567). The table replaces both.
- Below the table:
  - `details.grp` "360° world": library, load, Seen from, Turn, Horizon, Brightness, transport.
  - `details.grp` "Flat plates": the plate pool.
- **Copy:** the PowerShell sentence (~L3933) moves to the Help sheet's "Adding your own 360° plates" section. The drawer says "From the shared library" or "Load a file (this session only)".
- **Warning:** on a local-file load, show a persistent chip, "360°: local file, not saved", in the drawer header until the file is replaced.

### 7. Help sheet (~L500–529)
Add four short sections:
- **Cast & seats:** map, click to fill, click to select, shift-click to empty, Undo.
- **Role colours.**
- **Height off floor:** auto vs manual.
- **360° worlds:** the per-surface table, plus the proxy script for staff.

### 8. Verify (one bounded round)
- Browser desktop + phone width. Select a cast member through the subway shell, use the map, Undo, the role radio via keyboard, and the LED table.
- `sh .claude/skills/impeccable/scripts/impeccable detect --json index.html` once.
- Re-run the critique to compare against 20/40.
- **Do not clear storage on 127.0.0.1:8137** (the user's real layout). Test items go in through the UI and come out the same way.
- Update `docs/brief.md` and commit with `-F`. The user runs `git push`.

## Cost notes for the next session
- Steps 1–3 are the core. Do them first and commit.
- Steps 4–7 are smaller edits.
- Skip the subagent review if usage is tight; the plan already carries the review findings.
