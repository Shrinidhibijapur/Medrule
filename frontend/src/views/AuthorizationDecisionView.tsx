import React from 'react';
import { Check, CheckCircle2, Download, RotateCcw } from 'lucide-react';
import { ViewMode } from '../types';
import { mockJohnDoeCase } from '../mockData';

interface AuthorizationDecisionViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const AuthorizationDecisionView: React.FC<AuthorizationDecisionViewProps> = ({ onNavigate }) => {
  const handleDownload = () => {
    const reportText = `
MEDRULE / MEDAUTH CLINICAL AUTHORIZATION REPORT
==================================================
Case ID: ${mockJohnDoeCase.id}
Date: ${mockJohnDoeCase.evaluation_date}
Patient: ${mockJohnDoeCase.patient_name} (${mockJohnDoeCase.patient_age}/${mockJohnDoeCase.gender})
Facility: ${mockJohnDoeCase.facility}
Procedure: ${mockJohnDoeCase.procedure}
Insurer: ${mockJohnDoeCase.insurance_plan} (Version: ${mockJohnDoeCase.policy_version})
DECISION: ${mockJohnDoeCase.status.toUpperCase()}

KEY REASONING & EVIDENCE:
--------------------------------------------------
${mockJohnDoeCase.key_reasoning.map((r, i) => `${i + 1}. ${r}`).join('\n')}

CRITERION-BY-CRITERION SUMMARY:
--------------------------------------------------
${mockJohnDoeCase.criteria_results.map(c => `[${c.rule_id}] ${c.criterion_name} (${c.section}): ${c.ui_label} - "${c.evidence_excerpt}"`).join('\n')}

VERDICT STATEMENT:
--------------------------------------------------
Approval of a CT scan requires all minimum clinical criteria to be met.
Conditions R1-R6 are satisfied and meet that minimum.
Therefore the CT scan request can be approved.

NOTICE:
Preliminary clinical decision support. Subject to authorized human review.
==================================================
    `.trim();

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MedRule_Authorization_Report_${mockJohnDoeCase.patient_name.replace(' ', '_')}.txt`;
    a.click();
  };

  return (
    <div style={{ maxWidth: '1000px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px' }}>
          Authorization Decision
        </h1>
      </div>

      {/* Hero Decision Banner */}
      <div style={{
        backgroundColor: '#EBF3EE',
        border: '1px solid var(--success-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px 28px',
        display: 'flex',
        alignItems: 'center',
        gap: '20px',
        marginBottom: '28px'
      }}>
        <div style={{
          width: '52px',
          height: '52px',
          borderRadius: '50%',
          backgroundColor: 'var(--primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#FFFFFF'
        }}>
          <Check size={30} strokeWidth={2.8} />
        </div>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
            CT Scan is Approved
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            The request meets all required policy criteria for authorization.
          </p>
        </div>
      </div>

      {/* Two-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '24px', marginBottom: '36px' }}>
        {/* Summary Card */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '20px', color: 'var(--text-primary)' }}>
            Summary
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <tbody>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Patient</td>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{mockJohnDoeCase.patient_name} ({mockJohnDoeCase.patient_age}/{mockJohnDoeCase.gender})</td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Procedure</td>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{mockJohnDoeCase.procedure}</td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Insurance Plan</td>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{mockJohnDoeCase.insurance_plan}</td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Decision</td>
                <td style={{ padding: '8px 0' }}>
                  <span className="badge badge-approved">Approved</span>
                </td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Policy Version</td>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{mockJohnDoeCase.policy_version}</td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Evaluation Date</td>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{mockJohnDoeCase.evaluation_date}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Key Reasoning Card */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '20px', color: 'var(--text-primary)' }}>
            Key Reasoning
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {mockJohnDoeCase.key_reasoning.map((reason, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <CheckCircle2 size={18} color="var(--primary)" style={{ marginTop: '2px', flexShrink: 0 }} />
                <span style={{ fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                  {reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={handleDownload}
          className="btn btn-outline"
          style={{ gap: '8px', padding: '10px 20px' }}
        >
          <Download size={16} />
          <span>Download Report</span>
        </button>

        <button
          onClick={() => onNavigate('new_review')}
          className="btn btn-primary"
          style={{ gap: '8px', padding: '10px 24px' }}
        >
          <RotateCcw size={16} />
          <span>Start New Review</span>
        </button>
      </div>
    </div>
  );
};
