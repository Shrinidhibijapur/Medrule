from typing import Optional, Callable
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.security import (
    decode_and_validate_token,
    validate_csrf_token,
    AuthenticationError,
    AuthorizationError
)
from app.models.auth import AuthenticatedUser, UserRole, Permission
from app.services.audit_service import audit_service

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> AuthenticatedUser:
    """
    Authenticates the current user from Bearer header or HttpOnly session cookie.
    Validates token signature, expiration, issuer, audience, and required claims.
    Fails closed if token is invalid, expired, or missing.
    """
    token: Optional[str] = None
    
    # 1. Check Bearer Authorization header
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
        
    # 2. Check HttpOnly session cookie if header not provided
    if not token:
        cookie_val = request.cookies.get(settings.COOKIE_NAME)
        if cookie_val:
            token = cookie_val

    if not token:
        raise AuthenticationError("Authentication required. Please sign in via the configured Identity Provider.")

    try:
        user = decode_and_validate_token(token)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise AuthenticationError(f"Authentication validation failed: {str(e)}")

def require_permission(permission: Permission) -> Callable:
    """FastAPI dependency factory enforcing least-privilege role permissions."""
    async def permission_checker(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not current_user.has_permission(permission):
            # Log authorization denial event in audit trail
            audit_service.log_event(
                action="AUTHORIZATION_DENIED",
                user=current_user,
                resource=str(request.url.path),
                status="DENIED",
                ip_address=request.client.host if request.client else None,
                details={
                    "required_permission": permission.value,
                    "user_role": current_user.role.value,
                    "method": request.method
                }
            )
            raise AuthorizationError(
                f"Role '{current_user.role.value}' does not possess required permission '{permission.value}'"
            )
        return current_user
    return permission_checker

def require_role(allowed_roles: list[UserRole]) -> Callable:
    """FastAPI dependency factory enforcing specific user roles."""
    async def role_checker(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            audit_service.log_event(
                action="ROLE_ACCESS_DENIED",
                user=current_user,
                resource=str(request.url.path),
                status="DENIED",
                ip_address=request.client.host if request.client else None,
                details={
                    "allowed_roles": [r.value for r in allowed_roles],
                    "user_role": current_user.role.value
                }
            )
            raise AuthorizationError(
                f"User role '{current_user.role.value}' is not authorized for this resource"
            )
        return current_user
    return role_checker

async def verify_csrf_if_cookie(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> None:
    """
    CSRF Protection dependency.
    If the request uses a cookie-based session and modifies state (POST, PUT, PATCH, DELETE),
    verifies that a valid X-CSRF-Token header is supplied matching the session cookie.
    Bearer token requests are exempt from CSRF as browsers never send Bearer headers implicitly.
    """
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return

    # If Bearer token is provided explicitly in header, CSRF attack is not applicable
    if auth_header and auth_header.credentials:
        return

    # Check if session cookie is present
    session_cookie = request.cookies.get(settings.COOKIE_NAME)
    if not session_cookie:
        return

    csrf_header = request.headers.get("x-csrf-token")
    if not csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed: Missing X-CSRF-Token header on cookie-authenticated request."
        )

    # Resolve bound session ID from session token
    try:
        user = decode_and_validate_token(session_cookie)
        bound_id = user.user_id
    except Exception:
        bound_id = session_cookie

    if not validate_csrf_token(csrf_header, bound_id) and not validate_csrf_token(csrf_header, session_cookie):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed: Invalid or expired X-CSRF-Token token."
        )
