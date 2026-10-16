import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, X, Minus, AlertCircle, FileText, Sparkles, HelpCircle } from 'lucide-react';
import { ViewMode, ReviewCase } from '../types';
import { mockJohnDoeCase, mockJaneSmithUnmetCase, mockRobertChenMissingDocCase } from '../mockData';

interface CriteriaEvaluationViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const CriteriaEvaluationView: React.FC<CriteriaEvaluationViewProps> = ({ onNavigate }) => {
  const [selectedCaseId, setSelectedCaseId] = useState<'001' | '002' | '003'>('001');

  const currentCase: ReviewCase = 
    selectedCaseId === '001' ? mockJohnDoeCase :
    selectedCaseId === '002' ? mockJaneSmithUnmetCase :
    mockRobertChenMissingDocCase;

  return (
    <div style={{ maxWidth: '1180px' }}>
      {/* Header with Case Selector */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '24px'
      }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
            Policy Criteria Evaluation
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Deterministic rule-level evaluation against United Healthcare CT Scan Policy (CP.MP.107 / UHC-CT-2026)
          </p>
        </div>

        {/* Case Selector Pills */}
        <div style={{ display: 'flex', gap: '8px', backgroundColor: '#FAF9F6', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
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

      {/* Patient & Request Banner */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: '20px', backgroundColor: '#FAF9F6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Patient Record:</span>
          <div style={{ fontSize: '16px', fontWeight: '700' }}>{currentCase.patient_name} ({currentCase.patient_age}y / {currentCase.gender})</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>DOB: {currentCase.dob} &bull; Facility: {currentCase.facility}</div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Procedure Requested:</span>
          <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--primary)' }}>{currentCase.procedure}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Insurer: {currentCase.insurance_plan} &bull; Policy v{currentCase.policy_version}</div>
        </div>
      </div>

      {/* Evaluation Table Card */}
      <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 18px', width: '45px', fontWeight: '600', color: 'var(--text-secondary)' }}>#</th>
              <th style={{ padding: '14px 18px', width: '220px', fontWeight: '600', color: 'var(--text-secondary)' }}>Condition / Citation</th>
              <th style={{ padding: '14px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Policy Requirement</th>
              <th style={{ padding: '14px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Clinical Evidence Found</th>
              <th style={{ padding: '14px 18px', width: '160px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {currentCase.criteria_results.map((row) => (
              <tr key={row.rule_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '16px 18px', color: 'var(--text-secondary)', fontWeight: '600' }}>{row.rule_id}</td>
                
                <td style={{ padding: '16px 18px' }}>
                  <div style={{ fontWeight: '700', color: 'var(--text-primary)' }}>{row.criterion_name}</div>
                  <div style={{ display: 'inline-block', marginTop: '4px', fontSize: '11px', color: 'var(--text-secondary)', backgroundColor: '#EFEFEA', padding: '2px 6px', borderRadius: '4px' }}>
                    {row.section} {row.source_page ? `(p. ${row.source_page})` : ''}
                  </div>
                </td>

                <td style={{ padding: '16px 18px', color: 'var(--text-secondary)', fontSize: '13px' }}>
                  {row.requirement}
                </td>

                <td style={{ padding: '16px 18px' }}>
                  <div style={{ color: 'var(--text-primary)', fontStyle: 'italic', marginBottom: '4px' }}>
                    "{row.evidence_excerpt}"
                  </div>
                  {row.comment && (
                    <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                      {row.comment}
                    </div>
                  )}
                </td>

                <td style={{ padding: '16px 18px' }}>
                  {row.status === 'MET' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 12px',
                      borderRadius: '9999px',
                      backgroundColor: 'var(--success-bg)',
                      color: 'var(--success)',
                      border: '1px solid var(--success-border)',
                      fontSize: '12.5px',
                      fontWeight: '700'
                    }}>
                      <Check size={14} />
                      <span>Satisfied</span>
                    </span>
                  )}

                  {row.status === 'NOT_MET' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 12px',
                      borderRadius: '9999px',
                      backgroundColor: 'var(--danger-bg)',
                      color: 'var(--danger)',
                      border: '1px solid var(--danger-border)',
                      fontSize: '12.5px',
                      fontWeight: '700'
                    }}>
                      <X size={14} />
                      <span>Not met</span>
                    </span>
                  )}

                  {row.status === 'NOT_DOCUMENTED' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 12px',
                      borderRadius: '9999px',
                      backgroundColor: 'var(--danger-bg)',
                      color: 'var(--danger)',
                      border: '1px solid var(--danger-border)',
                      fontSize: '12.5px',
                      fontWeight: '700'
                    }}>
                      <X size={14} />
                      <span>Not documented</span>
                    </span>
                  )}

                  {row.status === 'NOT_APPLICABLE' && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 12px',
                      borderRadius: '9999px',
                      backgroundColor: '#F3F4F6',
                      color: '#4B5563',
                      border: '1px solid #E5E7EB',
                      fontSize: '12.5px',
                      fontWeight: '600'
                    }}>
                      <Minus size={14} />
                      <span>Not applicable</span>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Key Reasoning Box (Strictly Precedes Verdict) */}
      <div className="card" style={{ padding: '20px', marginBottom: '32px', backgroundColor: '#FAF9F6' }}>
        <h3 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="var(--primary)" />
          Clinical Evidence & Policy Reasoning Summary
        </h3>
        <ul style={{ paddingLeft: '20px', margin: '0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {currentCase.key_reasoning.map((bullet, idx) => (
            <li key={idx} style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {bullet}
            </li>
          ))}
        </ul>

        {selectedCaseId === '003' && (
          <div style={{
            marginTop: '12px',
            padding: '10px 14px',
            borderRadius: '4px',
            backgroundColor: 'var(--warning-bg)',
            border: '1px solid var(--warning-border)',
            color: 'var(--warning)',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={15} />
            <span>
              <strong>Clinical Governance Rule:</strong> Absence of documentation is NOT treated as a clinical failure. 
              The case status is held in review pending submission of prior conservative treatment records.
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
          <span>Back</span>
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
