import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  X, 
  Minus, 
  AlertCircle, 
  Sparkles, 
  ShieldCheck, 
  RefreshCw, 
  Edit3, 
  AlertTriangle 
} from 'lucide-react';
import { ViewMode, ReviewCase, ClinicalNoteRecord, EvaluationReport, CriterionEvaluationResult } from '../types';
import { mockJohnDoeCase, mockJaneSmithUnmetCase, mockRobertChenMissingDocCase } from '../mockData';
import { apiFetch } from '../api/client';

interface CriteriaEvaluationViewProps {
  onNavigate: (view: ViewMode) => void;
  caseRecord?: ClinicalNoteRecord | null;
  evaluationReport?: EvaluationReport | null;
  onEvaluationReportChange?: (report: EvaluationReport | null) => void;
}

export const CriteriaEvaluationView: React.FC<CriteriaEvaluationViewProps> = ({ 
  onNavigate,
  caseRecord,
  evaluationReport,
  onEvaluationReportChange
}) => {
  const [selectedCaseId, setSelectedCaseId] = useState<'active' | '001' | '002' | '003'>(
    caseRecord ? 'active' : '001'
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string | null>(null);

  // Fallback mock case for 001, 002, 003
  const currentMockCase: ReviewCase = 
    selectedCaseId === '002' ? mockJaneSmithUnmetCase :
    selectedCaseId === '003' ? mockRobertChenMissingDocCase :
    mockJohnDoeCase;

  // Evaluate active case from server API
  const handleEvaluate = () => {
    if (selectedCaseId === 'active' && caseRecord?.case_id) {
      setLoading(true);
      setServerError(null);
      apiFetch(`http://localhost:8000/api/cases/${caseRecord.case_id}/evaluate`, {
        method: 'POST'
      })
        .then(async (res) => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Evaluation failed' }));
            throw new Error(err.detail || 'Evaluation request returned error');
          }
          return res.json();
        })
        .then((data: EvaluationReport) => {
          if (onEvaluationReportChange) {
            onEvaluationReportChange(data);
          }
          setLoading(false);
        })
        .catch((err) => {
          console.warn('Backend evaluation failed, falling back to client evaluation preview:', err);
          setServerError(err.message);
          setLoading(false);
        });
    }
  };

  useEffect(() => {
    handleEvaluate();
  }, [selectedCaseId, caseRecord?.case_id]);

  const activeReport = selectedCaseId === 'active' ? evaluationReport : null;

  const patientName = activeReport ? activeReport.patient_name : (caseRecord?.patient_name || currentMockCase.patient_name);
  const procedureName = activeReport ? activeReport.procedure : (caseRecord?.procedure_requested || currentMockCase.procedure);
  const insurerName = activeReport ? activeReport.insurer : (caseRecord?.insurance_plan || currentMockCase.insurance_plan);
  const policyId = activeReport ? `${activeReport.policy_id} v${activeReport.policy_version}` : (caseRecord?.policy_id || 'P-UHC-CT-2026 v2026.1');

  // Derive decision status badge for banner
  const getDecisionBadge = () => {
    if (activeReport) {
      if (activeReport.decision_outcome === 'APPROVED') {
        return { label: 'Approved', color: 'var(--success)', bg: 'var(--success-bg)', border: 'var(--success-border)' };
      }
      if (activeReport.decision_outcome === 'ADDITIONAL_DOCUMENTATION_REQUIRED') {
        return { label: 'Additional Documentation Required', color: 'var(--warning)', bg: 'var(--warning-bg)', border: 'var(--warning-border)' };
      }
      if (activeReport.decision_outcome === 'CANNOT_BE_DETERMINED') {
        return { label: 'Cannot Be Determined (Clinician Review Required)', color: 'var(--warning)', bg: 'var(--warning-bg)', border: 'var(--warning-border)' };
      }
      return { label: 'Not Approved', color: 'var(--danger)', bg: 'var(--danger-bg)', border: 'var(--danger-border)' };
    }

    if (selectedCaseId === '001') {
      return { label: 'Approved', color: 'var(--success)', bg: 'var(--success-bg)', border: 'var(--success-border)' };
    }
    if (selectedCaseId === '003') {
      return { label: 'Missing Documentation (Not Denied)', color: 'var(--warning)', bg: 'var(--warning-bg)', border: 'var(--warning-border)' };
    }
    return { label: 'Not Met', color: 'var(--danger)', bg: 'var(--danger-bg)', border: 'var(--danger-border)' };
  };

  const decisionBadge = getDecisionBadge();

  return (
    <div style={{ maxWidth: '1180px' }}>
      {/* Header with Case Selector */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', margin: 0 }}>
              Evidence-to-Criteria Deterministic Evaluation
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
              Phase 4 Active
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            Strict deterministic rules engine connecting Phase 3 facts to Phase 2 criteria without hallucination
          </p>
        </div>

        {/* Case Selector Pills */}
        <div style={{ display: 'flex', gap: '6px', backgroundColor: '#FAF9F6', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          {caseRecord && (
            <button
              onClick={() => setSelectedCaseId('active')}
              className={`btn ${selectedCaseId === 'active' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              Uploaded Case ({caseRecord.patient_name.split(' ')[0]})
            </button>
          )}
          <button
            onClick={() => setSelectedCaseId('001')}
            className={`btn ${selectedCaseId === '001' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Case 001 (Approved)
          </button>
          <button
            onClick={() => setSelectedCaseId('002')}
            className={`btn ${selectedCaseId === '002' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Case 002 (Not Met)
          </button>
          <button
            onClick={() => setSelectedCaseId('003')}
            className={`btn ${selectedCaseId === '003' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Case 003 (Missing Doc)
          </button>
        </div>
      </div>

      {/* Governance & Verification Gate Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #FCD34D',
        borderRadius: '6px',
        padding: '10px 16px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={18} color="#92400E" />
          <span style={{ fontSize: '12.5px', color: '#92400E' }}>
            <strong>Phase 2 Verification Gate Enforced:</strong> Production clinical authorization remains BLOCKED until authentic policy and clinical reviewer sign-offs are completed. Running in verified demo mode.
          </span>
        </div>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#92400E' }}>
            <RefreshCw size={14} className="animate-spin" />
            <span>Evaluating...</span>
          </div>
        )}
      </div>

      {serverError && (
        <div style={{
          backgroundColor: '#FEE2E2',
          border: '1px solid #FCA5A5',
          borderRadius: '6px',
          padding: '10px 16px',
          marginBottom: '16px',
          color: '#991B1B',
          fontSize: '12.5px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>Notice: {serverError}. Displaying cached evaluation record.</span>
          </div>
          <button
            onClick={handleEvaluate}
            className="btn btn-outline"
            style={{
              padding: '3px 10px',
              fontSize: '11px',
              borderColor: '#FCA5A5',
              color: '#991B1B',
              backgroundColor: '#FFFFFF',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Patient & Request Banner */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: '20px', backgroundColor: '#FAF9F6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Patient Record:</span>
          <div style={{ fontSize: '16px', fontWeight: '700' }}>
            {patientName} {caseRecord?.patient_age ? `(${caseRecord.patient_age}y / ${caseRecord.gender || 'M'})` : ''}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Case ID: <strong>{activeReport?.case_id || caseRecord?.case_id || currentMockCase.id}</strong> &bull; Facility: {caseRecord?.facility || currentMockCase.facility}
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Procedure & Policy:</span>
          <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--primary)' }}>{procedureName}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {insurerName} &bull; Policy: {policyId}
          </div>
          <div style={{ marginTop: '4px' }}>
            <span style={{
              display: 'inline-block',
              padding: '2px 8px',
              borderRadius: '9999px',
              fontSize: '11px',
              fontWeight: '700',
              backgroundColor: decisionBadge.bg,
              color: decisionBadge.color,
              border: `1px solid ${decisionBadge.border}`
            }}>
              Outcome: {decisionBadge.label}
            </span>
          </div>
        </div>
      </div>

      {/* Evaluation Table Card */}
      <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '12px 16px', width: '90px', fontWeight: '600', color: 'var(--text-secondary)' }}>Rule ID</th>
              <th style={{ padding: '12px 16px', width: '220px', fontWeight: '600', color: 'var(--text-secondary)' }}>Criterion & Policy Citation</th>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Policy Requirement</th>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Clinical Evidence / Excerpt</th>
              <th style={{ padding: '12px 16px', width: '170px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ padding: '36px 16px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  <RefreshCw size={22} className="animate-spin" style={{ margin: '0 auto 8px', display: 'block', color: 'var(--primary)' }} />
                  <div style={{ fontWeight: '600', fontSize: '13px' }}>Evaluating Clinical Evidence Against Policy Criteria...</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>Executing deterministic logic rules without LLM hallucination</div>
                </td>
              </tr>
            ) : (activeReport ? activeReport.criteria_results : currentMockCase.criteria_results).length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <AlertCircle size={24} style={{ margin: '0 auto 8px', display: 'block', color: 'var(--text-muted)' }} />
                  <div>No criteria found for this policy or evaluation has not been executed yet.</div>
                  <button onClick={handleEvaluate} className="btn btn-outline" style={{ marginTop: '12px', fontSize: '12px' }}>
                    Run Deterministic Evaluation
                  </button>
                </td>
              </tr>
            ) : (
              (activeReport ? activeReport.criteria_results : currentMockCase.criteria_results).map((row: any) => (
              <tr key={row.rule_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                {/* Rule ID */}
                <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', fontWeight: '600' }}>
                  {row.rule_id}
                </td>

                {/* Criterion & Policy Citation */}
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ fontWeight: '700', color: 'var(--text-primary)' }}>{row.criterion_name}</div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '4px', fontSize: '11px', color: 'var(--text-secondary)', backgroundColor: '#EFEFEA', padding: '2px 6px', borderRadius: '4px' }}>
                    <span>{row.section}</span>
                    {row.source_page && <span>&bull; Page {row.source_page}</span>}
                  </div>
                  {row.policy_citation && (
                    <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {row.policy_citation}
                    </div>
                  )}
                </td>

                {/* Policy Requirement */}
                <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                  {row.requirement}
                  {row.plain_english_rationale && (
                    <div style={{ marginTop: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
                      Plain English: {row.plain_english_rationale}
                    </div>
                  )}
                </td>

                {/* Clinical Evidence Found */}
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ color: 'var(--text-primary)', fontStyle: 'italic', marginBottom: '4px' }}>
                    "{row.evidence_excerpt}"
                  </div>

                  {row.reviewer_overridden && (
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#FEF3C7',
                      color: '#92400E',
                      fontSize: '11px',
                      fontWeight: '600',
                      marginBottom: '4px'
                    }}>
                      <Edit3 size={11} />
                      <span>Reviewer Override ({row.reviewer_override_by})</span>
                    </div>
                  )}

                  {row.comment && (
                    <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                      {row.comment}
                    </div>
                  )}
                </td>

                {/* Status Column */}
                <td style={{ padding: '14px 16px' }}>
                  {row.status === 'MET' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '9999px',
                      backgroundColor: 'var(--success-bg)',
                      color: 'var(--success)',
                      border: '1px solid var(--success-border)',
                      fontSize: '12px',
                      fontWeight: '700'
                    }}>
                      <Check size={13} />
                      <span>Satisfied</span>
                    </span>
                  )}

                  {row.status === 'NOT_MET' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '9999px',
                      backgroundColor: 'var(--danger-bg)',
                      color: 'var(--danger)',
                      border: '1px solid var(--danger-border)',
                      fontSize: '12px',
                      fontWeight: '700'
                    }}>
                      <X size={13} />
                      <span>{row.is_exclusion ? 'Exclusion' : 'Not met'}</span>
                    </span>
                  )}

                  {row.status === 'NOT_DOCUMENTED' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '9999px',
                      backgroundColor: '#FEF3C7',
                      color: '#92400E',
                      border: '1px solid #FCD34D',
                      fontSize: '12px',
                      fontWeight: '700'
                    }}>
                      <AlertTriangle size={13} />
                      <span>Not documented</span>
                    </span>
                  )}

                  {row.status === 'UNCLEAR_CONFLICTING' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '9999px',
                      backgroundColor: '#FEF3C7',
                      color: '#92400E',
                      border: '1px solid #FCD34D',
                      fontSize: '12px',
                      fontWeight: '700'
                    }}>
                      <AlertCircle size={13} />
                      <span>Unclear / Review</span>
                    </span>
                  )}

                  {row.status === 'NOT_APPLICABLE' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '9999px',
                      backgroundColor: '#F3F4F6',
                      color: '#4B5563',
                      border: '1px solid #E5E7EB',
                      fontSize: '12px',
                      fontWeight: '600'
                    }}>
                      <Minus size={13} />
                      <span>Not applicable</span>
                    </span>
                  )}
                </td>
              </tr>
            )))}
          </tbody>
        </table>
      </div>

      {/* Key Reasoning Box (Strictly Precedes Verdict) */}
      <div className="card" style={{ padding: '20px', marginBottom: '28px', backgroundColor: '#FAF9F6' }}>
        <h3 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="var(--primary)" />
          Clinical Evidence & Policy Reasoning Trace
        </h3>
        <ul style={{ paddingLeft: '20px', margin: '0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {(activeReport ? activeReport.key_reasoning : currentMockCase.key_reasoning).map((bullet: string, idx: number) => (
            <li key={idx} style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {bullet}
            </li>
          ))}
        </ul>

        {activeReport?.verdict_sentence && (
          <div style={{
            marginTop: '16px',
            padding: '12px 16px',
            borderRadius: '4px',
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--border-subtle)',
            fontSize: '13px',
            fontWeight: '600',
            color: 'var(--text-primary)'
          }}>
            <strong>Deterministic Verdict Sentence:</strong> {activeReport.verdict_sentence}
          </div>
        )}

        {(selectedCaseId === '003' || activeReport?.decision_outcome === 'ADDITIONAL_DOCUMENTATION_REQUIRED') && (
          <div style={{
            marginTop: '12px',
            padding: '10px 14px',
            borderRadius: '4px',
            backgroundColor: '#FEF3C7',
            border: '1px solid #FCD34D',
            color: '#92400E',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={15} />
            <span>
              <strong>Clinical Governance Rule:</strong> Absence of documentation is NOT treated as a clinical denial. 
              The case status is held as "Additional Documentation Required" pending submission of clinical records.
            </span>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => onNavigate('extracted_info')}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Back to Fact Review</span>
        </button>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => onNavigate('detailed_analysis')}
            className="btn btn-outline"
          >
            <span>Detailed Analysis</span>
          </button>
          <button
            onClick={() => onNavigate('authorization_decision')}
            className="btn btn-primary"
            style={{ padding: '10px 24px' }}
          >
            <span>Proceed to Decision</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
