# Lumostage Stage Configurator — Build Brief

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

Camera/object manipulation: Three.js's own `OrbitControls` (viewport navigation) and `TransformControls` (move/rotate/scale gizmo, Blender-style) addons cover the whole interaction model — no third-party UI kit needed.

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
    { "id": "ceiling", "panelsLong": 8, "panelsWide": 10, "motorMountHeightFt": 24, "panelRigMinHeightFt": 4, "panelRigMaxHeightFt": 20, "adjustable": true, "adjustableAxis": "height-only", "positionOffsetFromMainWallFrontFt": 10.75, "positionOffsetFromCurveDeepestFt": 16 },
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

**Resolved from Darcy's filled-in measurement sheet** (full detail in the verification workbook): the main wall is a full 180° semicircle, not 50° as first transcribed — and that self-checks nicely against the page-3 sketch's separately-given "38ft diameter": panel-count arc length (36 panels × 0.5m) over 180° works out to ≈18.8ft radius, ≈37.6ft diameter. Panel-count ceiling dimensions (8×10 panels ≈ 13'8"×16'6") also line up with the sketch's separately hand-measured ceiling-rig box — two independent numbers agreeing is a good sign the panel counts are solid. Ceiling: 24ft is the motor mount height, not the panel plane — the panel rig itself is height-adjustable only (no repositioning, no tilt) between 4ft (lowered) and 20ft (raised, its closest approach to the mounts); the earlier 24-vs-20 conflict was two different reference points, not an error. Ceiling rig position is fixed: 10'9" from the main wall's front edge, starting 16ft back from the curve's deepest point. Rolling walls: straight track (not curved), default layout is one on each side of the main wall, panels facing inward, forming a U-shaped stage; the \~100ft figure is a power/data tether allowance, not a hard travel constraint — explicitly not blocking for the build. Stage deck: 2ft tall (the 13" reading was wrong), built from 4×4 aluminum or 4×8 steel modules. Subway car: 2 doorways, each a center-parting double-panel sliding door. Door box: one object with brick on one face and stucco on the other — orientation picks the finish, not a separate catalog entry per look. Rooftop set and door box v2/v3 are explicitly deferred — not needed for the initial build.

**Ceiling clarification from the photo review**: the ceiling panels are LED, not passive structure — used for top-down patterned/environmental lighting effects on set, the same content-emitting role the volume wall plays. They're fitted with a diffusion layer specifically to control moiré from reflective surfaces (car windshields, at certain angles) catching the panel pattern. That diffusion is why ceiling-truss reference photos read as a soft silk rather than visible LED tiles — it's not a different piece, just the rig photographed with its diffusion in place. Doesn't change what Phase 1 needs to build (still a plane at the given panel-count dimensions), but worth having on record: the ceiling is a second candidate for a swappable-pattern feature later, the same shape as the volume wall's background plate, if that's ever worth building. No further truss photos needed for this pass — rudimentary, correctly-dimensioned geometry is the right level of fidelity here, consistent with the rest of Phase 1.

**Why the split**: `assetCatalog` is the growing library of everything that's ever been built — glass walls in whatever configuration, the rooftop set, a vehicle library, next quarter's new piece. `placedAssets` is just which catalog entries are in *this* layout, and where. Adding a new set piece later means dropping in a glTF file and one new catalog entry — no code change, no touching the app. The deploy-it-when-you-want-it UI is a piece-library panel listing the catalog by category (set pieces / vehicles), each with an "add to scene" action that drops it in as a new `placedAssets` entry.

**Human stand-ins use the same mechanism, no new system needed**: just another `assetCatalog` category (`"category": "human"`), placed like anything else. Two things make them actually useful rather than decorative — **seat anchors** on vehicle catalog entries (named local positions: driver, front passenger, rear left/right; a seated figure snaps to one and moves with the vehicle if it's repositioned), and a plain **standing** variant for extras dropped anywhere — platform, street, background — no anchor required. Both at real average height (standing \~5'9", seated eye height \~3'10"–4'0" depending on the vehicle), so they double as scale and eyeline references for every camera setup — the seat anchor's height is exactly what an interior camera bookmark should key off.

Persistence: **JSON export/import is primary**, not a database. "Save config" writes this object to a downloadable `.json`; "load config" reads one back in. That makes layouts diffable, emailable, and versionable in a shared drive — which matters more here than a login system. Layer `localStorage` on top only for last-session autosave (wrap every read/write in try/catch; treat it as disposable, never the source of truth).

## Feature set, by phase

**Phase 1 — layout & fit-check (primitives, real dimensions)**

- Main volume wall as a fixed curved-wall mesh (radius, height, arc — not user-movable, but editable in the data file when specs change)
- Rolling walls as boxes, each with track position, deployed/stowed state, width/height — selectable and moved with the `TransformControls` gizmo, numeric inputs for exact placement
- Ceiling as a toggleable plane at adjustable height
- Subway car and station platform as to-scale shapes, freely positioned/rotated on the floor, snap-to-grid at a chosen increment (e.g. 0.5 ft). The subway car specifically must be modeled \*\*hollow from the start\*\* — real door/window openings cut into the geometry, interior walls/floor/ceiling with materials set to render from inside (double-sided, or separate inward-facing panels), not a solid box — with real openings on every side — near AND far windows both cut through, not just the camera-facing side, so a sightline can pass out-to-in, in-to-out, or straight through the whole car, not just into it
- Floor grid in feet, orbit + top-down camera presets, JSON save/load

**Phase 2 — accurate geometry**

- Swap primitive boxes for real glTF models of the volume wall panels, rolling wall modules, and set pieces once those exist (see Asset pipeline below) — the data model doesn't change, only which mesh renders each element

**Phase 3 — shot planning (stretch, see next section)**

- Lens/FOV camera overlay, saved "shot" camera bookmarks per sequence

Build Phase 1 first and get it in front of the department that will use it before touching Phase 2 — the fit-check value (does the train clear the rolling wall track, does the platform block a rig position) comes from correct *dimensions*, not from photorealistic geometry.

## Camera & shot-planning tools

This is the piece that turns it from a furniture-arranger into an actual techvis aid:

- **Free orbit** for general spatial sense (default Three.js `OrbitControls`)
- **Top-down plan view** camera preset — the view you actually block in
- **Lens/FOV overlay**: a camera object placeable on the floor with focal-length dropdown (18/24/35/50/85/100mm and any other primes actually in the truck) plus a sensor-size preset (Full Frame, Super 35), drawing the frustum as lines in the 3D view so you can see exactly what the lens frames against the wall, the train, and the platform. Answers "will a 28mm at this mark see past the edge of the volume wall / catch the rig / clear the platform edge" without a table read or a walk-through — this is the Techvis half of previs, and it's cheap to add once `TransformControls` and a perspective camera already exist in the scene
- **Saved shot bookmarks**: name a camera position + lens combo per sequence, store it in the same JSON as the layout, recall it instantly when re-checking a setup

This is the one feature worth prioritizing above strict phase order if the builder has spare time — it's what separates "nice 3D model" from "tool that answers can-we-get-this-shot."

**Camera placement isn't special-cased**: a camera object moves through the scene exactly like any other `TransformControls`-attached object — no "enter the vehicle" mechanic needed. Outside for the platform exterior shot, inside for the tunnel interior shot, same subway car asset, same tool. Worth building: a couple of **named camera bookmarks per piece** (e.g. subway car → "platform exterior" / "interior, center aisle") so you're placing into a known-good vantage point instead of hand-dragging one each session — pairs with the saved shot bookmarks below.

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
- [ ] Ceiling: resolved — 8×10 panels, motor mounts at 24ft, panel rig height-adjustable only between 4ft and 20ft off ground, fixed position 10'9" from the main wall's front edge starting 16ft back from the curve's deepest point.
- [ ] Subway car: resolved — 36'2"×8'6"×9'8" exterior, 6'8" interior ceiling (6'7⅜" near the door — slight concave), 37" window sill, 2 doorways each with a center-parting double-panel sliding door.
- [ ] Station platform: resolved — 3 versions (24×16, 24×20, 16×20), all 2ft off ground. Gap distance from platform edge to the subway car (v1 pairing) still not pinned down — not urgent, but worth getting before interior/exterior camera bookmarks get tuned.
- [ ] Any existing CAD/Blender/Unreal models of the above (glass prop walls, set pieces) that can export to glTF, vs. measurements only
- [ ] Rooftop set: deferred — Sir T said ignore for now on all three versions (dimensions, parapet heights, the "variable based on deck choice" question). Doesn't block Phase 1; revisit before Phase 2 asset work.
- [ ] Door box: v1 resolved (12'1"×4'4"×10'2", one object with brick/stucco on opposite faces). v2/v3 deferred, same as rooftop set.
- [ ] Auth: resolved — no login inside the tool itself. Client access is gated one layer up, behind Lumostage's own client portal; the configurator (edit and view/share modes both) stays unauthenticated by design.
- [ ] Confirm feet as the working unit (assumed here as standard film-industry practice in BC)
