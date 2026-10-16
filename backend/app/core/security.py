import hmac
import hashlib
import base64
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
import jwt
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.auth import AuthenticatedUser, UserRole, Permission, ROLE_PERMISSIONS

class AuthenticationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions for requested resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

def create_access_token(
    user: AuthenticatedUser,
    expires_delta: Optional[timedelta] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None
) -> str:
    """Generates a cryptographically signed standard OIDC/JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload: Dict[str, Any] = {
        "sub": user.user_id,
        "iss": issuer or settings.OIDC_ISSUER_URL,
        "aud": audience or settings.OIDC_AUDIENCE,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "role": user.role.value,
        "org_id": user.organization_id,
        "email": user.email,
        "preferred_username": user.username,
        "name": user.full_name,
    }
    
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return token

def decode_and_validate_token(
    token: str,
    verify_issuer: bool = True,
    verify_audience: bool = True
) -> AuthenticatedUser:
    """
    Validates token signature, expiration, issuer, audience, and claims.
    Fails closed on any cryptographic or claim violation.
    """
    try:
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_iss": verify_issuer,
            "verify_aud": verify_audience,
            "require": ["sub", "exp", "iss", "aud", "role", "org_id"]
        }
        
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.OIDC_ISSUER_URL if verify_issuer else None,
            audience=settings.OIDC_AUDIENCE if verify_audience else None,
            options=options
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Session token has expired. Please re-authenticate.")
    except jwt.InvalidIssuerError:
        raise AuthenticationError(f"Invalid token issuer. Must match {settings.OIDC_ISSUER_URL}.")
    except jwt.InvalidAudienceError:
        raise AuthenticationError(f"Invalid token audience. Must match {settings.OIDC_AUDIENCE}.")
    except jwt.InvalidSignatureError:
        raise AuthenticationError("Token cryptographic signature verification failed.")
    except jwt.PyJWTError as e:
        raise AuthenticationError(f"Invalid authentication token: {str(e)}")

    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Token missing required 'sub' (subject) claim.")

    role_str = payload.get("role")
    try:
        role = UserRole.from_str(role_str)
    except Exception:
        raise AuthenticationError(f"Unknown or unauthorized role claim: {role_str}")

    org_id = payload.get("org_id", "org_riverside")
    username = payload.get("preferred_username") or payload.get("email") or sub
    email = payload.get("email") or f"{username}@medauth.org"
    full_name = payload.get("name") or username

    return AuthenticatedUser(
        user_id=sub,
        username=username,
        email=email,
        full_name=full_name,
        role=role,
        organization_id=org_id,
        permissions=ROLE_PERMISSIONS.get(role, set())
    )

# --- CSRF Protection via Signed Double-Submit Token ---

def generate_csrf_token(session_id: str) -> str:
    """Generates an HMAC-signed CSRF token bound to the current session."""
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    random_salt = secrets.token_hex(8)
    message = f"{session_id}:{timestamp}:{random_salt}".encode("utf-8")
    signature = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    raw = f"{session_id}:{timestamp}:{random_salt}:{signature}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

def validate_csrf_token(csrf_token: str, session_id: str) -> bool:
    """Validates the authenticity and session binding of a submitted CSRF token."""
    if not csrf_token or not session_id:
        return False
    try:
        decoded = base64.urlsafe_b64decode(csrf_token.encode("utf-8")).decode("utf-8")
        parts = decoded.split(":")
        if len(parts) != 4:
            return False
        token_session, timestamp_str, random_salt, signature = parts
        
        # Verify session binding
        if not hmac.compare_digest(token_session, session_id):
            return False
            
        # Verify signature
        message = f"{token_session}:{timestamp_str}:{random_salt}".encode("utf-8")
        expected_sig = hmac.new(
            settings.CSRF_SECRET_KEY.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return False
            
        # Check expiry (token valid for 24 hours)
        token_time = int(timestamp_str)
        now_time = int(datetime.now(timezone.utc).timestamp())
        if now_time - token_time > 86400:
            return False
            
        return True
    except Exception:
        return False

# --- PKCE (RFC 7636) Helper for OIDC Authorization Code Flow ---

def generate_pkce_pair() -> Tuple[str, str]:
    """Generates a high-entropy code_verifier and corresponding SHA-256 code_challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge

def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verifies that SHA-256(code_verifier) matches the stored code_challenge."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return hmac.compare_digest(computed_challenge, code_challenge)
