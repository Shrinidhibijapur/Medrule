import React, { useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  User,
  Stethoscope,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Edit3,
  Flag,
  FileText,
  Clock,
  History,
  Check,
  X
} from 'lucide-react';
import {
  ViewMode,
  ClinicalNoteRecord,
  ExtractedFact,
  ClinicalFactStatus,
  FactCorrectionPayload,
  FactFlagPayload
} from '../types';

interface ExtractedInfoViewProps {
  onNavigate: (view: ViewMode) => void;
  caseRecord: ClinicalNoteRecord | null;
  onCaseRecordUpdated: (updated: ClinicalNoteRecord) => void;
}

export const ExtractedInfoView: React.FC<ExtractedInfoViewProps> = ({
  onNavigate,
  caseRecord,
  onCaseRecordUpdated,
}) => {
  const [editingFact, setEditingFact] = useState<ExtractedFact | null>(null);
  const [flaggingFact, setFlaggingFact] = useState<ExtractedFact | null>(null);

  // Form states for fact correction modal
  const [correctedValue, setCorrectedValue] = useState<any>('');
  const [correctedStatus, setCorrectedStatus] = useState<ClinicalFactStatus>('EXPLICIT');
  const [reviewerName, setReviewerName] = useState('Dr. Sarah Jenkins, MD');
  const [correctionReason, setCorrectionReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const record = caseRecord;
  const caseId = record?.case_id || 'CASE-2026-001';

  // Standard fallback facts if record not yet populated
  const factsList: ExtractedFact[] = record?.facts
    ? Object.values(record.facts)
    : [
        {
          fact_key: 'neurological_symptoms',
          label: 'Neurological Symptoms Documented',
          value: true,
          status: 'EXPLICIT',
          excerpt: 'Headaches, dizziness, visual disturbances',
          source_page: 1,
          confidence: 0.98
        },
        {
          fact_key: 'symptom_duration_weeks',
          label: 'Symptom Duration (Weeks)',
          value: 12.0,
          status: 'EXPLICIT',
          excerpt: 'Present for 3 months',
          source_page: 1,
          confidence: 0.99
        },
        {
          fact_key: 'conservative_treatment_attempted',
          label: 'Conservative Treatment Trial',
          value: true,
          status: 'EXPLICIT',
          excerpt: 'Conservative treatment (no improvement)',
          source_page: 1,
          confidence: 0.95
        },
        {
          fact_key: 'neurological_exam_abnormal',
          label: 'Abnormal Neurological Examination',
          value: true,
          status: 'EXPLICIT',
          excerpt: 'Neurological examination abnormal',
          source_page: 2,
          confidence: 0.97
        },
        {
          fact_key: 'rule_out_pathology',
          label: 'Rule Out Intracranial Pathology',
          value: true,
          status: 'EXPLICIT',
          excerpt: 'Rule out intracranial pathology',
          source_page: 2,
          confidence: 0.99
        },
        {
          fact_key: 'contrast_requested',
          label: 'Intravenous Contrast Requested',
          value: true,
          status: 'EXPLICIT',
          excerpt: 'CT scan of head with contrast',
          source_page: 2,
          confidence: 0.99
        },
        {
          fact_key: 'contrast_justified',
          label: 'Contrast Enhancement Justification',
          value: true,
          status: 'EXPLICIT',
          excerpt: 'Further diagnostic evaluation needed',
          source_page: 2,
          confidence: 0.94
        }
      ];

  const handleOpenEdit = (fact: ExtractedFact) => {
    setEditingFact(fact);
    setCorrectedValue(fact.value ?? '');
    setCorrectedStatus(fact.status);
    setCorrectionReason('');
    setActionError(null);
  };

  const handleOpenFlag = (fact: ExtractedFact) => {
    setFlaggingFact(fact);
    setCorrectionReason('');
    setActionError(null);
  };

  const handleSaveCorrection = async () => {
    if (!editingFact) return;
    if (!reviewerName.trim()) {
      setActionError('Reviewer name is required for clinical audit compliance.');
      return;
    }
    if (!correctionReason.trim()) {
      setActionError('Audit justification reason is required for fact overrides.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);

    // Parse value if boolean or numeric
    let parsedVal = correctedValue;
    if (correctedValue === 'true' || correctedValue === true) parsedVal = true;
    else if (correctedValue === 'false' || correctedValue === false) parsedVal = false;
    else if (!isNaN(Number(correctedValue)) && correctedValue !== '') parsedVal = Number(correctedValue);

    const payload: FactCorrectionPayload = {
      fact_key: editingFact.fact_key,
      corrected_value: parsedVal,
      corrected_status: correctedStatus,
      reviewer_name: reviewerName.trim(),
      reason: correctionReason.trim(),
    };

    try {
      const response = await fetch(`http://localhost:8000/api/notes/${caseId}/facts/${editingFact.fact_key}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to update fact' }));
        throw new Error(err.detail || `Server returned ${response.status}`);
      }

      const updatedRecord: ClinicalNoteRecord = await response.json();
      onCaseRecordUpdated(updatedRecord);
      setEditingFact(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to submit correction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveFlag = async () => {
    if (!flaggingFact) return;
    if (!correctionReason.trim()) {
      setActionError('Flag reason is required.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);

    const payload: FactFlagPayload = {
      fact_key: flaggingFact.fact_key,
      reviewer_name: reviewerName.trim(),
      reason: correctionReason.trim(),
    };

    try {
      const response = await fetch(`http://localhost:8000/api/notes/${caseId}/flag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to flag fact' }));
        throw new Error(err.detail || `Server returned ${response.status}`);
      }

      const updatedRecord: ClinicalNoteRecord = await response.json();
      onCaseRecordUpdated(updatedRecord);
      setFlaggingFact(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to submit flag.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status: ClinicalFactStatus) => {
    switch (status) {
      case 'EXPLICIT':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            backgroundColor: '#EBF3EE',
            color: '#315B45',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '700'
          }}>
            <CheckCircle2 size={12} />
            EXPLICIT
          </span>
        );
      case 'UNCLEAR':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            backgroundColor: '#FEF3C7',
            color: '#B45309',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '700'
          }}>
            <AlertTriangle size={12} />
            UNCLEAR
          </span>
        );
      case 'CONFLICTING':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            backgroundColor: '#FEE2E2',
            color: '#991B1B',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '700'
          }}>
            <AlertTriangle size={12} />
            CONFLICTING
          </span>
        );
      case 'ABSENT':
      default:
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            backgroundColor: '#F3F4F6',
            color: '#6B7280',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '700'
          }}>
            <X size={12} />
            ABSENT
          </span>
        );
    }
  };

  const hasSecurityWarning = record?.audit_trail?.some(a => a.action === 'SECURITY_WARNING');

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Governance Restriction Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #F59E0B',
        borderRadius: 'var(--radius-md)',
        padding: '12px 18px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldAlert size={18} color="#B45309" />
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#92400E' }}>
            DEVELOPMENT / DEMO MODE: Fact Extraction & Clinician Audit Interface
          </span>
        </div>
        <span style={{ fontSize: '12px', color: '#78350F' }}>
          Case: {record?.case_id || 'CASE-2026-001'} &bull; Synthetic Patient Data
        </span>
      </div>

      {/* Security Alert if prompt injection detected */}
      {hasSecurityWarning && (
        <div style={{
          backgroundColor: '#FEE2E2',
          border: '1px solid #EF4444',
          borderRadius: 'var(--radius-md)',
          padding: '12px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <AlertTriangle size={18} color="#991B1B" />
          <div style={{ fontSize: '13px', color: '#7F1D1D' }}>
            <strong>Security Notice:</strong> Prompt injection attempt detected in uploaded document content. Passive data isolation active. System commands neutralised.
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Clinical Evidence & Fact Review
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Compare extracted clinical facts against note excerpts and perform auditable corrections
        </p>
      </div>

      {/* Patient & Encounter Summary Card */}
      <div className="card" style={{ marginBottom: '24px', padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#FAF9F6'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <User size={16} color="var(--primary)" />
            <h2 style={{ fontSize: '14px', fontWeight: '700', margin: 0 }}>Encounter Information</h2>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Facility: <strong>{record?.facility || 'Riverside Medical Center'}</strong>
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '16px',
          padding: '16px 20px',
          fontSize: '13px'
        }}>
          <div>
            <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '12px' }}>Patient Name</span>
            <strong style={{ fontSize: '14px' }}>{record?.patient_name || 'John Doe'}</strong>
          </div>
          <div>
            <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '12px' }}>Age / DOB</span>
            <strong style={{ fontSize: '14px' }}>{record?.patient_age || 42} yrs &bull; {record?.dob || '01/15/1980'}</strong>
          </div>
          <div>
            <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '12px' }}>Requested Procedure</span>
            <strong style={{ fontSize: '14px' }}>{record?.procedure_requested || 'CT Scan of Head with Contrast'}</strong>
          </div>
          <div>
            <span style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '12px' }}>Target Policy</span>
            <strong style={{ fontSize: '14px' }}>{record?.policy_id || 'P-UHC-CT-2026'} (v{record?.policy_version || '2026.1'})</strong>
          </div>
        </div>
      </div>

      {/* Clinical Facts Evidence Table */}
      <div className="card" style={{ marginBottom: '24px', padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#FAF9F6'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Stethoscope size={16} color="var(--primary)" />
            <h2 style={{ fontSize: '14px', fontWeight: '700', margin: 0 }}>
              Policy Evidence Schema Facts ({factsList.length} criteria inputs)
            </h2>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Governed by approved policy schema: strictly no hallucinated clinical values
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                <th style={{ padding: '12px 16px', fontWeight: '700', width: '22%' }}>Required Evidence Fact</th>
                <th style={{ padding: '12px 14px', fontWeight: '700', width: '12%' }}>Status</th>
                <th style={{ padding: '12px 14px', fontWeight: '700', width: '12%' }}>Extracted Value</th>
                <th style={{ padding: '12px 14px', fontWeight: '700', width: '8%' }}>Page</th>
                <th style={{ padding: '12px 16px', fontWeight: '700', width: '30%' }}>Original Note Excerpt</th>
                <th style={{ padding: '12px 14px', fontWeight: '700', width: '8%' }}>Conf.</th>
                <th style={{ padding: '12px 16px', fontWeight: '700', width: '8%', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {factsList.map((fact) => {
                const isOverridden = fact.reviewer_override?.is_overridden;
                const isFlagged = fact.is_flagged_for_review;

                return (
                  <tr
                    key={fact.fact_key}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      backgroundColor: isOverridden ? '#FAFBF9' : '#FFFFFF',
                      transition: 'background-color 0.1s ease'
                    }}
                  >
                    {/* Fact Label */}
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: '700', color: '#1F211E', marginBottom: '2px' }}>
                        {fact.label}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {fact.fact_key}
                      </div>

                      {isOverridden && (
                        <div style={{
                          marginTop: '6px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '11px',
                          color: '#315B45',
                          backgroundColor: '#EBF3EE',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          <Edit3 size={10} />
                          <span>Overridden by {fact.reviewer_override?.overridden_by}</span>
                        </div>
                      )}

                      {isFlagged && (
                        <div style={{
                          marginTop: '6px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '11px',
                          color: '#991B1B',
                          backgroundColor: '#FEE2E2',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          <Flag size={10} />
                          <span>Flagged: {fact.flag_reason}</span>
                        </div>
                      )}
                    </td>

                    {/* Status */}
                    <td style={{ padding: '14px 14px' }}>
                      {getStatusBadge(fact.status)}
                    </td>

                    {/* Value */}
                    <td style={{ padding: '14px 14px', fontWeight: '700' }}>
                      {fact.value === null || fact.value === undefined ? (
                        <span style={{ color: 'var(--text-muted)', fontWeight: '400', fontStyle: 'italic' }}>
                          Not Documented
                        </span>
                      ) : typeof fact.value === 'boolean' ? (
                        fact.value ? 'True (Documented)' : 'False (Negated)'
                      ) : (
                        `${fact.value}${fact.fact_key.includes('weeks') ? ' weeks' : ''}`
                      )}
                    </td>

                    {/* Source Page */}
                    <td style={{ padding: '14px 14px' }}>
                      {fact.source_page ? (
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 6px',
                          backgroundColor: '#F3F4F6',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: '600',
                          color: '#374151'
                        }}>
                          P. {fact.source_page}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>—</span>
                      )}
                    </td>

                    {/* Excerpt */}
                    <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      {fact.excerpt ? (
                        <span style={{ fontStyle: 'italic', fontSize: '12px' }}>
                          "{fact.excerpt}"
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontStyle: 'italic' }}>
                          No text passage found in uploaded note.
                        </span>
                      )}
                    </td>

                    {/* Confidence */}
                    <td style={{ padding: '14px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '12px', fontWeight: '600' }}>
                          {Math.round(fact.confidence * 100)}%
                        </span>
                      </div>
                      <div style={{
                        height: '4px',
                        width: '45px',
                        backgroundColor: '#E5E7EB',
                        borderRadius: '2px',
                        overflow: 'hidden',
                        marginTop: '3px'
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.round(fact.confidence * 100)}%`,
                          backgroundColor: fact.confidence > 0.85 ? 'var(--primary)' : '#F59E0B'
                        }} />
                      </div>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          onClick={() => handleOpenEdit(fact)}
                          title="Correct Fact with Clinician Audit Reason"
                          style={{
                            border: '1px solid var(--border-subtle)',
                            background: '#FFFFFF',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            color: 'var(--text-primary)'
                          }}
                        >
                          <Edit3 size={12} color="var(--primary)" />
                          <span>Edit</span>
                        </button>

                        <button
                          onClick={() => handleOpenFlag(fact)}
                          title="Flag fact for re-review"
                          style={{
                            border: '1px solid var(--border-subtle)',
                            background: '#FFFFFF',
                            borderRadius: '4px',
                            padding: '4px 6px',
                            cursor: 'pointer'
                          }}
                        >
                          <Flag size={12} color={isFlagged ? '#991B1B' : '#9CA3AF'} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chronological Clinician Audit Trail */}
      {record?.audit_trail && record.audit_trail.length > 0 && (
        <div className="card" style={{ marginBottom: '28px', padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <History size={16} color="var(--primary)" />
            <h3 style={{ fontSize: '14px', fontWeight: '700', margin: 0 }}>
              Clinician Review Audit Trail ({record.audit_trail.length} logged actions)
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
            {record.audit_trail.map((entry, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#FAF9F6',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <strong style={{ color: '#1F211E', marginRight: '6px' }}>[{entry.action}]</strong>
                  <span>{entry.fact_key ? `Fact: ${entry.fact_key}` : entry.details}</span>
                  {entry.reason && (
                    <span style={{ color: 'var(--text-secondary)', marginLeft: '6px' }}>
                      &bull; Reason: "{entry.reason}"
                    </span>
                  )}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                  {entry.reviewer && <span style={{ marginRight: '8px' }}>By: {entry.reviewer}</span>}
                  <span>{entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fact Correction Modal */}
      {editingFact && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: '#FFFFFF',
            borderRadius: 'var(--radius-md)',
            width: '100%',
            maxWidth: '520px',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#FAF9F6'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Edit3 size={16} color="var(--primary)" />
                <h3 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>
                  Audit Correction: {editingFact.label}
                </h3>
              </div>
              <button
                onClick={() => setEditingFact(null)}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} color="var(--text-secondary)" />
              </button>
            </div>

            <div style={{ padding: '20px' }}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>
                  Corrected Clinical Value
                </label>
                <input
                  type="text"
                  value={String(correctedValue)}
                  onChange={(e) => setCorrectedValue(e.target.value)}
                  placeholder="e.g. true, false, 12, or clinical notes"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '13px'
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>
                  Status Classification
                </label>
                <select
                  value={correctedStatus}
                  onChange={(e) => setCorrectedStatus(e.target.value as ClinicalFactStatus)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '13px',
                    backgroundColor: '#FFFFFF'
                  }}
                >
                  <option value="EXPLICIT">EXPLICIT (Clearly documented)</option>
                  <option value="UNCLEAR">UNCLEAR (Ambiguous or low confidence)</option>
                  <option value="CONFLICTING">CONFLICTING (Contradictory entries in note)</option>
                  <option value="ABSENT">ABSENT (Not documented in encounter)</option>
                </select>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>
                  Reviewing Clinician Name (Required for Governance Audit)
                </label>
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  placeholder="e.g. Dr. Sarah Jenkins, MD"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '13px'
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>
                  Clinical Justification / Audit Reason (Required)
                </label>
                <textarea
                  rows={3}
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  placeholder="Explain why the automated extraction was corrected based on the original clinical note..."
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '13px',
                    resize: 'vertical'
                  }}
                />
              </div>

              {actionError && (
                <div style={{
                  padding: '8px 12px',
                  backgroundColor: '#FEE2E2',
                  color: '#991B1B',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  marginBottom: '16px'
                }}>
                  {actionError}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setEditingFact(null)}
                  className="btn btn-outline"
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveCorrection}
                  disabled={isSubmitting}
                  className="btn btn-primary"
                  style={{ padding: '8px 18px', fontSize: '13px' }}
                >
                  {isSubmitting ? 'Saving Audit Entry...' : 'Save & Audit Override'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fact Flagging Modal */}
      {flaggingFact && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: '#FFFFFF',
            borderRadius: 'var(--radius-md)',
            width: '100%',
            maxWidth: '480px',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#FAF9F6'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Flag size={16} color="#991B1B" />
                <h3 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>
                  Flag Fact for Secondary Review
                </h3>
              </div>
              <button
                onClick={() => setFlaggingFact(null)}
                style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} color="var(--text-secondary)" />
              </button>
            </div>

            <div style={{ padding: '20px' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                Flag <strong>{flaggingFact.label}</strong> for clinical supervisor or peer-to-peer verification.
              </p>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>
                  Flag Reason & Notes
                </label>
                <textarea
                  rows={3}
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  placeholder="e.g. Discrepancy between triage note and specialist exam..."
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '13px'
                  }}
                />
              </div>

              {actionError && (
                <div style={{
                  padding: '8px 12px',
                  backgroundColor: '#FEE2E2',
                  color: '#991B1B',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  marginBottom: '16px'
                }}>
                  {actionError}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setFlaggingFact(null)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveFlag}
                  disabled={isSubmitting}
                  className="btn btn-primary"
                  style={{ backgroundColor: '#991B1B' }}
                >
                  {isSubmitting ? 'Flagging...' : 'Confirm Flag'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => onNavigate('extracted_doc')}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Back to Document Viewer</span>
        </button>

        <button
          onClick={() => onNavigate('criteria_evaluation')}
          className="btn btn-primary"
          style={{ padding: '10px 24px' }}
        >
          <span>Proceed to Criteria Evaluation →</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
};
