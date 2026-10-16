import io
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.models.policy import (
    Policy,
    PolicyLifecycleStatus,
    PolicySection,
    PolicySearchResult,
)
from app.models.evaluation import EvaluationReport
from app.engine.rules_engine import DeterministicRulesEngine
from app.services.pdf_extractor import PDFExtractorService
from app.services.policy_registry import (
    PolicyRegistryService,
    DuplicatePolicyError,
    VersionConflictError,
    PolicyRegistryError,
)

from app.models.criteria import (
    CriterionRule,
    PolicyRuleset,
    VerificationStatus,
    VerificationGateRequest,
    CriteriaEvaluationRequest,
)
from app.services.criteria_service import CriteriaService, PolicyVerificationGateError

app = FastAPI(
    title="MedRule Decision-Support API",
    version="1.0.0",
    description="Rulebook-Driven Medical Insurance Authorization & Policy Registry Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
registry_service = PolicyRegistryService()
criteria_service = CriteriaService(DATA_DIR)

class EvaluateRequest(BaseModel):
    case_id: str
    patient_name: str
    policy_id: str
    facts: Dict[str, Any]

class StatusUpdatePayload(BaseModel):
    status: PolicyLifecycleStatus

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MedRule Policy & Evaluation Engine",
        "version": "1.0.0",
        "phase": "Phase 1 - Ingestion & Registry Active"
    }

# --- Policy Registry & Ingestion Endpoints (Phase 1) ---

@app.get("/api/policies", response_model=List[Policy])
def list_policies(
    lifecycle_status: Optional[PolicyLifecycleStatus] = None,
    insurer: Optional[str] = None
):
    policies = registry_service.get_all(status=lifecycle_status)
    if insurer:
        policies = [p for p in policies if p.insurer.lower() == insurer.lower()]
    return policies

@app.get("/api/policies/{policy_id}", response_model=Policy)
def get_policy(policy_id: str):
    policy = registry_service.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")
    return policy

@app.post("/api/policies/upload", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def upload_policy_pdf(
    file: UploadFile = File(...),
    insurer: str = Form(...),
    policy_name: str = Form(...),
    version: str = Form(...),
    procedure_type: str = Form(...),
    procedure_full_name: str = Form(...),
    effective_date: str = Form(...),
    plan: str = Form("Commercial & Medicare Advantage Plans"),
    cpt_codes: str = Form("")
):
    """
    Secure Policy PDF Ingestion:
    - Validates MIME type and file size (< 25MB)
    - Computes SHA-256 checksum
    - Extracts text by page, preserving page numbers
    - Detects scanned pages and produces quality report
    - Parses structured sections and numbered clauses
    - Enforces version management (prevents silent overwrites)
    - Registers policy in NEEDS_REVIEW status
    """
    # 1. Validation
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. MedRule accepts only valid PDF documents."
        )

    file_bytes = await file.read()
    max_size = 25 * 1024 * 1024  # 25MB
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum policy PDF size is 25MB."
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 2. Checksum & Extraction
    checksum = PDFExtractorService.compute_sha256(file_bytes)
    try:
        pages_data, quality_report, sections = PDFExtractorService.extract_document(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"PDF extraction failed. File may be corrupted or password-protected: {str(e)}"
        )

    cpt_list = [c.strip() for c in cpt_codes.split(",") if c.strip()]

    # 3. Registration & Overwrite Prevention
    try:
        policy = registry_service.register_policy_upload(
            file_bytes=file_bytes,
            filename=file.filename,
            insurer=insurer,
            policy_name=policy_name,
            version=version,
            procedure_type=procedure_type,
            procedure_full_name=procedure_full_name,
            effective_date=effective_date,
            cpt_codes=cpt_list,
            plan=plan,
            sections=sections,
            quality_report=quality_report,
            checksum=checksum
        )
        return policy
    except DuplicatePolicyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except VersionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.patch("/api/policies/{policy_id}/status", response_model=Policy)
def update_policy_lifecycle(policy_id: str, payload: StatusUpdatePayload):
    """
    Policy Activation Workflow:
    Transitions state: DRAFT -> PROCESSING -> NEEDS_REVIEW -> APPROVED_FOR_USE -> ARCHIVED.
    """
    try:
        updated = registry_service.update_status(policy_id, payload.status)
        return updated
    except PolicyRegistryError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/policies/{policy_id}/file")
def get_original_policy_file(policy_id: str):
    """Downloads or streams the canonical stored original PDF."""
    policy = registry_service.get_by_id(policy_id)
    if not policy or not policy.storage_path:
        raise HTTPException(status_code=404, detail="Policy file not found.")

    storage_path = Path(policy.storage_path)
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="Physical PDF file missing from storage.")

    safe_filename = policy.original_filename or f"{policy.id}.pdf"
    return FileResponse(
        path=str(storage_path),
        media_type="application/pdf",
        content_disposition_type="inline",
        filename=safe_filename,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'}
    )

