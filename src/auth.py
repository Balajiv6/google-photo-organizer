"""OAuth 2.0 authentication helpers for Google Photos."""

import os
import pathlib
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import config

_SCOPES: list[str] = ["https://www.googleapis.com/auth/photoslibrary"]

# Credential files are kept at the project root (one level above this src/ dir).
_PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
_CREDENTIALS_PATH: pathlib.Path = _PROJECT_ROOT / config.CREDENTIALS_FILE
_TOKEN_PATH: pathlib.Path = _PROJECT_ROOT / config.TOKEN_FILE


def get_credentials() -> Credentials:
    """Return valid Google OAuth 2.0 credentials.

    Loads a cached token from ``TOKEN_FILE`` when available and refreshes it
    if expired.  Falls back to a full browser-based ``InstalledAppFlow`` when
    no cached token exists.  The resulting token is always written back to
    ``TOKEN_FILE`` so subsequent runs skip the browser step.

    Returns
    -------
    Credentials
        A valid, non-expired Credentials object ready for API calls.

    Raises
    ------
    FileNotFoundError
        If ``CREDENTIALS_FILE`` does not exist and no cached token is
        available.
    """
    creds: Optional[Credentials] = None

    if _TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not _CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"OAuth credentials file not found: {_CREDENTIALS_PATH}. "
                "Download it from the Google Cloud Console and place it in the "
                "project root directory."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(_CREDENTIALS_PATH), _SCOPES
        )
        creds = flow.run_local_server(port=0)

    # Persist the (new or refreshed) token for the next run.
    _TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds
