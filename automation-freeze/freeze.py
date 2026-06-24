# automation-freeze/freeze.py
#
# PURPOSE: Disable (freeze) a misbehaving automation in UiPath Orchestrator
# when an incident is escalated (compliance officer clicks Reject).
#
# TRIGGER MECHANISM: This script is run MANUALLY by B during the demo, immediately
# after clicking Reject in Action Center on camera. This is a deliberate design
# choice — in a production deployment this would be triggered automatically by the
# Escalated stage transition; for the hackathon demo it is triggered directly to
# clearly show the containment action without building an extra webhook integration.
#
# Usage:
#   python freeze.py --automation "Customer Complaint Classifier"
#
# [WARNING]  OPEN QUESTIONS — do not treat the Orchestrator API calls as working until
#     these are resolved with Swetha:
#
#   1. ORCHESTRATOR API CONTRACT: Swetha's documentation states "full code was
#      provided to B separately." If you have received that code, fill in the
#      TODOs below. If not, ask Swetha for:
#        - The exact endpoint URL pattern
#        - Whether X-UIPATH-OrganizationUnitId header is required (and what value)
#        - The request body shape for SetEnabled
#
#   2. DUMMY AUTOMATION IN ORCHESTRATOR: For this script to succeed, a Release
#      named to match one of the scenario automation_name values (e.g.
#      "Customer Complaint Classifier") must actually exist in Swetha's Orchestrator
#      tenant. Confirm with Swetha whether this has been created.
#
# Until those questions are answered, the token-fetching and CLI scaffolding work,
# but the actual API calls are stubs and will not succeed against the live tenant.

import argparse
import os
import sys
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the repo root (one level up from automation-freeze/)
# ---------------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)

# ---------------------------------------------------------------------------
# Add shared/ to the path so we can import get_token from uipath_auth.py
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from uipath_auth import get_token  # noqa: E402

# ---------------------------------------------------------------------------
# Orchestrator base URL — constructed from org/tenant IDs per standard UiPath
# Orchestrator REST API conventions. Update if Swetha confirms a different pattern.
# ---------------------------------------------------------------------------
_ORG_ID = os.getenv("UIPATH_ORG_ID", "")
_TENANT_ID = os.getenv("UIPATH_TENANT_ID", "")
_ORCHESTRATOR_BASE = (
    f"https://cloud.uipath.com/{_ORG_ID}/{_TENANT_ID}/orchestrator_"
)


def _get_release_id(automation_name: str, token: str) -> int | None:
    """
    Look up the Orchestrator Release ID for a given automation name.

    TODO: confirm exact Orchestrator API endpoint and payload shape with Swetha —
    see open question #1 in the spec. The endpoint below follows standard UiPath
    Orchestrator OData conventions and is a best-guess scaffold only.

    Args:
        automation_name: The name of the automation (e.g. "Customer Complaint Classifier").
        token: UiPath bearer token from get_token().

    Returns:
        int: The Release ID, or None if not found.
    """
    # TODO: confirm exact endpoint (may need X-UIPATH-OrganizationUnitId header)
    # TODO: confirm whether staging.uipath.com or cloud.uipath.com is the correct base
    url = f"{_ORCHESTRATOR_BASE}/odata/Releases"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # TODO: Uncomment and fill in if Swetha confirms this header is required:
        # "X-UIPATH-OrganizationUnitId": "<folder_id>",
    }
    params = {"$filter": f"Name eq '{automation_name}'"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error querying Orchestrator Releases: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Releases lookup failed.\n"
            f"Status: {response.status_code}\n"
            f"Body: {response.text}\n\n"
            "If you get 401, your token may not have Orchestrator read permission.\n"
            "If you get 404, the base URL may be wrong — confirm with Swetha."
        )

    data = response.json()
    releases = data.get("value", [])

    if not releases:
        print(
            f"[WARNING]  No Release named '{automation_name}' found in Orchestrator.\n"
            "   This means either:\n"
            "   a) Swetha has not created a dummy process with this name yet (open question #2)\n"
            "   b) The automation_name in the scenario payload doesn't exactly match the Release name"
        )
        return None

    release_id = releases[0].get("Id")
    print(f"   Found Release ID: {release_id} for '{automation_name}'")
    return release_id


def _disable_release(release_id: int, token: str) -> bool:
    """
    Call Orchestrator's SetEnabled action to disable a Release.

    TODO: confirm exact endpoint and request body shape with Swetha —
    see open question #1 in the spec. The endpoint below follows standard UiPath
    Orchestrator OData conventions and is a best-guess scaffold only.

    Args:
        release_id: The Orchestrator Release ID from _get_release_id().
        token: UiPath bearer token.

    Returns:
        bool: True on success.
    """
    # TODO: confirm exact SetEnabled endpoint pattern with Swetha
    url = (
        f"{_ORCHESTRATOR_BASE}/odata/Releases({release_id})"
        f"/UiPath.Server.Configuration.OData.SetEnabled"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # TODO: Uncomment if needed:
        # "X-UIPATH-OrganizationUnitId": "<folder_id>",
    }
    body = {"enabled": False}

    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error calling SetEnabled: {exc}") from exc

    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"SetEnabled call failed.\n"
            f"Status: {response.status_code}\n"
            f"Body: {response.text}"
        )

    return True


def freeze_automation(automation_name: str) -> bool:
    """
    Main freeze function: finds the named automation in Orchestrator and disables it.

    Args:
        automation_name: The name of the automation to freeze.

    Returns:
        bool: True if successfully frozen, False if the Release was not found.

    Raises:
        RuntimeError: On any API failure (never swallows errors silently).
    """
    print(f"\n[KEY] Fetching UiPath access token...")
    token = get_token()
    print(f"   Token acquired.\n")

    print(f"[SEARCH] Looking up Release '{automation_name}' in Orchestrator...")
    release_id = _get_release_id(automation_name, token)

    if release_id is None:
        return False

    print(f"[STOP] Disabling Release ID {release_id}...")
    _disable_release(release_id, token)

    print(
        f"\n[OK] Automation '{automation_name}' has been DISABLED in Orchestrator. "
        f"Status: FROZEN."
    )
    return True


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Freeze (disable) a named automation in UiPath Orchestrator. "
            "Run this immediately after a compliance officer clicks Reject in Action Center."
        )
    )
    parser.add_argument(
        "--automation",
        required=True,
        help=(
            "Name of the automation to freeze. "
            'Must match the Orchestrator Release name exactly, e.g. '
            '"Customer Complaint Classifier"'
        ),
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  AI Incident Case Manager — Automation Freeze")
    print(f"  Target: {args.automation}")
    print(f"{'='*60}")

    try:
        success = freeze_automation(args.automation)
        if not success:
            print(
                "\n[FAIL] Freeze could not complete — automation not found in Orchestrator.\n"
                "   See open questions #1 and #2 in the spec (automation-freeze/freeze.py)."
            )
            sys.exit(1)
    except RuntimeError as exc:
        print(f"\n[FAIL] Freeze failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
