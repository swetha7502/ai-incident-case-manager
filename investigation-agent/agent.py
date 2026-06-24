# investigation-agent/agent.py
#
# This file serves DUAL purposes:
#   1. Importable module: exports investigate_incident(payload) for use by server.py
#      and for standalone testing via `python agent.py [--scenario A|B|C]`
#   2. FastAPI application: the `app` object is here so UiPath's Investigation Agent
#      can call this server via POST /investigate.
#
# LLM calls go through shared/llm_client.py which implements a 3-provider fallback chain:
#   GitHub Models (gpt-4.1) -> Google Gemini (gemini-2.5-flash) -> Groq (llama-3.3-70b)
#
# Run the server:
#   uvicorn agent:app --host 0.0.0.0 --port 8000
#
# Standalone test (no server):
#   python agent.py --scenario A

import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# ---------------------------------------------------------------------------
# Load .env from the repo root (one level up from investigation-agent/)
# ---------------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)

# ---------------------------------------------------------------------------
# Add shared/ to path so we can import call_llm
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from llm_client import call_llm  # noqa: E402

# ---------------------------------------------------------------------------
# Load the system prompt from the prompts/ subdirectory, relative to THIS file
# (so it works regardless of what directory the process is launched from)
# ---------------------------------------------------------------------------
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_SYSTEM_PROMPT_PATH = os.path.join(_PROMPTS_DIR, "investigation_system.txt")

with open(_SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read().strip()


# ---------------------------------------------------------------------------
# Core investigation function
# ---------------------------------------------------------------------------

def investigate_incident(payload: dict) -> dict:
    """
    Send an incident payload to the LLM for analysis and return a structured
    investigation report as a Python dict.

    Args:
        payload: Incident metadata dict (matches Swetha's 9 trigger-time case variables).

    Returns:
        dict: Parsed investigation report matching the specified JSON schema.

    Raises:
        ValueError: If the LLM response is not valid JSON.
        RuntimeError: If all LLM providers fail (from llm_client.py).
    """
    automation_id = payload.get("automation_id", "UNKNOWN")
    unix_epoch = int(time.time())

    user_message = (
        f"Investigate this AI incident:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        f"Use incident_id format: INC-{automation_id}-{unix_epoch}"
    )

    raw_text = call_llm(_SYSTEM_PROMPT, user_message)
    raw_text = raw_text.strip()

    # Defensive: strip markdown fences if the LLM adds them despite instructions
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1]).strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON output. JSON parse error: {exc}\n"
            f"Raw response:\n{raw_text}\n\n"
            "This usually means the LLM added preamble text. "
            "Check the system prompt or retry."
        ) from exc

    return result


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Incident Investigation Agent",
    description=(
        "FastAPI wrapper around the investigation agent. "
        "Called by UiPath's Investigation Agent (Agent Builder) to analyse "
        "flagged AI incidents and return a structured EU AI Act compliance report."
    ),
    version="1.0.0",
)


@app.post("/investigate")
async def investigate(payload: dict):
    """
    Accepts an incident payload (JSON body) and returns a structured investigation
    report. Called by UiPath's Investigation Agent.

    Expected payload fields (match Swetha's case variables):
        automation_id, automation_name, trigger_reason, flag_type, severity,
        flagged_output, prompt_used, incident_timestamp, data_subjects_affected
    """
    try:
        result = investigate_incident(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint. Returns {"status": "ok"} when the server is running."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Standalone test scenarios (mirrors fire_incident.py for consistency)
# ---------------------------------------------------------------------------

_TEST_SCENARIOS = {
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Standalone test: investigate one of the 3 demo scenarios."
    )
    parser.add_argument(
        "--scenario",
        choices=["A", "B", "C"],
        default="A",
        help="Which scenario to test (default: A -- bias detection).",
    )
    args = parser.parse_args()

    payload = _TEST_SCENARIOS[args.scenario]

    print(f"\n{'='*60}")
    print(f"  Investigation Agent -- Standalone Test")
    print(f"  Scenario {args.scenario}: {payload['automation_name']}")
    print(f"  Calling LLM via fallback chain...")
    print(f"{'='*60}\n")

    try:
        result = investigate_incident(payload)
        print("[OK] Investigation complete. Output:\n")
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"\n[FAIL] Investigation failed: {exc}")
        sys.exit(1)
