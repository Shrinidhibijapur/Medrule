import React from 'react';
import { ArrowLeft, ArrowRight, User, Stethoscope } from 'lucide-react';
import { ViewMode } from '../types';

interface ExtractedInfoViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const ExtractedInfoView: React.FC<ExtractedInfoViewProps> = ({ onNavigate }) => {
  return (
    <div style={{ maxWidth: '900px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Extracted Information
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Key information identified from the doctor's notes
        </p>
      </div>

      {/* Patient Information Card */}
      <div className="card" style={{ marginBottom: '24px', padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          backgroundColor: '#FAF9F6'
        }}>
          <User size={18} color="var(--primary)" />
          <h2 style={{ fontSize: '15px', fontWeight: '700' }}>Patient Information</h2>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', width: '220px', color: 'var(--text-secondary)' }}>Name</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>John Doe</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Age</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>42 years</td>
            </tr>
            <tr>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Relevant History</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>Hypertension</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Clinical Information Card */}
      <div className="card" style={{ marginBottom: '32px', padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          backgroundColor: '#FAF9F6'
        }}>
          <Stethoscope size={18} color="var(--primary)" />
          <h2 style={{ fontSize: '15px', fontWeight: '700' }}>Clinical Information</h2>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', width: '220px', color: 'var(--text-secondary)' }}>Primary Complaint</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>Recurrent severe headaches, dizziness</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Duration</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>3 months</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Associated Symptoms</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>Visual disturbances</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Previous Treatment</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>Conservative treatment (no improvement)</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Clinical Findings</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>Neurological examination abnormal</td>
            </tr>
            <tr>
              <td style={{ padding: '14px 24px', color: 'var(--text-secondary)' }}>Physician Recommendation</td>
              <td style={{ padding: '14px 24px', fontWeight: '600' }}>CT scan of head with contrast</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => onNavigate('extracted_doc')}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Back</span>
        </button>

        <button
          onClick={() => onNavigate('criteria_evaluation')}
          className="btn btn-primary"
          style={{ padding: '10px 24px' }}
        >
          <span>Continue</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
};
