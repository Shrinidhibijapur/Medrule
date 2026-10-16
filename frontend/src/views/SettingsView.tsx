import React from 'react';
import { Settings, ArrowLeft, ShieldCheck, Database, Lock, Sliders, Bell } from 'lucide-react';
import { ViewMode } from '../types';

interface SettingsViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onNavigate }) => {
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
              backgroundColor: '#FEF3C7',
              color: '#92400E',
              border: '1px solid #FCD34D'
            }}>
              Phase 6/7 Roadmap
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            Configurable regulatory controls, clinical reviewer roles, EHR connection endpoints, and audit retention policies
          </p>
        </div>

        <button
          onClick={() => onNavigate('dashboard')}
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
        <span style={{ fontSize: '13px', color: '#92400E' }}>
          <strong>Demo Preset Configuration:</strong> Settings currently operate under verified synthetic demonstration parameters. Production identity federation and EHR production endpoints will be unlocked during Phase 6/7.
        </span>
      </div>

      {/* Settings Sections Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '28px' }}>
        {/* Section 1: Verification Gate Controls */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Lock size={18} color="var(--primary)" />
            <h2 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>
              Phase 2 Clinical Policy Verification Gate Controls
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
      </div>
    </div>
  );
};
