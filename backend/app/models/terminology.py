"""
MedRule Phase 6: Terminology Models
Strictly separates terminology definitions from policy coverage criteria and rulesets.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TerminologySourceStatus(str, Enum):
    """Verification status of an external or rulebook terminology source."""
    VERIFIED = "VERIFIED"
    RESTRICTED_ACCESS = "RESTRICTED_ACCESS"
    SCOPE_RESTRICTED = "SCOPE_RESTRICTED"
    PENDING_REGULATORY_VERIFICATION = "PENDING_REGULATORY_VERIFICATION"


class TerminologyResolutionStatus(str, Enum):
    """Resolution outcome of a terminology lookup request."""
    RULEBOOK_DEFINED = "RULEBOOK_DEFINED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTING = "CONFLICTING"
    FAILED = "FAILED"


class ApprovedSource(BaseModel):
    """
    Registry record for an explicitly approved terminology source.
    Enforces allowlist verification before external queries can be enabled.
    """
    id: str
    name: str
    official_domain: str
    authority: str
    permitted_scope: str
    verification_status: TerminologySourceStatus
    access_restrictions: str
    official_url: str
    is_active: bool = True
    notes: Optional[str] = None


class TerminologyDefinition(BaseModel):
    """
    Authoritative terminology definition record.
    Strictly isolated from policy coverage rules and clinical evaluation logic.
    """
    term: str
    definition: str
    source_id: str
    source_name: str
    source_domain: str
    official_url: str
    resolution_status: TerminologyResolutionStatus
    retrieval_timestamp: str
    lookup_reason: str
    policy_citation: Optional[str] = None
    is_rulebook_first: bool = False
    provenance_audit_id: str
    disclaimer: str = (
        "Terminology definition is for conceptual reference only and does not create, "
        "modify, remove, or override policy coverage criteria or authorization logic."
    )


class TerminologyLookupRequest(BaseModel):
    """Request payload for terminology lookup."""
    term: str = Field(..., min_length=2, max_length=150, description="The clinical or insurance term to clarify")
    policy_id: Optional[str] = Field(None, description="Optional selected policy ID for rulebook-first resolution")
    lookup_reason: Optional[str] = Field(
        "Clinical term clarification during prior authorization review",
        description="Reason the lookup was necessary for audit provenance"
    )


class TerminologyLookupResponse(BaseModel):
    """Authoritative terminology lookup result with safe failure and provenance."""
    term: str
    status: TerminologyResolutionStatus
    definition_record: Optional[TerminologyDefinition] = None
    resolution_path: List[str] = Field(default_factory=list)
    requires_human_review: bool = False
    review_reason: Optional[str] = None
    provenance_audit_id: Optional[str] = None
    governance_warning: str = (
        "DEVELOPMENT/DEMO MODE: Terminology definitions are strictly isolated from policy evaluation logic."
    )
