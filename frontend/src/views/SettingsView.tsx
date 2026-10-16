import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, ArrowLeft, ShieldCheck, Database, Lock, Sliders, Bell } from 'lucide-react';
import { ViewMode } from '../types';

interface SettingsViewProps {
  onNavigate?: (view: ViewMode) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onNavigate }) => {
  const navigate = useNavigate();

  const handleBackToDashboard = () => {
    if (onNavigate) {
      onNavigate('dashboard');
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div style={{ maxWidth: '980px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', margin: 0 }}>
              System Governance & Integration Settings
            </h1>
            <span style={{
              fontSize: '11px',
              fontWeight: '700',
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: '#EAF5EE',
              color: '#26734D',
              border: '1px solid #C8E6D3'
            }}>
              Active Governance Controls
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            Configured regulatory constraints, clinical reviewer roles, audit retention rules, and Phase 8 identity roadmap
          </p>
        </div>

        <button
          type="button"
          onClick={handleBackToDashboard}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Dashboard</span>
        </button>
      </div>

      {/* Governance Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #FCD34D',
        borderRadius: 'var(--radius-md)',
        padding: '14px 18px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <ShieldCheck size={20} color="#92400E" />
        <span style={{ fontSize: '13px', color: '#92400E', lineHeight: 1.5 }}>
          <strong>Active Governance Enforcement:</strong> Settings parameters reflect strictly enforced Phase 2–6 verification gates, SHA-256 byte checksum validation, approved terminology domain registries, and HIPAA 7-year audit retention. Production EHR integrations and enterprise SSO/RBAC are scheduled for Phase 8.
        </span>
      </div>

      {/* Settings Sections Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '28px' }}>
        {/* Section 1: Verification Gate Controls */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Lock size={18} color="var(--primary)" />
            <h2 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>
              Clinical Policy Verification Gate Controls
            </h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', fontSize: '13px' }}>
            <div style={{ padding: '14px', backgroundColor: '#FAF9F6', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Mandatory Reviewer Count</div>
              <div style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>2 Independent Reviewers (Primary MD + Secondary RN/Auditor)</div>
              <span style={{ display: 'inline-block', marginTop: '8px', fontSize: '11px', fontWeight: '600', color: 'var(--success)' }}>
                ENFORCED (Code Gate Active)
              </span>
            </div>

            <div style={{ padding: '14px', backgroundColor: '#FAF9F6', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Checksum Validation Rule</div>
              <div style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>SHA-256 PDF byte verification with empty-hash rejection</div>
              <span style={{ display: 'inline-block', marginTop: '8px', fontSize: '11px', fontWeight: '600', color: 'var(--success)' }}>
                ENFORCED (Zero-Tolerance)
              </span>
            </div>
          </div>
        </div>

        {/* Section 2: Storage & Audit Retention */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Database size={18} color="var(--primary)" />
            <h2 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>
              Audit Package Retention & Export Standards
            </h2>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0', lineHeight: 1.5 }}>
            Every authorization assessment produces a tamper-evident audit record documenting the source PDF hash, extracted evidence citations, clinician corrections, and deterministic criteria trace.
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ padding: '10px 14px', backgroundColor: '#FAF9F6', borderRadius: '4px', border: '1px solid var(--border-subtle)', fontSize: '12px' }}>
              <strong>Formats:</strong> Formatted Plain Text (.txt) & Machine-Readable JSON (.json)
            </div>
            <div style={{ padding: '10px 14px', backgroundColor: '#FAF9F6', borderRadius: '4px', border: '1px solid var(--border-subtle)', fontSize: '12px' }}>
              <strong>Retention Policy:</strong> 7 Years (HIPAA Prior Authorization Compliance Preset)
            </div>
          </div>
        </div>

        {/* Section 3: Phase 8 Active Authentication & Access Control */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Sliders size={18} color="#315B45" />
            <h2 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>
              Phase 8 Authentication & Access Control Architecture
            </h2>
            <span style={{
              fontSize: '11px',
              fontWeight: '700',
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: '#EAF5EE',
              color: '#26734D',
              border: '1px solid #C8E6D3'
            }}>
              Active & Enforced
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 12px 0', lineHeight: 1.5 }}>
            Production-grade authentication, session isolation, and server-side authorization controls are active:
          </p>
          <ul style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            <li><strong>OpenID Connect (OIDC) & PKCE:</strong> Authorization Code Flow (RFC 7636) with configurable IdP (Keycloak). Direct production bypasses strictly prohibited.</li>
            <li><strong>Server-Side RBAC Enforcement:</strong> Granular permissions enforced via FastAPI dependencies for Reviewer MD, Nurse Auditor, Compliance Officer, and System Admin.</li>
            <li><strong>Tenant Isolation:</strong> Cross-organization IDOR access prevented at every endpoint; users restricted to their assigned health system records.</li>
            <li><strong>HttpOnly SameSite Cookies & Double-Submit CSRF:</strong> Cryptographic token validation on every request without exposing access tokens to localStorage.</li>
            <li><strong>Centralized Audit Attribution:</strong> Every auth, override, flag, evaluation, and export event bound to verified reviewer identity and timestamp without logging sensitive credentials or raw note texts.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SettingsView;
