"""google-photos-organizer — main entry point (Takeout mode).

This version reads photo metadata from a Google Takeout export, classifies
photos by keyword and/or date range, and produces actionable CSV reports.

Run:
    python src/main.py

Prerequisites:
    1. Export your library via https://takeout.google.com/ (Google Photos only)
    2. Extract the downloaded zip file
    3. Set TAKEOUT_PATH in config.py to the extracted folder path
"""

from __future__ import annotations

import csv
import pathlib
from typing import Any

import config
from detector import is_construction_photo
from takeout_reader import load_takeout


def _step1_construction(
    all_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify construction photos.

    Returns
    -------
    tuple
        ``(all_construction, not_yet_in_album)`` — the full set of
        construction photos and the subset not already in the album.
    """
    print("\n=== Step 1: Construction Photos ===")

    candidates = [
        item for item in all_items
        if is_construction_photo(
            item, config.CONSTRUCTION_KEYWORDS, config.CONSTRUCTION_DATE_RANGES
        )
    ]
    print(f"  Construction photos detected : {len(candidates)}")

    already_in = [
        item for item in candidates
        if config.CONSTRUCTION_ALBUM_TITLE in item.get("albums", [])
    ]
    to_add = [
        item for item in candidates
        if config.CONSTRUCTION_ALBUM_TITLE not in item.get("albums", [])
    ]

    print(f"  Already in album             : {len(already_in)}")
    print(f"  To be added                  : {len(to_add)}")

    if to_add:
        print("  Sample items:")
        for item in to_add[:5]:
            print(f"    • {item['filename']}  ({item.get('photoTakenTime', 'no date')})")
        if len(to_add) > 5:
            print(f"    … and {len(to_add) - 5} more")

    return candidates, to_add


def _step2_unalbumized(
    all_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return photos that do not belong to any album."""
    print("\n=== Step 2: Unalbumized Photos ===")
    unalbumized = [item for item in all_items if not item.get("albums")]
    print(f"  Unalbumized photos found     : {len(unalbumized)}")
    return unalbumized


def _save_reports(
    construction_items: list[dict[str, Any]],
    unalbumized_items: list[dict[str, Any]],
) -> pathlib.Path:
    """Write CSV reports and return the report directory path."""
    report_dir = pathlib.Path(config.REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)

    # Construction photos CSV
    construction_csv = report_dir / "construction_photos.csv"
    with open(construction_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["filename", "date", "current_albums", "google_photos_url", "filepath"])
        for item in construction_items:
            writer.writerow([
                item.get("filename", ""),
                item.get("photoTakenTime", ""),
                "; ".join(item.get("albums", [])),
                item.get("url", ""),
                item.get("filepath", ""),
            ])

    # Unalbumized photos CSV
    unalbumized_csv = report_dir / "unalbumized_photos.csv"
    with open(unalbumized_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["filename", "date", "google_photos_url", "filepath"])
        for item in unalbumized_items:
            writer.writerow([
                item.get("filename", ""),
                item.get("photoTakenTime", ""),
                item.get("url", ""),
                item.get("filepath", ""),
            ])

    print(f"\nReports saved to : {report_dir.resolve()}")
    print(f"  construction_photos.csv  — {len(construction_items)} photos")
    print(f"  unalbumized_photos.csv   — {len(unalbumized_items)} photos")
    return report_dir


def _print_summary(
    total: int,
    construction_count: int,
    unalbumized_count: int,
    report_dir: pathlib.Path,
) -> None:
    """Print a formatted summary table and next-step instructions."""
    mode = "DRY RUN (no changes made)" if config.DRY_RUN else "LIVE (changes applied)"
    date_filter = (
        ", ".join(f"{s} → {e}" for s, e in config.CONSTRUCTION_DATE_RANGES)
        if config.CONSTRUCTION_DATE_RANGES
        else "keyword match only"
    )
    width = 58
    print("\n" + "=" * width)
    print("  SUMMARY")
    print("=" * width)
    print(f"  {'Total photos scanned':<36} {total:>8}")
    print(f"  {'Construction photos found':<36} {construction_count:>8}")
    print(f"  {'Unalbumized photos found':<36} {unalbumized_count:>8}")
    print(f"  {'Date filter':<36} {date_filter}")
    print(f"  {'Mode':<36} {mode}")
    print("=" * width)
    print(f"\n  CSV reports : {report_dir.resolve()}")
    print("\n  Next steps to create albums in Google Photos:")
    print(f"  1. Open construction_photos.csv")
    print(f"     Each row has a 'google_photos_url' link — click to open the photo")
    print(f"  2. In Google Photos web UI, multi-select those photos and")
    print(f"     'Add to album → {config.CONSTRUCTION_ALBUM_TITLE}'")
    print(f"  3. Repeat with unalbumized_photos.csv → '{config.UNCATEGORIZED_ALBUM_TITLE}'")
    print(f"  4. Or wait for Google Photos API access to be restored for full automation")


def main() -> None:
    """Orchestrate the Takeout-based photo organisation workflow."""
    print("google-photos-organizer starting …")
    print(f"Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")

    if not config.TAKEOUT_PATH:
        print("\n[ERROR] TAKEOUT_PATH is not set in config.py")
        print("  Follow these steps to export your Google Photos:")
        print("  1. Go to https://takeout.google.com/")
        print("  2. Click 'Deselect all', then tick 'Google Photos' only")
        print("  3. Choose: .zip format, 'Export once', max file size 10 GB")
        print("  4. Click 'Create export' and wait for the download email")
        print("  5. Download and extract the zip file")
        print("  6. Set TAKEOUT_PATH in config.py to the extracted folder")
        return

    print(f"\nLoading Takeout export from: {config.TAKEOUT_PATH}")
    try:
        all_items = load_takeout(config.TAKEOUT_PATH)
    except FileNotFoundError as exc:
        print(f"\n[ERROR] {exc}")
        return

    print(f"  {len(all_items)} photo(s) loaded.")

    if not all_items:
        print("[ERROR] No photos found. Check that TAKEOUT_PATH is correct.")
        return

    # Classify
    construction_all, _construction_to_add = _step1_construction(all_items)
    unalbumized = _step2_unalbumized(all_items)

    # Save CSV reports (always, regardless of DRY_RUN)
    report_dir = _save_reports(construction_all, unalbumized)

    # Summary
    _print_summary(len(all_items), len(construction_all), len(unalbumized), report_dir)


if __name__ == "__main__":
    main()
