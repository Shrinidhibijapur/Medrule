import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    generate_pkce_pair,
    verify_pkce,
    decode_and_validate_token
)
from app.core.deps import get_current_user
from app.models.auth import (
    AuthenticatedUser,
    UserRole,
    UserProfileResponse,
    CSRFTokenResponse,
    ROLE_PERMISSIONS
)
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/auth", tags=["Authentication & Access Control"])

class DevLoginRequest(BaseModel):
    role: str = "Reviewer MD"
    username: Optional[str] = None
    organization_id: str = "org_riverside"

class CallbackRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Returns the authenticated reviewer profile, active role, organization, and permissions."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        organization_id=current_user.organization_id,
        permissions=[p.value for p in current_user.permissions]
    )

@router.get("/csrf", response_model=CSRFTokenResponse)
async def get_csrf_token(
    request: Request,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Issues or refreshes the double-submit CSRF token bound to the authenticated session."""
    session_id = current_user.user_id
    token = generate_csrf_token(session_id)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Accessible by frontend to attach to X-CSRF-Token header
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/"
    )
    return CSRFTokenResponse(csrf_token=token)

@router.get("/login-url")
async def get_oidc_login_url(redirect_uri: str = "http://localhost:5173/auth/callback"):
    """
    Generates standard OpenID Connect Authorization Code Flow URL with PKCE (RFC 7636).
    In production mode, requires a genuine configured IdP.
    """
    if settings.is_production and not settings.is_idp_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production OIDC Identity Provider is not configured. Access fails closed."
        )

    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)
    
    authorization_url = (
        f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/auth?"
        f"client_id={settings.OIDC_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid%20profile%20email&"
        f"redirect_uri={redirect_uri}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256&"
        f"state={state}"
    )

    return {
        "authorization_url": authorization_url,
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
        "state": state
    }

@router.post("/dev-login", response_model=UserProfileResponse)
async def dev_mode_login(
    req: DevLoginRequest,
    response: Response,
    request: Request
):
    """
    Development/Demo authentication endpoint.
    Permitted ONLY in local development environments when MEDRULE_ENV!=production.
    Issues cryptographically valid signed OIDC tokens for testing RBAC roles.
    Strictly blocked in production environments (fails closed).
    """
    if not settings.is_dev_auth_allowed:
        audit_service.log_event(
            action="DEV_LOGIN_BLOCKED_IN_PRODUCTION",
            user=None,
            status="DENIED",
            ip_address=request.client.host if request.client else None,
            details={"requested_role": req.role}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local development authentication is prohibited in production. Use configured OIDC provider."
        )

    try:
        role = UserRole.from_str(req.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{req.role}'. Must be one of: {[r.value for r in UserRole]}"
        )

    role_defaults = {
        UserRole.REVIEWER_MD: ("rev_shrinidhi", "Dr. Shrinidhi Bijapur, MD", "reviewer@medauth.org"),
        UserRole.NURSE_AUDITOR: ("nurse_auditor_01", "Sarah Jenkins, RN", "nurse.auditor@medauth.org"),
        UserRole.COMPLIANCE_OFFICER: ("comp_officer_01", "Marcus Vance, JD", "compliance@medauth.org"),
        UserRole.SYSTEM_ADMIN: ("sysadmin_01", "Platform Administrator", "admin@medauth.org"),
    }

    def_username, def_name, def_email = role_defaults[role]
    username = req.username or def_username

    user = AuthenticatedUser(
        user_id=f"usr_{username}",
        username=username,
        email=def_email,
        full_name=def_name,
        role=role,
        organization_id=req.organization_id,
        permissions=ROLE_PERMISSIONS.get(role, set())
    )

    token = create_access_token(user)
    csrf_token = generate_csrf_token(user.user_id)

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    # Set CSRF cookie
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    audit_service.log_event(
        action="AUTH_LOGIN_SUCCESS",
        user=user,
        resource="/api/auth/dev-login",
        status="SUCCESS",
        ip_address=request.client.host if request.client else None,
        details={"login_method": "development_mode", "role": user.role.value}
    )

    return UserProfileResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        organization_id=user.organization_id,
        permissions=[p.value for p in user.permissions]
    )

@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user)
):
    """Safely invalidates the browser session by clearing HttpOnly session and CSRF cookies."""
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")

    if current_user:
        audit_service.log_event(
            action="AUTH_LOGOUT",
            user=current_user,
            resource="/api/auth/logout",
            status="SUCCESS",
            ip_address=request.client.host if request.client else None,
            details={"logout_reason": "user_initiated"}
        )

    return {"message": "Session terminated successfully."}
