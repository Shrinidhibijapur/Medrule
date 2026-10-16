# MedRule Phase 8: Authentication, Authorization & Access Control Architecture

## 1. Executive Summary

Phase 8 elevates MedRule from unrestricted demonstration access to a security-first, role-based, tenant-isolated medical decision-support platform. The architecture implements standards-based OpenID Connect (OIDC) with Authorization Code Flow and PKCE (RFC 7636), server-side token validation, dual-transport session handling (secure HttpOnly SameSite cookies and Bearer tokens), double-submit HMAC CSRF mitigation, granular Role-Based Access Control (RBAC), multi-tenant case-level isolation, and tamper-evident audit logging.

> [!IMPORTANT]
> **Clinical Governance Notice**:
> MedRule Phase 8 maintains all prior clinical governance restrictions. Real-patient authorization remains strictly **BLOCKED**. All demonstrations use synthetic clinical records.

---

## 2. Authentication & Authorization Architecture

### 2.1 OpenID Connect (OIDC) with PKCE
MedRule integrates with standard OIDC identity providers (such as Keycloak, Okta, or Authentik) via the Authorization Code Flow with Proof Key for Code Exchange (RFC 7636):
1. **PKCE Pair Generation**: The client initiates authentication via `/api/auth/login-url`. The backend generates a cryptographically secure `code_verifier` (minimum 43 characters, URL-safe base64) and derives the `code_challenge` using SHA-256 (`code_challenge_method=S256`).
2. **Authorization Request**: The user is redirected to the IdP's authorization endpoint with `client_id`, `redirect_uri`, `scope=openid profile email`, `code_challenge`, and a signed `state` parameter to mitigate cross-site request forgery.
3. **Authorization Code Exchange**: The IdP issues an authorization code upon user authentication. The frontend or callback endpoint exchanges this code along with the `code_verifier` for an ID token, Access token, and Refresh token.
4. **Token Validation**: The server validates:
   - `iss` (Issuer): Must match `OIDC_ISSUER_URL`.
   - `aud` (Audience): Must match `OIDC_AUDIENCE` or `OIDC_CLIENT_ID`.
   - `exp` (Expiration): Current UTC timestamp must not exceed `exp`.
   - `nbf` / `iat`: Token must not be used before validity time.
   - Signature: Verified using the IdP's JSON Web Key Set (`OIDC_JWKS_URL`) via RS256, or internal HS256 for local development sessions.

### 2.2 Dual-Transport Session Security
MedRule supports two secure authentication transport mechanisms:
1. **HttpOnly SameSite Browser Cookies**:
   - Cookie Name: `medrule_session`
   - Attributes: `HttpOnly; SameSite=Lax; Path=/` (and `Secure` in production).
   - Never accessible to client-side JavaScript, mitigating Cross-Site Scripting (XSS) token extraction.
2. **Authorization Bearer Headers**:
   - Header: `Authorization: Bearer <jwt_token>`
   - Supported for programmatic API clients and automated integration tests.

### 2.3 Double-Submit HMAC CSRF Protection
For browser cookie sessions, state-mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) are protected against Cross-Site Request Forgery (CSRF):
- A cryptographically signed HMAC token is issued via `/api/auth/csrf` and bound to the user's session identifier.
- The client reads the CSRF token and submits it via the `X-CSRF-Token` header.
- The server validates the HMAC signature using `secrets.compare_digest` in `verify_csrf_if_cookie` dependency before executing any mutating action. Requests failing CSRF verification receive `403 Forbidden`.

### 2.4 Multi-Tenant Case-Level Isolation
- Every case record is permanently tagged with an `organization_id` (e.g. `org_riverside`, `org_cedars`, `org_memorial`).
- Every authenticated user possesses an assigned `organization_id`.
- The `check_case_tenant` gate verifies that `current_user.can_access_tenant(case.organization_id)` evaluates to `True`.
- Unauthorized attempts to access, evaluate, or export records across tenant boundaries are rejected with `403 Forbidden` and recorded in the audit log as `TENANT_ACCESS_DENIED`.

---

## 3. Role-Permission Matrix

MedRule enforces the principle of least privilege across four core organizational roles:

| Role Name | Identifier | Primary Responsibilities |
| :--- | :--- | :--- |
| **Reviewer MD** | `role_reviewer_md` | Licensed medical practitioner authorized for full clinical evaluation, fact verification, overrides, and final determination. |
| **Nurse Auditor** | `role_nurse_auditor` | Clinical auditor responsible for factual consistency checks, criteria evaluation, flagging discrepancies, and preliminary reviews. |
| **Compliance Officer** | `role_compliance_officer` | Regulatory officer auditing decision packages, verifying evidence provenance, inspecting audit trails, and exporting compliance logs. |
| **System Admin** | `role_system_admin` | Technical administrator managing policy lifecycles, terminology sources, system configuration, and audit settings. |

### 3.1 Detailed Granular Permissions Table

