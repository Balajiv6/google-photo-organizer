"""Parse a Google Takeout export to extract photo metadata and album membership.

Google Takeout organises photos like this after extraction::

    Takeout/
        Google Photos/
            Photos from 2022/      ← year folders (canonical source)
                photo.jpg
                photo.jpg.json     ← sidecar with metadata
            Photos from 2023/
                ...
            My Album Name/         ← album folders
                photo.jpg          ← same photo, may be duplicate
                photo.jpg.json

Photos already in an album appear in BOTH the year folder AND the album
folder.  This module uses year folders as the canonical source of all items
and album folders only to determine album membership.
"""

import datetime
import json
import re
from pathlib import Path
from typing import Any

_YEAR_FOLDER_RE = re.compile(r"^Photos from \d{4}$")
_SKIP_SUFFIXES: frozenset[str] = frozenset({".json", ".html", ".csv", ".txt"})


# --------------------------------------------------------------------------- #
#  Internal helpers
# --------------------------------------------------------------------------- #


def _find_photos_root(root: Path) -> Path | None:
    """Return the ``Google Photos`` sub-folder inside a Takeout tree."""
    candidates = [
        root,
        root / "Takeout" / "Google Photos",
        root / "Google Photos",
    ]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    # One extra level of recursion
    for child in root.iterdir():
        if child.is_dir() and child.name == "Google Photos":
            return child
    return None


def _find_sidecar(photo_path: Path) -> Path | None:
    """Return the JSON metadata sidecar for *photo_path*, or ``None``."""
    # Standard pattern: photo.jpg  → photo.jpg.json
    standard = photo_path.parent / (photo_path.name + ".json")
    if standard.exists():
        return standard

    # Google sometimes truncates long filenames before appending the extension.
    # e.g. averylongname(1).jpg → averylongname.jpg(1).json
    # Fall back to a stem-prefix search.
    stem = photo_path.stem
    for jf in photo_path.parent.glob("*.json"):
        inner = jf.name[: -len(".json")]  # e.g. "photo.jpg" or "photo(1).jpg"
        if inner == photo_path.name:
            return jf
        if len(stem) >= 46 and inner.startswith(stem[:46]):
            return jf

    return None


def _read_sidecar(sidecar: Path) -> dict[str, Any]:
    """Safely read and parse a JSON sidecar, returning {} on error."""
    try:
        return json.loads(sidecar.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def _timestamp_to_date(meta: dict[str, Any]) -> str:
    """Extract a ``YYYY-MM-DD`` date from a sidecar metadata dict."""
    ts_obj = meta.get("photoTakenTime") or meta.get("creationTime") or {}
    ts = ts_obj.get("timestamp", "")
    if ts:
        try:
            dt = datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            pass
    return ""


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #


def load_takeout(takeout_root: str) -> list[dict[str, Any]]:
    """Load all photos from a Google Takeout export directory.

    Parameters
    ----------
    takeout_root:
        Path to the extracted Takeout folder.  Both the outer ``Takeout/``
        folder and the ``Takeout/Google Photos`` sub-folder are accepted.

    Returns
    -------
    list[dict]
        One dict per unique photo with keys:

        ``filename``        — original file name (e.g. ``IMG_001.jpg``)
        ``description``     — user-entered description (may be empty)
        ``photoTakenTime``  — date the photo was taken, ``YYYY-MM-DD``
        ``filepath``        — absolute path to the photo file on disk
        ``albums``          — list of album names this photo belongs to
        ``url``             — Google Photos URL from sidecar (may be empty)

    Raises
    ------
    FileNotFoundError
        If no ``Google Photos`` sub-folder can be located.
    """
    root = Path(takeout_root).expanduser().resolve()
    photos_root = _find_photos_root(root)
    if photos_root is None:
        raise FileNotFoundError(
            f"Could not find a 'Google Photos' folder under {root}.\n"
            "Make sure TAKEOUT_PATH in config.py points to the extracted "
            "Takeout archive folder."
        )

    print(f"  Takeout root : {photos_root}")

    # Separate year folders from album folders
    year_folders: list[Path] = []
    album_folders: list[Path] = []
    for folder in sorted(photos_root.iterdir()):
        if not folder.is_dir():
            continue
        if _YEAR_FOLDER_RE.match(folder.name):
            year_folders.append(folder)
        else:
            album_folders.append(folder)

    print(f"  Year folders : {len(year_folders)}")
    print(f"  Album folders: {len(album_folders)}")

    # --- Phase 1: build album-membership maps from album folders ---
    # Keyed by Google Photos URL (reliable across duplicates) or filename.
    album_by_url:   dict[str, list[str]] = {}
    album_by_fname: dict[str, list[str]] = {}

    for folder in album_folders:
        for photo in folder.iterdir():
            if photo.suffix.lower() in _SKIP_SUFFIXES or not photo.is_file():
                continue
            sidecar = _find_sidecar(photo)
            url = _read_sidecar(sidecar).get("url", "") if sidecar else ""
            if url:
                album_by_url.setdefault(url, []).append(folder.name)
            else:
                album_by_fname.setdefault(photo.name.lower(), []).append(folder.name)

    # --- Phase 2: build canonical item list from year folders ---
    items: list[dict[str, Any]] = []
    seen_urls:  set[str] = set()
    seen_files: set[str] = set()

    for folder in year_folders:
        for photo in sorted(folder.iterdir()):
            if photo.suffix.lower() in _SKIP_SUFFIXES or not photo.is_file():
                continue

            sidecar = _find_sidecar(photo)
            meta = _read_sidecar(sidecar) if sidecar else {}
            description = meta.get("description", "") or ""
            url = meta.get("url", "") or ""
            date_str = _timestamp_to_date(meta)

            # Deduplicate: URL is the best key; fall back to absolute filepath
            if url:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
            else:
                fp_key = str(photo).lower()
                if fp_key in seen_files:
                    continue
                seen_files.add(fp_key)

            # Resolve album membership
            if url and url in album_by_url:
                albums = sorted(set(album_by_url[url]))
            else:
                albums = sorted(set(album_by_fname.get(photo.name.lower(), [])))

            items.append({
                "filename":       photo.name,
                "description":    description,
                "photoTakenTime": date_str,
                "filepath":       str(photo),
                "albums":         albums,
                "url":            url,
            })

    return items
