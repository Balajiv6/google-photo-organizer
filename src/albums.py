"""Google Photos REST API client.

All public functions accept a ``google.oauth2.credentials.Credentials`` object
and return plain Python data structures (lists, dicts, sets, ints).  HTTP 429
responses are automatically retried with exponential back-off (up to 3
attempts).  Paginated endpoints sleep 0.3 s between pages to stay within
quota limits.
"""

import time
from typing import Any

import requests
from google.oauth2.credentials import Credentials

import config

_MAX_RETRIES: int = 3
_PAGINATE_SLEEP: float = 0.3


# --------------------------------------------------------------------------- #
#  Internal helpers
# --------------------------------------------------------------------------- #


def _auth_headers(creds: Credentials) -> dict[str, str]:
    """Return the Authorization header dict for *creds*."""
    return {"Authorization": f"Bearer {creds.token}"}


def _request(
    method: str,
    url: str,
    creds: Credentials,
    **kwargs: Any,
) -> requests.Response:
    """Make an authenticated HTTP request with exponential back-off on HTTP 429.

    Parameters
    ----------
    method:
        HTTP verb (``"GET"``, ``"POST"``, …).
    url:
        Fully-qualified URL.
    creds:
        Valid Google credentials — used to build the Authorization header.
    **kwargs:
        Extra keyword arguments forwarded verbatim to ``requests.request``.

    Returns
    -------
    requests.Response
        The successful response (2xx).

    Raises
    ------
    requests.HTTPError
        After *_MAX_RETRIES* failed attempts on HTTP 429, or immediately on
        any other non-2xx error.
    """
    headers = {**_auth_headers(creds), **kwargs.pop("headers", {})}

    for attempt in range(_MAX_RETRIES):
        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 429:
            wait = 2 ** attempt
            print(
                f"  [rate-limit] HTTP 429 — retrying in {wait}s "
                f"(attempt {attempt + 1}/{_MAX_RETRIES})"
            )
            time.sleep(wait)
            continue

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise requests.HTTPError(
                f"{method} {url} failed with {response.status_code}: {response.text}"
            ) from exc

        return response

    # All retries exhausted on 429.
    raise requests.HTTPError(
        f"{method} {url} — still receiving HTTP 429 after {_MAX_RETRIES} retries."
    )


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #


def list_all_media_items(creds: Credentials) -> list[dict[str, Any]]:
    """Return every mediaItem in the authenticated user's Google Photos library.

    Uses ``POST /mediaItems:search`` with no filter so the API returns all
    items — not just those uploaded by this app.

    Parameters
    ----------
    creds:
        Valid Google credentials.

    Returns
    -------
    list[dict]
        All mediaItem dicts, in unspecified order.
    """
    url = f"{config.API_BASE}/mediaItems:search"
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        body: dict[str, Any] = {"pageSize": config.BATCH_SIZE}
        if page_token:
            body["pageToken"] = page_token

        try:
            resp = _request("POST", url, creds, json=body)
        except requests.HTTPError as exc:
            print(f"  [error] Failed to list media items: {exc}")
            raise

        data = resp.json()
        items.extend(data.get("mediaItems", []))

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(_PAGINATE_SLEEP)

    return items


def list_all_albums(creds: Credentials) -> dict[str, str]:
    """Return a mapping of album title → album ID for all albums.

    Parameters
    ----------
    creds:
        Valid Google credentials.

    Returns
    -------
    dict[str, str]
        ``{title: album_id}`` for every album visible to the authenticated
        user.
    """
    url = f"{config.API_BASE}/albums"
    albums: dict[str, str] = {}
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {"pageSize": 50}
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = _request("GET", url, creds, params=params)
        except requests.HTTPError as exc:
            print(f"  [error] Failed to list albums: {exc}")
            raise

        data = resp.json()
        for album in data.get("albums", []):
            albums[album.get("title", "")] = album["id"]

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(_PAGINATE_SLEEP)

    return albums


def get_items_in_album(creds: Credentials, album_id: str) -> set[str]:
    """Return the set of mediaItem IDs that belong to *album_id*.

    Parameters
    ----------
    creds:
        Valid Google credentials.
    album_id:
        The Google Photos album ID.

    Returns
    -------
    set[str]
        All mediaItem IDs present in the album.
    """
    url = f"{config.API_BASE}/mediaItems:search"
    ids: set[str] = set()
    page_token: str | None = None

    while True:
        body: dict[str, Any] = {"albumId": album_id, "pageSize": config.BATCH_SIZE}
        if page_token:
            body["pageToken"] = page_token

        try:
            resp = _request("POST", url, creds, json=body)
        except requests.HTTPError as exc:
            print(f"  [error] Failed to get items in album {album_id!r}: {exc}")
            raise

        data = resp.json()
        for item in data.get("mediaItems", []):
            ids.add(item["id"])

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(_PAGINATE_SLEEP)

    return ids


def create_album(creds: Credentials, title: str) -> str:
    """Create a new album with *title* and return its ID.

    Parameters
    ----------
    creds:
        Valid Google credentials.
    title:
        Display name for the new album.

    Returns
    -------
    str
        The newly created album's ID.
    """
    url = f"{config.API_BASE}/albums"
    body = {"album": {"title": title}}

    try:
        resp = _request("POST", url, creds, json=body)
    except requests.HTTPError as exc:
        print(f"  [error] Failed to create album {title!r}: {exc}")
        raise

    return resp.json()["id"]


def add_items_to_album(
    creds: Credentials, album_id: str, item_ids: list[str]
) -> int:
    """Add *item_ids* to *album_id*, batching in groups of 50 (API hard limit).

    Parameters
    ----------
    creds:
        Valid Google credentials.
    album_id:
        Target album ID.
    item_ids:
        List of mediaItem IDs to add.

    Returns
    -------
    int
        Total number of items successfully submitted to the API.
    """
    url = f"{config.API_BASE}/albums/{album_id}/batchAddMediaItems"
    added = 0

    for i in range(0, len(item_ids), config.BATCH_SIZE):
        chunk = item_ids[i : i + config.BATCH_SIZE]
        body = {"mediaItemIds": chunk}

        try:
            _request("POST", url, creds, json=body)
            added += len(chunk)
        except requests.HTTPError as exc:
            print(f"  [error] Failed to add batch to album {album_id!r}: {exc}")
            raise

    return added
