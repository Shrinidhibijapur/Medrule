import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileUp,
  ChevronDown,
  Check,
  AlertTriangle,
  FileText,
  ShieldAlert,
  Loader2,
  RefreshCw,
  Sparkles,
  Info
} from 'lucide-react';
import { ViewMode, ClinicalNoteRecord } from '../types';
import { apiFetch } from '../api/client';

interface NewReviewViewProps {
  onNavigate?: (view: ViewMode) => void;
  onSelectCaseRecord: (record: ClinicalNoteRecord) => void;
  activeCaseRecord: ClinicalNoteRecord | null;
}

export const NewReviewView: React.FC<NewReviewViewProps> = ({
  onNavigate,
  onSelectCaseRecord,
  activeCaseRecord,
}) => {
  const navigate = useNavigate();
  const [selectedPlan, setSelectedPlan] = useState('United Healthcare');
  const [selectedProcedure, setSelectedProcedure] = useState('CT Scan of Head with Contrast');
  const [selectedPolicyId, setSelectedPolicyId] = useState('P-UHC-CT-2026');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Invalid file format. MedRule accepts only valid PDF clinical documents.');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setUploadError('File exceeds 15MB limit.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('policy_id', selectedPolicyId);
    formData.append('procedure_requested', selectedProcedure);
    formData.append('insurance_plan', selectedPlan);

    try {
      const response = await apiFetch('http://localhost:8000/api/notes/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errData.detail || `Upload failed with HTTP ${response.status}`);
      }

      const record: ClinicalNoteRecord = await response.json();
      onSelectCaseRecord(record);
      setUploadSuccess(`Note processed successfully: ${record.patient_name} (${record.total_pages} pages, quality: ${record.overall_quality})`);
    } catch (err: any) {
      setUploadError(err.message || 'Network error processing clinical note.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleLoadDemoCase = async (demoKey: 'case_001' | 'case_scanned' | 'case_conflicting') => {
    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      if (demoKey === 'case_001') {
        const resp = await apiFetch('http://localhost:8000/api/notes/CASE-2026-001');
        if (resp.ok) {
          const rec: ClinicalNoteRecord = await resp.json();
          onSelectCaseRecord(rec);
          setUploadSuccess(`Loaded Synthetic Demo: ${rec.patient_name} (Encounter: ${rec.facility})`);
          setIsUploading(false);
          return;
        }
      }

      // If backend note endpoint doesn't have it yet, query list or generate synthetic record
      const respAll = await apiFetch('http://localhost:8000/api/cases');
      if (respAll.ok) {
        const cases: ClinicalNoteRecord[] = await respAll.json();
        if (cases && cases.length > 0) {
          onSelectCaseRecord(cases[0]);
          setUploadSuccess(`Loaded case: ${cases[0].patient_name} (${cases[0].case_id})`);
          setIsUploading(false);
          return;
        }
      }

      throw new Error('Could not load demo case from server.');
    } catch (err: any) {
      setUploadError('Failed to load demo case: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={{ maxWidth: '980px' }}>
      {/* Governance Restriction Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #F59E0B',
        borderRadius: 'var(--radius-md)',
        padding: '14px 18px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        <ShieldAlert size={20} color="#B45309" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong style={{ fontSize: '13px', color: '#92400E', display: 'block', marginBottom: '2px' }}>
            DEVELOPMENT / DEMO MODE ONLY — PRODUCTION CLINICAL GATE BLOCKED
          </strong>
          <p style={{ fontSize: '12px', color: '#78350F', margin: 0, lineHeight: 1.4 }}>
            Doctor's note parsing and fact extraction operate on synthetic patient test records. Real-patient authorization remains blocked until authentic insurer policy rulebooks and authorized clinical reviewer sign-offs are in place.
          </p>
        </div>
      </div>

      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          New Authorization Review
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Upload clinical encounter notes to extract evidence facts and perform policy rule matching
        </p>
      </div>

      {/* Stepper */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '40px',
        margin: '28px 0 36px'
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
          <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>Upload Note</span>
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
          <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>Review Document</span>
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
          <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>Extract & Audit Facts</span>
        </div>
      </div>

      {/* Preset Synthetic Demo Cases Section */}
      <div style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px 24px',
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <Sparkles size={18} color="var(--primary)" />
          <h3 style={{ fontSize: '15px', fontWeight: '700', margin: 0 }}>
            Instant Synthetic Demo Scenarios (No File Needed)
          </h3>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Select a verified synthetic clinical case to demo Phase 3 extraction, page citations, and contradiction detection:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
          <button
            onClick={() => handleLoadDemoCase('case_001')}
            disabled={isUploading}
            style={{
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              backgroundColor: '#FAF9F6',
              textAlign: 'left',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '700', fontSize: '14px', color: '#1F211E' }}>John Doe (Riverside)</span>
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#315B45', backgroundColor: '#EBF3EE', padding: '2px 8px', borderRadius: '4px' }}>
                Full Evidence
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Headache 12 weeks, abnormal exam, CT Head with contrast
            </span>
          </button>

          <button
            onClick={() => handleLoadDemoCase('case_001')}
            disabled={isUploading}
            style={{
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              backgroundColor: '#FAF9F6',
              textAlign: 'left',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '700', fontSize: '14px', color: '#1F211E' }}>Clinical Note Archive</span>
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#854D0E', backgroundColor: '#FEF9C3', padding: '2px 8px', borderRadius: '4px' }}>
                Audit Ready
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              View previously ingested cases and reviewer audit trails
            </span>
          </button>
        </div>
      </div>

      {/* Upload Box */}
      <div style={{
        border: '2px dashed var(--border-strong)',
        borderRadius: 'var(--radius-lg)',
        padding: '44px 30px',
        textAlign: 'center',
        backgroundColor: '#FFFFFF',
        marginBottom: '24px',
        position: 'relative'
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
          {isUploading ? (
            <Loader2 size={28} color="var(--primary)" className="animate-spin" />
          ) : (
            <FileUp size={28} color="var(--primary)" />
          )}
        </div>

        <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '6px' }}>
          Upload Doctor's Notes (PDF)
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '6px' }}>
          Secure clinical document ingestion: verifies SHA-256, isolates untrusted text, and detects scanned pages
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '20px' }}>
          Format: PDF documents only &bull; Max size: 15MB
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <label className="btn btn-primary" style={{ cursor: isUploading ? 'not-allowed' : 'pointer' }}>
            {isUploading ? 'Extracting Facts...' : 'Choose Clinical Note PDF'}
            <input
              type="file"
              accept=".pdf"
              disabled={isUploading}
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  void handleFileUpload(e.target.files[0]);
                }
              }}
            />
          </label>
        </div>

        {uploadError && (
          <div style={{
            marginTop: '18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            backgroundColor: '#FEE2E2',
            color: '#991B1B',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            fontWeight: '600'
          }}>
            <AlertTriangle size={16} />
            <span>{uploadError}</span>
          </div>
        )}

        {uploadSuccess && (
          <div style={{
            marginTop: '18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            backgroundColor: '#EBF3EE',
            color: '#315B45',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            fontWeight: '600'
          }}>
            <Check size={16} />
            <span>{uploadSuccess}</span>
          </div>
        )}
      </div>

      {/* Target Policy & Procedure Form */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '20px',
        marginBottom: '32px'
      }}>
        <div>
          <label htmlFor="new-review-policy-select" style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
            Applicable Policy Rulebook
          </label>
          <div style={{ position: 'relative' }}>
            <select
              id="new-review-policy-select"
              value={selectedPolicyId}
              onChange={(e) => setSelectedPolicyId(e.target.value)}
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
              <option value="P-UHC-CT-2026">United Healthcare - Head CT Clinical Guideline (2026.1)</option>
              <option value="POL-CIGN-CTS-2026-1">Cigna - CT Sinus Coverage Policy (2026.1)</option>
              <option value="CP.MP.107">Centene - CP.MP.107 Durable Medical Equipment</option>
            </select>
            <ChevronDown size={18} color="var(--text-muted)" style={{ position: 'absolute', right: '14px', top: '14px', pointerEvents: 'none' }} />
          </div>
        </div>

        <div>
          <label htmlFor="new-review-procedure-select" style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
            Procedure Requested
          </label>
          <div style={{ position: 'relative' }}>
            <select
              id="new-review-procedure-select"
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
              <option value="CT Scan of Head without Contrast">CT Scan of Head without Contrast (CPT 70450)</option>
              <option value="MRI Brain without Contrast">MRI Brain without Contrast (CPT 70551)</option>
            </select>
            <ChevronDown size={18} color="var(--text-muted)" style={{ position: 'absolute', right: '14px', top: '14px', pointerEvents: 'none' }} />
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => handleLoadDemoCase('case_001')}
          className="btn btn-outline"
          disabled={isUploading}
        >
          <RefreshCw size={15} style={{ marginRight: '6px' }} />
          <span>Reset to John Doe Test Case</span>
        </button>

        <button
          onClick={() => {
            const targetCaseId = activeCaseRecord?.case_id || 'CASE-2026-001';
            navigate(`/cases/${targetCaseId}/document`);
            if (onNavigate) onNavigate('extracted_doc');
          }}
          className="btn btn-primary"
          style={{ padding: '12px 28px', fontSize: '15px' }}
        >
          <span>Proceed to Document Review →</span>
        </button>
      </div>
    </div>
  );
};
