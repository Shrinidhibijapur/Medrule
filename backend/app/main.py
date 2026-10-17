import os
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.deps import (
    get_current_user,
    require_permission,
    require_role,
    verify_csrf_if_cookie,
)
from app.models.auth import Permission, AuthenticatedUser, UserRole, AuditEvent
from app.services.audit_service import audit_service
from app.api.auth import router as auth_router

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
from app.services.criteria_service import CriteriaService, PolicyVerificationGateError, PolicyMismatchError
from app.models.trace import AgentTrace
from app.models.note import (
    ClinicalNoteRecord,
    ExtractedFact,
    ClinicalFactStatus,
    FactCorrectionRequest,
    FactFlagRequest,
)
from app.services.note_extractor import ClinicalNoteExtractorService, OCRService
from app.models.terminology import (
    ApprovedSource,
    TerminologyDefinition,
    TerminologyLookupRequest,
    TerminologyLookupResponse,
)
from app.services.terminology_service import TerminologyService
from app.services.agent_service import AgentService, AgentIntent

app = FastAPI(
    title="MedRule Decision-Support API",
    version="1.0.0",
    description="Rulebook-Driven Medical Insurance Authorization & Policy Registry Engine"
)

# Apply CORS with explicit allowed origins for secure cookie authentication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply standard Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Allow PDF clinical documents to be previewed inside the trusted MedRule frontend iframe
    if request.url.path.endswith("/document"):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "frame-ancestors 'self' http://localhost:5173 http://127.0.0.1:5173;"
        )
    else:
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "frame-ancestors 'none';"
        )
    return response

# Mount Authentication Router (OIDC PKCE, session management, CSRF)
app.include_router(auth_router)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
registry_service = PolicyRegistryService()
criteria_service = CriteriaService(DATA_DIR)
note_extractor_service = ClinicalNoteExtractorService(data_dir=DATA_DIR)
terminology_service = TerminologyService(data_dir=DATA_DIR)

def check_case_tenant(case_record: ClinicalNoteRecord, current_user: AuthenticatedUser) -> None:
    """Enforces tenant isolation. Users cannot view or modify cases outside their organization."""
    case_org = getattr(case_record, "organization_id", None) or "org_riverside"
    if not current_user.can_access_tenant(case_org):
        audit_service.log_event(
            action="TENANT_ACCESS_DENIED",
            user=current_user,
            resource=f"case:{case_record.case_id}",
            status="DENIED",
            details={
                "case_organization": case_org,
                "user_organization": current_user.organization_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant Access Denied: Case '{case_record.case_id}' belongs to organization '{case_org}'."
        )

@app.get("/api/audit/logs", response_model=List[AuditEvent])
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.AUDIT_VIEW_COMPLIANCE))
):
    """
    Retrieves system security and clinical governance audit trail.
    Restricted to Compliance Officers and System Administrators.
    """
    return audit_service.get_events(user=current_user, limit=limit, action_filter=action)


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
    insurer: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    policies = registry_service.get_all(status=lifecycle_status)
    if insurer:
        policies = [p for p in policies if p.insurer.lower() == insurer.lower()]
    return policies

@app.get(
    "/api/policies/{policy_id}",
    response_model=Policy,
    responses={
        404: {"description": "Policy not found"}
    }
)
def get_policy(
    policy_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    policy = registry_service.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")
    return policy

@app.post(
    "/api/policies/upload",
    response_model=Policy,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid PDF format or empty file"},
        413: {"description": "File size exceeds 25MB maximum limit"},
        422: {"description": "PDF extraction failed or file corrupted"},
        409: {"description": "Duplicate policy or version overwrite conflict"}
    }
)
async def upload_policy_pdf(
    file: UploadFile = File(...),
    insurer: str = Form(...),
    policy_name: str = Form(...),
    version: str = Form(...),
    procedure_type: str = Form(...),
    procedure_full_name: str = Form(...),
    effective_date: str = Form(...),
    plan: str = Form("Commercial & Medicare Advantage Plans"),
    cpt_codes: str = Form(""),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.POLICY_ADMIN)),
    _csrf: None = Depends(verify_csrf_if_cookie)
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
        audit_service.log_event(
            action="POLICY_UPLOAD",
            user=current_user,
            resource=policy.id,
            status="SUCCESS",
            details={"policy_name": policy.policy_name, "version": policy.version, "checksum": policy.sha256_checksum}
        )
        return policy
    except DuplicatePolicyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except VersionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.patch("/api/policies/{policy_id}/status", response_model=Policy)
def update_policy_lifecycle(
    policy_id: str,
    payload: StatusUpdatePayload,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.POLICY_ADMIN)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """
    Policy Activation Workflow:
    Transitions state: DRAFT -> PROCESSING -> NEEDS_REVIEW -> APPROVED_FOR_USE -> ARCHIVED.
    """
    try:
        updated = registry_service.update_status(policy_id, payload.status)
        audit_service.log_event(
            action="POLICY_STATUS_CHANGE",
            user=current_user,
            resource=policy_id,
            status="SUCCESS",
            details={"new_status": payload.status.value}
        )
        return updated
    except PolicyRegistryError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/policies/{policy_id}/file")
