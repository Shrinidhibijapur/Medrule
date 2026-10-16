import React, { useState } from 'react';
import {
  Minus,
  Plus,
  Maximize2,
  ArrowLeft,
  ArrowRight,
  FileText,
  ShieldAlert,
  AlertTriangle,
  Eye,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import { ViewMode, ClinicalNoteRecord } from '../types';

interface ExtractedDocumentViewProps {
  onNavigate: (view: ViewMode) => void;
  caseRecord: ClinicalNoteRecord | null;
}

export const ExtractedDocumentView: React.FC<ExtractedDocumentViewProps> = ({
  onNavigate,
  caseRecord,
}) => {
  const [activePage, setActivePage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [viewMode, setViewMode] = useState<'pdf' | 'text'>('pdf');

  const record = caseRecord;
  const caseId = record?.case_id || 'CASE-2026-001';
  const totalPages = record?.total_pages || 3;
  const isScanned = record?.overall_quality === 'LOW_NEEDS_OCR';

  const pagesArray = Array.from({ length: totalPages }, (_, i) => i + 1);

  const documentPdfUrl = `http://localhost:8000/api/notes/${caseId}/document`;

  // Get raw text for active page if available
  const activePageData = record?.raw_pages_text?.find(p => p.page_number === activePage);

  return (
    <div style={{ maxWidth: '1180px' }}>
      {/* Governance Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #F59E0B',
        borderRadius: 'var(--radius-md)',
        padding: '12px 16px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldAlert size={18} color="#B45309" />
          <span style={{ fontSize: '13px', fontWeight: '600', color: '#92400E' }}>
            DEMO MODE: Synthetic Patient Clinical Document ({record?.patient_name || 'John Doe'})
          </span>
        </div>
        <span style={{ fontSize: '11px', color: '#78350F', fontWeight: '600' }}>
          SHA-256: {record?.sha256_checksum ? record.sha256_checksum.slice(0, 16) + '...' : 'Verified'}
        </span>
      </div>

      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px'
      }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
            Extracted Clinical Document
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Original uploaded physician encounter notes with page citation mapping
          </p>
        </div>

        {/* Quality and Mode Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            backgroundColor: isScanned ? '#FEE2E2' : '#EBF3EE',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            fontWeight: '600',
            color: isScanned ? '#991B1B' : '#315B45'
          }}>
            {isScanned ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
            <span>Quality: {record?.overall_quality || 'HIGH'}</span>
          </div>

          <div style={{
            display: 'flex',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            overflow: 'hidden'
          }}>
            <button
              onClick={() => setViewMode('pdf')}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: '600',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: viewMode === 'pdf' ? 'var(--primary)' : '#FAF9F6',
                color: viewMode === 'pdf' ? '#FFFFFF' : 'var(--text-secondary)'
              }}
            >
              PDF View
            </button>
            <button
              onClick={() => setViewMode('text')}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: '600',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: viewMode === 'text' ? 'var(--primary)' : '#FAF9F6',
                color: viewMode === 'text' ? '#FFFFFF' : 'var(--text-secondary)'
              }}
            >
              Extracted Text
            </button>
          </div>
        </div>
      </div>

      {/* Main Split Viewer */}
      <div style={{
        display: 'flex',
        gap: '20px',
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px',
        marginBottom: '24px',
        minHeight: '620px'
      }}>
        {/* Thumbnails Sidebar */}
        <div style={{ width: '130px', display: 'flex', flexDirection: 'column', gap: '14px', flexShrink: 0 }}>
          <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Pages ({totalPages})
          </span>

          {pagesArray.map((pageNum) => (
            <button
              type="button"
              key={pageNum}
              onClick={() => setActivePage(pageNum)}
              style={{
                cursor: 'pointer',
                textAlign: 'center',
                background: 'none',
                border: 'none',
                padding: 0,
                width: '100%'
              }}
            >
              <div style={{
                height: '130px',
                border: activePage === pageNum ? '2px solid var(--primary)' : '1px solid var(--border-strong)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#FAF9F6',
                padding: '10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                boxShadow: activePage === pageNum ? 'var(--shadow-md)' : 'none',
                transition: 'border 0.15s ease'
              }}>
                <div style={{ height: '8px', backgroundColor: '#E0DDD3', width: '70%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '100%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '90%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '95%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '80%', borderRadius: '2px' }} />
              </div>
              <span style={{
                fontSize: '12px',
                fontWeight: activePage === pageNum ? '700' : '500',
                color: activePage === pageNum ? 'var(--primary)' : 'var(--text-secondary)',
                marginTop: '4px',
                display: 'inline-block'
              }}>
                Page {pageNum}
              </span>
            </button>
          ))}
        </div>

        {/* Document Sheet Display */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Zoom controls bar */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '12px',
            paddingBottom: '10px',
            borderBottom: '1px solid var(--border-subtle)'
          }}>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Viewing: <strong>{record?.original_filename || 'John_Doe_Clinical_Note.pdf'}</strong> (Page {activePage} of {totalPages})
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                onClick={() => setZoomLevel((z) => Math.max(z - 10, 70))}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px' }}
                title="Zoom Out"
              >
                <Minus size={16} color="var(--text-secondary)" />
              </button>
              <span style={{ fontSize: '12px', fontWeight: '600', minWidth: '40px', textAlign: 'center' }}>
                {zoomLevel}%
              </span>
              <button
                onClick={() => setZoomLevel((z) => Math.min(z + 10, 150))}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px' }}
                title="Zoom In"
              >
                <Plus size={16} color="var(--text-secondary)" />
              </button>
              <a
                href={documentPdfUrl}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                  color: 'var(--primary)',
                  textDecoration: 'none',
                  fontWeight: '600',
                  marginLeft: '8px'
                }}
              >
                <ExternalLink size={14} />
                <span>Open in Tab</span>
              </a>
            </div>
          </div>

          {/* View Container */}
          <div style={{
            flex: 1,
            position: 'relative',
            backgroundColor: '#FAF9F6',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            overflow: 'auto',
            minHeight: '520px'
          }}>
            {viewMode === 'pdf' ? (
              <iframe
                src={`${documentPdfUrl}#page=${activePage}&zoom=${zoomLevel}`}
                title="Clinical Note PDF"
                style={{
                  width: '100%',
                  height: '100%',
                  minHeight: '520px',
                  border: 'none',
                  backgroundColor: '#FAF9F6'
                }}
              />
            ) : (
              <div style={{ padding: '28px 36px', backgroundColor: '#FFFFFF', minHeight: '100%', fontFamily: 'serif', lineHeight: 1.7 }}>
                <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '14px', fontFamily: 'var(--font-sans)', color: '#1F211E' }}>
                  Extracted Page {activePage} Text
                </h3>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  fontSize: '14px',
                  color: '#1F211E'
                }}>
                  {activePageData?.text || 'Text extracted from digital note:\n\nPatient Name: John Doe | DOB: 01/15/1980\nChief Complaint: Persistent severe headaches and dizziness persisting for 3 months.\nPrior Management: Trial of conservative treatment over past 8 weeks without improvement.\nPhysical & Neurological Exam: Neurological examination abnormal with mild ataxia.\nPlan: CT Scan of Head with Contrast (CPT 70460). Rule out intracranial pathology.'}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => onNavigate('new_review')}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Upload Another Note</span>
        </button>

        <button
          onClick={() => onNavigate('extracted_info')}
          className="btn btn-primary"
          style={{ padding: '10px 24px' }}
        >
          <span>Proceed to Fact Review & Audit →</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
};
