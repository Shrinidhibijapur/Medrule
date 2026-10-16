import React, { useState, useEffect } from 'react';
import { Plus, CheckCircle2, XCircle, Clock, FileText, AlertCircle, RefreshCw, ShieldAlert, ArrowRight } from 'lucide-react';
import { ViewMode, ClinicalNoteRecord } from '../types';

interface DashboardStats {
  total_reviews: number;
  approved_count: number;
  not_approved_count: number;
  pending_count: number;
  recent_reviews: Array<{
    case_id: string;
    patient_name: string;
    procedure: string;
    insurance_plan: string;
    policy_id: string;
    date: string;
    status: string;
  }>;
  is_synthetic_demo: boolean;
}

interface DashboardViewProps {
  onNavigate: (view: ViewMode) => void;
  onSelectCaseRecord?: (record: ClinicalNoteRecord) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate, onSelectCaseRecord }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/dashboard/stats');
      if (!res.ok) {
        throw new Error(`Failed to load dashboard metrics (HTTP ${res.status})`);
      }
      const data: DashboardStats = await res.json();
      setStats(data);
    } catch (err: any) {
      console.warn('Dashboard stats error:', err);
      setError(err.message || 'Error connecting to MedRule backend service');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleSelectCase = async (caseId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/cases/${caseId}`);
      if (res.ok) {
        const record: ClinicalNoteRecord = await res.json();
        if (onSelectCaseRecord) {
          onSelectCaseRecord(record);
        }
        onNavigate('authorization_decision');
      } else {
        onNavigate('new_review');
      }
    } catch {
      onNavigate('new_review');
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === 'APPROVED') {
      return {
        label: 'Approved',
        className: 'badge badge-approved',
        style: {}
      };
    }
    if (status === 'DENIED' || status === 'NOT_APPROVED') {
      return {
        label: 'Not Approved',
        className: 'badge badge-not-approved',
        style: {}
      };
    }
    if (status === 'ADDITIONAL_DOCUMENTATION_REQUIRED') {
      return {
        label: 'Documentation Needed',
        className: 'badge',
        style: { backgroundColor: '#FEF3C7', color: '#92400E', border: '1px solid #FCD34D' }
      };
    }
    if (status === 'CANNOT_BE_DETERMINED') {
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

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Governance Banner */}
      <div style={{
        backgroundColor: '#FEF3C7',
        border: '1px solid #FCD34D',
        borderRadius: '6px',
        padding: '10px 16px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px'
      }}>
        <ShieldAlert size={18} color="#92400E" />
        <span style={{ fontSize: '12.5px', color: '#92400E' }}>
          <strong>Synthetic Demo Mode Active:</strong> Dashboard aggregates real test cases processed by the deterministic engine. Real patient clinical evaluation remains BLOCKED at the Phase 2 policy verification gate.
        </span>
      </div>

      {/* Top Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px'
      }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
            Authorization Review Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            Live overview of prior authorization cases, criteria evaluation outcomes, and audit histories
          </p>
        </div>
        <button
          onClick={() => onNavigate('new_review')}
          className="btn btn-primary"
          style={{ padding: '10px 18px', fontSize: '14px' }}
        >
          <Plus size={16} />
          <span>New Review</span>
        </button>
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
            onClick={fetchStats}
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '11px', borderColor: '#FCA5A5', color: '#991B1B', backgroundColor: '#FFFFFF' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* KPI Stat Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '18px',
        marginBottom: '32px'
      }}>
        {/* Total Reviews */}
        <div className="card" style={{ padding: '20px 22px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Total Cases Recorded
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              backgroundColor: '#EFEFEA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <FileText size={18} color="var(--primary)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>
              {loading ? '-' : (stats?.total_reviews ?? 0)}
            </div>
          </div>
        </div>

        {/* Approved */}
        <div className="card" style={{ padding: '20px 22px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Approved
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              backgroundColor: 'var(--success-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <CheckCircle2 size={18} color="var(--success)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>
              {loading ? '-' : (stats?.approved_count ?? 0)}
            </div>
          </div>
        </div>

        {/* Not Approved */}
        <div className="card" style={{ padding: '20px 22px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Not Approved / Denied
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              backgroundColor: 'var(--danger-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <XCircle size={18} color="var(--danger)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>
              {loading ? '-' : (stats?.not_approved_count ?? 0)}
            </div>
          </div>
        </div>

        {/* In Review / Pending */}
        <div className="card" style={{ padding: '20px 22px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Review / Missing Docs
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              backgroundColor: 'var(--warning-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Clock size={18} color="var(--warning)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>
              {loading ? '-' : (stats?.pending_count ?? 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Reviews Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '18px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--border-subtle)'
        }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>Recent Authorization Cases</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Dynamically retrieved from saved case repository</span>
          </div>
          <button
            onClick={() => onNavigate('cases_history')}
            className="btn btn-outline"
            style={{ padding: '6px 14px', fontSize: '12px' }}
          >
            <span>View All Cases</span>
            <ArrowRight size={13} style={{ marginLeft: '4px' }} />
          </button>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '12px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Patient Name</th>
              <th style={{ padding: '12px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Procedure Requested</th>
              <th style={{ padding: '12px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Payer & Policy</th>
              <th style={{ padding: '12px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Evaluation Outcome</th>
              <th style={{ padding: '12px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Encounter Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  <RefreshCw size={20} className="animate-spin" style={{ margin: '0 auto 8px', display: 'block', color: 'var(--primary)' }} />
                  <div>Loading recent reviews from server...</div>
                </td>
              </tr>
            ) : !stats?.recent_reviews || stats.recent_reviews.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <FileText size={24} style={{ margin: '0 auto 8px', display: 'block', color: 'var(--text-muted)' }} />
                  <div>No clinical review cases registered yet.</div>
                  <button
                    onClick={() => onNavigate('new_review')}
                    className="btn btn-primary"
                    style={{ marginTop: '12px', fontSize: '13px' }}
                  >
                    Start First Review
                  </button>
                </td>
              </tr>
            ) : (
              stats.recent_reviews.map((row) => {
                const badge = getStatusBadge(row.status);
                return (
                  <tr
                    key={row.case_id}
                    onClick={() => handleSelectCase(row.case_id)}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      transition: 'background-color 0.1s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '14px 24px', fontWeight: '600' }}>
                      <div>{row.patient_name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.case_id}</div>
                    </td>
                    <td style={{ padding: '14px 24px', color: 'var(--text-primary)' }}>{row.procedure}</td>
                    <td style={{ padding: '14px 24px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                      <div>{row.insurance_plan}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.policy_id}</div>
                    </td>
                    <td style={{ padding: '14px 24px' }}>
                      <span className={badge.className} style={badge.style}>
                        {badge.label}
                      </span>
                    </td>
                    <td style={{ padding: '14px 24px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                      {row.date}
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
