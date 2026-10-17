import pytest
from app.main import app
from app.core.deps import get_current_user
from app.models.auth import AuthenticatedUser, UserRole, Permission, ROLE_PERMISSIONS

@pytest.fixture(autouse=True)
def default_test_auth_override(request):
    """
    Ensures backwards compatibility for legacy tests (Phases 0–7) by providing
    a default authorized reviewer identity.
    For Phase 8 security tests, this override is bypassed so real authentication
    and authorization checks are exercised.
    """
    # Do NOT apply default auth override to Phase 8 security test files or conversational routing tests
    if "test_phase8_auth" in request.node.nodeid or "test_conversational_routing" in request.node.nodeid:
        yield
        return

    # Authorized test reviewer with full clinical review permissions
    test_user = AuthenticatedUser(
        user_id="usr_test_reviewer_001",
        username="reviewer_md",
        email="reviewer@medauth.org",
        full_name="Dr. Shrinidhi Bijapur, MD",
        role=UserRole.REVIEWER_MD,
        organization_id="*",
        permissions=set(ROLE_PERMISSIONS[UserRole.REVIEWER_MD]).union({
            Permission.POLICY_ADMIN,
            Permission.TERMINOLOGY_ADMIN,
            Permission.AUDIT_VIEW_COMPLIANCE,
            Permission.SETTINGS_MANAGE
        })
    )

    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
