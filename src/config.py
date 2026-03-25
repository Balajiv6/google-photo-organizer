"""Central configuration for google-photos-organizer.

Edit this file to customise behaviour — no other file needs to change.

The ``DRY_RUN`` flag can also be overridden at runtime via the environment
variable ``ORGANIZER_DRY_RUN`` (set to ``false`` / ``0`` / ``no`` to apply
changes without editing this file — useful for CI / GitHub Actions).
"""

import os

# --------------------------------------------------------------------------- #
#  Runtime mode
# --------------------------------------------------------------------------- #
# Default: True (safe preview).  Override: set ORGANIZER_DRY_RUN=false in env.
DRY_RUN: bool = os.environ.get("ORGANIZER_DRY_RUN", "true").lower() not in (
    "false",
    "0",
    "no",
)

# --------------------------------------------------------------------------- #
#  OAuth / credential files
# --------------------------------------------------------------------------- #
CREDENTIALS_FILE: str = "credentials.json"
TOKEN_FILE: str = "token.json"

# --------------------------------------------------------------------------- #
#  Album titles
# --------------------------------------------------------------------------- #
CONSTRUCTION_ALBUM_TITLE: str = "Cauvery Nagar Home"
UNCATEGORIZED_ALBUM_TITLE: str = "Uncategorized"

# --------------------------------------------------------------------------- #
#  Construction detection
# --------------------------------------------------------------------------- #
CONSTRUCTION_KEYWORDS: list[str] = [
    "construction",
    "cement",
    "bricks",
    "foundation",
    "plumbing",
    "tiles",
    "flooring",
    "paint",
    "slab",
    "site",
    "cauvery",
    "nagar",
    "renovation",
    "interior",
    "contractor",
    "scaffold",
    "roof",
    "architect",
]

# Each tuple is an inclusive (start, end) date range in "YYYY-MM-DD" format.
# Leave empty to skip date-range filtering entirely.
#
# At runtime, the env vars ORGANIZER_DATE_FROM / ORGANIZER_DATE_TO (both
# "YYYY-MM-DD") override this list entirely — useful when triggering from
# GitHub Actions or the GitHub Pages site without editing this file.
import datetime as _dt

_env_date_from: str = os.environ.get("ORGANIZER_DATE_FROM", "").strip()
_env_date_to:   str = os.environ.get("ORGANIZER_DATE_TO",   "").strip()

if _env_date_from:
    _date_to_resolved = _env_date_to or _dt.date.today().strftime("%Y-%m-%d")
    CONSTRUCTION_DATE_RANGES: list[tuple[str, str]] = [(_env_date_from, _date_to_resolved)]
else:
    # Default: no date filtering — rely on keyword matching only.
    CONSTRUCTION_DATE_RANGES: list[tuple[str, str]] = []

# --------------------------------------------------------------------------- #
#  API settings
# --------------------------------------------------------------------------- #
API_BASE: str = "https://photoslibrary.googleapis.com/v1"
BATCH_SIZE: int = 50
