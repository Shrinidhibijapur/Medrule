from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TraceCompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    NO_APPLICABLE_VERIFIED_POLICY = "NO_APPLICABLE_VERIFIED_POLICY"

class TraceConcordanceStatus(str, Enum):
    CONCORDANT = "CONCORDANT"
    SERVICE_DOCUMENT_MISMATCH = "SERVICE_DOCUMENT_MISMATCH"

class ClaimEvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICTING = "CONFLICTING"

class VerifiedClaim(BaseModel):
    claim_text: str
    evidence_excerpt: Optional[str] = None
    source_document_id: Optional[str] = None
    source_document_sha256: Optional[str] = None
    source_page: Optional[int] = None
    evidence_status: ClaimEvidenceStatus = ClaimEvidenceStatus.NOT_FOUND
    is_verified: bool = False
    verification_notes: List[str] = Field(default_factory=list)

class TraceFactEntry(BaseModel):
    fact_key: str
    label: str
    status: str
    value: Optional[Any] = None
    source_document_id: Optional[str] = None
    source_page: Optional[int] = None
    source_span: Optional[str] = None
    confidence: float = 1.0
    is_overridden: bool = False
    override_details: Optional[Dict[str, Any]] = None

class TraceCriterionEntry(BaseModel):
    rule_id: str
    criterion_name: str
    section: str
    requirement: str
    deterministic_status: str
    ui_label: str
    policy_citation: str
    evidence_status: str
    evidence_page: Optional[int] = None
    evidence_source_passage: Optional[str] = None
    explanation: str
    is_overridden: bool = False
    override_details: Optional[Dict[str, Any]] = None

class AgentTrace(BaseModel):
    trace_id: str
    case_id: str
    patient_name: str
    date_of_service: Optional[str] = None
    document_id: Optional[str] = None
    document_filename: str
    document_sha256: str
    valid_page_count: int
    extraction_method: str = "Digital Text Extraction (pypdf)"
    extraction_status: str = "COMPLETED"
    intent: str = "EVALUATION_QUERY"
    
    # Request & Modality Identification
    requested_service: str
    procedure_modality: str
    anatomical_region: str
    contrast_status: Optional[str] = None
    payer: str
    
    # Policy Resolution & Compatibility
    selected_policy_id: Optional[str] = None
    policy_name: Optional[str] = None
    policy_version: Optional[str] = None
    policy_hash: Optional[str] = None
    policy_lifecycle_status: Optional[str] = None
    compatibility_status: TraceCompatibilityStatus = TraceCompatibilityStatus.COMPATIBLE
    compatibility_reasons: List[str] = Field(default_factory=list)
    required_policy_description: Optional[str] = None
    
    # Service-Document Concordance
    service_document_concordance: TraceConcordanceStatus = TraceConcordanceStatus.CONCORDANT
    concordance_details: List[str] = Field(default_factory=list)
    
    # Extracted Evidence & Rule Results
    extracted_facts: List[TraceFactEntry] = Field(default_factory=list)
    criteria_results: List[TraceCriterionEntry] = Field(default_factory=list)
    
    # Deterministic Decision & Blockers
    deterministic_verdict: Optional[str] = None
    decision_outcome: Optional[str] = None
    governance_blockers: List[str] = Field(default_factory=list)
    
    # Narrative & LLM Verification
    llm_invoked: bool = False
    llm_model: Optional[str] = None
    llm_correlation_id: Optional[str] = None
    narrative_validation_status: str = "NOT_APPLICABLE"
    narrative_validation_passed: Optional[bool] = None
    narrative_validation_notes: List[str] = Field(default_factory=list)
    verified_claims: List[VerifiedClaim] = Field(default_factory=list)
    
    # Human Review & Audit Trail
    human_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str = ""
