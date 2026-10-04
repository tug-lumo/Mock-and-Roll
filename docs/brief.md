# Mock & Roll (Lumostage Stage Configurator) — Build Brief

Sep 24, 2026 · @Tug Phipps

A browser-based, to-scale 3D configurator for the Lumostage stage — fixed main volume wall, movable rolling walls, ceiling, and hybrid set pieces (subway train car, station platform) — so blocking, clearances, and shot feasibility can be checked before committing crew and build time to a sequence.

## Stack recommendation

Build it as a single self-contained HTML file on vanilla **Three.js** (UMD build, pinned version, no bundler, no build step, no server). Runs from a double-clicked file or a USB stick, works with zero internet after first load, and any future maintainer opens one file to change it.

| Option | Verdict |
| --- | --- |
| **Three.js (vanilla)** | Recommended. Minimal renderer, largest ecosystem, MIT-licensed, tree-shakeable core; you hand-pick only what a stage layout tool needs (geometry, transform gizmo, raycasting) instead of carrying a game engine. |
| Babylon.js | Full engine (physics, GUI, XR, inspector) — all overhead this tool doesn't use. Heavier bundle, TypeScript-first, backed by Microsoft. Better fit if the tool later needs physics or VR walkthroughs; not needed for a blocking/fit-check tool. |
| PlayCanvas | Cloud-hosted visual editor — wrong shape for "local or browser use": it wants an account and a hosted project, not a file you hand off. |
| Unreal LED-volume/nDisplay plugins (e.g. marketplace LED Volume Designer tools) | This is the real deal for generating nDisplay-ready panel meshes, but it's Unreal-only, needs the Editor installed, and is built for pixel-accurate panel mapping — far more tool than a quick "does the train fit / can we frame this" check needs. Wrong tool for this brief; worth keeping in mind only if Lumostage later wants the configurator's layout to round-trip into the actual nDisplay config. |

Camera/object manipulation: small custom code — drag-the-piece-along-the-floor movement, the yaw ring and viewport navigation (see "As built (controls)"); `TransformControls` and `OrbitControls` are not used — no third-party UI kit needed.

**Hosting & rollout**: the single-file architecture doesn't change when it goes company-wide — it just gets served from a URL instead of opened locally (any static host: internal server, SharePoint, Netlify, GitHub Pages). No backend, no build pipeline either way. Worth building two modes in from the start rather than retrofitting: an **edit mode** (full controls, internal use) and a **view/share mode** (loads one saved JSON config read-only, editing UI hidden) — so a client gets a link to one specific setup, not the whole configurator.

**Performance**: light by web-3D standards — one curved wall, a handful of boxes, a video texture, no physics. Runs fine on integrated graphics, not just dedicated GPUs.

**As the catalog grows (humans, vehicles, video plate) — three guardrails to keep it light:**

- Sourced vehicle/set-piece models: prefer low-poly variants; run anything heavier through a decimate pass or `gltf-transform` before it enters the catalog — a photoreal marketplace car (100k+ tris, 4K PBR textures) is the wrong weight class for a blocking proxy
- Video texture on the volume wall: cap source video at 1080p — it's a framing check, not a color-accurate LED render, and continuous per-frame texture upload is the single heaviest thing the tool does on its own
- Repeated extras: if placing more than a handful of identical human stand-ins, render them via `THREE.InstancedMesh` (one draw call for all instances) rather than as separate objects

## Data model & persistence

Every stage element is a plain JSON object — not hardcoded geometry — so specs can change without touching render code:

