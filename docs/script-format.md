# `lumostage.script` — the script handoff between Slugger and Mock & Roll

One JSON file (`<title>.lumoscript.json`) carries a screenplay's scenes and breakdown from
**Slugger** (Export to Mock & Roll) into **Mock & Roll** (File → Import script…, or drop it on the board).
Mock & Roll's in-browser PDF reader produces the same document for clients who upload a script PDF,
so both routes feed the same Script panel.

Writer of record: `Slugger/screenplay_reader/mockroll_link.py` (`build_handoff`). Reader + PDF port:
`index.html` → *SCRIPT* section (`parseScreenplayLines`, `importScriptFile`).

```jsonc
{
  "format": "lumostage.script", "version": 1,
  "source": { "app": "Slugger" | "Mock & Roll", "exportedAt": "2026-10-07T11:40:00", "file": "<title>" },
  "title": "HFC_D2_Apr8_Lumo", "pages": 106,
  "includesText": true,                       // false = breakdown only (client copies)
  "approaches": [ { "name": "VPROD", "onVolume": true, "colour": "#FFF2CC" } ],   // Slugger's approach list
  "scenes": [ {
    "n": "12", "slug": "INT. CHASE'S 18-WHEELER, DRIVING - LATER", "ie": "INT", "loc": "…", "tod": "LATER",
    "page": 15, "pg": 14.27, "pgEnd": 15.52, "eighths": 10, "eighthsStr": "1 2/8",
    "chars": ["JO/CHASE", "CHASE"], "desc": "first action line", "flags": [],
    "approach": "INT. CAR", "onVolume": true, "solutions": ["CUSTOM/VAD", "PRACTICAL PLATES"],
    "vfxNotes": "", "prodNotes": "", "stageNotes": "", "manual": false,
    "elements": [ { "t": "slug|action|character|paren|dialogue|transition", "text": "…", "p": 15, "y": 71.5, "y2": 83.1 } ]
  } ]
}
```

- `pg` / `pgEnd`: zero-based page position (page index + fraction down the page) of the scene start/end;
  `eighths` is the scene length in eighths of a page (scheduling unit).
- `elements` (only with `includesText`): the scene's text split by screenplay indent. Wrapped lines of one
  paragraph are joined. `p`/`y`/`y2` locate it on the page (points from the top) — for a future lined script.
- Watermarks are dropped by font, size and rotation, and body-font watermarks by repeating across pages off the
  12 pt line grid (also when fused into a real line). Revision asterisks, scene/page numbers, (MORE)/CONTINUED and
  running headers/footers are not elements.
- `onVolume` comes from Slugger's approach config (`lumo: YES`); `null` when unknown (a PDF read in the browser).

Checked against four production scripts (75–247 scenes): the browser reader and Slugger agree on every scene
number and page length; the browser keeps full slugs where a PDF splits them across text objects.