def get_original_policy_file(
    policy_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
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
    insurer: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Searches extracted sections across active/approved policies with citations."""
    return registry_service.search_sections(
        query=query,
        approved_only=approved_only,
        insurer=insurer
    )

# --- Phase 2: Policy Criteria Encoding & Verification Gate Endpoints ---

@app.get("/api/policies/{policy_id}/criteria", response_model=PolicyRuleset)
def get_policy_criteria(
    policy_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
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
def save_policy_criteria(
    policy_id: str,
    payload: PolicyRuleset,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.POLICY_ADMIN)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
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
def verify_policy_criteria_gate(
    policy_id: str,
    req: VerificationGateRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.POLICY_ADMIN)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
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
        audit_service.log_event(
            action="POLICY_GATE_VERIFICATION",
            user=current_user,
            resource=policy_id,
            status="SUCCESS",
            details={"primary_reviewer": req.primary_reviewer, "secondary_reviewer": req.secondary_reviewer}
        )
        return updated_ruleset
    except PolicyVerificationGateError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/api/criteria/evaluate", response_model=EvaluationReport)
def evaluate_criteria(
    req: CriteriaEvaluationRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.EVALUATION_RUN))
):
    """
    Phase 2 & Phase 4 Deterministic Criteria Evaluator:
    Enforces Policy Verification Gate, evaluates logic trees/thresholds/exclusions,
    separates missing docs from clinical failures, and outputs reasoning before verdict.
    Can evaluate facts provided directly OR read from a stored clinical note case record.
    """
    policy = registry_service.get_by_id(req.policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{req.policy_id}' not found.")

    facts = req.patient_facts
    if (facts is None or len(facts) == 0) and req.case_id:
        note_record = note_extractor_service.get_note_record(req.case_id)
        if note_record:
            check_case_tenant(note_record, current_user)
            try:
                return criteria_service.evaluate_note_record(policy=policy, note_record=note_record)
            except PolicyVerificationGateError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except PolicyMismatchError as e:
                raise HTTPException(status_code=422, detail=str(e))

    try:
        report = criteria_service.evaluate_policy_case(
            policy=policy,
            case_id=req.case_id,
            patient_name=req.patient_name,
            facts=facts or {}
        )
        return report
    except PolicyVerificationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PolicyMismatchError as e:
        raise HTTPException(status_code=422, detail=str(e))

# --- Decision Evaluation & Case Endpoints ---

@app.post("/api/evaluate", response_model=EvaluationReport)
def evaluate_request(
    req: EvaluateRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.EVALUATION_RUN)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
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
    if not ruleset:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Policy Verification Gate Blocked: No criteria ruleset found for policy '{policy.id}'. "
                "Rules must be verified and approved by two independent reviewers before use in evaluations."
            )
        )
    if ruleset.verification_status != VerificationStatus.APPROVED_VERIFIED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Policy Verification Gate Blocked: Ruleset for '{policy.id}' is in '{ruleset.verification_status.value}' state. "
                "Rules must be verified and approved by two independent reviewers before use in evaluations."
            )
        )
    try:
        report = criteria_service.evaluate_policy_case(
            policy=policy,
            case_id=req.case_id,
            patient_name=req.patient_name,
            facts=req.facts
        )
        audit_service.log_event(
            action="EVALUATION_RUN",
            user=current_user,
            resource=f"case:{req.case_id}",
            status="SUCCESS",
            details={"policy_id": req.policy_id, "verdict": report.verdict.value}
        )
        return report
    except PolicyVerificationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Phase 3: Doctor's Note Ingestion, Fact Extraction & Evidence Review ---

@app.get("/api/notes/ocr-status")
def get_ocr_status(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
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
    policy_id: Optional[str] = Form(None),
    patient_name: Optional[str] = Form(None),
    facility: Optional[str] = Form(None),
    procedure_requested: Optional[str] = Form(None),
    insurance_plan: Optional[str] = Form(None),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_UPLOAD)),
    _csrf: None = Depends(verify_csrf_if_cookie)
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
    - Attaches organization_id for tenant isolation
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

    effective_policy_id = policy_id
    policy_rules = None
    if effective_policy_id:
        ruleset = criteria_service.get_ruleset(effective_policy_id)
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
            organization_id=current_user.organization_id,
        )
        audit_service.log_event(
            action="CASE_UPLOAD",
            user=current_user,
            resource=f"case:{record.case_id}",
            status="SUCCESS",
            details={
                "filename": file.filename,
                "document_id": record.document_id,
                "policy_id": policy_id,
                "procedure": record.procedure_requested,
                "organization_id": current_user.organization_id
            }
        )
        return record
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Clinical note processing failed: {str(e)}"
        )

@app.post("/api/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document_standalone(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_UPLOAD)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """
    Dedicated Standalone Document Upload API for Ask MedRule:
    - Extracts PDF page-by-page text
    - Generates unique document ID and computes SHA-256
    - Does NOT require an insurance policy or case assignment
    - Returns document metadata, page count, and extracted clinical facts
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. MedRule accepts only valid clinical PDF documents."
        )

    file_bytes = await file.read()
    max_size = 15 * 1024 * 1024  # 15MB
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=413, detail="File too large. Maximum clinical note PDF size is 15MB.")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        record = note_extractor_service.extract_note(
            file_bytes=file_bytes,
            filename=file.filename,
            policy_id=None,
            organization_id=current_user.organization_id,
        )
        audit_service.log_event(
            action="DOCUMENT_UPLOAD",
            user=current_user,
            resource=f"document:{record.document_id or record.case_id}",
            status="SUCCESS",
            details={
                "filename": file.filename,
                "document_id": record.document_id or record.case_id,
                "sha256": record.sha256_checksum,
                "pages": record.total_pages,
                "organization_id": current_user.organization_id
            }
        )
        return {
            "document_id": record.document_id or record.case_id,
            "case_id": record.case_id,
            "filename": record.original_filename,
            "sha256_checksum": record.sha256_checksum,
            "total_pages": record.total_pages,
            "patient_name": record.patient_name,
            "date_of_visit": record.date_of_visit,
            "procedure_requested": record.procedure_requested,
            "insurance_plan": record.insurance_plan,
            "facts": {k: f.model_dump() for k, f in record.facts.items()} if record.facts else {},
            "raw_pages_text": record.raw_pages_text
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Document processing failed: {str(e)}")

@app.get("/api/documents/{document_id}")
def get_document_details(
    document_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_VIEW))
):
    """Retrieves extracted document text, metadata, and facts by document_id or case_id."""
    record = note_extractor_service.get_note_record(document_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    check_case_tenant(record, current_user)
    return {
        "document_id": record.document_id or record.case_id,
        "case_id": record.case_id,
        "filename": record.original_filename,
        "sha256_checksum": record.sha256_checksum,
        "total_pages": record.total_pages,
        "patient_name": record.patient_name,
        "date_of_visit": record.date_of_visit,
        "procedure_requested": record.procedure_requested,
        "insurance_plan": record.insurance_plan,
        "facts": {k: f.model_dump() for k, f in record.facts.items()} if record.facts else {},
        "raw_pages_text": record.raw_pages_text
    }

@app.get("/api/notes/{case_id}", response_model=ClinicalNoteRecord)
def get_clinical_note(
    case_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_VIEW))
):
    """Retrieves full case record with extracted facts and quality report."""
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case note '{case_id}' not found.")
    check_case_tenant(record, current_user)
    return record