```json
{
  "units": "ft",
  "panelSizeM": 0.5,
  "fixedElements": [
    { "id": "mainVolumeWall", "type": "curvedWall", "panelsHigh": 10, "panelsWideAtArc": 36, "arcDegAchieved": 180, "footingHeightFt": 0.5625 },
    { "id": "ceiling", "panelsLong": 6, "panelsWide": 10, "motorMountHeightFt": 24, "panelRigMinHeightFt": 4, "panelRigMaxHeightFt": 20, "adjustable": true, "adjustableAxis": "height-only", "positionOffsetFromMainWallFrontFt": 10.75, "positionOffsetFromCurveDeepestFt": 16 },
    { "id": "stageDeckCasters", "heightFt": 2, "lengthFt": 16, "depthFt": 4, "moduleNote": "built from 4x4 aluminum or 4x8 steel deck units, combined" }
  ],
  "rollingWalls": [
    { "id": "rollWall_L", "panelsHigh": 8, "panelsWide": 10, "track": "straight", "defaultSide": "left", "facing": "in", "maxTravelFt": null, "travelNote": "tethered via 100ft flexible cable — not a hard travel limit; derive default range from deck length rather than hardcoding", "deployed": true },
    { "id": "rollWall_R", "panelsHigh": 8, "panelsWide": 10, "track": "straight", "defaultSide": "right", "facing": "in", "maxTravelFt": null, "travelNote": "identical pair with rollWall_L", "deployed": true }
  ],
  "assetCatalog": [
    { "assetId": "stationPlatform", "name": "Station Platform", "category": "set-piece",
      "variants": [
        { "variant": "v1", "lengthFt": 24, "widthFt": 16, "heightFt": 2, "model": "assets/station_platform_v1.glb" },
        { "variant": "v2", "lengthFt": 24, "widthFt": 20, "heightFt": 2, "model": "assets/station_platform_v2.glb" },
        { "variant": "v3", "lengthFt": 16, "widthFt": 20, "heightFt": 2, "model": "assets/station_platform_v3.glb" }
      ]
    },
    { "assetId": "rooftopSet", "name": "Rooftop Set", "category": "set-piece", "status": "deferred",
      "variants": [
        { "variant": "v1", "parapetHeightFt": 1.3125, "model": "assets/rooftop_v1.glb" },
        { "variant": "v2", "parapetHeightFt": 3.375, "model": "assets/rooftop_v2.glb" }
      ]
    },
    { "assetId": "doorBox", "name": "Door Box (rooftop component)", "category": "set-piece", "parentSet": "rooftopSet", "status": "v2/v3 deferred",
      "dualMaterial": { "sideA": "brick", "sideB": "stucco", "note": "one object, two faces — orientation picks which side shows, not a separate variant per finish" },
      "variants": [
        { "variant": "v1", "lengthFt": 12.083, "widthFt": 4.333, "heightFt": 10.167, "model": "assets/door_box_v1.glb" }
      ]
    },
    { "assetId": "cornerPillar", "name": "Glass Wall Corner Pillar", "category": "set-piece", "parentSet": "glassPropWalls",
      "lengthFt": 4, "widthFt": 4, "heightFt": 10,
      "note": "connects two glass prop wall sections at a building-corner configuration (stands in for the structural pillar real high-rises have between glass panes, instead of a glass-to-glass seam); sits on its own 4x4 stage deck module at 2ft base height, flush to the deck edges, total height 10ft to match the glass wall's window height",
      "model": "assets/corner_pillar.glb" },
    { "assetId": "subwayCar", "name": "Subway Car", "category": "set-piece", "lengthFt": 36.167, "widthFt": 8.5, "heightFt": 9.667,
      "doorConfig": { "doorways": 2, "panelsPerDoorway": 2, "style": "center-parting sliding" },
      "model": "assets/subway_car.glb" },
    { "assetId": "sedan_generic", "name": "Sedan (generic)", "category": "vehicle", "lengthFt": 15, "widthFt": 6, "heightFt": 5, "model": "assets/sedan_generic.glb",
      "seatAnchors": [
        { "seat": "driver", "x": -1.2, "y": 3.0, "z": 2.0, "rotationDeg": 0 }
      ]
    },
    { "assetId": "human_standing", "name": "Human — standing (generic)", "category": "human", "heightFt": 5.75, "model": "assets/human_standing.glb" }
  ],
  "placedAssets": [
    { "assetId": "stationPlatform", "variant": "v1", "x": 0, "z": 0, "rotationDeg": 0 },
    { "assetId": "human_standing", "x": 12, "z": 4, "rotationDeg": 90 }
  ]
}
```

Units: feet, matching film-industry convention and how the stage is almost certainly already measured; a ft/m toggle is a display-layer conversion, not a schema change.

**Two schema updates from the field-measurement pass**: (1) the volume wall, rolling walls, and ceiling are dimensioned in **panel counts**, not feet directly — panels are a fixed 50cm × 50cm module (`panelSizeM: 0.5` at the schema root), so physical size is always `panelCount × 0.5m`, derived at render time rather than re-entered. This also adds two physical elements that aren't LED panels: the **stage deck on casters** the rolling walls ride on (its own height/length/depth), and the main volume's **footing height** off the ground (\~7in / 0.58ft). (2) Station platform, rooftop set, and the rooftop's **door box** aren't single fixed pieces — they're built in multiple pre-configured sizes. Each catalog entry now carries a `variants` array (v1, v2, …), each with its own dimensions and glTF path; a `placedAssets` entry references both the `assetId` and which `variant` is in the scene. The piece-library panel groups these as one entry with a version dropdown, not a separate catalog row per size.

**Revised model — stage decking vs. rolling walls (field clarification, supersedes the two items above where they conflict)**: two terms got conflated and are now split into three distinct definitions.

