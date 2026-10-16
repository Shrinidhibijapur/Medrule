from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PolicyLifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED_FOR_USE = "APPROVED_FOR_USE"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"

class Criterion(BaseModel):
    id: str
    section: str
    name: str
    requirement: str
    mandatory: bool = True
    conditional_on: Optional[str] = None
    fact_key: str
    min_value: Optional[float] = None

class PolicySection(BaseModel):
    id: str
    section_number: str
    heading: str
    page_number: int
    content: str
    character_count: int
    table_detected: bool = False

class PageExtractionReport(BaseModel):
    page_number: int
    character_count: int
    has_images: bool = False
    is_scanned_flag: bool = False
    quality_score: float = 1.0  # 0.0 to 1.0
    warnings: List[str] = Field(default_factory=list)

class ExtractionQualityReport(BaseModel):
    total_pages: int
    scanned_pages_count: int = 0
    low_confidence_pages: List[int] = Field(default_factory=list)
    overall_quality: str = "HIGH"  # HIGH, MEDIUM, LOW_NEEDS_OCR
    notes: List[str] = Field(default_factory=list)

class Policy(BaseModel):
    id: str
    policy_id: Optional[str] = None  # Base canonical ID e.g. "POL-UHC-CT"
    insurer: str
    policy_name: str
    plan: Optional[str] = "All Standard Commercial & Medicare Advantage Plans"
    version: str
    procedure_type: str
    procedure_full_name: str
    cpt_codes: List[str] = Field(default_factory=list)
    effective_date: str
    expiry_date: Optional[str] = None
    upload_date: Optional[str] = None
    sha256_checksum: Optional[str] = None
    original_filename: Optional[str] = None
    storage_path: Optional[str] = None
    total_pages: int = 0
    lifecycle_status: PolicyLifecycleStatus = PolicyLifecycleStatus.NEEDS_REVIEW
    criteria: List[Criterion] = Field(default_factory=list)
    ruleset: Optional[Any] = None
    sections: List[PolicySection] = Field(default_factory=list)
    extraction_report: Optional[ExtractionQualityReport] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class PolicySearchResult(BaseModel):
    policy_id: str
    policy_name: str
    version: str
    insurer: str
    section_id: str
    section_number: str
    heading: str
    page_number: int
    matched_snippet: str
    lifecycle_status: PolicyLifecycleStatus
