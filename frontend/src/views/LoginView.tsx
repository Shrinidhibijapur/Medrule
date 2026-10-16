import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { 
  ShieldAlert, 
  ArrowRight, 
  ShieldCheck, 
  KeyRound, 
  Stethoscope, 
  FileCheck, 
  Scale, 
  Shield, 
  AlertCircle,
  Building2,
  LucideIcon
} from 'lucide-react';

interface LoginViewProps {
  onLoginSuccess?: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { loginWithRole, loginWithOidc, authError, isLoading } = useAuth();

  const [selectedRole, setSelectedRole] = useState<UserRole>('Reviewer MD');
  const [selectedOrg, setSelectedOrg] = useState<string>('org_riverside');

  const destination = (location.state as any)?.from?.pathname || '/dashboard';

  const handleRoleSignIn = async (role: UserRole) => {
    setSelectedRole(role);
    const success = await loginWithRole(role, selectedOrg);
    if (success) {
      if (onLoginSuccess) {
        onLoginSuccess();
      } else {
        navigate(destination, { replace: true });
      }
    }
  };

  const handleOidcSignIn = async () => {
    await loginWithOidc();
  };

  const roleProfiles: Array<{
    role: UserRole;
    name: string;
    icon: LucideIcon;
    desc: string;
    permissions: string;
  }> = [
    {
      role: 'Reviewer MD',
      name: 'Dr. Shubhankar Roy, MD',
      icon: Stethoscope,
      desc: 'Lead Clinical Reviewer',
      permissions: 'Full clinical review, fact overrides, deterministic evaluations & export.',
    },
    {
      role: 'Nurse Auditor',
      name: 'Sarah Jenkins, RN',
      icon: FileCheck,
      desc: 'Clinical Prior Auth Auditor',
      permissions: 'Evidence inspection & fact flagging. Fact overrides strictly restricted.',
    },
    {
      role: 'Compliance Officer',
      name: 'Marcus Vance, JD',
      icon: Scale,
      desc: 'Regulatory & Governance Officer',
      permissions: 'Audit trail inspection & export packages. Fact changes & note uploads blocked.',
    },
    {
      role: 'System Admin',
      name: 'Platform Administrator',
      icon: Shield,
      desc: 'Security & Policy Admin',
      permissions: 'Policy verification gates, terminology allowlist, audit. No clinical editing.',
    },
  ];

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      width: '100vw',
      backgroundColor: '#FFFFFF',
      fontFamily: 'var(--font-sans)',
    }}>
      {/* Left Botanical Brand Hero */}
      <div style={{
        flex: 1,
        backgroundColor: '#EBE9E1',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '80px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute',
          left: '-40px',
          bottom: '-60px',
          width: '380px',
          height: '480px',
          opacity: 0.85,
          pointerEvents: 'none',
        }}>
          <svg aria-hidden="true" role="presentation" viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M40,240 C30,170 50,110 90,60 C100,45 120,20 140,10 C145,25 140,50 120,80 C95,115 80,165 75,240 Z" fill="#3D5A47" />
            <path d="M75,180 C110,160 160,150 190,130 C185,150 165,175 130,195 C100,210 85,220 75,240 Z" fill="#69806F" />
            <path d="M60,110 C90,80 140,65 170,40 C160,65 140,90 105,115 C85,128 70,135 60,140 Z" fill="#4C6855" />
          </svg>
        </div>

        <div style={{ maxWidth: '440px', position: 'relative', zIndex: 1 }}>
          <h1 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '44px',
            lineHeight: 1.15,
            color: 'var(--text-primary)',
            marginBottom: '18px',
            fontWeight: 600,
          }}>
            Medical<br />Authorization<br />Assistant
          </h1>
          <p style={{
            fontSize: '18px',
            color: 'var(--text-secondary)',
            letterSpacing: '0.2px',
            marginBottom: '32px',
          }}>
            Policy-driven. Accurate. Transparent.
          </p>

          <div style={{
            backgroundColor: 'rgba(255, 255, 255, 0.75)',
            border: '1px solid #D5D2C7',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '16px',
            fontSize: '12px',
            lineHeight: 1.5,
            color: '#4B5563',
          }}>
            <strong style={{ display: 'block', color: '#1C201D', marginBottom: '4px' }}>
              Genuine Role-Based Access Control
            </strong>
            Protected endpoints enforce server-side authorization gates. Hiding UI elements is never treated as security.
          </div>
        </div>
      </div>

      {/* Right Sign-in Form Panel */}
      <div style={{
        flex: 1.2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px',
        overflowY: 'auto',
      }}>
        <div style={{ width: '100%', maxWidth: '480px' }}>
          {/* Clinical Governance Callout */}
          <div style={{
            backgroundColor: '#FEF3C7',
            border: '1px solid #F59E0B',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '14px 16px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}>
            <ShieldAlert size={20} color="#B45309" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <strong style={{ fontSize: '12px', color: '#92400E', display: 'block', marginBottom: '2px' }}>
                PHASE 8 GENUINE AUTHENTICATION & ACCESS CONTROL ACTIVE
              </strong>
              <p style={{ fontSize: '12px', color: '#78350F', margin: 0, lineHeight: 1.45 }}>
                Authentic session cookies and RBAC permissions are active. Real patient authorization remains strictly BLOCKED until genuine policy checksum verification and clinical sign-offs are completed.
              </p>
            </div>
          </div>

          {/* Auth Error Banner */}
          {authError && (
            <div style={{
              backgroundColor: '#FEE2E2',
              border: '1px solid #EF4444',
              borderRadius: 'var(--radius-md, 8px)',
              padding: '12px 16px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '13px',
              color: '#991B1B',
            }}>
              <AlertCircle size={18} color="#DC2626" />
              <span>{authError}</span>
            </div>
          )}

          <h2 style={{ fontSize: '26px', fontWeight: '700', marginBottom: '6px', color: '#1C201D' }}>
            Reviewer Portal
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '20px' }}>
            OpenID Connect (OIDC) PKCE Authentication & Clinical Role Switcher
          </p>

          {/* Organization Selector */}
          <div style={{ marginBottom: '18px' }}>
            <label htmlFor="login-org" style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: '#1C201D' }}>
              Healthcare Organization (Tenant Isolation)
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              border: '1px solid var(--border-subtle, #E5E2DA)',
              borderRadius: 'var(--radius-sm, 6px)',
              padding: '8px 12px',
              backgroundColor: '#FAFAF8',
            }}>
              <Building2 size={16} color="#6D7069" />
              <select
                id="login-org"
                value={selectedOrg}
                onChange={(e) => setSelectedOrg(e.target.value)}
                style={{
                  border: 'none',
                  outline: 'none',
                  width: '100%',
                  backgroundColor: 'transparent',
                  fontSize: '13px',
                  color: '#1C201D',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                <option value="org_riverside">Riverside Regional Medical Center (Tenant A)</option>
                <option value="org_memorial">Memorial Healthcare System (Tenant B)</option>
              </select>
            </div>
          </div>

          {/* OIDC Keycloak SSO Button */}
          <button
            type="button"
            onClick={handleOidcSignIn}
            disabled={isLoading}
            className="btn btn-outline"
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '14px',
              fontWeight: 600,
              gap: '10px',
              justifyContent: 'center',
              backgroundColor: '#FAF9F6',
              border: '1px solid #315B45',
              color: '#315B45',
              marginBottom: '20px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
            }}
          >
            <KeyRound size={18} color="#315B45" />
            <span>Sign in via Identity Provider (OIDC / Keycloak)</span>
          </button>

          {/* Divider */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            margin: '20px 0',
            gap: '12px',
          }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle, #E5E2DA)' }} />
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted, #6D7069)', fontWeight: 600 }}>
              Authorized Role Sign-In
            </span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle, #E5E2DA)' }} />
          </div>

          {/* Role Profiles Grid */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
            {roleProfiles.map((item) => {
              const Icon = item.icon;
              const isSelected = selectedRole === item.role;

              return (
                <button
                  key={item.role}
                  type="button"
                  onClick={() => handleRoleSignIn(item.role)}
                  disabled={isLoading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-sm, 6px)',
                    border: isSelected ? '2px solid #315B45' : '1px solid #E5E2DA',
                    backgroundColor: isSelected ? '#FAF9F6' : '#FFFFFF',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '6px',
                      backgroundColor: isSelected ? '#EBE9E1' : '#F7F6F2',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <Icon size={18} color="#315B45" />
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#1C201D' }}>
                        {item.role} <span style={{ fontWeight: 400, color: '#6D7069' }}>— {item.name}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#6D7069', marginTop: '2px' }}>
                        {item.permissions}
                      </div>
                    </div>
                  </div>
                  <ArrowRight size={16} color={isSelected ? '#315B45' : '#A3A39D'} />
                </button>
              );
            })}
          </div>

          <p style={{
            fontSize: '11px',
            color: '#8A8D86',
            textAlign: 'center',
            lineHeight: 1.4,
            margin: 0,
          }}>
            Protected by HttpOnly SameSite Session Cookies & Double-Submit HMAC CSRF.<br />
            Access tokens are strictly managed on the server and never stored in localStorage.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginView;
