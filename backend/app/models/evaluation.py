from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CriterionStatus(str, Enum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    NOT_DOCUMENTED = "NOT_DOCUMENTED"
    UNCLEAR_CONFLICTING = "UNCLEAR_CONFLICTING"
    POLICY_AMBIGUITY = "POLICY_AMBIGUITY"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class Verdict(str, Enum):
    APPROVED = "APPROVED"
    NOT_APPROVED = "NOT_APPROVED"
    CANNOT_BE_DETERMINED = "CANNOT_BE_DETERMINED"

class DecisionOutcome(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    ADDITIONAL_DOCUMENTATION_REQUIRED = "ADDITIONAL_DOCUMENTATION_REQUIRED"
    CANNOT_BE_DETERMINED = "CANNOT_BE_DETERMINED"

class CriterionEvaluationResult(BaseModel):
    rule_id: str
    criterion_name: str
    section: str
    requirement: str
    evidence_excerpt: str
    source_page: Optional[int] = None
    status: CriterionStatus
    ui_symbol: str  # "✅" or "❌" or "–"
    ui_label: str   # "Satisfied", "Not met", "Not documented", etc.
    comment: str
    policy_citation: Optional[str] = None
    logic_group: Optional[str] = None
    plain_english_rationale: Optional[str] = None
    is_exclusion: bool = False
    fact_key: Optional[str] = None
    fact_confidence: Optional[float] = None
    reviewer_overridden: bool = False
    reviewer_override_by: Optional[str] = None
    reviewer_override_reason: Optional[str] = None

class EvaluationReport(BaseModel):
    case_id: str
    patient_name: str
    procedure: str
    insurer: str
    policy_id: str
    policy_version: str
    evaluation_date: str
    criteria_results: List[CriterionEvaluationResult]
    key_reasoning: List[str]
    verdict: Verdict
    verdict_sentence: str
    requires_human_review: bool
    review_reasons: List[str] = Field(default_factory=list)
    decision_outcome: Optional[DecisionOutcome] = None
    policy_checksum: Optional[str] = None
    verification_gate_verified: bool = True
    is_synthetic_demo: bool = True
    governance_notice: str = "DEVELOPMENT/DEMO MODE ONLY: Synthetic Clinical Records. Real patient evaluation remains BLOCKED until authentic policy and clinical sign-offs are completed."
