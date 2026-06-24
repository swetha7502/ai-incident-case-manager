# AI Incident Case Manager
### EU AI Act Article 73 Compliant — Built on UiPath Maestro Case

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UiPath Maestro Case](https://img.shields.io/badge/UiPath-Maestro%20Case-orange)](https://uipath.com)
[![Track](https://img.shields.io/badge/Track-UiPath%20Maestro%20Case-blue)](https://uipath.com)

> **UiPath AgentHack 2025 — Track 1: UiPath Maestro Case**

---

## 📖 The Problem

Every enterprise is deploying AI agents right now. Nobody has a plan for when one goes wrong.

When an LLM-powered automation produces a biased output, hallucinates in a customer-facing workflow, or leaks PII — who gets notified? What gets documented? How fast does the automation get frozen? And critically: **EU AI Act Article 73 requires serious incident reports within 15 days. What's your process?**

No dedicated tooling exists for AI behavioural incidents. PagerDuty handles server outages. OneTrust handles compliance tracking. Nothing orchestrates the end-to-end response to an AI agent misbehaving in production — until now.

---

## 🚀 The Solution

**AI Incident Case Manager** is an agentic case management system built on UiPath Maestro Case that orchestrates the full response lifecycle when an AI automation produces a flagged output.

A single incident triggers a coordinated response across agents, humans, and systems:

```
AI Automation Misbehaves
        ↓
Webhook fires → Maestro Case opens (AIINC-XXXXX)
        ↓
Intake Agent extracts and validates all incident metadata
        ↓
Investigation Agent (LLM Fallback Chain) analyses root cause, severity, EU AI Act relevance
        ↓
Compliance Officer reviews findings in Action Center
        ↓
    Approve → Case closed with full audit trail
    Reject  → EU AI Act Article 73 report auto-generated
              + Automation frozen in Orchestrator
```

---

## 🏗️ What Was Built (Technical Specifications)

The Intelligence Layer (Python/FastAPI) has been fully completed. Here is exactly what was built and how it functions:

### 1. Robust LLM Fallback Chain
Instead of relying on a single point of failure (e.g., Anthropic Claude), the entire Intelligence Layer utilizes a resilient **3-provider fallback chain**:
- **Primary:** GitHub Models (`openai/gpt-4.1`)
- **Secondary:** Google Gemini (`gemini-2.5-flash`)
- **Tertiary:** Groq (`llama-3.3-70b-versatile`)

*How it works:* The `shared/llm_client.py` module encapsulates this logic. It attempts to generate a response from the primary provider. If rate-limited or out of credits, it instantly falls back down the chain, guaranteeing an uninterrupted response for incident triage.

### 2. The Investigation Agent (`investigation-agent/agent.py`)
This is the core analysis engine. It takes an incoming incident payload (e.g., a flagged AI output) and uses the LLM fallback chain to generate a strictly formatted JSON report. 
- It assesses the **Severity** of the incident.
- It determines if **EU AI Act Article 73** is triggered (mandating reporting if the incident is severe, involves bias/data leaks, and affects data subjects).
- It proposes concrete root cause hypotheses and actionable remediation steps.

### 3. The Article 73 Report Generator (`report-generator/generator.py`)
When a Compliance Officer confirms a severe incident, this module generates a formal regulatory draft. 
- It outputs strict JSON conforming to 7 specific regulatory sections required by national competent authorities.

### 4. Unified FastAPI Server (`server.py`)
To expose the Python intelligence layer to UiPath Maestro, we built a single unified FastAPI application. 
- It exposes a `/health` endpoint for monitoring.
- It exposes an `/investigate` endpoint which accepts the incident payload and synchronously returns the Investigation Agent's JSON analysis.

### 5. Trigger Simulation (`trigger-simulation/fire_incident.py`)
A testing harness that acts like a misbehaving AI in the wild. It authenticates with the UiPath Cloud via OAuth2 (Client Credentials) and fires a payload to the UiPath Webhook, triggering the Maestro Case workflow.

### 6. Automation Freeze Scaffold (`automation-freeze/freeze.py`)
A CLI scaffold designed to automatically disable the affected process in UiPath Orchestrator to prevent further harm while the incident is investigated.

---

## 🧪 Test Results Summary

During development, rigorous testing was performed across the intelligence layer. Here is a summary of the outcomes:

| Test Component | Target Script | Outcome | Details & Reasoning |
|----------------|---------------|---------|---------------------|
| **Investigation Agent (Standalone)** | `investigation-agent/agent.py --scenario A, B, C` | ✅ **PASSED** | Validated the LLM fallback chain and strict JSON schema adherence. The GitHub Models fallback succeeded, accurately parsing bias (A), hallucination (B), and data leaks (C). |
| **Report Generator (Standalone)** | `report-generator/generator.py` | ✅ **PASSED** | Successfully generated the 7-section Article 73 compliance report using the exact requested JSON schema. |
| **HTTP Endpoints (Integration)** | `server.py` + `test_endpoints.py` | ✅ **PASSED** | The FastAPI server booted cleanly on port 8000. `test_endpoints.py` successfully hit `/health` (200 OK) and `/investigate` (200 OK), confirming the server logic routes properly. |
| **Live Webhook Fire** | `trigger-simulation/fire_incident.py` | ❌ **FAILED** | Failed at the **Authentication Phase** with a `400 invalid_client` error from UiPath. **Why:** The `UIPATH_CLIENT_ID` or `UIPATH_CLIENT_SECRET` provided in the `.env` file are incorrect, or the External App in UiPath was not properly configured as a confidential app. The script never reached the webhook step. |

---

## 🚀 Setup & Execution Instructions

### Prerequisites
- Python 3.9+
- A configured `.env` file at the root containing:
  - `GITHUB_MODELS_TOKEN`
  - `GOOGLE_API_KEY`
  - `GROQ_API_KEY`
  - `UIPATH_CLIENT_ID`
  - `UIPATH_CLIENT_SECRET`
  - `UIPATH_WEBHOOK_URL`

### Step 1: Start the Intelligence Server
The unified FastAPI server needs to be running to accept requests from UiPath (and for local testing).

```bash
# Start the Uvicorn server on port 8000
uvicorn server:app --host 0.0.0.0 --port 8000
```
*Reasoning:* UiPath Maestro needs a live HTTP endpoint to POST to. Running this command hosts the `/investigate` endpoint locally. To connect it to the cloud, use a tool like `ngrok` (e.g., `ngrok http 8000`).

### Step 2: Run the Endpoint Integration Tests (Optional)
In a separate terminal, while the server is running, you can test if the endpoints are responding correctly.

```bash
python test_endpoints.py
```
*Reasoning:* This mimics the exact HTTP POST request that UiPath will send, ensuring the data schema and network routing are functioning before touching the cloud.

### Step 3: Run Standalone Agent Tests
If you want to test the LLM logic without the server overhead, you can run the agents directly via CLI.

```bash
# Test the Investigation Agent against various scenarios
python investigation-agent/agent.py --scenario A

# Test the formal Report Generator
python report-generator/generator.py
```
*Reasoning:* This is useful for rapid prompt engineering or debugging the LLM fallback chain without worrying about HTTP layers.

### Step 4: Fire a Live Incident into UiPath
Once your server is publicly exposed and UiPath is configured, use the trigger simulation to test the end-to-end flow.

```bash
cd trigger-simulation
python fire_incident.py --scenario A
```
*Reasoning:* This authenticates with UiPath and hits the webhook, placing an actual incident case into the Maestro dashboard for the compliance officer to review. *(Note: Ensure your `UIPATH_CLIENT_ID` and `SECRET` are valid to avoid the `invalid_client` error).*

---

## 🤝 Team

| Member | Role |
|--------|------|
| **Swetha Sriram** | UiPath Platform — Maestro Case, Agent Builder, Orchestrator, Action Center |
| **B** | Intelligence Layer — LLM Fallback Chain, FastAPI Server, Article 73 Generator, Trigger Simulation |

## License
MIT License — see [LICENSE](LICENSE) for details.