- **Rolling wall = one object (wall + its own rolling deck base, fixed together, do not come apart).** The "stage deck on casters" is NOT a standalone mobile piece — it is the base *underneath each mobile wall*. One 16′L × 4′D × 2′H deck section per wall; the LED panels sit atop it, their long side aligned and **flush to one (inward, volume-facing) edge**, so from the 4′ end the unit reads as an **L**. The flat flush faces point into the middle of the volume. Default layout is still one such unit on each side of the main wall (turning the C into a U). The whole wall-plus-base is a single selectable object.
- **Stage decking = a general, custom-dimensioned modular platform, fixed 2′ tall (length × width free), spawnable in multiple segments** for unconventional shapes/configs. It is the same physical decking the shop builds in many configurations; it plays many roles depending on the hybrid/custom build.
- **Presets set the size, not a separate object.** The **station platform** (and, deferred, the **rooftop**) are just **preset size configurations of the stage decking** — selectable so the user picks a role and the dimensions are filled in, rather than typing numbers. So the old `stationPlatform` "set-piece with variants" becomes a generic `stageDeck` piece plus a `stageDeckPresets` list (station v1 24×16, v2 24×20, v3 16×20; rooftop deferred). A placed stage deck carries its own `lengthFt`/`widthFt` (and an optional `preset` label).

**Resolved from Darcy's filled-in measurement sheet** (full detail in the verification workbook): the main wall is a full 180° semicircle, not 50° as first transcribed — and that self-checks nicely against the page-3 sketch's separately-given "38ft diameter": panel-count arc length (36 panels × 0.5m) over 180° works out to ≈18.8ft radius, ≈37.6ft diameter. Panel-count ceiling dimensions line up with the sketch's separately hand-measured ceiling-rig box — two independent numbers agreeing is a good sign the panel counts are solid. (The later dimensioned floor plan pins the ceiling at 16.5′×10′, so the build uses 10×6 panels ≈16.4′×9.84′ — the width held, the length was trimmed from 8 to 6.) Ceiling: 24ft is the motor mount height, not the panel plane — the panel rig itself is height-adjustable only (no repositioning, no tilt) between 4ft (lowered) and 20ft (raised, its closest approach to the mounts); the earlier 24-vs-20 conflict was two different reference points, not an error. Ceiling rig position is fixed: 10'9" from the main wall's front edge, starting 16ft back from the curve's deepest point. Rolling walls: straight track (not curved), default layout is one on each side of the main wall, panels facing inward, forming a U-shaped stage; the \~100ft figure is a power/data tether allowance, not a hard travel constraint — explicitly not blocking for the build. Stage deck: 2ft tall (the 13" reading was wrong), built from 4×4 aluminum or 4×8 steel modules. Subway car: 2 doorways, each a center-parting double-panel sliding door. Door box: one object with brick on one face and stucco on the other — orientation picks the finish, not a separate catalog entry per look. Rooftop set and door box v2/v3 are explicitly deferred — not needed for the initial build.

**Ceiling clarification from the photo review**: the ceiling panels are LED, not passive structure — used for top-down patterned/environmental lighting effects on set, the same content-emitting role the volume wall plays. They're fitted with a diffusion layer specifically to control moiré from reflective surfaces (car windshields, at certain angles) catching the panel pattern. That diffusion is why ceiling-truss reference photos read as a soft silk rather than visible LED tiles — it's not a different piece, just the rig photographed with its diffusion in place. Doesn't change what Phase 1 needs to build (still a plane at the given panel-count dimensions), but worth having on record: the ceiling is a second candidate for a swappable-pattern feature later, the same shape as the volume wall's background plate, if that's ever worth building. No further truss photos needed for this pass — rudimentary, correctly-dimensioned geometry is the right level of fidelity here, consistent with the rest of Phase 1.

**Why the split**: `assetCatalog` is the growing library of everything that's ever been built — glass walls in whatever configuration, the rooftop set, a vehicle library, next quarter's new piece. `placedAssets` is just which catalog entries are in *this* layout, and where. Adding a new set piece later means dropping in a glTF file and one new catalog entry — no code change, no touching the app. The deploy-it-when-you-want-it UI is a piece-library panel listing the catalog by category (set pieces / vehicles), each with an "add to scene" action that drops it in as a new `placedAssets` entry.

