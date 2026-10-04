# 360° environments

Put 360° (equirectangular, 2:1) videos or images in `environments/source/`, then run:

```
.\tools\make-360-proxies.ps1
```

Proxies land here (`*.mp4` / `*.jpg`) and are listed in `library.json`, which Mock & Roll reads
(LED → 360° environment → Library). Sources and proxies stay on this PC (git-ignored); only
`samples.json` + `samples/` ship with the app. Full guide: [docs/360-environments.md](../docs/360-environments.md).
