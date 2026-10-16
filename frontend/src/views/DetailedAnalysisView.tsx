import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, Check, X, Minus, AlertCircle, AlertTriangle } from 'lucide-react';
import { ViewMode, EvaluationReport, ClinicalNoteRecord } from '../types';
import { mockJohnDoeCase } from '../mockData';

interface DetailedAnalysisViewProps {
  onNavigate: (view: ViewMode) => void;
  evaluationReport?: EvaluationReport | null;
  caseRecord?: ClinicalNoteRecord | null;
}

export const DetailedAnalysisView: React.FC<DetailedAnalysisViewProps> = ({ 
  onNavigate,
  evaluationReport,
  caseRecord
}) => {
  const [showRulebookModal, setShowRulebookModal] = useState(false);

  const criteriaRows = evaluationReport 
    ? evaluationReport.criteria_results 
    : mockJohnDoeCase.criteria_results;

  const patientName = evaluationReport?.patient_name || caseRecord?.patient_name || mockJohnDoeCase.patient_name;
  const procedure = evaluationReport?.procedure || caseRecord?.procedure_requested || mockJohnDoeCase.procedure;

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
            Detailed Criteria & Evidence Analysis
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            {patientName} &bull; {procedure} &bull; Line-by-line evidence mapping to canonical policy ruleset
          </p>
        </div>

        <button
          onClick={() => setShowRulebookModal(true)}
          className="btn btn-outline"
          style={{ gap: '8px' }}
        >
          <BookOpen size={16} color="var(--primary)" />
          <span>View Rulebook Source</span>
        </button>
      </div>

      {/* Analysis Table Card */}
      <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '32px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 18px', width: '50px', fontWeight: '600', color: 'var(--text-secondary)' }}>#</th>
              <th style={{ padding: '14px 18px', width: '180px', fontWeight: '600', color: 'var(--text-secondary)' }}>Criterion</th>
              <th style={{ padding: '14px 18px', width: '160px', fontWeight: '600', color: 'var(--text-secondary)' }}>Policy Reference</th>
              <th style={{ padding: '14px 18px', width: '240px', fontWeight: '600', color: 'var(--text-secondary)' }}>Evidence from Note</th>
              <th style={{ padding: '14px 18px', width: '100px', fontWeight: '600', color: 'var(--text-secondary)', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '14px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Evaluation Explanation</th>
            </tr>
          </thead>
          <tbody>
            {criteriaRows.map((row: any) => (
              <tr key={row.rule_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '16px 18px', color: 'var(--text-secondary)', fontWeight: '600' }}>{row.rule_id}</td>
                <td style={{ padding: '16px 18px', fontWeight: '600' }}>{row.criterion_name}</td>
                <td style={{ padding: '16px 18px' }}>
                  <div style={{ color: 'var(--primary)', fontWeight: '600' }}>{row.section}</div>
                  {row.source_page && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Page {row.source_page}</div>
                  )}
                </td>
                <td style={{ padding: '16px 18px', color: 'var(--text-primary)', fontStyle: 'italic' }}>
                  "{row.evidence_excerpt}"
                </td>
                <td style={{ padding: '16px 18px', textAlign: 'center' }}>
                  {row.status === 'MET' && (
                    <div style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--success-bg)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--success)',
                      margin: '0 auto'
                    }} title="Satisfied">
                      <Check size={16} />
                    </div>
                  )}
                  {row.status === 'NOT_MET' && (
                    <div style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--danger-bg)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--danger)',
                      margin: '0 auto'
                    }} title="Not Met">
                      <X size={16} />
                    </div>
                  )}
                  {row.status === 'NOT_DOCUMENTED' && (
                    <div style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '50%',
                      backgroundColor: '#FEF3C7',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#92400E',
                      margin: '0 auto'
                    }} title="Not Documented">
                      <AlertTriangle size={15} />
                    </div>
                  )}
                  {row.status === 'UNCLEAR_CONFLICTING' && (
                    <div style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '50%',
                      backgroundColor: '#FEF3C7',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#92400E',
                      margin: '0 auto'
                    }} title="Unclear / Review">
                      <AlertCircle size={15} />
                    </div>
                  )}
                  {row.status === 'NOT_APPLICABLE' && (
                    <div style={{
                      width: '26px',
                      height: '26px',
                      borderRadius: '50%',
                      backgroundColor: '#F3F4F6',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#4B5563',
                      margin: '0 auto'
                    }} title="Not Applicable">
                      <Minus size={15} />
                    </div>
                  )}
                </td>
                <td style={{ padding: '16px 18px', color: 'var(--text-secondary)' }}>
                  {row.comment}
                  {row.reviewer_overridden && (
                    <div style={{ marginTop: '4px', fontSize: '11px', color: '#92400E', fontWeight: '600' }}>
                      [Overridden by {row.reviewer_override_by}: {row.reviewer_override_reason}]
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => onNavigate('criteria_evaluation')}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Back to Evaluation</span>
        </button>

        <button
          onClick={() => onNavigate('authorization_decision')}
          className="btn btn-primary"
          style={{ padding: '10px 24px' }}
        >
          <span>Continue to Decision</span>
          <ArrowRight size={16} />
        </button>
      </div>

      {/* Rulebook Modal */}
      {showRulebookModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(31, 33, 30, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: '#FFFFFF',
            borderRadius: 'var(--radius-md)',
            width: '100%',
            maxWidth: '650px',
            maxHeight: '85vh',
            overflowY: 'auto',
            padding: '28px',
            boxShadow: 'var(--shadow-lg)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '700' }}>
                United Healthcare Clinical Coverage Policy (2026.1)
              </h3>
              <button
                onClick={() => setShowRulebookModal(false)}
                style={{ border: 'none', background: 'none', cursor: 'pointer' }}
              >
                <X size={20} color="var(--text-muted)" />
              </button>
            </div>
            <div style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
              <p style={{ marginBottom: '12px' }}>
                <strong>Document Authority:</strong> UHC Commercial & Medicare Advantage Guidelines §4.2 (Head / Brain Computed Tomography).
              </p>
              <p style={{ marginBottom: '12px' }}>
                <strong>Section 4.2.1:</strong> Indicated when patient presents with documented neurological deficit, persistent headaches with atypical features, or symptoms localized to central nervous system.
              </p>
              <p style={{ marginBottom: '12px' }}>
                <strong>Section 4.2.2:</strong> For chronic headaches, conservative outpatient therapy is expected for minimum duration of 6 weeks unless red flag clinical signs are present.
              </p>
              <p style={{ marginBottom: '12px' }}>
                <strong>Section 4.2.6:</strong> Intravenous contrast requires specific diagnostic justification such as evaluation of intracranial mass, neoplasm, abscess, or vascular malformation.
              </p>
            </div>
            <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowRulebookModal(false)}
                className="btn btn-primary"
              >
                Close Rulebook Source
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
