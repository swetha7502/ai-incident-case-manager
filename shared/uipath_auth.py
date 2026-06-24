# shared/uipath_auth.py
# Shared UiPath OAuth2 helper — imported by fire_incident.py and freeze.py
# to avoid duplicating the token-fetching logic.

import os
import requests
from dotenv import load_dotenv

# Load .env from the repo root (two levels up from this file: shared/ → repo root)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)


def get_token() -> str:
    """
    Request a fresh OAuth2 bearer token from UiPath Cloud using the
    client_credentials grant. Tokens are short-lived — always call this
    per script run, never cache across runs.

    Returns:
        str: The access token string.

    Raises:
        RuntimeError: If the token request fails (non-200 status or missing token).
        ValueError: If required environment variables are not set.
    """
    auth_url = os.getenv("UIPATH_AUTH_URL")
    client_id = os.getenv("UIPATH_CLIENT_ID")
    client_secret = os.getenv("UIPATH_CLIENT_SECRET")

    missing = [k for k, v in {
        "UIPATH_AUTH_URL": auth_url,
        "UIPATH_CLIENT_ID": client_id,
        "UIPATH_CLIENT_SECRET": client_secret,
    }.items() if not v or v.startswith("# B:")]

    if missing:
        raise ValueError(
            f"Missing or unfilled environment variables: {', '.join(missing)}\n"
            "Edit .env at the repo root and set these values before running."
        )

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        response = requests.post(auth_url, data=payload, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error reaching UiPath auth endpoint: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"UiPath auth request failed.\n"
            f"Status: {response.status_code}\n"
            f"Body: {response.text}"
        )

    token_data = response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise RuntimeError(
            f"Auth response did not contain 'access_token'.\nFull response: {token_data}"
        )

    return access_token
