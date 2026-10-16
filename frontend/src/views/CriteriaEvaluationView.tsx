import React from 'react';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { ViewMode } from '../types';
import { mockJohnDoeCase } from '../mockData';

interface CriteriaEvaluationViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const CriteriaEvaluationView: React.FC<CriteriaEvaluationViewProps> = ({ onNavigate }) => {
  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Policy Criteria Evaluation
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          CT Scan - United Healthcare (Policy Version 2026)
        </p>
      </div>

      {/* Evaluation Table Card */}
      <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '32px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 20px', width: '50px', fontWeight: '600', color: 'var(--text-secondary)' }}>#</th>
              <th style={{ padding: '14px 20px', width: '220px', fontWeight: '600', color: 'var(--text-secondary)' }}>Criterion / Condition</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Requirement</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Evidence Found</th>
              <th style={{ padding: '14px 20px', width: '140px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {mockJohnDoeCase.criteria_results.map((row) => (
              <tr key={row.rule_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>{row.rule_id}</td>
                <td style={{ padding: '16px 20px', fontWeight: '600' }}>{row.criterion_name}</td>
                <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>{row.requirement}</td>
                <td style={{ padding: '16px 20px', color: 'var(--text-primary)' }}>{row.evidence_excerpt}</td>
                <td style={{ padding: '16px 20px' }}>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 12px',
                    borderRadius: '9999px',
                    backgroundColor: row.status === 'MET' ? 'var(--success-bg)' : 'var(--danger-bg)',
                    color: row.status === 'MET' ? 'var(--success)' : 'var(--danger)',
                    border: `1px solid ${row.status === 'MET' ? 'var(--success-border)' : 'var(--danger-border)'}`,
                    fontSize: '13px',
                    fontWeight: '600'
                  }}>
                    <Check size={14} />
                    <span>Satisfied</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