@app.get("/api/policies/search/sections", response_model=List[PolicySearchResult])
def search_policy_sections(
    query: str = Query(..., min_length=2),
    approved_only: bool = Query(True),
    insurer: Optional[str] = Query(None)
):
    """Searches extracted sections across active/approved policies with citations."""
    return registry_service.search_sections(
        query=query,
        approved_only=approved_only,
        insurer=insurer
    )

# --- Phase 2: Policy Criteria Encoding & Verification Gate Endpoints ---

@app.get("/api/policies/{policy_id}/criteria", response_model=PolicyRuleset)
def get_policy_criteria(policy_id: str):
    """Retrieves structured criteria ruleset and verification status for a policy."""
    policy = registry_service.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")

    ruleset = criteria_service.get_ruleset(policy.id)
    if not ruleset:
        # Build draft ruleset from policy.criteria if available
        rules = []
        for c in policy.criteria:
            rules.append(CriterionRule(
                id=c.id,
                policy_id=policy.id,
                policy_version=policy.version,
                section_number=c.section,
                section_name=c.name,
                source_page=1,
                source_text=c.requirement,
                plain_english_description=f"Requirement: {c.requirement}",
                is_mandatory=c.mandatory,
                fact_key=c.fact_key,
                threshold_value=c.min_value,
                comparison_op=">=" if c.min_value else None,
                threshold_unit="weeks" if "week" in c.requirement.lower() else None,
                conditional_prerequisite=c.conditional_on,
                verification_status=VerificationStatus.DRAFT
            ))
        ruleset = PolicyRuleset(
            policy_id=policy.id,
            policy_name=policy.policy_name,
            policy_version=policy.version,
            policy_checksum=policy.sha256_checksum or "",
            procedure_type=policy.procedure_type,
            rules=rules,
            verification_status=VerificationStatus.DRAFT
        )
        criteria_service.save_ruleset(ruleset)

    return ruleset

@app.post("/api/policies/{policy_id}/criteria", response_model=PolicyRuleset)
def save_policy_criteria(policy_id: str, payload: PolicyRuleset):
    """Proposes or updates structured criteria ruleset for a policy (defaults to DRAFT)."""
    policy = registry_service.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")

    payload.policy_id = policy.id
    payload.policy_version = policy.version
    if not payload.policy_checksum:
        payload.policy_checksum = policy.sha256_checksum or ""

    return criteria_service.save_ruleset(payload)

@app.post("/api/policies/{policy_id}/criteria/verify-gate", response_model=PolicyRuleset)
def verify_policy_criteria_gate(policy_id: str, req: VerificationGateRequest):
    """
    Policy Verification Gate:
    Enforces side-by-side verification, count completeness, independent 2nd reviewer sign-off,
    and policy checksum matching before promoting rules to APPROVED_VERIFIED.
    """
    policy = registry_service.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")

    try:
        updated_ruleset = criteria_service.verify_ruleset_gate(policy, req)
        return updated_ruleset
    except PolicyVerificationGateError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/api/criteria/evaluate", response_model=EvaluationReport)
def evaluate_criteria(req: CriteriaEvaluationRequest):
    """
    Phase 2 Deterministic Criteria Evaluator:
    Enforces Policy Verification Gate, evaluates logic trees/thresholds/exclusions,
    separates missing docs from clinical failures, and outputs reasoning before verdict.
    """
    policy = registry_service.get_by_id(req.policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{req.policy_id}' not found.")

    try:
        report = criteria_service.evaluate_policy_case(
            policy=policy,
            case_id=req.case_id,
            patient_name=req.patient_name,
            facts=req.patient_facts
        )
        return report
    except PolicyVerificationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Decision Evaluation & Case Endpoints ---

@app.post("/api/evaluate", response_model=EvaluationReport)
def evaluate_request(req: EvaluateRequest):
    policy = registry_service.get_by_id(req.policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{req.policy_id}' not found.")

    # Phase 1 Exit Criterion: Policy must be in APPROVED_FOR_USE status before assessment
    if policy.lifecycle_status != PolicyLifecycleStatus.APPROVED_FOR_USE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Policy '{policy.id}' is currently in '{policy.lifecycle_status.value}' state. "
                "Policies must be approved by an authorized reviewer before use in evaluations."
            )
        )

    ruleset = criteria_service.get_ruleset(policy.id)
    if ruleset:
        if ruleset.verification_status != VerificationStatus.APPROVED_VERIFIED:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Policy Verification Gate Blocked: Ruleset for '{policy.id}' is in '{ruleset.verification_status.value}' state. "
                    "Rules must be verified and approved by two independent reviewers before use in evaluations."
                )
            )
        try:
            return criteria_service.evaluate_policy_case(
                policy=policy,
                case_id=req.case_id,
                patient_name=req.patient_name,
                facts=req.facts
            )
        except PolicyVerificationGateError as e:
            raise HTTPException(status_code=400, detail=str(e))

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
