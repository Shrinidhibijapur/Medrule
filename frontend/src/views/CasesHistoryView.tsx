import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Download, RefreshCw, AlertCircle, FileText, Filter, ArrowRight } from 'lucide-react';
import { ViewMode, ClinicalNoteRecord } from '../types';
import { apiFetch } from '../api/client';

interface CasesHistoryViewProps {
  onNavigate?: (view: ViewMode) => void;
  onSelectCaseRecord?: (record: ClinicalNoteRecord) => void;
}

export const CasesHistoryView: React.FC<CasesHistoryViewProps> = ({ onNavigate, onSelectCaseRecord }) => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<ClinicalNoteRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'APPROVED' | 'NOT_APPROVED' | 'ADDITIONAL_DOCS' | 'UNCLEAR'>('ALL');

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('http://localhost:8000/api/cases');
      if (!res.ok) {
        throw new Error(`Failed to load cases from server (HTTP ${res.status})`);
      }
      const data: ClinicalNoteRecord[] = await res.json();
      setCases(data);
    } catch (err: any) {
      console.warn('Cases history fetch error:', err);
      setError(err.message || 'Error connecting to MedRule backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const handleSelectCase = (record: ClinicalNoteRecord) => {
    if (onSelectCaseRecord) {
      onSelectCaseRecord(record);
    }
    navigate(`/cases/${record.case_id}/decision`);
    if (onNavigate) onNavigate('authorization_decision');
  };

  const handleExportCase = async (e: React.MouseEvent, caseId: string, patientName: string) => {
    e.stopPropagation();
    try {
      const res = await apiFetch(`http://localhost:8000/api/cases/${caseId}/export?format=txt`);
      if (!res.ok) {
        throw new Error('Server export endpoint failed');
      }
      const text = await res.text();
      const blob = new Blob([text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `MedRule_Audit_${caseId}_${patientName.replace(/\s+/g, '_')}.txt`;
      a.click();
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const getStatusBadge = (outcome?: string) => {
    if (outcome === 'APPROVED') {
      return {
        label: 'Approved',
        className: 'badge badge-approved',
        style: {}
      };
    }
    if (outcome === 'DENIED' || outcome === 'NOT_APPROVED') {
      return {
        label: 'Not Approved',
        className: 'badge badge-not-approved',
        style: {}
      };
    }
    if (outcome === 'ADDITIONAL_DOCUMENTATION_REQUIRED') {
      return {
        label: 'Documentation Needed',
        className: 'badge',
        style: { backgroundColor: '#FEF3C7', color: '#92400E', border: '1px solid #FCD34D' }
      };
    }
    if (outcome === 'CANNOT_BE_DETERMINED') {
      return {
        label: 'Clinician Review',
        className: 'badge',
        style: { backgroundColor: '#FEF3C7', color: '#92400E', border: '1px solid #FCD34D' }
      };
    }
    return {
      label: 'Pending Review',
      className: 'badge badge-in-review',
      style: {}
    };
  };

  const filteredCases = cases.filter(c => {
    const q = searchTerm.toLowerCase();
    const matchesSearch = 
      c.patient_name.toLowerCase().includes(q) ||
      c.procedure_requested.toLowerCase().includes(q) ||
      c.insurance_plan.toLowerCase().includes(q) ||
      c.case_id.toLowerCase().includes(q);

    if (!matchesSearch) return false;

    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'APPROVED') return c.latest_outcome === 'APPROVED';
    if (statusFilter === 'NOT_APPROVED') return c.latest_outcome === 'DENIED' || c.latest_outcome === 'NOT_APPROVED';
    if (statusFilter === 'ADDITIONAL_DOCS') return c.latest_outcome === 'ADDITIONAL_DOCUMENTATION_REQUIRED';
    if (statusFilter === 'UNCLEAR') return c.latest_outcome === 'CANNOT_BE_DETERMINED';
    return true;
  });

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Authorization Cases History
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
          View, audit, and re-evaluate all clinical encounter records registered in the system
        </p>
      </div>

      {error && (
        <div style={{
          backgroundColor: '#FEE2E2',
          border: '1px solid #FCA5A5',
          borderRadius: '6px',
          padding: '12px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: '#991B1B'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchCases}
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '11px', borderColor: '#FCA5A5', color: '#991B1B', backgroundColor: '#FFFFFF' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Search and Filter Row */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '20px',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{
          flex: '1 1 320px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: '10px 16px',
          backgroundColor: '#FFFFFF'
        }}>
          <Search size={18} color="var(--text-muted)" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by patient name, case ID, procedure, or plan..."
            style={{
              border: 'none',
              outline: 'none',
              width: '100%',
              backgroundColor: 'transparent',
              fontSize: '14px'
            }}
          />
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '6px', backgroundColor: '#FAF9F6', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`btn ${statusFilter === 'ALL' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            All ({cases.length})
          </button>
          <button
            onClick={() => setStatusFilter('APPROVED')}
            className={`btn ${statusFilter === 'APPROVED' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Approved
          </button>
          <button
            onClick={() => setStatusFilter('NOT_APPROVED')}
            className={`btn ${statusFilter === 'NOT_APPROVED' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Not Approved
          </button>
          <button
            onClick={() => setStatusFilter('ADDITIONAL_DOCS')}
            className={`btn ${statusFilter === 'ADDITIONAL_DOCS' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Docs Needed
          </button>
          <button
            onClick={() => setStatusFilter('UNCLEAR')}
            className={`btn ${statusFilter === 'UNCLEAR' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            Review
          </button>
        </div>
      </div>

      {/* Cases Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Case & Patient Name</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Procedure Requested</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Insurance Plan & Policy</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Latest Outcome</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Date Recorded</th>
              <th style={{ padding: '14px 20px', width: '110px', fontWeight: '600', color: 'var(--text-secondary)', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  <RefreshCw size={20} className="animate-spin" style={{ margin: '0 auto 8px', display: 'block', color: 'var(--primary)' }} />
                  <div>Loading cases from server...</div>
                </td>
              </tr>
            ) : filteredCases.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <FileText size={24} style={{ margin: '0 auto 8px', display: 'block', color: 'var(--text-muted)' }} />
                  <div>No matching authorization cases found.</div>
                  <button
                    onClick={() => {
                      navigate('/review/new');
                      if (onNavigate) onNavigate('new_review');
                    }}
                    className="btn btn-primary"
                    style={{ marginTop: '12px', fontSize: '13px' }}
                  >
                    Start a New Review
                  </button>
                </td>
              </tr>
            ) : (
              filteredCases.map((row) => {
                const badge = getStatusBadge(row.latest_outcome);
                return (
                  <tr
                    key={row.case_id}
                    onClick={() => handleSelectCase(row)}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      transition: 'background-color 0.1s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '16px 20px', fontWeight: '600' }}>
                      <div style={{ color: 'var(--text-primary)' }}>{row.patient_name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.case_id}</div>
                    </td>
                    <td style={{ padding: '16px 20px', color: 'var(--text-primary)' }}>
                      <div>{row.procedure_requested}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.facility || 'Outpatient Facility'}</div>
                    </td>
                    <td style={{ padding: '16px 20px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                      <div>{row.insurance_plan}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.policy_id}</div>
                    </td>
                    <td style={{ padding: '16px 20px' }}>
                      <span className={badge.className} style={badge.style}>
                        {badge.label}
                      </span>
                    </td>
                    <td style={{ padding: '16px 20px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                      {row.date_of_visit || (row.created_at ? row.created_at.slice(0, 10) : '2026-10-16')}
                    </td>
                    <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                      <button
                        onClick={(e) => handleExportCase(e, row.case_id, row.patient_name)}
                        className="btn btn-outline"
                        style={{ padding: '4px 8px', fontSize: '11px', gap: '4px' }}
                        title="Download Prior Authorization Audit Package"
                      >
                        <Download size={12} />
                        <span>Export</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
