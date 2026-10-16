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
from app.models.note import (
    ClinicalNoteRecord,
    ExtractedFact,
    ClinicalFactStatus,
    FactCorrectionRequest,
    FactFlagRequest,
)
from app.services.note_extractor import ClinicalNoteExtractorService, OCRService

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
note_extractor_service = ClinicalNoteExtractorService(data_dir=DATA_DIR)

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

# --- Phase 3: Doctor's Note Ingestion, Fact Extraction & Evidence Review ---

@app.get("/api/notes/ocr-status")
def get_ocr_status():
    """
    Reports the status of the OCR subsystem and any unconfigured components.
    Gracefully flags when OCR binary is unavailable and reports fallback mode.
    """
    is_available, details = OCRService.get_ocr_status()
    return {
        "ocr_available": is_available,
        "status": "OCR_AVAILABLE" if is_available else "OCR_UNAVAILABLE_FALLBACK_TO_MANUAL_REVIEW",
        "details": details,
        "supported_formats": ["PDF", "PNG", "JPEG"],
        "fallback_mode": "Manual clinician review and side-by-side verification interface"
    }

@app.post("/api/notes/upload", response_model=ClinicalNoteRecord, status_code=status.HTTP_201_CREATED)
async def upload_clinical_note(
    file: UploadFile = File(...),
    policy_id: str = Form("P-UHC-CT-2026"),
    patient_name: Optional[str] = Form(None),
    facility: Optional[str] = Form(None),
    procedure_requested: Optional[str] = Form(None),
    insurance_plan: Optional[str] = Form("United Healthcare"),
):
    """
    Secure Doctor's Note Upload & Fact Extraction:
    - Validates file format (.pdf only) and file size (< 15MB)
    - Computes SHA-256 and stores original file
    - Page-by-page text extraction with precise page citations
    - Detects scanned pages and low character density
    - Treats document content as untrusted data (mitigating prompt injections)
    - Extracts only facts required by the policy's approved evidence schema
    - Detects contradictions, ambiguities, and abbreviations
    - Saves record with DEVELOPMENT/DEMO synthetic governance watermark
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. MedRule accepts only valid clinical PDF documents."
        )

    file_bytes = await file.read()
    max_size = 15 * 1024 * 1024  # 15MB
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum clinical note PDF size is 15MB."
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    policy_rules = None
    ruleset = criteria_service.get_ruleset(policy_id)
    if ruleset:
        policy_rules = ruleset.rules

    try:
        record = note_extractor_service.extract_note(
            file_bytes=file_bytes,
            filename=file.filename,
            policy_id=policy_id,
            policy_rules=policy_rules,
            patient_name_override=patient_name,
            facility_override=facility,
            procedure_requested_override=procedure_requested,
            insurance_plan=insurance_plan,
        )
        return record
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Clinical note processing failed: {str(e)}"
        )

@app.get("/api/notes/{case_id}", response_model=ClinicalNoteRecord)
def get_clinical_note(case_id: str):
    """Retrieves full case record with extracted facts and quality report."""
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case note '{case_id}' not found.")
    return record

@app.get("/api/notes/{case_id}/document")
def get_note_document(case_id: str):
    """Streams original uploaded doctor's note PDF inline for browser viewing."""
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case note '{case_id}' not found.")
    if not record.storage_path or not Path(record.storage_path).exists():
        raise HTTPException(status_code=404, detail="Physical note PDF not found in storage.")

    safe_filename = record.original_filename or f"{case_id}.pdf"
    return FileResponse(
        path=record.storage_path,
        media_type="application/pdf",
        content_disposition_type="inline",
        filename=safe_filename,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'}
    )

@app.patch("/api/notes/{case_id}/facts/{fact_key}", response_model=ClinicalNoteRecord)
def correct_extracted_fact(case_id: str, fact_key: str, payload: FactCorrectionRequest):
    """
    Auditable Fact Correction Workflow:
    Allows clinical reviewers to correct or override an extracted fact.
    Records reviewer name, reason, timestamp, and audit trail entry.
    """
    payload.fact_key = fact_key
    try:
        updated = note_extractor_service.apply_fact_override(case_id, payload)
        return updated
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/notes/{case_id}/flag", response_model=ClinicalNoteRecord)
def flag_extracted_fact(case_id: str, payload: FactFlagRequest):
    """Flags an extracted fact for secondary clinical review."""
    try:
        updated = note_extractor_service.flag_fact_for_review(case_id, payload)
        return updated
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/cases", response_model=List[ClinicalNoteRecord])
def list_cases():
    """Lists all saved cases with clinical note records."""
    return note_extractor_service.list_note_records()

