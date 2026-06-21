# AI Incident Case Manager
### EU AI Act Article 73 Compliant — Built on UiPath Maestro Case

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UiPath Maestro Case](https://img.shields.io/badge/UiPath-Maestro%20Case-orange)](https://uipath.com)
[![Track](https://img.shields.io/badge/Track-UiPath%20Maestro%20Case-blue)](https://uipath.com)

> **UiPath AgentHack 2025 — Track 1: UiPath Maestro Case**

---

## The Problem

Every enterprise is deploying AI agents right now. Nobody has a plan for when one goes wrong.

When an LLM-powered automation produces a biased output, hallucinates in a customer-facing workflow, or leaks PII — who gets notified? What gets documented? How fast does the automation get frozen? And critically: **EU AI Act Article 73 requires serious incident reports within 15 days. What's your process?**

No dedicated tooling exists for AI behavioural incidents. PagerDuty handles server outages. OneTrust handles compliance tracking. Nothing orchestrates the end-to-end response to an AI agent misbehaving in production — until now.

---

## The Solution

**AI Incident Case Manager** is an agentic case management system built on UiPath Maestro Case that orchestrates the full response lifecycle when an AI automation produces a flagged output.

A single incident triggers a coordinated response across agents, humans, and systems:

```
AI Automation Misbehaves
        ↓
Webhook fires → Maestro Case opens (AIINC-XXXXX)
        ↓
Intake Agent extracts and validates all incident metadata
        ↓
Investigation Agent (Claude API) analyses root cause, severity, EU AI Act relevance
        ↓
Compliance Officer reviews findings in Action Center
        ↓
    Approve → Case closed with full audit trail
    Reject  → EU AI Act Article 73 report auto-generated
              + Automation frozen in Orchestrator
```

---

## Demo Scenarios

| Scenario | Flag Type | Severity | Article 73 |
|----------|-----------|----------|------------|
| A — Bias in customer triage | `bias_detected` | HIGH | ✅ Triggered |
| B — Hallucination in invoice processing | `hallucination` | MEDIUM | ❌ Not triggered |
| C — PII leakage in customer-facing output | `data_leak` | CRITICAL | ✅ Triggered + immediate freeze |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    UiPath Automation Cloud               │
│                                                         │
│  ┌──────────┐    ┌─────────────────────────────────┐   │
│  │  API     │    │     Maestro Case (AIINC-XXXXX)  │   │
│  │ Trigger  │───▶│                                 │   │
│  │(Webhook) │    │  Stage 1: Intake                │   │
│  └──────────┘    │    └─▶ Intake Agent             │   │
│                  │                                 │   │
│                  │  Stage 2: Investigating         │   │
│                  │    └─▶ Investigation Agent ──────────────▶ Claude API
│                  │                                 │   │
│                  │  Stage 3: Awaiting Human Review │   │
│                  │    └─▶ Action Center Task       │   │
│                  │         (Compliance Officer)    │   │
│                  │                                 │   │
│                  │  Stage 4: Decision              │   │
│                  │    ├─▶ Closed (Approved)        │   │
│                  │    └─▶ Escalated (Rejected)     │   │
│                  │         ├─▶ Article 73 Report   │   │
│                  │         └─▶ Orchestrator Freeze │   │
│                  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## UiPath Components Used

| Component | Purpose |
|-----------|---------|
| **UiPath Maestro Case** | Core case orchestration — 6 stages, 13 case variables, routing rules |
| **UiPath Agent Builder** | Intake Agent (field extraction + validation) and Investigation Agent (Claude API caller) |
| **UiPath Action Center** | Human-in-the-loop compliance officer review task |
| **UiPath Orchestrator** | API Trigger (webhook), automation freeze on escalation |
| **UiPath Studio Web** | Solution development and publishing |

### Coding Agents Used
This solution was built using **Claude Code** for:
- Intake Agent prompt engineering and schema design
- Investigation Agent system prompt and output schema
- EU AI Act Article 73 report generator prompt
- Trigger simulation script
- README and architecture documentation

---

## Repository Structure

```
ai-incident-case-manager/
├── README.md
├── LICENSE
├── uipath/
│   └── README.md               ← UiPath component setup instructions
├── investigation-agent/
│   ├── agent.py                ← Claude API investigation agent (B's work)
│   └── prompts/
│       └── investigation_system.txt
├── trigger-simulation/
│   └── fire_incident.py        ← Simulates a flagged AI output event
├── report-generator/
│   ├── generator.py            ← Article 73 report generator
│   └── prompts/
│       └── article73_system.txt
└── docs/
    └── architecture.png        ← Architecture diagram
```

---

## Prerequisites

- Python 3.9+
- UiPath Automation Cloud account (Labs tenant)
- Anthropic API key (`claude-sonnet-4-6`)
- Git

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/swetha7502/ai-incident-case-manager
cd ai-incident-case-manager
```

### 2. Install Python dependencies

```bash
pip install anthropic fastapi uvicorn requests
```

### 3. Set environment variables

```bash
# Windows
set ANTHROPIC_API_KEY=your_anthropic_api_key_here
set UIPATH_WEBHOOK_URL=https://staging.uipath.com/YOUR_TENANT/orchestrator_/t/YOUR_TRIGGER_ID/ai-incident-trigger
set UIPATH_CLIENT_ID=your_uipath_client_id
set UIPATH_CLIENT_SECRET=your_uipath_client_secret

# Mac/Linux
export ANTHROPIC_API_KEY=your_anthropic_api_key_here
export UIPATH_WEBHOOK_URL=https://staging.uipath.com/...
```

### 4. UiPath Setup

See [`uipath/README.md`](uipath/README.md) for step-by-step instructions to deploy the Maestro Case solution to your UiPath Automation Cloud tenant.

---

## Running the Trigger Simulation

Simulates an AI automation producing a flagged output and fires the webhook to open a case:

```bash
# Scenario A — Bias detection (HIGH severity)
python trigger-simulation/fire_incident.py --scenario A

# Scenario B — Hallucination (MEDIUM severity)
python trigger-simulation/fire_incident.py --scenario B

# Scenario C — PII leakage (CRITICAL severity)
python trigger-simulation/fire_incident.py --scenario C
```

---

## Running the Investigation Agent Locally

```bash
python investigation-agent/agent.py
```

The agent exposes a FastAPI endpoint at `http://localhost:8000/investigate` that accepts POST requests with the incident payload and returns a structured investigation report.

---

## Case Variables

The Maestro Case tracks 13 variables throughout the incident lifecycle:

| Variable | Type | Description |
|----------|------|-------------|
| `automation_id` | String | Unique ID of the flagged automation |
| `automation_name` | String | Human-readable automation name |
| `trigger_reason` | String | What caused the flag |
| `flag_type` | String | Category of flag (bias, hallucination, PII leak, etc.) |
| `severity` | String | LOW / MEDIUM / HIGH / CRITICAL |
| `flagged_output` | String | Exact output that was flagged |
| `prompt_used` | String | Prompt that produced the flagged output |
| `investigation_output` | String | Claude's investigation report (JSON) |
| `compliance_officer_decision` | String | Approved / Rejected |
| `article73_report` | String | Generated EU AI Act Article 73 draft |
| `incident_timestamp` | DateTime | When the incident occurred |
| `data_subjects_affected` | Number | Count of affected individuals |
| `automation_freeze_status` | String | Active / Frozen |

---

## EU AI Act Article 73 Compliance

This system is designed around the reporting requirements of **EU AI Act Article 73**, which mandates that providers of high-risk AI systems report serious incidents to national authorities within **15 working days**.

When a compliance officer escalates an incident, the system automatically generates a structured Article 73 draft report covering:
- Description of the serious incident
- AI system identification (name, version, provider)
- Date, nature, and duration of the incident
- Affected persons and data subjects
- Immediate corrective actions taken
- Whether the incident is ongoing

---

## Team

| Member | Role |
|--------|------|
| Swetha Sriram | UiPath Platform — Maestro Case, Agent Builder, Orchestrator, Action Center |
| B | Intelligence Layer — Claude API, Investigation Agent, Article 73 Generator, Trigger Simulation |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