| Action / Capability | API Endpoint | Reviewer MD | Nurse Auditor | Compliance Officer | System Admin |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **View Cases & Facts** | `GET /api/cases`, `GET /api/cases/{id}` |  ALLOW |  ALLOW |  ALLOW |  ALLOW |
| **Upload Clinical Notes** | `POST /api/notes/extract` |  ALLOW |  ALLOW | ❌ DENIED | ❌ DENIED |
| **Flag Inaccurate Facts** | `POST /api/cases/{id}/facts/{fid}/flag` |  ALLOW |  ALLOW | ❌ DENIED | ❌ DENIED |
| **Override Clinical Facts** | `POST /api/cases/{id}/facts/{fid}/correct` |  ALLOW | ❌ DENIED | ❌ DENIED | ❌ DENIED |
| **Evaluate Criteria** | `POST /api/criteria/evaluate` |  ALLOW |  ALLOW | ❌ DENIED | ❌ DENIED |
| **Export Decision Report** | `GET /api/cases/{id}/export-decision` |  ALLOW |  ALLOW |  ALLOW | ❌ DENIED |
| **Export Audit Package** | `GET /api/cases/{id}/export-audit` |  ALLOW |  ALLOW |  ALLOW | ❌ DENIED |
| **View Audit Trail** | `GET /api/audit/events` | ❌ DENIED | ❌ DENIED |  ALLOW |  ALLOW |
| **Manage Policies** | `POST /api/policies/register`, `POST .../status` | ❌ DENIED | ❌ DENIED | ❌ DENIED |  ALLOW |
| **Manage Terminology** | `POST /api/terminology/sources` | ❌ DENIED | ❌ DENIED | ❌ DENIED |  ALLOW |
| **System Administration** | `/api/settings/*` | ❌ DENIED | ❌ DENIED | ❌ DENIED |  ALLOW |

---

## 4. Database Migrations & Persistence Schemas

In production environments, MedRule transitions from local JSON/JSONL flat-file storage to an enterprise relational database (PostgreSQL with Row-Level Security). Below are the target production migration schemas:

### 4.1 Schema Definitions (PostgreSQL DDL)

```sql
-- 1. Organizations (Tenants)
CREATE TABLE organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table
CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    oidc_subject_id VARCHAR(255) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Roles and Permissions
CREATE TABLE roles (
    name VARCHAR(64) PRIMARY KEY,
    display_name VARCHAR(128) NOT NULL,
    description TEXT
);

CREATE TABLE role_permissions (
    role_name VARCHAR(64) NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
    permission VARCHAR(64) NOT NULL,
    PRIMARY KEY (role_name, permission)
);

CREATE TABLE user_roles (
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_name VARCHAR(64) NOT NULL REFERENCES roles(name) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(64) REFERENCES users(id),
    PRIMARY KEY (user_id, role_name)
);

-- 4. Audit Log (Append-Only, Immutable)
CREATE TABLE audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    username VARCHAR(255) NOT NULL,
    role VARCHAR(64) NOT NULL,
    organization_id VARCHAR(64) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Row-level security for multi-tenant isolation
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON audit_events
    FOR ALL
    USING (organization_id = current_setting('app.current_organization_id', true));
```

### 4.2 Seed Data
```sql
INSERT INTO roles (name, display_name, description) VALUES
('role_reviewer_md', 'Reviewer MD', 'Licensed physician with full clinical determination authority'),
('role_nurse_auditor', 'Nurse Auditor', 'Clinical auditor for fact verification and criteria checking'),
('role_compliance_officer', 'Compliance Officer', 'Regulatory officer auditing determinations and audit trails'),
('role_system_admin', 'System Admin', 'Technical administrator managing policies, terminology, and system config');

INSERT INTO organizations (id, name, domain) VALUES
('org_riverside', 'Riverside Health Network', 'riversidehealth.org'),
('org_cedars', 'Cedars Clinical Group', 'cedarsclinical.org');
```

---

## 5. Security Controls & Audit Logging

### 5.1 Log Sanitization & Privacy Preservation
The centralized `AuditService` (`backend/app/services/audit_service.py`) guarantees patient privacy and credential security:
- **Zero Credential Logging**: Access tokens, refresh tokens, passwords, and client secrets are stripped before serialization.
- **Zero Raw Clinical Note Logging**: Free-text clinical narratives, patient physician names, and unstructured EHR extracts are never written to audit event logs.
- **Sanitized Details**: Only structured IDs (`case_id`, `fact_id`, `policy_id`), criterion keys (`c1_lumbar_radiculopathy`), and status transitions (`APPROVED`, `OVERRIDDEN`) are logged.
- **Deterministic Attribution**: Every audit entry binds the user's UUID, full name, role, organization, ISO 8601 UTC timestamp, and action outcome (`SUCCESS`, `DENIED`, `FAILED`).

### 5.2 Security Headers
The backend enforces modern HTTP security headers across every endpoint:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none';
```

---

## 6. Local Development vs. Production Setup

### 6.1 Safe Local Development Setup
1. Ensure `.env` is configured with `MEDRULE_ENV=development`.
2. In development mode, developers can use the authenticated Dev Login workflow on `/login` to switch between test roles (`Reviewer MD`, `Nurse Auditor`, `Compliance Officer`, `System Admin`) and test organizations.
3. Dev tokens are signed using the local `JWT_SECRET_KEY` and delivered via HttpOnly session cookies.

### 6.2 Production Fail-Closed Setup
1. Set `MEDRULE_ENV=production`.
2. Configure `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_AUDIENCE`, and `OIDC_JWKS_URL`.
3. Set `COOKIE_SECURE=true` and `CORS_ALLOWED_ORIGINS=https://app.medrule.health`.
4. Dev login endpoints (`/api/auth/dev-login`) are automatically disabled with `403 Forbidden`.
5. If the production OIDC Identity Provider is unreachable or unconfigured, the system fails closed with `503 Service Unavailable`, rejecting all protected API requests.
