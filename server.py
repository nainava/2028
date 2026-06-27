"""2028 Tier List — Flask backend for shareable links + Wordle grids."""

import json
import re
import secrets
import sqlite3
import string
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=None)
DB_PATH = Path(__file__).parent / "2028.db"

# ── Canonical candidate list (must match JS order) ──────────────────────────

CANDIDATES = [
    # Dems
    {"id": "gavin-newsom",       "party": "D"},
    {"id": "kamala-harris",      "party": "D"},
    {"id": "pete-buttigieg",     "party": "D"},
    {"id": "aoc",                "party": "D"},
    {"id": "tim-walz",           "party": "D"},
    {"id": "bernie-sanders",     "party": "D"},
    {"id": "elizabeth-warren",   "party": "D"},
    {"id": "cory-booker",        "party": "D"},
    {"id": "jb-pritzker",        "party": "D"},
    {"id": "gretchen-whitmer",   "party": "D"},
    {"id": "mark-kelly",         "party": "D"},
    {"id": "amy-klobuchar",      "party": "D"},
    {"id": "andy-beshear",       "party": "D"},
    {"id": "wes-moore",          "party": "D"},
    {"id": "josh-shapiro",       "party": "D"},
    {"id": "john-fetterman",     "party": "D"},
    {"id": "ro-khanna",          "party": "D"},
    {"id": "jon-ossoff",         "party": "D"},
    {"id": "rahm-emanuel",       "party": "D"},
    {"id": "andrew-cuomo",       "party": "D"},
    {"id": "josh-green",         "party": "D"},
    # GOP
    {"id": "jd-vance",                  "party": "R"},
    {"id": "marco-rubio",               "party": "R"},
    {"id": "ron-desantis",              "party": "R"},
    {"id": "donald-trump-jr",           "party": "R"},
    {"id": "ted-cruz",                  "party": "R"},
    {"id": "vivek-ramaswamy",           "party": "R"},
    {"id": "tulsi-gabbard",             "party": "R"},
    {"id": "rfk-jr",                    "party": "R"},
    {"id": "nikki-haley",               "party": "R"},
    {"id": "sarah-huckabee-sanders",    "party": "R"},
    {"id": "brian-kemp",                "party": "R"},
    {"id": "tim-scott",                 "party": "R"},
    {"id": "marjorie-taylor-greene",    "party": "R"},
    {"id": "glenn-youngkin",            "party": "R"},
    {"id": "greg-abbott",               "party": "R"},
    # Rogues (mixed parties)
    {"id": "graham-platner",     "party": "D", "rogue": True},
    {"id": "dan-osborn",         "party": "I", "rogue": True},
    {"id": "mark-cuban",         "party": "D", "rogue": True},
    {"id": "jasmine-crockett",   "party": "D", "rogue": True},
    {"id": "stephen-a-smith",    "party": "D", "rogue": True},
    {"id": "tucker-carlson",     "party": "R", "rogue": True},
    {"id": "joe-rogan",          "party": "R", "rogue": True},
    {"id": "pete-hegseth",       "party": "R", "rogue": True},
    {"id": "thomas-massie",      "party": "R", "rogue": True},
]

TIER_EMOJI = {
    "S": "\U0001f7e5",  # red square
    "A": "\U0001f7e7",  # orange square
    "B": "\U0001f7e8",  # yellow square
    "C": "\U0001f7e9",  # green square
    "D": "\U0001f7e6",  # blue square
    "F": "\U0001f7ea",  # purple square
}
UNRANKED_EMOJI = "\u2b1c"  # white square

PARTY_PREFIX = {"D": "\U0001f535", "R": "\U0001f534", "I": "\u26a1"}  # rogue group uses I prefix


# ── Database ────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            tiers TEXT NOT NULL,
            customs TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    db.commit()
    db.close()


# ── Helpers ─────────────────────────────────────────────────────────────────

def gen_id(length=6):
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_wordle_grid(name, tiers):
    """Build Wordle-style emoji grid from tier assignments.

    Groups candidates by party with emoji prefixes.
    Custom candidates are excluded (not in canonical list).
    """
    # Split canonical candidates into groups
    dems = [c for c in CANDIDATES if c["party"] == "D" and not c.get("rogue")]
    gop = [c for c in CANDIDATES if c["party"] == "R" and not c.get("rogue")]
    rogues = [c for c in CANDIDATES if c.get("rogue")]

    def row(prefix, group):
        squares = "".join(
            TIER_EMOJI.get(tiers.get(c["id"], ""), UNRANKED_EMOJI)
            for c in group
        )
        return f"{prefix} {squares}"

    lines = [
        f"2028 Tier List \u2014 {name}",
        row("\U0001f535", dems),
        row("\U0001f534", gop),
        row("\u26a1", rogues),
        f"S{TIER_EMOJI['S']} A{TIER_EMOJI['A']} B{TIER_EMOJI['B']} C{TIER_EMOJI['C']} D{TIER_EMOJI['D']} F{TIER_EMOJI['F']}",
    ]
    return "\n".join(lines)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(Path(__file__).parent, "2028.html")


@app.route("/tierzoo.png")
def logo():
    return send_from_directory(Path(__file__).parent, "tierzoo.png")


@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip() or "Anon"
    tiers = data.get("tiers", {})
    customs = data.get("customs", [])

    if not isinstance(tiers, dict):
        return jsonify(error="tiers must be an object"), 400

    db = get_db()
    for _ in range(10):
        sid = gen_id()
        try:
            db.execute(
                "INSERT INTO submissions (id, name, tiers, customs) VALUES (?, ?, ?, ?)",
                (sid, name[:32], json.dumps(tiers), json.dumps(customs)),
            )
            db.commit()
            break
        except sqlite3.IntegrityError:
            continue
    else:
        return jsonify(error="could not generate unique id"), 500

    grid = build_wordle_grid(name, tiers)
    url = request.host_url.rstrip("/") + "/" + sid

    return jsonify(id=sid, url=url, grid=grid)


@app.route("/api/submission/<sid>")
def get_submission(sid):
    db = get_db()
    row = db.execute("SELECT * FROM submissions WHERE id = ?", (sid,)).fetchone()
    if not row:
        return jsonify(error="not found"), 404
    return jsonify(
        id=row["id"],
        name=row["name"],
        tiers=json.loads(row["tiers"]),
        customs=json.loads(row["customs"]),
        created_at=row["created_at"],
    )


@app.route("/<path:path>")
def catch_all(path):
    """Serve 2028.html for 6-char short IDs (shared view). Let other paths 404."""
    if re.fullmatch(r"[a-z0-9]{6}", path):
        return send_from_directory(Path(__file__).parent, "2028.html")
    return jsonify(error="not found"), 404


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
