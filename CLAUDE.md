# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A "2028 US presidential contenders" tier-list ranker. The entire front-end app lives in a single self-contained file, `2028.html` (HTML + CSS + JS, no build step). The backend runs on Cloudflare Pages Functions with KV storage for shareable links; the app also works without it via offline base64 share codes.

There is no build, lint, or test tooling. Edits to `2028.html` are plain file edits.

## Contributing workflow

This repo is worked on collaboratively. Never commit directly to `main`.

- **Every change goes on a new branch, then a pull request.** Branch off `main`, commit, push the branch, and open a PR for review/merge.
- **Pull with rebase** to keep history linear. Configured locally via `git config pull.rebase true` (run it again if you clone fresh, or set `--global`).
- **Create the PR with `gh`**: `gh pr create --base main --head <branch>`. The `gh` CLI is installed at `~/.local/bin/gh` and authenticated as `nainava` (`repo` scope), so the whole branch → PR flow works from the terminal. (If `gh` is ever unavailable, fall back to the compare URL `https://github.com/nainava/2028/compare/main...<branch>?expand=1`.)

## Running

```bash
wrangler pages dev        # serves on http://localhost:8788
```

- `wrangler pages dev` serves `public/`, routes `/api/*` calls to `functions/`, and emulates KV locally.
- `2028.html` is the source of truth for the front end; it is copied to `public/index.html`. Front-end edits to `public/index.html` (or `2028.html` + copy) just need a browser refresh — no restart.

## Architecture

### `2028.html` — the whole app
Organized into banner-commented JS sections (`DATA`, `STATE`, `RENDER`, `SORTABLE`, `FILTERS`, `NAME`, `SHARE IMAGE GENERATOR`, `SHARE FLOW (API)`, `COMPARE`, `RANDOMIZE`, `ASK AI`, `THEME TOGGLE`, `SHARED VIEW`, `INIT`). External deps are SortableJS (drag/drop) and html2canvas (image export), both via CDN.

- **State / persistence**: localStorage keys `2028_name`, `2028_tiers`, `2028_customs`, `2028_theme`. `tiers` is `{candidateId: "S"|"A"|"B"|"C"|"D"|"F"}`; unranked candidates are simply absent.
- **Candidate IDs**: derived client-side from the display name via `slug(name)` (lowercase, non-alphanumerics → `-`). The `CANDIDATES` array holds `{name, party, role, rogue?}`; IDs are assigned at load.
- **Custom candidates**: user-added entries (`2028_customs`), client-only, marked with a `★` badge. Carried inside share payloads.

### Two independent share mechanisms
1. **Server links** (`SHARE FLOW (API)` + `SHARED VIEW`): `POST /api/submit` stores the list in KV and returns a 6-char id + URL. Opening a URL whose path is a 6-char id is rewritten to `index.html` via `public/_redirects`, and the `SHARED VIEW` code reads `window.location.pathname` and `GET /api/submission/<id>` to render that list read-only.
2. **Offline base64 codes** (`COMPARE`): a `"TIER-<base64-json>"` string encoding name/tiers/customs, pasted into the Compare box. Works with no backend.

### Cloudflare Pages Functions — the backend
- **`functions/api/submit.js`** — `onRequestPost`: validates the JSON body, generates a 6-char alphanumeric ID, stores `{id, name, tiers, customs, created_at}` in KV, and returns `{id, url}`.
- **`functions/api/submission/[id].js`** — `onRequestGet`: looks up the submission by ID from KV and returns it as JSON (or 404).
- **KV namespace**: `SUBMISSIONS` (binding configured in `wrangler.jsonc`).
- **SPA routing**: `public/_redirects` rewrites all non-file paths to `index.html` so shared-view URLs (6-char IDs) load the app.

## Other notes

- The blue/red square summary image (referred to as the "heat map" in discussion) is `generateShareImage()` — a `<canvas>` drawing, so CSS doesn't affect it.
- `archive/index.html` is the **original static, no-backend** variant (base64 sharing only) kept for reference — not the live app. See `archive/README.md`.
