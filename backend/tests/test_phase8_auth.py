"""
Phase 8 Automated Test Suite: Genuine Authentication, Authorization & Access Control
Tests cover:
1. Unauthenticated rejection (401 Unauthorized) across all protected APIs
2. Cryptographic token validation: signature, issuer, audience, expiration rejection (401)
3. Role-Based Access Control (RBAC) enforcing least privilege across 4 roles:
   - Reviewer MD
   - Nurse Auditor
   - Compliance Officer
   - System Admin
4. Tenant isolation and IDOR protection (403 Forbidden when accessing other org's cases)
5. CSRF protection on cookie-authenticated state-changing requests
6. Safe fail-closed behavior when IdP is unconfigured in production
7. Centralized audit trail binding to authenticated user without credential or PII leaks
"""

import pytest
from datetime import datetime, timezone, timedelta
import jwt
from fastapi.testclient import TestClient
from app.main import app, registry_service, note_extractor_service
from app.core.config import settings
from app.core.security import create_access_token, generate_csrf_token
from app.models.auth import UserRole, Permission, ROLE_PERMISSIONS, AuthenticatedUser
from app.models.note import ClinicalNoteRecord, ExtractedFact, ClinicalFactStatus

client = TestClient(app)

# Helper token generator for test identities
def get_token_for_role(
    role: UserRole,
    user_id: str = "usr_test_001",
    username: str = "test_user",
    org_id: str = "org_riverside"
) -> str:
    user = AuthenticatedUser(
        user_id=user_id,
        username=username,
        email=f"{username}@medauth.org",
        full_name=f"Test {role.value}",
        role=role,
        organization_id=org_id,
        permissions=set(ROLE_PERMISSIONS[role])
    )
    return create_access_token(user=user, expires_delta=timedelta(hours=1))

@pytest.fixture(scope="module", autouse=True)
def setup_phase8_test_records():
    """Sets up synthetic isolated test cases for tenant testing."""
    # Organization A Case
    case_org_a = ClinicalNoteRecord(
        case_id="CASE-ORG-A-001",
        patient_name="Riverside Patient A",
        procedure_requested="CT Scan of Head without Contrast",
        policy_id="P-UHC-CT-2026",
        policy_version="2026.1",
        organization_id="org_riverside",
        facts={
            "acute_neuro_symptoms": ExtractedFact(
                fact_key="acute_neuro_symptoms",
                label="Acute Neurological Symptoms",
                value=False,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="Patient denies acute symptoms.",
                source_page=1,
                confidence=0.95
            )
        },
        audit_trail=[]
    )
    note_extractor_service.save_note_record(case_org_a)

    # Organization B Case (Different Tenant)
    case_org_b = ClinicalNoteRecord(
        case_id="CASE-ORG-B-002",
        patient_name="Memorial Patient B",
        procedure_requested="CT Scan of Head without Contrast",
        policy_id="P-UHC-CT-2026",
        policy_version="2026.1",
        organization_id="org_memorial",
        facts={
            "acute_neuro_symptoms": ExtractedFact(
                fact_key="acute_neuro_symptoms",
                label="Acute Neurological Symptoms",
                value=False,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="No acute deficit noted.",
                source_page=1,
                confidence=0.90
            )
        },
        audit_trail=[]
    )
    note_extractor_service.save_note_record(case_org_b)
    yield case_org_a, case_org_b
    for cid in ["CASE-ORG-A-001", "CASE-ORG-B-002"]:
        p = note_extractor_service.notes_data_dir / f"{cid}.json"
        if p.exists():
            p.unlink()


# ==============================================================================
# 1. Unauthenticated Rejection Tests (401 Unauthorized)
# ==============================================================================

