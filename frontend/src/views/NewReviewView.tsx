import React, { useState } from 'react';
import { FileUp, ChevronDown, Check, Sparkles } from 'lucide-react';
import { ViewMode } from '../types';

interface NewReviewViewProps {
  onNavigate: (view: ViewMode) => void;
  onFileSelect?: (file: File | null) => void;
}

export const NewReviewView: React.FC<NewReviewViewProps> = ({ onNavigate }) => {
  const [selectedPlan, setSelectedPlan] = useState('United Healthcare');
  const [selectedProcedure, setSelectedProcedure] = useState('CT Scan of Head with Contrast');
  const [uploadedFileName, setUploadedFileName] = useState<string | null>('John_Doe_Clinical_Note_Riverside.pdf');

  const handleProceed = () => {
    onNavigate('extracted_doc');
  };

  return (
    <div style={{ maxWidth: '900px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          New Authorization Review
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Upload doctor's notes and select the procedure to check authorization
        </p>
      </div>

      {/* Stepper */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '40px',
        margin: '32px 0 40px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            backgroundColor: 'var(--primary)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            fontWeight: '700'
          }}>1</div>
          <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>Upload Documents</span>
        </div>

        <div style={{ width: '40px', height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', opacity: 0.6 }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            border: '1px solid var(--border-strong)',
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            fontWeight: '600'
          }}>2</div>
          <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>Review Details</span>
        </div>

        <div style={{ width: '40px', height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', opacity: 0.6 }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            border: '1px solid var(--border-strong)',
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            fontWeight: '600'
          }}>3</div>
          <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>Get Results</span>
        </div>
      </div>

      {/* Upload Box */}
      <div style={{
        border: '2px dashed var(--border-strong)',
        borderRadius: 'var(--radius-lg)',
        padding: '50px 30px',
        textAlign: 'center',
        backgroundColor: '#FFFFFF',
        marginBottom: '32px'
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          margin: '0 auto 16px',
          borderRadius: '50%',
          backgroundColor: 'var(--bg-surface-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <FileUp size={28} color="var(--primary)" />
        </div>
        <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '6px' }}>Upload Doctor's Notes</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '6px' }}>
          Drag and drop files here or click to browse
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '20px' }}>
          Supports PDF, JPG, PNG (Max 10MB)
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
            Choose Files
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setUploadedFileName(e.target.files[0].name);
                }
              }}
            />
          </label>
        </div>

        {uploadedFileName && (
          <div style={{
            marginTop: '20px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            backgroundColor: 'var(--success-bg)',
            color: 'var(--success)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            fontWeight: '600'
          }}>
            <Check size={16} />
            <span>Ready: {uploadedFileName}</span>
          </div>
        )}
      </div>

      {/* Select Insurance Plan & Procedure Form */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '32px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
            Select Insurance Plan
          </label>
          <div style={{ position: 'relative' }}>
            <select
              value={selectedPlan}
              onChange={(e) => setSelectedPlan(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: '#FFFFFF',
                fontSize: '14px',
                appearance: 'none',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="United Healthcare">United Healthcare (Policy Version 2026)</option>
              <option value="Aetna">Aetna (Policy Version 2026)</option>
              <option value="BCBS">Blue Cross Blue Shield (Policy Version 2026)</option>
              <option value="Cigna">Cigna (Policy Version 2026)</option>
            </select>
            <ChevronDown size={18} color="var(--text-muted)" style={{ position: 'absolute', right: '14px', top: '14px', pointerEvents: 'none' }} />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
            Procedure Requested
          </label>
          <div style={{ position: 'relative' }}>
            <select
              value={selectedProcedure}
              onChange={(e) => setSelectedProcedure(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: '#FFFFFF',
                fontSize: '14px',
                appearance: 'none',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="CT Scan of Head with Contrast">CT Scan of Head with Contrast (CPT 70460)</option>
              <option value="MRI Lumbar Spine">MRI Lumbar Spine (CPT 72148)</option>
              <option value="CT Sinus">CT Sinus without Contrast (CPT 70486)</option>
            </select>
            <ChevronDown size={18} color="var(--text-muted)" style={{ position: 'absolute', right: '14px', top: '14px', pointerEvents: 'none' }} />
          </div>
        </div>
      </div>

      {/* Action footer */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
        <button
          onClick={handleProceed}
          className="btn btn-primary"
          style={{ padding: '12px 28px', fontSize: '15px' }}
        >
          Proceed to Document Review →
        </button>
      </div>
    </div>
  );
};
