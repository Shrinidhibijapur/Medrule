import React, { useState } from 'react';
import { Minus, Plus, Maximize2, ArrowLeft, ArrowRight, FileText } from 'lucide-react';
import { ViewMode } from '../types';

interface ExtractedDocumentViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const ExtractedDocumentView: React.FC<ExtractedDocumentViewProps> = ({ onNavigate }) => {
  const [activePage, setActivePage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Extracted Document
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Review the uploaded doctor's notes
        </p>
      </div>

      {/* Main Split Viewer */}
      <div style={{
        display: 'flex',
        gap: '24px',
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px',
        marginBottom: '28px',
        minHeight: '560px'
      }}>
        {/* Thumbnails Sidebar */}
        <div style={{ width: '130px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {[1, 2, 3].map((pageNum) => (
            <div
              key={pageNum}
              onClick={() => setActivePage(pageNum)}
              style={{
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <div style={{
                height: '140px',
                border: activePage === pageNum ? '2px solid var(--primary)' : '1px solid var(--border-strong)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#FAF9F6',
                padding: '10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                boxShadow: activePage === pageNum ? 'var(--shadow-md)' : 'none'
              }}>
                <div style={{ height: '8px', backgroundColor: '#E0DDD3', width: '70%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '100%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '90%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '95%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '80%', borderRadius: '2px' }} />
                <div style={{ height: '6px', backgroundColor: '#EAE7DF', width: '85%', borderRadius: '2px' }} />
              </div>
              <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', marginTop: '4px', display: 'inline-block' }}>
                Page {pageNum}
              </span>
            </div>
          ))}
        </div>

        {/* Document Sheet Display */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Zoom controls bar */}
          <div style={{
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '16px',
            paddingBottom: '12px',
            borderBottom: '1px solid var(--border-subtle)'
          }}>
            <button
              onClick={() => setZoomLevel((z) => Math.max(z - 10, 70))}
              style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px' }}
            >
              <Minus size={16} color="var(--text-secondary)" />
            </button>
            <span style={{ fontSize: '13px', fontWeight: '600', minWidth: '45px', textAlign: 'center' }}>
              {zoomLevel}%
            </span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(z + 10, 150))}
              style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px' }}
            >
              <Plus size={16} color="var(--text-secondary)" />
            </button>
            <button style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px', marginLeft: '8px' }}>
              <Maximize2 size={16} color="var(--text-secondary)" />
            </button>
          </div>

          {/* Clinical Document Paper */}
          <div style={{
            flex: 1,
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '36px 44px',
            fontFamily: 'serif',
            color: '#1F211E',
            lineHeight: 1.6,
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ textAlign: 'center', marginBottom: '24px', borderBottom: '2px solid #315B45', paddingBottom: '12px' }}>
              <h2 style={{ fontSize: '22px', fontWeight: '700', letterSpacing: '-0.3px', color: '#1F211E' }}>
                Riverside Medical Center
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' }}>
                Department of Neurology &bull; Clinical Encounter Record
              </p>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '8px 24px',
              fontFamily: 'var(--font-sans)',
              fontSize: '13px',
              marginBottom: '20px',
              backgroundColor: '#FAF9F6',
              padding: '14px 18px',
              borderRadius: 'var(--radius-sm)'
            }}>
              <div><strong>Patient Name:</strong> John Doe</div>
              <div><strong>DOB:</strong> 01/15/1980 (Age: 42)</div>
              <div><strong>Date of Visit:</strong> 10/05/2026</div>
              <div><strong>Encounter ID:</strong> ENC-884920</div>
            </div>

            <div style={{ fontFamily: 'var(--font-sans)', fontSize: '14px' }}>
              <div style={{ marginBottom: '14px' }}>
                <strong style={{ display: 'block', color: 'var(--primary)', marginBottom: '4px' }}>
                  Chief Complaint:
                </strong>
                <p>Persistent headaches and dizziness.</p>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <strong style={{ display: 'block', color: 'var(--primary)', marginBottom: '4px' }}>
                  History of Present Illness:
                </strong>
                <p>
                  42 year old male presents with recurrent severe headaches and episodic dizziness persisting for 3 months with associated visual disturbances. Symptoms have progressively worsened despite outpatient management.
                </p>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <strong style={{ display: 'block', color: 'var(--primary)', marginBottom: '4px' }}>
                  Clinical Findings:
                </strong>
                <ol style={{ paddingLeft: '20px' }}>
                  <li>Neurological examination shows cranial nerve asymmetry and mild gait ataxia.</li>
                  <li>No improvement with conservative treatment over past 8 weeks.</li>
                  <li>Patient has history of hypertension.</li>
                </ol>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <strong style={{ display: 'block', color: 'var(--primary)', marginBottom: '4px' }}>
                  Impression & Plan:
                </strong>
                <p>
                  Rule out intracranial pathology or mass lesion. Recommend CT scan of head with IV contrast for definitive evaluation.
                </p>
              </div>
            </div>
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
          <span>Edit</span>
        </button>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => onNavigate('extracted_info')}
            className="btn btn-outline"
          >
            <span>View Extracted Info</span>
          </button>
          <button
            onClick={() => onNavigate('criteria_evaluation')}
            className="btn btn-primary"
            style={{ padding: '10px 24px' }}
          >
            <span>Proceed to Evaluation</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
