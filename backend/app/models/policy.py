from typing import List, Optional
from pydantic import BaseModel, Field

class Criterion(BaseModel):
    id: str
    section: str
    name: str
    requirement: str
    mandatory: bool = True
    conditional_on: Optional[str] = None
    fact_key: str
    min_value: Optional[float] = None

class Policy(BaseModel):
    id: str
    insurer: str
    policy_name: str
    version: str
    procedure_type: str
    procedure_full_name: str
    cpt_codes: List[str] = Field(default_factory=list)
    effective_date: str
    lifecycle_status: str = "APPROVED_FOR_USE"
    criteria: List[Criterion] = Field(default_factory=list)