def test_unauthenticated_requests_are_rejected():
    """Unauthenticated requests to protected endpoints must return 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/policies"),
        ("GET", "/api/cases"),
        ("GET", "/api/cases/CASE-ORG-A-001"),
        ("GET", "/api/dashboard/stats"),
        ("GET", "/api/notes/ocr-status"),
        ("GET", "/api/terminology/sources"),
        ("GET", "/api/audit/logs"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path)
        assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"
        detail = res.json().get("detail", "").lower()
        assert "authentication" in detail or "token" in detail or "not authenticated" in detail


# ==============================================================================
# 2. Token Validation & Cryptographic Integrity Tests
# ==============================================================================

def test_invalid_signature_token_is_rejected():
    """Tokens with an invalid cryptographic signature must return 401."""
    tampered_token = jwt.encode(
        {"sub": "usr_fake", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "WRONG_SECRET_KEY_NOT_MEDRULE_LONGER_THAN_32_BYTES",
        algorithm="HS256"
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401
    assert "signature" in res.json()["detail"].lower()


def test_expired_token_is_rejected():
    """Expired tokens must return 401 Unauthorized with token expired message."""
    user = AuthenticatedUser(
        user_id="usr_expired",
        username="expired_user",
        email="expired@medauth.org",
        full_name="Expired User",
        role=UserRole.REVIEWER_MD,
        organization_id="org_riverside",
        permissions=set(ROLE_PERMISSIONS[UserRole.REVIEWER_MD])
    )
    expired_token = create_access_token(
        user=user,
        expires_delta=timedelta(minutes=-30)  # expired 30 mins ago
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_invalid_issuer_or_audience_token_is_rejected():
    """Tokens with incorrect issuer or audience claim must be rejected."""
    wrong_issuer_token = jwt.encode(
        {
            "sub": "usr_fake",
            "iss": "https://malicious-idp.example.com/auth",
            "aud": settings.OIDC_AUDIENCE,
            "role": "Reviewer MD",
            "org_id": "org_riverside",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {wrong_issuer_token}"})
    assert res.status_code == 401
    detail = res.json()["detail"].lower()
    assert "claims" in detail or "issuer" in detail or "invalid" in detail


# ==============================================================================
# 3. Role-Based Access Control (RBAC) Least Privilege Tests
# ==============================================================================

def test_reviewer_md_authorized_actions():
    """Reviewer MD can view cases, override facts, run evaluations, and export decisions."""
    token = get_token_for_role(UserRole.REVIEWER_MD, username="dr_smith")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. View cases (Allowed)
    res = client.get("/api/cases", headers=headers)
    assert res.status_code == 200

    # 2. Fact override (Allowed)
    override_res = client.patch(
        "/api/notes/CASE-ORG-A-001/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "Clinician physical exam verified."
        },
        headers=headers
    )
    assert override_res.status_code == 200

    # 3. Policy administration (Forbidden for Reviewer MD)
    policy_res = client.patch(
        "/api/policies/P-UHC-CT-2026/status",
        json={"status": "APPROVED_FOR_USE"},
        headers=headers
    )
    assert policy_res.status_code == 403
    assert "policy:admin" in policy_res.json()["detail"]


def test_nurse_auditor_least_privilege_enforcement():
    """Nurse Auditor can view and flag facts, but CANNOT execute fact overrides (403 Forbidden)."""
    token = get_token_for_role(UserRole.NURSE_AUDITOR, username="nurse_auditor_1")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. View case (Allowed)
    res = client.get("/api/cases/CASE-ORG-A-001", headers=headers)
    assert res.status_code == 200

    # 2. Flag fact for review (Allowed)
    flag_res = client.post(
        "/api/notes/CASE-ORG-A-001/flag",
        json={
            "fact_key": "acute_neuro_symptoms",
            "reason": "Secondary clinical review requested for duration."
        },
        headers=headers
    )
    assert flag_res.status_code == 200

    # 3. Attempt Fact Override (Forbidden - Nurses cannot override clinical facts)
    override_res = client.patch(
        "/api/notes/CASE-ORG-A-001/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "Nurse attempt"
        },
        headers=headers
    )
    assert override_res.status_code == 403
    assert "fact:override" in override_res.json()["detail"]


def test_compliance_officer_least_privilege_enforcement():
    """Compliance Officer can view audit logs and case exports, but CANNOT modify facts or run evaluations."""
    token = get_token_for_role(UserRole.COMPLIANCE_OFFICER, username="compliance_officer_1")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. View audit logs (Allowed)
    audit_res = client.get("/api/audit/logs", headers=headers)
    assert audit_res.status_code == 200

    # 2. Attempt Fact Override (Forbidden)
    override_res = client.patch(
        "/api/notes/CASE-ORG-A-001/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "Compliance officer attempt"
        },
        headers=headers
    )
    assert override_res.status_code == 403

    # 3. Attempt Note Upload (Forbidden)
    upload_res = client.post(
        "/api/notes/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 empty", "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == 403


def test_system_admin_least_privilege_enforcement():
    """System Admin can view audit logs and manage policies, but CANNOT override clinical facts (no practicing medicine)."""
    token = get_token_for_role(UserRole.SYSTEM_ADMIN, username="admin_sys")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. View audit logs (Allowed)
    audit_res = client.get("/api/audit/logs", headers=headers)
    assert audit_res.status_code == 200

    # 2. Attempt Fact Override (Forbidden - Admins cannot alter patient clinical evidence)
    override_res = client.patch(
        "/api/notes/CASE-ORG-A-001/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "Admin modification attempt"
        },
        headers=headers
    )
    assert override_res.status_code == 403
    assert "fact:override" in override_res.json()["detail"]


# ==============================================================================
# 4. Tenant Isolation & IDOR Protection Tests
# ==============================================================================

def test_tenant_isolation_prevents_cross_organization_case_access(setup_phase8_test_records):
    """
    A user from Organization Riverside (org_riverside) must NOT access records
    belonging to Organization Memorial (org_memorial) by changing the case ID in the URL.
    """
    riverside_token = get_token_for_role(UserRole.REVIEWER_MD, username="dr_riverside", org_id="org_riverside")
    headers = {"Authorization": f"Bearer {riverside_token}"}

    # Access own case (Allowed)
    own_res = client.get("/api/cases/CASE-ORG-A-001", headers=headers)
    assert own_res.status_code == 200

    # Attempt cross-tenant IDOR access to Memorial case (Forbidden 403)
    idor_res = client.get("/api/cases/CASE-ORG-B-002", headers=headers)
    assert idor_res.status_code == 403
    assert "Tenant Access Denied" in idor_res.json()["detail"]

    # Attempt cross-tenant export (Forbidden 403)
    idor_export = client.get("/api/cases/CASE-ORG-B-002/export", headers=headers)
    assert idor_export.status_code == 403

    # Attempt cross-tenant fact override (Forbidden 403)
    idor_override = client.patch(
        "/api/notes/CASE-ORG-B-002/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "IDOR attempt"
        },
        headers=headers
    )
    assert idor_override.status_code == 403


def test_case_list_and_dashboard_are_tenant_filtered(setup_phase8_test_records):
    """Cases list and dashboard statistics must only return cases belonging to the user's organization."""
    riverside_token = get_token_for_role(UserRole.REVIEWER_MD, username="dr_riverside", org_id="org_riverside")
    headers = {"Authorization": f"Bearer {riverside_token}"}

    cases_res = client.get("/api/cases", headers=headers)
    assert cases_res.status_code == 200
    cases = cases_res.json()

    # Verify no Memorial cases leaked into Riverside list
    case_ids = [c["case_id"] for c in cases]
    assert "CASE-ORG-A-001" in case_ids
    assert "CASE-ORG-B-002" not in case_ids