@app.get("/api/notes/{case_id}/document")
def get_note_document(
    case_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_VIEW))
):
    """Streams original uploaded doctor's note PDF inline for browser viewing."""
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case note '{case_id}' not found.")
    check_case_tenant(record, current_user)
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
def correct_extracted_fact(
    case_id: str,
    fact_key: str,
    payload: FactCorrectionRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.FACT_OVERRIDE)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """
    Auditable Fact Correction Workflow (Phase 5):
    Allows clinical reviewers to correct or override an extracted fact.
    Records reviewer name, reason, timestamp, and audit trail entry.
    Automatically reevaluates the policy ruleset with the updated facts.
    """
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case note '{case_id}' not found.")
    check_case_tenant(record, current_user)

    payload.fact_key = fact_key
    if not payload.reviewer_name:
        payload.reviewer_name = current_user.full_name
    try:
        updated = note_extractor_service.apply_fact_override(case_id, payload)
        # Re-evaluate automatically to update outcome
        target_policy = registry_service.get_by_id(updated.policy_id)
        if target_policy and target_policy.lifecycle_status == PolicyLifecycleStatus.APPROVED_FOR_USE:
            try:
                report = criteria_service.evaluate_note_record(policy=target_policy, note_record=updated)
                updated.latest_outcome = report.decision_outcome.value if hasattr(report.decision_outcome, "value") else str(report.decision_outcome)
                updated.latest_evaluation = report.model_dump()
                note_extractor_service.save_note_record(updated)
            except Exception as eval_err:
                logger.warning(f"Auto-reevaluation notice: {eval_err}")

        audit_service.log_event(
            action="FACT_OVERRIDE",
            user=current_user,
            resource=f"case:{case_id}",
            status="SUCCESS",
            details={
                "fact_key": fact_key,
                "corrected_value": str(payload.corrected_value),
                "corrected_status": payload.corrected_status.value if hasattr(payload.corrected_status, "value") else str(payload.corrected_status),
                "reason": payload.reason
            }
        )
        return updated
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/notes/{case_id}/flag", response_model=ClinicalNoteRecord)
def flag_extracted_fact(
    case_id: str,
    payload: FactFlagRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.FACT_FLAG)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """Flags an extracted fact for secondary clinical review."""
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case note '{case_id}' not found.")
    check_case_tenant(record, current_user)

    if not payload.reviewer_name:
        payload.reviewer_name = current_user.full_name
    try:
        updated = note_extractor_service.flag_fact_for_review(case_id, payload)
        audit_service.log_event(
            action="FACT_FLAG",
            user=current_user,
            resource=f"case:{case_id}",
            status="SUCCESS",
            details={
                "fact_key": payload.fact_key,
                "reason": payload.reason
            }
        )
        return updated
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Phase 5: Real-time dashboard statistics derived dynamically from saved case records.
    Computes total reviews, approved, not approved, pending, and recent review summaries.
    Enforces tenant isolation: users only see metrics for their authorized organization.
    """
    all_cases = note_extractor_service.list_note_records()
    cases = [c for c in all_cases if current_user.can_access_tenant(getattr(c, "organization_id", "org_riverside"))]
    total_reviews = len(cases)
    approved_count = 0
    not_approved_count = 0
    pending_count = 0

    recent_reviews = []
    for c in sorted(cases, key=lambda x: x.created_at or "", reverse=True):
        outcome = c.latest_outcome
        if not outcome:
            outcome = "PENDING_REVIEW"
            pending_count += 1
        elif outcome == "APPROVED":
            approved_count += 1
        elif outcome in ("DENIED", "NOT_APPROVED"):
            not_approved_count += 1
        else:
            pending_count += 1

        if len(recent_reviews) < 6:
            recent_reviews.append({
                "case_id": c.case_id,
                "patient_name": c.patient_name,
                "procedure": c.procedure_requested,
                "insurance_plan": c.insurance_plan,
                "policy_id": c.policy_id,
                "date": c.date_of_visit or (c.created_at[:10] if c.created_at else "2026-10-16"),
                "status": outcome
            })

    return {
        "total_reviews": total_reviews,
        "approved_count": approved_count,
        "not_approved_count": not_approved_count,
        "pending_count": pending_count,
        "recent_reviews": recent_reviews,
        "is_synthetic_demo": True
    }

@app.get("/api/cases", response_model=List[ClinicalNoteRecord])
def list_cases(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_VIEW))
):
    """Lists all saved cases with clinical note records filtered by tenant isolation."""
    all_cases = note_extractor_service.list_note_records()
    return [
        c for c in all_cases
        if current_user.can_access_tenant(getattr(c, "organization_id", "org_riverside"))
        and not (c.case_id and c.case_id.endswith("-TEST"))
    ]

@app.get("/api/cases/{case_id}", response_model=ClinicalNoteRecord)
def get_case(
    case_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.CASE_VIEW))
):
    """Retrieves an individual case record by case_id."""
    record = note_extractor_service.get_note_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Case record '{case_id}' not found.")
    check_case_tenant(record, current_user)
    return record

@app.post("/api/cases/{case_id}/evaluate", response_model=EvaluationReport)
def evaluate_case(
    case_id: str,
    policy_id: Optional[str] = Query(None, description="Optional override policy ID"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.EVALUATION_RUN)),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """
    Phase 4 & 5 Deterministic Case Evaluation:
    Connects extracted clinical facts to the structured criteria engine.
    Produces traceable criterion-by-criterion results, reasoning, and stores latest outcome.
    """
    note_record = note_extractor_service.get_note_record(case_id)
    if not note_record:
        raise HTTPException(status_code=404, detail=f"Case record '{case_id}' not found.")
    check_case_tenant(note_record, current_user)

    target_policy_id = policy_id or note_record.policy_id
    policy = registry_service.get_by_id(target_policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{target_policy_id}' not found.")

    try:
        report = criteria_service.evaluate_note_record(policy=policy, note_record=note_record)
        note_record.latest_outcome = report.decision_outcome.value if hasattr(report.decision_outcome, "value") else str(report.decision_outcome)
        note_record.latest_evaluation = report.model_dump()
        note_extractor_service.save_note_record(note_record)
        audit_service.log_event(
            action="EVALUATION_RUN",
            user=current_user,
            resource=f"case:{case_id}",
            status="SUCCESS",
            details={"policy_id": target_policy_id, "outcome": note_record.latest_outcome}
        )
        return report
    except PolicyVerificationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PolicyMismatchError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/api/cases/{case_id}/export")
@app.get("/api/cases/{case_id}/export-decision")
def export_case_audit_report(
    case_id: str,
    format: str = Query("txt", description="Export format: 'txt' or 'json'"),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.DECISION_EXPORT))
):
    """
    Phase 5 Auditable Decision Report Export:
    Generates a complete prior authorization audit package containing case data,
    policy checksum, verification gate status, line-by-line criterion outcomes,
    reviewer override history, audit trail, and clinical governance warnings.
    """
    note_record = note_extractor_service.get_note_record(case_id)
    if not note_record:
        raise HTTPException(status_code=404, detail=f"Case record '{case_id}' not found.")
    check_case_tenant(note_record, current_user)

    policy = registry_service.get_by_id(note_record.policy_id) if note_record.policy_id else None
    if not policy and note_record.policy_id:
        policy = registry_service.get_by_id(note_record.policy_id)

    audit_service.log_event(
        action="DECISION_EXPORT",
        user=current_user,
        resource=f"case:{case_id}",
        status="SUCCESS",
        details={"format": format, "policy_id": note_record.policy_id}
    )

    evaluation = None
    try:
        evaluation = criteria_service.evaluate_note_record(policy=policy, note_record=note_record)
    except Exception as e:
        logger.warning(f"Evaluation computation notice during export: {e}")

    if format.lower() == "json":
        bundle = {
            "export_type": "MEDRULE_AUDIT_PACKAGE",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "is_synthetic_demo": True,
            "case_id": note_record.case_id,
            "patient_name": note_record.patient_name,
            "patient_age": note_record.patient_age,
            "gender": note_record.gender,
            "facility": note_record.facility,
            "date_of_visit": note_record.date_of_visit,
            "procedure_requested": note_record.procedure_requested,
            "insurance_plan": note_record.insurance_plan,
            "policy_id": policy.id,
            "policy_version": policy.version,
            "policy_checksum": policy.sha256_checksum,
            "policy_verification_status": policy.lifecycle_status.value,
            "evaluation": evaluation.model_dump() if evaluation else None,
            "clinical_facts": {k: f.model_dump() for k, f in note_record.facts.items()},
            "audit_trail": note_record.audit_trail,
            "governance_notice": "DEVELOPMENT/DEMO MODE ONLY: Synthetic Clinical Records. Real patient evaluation remains BLOCKED until authentic policy and clinical sign-offs are completed."
        }
        return JSONResponse(
            content=bundle,
            headers={"Content-Disposition": f'attachment; filename="MedRule_Audit_{case_id}.json"'}
        )

    # Format 'txt' report
    lines = [
        "================================================================================",
        "                 MEDRULE PRIOR AUTHORIZATION AUDIT PACKAGE",
        "                [DEMO / SYNTHETIC CASE - NOT A CLINICAL DECISION]",
        "================================================================================",
        f"Case Identifier        : {note_record.case_id}",
        f"Patient Name           : {note_record.patient_name}",
        f"Patient Demographics   : Age {note_record.patient_age or 'N/A'}, Gender {note_record.gender or 'N/A'}",
        f"Encounter Facility     : {note_record.facility or 'N/A'}",
        f"Date of Visit          : {note_record.date_of_visit or 'N/A'}",
        f"Procedure Requested    : {note_record.procedure_requested}",
        f"Insurance Plan         : {note_record.insurance_plan}",
        f"Policy Rulebook        : {policy.policy_name} ({policy.id} v{policy.version})",
        f"Policy PDF Checksum    : {policy.sha256_checksum}",
        f"Policy Gate Status     : {policy.lifecycle_status.value}",
        f"Export Generated At    : {datetime.now(timezone.utc).isoformat()} UTC",
        "",
        "--------------------------------------------------------------------------------",
        "1. DETERMINISTIC EVALUATION OUTCOME",
        "--------------------------------------------------------------------------------",
    ]

    if evaluation:
        lines.extend([
            f"Final Verdict          : {evaluation.verdict.value}",
            f"Decision Outcome       : {evaluation.decision_outcome.value if evaluation.decision_outcome else 'N/A'}",
            f"Requires Human Review  : {'YES' if evaluation.requires_human_review else 'NO'}",
            "Verdict Sentence       :",
            f"  {evaluation.verdict_sentence}",
            "",
            "Key Reasoning Trace    :",
        ])
        for r in evaluation.key_reasoning:
            lines.append(f"  * {r}")

        if evaluation.review_reasons:
            lines.append("")
            lines.append("Clinical Review Reasons:")
            for rr in evaluation.review_reasons:
                lines.append(f"  ! {rr}")

        lines.extend([
            "",
            "--------------------------------------------------------------------------------",
            "2. CRITERION-BY-CRITERION RESULTS",
            "--------------------------------------------------------------------------------",
        ])
        for crit in evaluation.criteria_results:
            lines.extend([
                f"Rule ID    : {crit.rule_id} [{crit.criterion_name}]",
                f"Citation   : {crit.section} (Source Page: {crit.source_page or 'N/A'})",
                f"Status     : {crit.status.value} ({crit.ui_label})",
                f"Mandate    : {crit.requirement}",
                f"Evidence   : \"{crit.evidence_excerpt}\"",
                f"Rationale  : {crit.comment}",
            ])
            if crit.reviewer_overridden:
                lines.append(f"OVERRIDE   : Overridden by {crit.reviewer_override_by} - Reason: {crit.reviewer_override_reason}")
            lines.append("")
    else:
        lines.append("Evaluation report could not be computed (case has not been evaluated or verification gate blocked).")

    lines.extend([
        "--------------------------------------------------------------------------------",
        "3. EXTRACTED CLINICAL EVIDENCE FACTS & OVERRIDES",
        "--------------------------------------------------------------------------------",
    ])
    for k, fact in note_record.facts.items():
        lines.append(f"Fact Key   : {fact.fact_key} ({fact.label})")
        lines.append(f"Value      : {fact.value} | Status: {fact.status.value} | Confidence: {fact.confidence}")
        lines.append(f"Excerpt    : \"{fact.excerpt}\" (Page {fact.source_page})")
        if fact.reviewer_override and fact.reviewer_override.is_overridden:
            ro = fact.reviewer_override
            lines.append(f"  [OVERRIDDEN by {ro.overridden_by} at {ro.overridden_at}]")
            lines.append(f"  Previous: {ro.original_value} ({ro.original_status.value if hasattr(ro.original_status, 'value') else ro.original_status}) -> New: {ro.corrected_value} ({ro.corrected_status.value if hasattr(ro.corrected_status, 'value') else ro.corrected_status})")
            lines.append(f"  Justification: {ro.reason}")
        lines.append("")

    lines.extend([
        "--------------------------------------------------------------------------------",
        "4. AUDIT TRAIL LOG",
        "--------------------------------------------------------------------------------",
    ])
    if note_record.audit_trail:
        for ev in note_record.audit_trail:
            lines.append(f"[{ev.get('timestamp')}] {ev.get('action')}: {ev.get('reason', '')} (Actor: {ev.get('reviewer', 'System')})")
    else:
        lines.append("No audit events recorded.")

    lines.extend([
        "",
        "================================================================================",
        "5. REGULATORY & CLINICAL GOVERNANCE WARNING",
        "================================================================================",
        "DEVELOPMENT / DEMO MODE ONLY: Synthetic Clinical Records.",
        "Real patient clinical evaluation remains strictly BLOCKED until authentic policy",
        "rulebooks and genuine clinical reviewer sign-offs are completed.",
        "================================================================================",
    ])

    return Response(
        content="\n".join(lines),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="MedRule_Audit_{case_id}.txt"'}
    )


# --- Authoritative Terminology-Only Lookup Endpoints (Phase 6) ---

@app.get("/api/terminology/sources", response_model=List[ApprovedSource])
def get_terminology_sources(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Approved Source Registry:
    Returns explicitly registered and verified terminology authorities
    along with their permitted scopes and access restrictions.
    """
    return terminology_service.get_approved_sources()