**Human stand-ins use the same mechanism, no new system needed**: just another `assetCatalog` category (`"category": "human"`), placed like anything else. Two things make them actually useful rather than decorative — **seat anchors** on vehicle catalog entries (named local positions: driver, front passenger, rear left/right; a seated figure snaps to one and moves with the vehicle if it's repositioned), and a plain **standing** variant for extras dropped anywhere — platform, street, background — no anchor required. Both at real average height (standing \~5'9", seated eye height \~3'10"–4'0" depending on the vehicle), so they double as scale and eyeline references for every camera setup — the seat anchor's height is exactly what an interior camera bookmark should key off.

Persistence: **JSON export/import is primary**, not a database. "Save config" writes this object to a downloadable `.json`; "load config" reads one back in. That makes layouts diffable, emailable, and versionable in a shared drive — which matters more here than a login system. Layer `localStorage` on top only for last-session autosave (wrap every read/write in try/catch; treat it as disposable, never the source of truth).

## Feature set, by phase

**Phase 1 — layout & fit-check (primitives, real dimensions)**

- Main volume wall as a fixed curved-wall mesh (radius, height, arc — not user-movable, but editable in the data file when specs change)
- Rolling walls as boxes, each with track position, deployed/stowed state, width/height — selectable and dragged along the floor (see "As built (controls)"), numeric inputs for exact placement
- Ceiling as a toggleable plane at adjustable height
- Subway car and station platform as to-scale shapes, freely positioned/rotated on the floor, snap-to-grid at a chosen increment (e.g. 0.5 ft). The subway car specifically must be modeled \*\*hollow from the start\*\* — real door/window openings cut into the geometry, interior walls/floor/ceiling with materials set to render from inside (double-sided, or separate inward-facing panels), not a solid box — with real openings on every side — near AND far windows both cut through, not just the camera-facing side, so a sightline can pass out-to-in, in-to-out, or straight through the whole car, not just into it
- Floor grid in feet, fly + top-down camera presets, JSON save/load

**Phase 2 — accurate geometry**

- Swap primitive boxes for real glTF models of the volume wall panels, rolling wall modules, and set pieces once those exist (see Asset pipeline below) — the data model doesn't change, only which mesh renders each element

**Phase 3 — shot planning (stretch, see next section)**

- Lens/FOV camera overlay, saved "shot" camera bookmarks per sequence

Build Phase 1 first and get it in front of the department that will use it before touching Phase 2 — the fit-check value (does the train clear the rolling wall track, does the platform block a rig position) comes from correct *dimensions*, not from photorealistic geometry.

## Camera & shot-planning tools

This is the piece that turns it from a furniture-arranger into an actual techvis aid:

- **Free-fly** for general spatial sense (as built: custom FPS-style navigation replaced `OrbitControls` — see "As built (controls)")
- **Top-down plan view** camera preset — the view you actually block in
- **Lens/FOV overlay**: a camera object placeable on the floor with focal-length dropdown (18/24/35/50/85/100mm and any other primes actually in the truck) plus a sensor-size preset (Full Frame, Super 35), drawing the frustum as lines in the 3D view so you can see exactly what the lens frames against the wall, the train, and the platform. Answers "will a 28mm at this mark see past the edge of the volume wall / catch the rig / clear the platform edge" without a table read or a walk-through — this is the Techvis half of previs, and it's cheap to add once floor-drag placement and a perspective camera already exist in the scene
- **Saved shot bookmarks**: name a camera position + lens combo per sequence, store it in the same JSON as the layout, recall it instantly when re-checking a setup

This is the one feature worth prioritizing above strict phase order if the builder has spare time — it's what separates "nice 3D model" from "tool that answers can-we-get-this-shot."

**Camera placement isn't special-cased**: a camera object moves through the scene exactly like any other draggable object — no "enter the vehicle" mechanic needed. Outside for the platform exterior shot, inside for the tunnel interior shot, same subway car asset, same tool. Worth building: a couple of **named camera bookmarks per piece** (e.g. subway car → "platform exterior" / "interior, center aisle") so you're placing into a known-good vantage point instead of hand-dragging one each session — pairs with the saved shot bookmarks below.

**As built (Phase 3):** the camera is a `camera` catalog piece (spawn several). Rotation 0° faces −Z (toward the volume's deepest point); the piece still only moves on the floor and yaws, while lens height, tilt, focal length, sensor and focus distance are inspector fields. `lensSetMm` and `sensors` live at the schema root so the lens kit is edited in data. The frustum is drawn gold with a cyan focus plane; **Camera View** looks through the camera letterboxed to the sensor aspect (Esc exits). Shots (`shots` at schema root: sequence, name, position, yaw, height, tilt, lens, sensor, focus) save with the layout and recall in view mode too. Named vantages are `cameraMarks` on catalog entries, in the piece's local frame — the subway car ships with platform exterior, interior center aisle, and interior looking out a door. Mark `heightFt` is lens height above the ground. When several cameras exist, the shot bar's camera picker shows which one Camera View / Save shot / Recall act on — the last one picked or selected, else the first.

**As built (field corrections):** (1) The **subway car rides on a 2′ air-caster undercarriage** (`undercarriageFt: 2`), so its interior floor is at 2′ — flush with stage decking and the station platform. Catalog `heightFt` (9.667′) is the car body above its floor; total height is 11.667′. Interior ceiling, window sill and door heights are floor-relative. (2) **Rolling walls' deck extends outward** (away from the volume) with the flush face inward — the default. (3) **Seat anchors** are implemented: `y` is the seated **eye** height, so each anchor also appears as an eye-level camera vantage. A placed vehicle gets a persistent `key` when first occupied; a seated human stores `seat: { key, seat }`, is drawn as a shortened (seated) figure, and moves with the vehicle. Dragging a human within 2.5′ of a free anchor snaps it in; the inspector's Seat dropdown does the same. The sedan ships with driver, front passenger, rear left and rear right; vehicles render ghosted so seated figures stay visible.

**As built (controls):** (1) **Rotate is a ground yaw ring, not the TransformControls rotate gizmo** (its quaternion→Euler readout clamped at ±90° and swung back). With Rotate active, a blue ring with a heading cone appears around the selection; grab it and drag around its curve — yaw follows the cursor's angle about the object's pivot with unwrapped accumulation, so 180° and full turns work. Snaps to 15°, Shift = 1°. Keyboard: Shift+←/→ = 15°, Shift+Alt+←/→ = 1°. Typing in the inspector still works. Seated humans have no ring (they follow their vehicle). **Moving is drag-the-piece**: press on any piece's body and drag it along the floor (grab offset kept, snapped to the snap selector; a plain click only selects). This works in either tool, and the arrow gizmo (`TransformControls`) was removed. Dragging a human near a free seat anchor snaps it in. Dragging empty space navigates the view instead. (2) **Camera View is first-person**: the camera object is the body. W/S move along its heading, A/D strafe, Q/E lower/raise the lens, left-drag mouse (or arrow keys) looks — yaw and tilt, look speed scales with focal length — Shift = fast, Esc exits. Position, heading, height and tilt write back to the camera object on exit. (3) **The main view is FPS-style too; `OrbitControls` was removed** (it pinned the view to a fixed pivot). **Fly** (default): W/S move along the heading, A/D strafe, Q/E down/up, drag empty space (any button) to look, arrows look, wheel dollies, Shift = 3× speed. **Top-Down** looks straight down and never rotates: W/A/S/D or drag pans, wheel or Q/E zooms (wheel zooms about the cursor). New pieces spawn where the main view is centred. Move/Rotate tool shortcuts are now keys **1** and **2** (W/E are navigation). When several cameras exist, only the active one draws a full-strength frustum (others 25%), and the Camera View HUD reads "Camera N of M".

**As built (studio shell & scene setup — floor-plan pass, 20315 96 Ave):** the configurator now opens to the **base volume only** and is wrapped in the real room.

- **Coordinate frame**: world origin = centre of the main wall's curvature; **+Z faces out of the curve** (the open shooting floor / "front"), −Z is the apex/back, X is the cross axis. Main wall unchanged — 38′ dia (radius ≈18.8′), 180°, 16′ high; mouth tips at z=0, apex at z≈−18.8.
- **Studio shell** (`config.studio`): a floor + three walls (±X and the −Z back wall), **front (+Z) left open**, **no roof**, walls 27′ tall. Cross axis ≈79′ (the plan's 42′+37′ either side of the pillar line); the mouth sits 40′ from the front fire-lane edge and the apex backs up near the rear wall. A 4′ **fire-lane** keep-clear band is drawn as a floor marking (two boundary lines), not a wall. Nothing in the shell is selectable/movable.
- **Pillar** (`config.pillar`): a fixed 2′×2′ structural column, 27′ tall, standing in the shooting floor at the plan's 42′/37′ dot (front-back position approximate, easy to nudge). A real obstacle — not movable.
- **Ceiling** trimmed to the plan's **16.5′ × 10′** (`panelsWide: 10` ≈16.4′, `panelsLong: 6` ≈9.84′; was 8 long).
- **Rolling walls** default to the **mouth** of the curve (x = ±18.8 = the wall radius, running +Z) so their flush faces continue the arc into the U.
- **First load = base volume only**: `placedAssets` ships just **one camera**. The subway car, stage decks and humans are no longer in the default scene.
- **Sets menu** (`config.sets`): the big pre-configured pieces (Subway Car, Station Platform v1/v2/v3) load in/out from a **toggle list** at the top of the Piece Library — ticking spawns one instance at its home spot (tagged `_setKey`), unticking removes it. The rest of the library still places multiples / custom sizes. Checkboxes stay in sync however a piece is added/removed.
- **Single camera, frustum off by default**: `config.showFrustums` (default **false**) hides the gold frustum + cyan focus overlay on every camera until toggled on from the camera inspector ("Show frustum").
- **Camera Mark vs Shot**: the shot bar now offers two saves. A **mark** stores position + aim only (recall moves the camera there but keeps the current lens — for quick blocking); a **shot** stores position + aim **and** lens/sensor/focus (recall restores the whole framing). Both live in `config.shots` with a `kind` field and group by sequence.
- **Autosave key bumped to v2** so stale layouts (which could carry duplicate cameras / old default sets) don't resurrect the old scene.

**As built (position-markup pass — supersedes the positions above where they differ):**

- **Curve orientation**: main wall `CylinderGeometry` thetaStart = **+π/2**, so the **concave face points +Z into the studio** and the convex back faces the rear wall (−π/2 rendered it the wrong way round).
- **Layout from the position markup** (dimensions from the floor plan, positions from the markup): volume on the LEFT, room opens RIGHT. Studio `xMin −23.5 / xMax 56.2`, `zBack −27.8 / zFrontOpen 42.3`. Studio walls near-black (`0x0d0f12`) so the lit volume reads. Pillar at **(x 20, z 16)**. Rolling walls at **(±18.8, z 8)**. Default camera at the markup's red star **(0, 31)**, 24mm, start view looking into the lit volume. Subway set home **(46.5, 18), rot 90°** — runs N–S.
- **LED content on every LED surface**: main wall, ceiling and each rolling wall each pick from a shared pool of image/video plates (`surfacePlateIdx`); main wall + ceiling default to a soft blue gradient. Rolling-wall content is set from its inspector.
- **Glass walls** (from *Lumostage – Glass Walls – Dimensions and Configurations*): **Glass Wall on Deck** = 12′×10′ storefront wall (1′ base, 3×2 pane grid) standing on its own **12′×4′×2′ steel deck, flush to one long side** — one object, total height 12′. **Glass Wall Corner Piece** = 4′×4′×10′ (brick reverse faces) on a 4′×4′×2′ deck so its top lines up with the walls.
- **Imported .glb models**: Piece Library → *Imported Models* → **Import .glb…**. The file is kept in the browser's IndexedDB (`lumostage-models`); the layout stores only a small record in `config.customModels` plus per-instance `fitAxis` / `fitFt`. Each instance is scaled **uniformly** from one real dimension entered in the Inspector (length, width or height) — length = the model's longer horizontal side, laid along local X. Until the file is read back the piece shows as a ghost box at its true size. Note: a saved JSON carries the record, not the model file — on another machine, re-import the .glb.
- **Gamepad (XInput / browser "standard" mapping)**, polled each frame alongside mouse + keyboard. First-person: left stick move/strafe, right stick look, LT/RT down/up, L3 sprint (latches until the stick centres). **A** toggles overhead ↔ first-person (returning drops you where you panned to, same height/heading). **R1 hold** grabs the piece under a centre crosshair and carries it as you move/look; **R1 + D-pad ←/→** turns it one 15° step (hold repeats). **X** parks the film camera at your viewpoint (overhead: just the floor spot). **Y** look through the film camera (sticks then drive it), **B** drop / deselect / exit camera view, **Start** save shot, **LB** save mark, **Select/Back** lens menu, **R3** print shot. Crosshair turns gold and names what R1 would grab; ignores anything within 2.5′ of the eye. Rumble on grab/drop/place where supported. The pad is detected after its first button press.
- **Imported model colour**: the app renders without output colour conversion, so glTF models are brought into that pipeline on load (`fixModelColors`: textures pass straight through, linear colour factors re-expressed as sRGB). This fixed models coming in dark and muddy.
- **Live reflections**: imported models and the subway car's stainless shell each carry a cube-map **reflection probe** at their centre that snapshots the stage (main wall, rolling walls, ceiling — video included) and feeds it to their PBR materials as the environment, so paint/chrome/glass mirror the volume and its colour lights the body. The piece is hidden during its own snapshot. Probes update round-robin, one per frame: **Settings → Live reflections** (off = snapshot only when the piece moves) and **Reflection quality** (Light 128 px · 4/s, Balanced 256 px · 10/s, Smooth 256 px · 30/s; phones always Light). Per piece in the inspector: **Mirror the LED stage** on/off and **Strength** (0–3). Known limits: reflections are from one point (less exact very close to a wall), no reflections of reflections. Measured: 60 fps with two live probes on the dev laptop.
- **360° environments** (LED section): one equirectangular image/video projected onto every LED surface via a shared `ShaderMaterial` — each fragment looks up the frame along its own direction from an eyepoint (film camera lens by default = tracked-volume parallax; or the walk-view camera; or a fixed stage point), with Turn (yaw), Horizon (pitch) and Brightness. Proxies may be partial crops of the sphere; the shader takes the lon/lat range from the manifest. Per-surface "Show on" toggles; the panel's own material is set aside and restored. Library = `environments/library.json` (written by `tools/make-360-proxies.ps1`: crop ±135°/−40…+80°, 3840 px, H.264 faststart / JPEG, manifest with crop + yaw) + `environments/samples.json` (bundled calibration grid). Layout stores `config.environment` (libraryId, surfaces, follow, yaw, pitch, brightness, fixed) and restores it on load. `serve.py` serves `environments/` with byte-range support. Verified: seamless across wall/ceiling/rolling walls, shows in glossy floor + car reflections + lens view, 60 fps with a 4K video. Guide: `docs/360-environments.md`.
- **Glossy floor**: a `THREE.Reflector` planar mirror sits just under a semi-transparent studio floor. **Settings → Floor finish**: Matte (no mirror), Satin (default, 20% reflection) or Polished (~40%). Phones default to matte. The mirror is left out of probe snapshots and plan prints. The floor grid is on layer 1 (main view only), so it isn't mirrored, reflected in cars, or drawn in Lens view / printed shots.
- **Invert gamepad look**: Settings checkbox; flips right-stick Y for looking (Walk) and camera tilt (Lens view), not Plan zoom. Saved per browser (`localStorage` `lumostage.padInvertY`), not in the layout.
- **Ceiling** starts at **20′** (rig max). It's a "two-way mirror": the LED face is a single downward-facing plane drawn front-side only, so it's lit from below and see-through from above (Plan view), with a thin metal frame around its edge visible from every angle. Saved layouts still on the old 12′ default are lifted to 20′ once (`config.migrations.ceiling20`); a deliberately set height is kept.
- **Interface layout (first-time-user pass)**: the 3D view owns the screen on load. Top bar = brand, the **Walk / Plan / Lens** view switch, and **File** (save/open layout, publish to phone, view-only mode), **Settings** (units, snap) and **Help** (full controls reference; also the `?` key). A left **section rail** opens one drawer at a time: **Stage** (sets toggles, ceiling), **Add** (collapsible groups: decking, glass walls, set pieces, vehicles, people, cameras, your 3D models), **LED** (what every LED surface shows + add content), **Camera** (active camera, lens, field-of-view toggle, look through lens, saved shots, save shot/mark, print). The **inspector** appears only while a piece is selected (Move/Rotate tool in its header; Position / Lens / Rig groups). Lens view gets a compact action bar (Lens · Save shot · Save mark · Print · Exit). First run shows a 3-step welcome card (dismissed for good once closed or once any section is opened); the one-line control hint fades after you start moving. Phone: the rail becomes a bottom tab row (Camera only, read-only) and drawers become bottom sheets.
- **Viewfinder** in Camera View: corner brackets, AF box + centre cross, ● CAM n, sensor / focal / H-FOV / 24FPS badges, running timecode, focus/height/tilt/position readout and a MENU button — framed exactly on the letterboxed lens image. Side panels hide while looking through the lens.
- **Lens menu**: gamepad **Select/Back**, keyboard **L**, or viewfinder **MENU**. ↑/↓ lens (applies live), ←/→ sensor, A / Select / Enter closes, B / Esc closes. (Save mark moved to **LB**.)
- **Print shot** (shot bar button, gamepad **R3**): one PNG, 2400 px wide — the lens view (rendered off-screen at 2× for quality, no HUD), a top-down stage plan (main-wall arc and rolling walls drawn in, ceiling as a dashed outline, camera + field-of-view wedge + focus arc, 10′ scale bar) and the camera report (lens, sensor, FOV, focus, frame size at focus, lens height, tilt, heading, position, pieces on stage). Title = sequence · shot name from the shot bar.
- **Collision warning** (advisory, never blocks): whenever the selected piece moves or turns (mouse, keys, inspector or gamepad), its oriented floor footprint is tested against the pillar, studio walls, the main wall's arc (1′ deep behind the LED face), the ceiling (by height), rolling walls and other pieces. Hits draw a **red outline** plus a banner naming what it overlaps; sitting in the **4′ fire lane** draws **amber**. Pieces standing on a stage deck don't count as overlapping it (deck-vs-deck does). Cameras and humans are skipped. Flush/abutting pieces (within 0.05′) don't trigger.
- **migrateConfig**: app-defined collections (`assetCatalog`, `sets`, `stageDeckPresets`, `lensSetMm`, `sensors`) always refresh from the current build; user data (`placedAssets`, `shots`, `customModels`, studio/pillar/stage tweaks) is preserved. Autosave key is now **v3**.

**Aperture / depth of field**: scoped out of the near-term build. Physically accurate DOF needs circle-of-confusion math and either a blur pass or a depth-based shader — real effort for a tool whose job is blocking and framing, not cinematography previs. A lightweight substitute: mark the focus-distance point on the frustum line as a simple visual cue, with no actual blur rendered. Revisit true DOF only if this tool's role grows beyond fit-checks.

## Volume wall background plate

Not live parallax or a tracked render — a flat, swappable texture on the wall geometry so a candidate background reads correctly against the physical set pieces before committing to a real LED render. Straightforward to add once the wall mesh exists (Phase 1 or 2, either primitive or real geometry):

- Static image: any uploaded file (jpg/png) mapped onto the wall as a standard texture
- Looping video: an uploaded video file bound as a `THREE.VideoTexture` — plays back flat on the wall, no camera tracking, no parallax, no perspective correction; it's there to check framing and color/scale relationships against the train and platform, not to simulate the LED volume's actual render behavior
- One dropdown to swap between a few saved plates per session, so you can flip through candidate backgrounds against the same camera/lens setup without re-placing anything

## Asset pipeline

**Format: glTF/GLB.** It's the standard export target from Blender, Unreal, and most CAD-to-mesh workflows, loads natively via Three.js's `GLTFLoader`, and keeps file size down (binary, compressed textures) — important for a single-file local tool that shouldn't balloon past a few MB.

Where the real geometry comes from:

- **Glass prop walls**: if there's an existing Unreal/Blender/CAD model from the \[\[glass-prop-walls\]\] build (the ones in the VERTual Production deck), export that to glTF directly — don't remodel from scratch

  The glass prop wall system now also includes a **corner pillar** piece (4ft×4ft footprint, 10ft tall to match the glass walls' window height, sits flush on its own 4x4 stage deck module at 2ft base height) used to join two glass wall sections at a building-corner configuration instead of a glass-to-glass seam — catalogued the same way as everything else, no separate mechanism needed.
- **Main volume wall**: whatever CAD/as-built drawing exists for the physical LED volume; if none, a measured box/curved-wall approximation is fine for Phase 1 and gets swapped later
- **Subway car / station platform**: if these were built as physical set pieces, construction drawings give exact dimensions even before a 3D model exists; if a set designer already modeled them digitally, that model exports straight to glTF

* **Vehicles**: don't model these from scratch — source ready-made glTF vehicle models (Sketchfab, Kenney.nl for free low-poly packs, CGTrader/TurboSquid for higher fidelity). A small curated set — sedan, SUV, full-size pickup, cargo van — covers most needs; check license terms before anything ships client-facing, since some "free" marketplace models are personal-use only

**Reference photos, not video**: stills are the usable input here, not a walkthrough video — nothing in this pipeline processes video natively, so a walkthrough would just need manual frame-grabbing to become useful anyway. Photos don't replace the measurement sheet's numbers; they cover what numbers can't — whether the volume wall curve is continuous or segmented flats, how the rolling wall track mechanism physically works, how the door box attaches to the rooftop set, what the main wall's footing looks like. One wide shot per sheet item, plus a close-up of anything mechanical, same scale-reference-in-frame approach as elsewhere.

Until real models exist, Phase 1 primitives (correctly *dimensioned* boxes/cylinders) are not a placeholder to apologize for — they're the right first deliverable. Swapping mesh references later is a small change to the loader, not a rebuild.

## Open items — what the builder needs before starting

- [ ] Main volume wall: resolved — 10 panels high, 36 panels wide across a 180° semicircle, footing 0.56ft (6¾ in) off ground. Cross-validated against the page-3 sketch's 38ft diameter figure.
- [ ] Rolling walls: resolved — 2 walls (identical pair), 8 panels high × 10 wide each, straight track, default L+R flanking the main wall facing inward (U-shape), stowed within the volume. Travel distance not pinned down (100ft cable allowance ≠ travel range) but explicitly non-blocking — derive a default from deck length instead.
- [ ] Ceiling: resolved — 6×10 panels (≈10′×16′6″, per the floor plan's "LED Ceiling 16.5′ × 10′"; was 8 long), motor mounts at 24ft, panel rig height-adjustable only between 4ft and 20ft off ground, fixed position 10'9" from the main wall's front edge starting 16ft back from the curve's deepest point.
- [ ] Subway car: resolved — 36'2"×8'6"×9'8" exterior, 6'8" interior ceiling (6'7⅜" near the door — slight concave), 37" window sill, 2 doorways each with a center-parting double-panel sliding door.
- [ ] Station platform: resolved — 3 versions (24×16, 24×20, 16×20), all 2ft off ground. Gap distance from platform edge to the subway car (v1 pairing) still not pinned down — not urgent, but worth getting before interior/exterior camera bookmarks get tuned.
- [ ] Any existing CAD/Blender/Unreal models of the above (glass prop walls, set pieces) that can export to glTF, vs. measurements only
- [ ] Rooftop set: deferred — Sir T said ignore for now on all three versions (dimensions, parapet heights, the "variable based on deck choice" question). Doesn't block Phase 1; revisit before Phase 2 asset work.
- [ ] Door box: v1 resolved (12'1"×4'4"×10'2", one object with brick/stucco on opposite faces). v2/v3 deferred, same as rooftop set.
- [ ] Auth: resolved — no login inside the tool itself. Client access is gated one layer up, behind Lumostage's own client portal; the configurator (edit and view/share modes both) stays unauthenticated by design.
- [ ] Confirm feet as the working unit (assumed here as standard film-industry practice in BC)
