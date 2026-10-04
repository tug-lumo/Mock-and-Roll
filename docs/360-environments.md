# 360° environments in Mock & Roll

One 360° video or image wrapped across **every LED surface** — main wall, ceiling and both
rolling walls — with each panel showing the slice of the world it would actually see. Corners
and seams line up because every pixel looks the world up along its own direction from one
eyepoint, the same idea a real volume uses.

## Quick start

1. Drop 360° files (equirectangular, 2:1 — the standard "360 video" format) into
   `environments\source\`.
2. In PowerShell, from the project folder:
   ```
   .\tools\make-360-proxies.ps1
   ```
3. In Mock & Roll: **LED → 360° environment → Library →** pick it.
   (Or **Load 360° image or video…** to try any file straight off disk.)

## In the app (LED section)

| Control | What it does |
|---|---|
| **Library** | Proxies from `environments/library.json` (made by the script) plus bundled samples. |
| **Load 360° image or video…** | Any local file, full sphere assumed. Not remembered after a refresh — use the script for keepers. |
| **Show on** | Main wall / Ceiling / each rolling wall. Untick to go back to what that surface showed before. |
| **Seen from** | **Film camera (tracked)** — parallax follows the active camera, like a tracked volume (default). **You (walk view)** — explore how the world sits around you. **Fixed stage point** — a static projection. |
| **Turn** | Rotate the world left/right to line up a street, horizon or sun with the set. Saved per environment in the layout (and as `yaw` in the manifest). |
| **Horizon** | Raise (+) or lower (−) the world's horizon. |
| **Brightness** | LED output, 20–200%. |
| **Play / Pause / Restart / Remove** | Video transport; Remove takes it off every surface. |

The environment shows up everywhere the stage is drawn: Walk/Plan views and the Viewfinder, the glossy floor,
live car/subway reflections, and **Print shot**. A layout remembers which library environment it
used, where it was shown, and its turn/horizon/brightness.

Test pattern: **Calibration grid (sample)** ships with the app. FRONT should sit centred on the
main wall, the seafoam horizon at lens height, LEFT (green) on the left rolling wall and RIGHT
(salmon) on the right.

## The proxy script — `tools\make-360-proxies.ps1`

For each file in `environments\source\` it:

1. **Crops** to the part of the sphere the stage can see — default 270° around (±135° from the
   centre of the frame) and 40° below to 80° above the horizon — so pixels go where the panels are.
2. **Scales** to 3840 px wide (fits every laptop's 4096 px texture limit).
3. **Encodes** videos as H.264 MP4 (yuv420p, fast-start, no audio) and stills as JPEG.
4. **Writes** `environments\library.json` with each proxy's crop range so the app maps it back
   onto the right part of the sphere. Your edits to `name` and `yaw` survive re-runs.

Already-converted files are skipped unless `-Force`.

| Option | Default | Use |
|---|---|---|
| `-CenterLon 90` | 0 | Make that direction (+ = right) "straight ahead" before cropping. |
| `-LonMin -LonMax` | -135, 135 | Horizontal coverage around the centre. |
| `-LatMin -LatMax` | -40, 80 | Vertical coverage (below/above the horizon). |
| `-Full` | — | Keep the whole sphere, no crop. |
| `-Width 2560` | 3840 | Lighter proxies for phones / older laptops. |
| `-Crf 18` | 20 | Higher quality (bigger files); 23 = smaller. |
| `-MaxSeconds 30` | 0 (all) | Trim long plates for quick looks. |
| `-Force` | — | Rebuild even if the proxy is newer than the source. |

`tools\make-test-equirect.py` regenerates the calibration grid.

## Limits worth knowing

- **Previs, not the real render.** It's a flat 360° frame projected from one eyepoint — great for
  checking framing, horizon, scale and what reflects in the car; it isn't Unreal's 3D world with
  true parallax, and there's no inner/outer frustum split.
- **Size.** Browsers decode one 4K H.264 stream comfortably; 8K sources must go through the script.
- **Local vs hosted.** `environments/` proxies live on this PC (served by `serve.py`, git-ignored).
  The hosted site only has the bundled samples — Cloudflare's per-file limit is 25 MB, so real
  plates need storage like R2 (part of the shared-library work).
