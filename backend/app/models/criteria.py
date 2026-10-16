from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CriterionType(str, Enum):
    CRITERION = "CRITERION"
    LOGIC_GROUP = "LOGIC_GROUP"
    NUMERIC_THRESHOLD = "NUMERIC_THRESHOLD"
    DURATION = "DURATION"
    EXCLUSION = "EXCLUSION"
    NOTE_EXPLANATORY = "NOTE_EXPLANATORY"

class LogicOperator(str, Enum):
    AND = "AND"
    OR = "OR"
    MINIMUM_COUNT = "MINIMUM_COUNT"
    CONDITIONAL = "CONDITIONAL"

class ComparisonOperator(str, Enum):
    GTE = ">="
    LTE = "<="
    GT = ">"
    LT = "<"
    EQ = "=="
    BETWEEN = "BETWEEN"

class VerificationStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    APPROVED_VERIFIED = "APPROVED_VERIFIED"
    REJECTED = "REJECTED"

class ReviewerSignoff(BaseModel):
    primary_reviewer: str
    primary_reviewer_role: str
    secondary_reviewer: str
    secondary_reviewer_role: str
    signed_off_at: str
    policy_checksum: str
    source_criteria_count: int
    encoded_criteria_count: int
    side_by_side_verified: bool = True
    plain_english_verified: bool = True
    notes: Optional[str] = None

class CriterionRule(BaseModel):
    id: str
    policy_id: str
    policy_version: str
    section_number: str
    section_name: str
    source_page: int
    source_text: str  # Unaltered source text from policy
    plain_english_description: str
    criterion_type: CriterionType = CriterionType.CRITERION
    is_mandatory: bool = True
    fact_key: Optional[str] = None
    operator: Optional[LogicOperator] = None
    min_count: Optional[int] = None
    comparison_op: Optional[str] = None
    threshold_value: Optional[float] = None
    threshold_max: Optional[float] = None
    threshold_unit: Optional[str] = None
    conditional_prerequisite: Optional[str] = None
    is_exclusion: bool = False
    children: List["CriterionRule"] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.DRAFT
    reviewer_signoff: Optional[ReviewerSignoff] = None

if hasattr(CriterionRule, "model_rebuild"):
    CriterionRule.model_rebuild()
else:
    CriterionRule.update_forward_refs()

class PolicyRuleset(BaseModel):
    policy_id: str
    policy_name: str
    policy_version: str
    policy_checksum: str
    procedure_type: str
    rules: List[CriterionRule] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.DRAFT
    signoff: Optional[ReviewerSignoff] = None
    last_updated: Optional[str] = None

class VerificationGateRequest(BaseModel):
    primary_reviewer: str
    primary_reviewer_role: str
    secondary_reviewer: str
    secondary_reviewer_role: str
    source_criteria_count: int
    side_by_side_verified: bool
    plain_english_verified: bool
    notes: Optional[str] = None

class CriteriaEvaluationRequest(BaseModel):
    policy_id: str
    version: Optional[str] = None
    case_id: str = "CASE-TEMP"
    patient_name: str = "Patient"
    patient_facts: Optional[Dict[str, Any]] = None

