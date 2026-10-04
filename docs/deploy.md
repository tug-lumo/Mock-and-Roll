# Deploying Mock & Roll

The configurator is a static site: everything (3D, reflections, camera tools) runs in the
viewer's browser. Hosting = serving `index.html` + `vendor/` + `brand/` behind a login.

**Setup:** GitHub (private repo) → **Cloudflare Pages** (auto-deploys every push) →
**Cloudflare Access** (Google Workspace login in front). Free at our size.

## 1. GitHub — one time

1. Create a **private** repo on github.com, e.g. `lumostage/mock-and-roll` (no README/licence — the project already has them).
2. In this folder:
   ```
   git remote add origin https://github.com/<org>/mock-and-roll.git
   git push -u origin main
   ```
   Windows' Git Credential Manager pops up a GitHub sign-in the first time.

After that, shipping a change is just `git push`.

## 2. Cloudflare Pages — one time

1. dash.cloudflare.com → sign up / sign in with the company Google account.
2. **Workers & Pages → Create → Pages → Connect to Git** → authorise GitHub → pick the repo.
3. Build settings:
   - Production branch: `main`
   - Framework preset: **None**
   - Build command: `sh scripts/build.sh`
   - Build output directory: `dist`
4. **Save and Deploy.** You get `https://<project>.pages.dev`.

`scripts/build.sh` copies **only** the app files into `dist/` — `docs/`, reference material,
`.claude/` and `serve.py` are never published.

## 3. Cloudflare Access (the login) — one time

1. dash.cloudflare.com → **Zero Trust** (pick the free plan; a card may be asked for, not charged).
2. **Settings → Authentication → Login methods → Add new → Google Workspace** (follow the
   wizard: it has you create an OAuth client in Google Cloud console — ~10 minutes).
   Also keep **One-time PIN** enabled — that's how people *outside* the company get in.
3. **Access → Applications → Add → Self-hosted**:
   - Application domain: `<project>.pages.dev` (and the preview domain `*.<project>.pages.dev`)
   - Policy **"Lumostage staff"**: Action *Allow*, Include → *Emails ending in* `@lumostage.com`
   - Policy **"Guests"** (optional): Action *Allow*, Include → *Emails* → add a specific address
4. Save. Visiting the site now asks for a Google login (staff) or emails a one-time code (guests).

**Giving someone a login to play with it:** add their email to the *Guests* policy. They get a
6-digit code by email each time — no account to create. Remove the email to revoke.

## What works where

| | Local (`serve.py`, this PC) | Hosted (Pages) |
|---|---|---|
| Everything in the 3D app | ✓ | ✓ |
| Layouts / imported models | per browser | per browser |
| Save / Open layout (.json) | ✓ | ✓ |
| "Publish to phone" | ✓ | — (local only) |
| Shared layout links | `?config=published/layout.json` | commit a file to `layouts/`, open `…/?config=layouts/name.json&view` |

Each person's layouts and imported models stay in **their own browser** until a shared library
is built (step 2 in the roadmap: save/open from a team library, shared models and LED content).

## Local development

```
pythonw serve.py          # http://127.0.0.1:8137/  (loopback only)
tailscale serve --bg 8137 # optional: private link for your own devices
```
