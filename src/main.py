"""google-photos-organizer — main entry point.

Run:
    python main.py

By default this operates in DRY_RUN mode (config.DRY_RUN = True) and only
prints what it *would* do.  Set DRY_RUN = False in config.py to apply changes.
"""

from __future__ import annotations

from typing import Any

import config
from auth import get_credentials
from albums import (
    add_items_to_album,
    create_album,
    get_items_in_album,
    list_all_albums,
    list_all_media_items,
)
from detector import is_construction_photo


def _step1_construction(
    creds: Any,
    all_items: list[dict[str, Any]],
    albums: dict[str, str],
) -> int:
    """Tag construction photos and add them to the construction album.

    Parameters
    ----------
    creds:
        Valid Google credentials.
    all_items:
        Full library item list.
    albums:
        Current ``{title: album_id}`` mapping (mutated if a new album is
        created).

    Returns
    -------
    int
        Number of items found (or that would be added in dry-run mode).
    """
    print("\n=== Step 1: Construction Photos ===")

    candidates = [
        item
        for item in all_items
        if is_construction_photo(
            item, config.CONSTRUCTION_KEYWORDS, config.CONSTRUCTION_DATE_RANGES
        )
    ]
    print(f"  Construction photos detected : {len(candidates)}")

    if not candidates:
        return 0

    # Determine which are already in the album to avoid duplicate additions.
    existing_ids: set[str] = set()
    if config.CONSTRUCTION_ALBUM_TITLE in albums:
        album_id = albums[config.CONSTRUCTION_ALBUM_TITLE]
        print(f"  Album already exists (id={album_id}) — fetching current members …")
        existing_ids = get_items_in_album(creds, album_id)

    to_add = [item for item in candidates if item["id"] not in existing_ids]
    print(f"  Already in album             : {len(candidates) - len(to_add)}")
    print(f"  To be added                  : {len(to_add)}")

    if not to_add:
        return 0

    if config.DRY_RUN:
        print("  [DRY RUN] Would add the following items:")
        for item in to_add[:10]:
            print(f"    • {item.get('filename', item['id'])}")
        if len(to_add) > 10:
            print(f"    … and {len(to_add) - 10} more")
    else:
        if config.CONSTRUCTION_ALBUM_TITLE not in albums:
            print(f"  Creating album {config.CONSTRUCTION_ALBUM_TITLE!r} …")
            album_id = create_album(creds, config.CONSTRUCTION_ALBUM_TITLE)
            albums[config.CONSTRUCTION_ALBUM_TITLE] = album_id

        album_id = albums[config.CONSTRUCTION_ALBUM_TITLE]
        added = add_items_to_album(creds, album_id, [item["id"] for item in to_add])
        print(f"  Added {added} item(s) to {config.CONSTRUCTION_ALBUM_TITLE!r}.")

    return len(to_add)


def _step2_uncategorized(
    creds: Any,
    all_items: list[dict[str, Any]],
    albums: dict[str, str],
) -> int:
    """Collect items that belong to no album and add them to "Uncategorized".

    Parameters
    ----------
    creds:
        Valid Google credentials.
    all_items:
        Full library item list.
    albums:
        Current ``{title: album_id}`` mapping (mutated if a new album is
        created).

    Returns
    -------
    int
        Number of unalbumized items found (or that would be added in
        dry-run mode).
    """
    print("\n=== Step 2: Unalbumized Photos ===")

    # Build the union of all item IDs that already belong to at least one album.
    all_album_ids: set[str] = set()
    print(f"  Scanning {len(albums)} album(s) for existing memberships …")
    for title, album_id in albums.items():
        album_item_ids = get_items_in_album(creds, album_id)
        all_album_ids.update(album_item_ids)
        print(f"    {title!r}: {len(album_item_ids)} item(s)")

    all_item_ids = {item["id"] for item in all_items}
    unalbumized_ids = list(all_item_ids - all_album_ids)
    print(f"  Unalbumized items found      : {len(unalbumized_ids)}")

    if not unalbumized_ids:
        return 0

    if config.DRY_RUN:
        print(
            f"  [DRY RUN] Would add {len(unalbumized_ids)} item(s) to "
            f"{config.UNCATEGORIZED_ALBUM_TITLE!r}."
        )
    else:
        if config.UNCATEGORIZED_ALBUM_TITLE not in albums:
            print(f"  Creating album {config.UNCATEGORIZED_ALBUM_TITLE!r} …")
            album_id = create_album(creds, config.UNCATEGORIZED_ALBUM_TITLE)
            albums[config.UNCATEGORIZED_ALBUM_TITLE] = album_id

        album_id = albums[config.UNCATEGORIZED_ALBUM_TITLE]
        added = add_items_to_album(creds, album_id, unalbumized_ids)
        print(f"  Added {added} item(s) to {config.UNCATEGORIZED_ALBUM_TITLE!r}.")

    return len(unalbumized_ids)


def _print_summary(
    total: int,
    construction_count: int,
    unalbumized_count: int,
) -> None:
    """Print a formatted summary table to stdout."""
    mode = "DRY RUN (no changes made)" if config.DRY_RUN else "LIVE (changes applied)"
    date_filter = (
        ", ".join(f"{s} → {e}" for s, e in config.CONSTRUCTION_DATE_RANGES)
        if config.CONSTRUCTION_DATE_RANGES
        else "keyword match only"
    )
    width = 50
    print("\n" + "=" * width)
    print("  SUMMARY")
    print("=" * width)
    print(f"  {'Total photos scanned':<32} {total:>8}")
    print(f"  {'Construction photos found':<32} {construction_count:>8}")
    print(f"  {'Unalbumized photos found':<32} {unalbumized_count:>8}")
    print(f"  {'Date filter':<32} {date_filter}")
    print(f"  {'Mode':<32} {mode}")
    print("=" * width)


def main() -> None:
    """Orchestrate the two-step Google Photos organisation workflow."""
    print("google-photos-organizer starting …")
    print(f"Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")

    # Authenticate.
    print("\nAuthenticating …")
    creds = get_credentials()
    print("  OK")

    # Fetch the full library once — shared between both steps.
    print("\nFetching all media items (this may take a while for large libraries) …")
    all_items = list_all_media_items(creds)
    print(f"  {len(all_items)} item(s) found in library.")

    # Fetch current album list — shared and mutated as albums are created.
    print("\nFetching existing albums …")
    albums = list_all_albums(creds)
    print(f"  {len(albums)} album(s) found.")

    # Run the two steps.
    construction_count = _step1_construction(creds, all_items, albums)
    unalbumized_count = _step2_uncategorized(creds, all_items, albums)

    # Print summary.
    _print_summary(len(all_items), construction_count, unalbumized_count)


if __name__ == "__main__":
    main()
