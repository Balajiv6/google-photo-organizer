"""Heuristic detector for construction-related photos."""

from typing import Any


def is_construction_photo(
    item: dict[str, Any],
    keywords: list[str],
    date_ranges: list[tuple[str, str]],
) -> bool:
    """Decide whether a mediaItem is a construction photo.

    A photo is classified as a construction photo when **either** of the
    following conditions is met (both are evaluated independently):

    1. A keyword from *keywords* appears (case-insensitive) in the
       concatenation of ``item["filename"]`` and ``item["description"]``.
    2. *date_ranges* is non-empty **and** the photo's creation date falls
       inside at least one of the supplied (start, end) inclusive ranges.

    Parameters
    ----------
    item:
        A mediaItem dict as returned by the Google Photos REST API.
    keywords:
        List of keyword strings to match against filename / description.
    date_ranges:
        List of ``("YYYY-MM-DD", "YYYY-MM-DD")`` inclusive date range tuples.
        Pass an empty list to skip date-range filtering.

    Returns
    -------
    bool
        ``True`` if the item matches at least one criterion.
    """
    # Build the text blob to search: filename + description (both optional).
    filename: str = item.get("filename", "") or ""
    description: str = item.get("description", "") or ""
    text: str = (filename + " " + description).lower()

    # Criterion 1: keyword match.
    if any(kw.lower() in text for kw in keywords):
        return True

    # Criterion 2: date-range match (only evaluated when ranges are specified).
    if date_ranges:
        # Support Takeout format (photoTakenTime: "YYYY-MM-DD") and
        # Google Photos API format (mediaMetadata.creationTime: RFC 3339).
        date_str: str = (
            item.get("photoTakenTime", "")
            or (item.get("mediaMetadata") or {}).get("creationTime", "")[:10]
            or ""
        )
        if date_str:
            for start, end in date_ranges:
                if start <= date_str <= end:
                    return True

    return False
