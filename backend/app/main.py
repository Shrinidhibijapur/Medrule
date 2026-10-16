import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models.policy import Policy
from app.models.evaluation import EvaluationReport
from app.engine.rules_engine import DeterministicRulesEngine

app = FastAPI(
    title="MedRule Decision-Support API",
    version="1.0.0",
    description="Rulebook-Driven Medical Insurance Authorization Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

class EvaluateRequest(BaseModel):
    case_id: str
    patient_name: str
    policy_id: str
    facts: Dict[str, Any]

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MedRule Policy & Evaluation Engine",
        "version": "1.0.0",
        "phase": "Phase 0 Verified"
    }

@app.get("/api/policies")
def list_policies():
    policies_dir = DATA_DIR / "policies"
    policies = []
    if policies_dir.exists():
        for file in policies_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                policies.append(json.load(f))
    return policies

@app.get("/api/policies/{policy_id}")
def get_policy(policy_id: str):
    policies = list_policies()
    for p in policies:
        if p["id"] == policy_id:
            return p
    raise HTTPException(status_code=404, detail="Policy not found")

@app.post("/api/evaluate", response_model=EvaluationReport)
def evaluate_request(req: EvaluateRequest):
    policy_data = get_policy(req.policy_id)
    policy = Policy(**policy_data)
    report = DeterministicRulesEngine.evaluate_case(
        case_id=req.case_id,
        patient_name=req.patient_name,
        policy=policy,
        facts=req.facts
    )
    return report

@app.get("/api/cases")
def list_cases():
    notes_dir = DATA_DIR / "notes"
    cases = []
    if notes_dir.exists():
        for file in notes_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                cases.append(json.load(f))
    return cases
