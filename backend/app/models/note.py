from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator

class ClinicalFactStatus(str, Enum):
    EXPLICIT = "EXPLICIT"
    UNCLEAR = "UNCLEAR"
    CONFLICTING = "CONFLICTING"
    ABSENT = "ABSENT"

class ReviewerFactOverride(BaseModel):
    is_overridden: bool = True
    overridden_by: str
    overridden_at: str
    original_value: Optional[Any] = None
    corrected_value: Any
    original_status: ClinicalFactStatus
    corrected_status: ClinicalFactStatus
    reason: str

class ExtractedFact(BaseModel):
    fact_key: str
    label: str
    value: Optional[Any] = None
    status: ClinicalFactStatus = ClinicalFactStatus.ABSENT
    excerpt: Optional[str] = None
    source_page: Optional[int] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_flagged_for_review: bool = False
    flag_reason: Optional[str] = None
    reviewer_override: Optional[ReviewerFactOverride] = None

class FactCorrectionRequest(BaseModel):
    fact_key: str
    corrected_value: Any
    corrected_status: ClinicalFactStatus
    reviewer_name: str
    reason: str

class FactFlagRequest(BaseModel):
    fact_key: str
    reviewer_name: str
    reason: str

class ClinicalNoteRecord(BaseModel):
    case_id: str
    patient_name: str
    patient_age: Optional[int] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    facility: Optional[str] = None
    date_of_visit: Optional[str] = None
    procedure_requested: str
    procedure_type: Optional[str] = None
    insurance_plan: str = "United Healthcare"
    policy_id: str = "P-UHC-CT-2026"
    policy_version: Optional[str] = "2026.1"
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    clinical_findings: List[str] = Field(default_factory=list)
    impression: Optional[str] = None
    physician_recommendation: Optional[str] = None
    original_filename: str = "clinical_note.pdf"
    storage_path: Optional[str] = None
    sha256_checksum: str = ""
    total_pages: int = 1
    scanned_pages_count: int = 0
    overall_quality: str = "HIGH"
    ocr_engine_status: str = "OCR_UNAVAILABLE_FALLBACK_TO_MANUAL_REVIEW"
    facts: Dict[str, ExtractedFact] = Field(default_factory=dict)
    extracted_facts: Optional[Dict[str, Any]] = None
    raw_pages_text: List[Dict[str, Any]] = Field(default_factory=list)
    is_synthetic: bool = True
    governance_warning: str = "DEVELOPMENT/DEMO MODE ONLY: Synthetic Patient Record - Production Clinical Verification Gate Remains Active"
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @model_validator(mode="before")
    @classmethod
    def populate_facts_and_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If facts is missing but extracted_facts is present, convert extracted_facts to facts
            if not data.get("facts") and data.get("extracted_facts"):
                facts_dict = {}
                for k, v in data["extracted_facts"].items():
                    if isinstance(v, dict):
                        facts_dict[k] = {
                            "fact_key": k,
                            "label": k.replace("_", " ").title(),
                            "value": v.get("value"),
                            "status": "EXPLICIT" if v.get("value") is not None else "ABSENT",
                            "excerpt": v.get("excerpt"),
                            "source_page": v.get("source_page"),
                            "confidence": v.get("confidence", 0.95),
                        }
                    else:
                        facts_dict[k] = {
                            "fact_key": k,
                            "label": k.replace("_", " ").title(),
                            "value": v,
                            "status": "EXPLICIT" if v is not None else "ABSENT",
                            "excerpt": str(v),
                            "source_page": 1,
                            "confidence": 0.95,
                        }
                data["facts"] = facts_dict

            # Also ensure extracted_facts matches facts for backward compatibility
            if data.get("facts") and not data.get("extracted_facts"):
                ext_dict = {}
                for k, v in data["facts"].items():
                    if isinstance(v, dict):
                        ext_dict[k] = {
                            "value": v.get("value"),
                            "excerpt": v.get("excerpt"),
                            "source_page": v.get("source_page"),
                            "confidence": v.get("confidence", 1.0)
                        }
                    elif hasattr(v, "value"):
                        ext_dict[k] = {
                            "value": v.value,
                            "excerpt": v.excerpt,
                            "source_page": v.source_page,
                            "confidence": v.confidence
                        }
                data["extracted_facts"] = ext_dict

            if not data.get("created_at"):
                data["created_at"] = "2026-10-15T00:00:00Z"
            if not data.get("updated_at"):
                data["updated_at"] = data["created_at"]
        return data
