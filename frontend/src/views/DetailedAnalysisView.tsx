import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, Check, X } from 'lucide-react';
import { ViewMode } from '../types';
import { mockJohnDoeCase } from '../mockData';

interface DetailedAnalysisViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const DetailedAnalysisView: React.FC<DetailedAnalysisViewProps> = ({ onNavigate }) => {
  const [showRulebookModal, setShowRulebookModal] = useState(false);

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px'
      }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
            Detailed Analysis
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Complete evaluation with rulebook references and evidence
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
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 18px', width: '40px', fontWeight: '600', color: 'var(--text-secondary)' }}>#</th>
              <th style={{ padding: '14px 18px', width: '180px', fontWeight: '600', color: 'var(--text-secondary)' }}>Criterion</th>
              <th style={{ padding: '14px 18px', width: '140px', fontWeight: '600', color: 'var(--text-secondary)' }}>Policy Reference</th>
              <th style={{ padding: '14px 18px', width: '220px', fontWeight: '600', color: 'var(--text-secondary)' }}>Evidence from Note</th>
              <th style={{ padding: '14px 18px', width: '80px', fontWeight: '600', color: 'var(--text-secondary)', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '14px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Comments</th>
            </tr>
          </thead>
          <tbody>
            {mockJohnDoeCase.criteria_results.map((row) => (
              <tr key={row.rule_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '16px 18px', color: 'var(--text-secondary)' }}>{row.rule_id}</td>
                <td style={{ padding: '16px 18px', fontWeight: '600' }}>{row.criterion_name}</td>
                <td style={{ padding: '16px 18px', color: 'var(--primary)', fontWeight: '600' }}>{row.section}</td>
                <td style={{ padding: '16px 18px', color: 'var(--text-primary)' }}>{row.evidence_excerpt}</td>
                <td style={{ padding: '16px 18px', textAlign: 'center' }}>
                  <div style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--success-bg)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--success)'
                  }}>
                    <Check size={15} />
                  </div>
                </td>
                <td style={{ padding: '16px 18px', color: 'var(--text-secondary)' }}>{row.comment}</td>
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
          <span>Back</span>
        </button>

        <button
          onClick={() => onNavigate('authorization_decision')}
          className="btn btn-primary"
          style={{ padding: '10px 24px' }}
        >
          <span>Continue</span>
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
