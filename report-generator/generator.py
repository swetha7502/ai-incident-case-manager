# report-generator/generator.py
#
# PURPOSE: Generate a formal EU AI Act Article 73 serious incident report via LLM.
# Only triggered when the compliance officer clicks Reject in Action Center.
# Takes the investigation output (from agent.py) plus the officer's notes.
#
# LLM calls go through shared/llm_client.py (3-provider fallback chain).
#
# Standalone test:
#   python generator.py
#
# As part of the combined server (recommended):
#   uvicorn server:app --host 0.0.0.0 --port 8000  (from repo root)

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# ---------------------------------------------------------------------------
# Load .env from the repo root (one level up from report-generator/)
# ---------------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)

# ---------------------------------------------------------------------------
# Add shared/ to path so we can import call_llm
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from llm_client import call_llm  # noqa: E402

# ---------------------------------------------------------------------------
# Load the Article 73 system prompt, path relative to THIS file's location
# ---------------------------------------------------------------------------
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_SYSTEM_PROMPT_PATH = os.path.join(_PROMPTS_DIR, "article73_system.txt")

with open(_SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read().strip()


# ---------------------------------------------------------------------------
# Core report generation function
# ---------------------------------------------------------------------------

def generate_article73_report(investigation_output: dict, officer_notes: str) -> dict:
    """
    Generate a formal EU AI Act Article 73 draft report using an LLM.

    Args:
        investigation_output: The structured investigation JSON from agent.py.
        officer_notes: The compliance officer's plain-text rationale for escalation.

    Returns:
        dict: Parsed Article 73 report matching the specified JSON schema.

    Raises:
        ValueError: If the LLM response is not valid JSON.
        RuntimeError: If all LLM providers fail (from llm_client.py).
    """
    user_message = (
        "Generate a formal EU AI Act Article 73 serious incident report "
        "based on the following:\n\n"
        f"Investigation findings:\n{json.dumps(investigation_output, indent=2)}\n\n"
        f"Compliance officer notes:\n{officer_notes}"
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
            "Check the Article 73 system prompt or retry."
        ) from exc

    return result


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Article 73 Report Generator",
    description=(
        "Generates formal EU AI Act Article 73 serious incident reports via LLM. "
        "Triggered on the Reject/Escalate path in the UiPath Maestro Case workflow."
    ),
    version="1.0.0",
)


@app.post("/generate-report")
async def generate_report(payload: dict):
    """
    Generate an Article 73 report.

    Expected JSON body:
    {
        "investigation_output": { ...full investigation JSON from /investigate... },
        "officer_notes": "Plain text rationale from the compliance officer."
    }
    """
    investigation_output = payload.get("investigation_output")
    officer_notes = payload.get("officer_notes", "")

    if investigation_output is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "'investigation_output' key is required in the request body. "
                "It should be the full investigation JSON from the /investigate endpoint."
            ),
        )

    try:
        result = generate_article73_report(investigation_output, officer_notes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

_SAMPLE_INVESTIGATION = {
    "incident_id": "INC-AUTO-2024-LLM-003-1719237120",
    "investigation_timestamp": "2026-06-24T14:32:00Z",
    "severity_assessment": "HIGH",
    "incident_summary": (
        "The Customer Complaint Classifier automation produced output containing "
        "a demographic-based routing recommendation, constituting a bias-detected "
        "policy violation. One data subject is directly affected."
    ),
    "root_cause_hypothesis": (
        "The underlying LLM was not sufficiently constrained to prevent demographic "
        "inference from complaint text, resulting in a biased priority recommendation."
    ),
    "affected_components": [
        "Customer Complaint Classifier",
        "CRM routing queue",
        "LLM inference layer",
    ],
    "data_subjects_at_risk": 1,
    "eu_ai_act_relevance": {
        "article_73_triggered": True,
        "risk_category": "HIGH_RISK",
        "reporting_deadline_days": 15,
        "rationale": (
            "Severity is HIGH, flag_type is bias_detected, data_subjects_affected > 0. "
            "All three Article 73 trigger conditions are met."
        ),
    },
    "recommended_actions": [
        {
            "action": "Immediately disable the Customer Complaint Classifier automation",
            "priority": "IMMEDIATE",
        },
        {
            "action": "Conduct a full bias audit of the LLM prompt and training data",
            "priority": "SHORT_TERM",
        },
        {
            "action": "Implement demographic-blind processing guardrails",
            "priority": "LONG_TERM",
        },
    ],
    "automation_freeze_recommended": True,
    "compliance_officer_notes": (
        "This incident meets the threshold for Article 73 reporting. "
        "Recommend immediate escalation and automation freeze."
    ),
}

_SAMPLE_OFFICER_NOTES = "Confirmed bias pattern, escalating per policy."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Standalone test: generate an Article 73 report from a sample investigation."
    )
    parser.add_argument(
        "--notes",
        default=_SAMPLE_OFFICER_NOTES,
        help="Compliance officer notes (default: sample bias escalation note).",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Article 73 Report Generator -- Standalone Test")
    print(f"  Calling LLM via fallback chain...")
    print(f"{'='*60}\n")

    try:
        result = generate_article73_report(_SAMPLE_INVESTIGATION, args.notes)
        print("[OK] Article 73 report generated. Output:\n")
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"\n[FAIL] Report generation failed: {exc}")
        sys.exit(1)
