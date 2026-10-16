from enum import Enum
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field

class UserRole(str, Enum):
    REVIEWER_MD = "Reviewer MD"
    NURSE_AUDITOR = "Nurse Auditor"
    COMPLIANCE_OFFICER = "Compliance Officer"
    SYSTEM_ADMIN = "System Admin"

    @classmethod
    def from_str(cls, role_str: str) -> "UserRole":
        for member in cls:
            if member.value.lower() == role_str.lower() or member.name.lower() == role_str.lower():
                return member
        raise ValueError(f"Unknown user role: {role_str}")

class Permission(str, Enum):
    CASE_VIEW = "case:view"
    CASE_UPLOAD = "case:upload"
    FACT_OVERRIDE = "fact:override"
    FACT_FLAG = "fact:flag"
    EVALUATION_RUN = "evaluation:run"
    DECISION_EXPORT = "decision:export"
    POLICY_ADMIN = "policy:admin"
    TERMINOLOGY_ADMIN = "terminology:admin"
    AUDIT_VIEW_COMPLIANCE = "audit:view_compliance"
    SETTINGS_MANAGE = "settings:manage"

# Explicit least-privilege role-to-permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.REVIEWER_MD: {
        Permission.CASE_VIEW,
        Permission.CASE_UPLOAD,
        Permission.FACT_OVERRIDE,
        Permission.FACT_FLAG,
        Permission.EVALUATION_RUN,
        Permission.DECISION_EXPORT,
    },
    UserRole.NURSE_AUDITOR: {
        Permission.CASE_VIEW,
        Permission.CASE_UPLOAD,
        Permission.FACT_FLAG,
        Permission.EVALUATION_RUN,
        Permission.DECISION_EXPORT,
    },
    UserRole.COMPLIANCE_OFFICER: {
        Permission.CASE_VIEW,
        Permission.DECISION_EXPORT,
        Permission.AUDIT_VIEW_COMPLIANCE,
    },
    UserRole.SYSTEM_ADMIN: {
        Permission.CASE_VIEW,
        Permission.POLICY_ADMIN,
        Permission.TERMINOLOGY_ADMIN,
        Permission.AUDIT_VIEW_COMPLIANCE,
        Permission.SETTINGS_MANAGE,
    },
}

class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    organization_id: str = "org_riverside"
    permissions: Set[Permission] = Field(default_factory=set)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions or permission in ROLE_PERMISSIONS.get(self.role, set())

    def can_access_tenant(self, target_org_id: Optional[str]) -> bool:
        """Enforces tenant isolation. Admins and Compliance Officers can view, clinicians bound to org."""
        if not target_org_id:
            return True
        if self.role in [UserRole.SYSTEM_ADMIN, UserRole.COMPLIANCE_OFFICER] or self.organization_id == "*":
            return True
        return self.organization_id.lower() == target_org_id.lower()

class TokenPayload(BaseModel):
    sub: str
    iss: str
    aud: str
    exp: int
    iat: int
    role: str
    org_id: str
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    name: Optional[str] = None

class AuditEvent(BaseModel):
    event_id: str
    timestamp: str
    action: str
    user_id: str
    username: str
    role: str
    organization_id: str
    resource: Optional[str] = None
    status: str = "SUCCESS"  # "SUCCESS", "DENIED", "FAILED"
    ip_address: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    role: str
    organization_id: str
    permissions: List[str]

class CSRFTokenResponse(BaseModel):
    csrf_token: str
