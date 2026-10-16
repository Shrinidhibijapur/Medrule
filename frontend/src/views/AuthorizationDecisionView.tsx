import React from 'react';
import { Check, X, AlertCircle, AlertTriangle, Download, RotateCcw, ShieldCheck } from 'lucide-react';
import { ViewMode, EvaluationReport, ClinicalNoteRecord } from '../types';
import { mockJohnDoeCase } from '../mockData';

interface AuthorizationDecisionViewProps {
  onNavigate: (view: ViewMode) => void;
  evaluationReport?: EvaluationReport | null;
  caseRecord?: ClinicalNoteRecord | null;
}

export const AuthorizationDecisionView: React.FC<AuthorizationDecisionViewProps> = ({ 
  onNavigate,
  evaluationReport,
  caseRecord
}) => {
  const isLive = Boolean(evaluationReport);

  const patientName = evaluationReport?.patient_name || caseRecord?.patient_name || mockJohnDoeCase.patient_name;
  const procedure = evaluationReport?.procedure || caseRecord?.procedure_requested || mockJohnDoeCase.procedure;
  const insurer = evaluationReport?.insurer || caseRecord?.insurance_plan || mockJohnDoeCase.insurance_plan;
  const policyVersion = evaluationReport?.policy_version || caseRecord?.policy_version || mockJohnDoeCase.policy_version;
  const caseId = evaluationReport?.case_id || caseRecord?.case_id || mockJohnDoeCase.id;
  const evalDate = evaluationReport?.evaluation_date || mockJohnDoeCase.evaluation_date;
  const reasoning = evaluationReport?.key_reasoning || mockJohnDoeCase.key_reasoning;

  // Determine decision presentation
  const isApproved = evaluationReport 
    ? evaluationReport.decision_outcome === 'APPROVED' 
    : true;
  const isMissingDoc = evaluationReport?.decision_outcome === 'ADDITIONAL_DOCUMENTATION_REQUIRED';
  const isUnclear = evaluationReport?.decision_outcome === 'CANNOT_BE_DETERMINED';
  const isDenied = evaluationReport?.decision_outcome === 'DENIED';

  const getBannerConfig = () => {
    if (isApproved) {
      return {
        bg: '#EBF3EE',
        border: 'var(--success-border)',
        iconBg: 'var(--primary)',
        icon: <Check size={28} strokeWidth={2.8} color="#FFFFFF" />,
        title: `${procedure} is Approved`,
        subtitle: 'The clinical request meets all required policy criteria and thresholds for prior authorization.',
        badgeClass: 'badge badge-approved',
        badgeText: 'Approved'
      };
    }
    if (isMissingDoc) {
      return {
        bg: '#FEF3C7',
        border: '#FCD34D',
        iconBg: '#D97706',
        icon: <AlertTriangle size={28} strokeWidth={2.5} color="#FFFFFF" />,
        title: 'Additional Documentation Required',
        subtitle: 'Clinical evidence is missing from submitted records. Not treated as a clinical denial.',
        badgeClass: 'badge',
        badgeText: 'Documentation Needed',
        customBadgeStyle: { backgroundColor: '#FEF3C7', color: '#92400E', border: '1px solid #FCD34D' }
      };
    }
    if (isUnclear) {
      return {
        bg: '#FEF3C7',
        border: '#FCD34D',
        iconBg: '#D97706',
        icon: <AlertCircle size={28} strokeWidth={2.5} color="#FFFFFF" />,
        title: 'Authorization Cannot Be Determined',
        subtitle: 'Ambiguous or conflicting clinical notes detected. Case requires manual clinician adjudication.',
        badgeClass: 'badge',
        badgeText: 'Clinician Review Required',
        customBadgeStyle: { backgroundColor: '#FEF3C7', color: '#92400E', border: '1px solid #FCD34D' }
      };
    }
    return {
      bg: '#FDF2F2',
      border: 'var(--danger-border)',
      iconBg: 'var(--danger)',
      icon: <X size={28} strokeWidth={2.8} color="#FFFFFF" />,
      title: `${procedure} is Not Approved`,
      subtitle: 'Documented clinical evidence explicitly fails mandatory criteria or contraindication was triggered.',
      badgeClass: 'badge badge-denied',
      badgeText: 'Not Approved'
    };
  };

  const banner = getBannerConfig();

  const handleDownloadTxt = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/cases/${caseId}/export?format=txt`);
      if (res.ok) {
        const text = await res.text();
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `MedRule_Audit_${caseId}_${patientName.replace(/\s+/g, '_')}.txt`;
        a.click();
        return;
      }
    } catch (e) {
      console.warn('Backend export fetch failed, falling back to client report:', e);
    }

    // Client-side fallback report
    const reportText = `
MEDRULE PRIOR AUTHORIZATION AUDIT PACKAGE
[DEMO / SYNTHETIC CASE - NOT A CLINICAL DECISION]
==================================================
Case ID: ${caseId}
Evaluation Date: ${evalDate}
Patient: ${patientName}
Procedure: ${procedure}
Insurer: ${insurer}
Policy: ${evaluationReport?.policy_id || 'P-UHC-CT-2026'} (v${policyVersion})
Checksum: ${evaluationReport?.policy_checksum || '681f8ececb53bcac...'}
Gate Verification: ${evaluationReport?.verification_gate_verified ? 'VERIFIED (Two-Reviewer Gate Passed)' : 'DRAFT/UNVERIFIED'}

DETERMINISTIC VERDICT:
--------------------------------------------------
Verdict: ${evaluationReport?.verdict || 'APPROVED'}
Decision Outcome: ${evaluationReport?.decision_outcome || 'APPROVED'}
Verdict Statement:
${evaluationReport?.verdict_sentence || 'Approval requires all minimum clinical criteria to be met. All conditions satisfied.'}

HUMAN REVIEW REQUIREMENTS:
--------------------------------------------------
Requires Clinician Review: ${evaluationReport?.requires_human_review ? 'YES' : 'NO'}
Review Reasons:
${evaluationReport?.review_reasons?.map((r, i) => `${i + 1}. ${r}`).join('\n') || 'None - fully automated deterministic pass'}

KEY REASONING TRACE:
--------------------------------------------------
${reasoning.map((r, i) => `${i + 1}. ${r}`).join('\n')}

CRITERION EVALUATION SUMMARY:
--------------------------------------------------
${(evaluationReport?.criteria_results || mockJohnDoeCase.criteria_results).map(c => 
  `[${c.rule_id}] ${c.criterion_name} (${c.section}): ${c.ui_label}
   Requirement: ${c.requirement}
   Evidence: "${c.evidence_excerpt}" (Source Page: ${c.source_page || 'N/A'})
   Explanation: ${c.comment}
   ${c.reviewer_overridden ? `[Clinician Override by ${c.reviewer_override_by}: '${c.reviewer_override_reason}']` : ''}`
).join('\n\n')}

GOVERNANCE NOTICE:
==================================================
${evaluationReport?.governance_notice || 'DEVELOPMENT/DEMO MODE ONLY: Synthetic Patient Record. Real clinical authorization remains BLOCKED until authentic policy and sign-offs are completed.'}
==================================================
    `.trim();

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MedRule_Authorization_Report_${caseId}_${patientName.replace(/\s+/g, '_')}.txt`;
    a.click();
  };

  const handleDownloadJson = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/cases/${caseId}/export?format=json`);
      if (res.ok) {
        const jsonContent = await res.text();
        const blob = new Blob([jsonContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `MedRule_Audit_${caseId}_${patientName.replace(/\s+/g, '_')}.json`;
        a.click();
        return;
      }
    } catch (e) {
      console.warn('Backend JSON export fetch failed:', e);
    }

    const fallbackJson = {
      export_type: "MEDRULE_AUDIT_PACKAGE",
      is_synthetic_demo: true,
      case_id: caseId,
      patient_name: patientName,
      procedure: procedure,
      evaluation: evaluationReport,
      governance_notice: "DEVELOPMENT/DEMO MODE ONLY: Synthetic Clinical Record."
    };
    const blob = new Blob([JSON.stringify(fallbackJson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MedRule_Audit_${caseId}_${patientName.replace(/\s+/g, '_')}.json`;
    a.click();
  };

  return (
    <div style={{ maxWidth: '1040px' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Authorization Decision
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
          Deterministic, auditable outcome generated strictly from clinical criteria and patient evidence
        </p>
      </div>

      {/* Governance Notice Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #FCD34D',
        borderRadius: '6px',
        padding: '10px 16px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px'
      }}>
        <ShieldCheck size={18} color="#92400E" />
        <span style={{ fontSize: '12.5px', color: '#92400E' }}>
          <strong>Development/Demo Mode Only:</strong> Synthetic Patient Case ({caseId}). Real patient clinical authorizations remain BLOCKED at the Phase 2 policy verification gate.
        </span>
      </div>

      {/* Hero Decision Banner */}
      <div style={{
        backgroundColor: banner.bg,
        border: `1px solid ${banner.border}`,
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
          backgroundColor: banner.iconBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          {banner.icon}
        </div>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
            {banner.title}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            {banner.subtitle}
          </p>
        </div>
      </div>

      {/* Two-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: '24px', marginBottom: '32px' }}>
        {/* Summary Card */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '16px', color: 'var(--text-primary)' }}>
            Decision Summary
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13.5px' }}>
            <tbody>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Case ID</th>
                <td style={{ padding: '8px 0', fontWeight: '700' }}>{caseId}</td>
              </tr>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Patient</th>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{patientName}</td>
              </tr>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Procedure</th>
                <td style={{ padding: '8px 0', fontWeight: '600', color: 'var(--primary)' }}>{procedure}</td>
              </tr>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Insurer / Policy</th>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{insurer} (v{policyVersion})</td>
              </tr>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Outcome</th>
                <td style={{ padding: '8px 0' }}>
                  <span 
                    className={banner.badgeClass}
                    style={banner.customBadgeStyle}
                  >
                    {banner.badgeText}
                  </span>
                </td>
              </tr>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Evaluation Date</th>
                <td style={{ padding: '8px 0', fontWeight: '600' }}>{evalDate}</td>
              </tr>
              <tr>
                <th scope="row" style={{ textAlign: 'left', fontWeight: 'normal', padding: '8px 0', color: 'var(--text-secondary)' }}>Reviewer Sign-off</th>
                <td style={{ padding: '8px 0', fontWeight: '600', color: 'var(--success)' }}>Gate Verified (2 Reviewers)</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Key Reasoning Card */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '16px', color: 'var(--text-primary)' }}>
            Traceable Policy Reasoning
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {reasoning.map((reason, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <span style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  backgroundColor: '#EFEFEA',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '11px',
                  fontWeight: '700',
                  flexShrink: 0,
                  marginTop: '1px'
                }}>
                  {idx + 1}
                </span>
                <span style={{ fontSize: '13.5px', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                  {reason}
                </span>
              </div>
            ))}
          </div>

          {evaluationReport?.verdict_sentence && (
            <div style={{
              marginTop: '18px',
              padding: '12px 14px',
              backgroundColor: '#FAF9F6',
              borderRadius: '4px',
              border: '1px solid var(--border-subtle)',
              fontSize: '12.5px',
              lineHeight: 1.5,
              color: 'var(--text-primary)'
            }}>
              <strong>Final Verdict Statement:</strong> {evaluationReport.verdict_sentence}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleDownloadTxt}
            className="btn btn-outline"
            style={{ gap: '6px', padding: '9px 16px', fontSize: '13px' }}
            title="Download formatted text audit package"
          >
            <Download size={15} />
            <span>Export Report (.txt)</span>
          </button>
          <button
            onClick={handleDownloadJson}
            className="btn btn-outline"
            style={{ gap: '6px', padding: '9px 16px', fontSize: '13px' }}
            title="Download machine-readable JSON audit bundle"
          >
            <Download size={15} />
            <span>Export Audit (.json)</span>
          </button>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => onNavigate('criteria_evaluation')}
            className="btn btn-outline"
            style={{ padding: '9px 16px', fontSize: '13px' }}
          >
            <span>Criteria Review</span>
          </button>

          <button
            onClick={() => onNavigate('cases_history')}
            className="btn btn-outline"
            style={{ padding: '9px 16px', fontSize: '13px' }}
          >
            <span>Cases History</span>
          </button>

          <button
            onClick={() => onNavigate('new_review')}
            className="btn btn-primary"
            style={{ gap: '8px', padding: '9px 20px', fontSize: '13px' }}
          >
            <RotateCcw size={15} />
            <span>New Review</span>
          </button>
        </div>
      </div>
    </div>
  );
};
