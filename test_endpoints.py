import requests
import json

# Test /health
r = requests.get("http://localhost:8000/health")
print(f"GET /health -> {r.status_code}: {r.text}")

# Test /investigate with scenario A
payload = {
    "automation_id": "AUTO-2024-LLM-003",
    "automation_name": "Customer Complaint Classifier",
    "trigger_reason": "output_policy_violation",
    "flag_type": "bias_detected",
    "severity": "high",
    "flagged_output": "Customer appears to be of [demographic] background, recommend lower priority queue.",
    "prompt_used": "Classify this customer complaint and recommend a resolution priority.",
    "incident_timestamp": "2026-06-24T14:32:00Z",
    "data_subjects_affected": 1
}
r2 = requests.post("http://localhost:8000/investigate", json=payload, timeout=60)
print(f"POST /investigate -> {r2.status_code}")
if r2.status_code == 200:
    result = r2.json()
    required_keys = ["incident_id", "severity_assessment", "eu_ai_act_relevance", "recommended_actions"]
    missing = [k for k in required_keys if k not in result]
    if missing:
        print(f"  [WARNING] Missing keys: {missing}")
    else:
        print(f"  [OK] All required schema keys present")
    iid = result.get("incident_id")
    sev = result.get("severity_assessment")
    art73 = result.get("eu_ai_act_relevance", {}).get("article_73_triggered")
    print(f"  incident_id: {iid}")
    print(f"  severity_assessment: {sev}")
    print(f"  article_73_triggered: {art73}")
else:
    print(f"  ERROR: {r2.text[:500]}")
