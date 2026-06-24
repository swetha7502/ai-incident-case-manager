# trigger-simulation/fire_incident.py
#
# PURPOSE: Simulates "an AI automation just produced a flagged output."
# This is a STAND-IN for a real bias/PII/hallucination detector — no such
# detector was built in this project. This script fires a UiPath webhook to
# open a new Maestro Case (e.g. AIINC-12345) with the incident metadata.
#
# Usage:
#   python fire_incident.py --scenario A   # Bias detection (default, primary demo)
#   python fire_incident.py --scenario B   # Hallucination
#   python fire_incident.py --scenario C   # PII leak (critical)
#
# NOTE on webhook URL: If this script fails with a 404 or connection error,
# check whether the GUID segment "8369" in UIPATH_WEBHOOK_URL needs to be
# "8367" — see Section 3 of the build spec. Change it in .env, not here.

import argparse
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load .env from the repo root (one level up from trigger-simulation/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)

# ---------------------------------------------------------------------------
# Add shared/ to the path so we can import get_token from uipath_auth.py
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from uipath_auth import get_token  # noqa: E402  (import after sys.path patch)

# ---------------------------------------------------------------------------
# Incident scenario payloads — field names match Swetha's case variables exactly
# ---------------------------------------------------------------------------

SCENARIOS = {
    "A": {
        "automation_id": "AUTO-2024-LLM-003",
        "automation_name": "Customer Complaint Classifier",
        "trigger_reason": "output_policy_violation",
        "flag_type": "bias_detected",
        "severity": "high",
        "flagged_output": (
            "Customer appears to be of [demographic] background, "
            "recommend lower priority queue."
        ),
        "prompt_used": (
            "Classify this customer complaint and recommend a resolution priority."
        ),
        "incident_timestamp": "2026-06-24T14:32:00Z",
        "data_subjects_affected": 1,
    },
    "B": {
        "automation_id": "AUTO-2024-LLM-007",
        "automation_name": "Invoice Line Item Summariser",
        "trigger_reason": "output_accuracy_failure",
        "flag_type": "hallucination",
        "severity": "medium",
        "flagged_output": (
            "Invoice total: $47,832.00 for items: "
            "[fabricated line items not present in source document]"
        ),
        "prompt_used": (
            "Summarise the line items from this invoice and calculate the total."
        ),
        "incident_timestamp": "2026-06-24T09:15:00Z",
        "data_subjects_affected": 0,
    },
    "C": {
        "automation_id": "AUTO-2024-LLM-011",
        "automation_name": "Customer Service Response Bot",
        "trigger_reason": "pii_exposure",
        "flag_type": "data_leak",
        "severity": "critical",
        "flagged_output": (
            "Dear John Smith, your account 4532-XXXX-XXXX-8821 and "
            "SSN 123-45-6789 have been noted."
        ),
        "prompt_used": (
            "Generate a personalised response to this customer service query."
        ),
        "incident_timestamp": "2026-06-24T11:45:00Z",
        "data_subjects_affected": 847,
    },
}


def fire(payload: dict) -> None:
    """
    Get a fresh UiPath bearer token, then POST the incident payload to the
    webhook URL. Prints the HTTP status and response body.
    Raises clearly on any failure — never swallows errors silently.
    """
    webhook_url = os.getenv("UIPATH_WEBHOOK_URL")
    if not webhook_url or webhook_url.startswith("# B:"):
        raise ValueError(
            "UIPATH_WEBHOOK_URL is not set in .env. "
            "Add it before running this script."
        )

    print("[KEY] Fetching UiPath access token...")
    token = get_token()
    print("   Token acquired.\n")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"[FIRE] Firing incident to: {webhook_url}")
    print(f"   Payload:\n{json.dumps(payload, indent=2)}\n")

    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    except requests.exceptions.RequestException as exc:
        print(f"\n[FAIL] Network error — could not reach webhook: {exc}")
        print(
            "\n💡 If this is a connection error, verify the webhook URL in .env.\n"
            "   Try swapping '8369' → '8367' in the GUID segment if you get a 404."
        )
        sys.exit(1)

    print(f"[RESPONSE] Response Status: {response.status_code}")
    print(f"   Response Body:   {response.text}")

    if 200 <= response.status_code < 300:
        print(
            f"\n[OK] Incident fired successfully. "
            f"A new Maestro Case should appear in Swetha's dashboard."
        )
    else:
        print(
            f"\n[FAIL] Webhook returned non-2xx status ({response.status_code}). "
            f"Check the response body above for details."
        )
        if response.status_code == 404:
            print(
                "💡 Got 404 — the webhook URL may be wrong. "
                "Try swapping '8369' → '8367' in the GUID segment in .env."
            )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fire a simulated AI incident to the UiPath Maestro Case webhook."
    )
    parser.add_argument(
        "--scenario",
        choices=["A", "B", "C"],
        default="A",
        help=(
            "Which incident scenario to fire. "
            "A = Bias detection (default/primary demo), "
            "B = Hallucination, "
            "C = PII leak (critical)"
        ),
    )
    args = parser.parse_args()

    payload = SCENARIOS[args.scenario]
    print(f"\n{'='*60}")
    print(f"  AI Incident Case Manager — Trigger Simulation")
    print(f"  Scenario {args.scenario}: {payload['automation_name']}")
    print(f"  Flag type: {payload['flag_type']} | Severity: {payload['severity']}")
    print(f"{'='*60}\n")

    fire(payload)


if __name__ == "__main__":
    main()