@app.post(
    "/api/terminology/lookup",
    response_model=TerminologyLookupResponse,
    responses={
        400: {"description": "Invalid lookup request or term formatting error"}
    }
)
def lookup_terminology(
    payload: TerminologyLookupRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """
    Authoritative Terminology-Only Lookup:
    1. RULEBOOK-FIRST: Always checks selected policy rulebook definitions first.
    2. APPROVED SOURCES: Queries only allowlisted authoritative domains (NLM MeSH, MedlinePlus, CMS).
    3. SAFE FAILURE: Returns UNRESOLVED or CONFLICTING with human review flag if ambiguous.
    4. STRICT SEPARATION: Strictly isolated from policy coverage rules and evaluation engine.
    """
    if not payload.term or len(payload.term.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search term must be at least 2 characters.")
    return terminology_service.lookup_term(payload)


@app.get("/api/terminology/rulebook-terms/{policy_id}")
def get_policy_rulebook_terms(
    policy_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Rulebook-First Definitions:
    Retrieves all terms natively defined by the specified policy rulebook.
    """
    return terminology_service.get_rulebook_terms(policy_id)


@app.get("/api/terminology/audit-log")
def get_terminology_audit_log(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.AUDIT_VIEW_COMPLIANCE))
):
    """
    Terminology Provenance Audit Trail:
    Retrieves the immutable audit log of all clinical terminology lookups.
    """
    return terminology_service.get_audit_trail()


# --- Phase 9: Interactive Agent Copilot (Groq Llama 3.3 & Deterministic Engine) ---

class AgentCitation(BaseModel):
    document_id: Optional[str] = None
    document_filename: Optional[str] = None
    page_number: int
    excerpt: Optional[str] = None

class AgentChatRequest(BaseModel):
    message: str
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    policy_id: Optional[str] = None
    intent: Optional[str] = None
    request_id: Optional[str] = None
    groq_api_key: Optional[str] = None
    model: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None

class SetGroqKeyRequest(BaseModel):
    groq_api_key: str

class AgentChatResponse(BaseModel):
    response: str
    intent: str = "DOCUMENT_ANALYSIS"
    model_used: str
    is_groq_powered: bool
    request_id: Optional[str] = None
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list)
    document_filename: Optional[str] = None
    valid_page_count: Optional[int] = None
    patient_name: Optional[str] = None
    procedure: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
    extracted_facts: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    compatibility_status: Optional[str] = "COMPATIBLE"
    citations: List[AgentCitation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

@app.get("/api/agent/status")
def get_agent_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Reports whether Groq AI Copilot is active and lists supported models."""
    has_key = AgentService.is_configured()
    return {
        "groq_configured": has_key,
        "active_model": settings.GROQ_MODEL or "llama-3.3-70b-versatile",
        "supported_models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ],
        "status": "ONLINE_GROQ_POWERED" if has_key else "DETERMINISTIC_MODE_GROQ_KEY_AVAILABLE"
    }

@app.post("/api/agent/set-groq-key")
def set_groq_key(
    payload: SetGroqKeyRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_if_cookie)
):
    """Configures or updates Groq API key for the active session (Administrative)."""
    key = payload.groq_api_key.strip()
    if not key.startswith("gsk_") and len(key) < 20:
        raise HTTPException(status_code=400, detail="Invalid Groq API Key format. Groq keys typically start with 'gsk_'.")
    settings.GROQ_API_KEY = key
    os.environ["GROQ_API_KEY"] = key
    audit_service.log_event(
        action="GROQ_API_KEY_CONFIGURED",
        user=current_user,
        resource="system:groq_agent",
        status="SUCCESS",
        details={"model": settings.GROQ_MODEL}
    )
    return {
        "status": "SUCCESS",
        "message": "Groq API key activated successfully. Interactive Agent is now live with Llama 3.3.",
        "model": settings.GROQ_MODEL
    }

@app.get("/api/agent/trace/{case_id}", response_model=AgentTrace)
def get_case_agent_trace(
    case_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retrieves the structured, auditable decision trace for a case assessment.
    Links encounter, document hash, valid page bounds, policy compatibility,
    extracted facts, criterion evaluations, evidence citations, narrative validation, and audit history.
    """
    note_record = note_extractor_service.get_note_record(case_id)
    if not note_record:
        raise HTTPException(status_code=404, detail=f"Case record '{case_id}' not found.")
    check_case_tenant(note_record, current_user)

    policy = None
    if note_record.policy_id:
        policy = registry_service.get_by_id(note_record.policy_id)

    evaluation = None
    if note_record.latest_evaluation:
        try:
            evaluation = EvaluationReport(**note_record.latest_evaluation)
        except Exception:
            pass

    trace = AgentService.generate_agent_trace(
        case_id=case_id,
        note_record=note_record,
        evaluation_report=evaluation,
        policy=policy,
        compatibility_status="COMPATIBLE",
        llm_invoked=False
    )
    return trace

@app.post("/api/agent/analyze-document", response_model=AgentChatResponse)
async def analyze_document_endpoint(
    req: AgentChatRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Dedicated Document-Analysis Conversational Endpoint for Ask MedRule:
    Forces DOCUMENT_ANALYSIS intent regardless of query phrasing, analyzing
    explicitly selected document(s) with Groq without requiring a payer policy.
    """
    req.intent = AgentIntent.DOCUMENT_ANALYSIS.value
    return await chat_with_agent(req, request, current_user)

def resolve_policy_for_encounter(
    note_record: Optional[ClinicalNoteRecord],
    requested_policy_id: Optional[str],
    registry_svc: PolicyRegistryService,
    criteria_svc: CriteriaService
) -> Tuple[Optional[Policy], Optional[str], str]:
    """
    Resolves an authentic, verified, approved policy from the policy registry.
    Handles explicit IDs and the 'UNSPECIFIED' default lookup case.
    Distinguishes:
    - SPECIFIED_POLICY_NOT_FOUND (invalid lookup key)
    - POLICY_NOT_APPROVED (registered but in NEEDS_REVIEW or ARCHIVED status)
    - POLICY_MISMATCH (payer, modality, or anatomy incompatibility)
    - NO_APPLICABLE_VERIFIED_POLICY (missing policy ingestion for encounter payer/procedure)
    - COMPATIBLE_RESOLVED (compatible approved policy found)
    """
    if not note_record:
        return None, "No active clinical note record loaded for policy resolution.", "NO_RECORD"

    target_id = (requested_policy_id or getattr(note_record, "policy_id", None) or "").strip()

    # Case 1: Specific Policy ID requested or explicitly bound
    if target_id and target_id.upper() != "UNSPECIFIED":
        policy = registry_svc.get_by_id(target_id)
        if not policy:
            diag = (
                f"Specified policy ID '{target_id}' was not found in the MedRule policy registry. "
                "Failure is caused by an incorrect lookup key or missing policy ingestion."
            )
            return None, diag, "SPECIFIED_POLICY_NOT_FOUND"

        if policy.lifecycle_status != PolicyLifecycleStatus.APPROVED_FOR_USE:
            diag = (
                f"Policy '{policy.id}' is registered in the database but currently in '{policy.lifecycle_status.value}' status. "
                "MedRule governance gate blocks clinical evaluation on unapproved guidelines."
            )
            return policy, diag, "POLICY_NOT_APPROVED"

        is_compat, status, reasons, req_pol = criteria_svc.validate_policy_compatibility(policy, note_record)
        if not is_compat:
            reasons_str = "; ".join(reasons)
            diag = f"POLICY_MISMATCH: Incompatible policy '{policy.id}' ({policy.policy_name}). {reasons_str}"
            return policy, diag, "POLICY_MISMATCH"

        return policy, None, "COMPATIBLE_RESOLVED"

    # Case 2: Policy ID was NOT specified ('UNSPECIFIED' case)
    # Check registry for an authentic, verified, approved policy matching payer, modality, and anatomy
    approved_policies = registry_svc.get_all(status=PolicyLifecycleStatus.APPROVED_FOR_USE)
    compatible_approved: List[Policy] = []

    for p in approved_policies:
        is_compat, _, _, _ = criteria_svc.validate_policy_compatibility(p, note_record)
        if is_compat:
            compatible_approved.append(p)

    if compatible_approved:
        return compatible_approved[0], None, "COMPATIBLE_RESOLVED"

    # If no compatible approved policy exists in the registry, diagnose precisely what is missing
    norm_payer = criteria_svc.normalize_payer(note_record.insurance_plan)
    norm_mod = criteria_svc.normalize_modality(note_record.procedure_requested)
    norm_anat = criteria_svc.normalize_anatomy(note_record.procedure_requested).replace("_", " ").title()

    all_policies = registry_svc.get_all()
    unapproved_matches = [
        p for p in all_policies
        if criteria_svc.normalize_payer(p.insurer) == norm_payer and p.lifecycle_status != PolicyLifecycleStatus.APPROVED_FOR_USE
    ]

    avail_approved = [f"{p.id} ({p.insurer} - {p.procedure_type})" for p in approved_policies]
    avail_str = ", ".join(avail_approved) if avail_approved else "None"

    if unapproved_matches:
        cand = unapproved_matches[0]
        diag = (
            f"Policy ID was unspecified, and candidate guideline '{cand.id}' for payer '{note_record.insurance_plan}' "
            f"is currently in '{cand.lifecycle_status.value}' status. "
            "Governance requires an APPROVED_FOR_USE policy before evaluating prior authorization."
        )
        return None, diag, "POLICY_NOT_APPROVED"

    diag = (
        f"Policy ID was unspecified and no compatible approved policy exists in the registry for this encounter. "
        f"Failure cause: Missing Policy Ingestion. "
        f"Encounter requires an authentic, approved coverage guideline for payer '{note_record.insurance_plan}' "
        f"governing '{note_record.procedure_requested}' (Modality: {norm_mod}, Anatomy: {norm_anat}). "
        f"Currently approved policies in registry: [{avail_str}]. Fail-closed governance blocks evaluation."
    )
    return None, diag, "NO_APPLICABLE_VERIFIED_POLICY"

@app.post("/api/agent/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    req: AgentChatRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    MedRule Conversational Copilot Router:
    Routes questions by intent:
    - DOCUMENT_ANALYSIS: Summarizes / extracts from uploaded document without requiring a policy.
    - WORKFLOW_QUERY: Answers review readiness and trace questions for an encounter.
    - EVALUATION_QUERY: Invokes deterministic rules engine, strictly fail-closed on policy mismatch.
    - APPEAL_DRAFT: Generates evidence-based appeal draft with placeholders if policy unverified.
    """
    # 1. Resolve Document Context (Least-privilege, request-scoped)
    requested_doc_ids: List[str] = []
    if req.document_ids:
        for d in req.document_ids:
            if d and d not in requested_doc_ids:
                requested_doc_ids.append(d)
    if req.document_id and req.document_id not in requested_doc_ids:
        requested_doc_ids.append(req.document_id)

    resolved_docs: List[ClinicalNoteRecord] = []
    for d_id in requested_doc_ids:
        doc_rec = note_extractor_service.get_note_record(d_id)
        if not doc_rec:
            raise HTTPException(status_code=404, detail=f"Document '{d_id}' not found.")
        check_case_tenant(doc_rec, current_user)
        resolved_docs.append(doc_rec)

    primary_note_record: Optional[ClinicalNoteRecord] = None
    if resolved_docs:
        primary_note_record = resolved_docs[0]
    elif req.case_id:
        c_rec = note_extractor_service.get_note_record(req.case_id)
        if c_rec:
            check_case_tenant(c_rec, current_user)
            primary_note_record = c_rec
            resolved_docs = [c_rec]

    # 2. Classify Intent
    classified_intent, confidence, rationale = AgentService.classify_intent(req.message)
    active_intent = AgentIntent(req.intent) if (req.intent and req.intent in [e.value for e in AgentIntent]) else classified_intent

    # Resolve Groq API key from server configuration
    header_key = request.headers.get("x-groq-api-key")
    resolved_key = AgentService.get_api_key(req.groq_api_key or header_key)

    # -------------------------------------------------------------
    # INTENT A: DOCUMENT ANALYSIS
    # -------------------------------------------------------------
    if active_intent == AgentIntent.DOCUMENT_ANALYSIS:
        if not resolved_docs:
            return AgentChatResponse(
                response=(
                    "### 📄 Document Analysis\n\n"
                    "No clinical document is currently selected or attached. "
                    "Please attach a clinical note PDF or select an encounter to analyze its symptoms, findings, and treatments."
                ),
                intent=active_intent.value,
                model_used="MedRule Conversational Engine",
                is_groq_powered=False,
                request_id=req.request_id,
                compatibility_status="NOT_APPLICABLE"
            )

        doc_primary = resolved_docs[0]
        # Check if Groq is available for document analysis
        if resolved_key:
            sys_prompt = AgentService.build_document_analysis_system_prompt()
            user_prompt = AgentService.build_document_analysis_user_prompt(req.message, resolved_docs)
            messages = [{"role": "system", "content": sys_prompt}]
            if req.history:
                for turn in req.history[-6:]:
                    if turn.get("role") in ["user", "assistant"] and turn.get("content"):
                        messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": user_prompt})

            answer, model_used, err = await AgentService.call_groq_api(
                messages=messages,
                api_key=resolved_key,
                model=req.model
            )
            if answer and not err:
                is_consistent, warnings, final_text = AgentService.validate_narrative_consistency(
                    narrative=answer,
                    note_record=doc_primary,
                    evaluation_report=None
                )
                citations, cite_warnings = AgentService.extract_and_validate_citations(
                    final_text,
                    doc_primary.total_pages,
                    document_id=doc_primary.document_id or doc_primary.case_id,
                    document_filename=doc_primary.original_filename
                )
                all_warnings = warnings + cite_warnings
                trace = AgentService.generate_agent_trace(
                    case_id=doc_primary.case_id,
                    note_record=doc_primary,
                    evaluation_report=None,
                    policy=None,
                    compatibility_status="COMPATIBLE",
                    llm_invoked=True,
                    llm_model=model_used,
                    narrative_passed=is_consistent,
                    narrative_notes=all_warnings,
                    intent=active_intent.value,
                    document_id=doc_primary.document_id
                )
                audit_service.log_event(
                    action="AGENT_DOCUMENT_ANALYSIS",
                    user=current_user,
                    resource=f"document:{doc_primary.document_id or doc_primary.case_id}",
                    status="SUCCESS",
                    details={"model": model_used, "is_groq": True, "trace_id": trace.trace_id}
                )
                return AgentChatResponse(
                    response=final_text,
                    intent=active_intent.value,
                    model_used=f"{model_used} (Groq)",
                    is_groq_powered=True,
                    request_id=req.request_id,
                    case_id=doc_primary.case_id,
                    document_id=doc_primary.document_id or doc_primary.case_id,
                    document_ids=[d.document_id or d.case_id for d in resolved_docs],
                    document_filename=doc_primary.original_filename,
                    valid_page_count=doc_primary.total_pages,
                    patient_name=doc_primary.patient_name,
                    procedure=doc_primary.procedure_requested,
                    evaluation=None,
                    extracted_facts={k: f.model_dump() for k, f in doc_primary.facts.items()} if doc_primary.facts else None,
                    trace=trace.model_dump(),
                    compatibility_status="NOT_APPLICABLE",
                    citations=[AgentCitation(**c) for c in citations],
                    warnings=all_warnings
                )

        # Fallback to deterministic extraction summary if Groq unavailable
        fallback_text = AgentService.generate_document_analysis_fallback(
            req.message,
            resolved_docs,
            error_reason=err if resolved_key else "CONFIG_ERROR: Groq inference service is not configured on the server."
        )
        trace = AgentService.generate_agent_trace(
            case_id=doc_primary.case_id,
            note_record=doc_primary,
            evaluation_report=None,
            policy=None,
            compatibility_status="COMPATIBLE",
            llm_invoked=False,
            intent=active_intent.value,
            document_id=doc_primary.document_id
        )
        audit_service.log_event(
            action="AGENT_DOCUMENT_ANALYSIS",
            user=current_user,
            resource=f"document:{doc_primary.document_id or doc_primary.case_id}",
            status="SUCCESS",
            details={"model": "deterministic-extractor", "is_groq": False, "trace_id": trace.trace_id}
        )
        return AgentChatResponse(
            response=fallback_text,
            intent=active_intent.value,
            model_used="MedRule Digital Text Extraction Engine",
            is_groq_powered=False,
            request_id=req.request_id,
            case_id=doc_primary.case_id,
            document_id=doc_primary.document_id or doc_primary.case_id,
            document_ids=[d.document_id or d.case_id for d in resolved_docs],
            document_filename=doc_primary.original_filename,
            valid_page_count=doc_primary.total_pages,
            patient_name=doc_primary.patient_name,
            procedure=doc_primary.procedure_requested,
            evaluation=None,
            extracted_facts={k: f.model_dump() for k, f in doc_primary.facts.items()} if doc_primary.facts else None,
            trace=trace.model_dump(),
            compatibility_status="NOT_APPLICABLE"
        )

    # -------------------------------------------------------------
    # INTENT D: APPEAL DRAFTING
    # -------------------------------------------------------------
    if active_intent == AgentIntent.APPEAL_DRAFT:
        policy, policy_diag, resolution_code = resolve_policy_for_encounter(
            primary_note_record, req.policy_id, registry_service, criteria_service
        ) if primary_note_record else (None, None, "NO_RECORD")

        evaluation = None
        comp_status = "COMPATIBLE"
        comp_reasons = []

        if policy_diag:
            comp_status = "POLICY_MISMATCH" if "POLICY_MISMATCH" in policy_diag else "NO_APPLICABLE_VERIFIED_POLICY"
            comp_reasons = [policy_diag]
        elif policy and primary_note_record:
            try:
                evaluation = criteria_service.evaluate_note_record(policy=policy, note_record=primary_note_record)
            except (PolicyMismatchError, PolicyVerificationGateError) as e:
                comp_status = "POLICY_MISMATCH"
                comp_reasons = [str(e)]

        appeal_text = AgentService.generate_appeal_draft(
            user_query=req.message,
            note_record=primary_note_record,
            evaluation_report=evaluation,
            policy=policy,
            compatibility_status=comp_status
        )
        trace = AgentService.generate_agent_trace(
            case_id=primary_note_record.case_id if primary_note_record else "CASE-UNKNOWN",
            note_record=primary_note_record,
            evaluation_report=evaluation,
            policy=policy,
            compatibility_status=comp_status,
            compatibility_reasons=comp_reasons,
            llm_invoked=False,
            intent=active_intent.value,
            document_id=primary_note_record.document_id if primary_note_record else None
        )
        audit_service.log_event(
            action="AGENT_APPEAL_DRAFT",
            user=current_user,
            resource=f"case:{primary_note_record.case_id if primary_note_record else 'unknown'}",
            status="SUCCESS",
            details={"is_groq": False, "trace_id": trace.trace_id, "comp_status": comp_status}
        )
        return AgentChatResponse(
            response=appeal_text,
            intent=active_intent.value,
            model_used="MedRule Clinical Appeal Generator",
            is_groq_powered=False,
            request_id=req.request_id,
            case_id=primary_note_record.case_id if primary_note_record else None,
            document_id=primary_note_record.document_id if primary_note_record else None,
            document_ids=[d.document_id or d.case_id for d in resolved_docs],
            document_filename=primary_note_record.original_filename if primary_note_record else None,
            valid_page_count=primary_note_record.total_pages if primary_note_record else None,
            patient_name=primary_note_record.patient_name if primary_note_record else None,
            procedure=primary_note_record.procedure_requested if primary_note_record else None,
            evaluation=evaluation.model_dump() if evaluation else None,
            extracted_facts={k: f.model_dump() for k, f in primary_note_record.facts.items()} if primary_note_record and primary_note_record.facts else None,
            trace=trace.model_dump(),
            compatibility_status=comp_status
        )

    # -------------------------------------------------------------
    # INTENT C & B: AUTHORIZATION EVALUATION & WORKFLOW QUERIES
    # -------------------------------------------------------------
    policy = None
    evaluation = None
    policy_mismatch_error = None

    if primary_note_record:
        policy, policy_diag, resolution_code = resolve_policy_for_encounter(
            primary_note_record, req.policy_id, registry_service, criteria_service
        )
        if policy_diag:
            policy_mismatch_error = policy_diag
        elif policy:
            try:
                evaluation = criteria_service.evaluate_note_record(policy=policy, note_record=primary_note_record)
            except PolicyMismatchError as e:
                policy_mismatch_error = str(e)
            except PolicyVerificationGateError as e:
                policy_mismatch_error = str(e)
            except Exception as e:
                logger.warning(f"Agent evaluation notice: {e}")

    # Fail closed on policy mismatch or missing verified policy
    if policy_mismatch_error and primary_note_record:
        mismatch_narrative = (
            f"### 🛑 POLICY INCOMPATIBILITY DETECTED (FAIL-CLOSED)\n\n"
            f"**Evaluation Blocked:** {policy_mismatch_error}\n\n"
            f"- **Requested Case:** {primary_note_record.patient_name} (Case ID: {primary_note_record.case_id})\n"
            f"- **Requested Procedure:** {primary_note_record.procedure_requested}\n"
            f"- **Payer:** {primary_note_record.insurance_plan}\n"
            f"- **Selected Policy:** {policy.policy_id if policy else 'None'} ({policy.policy_name if policy else 'None'})\n\n"
            f"**MedRule Governance Policy:**\n"
            f"- The deterministic rules engine remains the sole authority for clinical authorization outcomes.\n"
            f"- Cross-payer or cross-modality policy evaluation is strictly prohibited (e.g. evaluating an Ambetter Lumbar Spine MRI under a UnitedHealthcare Head CT policy).\n"
            f"- Please ingest and approve an authentic verified {primary_note_record.insurance_plan} policy for {primary_note_record.procedure_requested} to proceed."
        )
        trace = AgentService.generate_agent_trace(
            case_id=primary_note_record.case_id,
            note_record=primary_note_record,
            evaluation_report=None,
            policy=policy,
            compatibility_status="POLICY_MISMATCH",
            compatibility_reasons=[policy_mismatch_error],
            llm_invoked=False,
            intent=active_intent.value,
            document_id=primary_note_record.document_id
        )

        audit_service.log_event(
            action="AGENT_POLICY_MISMATCH_BLOCKED",
            user=current_user,
            resource=f"case:{primary_note_record.case_id}",
            status="BLOCKED",
            details={"policy_id": policy.policy_id if policy else None, "reason": policy_mismatch_error}
        )

        return AgentChatResponse(
            response=mismatch_narrative,
            intent=active_intent.value,
            model_used="MedRule Deterministic Rules Engine",
            is_groq_powered=False,
            request_id=req.request_id,
            case_id=primary_note_record.case_id,
            document_id=primary_note_record.document_id or primary_note_record.case_id,
            document_ids=[d.document_id or d.case_id for d in resolved_docs],
            document_filename=primary_note_record.original_filename,
            valid_page_count=primary_note_record.total_pages,
            patient_name=primary_note_record.patient_name,
            procedure=primary_note_record.procedure_requested,
            evaluation=None,
            extracted_facts={k: f.model_dump() for k, f in primary_note_record.facts.items()} if primary_note_record and primary_note_record.facts else None,
            trace=trace.model_dump(),
            compatibility_status="POLICY_MISMATCH"
        )

    # Groq-powered generation with strict evidence grounding for compatible evaluation
    if resolved_key and evaluation:
        system_prompt = AgentService.build_system_prompt()
        context_prompt = AgentService.build_user_context_prompt(
            user_query=req.message,
            note_record=primary_note_record,
            evaluation_report=evaluation
        )

        messages = [{"role": "system", "content": system_prompt}]
        if req.history:
            for turn in req.history[-6:]:
                if turn.get("role") in ["user", "assistant"] and turn.get("content"):
                    messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": context_prompt})

        answer, model_used, err = await AgentService.call_groq_api(
            messages=messages,
            api_key=resolved_key,
            model=req.model
        )

        if answer and not err:
            is_consistent, warnings, final_text = AgentService.validate_narrative_consistency(
                narrative=answer,
                note_record=primary_note_record,
                evaluation_report=evaluation
            )
            answer = final_text

            trace = AgentService.generate_agent_trace(
                case_id=primary_note_record.case_id if primary_note_record else (req.case_id or "CASE-GENERAL"),
                note_record=primary_note_record,
                evaluation_report=evaluation,
                policy=policy,
                compatibility_status="COMPATIBLE",
                llm_invoked=True,
                llm_model=model_used,
                narrative_passed=is_consistent,
                narrative_notes=warnings,
                intent=active_intent.value,
                document_id=primary_note_record.document_id if primary_note_record else None
            )

            audit_service.log_event(
                action="AGENT_CHAT_QUERY",
                user=current_user,
                resource=f"case:{primary_note_record.case_id if primary_note_record else 'general'}",
                status="SUCCESS",
                details={"model": model_used, "is_groq": True, "trace_id": trace.trace_id}
            )
            return AgentChatResponse(
                response=answer,
                intent=active_intent.value,
                model_used=f"{model_used} (Groq)",
                is_groq_powered=True,
                request_id=req.request_id,
                case_id=primary_note_record.case_id if primary_note_record else None,
                document_id=primary_note_record.document_id if primary_note_record else None,
                document_ids=[d.document_id or d.case_id for d in resolved_docs],
                document_filename=primary_note_record.original_filename if primary_note_record else None,
                valid_page_count=primary_note_record.total_pages if primary_note_record else None,
                patient_name=primary_note_record.patient_name if primary_note_record else None,
                procedure=primary_note_record.procedure_requested if primary_note_record else None,
                evaluation=evaluation.model_dump() if evaluation else None,
                extracted_facts={k: f.model_dump() for k, f in primary_note_record.facts.items()} if primary_note_record and primary_note_record.facts else None,
                trace=trace.model_dump(),
                compatibility_status="COMPATIBLE"
            )

        logger.warning(f"Groq API error encountered, using deterministic fallback: {err}")

    # Fallback to deterministic clinical engine if no key or on error
    fallback_answer = AgentService.generate_deterministic_fallback(
        user_query=req.message,
        note_record=primary_note_record,
        evaluation_report=evaluation
    )
    trace = AgentService.generate_agent_trace(
        case_id=primary_note_record.case_id if primary_note_record else (req.case_id or "CASE-GENERAL"),
        note_record=primary_note_record,
        evaluation_report=evaluation,
        policy=policy,
        compatibility_status="COMPATIBLE",
        llm_invoked=False,
        intent=active_intent.value,
        document_id=primary_note_record.document_id if primary_note_record else None
    )
    audit_service.log_event(
        action="AGENT_CHAT_QUERY",
        user=current_user,
        resource=f"case:{primary_note_record.case_id if primary_note_record else 'general'}",
        status="SUCCESS",
        details={"model": "deterministic-rules-engine", "is_groq": False, "trace_id": trace.trace_id}
    )
    return AgentChatResponse(
        response=fallback_answer,
        intent=active_intent.value,
        model_used="MedRule Deterministic Rules Engine",
        is_groq_powered=False,
        request_id=req.request_id,
        case_id=primary_note_record.case_id if primary_note_record else None,
        document_id=primary_note_record.document_id if primary_note_record else None,
        document_ids=[d.document_id or d.case_id for d in resolved_docs],
        document_filename=primary_note_record.original_filename if primary_note_record else None,
        valid_page_count=primary_note_record.total_pages if primary_note_record else None,
        patient_name=primary_note_record.patient_name if primary_note_record else None,
        procedure=primary_note_record.procedure_requested if primary_note_record else None,
        evaluation=evaluation.model_dump() if evaluation else None,
        extracted_facts={k: f.model_dump() for k, f in primary_note_record.facts.items()} if primary_note_record and primary_note_record.facts else None,
        trace=trace.model_dump(),
        compatibility_status="COMPATIBLE"
    )


