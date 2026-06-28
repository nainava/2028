# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A "2028 US presidential contenders" tier-list ranker. The entire front-end app lives in a single self-contained file, `2028.html` (HTML + CSS + JS, no build step). `server.py` is an optional Flask backend that adds server-stored shareable links; the app also works without it via offline base64 share codes.

There is no build, lint, or test tooling. Edits to `2028.html` are plain file edits.

## Contributing workflow

This repo is worked on collaboratively. Never commit directly to `main`.

- **Every change goes on a new branch, then a pull request.** Branch off `main`, commit, push the branch, and open a PR for review/merge.
- **Pull with rebase** to keep history linear. Configured locally via `git config pull.rebase true` (run it again if you clone fresh, or set `--global`).
- **No `gh` CLI is installed**, so PRs can't be created from the terminal. After pushing a branch, open the PR via the compare URL: `https://github.com/nainava/2028/compare/main...<branch>?expand=1` (the `git push` output also prints a "Create a pull request" link).

## Running

```bash
pip install flask          # only dependency, not vendored
python3 server.py          # serves on http://localhost:5050, debug=True
```

- `server.py` auto-creates the SQLite DB (`2028.db`, gitignored) via `init_db()` on startup.
- Flask `debug=True` watches `server.py` and reloads it. `2028.html` is served fresh from disk on every request, so **front-end edits just need a browser refresh — no restart**.

## Architecture

### `2028.html` — the whole app
Organized into banner-commented JS sections (`DATA`, `STATE`, `RENDER`, `SORTABLE`, `FILTERS`, `NAME`, `SHARE IMAGE GENERATOR`, `SHARE FLOW (API)`, `COMPARE`, `RANDOMIZE`, `ASK AI`, `THEME TOGGLE`, `SHARED VIEW`, `INIT`). External deps are SortableJS (drag/drop) and html2canvas (image export), both via CDN.

- **State / persistence**: localStorage keys `2028_name`, `2028_tiers`, `2028_customs`, `2028_theme`. `tiers` is `{candidateId: "S"|"A"|"B"|"C"|"D"|"F"}`; unranked candidates are simply absent.
- **Candidate IDs**: derived client-side from the display name via `slug(name)` (lowercase, non-alphanumerics → `-`). The `CANDIDATES` array holds `{name, party, role, rogue?}`; IDs are assigned at load.
- **Custom candidates**: user-added entries (`2028_customs`), client-only, marked with a `★` badge. Carried inside share payloads but excluded from the server-side Wordle grid.

### Two independent share mechanisms
1. **Server links** (`SHARE FLOW (API)` + `SHARED VIEW`): `POST /api/submit` stores the list and returns a 6-char id + URL. Opening a URL whose path is a 6-char id makes `catch_all` serve `2028.html`, and the `SHARED VIEW` code reads `window.location.pathname` and `GET /api/submission/<id>` to render that list read-only.
2. **Offline base64 codes** (`COMPARE`): a `"TIER-<base64-json>"` string encoding name/tiers/customs, pasted into the Compare box. Works with no backend.

### `server.py` — Flask + SQLite
Routes: `/` (serve app), `/tierzoo.png` (logo), `POST /api/submit`, `GET /api/submission/<sid>`, `catch_all` (serves app for 6-char ids, else 404). Single `submissions` table (`id, name, tiers, customs, created_at`). `build_wordle_grid()` produces a shareable emoji grid returned from `/api/submit`.

## Critical cross-file invariant

`server.py`'s `CANDIDATES` list **duplicates the candidate ids and parties** from the JS in `2028.html` and must stay in sync. Adding, removing, or renaming a candidate requires editing **both** files — the server uses these ids to build the Wordle grid, and a rename changes the slug-derived id.

Known divergence to be aware of: the front-end removed the "rogue" category (no ⚡ badges/filter; rogues render by party), but `server.py` still groups by `rogue` (with an `I`/⚡ prefix) in `build_wordle_grid()` and `PARTY_PREFIX`. The Wordle grid therefore still reflects the old rogue grouping.

## Other notes

- The blue/red square summary image (referred to as the "heat map" in discussion) is `generateShareImage()` — a `<canvas>` drawing, so CSS doesn't affect it.
- `archive/index.html` is the **original static, no-backend** variant (base64 sharing only) kept for reference — not the live app, and the only version deployable to plain GitHub Pages (the root app needs a Python host). See `archive/README.md`.
