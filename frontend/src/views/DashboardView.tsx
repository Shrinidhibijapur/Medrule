import React from 'react';
import { Plus, CheckCircle2, XCircle, Clock, FileText } from 'lucide-react';
import { ViewMode } from '../types';
import { mockCasesList } from '../mockData';

interface DashboardViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate }) => {
  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Top Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '28px'
      }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
            Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Overview of your medical authorization reviews
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

      {/* KPI Stat Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '20px',
        marginBottom: '36px'
      }}>
        {/* Total Reviews */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Total Reviews
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'var(--success-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <FileText size={18} color="var(--success)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>24</div>
          </div>
        </div>

        {/* Approved */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Approved
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'var(--success-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <CheckCircle2 size={18} color="var(--success)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>16</div>
          </div>
        </div>

        {/* Not Approved */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            Not Approved
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'var(--danger-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <XCircle size={18} color="var(--danger)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>6</div>
          </div>
        </div>

        {/* In Review */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500', marginBottom: '12px' }}>
            In Review
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'var(--warning-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Clock size={18} color="var(--warning)" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: '700' }}>2</div>
          </div>
        </div>
      </div>

      {/* Recent Reviews Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '20px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--border-subtle)'
        }}>
          <h2 style={{ fontSize: '17px', fontWeight: '700' }}>Recent Reviews</h2>
          <button
            onClick={() => onNavigate('cases_history')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '13px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            View all
          </button>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Patient Name</th>
              <th style={{ padding: '14px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Procedure</th>
              <th style={{ padding: '14px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Insurance Plan</th>
              <th style={{ padding: '14px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
              <th style={{ padding: '14px 24px', fontWeight: '600', color: 'var(--text-secondary)' }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {mockCasesList.slice(0, 4).map((row, idx) => (
              <tr
                key={idx}
                onClick={() => onNavigate('extracted_doc')}
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'background-color 0.1s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <td style={{ padding: '16px 24px', fontWeight: '600' }}>{row.patient_name}</td>
                <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{row.procedure}</td>
                <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{row.insurance_plan}</td>
                <td style={{ padding: '16px 24px' }}>
                  <span className={`badge ${
                    row.status === 'Approved' ? 'badge-approved' : 
                    row.status === 'Not Approved' ? 'badge-not-approved' : 'badge-in-review'
                  }`}>
                    {row.status}
                  </span>
                </td>
                <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{row.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