# ==============================================================================
# 5. CSRF Protection & Session Cookie Tests
# ==============================================================================

def test_cookie_authenticated_state_changing_request_requires_csrf():
    """
    Cookie-authenticated state-changing requests (POST/PATCH) without
    a matching X-CSRF-Token must be rejected with 403 Forbidden.
    """
    user_token = get_token_for_role(UserRole.REVIEWER_MD, username="dr_cookie_user")
    cookies = {settings.SESSION_COOKIE_NAME: user_token}

    # 1. Attempt PATCH without CSRF header (Rejected 403)
    res_no_csrf = client.patch(
        "/api/notes/CASE-ORG-A-001/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "CSRF test missing token"
        },
        cookies=cookies
    )
    assert res_no_csrf.status_code == 403
    assert "CSRF" in res_no_csrf.json()["detail"]

    # 2. Obtain valid CSRF token from /api/auth/csrf using session cookie
    csrf_res = client.get("/api/auth/csrf", cookies=cookies)
    assert csrf_res.status_code == 200
    csrf_token = csrf_res.json()["csrf_token"]

    # 3. Supply valid CSRF header and cookie (Allowed 200)
    res_with_csrf = client.patch(
        "/api/notes/CASE-ORG-A-001/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reason": "CSRF test valid token"
        },
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token}
    )
    assert res_with_csrf.status_code == 200


def test_logout_clears_session_cookie():
    """Logout endpoint must clear session cookie and return success message."""
    user_token = get_token_for_role(UserRole.REVIEWER_MD)
    res = client.post(
        "/api/auth/logout",
        cookies={settings.SESSION_COOKIE_NAME: user_token}
    )
    assert res.status_code == 200
    msg = res.json()["message"].lower()
    assert "terminated" in msg or "logged out" in msg


# ==============================================================================
# 6. Safe Fail-Closed Configuration Tests
# ==============================================================================

def test_fail_closed_when_dev_login_attempted_in_production(monkeypatch):
    """
    In production mode (MEDRULE_ENV=production), development mock login
    must fail closed with 403 Forbidden.
    """
    monkeypatch.setattr(settings, "MEDRULE_ENV", "production")
    res = client.post("/api/auth/dev-login", json={"role": "Reviewer MD"})
    assert res.status_code == 403
    assert "prohibited in production" in res.json()["detail"].lower()


def test_fail_closed_when_idp_unconfigured_in_production(monkeypatch):
    """
    In production mode with an unconfigured/localhost IdP,
    /api/auth/login-url must fail closed with 503 Service Unavailable.
    """
    monkeypatch.setattr(settings, "MEDRULE_ENV", "production")
    monkeypatch.setattr(settings, "OIDC_ISSUER_URL", "http://localhost:8080/realms/medrule")
    res = client.get("/api/auth/login-url")
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


# ==============================================================================
# 7. Audit Trail Attribution & Sensitive Data Sanitization Tests
# ==============================================================================

def test_audit_logs_bind_identity_and_sanitize_sensitive_content():
    """
    Audit events must record user ID, username, role, and organization,
    and MUST NEVER log passwords, session tokens, or raw clinical notes.
    """
    admin_token = get_token_for_role(UserRole.SYSTEM_ADMIN, username="admin_audit_tester")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.get("/api/audit/logs?limit=50", headers=headers)
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0

    for event in logs:
        # Verify authenticated identity attribution
        assert "user_id" in event
        assert "role" in event
        assert "timestamp" in event
        assert "action" in event

        # Verify sensitive information is never leaked
        serialized = str(event).lower()
        assert "password" not in serialized
        assert "jwt_secret" not in serialized
        assert "bearerey" not in serialized
