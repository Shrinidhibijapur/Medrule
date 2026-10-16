import os
from typing import List, Optional
from pydantic import BaseModel, Field

class Settings(BaseModel):
    # Environment
    MEDRULE_ENV: str = Field(default_factory=lambda: os.getenv("MEDRULE_ENV", "development"))
    
    # OIDC Configuration
    OIDC_ISSUER_URL: str = Field(default_factory=lambda: os.getenv("OIDC_ISSUER_URL", "http://localhost:8080/realms/medrule"))
    OIDC_CLIENT_ID: str = Field(default_factory=lambda: os.getenv("OIDC_CLIENT_ID", "medrule-web"))
    OIDC_CLIENT_SECRET: Optional[str] = Field(default_factory=lambda: os.getenv("OIDC_CLIENT_SECRET", None))
    OIDC_AUDIENCE: str = Field(default_factory=lambda: os.getenv("OIDC_AUDIENCE", "medrule-api"))
    OIDC_JWKS_URL: Optional[str] = Field(default_factory=lambda: os.getenv("OIDC_JWKS_URL", None))
    
    # JWT & Session Cryptography
    JWT_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", "medrule-dev-insecure-signing-key-32chars-min-needed!!"))
    JWT_ALGORITHM: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    
    # Cookie Settings
    COOKIE_NAME: str = "medrule_session"
    SESSION_COOKIE_NAME: str = "medrule_session"
    COOKIE_SECURE: bool = Field(default_factory=lambda: os.getenv("COOKIE_SECURE", "false").lower() == "true")
    COOKIE_SAMESITE: str = Field(default_factory=lambda: os.getenv("COOKIE_SAMESITE", "lax"))
    COOKIE_DOMAIN: Optional[str] = Field(default_factory=lambda: os.getenv("COOKIE_DOMAIN", None))
    
    # CSRF Protection
    CSRF_COOKIE_NAME: str = "medrule_csrf"
    CSRF_HEADER_NAME: str = "x-csrf-token"
    CSRF_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("CSRF_SECRET_KEY", "medrule-csrf-secret-key-32chars-min-needed!!"))
    
    # CORS Origins
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if origin.strip()
        ]
    )
    
    # Security Governance
    FAIL_CLOSED_ON_MISSING_IDP: bool = Field(
        default_factory=lambda: os.getenv("FAIL_CLOSED_ON_MISSING_IDP", "true").lower() == "true"
    )

    @property
    def is_production(self) -> bool:
        return self.MEDRULE_ENV.lower() == "production"

    @property
    def is_idp_configured(self) -> bool:
        """Checks if a valid non-default OIDC IdP is reachable/configured."""
        if not self.OIDC_ISSUER_URL:
            return False
        if self.is_production and ("localhost" in self.OIDC_ISSUER_URL or "127.0.0.1" in self.OIDC_ISSUER_URL):
            return False
        return True

    @property
    def is_dev_auth_allowed(self) -> bool:
        """Local development token issuance is only allowed when strictly not in production."""
        return not self.is_production


settings = Settings()
