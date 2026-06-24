# server.py  (repo root)
#
# Combined FastAPI server — exposes ALL endpoints on a single port so that
# only one ngrok tunnel is needed. This is the RECOMMENDED way to run the
# intelligence layer in production / demo mode.
#
# Endpoints:
#   GET  /health            — liveness check
#   POST /investigate       — AI incident investigation (UiPath Investigation Agent calls this)
#   POST /generate-report   — Article 73 report generation (UiPath calls this on Escalate path)
#
# Run with (from the repo root):
#   ..\uipath\Scripts\uvicorn.exe server:app --host 0.0.0.0 --port 8000
#   -- or, if venv is activated --
#   uvicorn server:app --host 0.0.0.0 --port 8000
#
# Then expose publicly with ngrok:
#   ngrok http 8000
# Give the resulting https://<hash>.ngrok-free.app URL to Swetha.

import os
import sys

# Ensure investigation-agent/ and report-generator/ are importable regardless of CWD
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "investigation-agent"))
sys.path.insert(0, os.path.join(_ROOT, "report-generator"))

from fastapi import FastAPI, HTTPException

# Import just the core functions (not sub-apps) from each module
from agent import investigate_incident          # noqa: E402
from generator import generate_article73_report  # noqa: E402

app = FastAPI(
    title="AI Incident Case Manager — Intelligence Layer",
    description=(
        "Combined API server for B's intelligence layer. "
        "Exposes Claude investigation agent and Article 73 report generator "
        "on a single port for simple ngrok tunnelling."
    ),
    version="1.0.0",
)


@app.get("/health")
async def health():
    """Health check — verify the server is reachable."""
    return {"status": "ok"}


@app.post("/investigate")
async def investigate(payload: dict):
    """
    Investigate an AI incident. Called by UiPath's Investigation Agent.
    Returns a structured investigation report matching the schema in agent.py.
    """
    try:
        result = investigate_incident(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-report")
async def generate_report(payload: dict):
    """
    Generate an Article 73 report. Called on the Reject/Escalate path.

    Expected JSON body:
    {
        "investigation_output": { ...full investigation JSON from /investigate... },
        "officer_notes": "Compliance officer's plain-text rationale."
    }
    """
    investigation_output = payload.get("investigation_output")
    officer_notes = payload.get("officer_notes", "")

    if investigation_output is None:
        raise HTTPException(
            status_code=422,
            detail="'investigation_output' key is required in the request body.",
        )

    try:
        result = generate_article73_report(investigation_output, officer_notes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
