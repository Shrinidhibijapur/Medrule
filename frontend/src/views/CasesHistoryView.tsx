import React, { useState } from 'react';
import { Search, SlidersHorizontal, MoreHorizontal, ChevronLeft, ChevronRight } from 'lucide-react';
import { ViewMode } from '../types';
import { mockCasesList } from '../mockData';

interface CasesHistoryViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const CasesHistoryView: React.FC<CasesHistoryViewProps> = ({ onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredCases = mockCasesList.filter(c => 
    c.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.procedure.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.insurance_plan.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Cases History
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          View all past authorization reviews
        </p>
      </div>

      {/* Search and Filter Row */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px'
      }}>
        <div style={{
          flex: 1,
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
            placeholder="Search by patient name, procedure, or plan..."
            style={{
              border: 'none',
              outline: 'none',
              width: '100%',
              backgroundColor: 'transparent',
              fontSize: '14px'
            }}
          />
        </div>

        <button className="btn btn-outline" style={{ gap: '8px', padding: '10px 18px' }}>
          <SlidersHorizontal size={16} />
          <span>Filter</span>
        </button>
      </div>

      {/* Cases Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Patient Name</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Procedure</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Insurance Plan</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
              <th style={{ padding: '14px 20px', fontWeight: '600', color: 'var(--text-secondary)' }}>Date</th>
              <th style={{ padding: '14px 20px', width: '60px', fontWeight: '600', color: 'var(--text-secondary)', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCases.map((row, idx) => (
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
                <td style={{ padding: '16px 20px', fontWeight: '600' }}>{row.patient_name}</td>
                <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>{row.procedure}</td>
                <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>{row.insurance_plan}</td>
                <td style={{ padding: '16px 20px' }}>
                  <span className={`badge ${
                    row.status === 'Approved' ? 'badge-approved' : 
                    row.status === 'Not Approved' ? 'badge-not-approved' : 'badge-in-review'
                  }`}>
                    {row.status}
                  </span>
                </td>
                <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>{row.date}</td>
                <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                  <button style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                    <MoreHorizontal size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
        <button className="btn btn-outline" style={{ padding: '6px 10px' }}>
          <ChevronLeft size={16} />
        </button>
        <button className="btn btn-primary" style={{ padding: '6px 12px', minWidth: '32px' }}>
          1
        </button>
        <button className="btn btn-outline" style={{ padding: '6px 12px', minWidth: '32px' }}>
          2
        </button>
        <button className="btn btn-outline" style={{ padding: '6px 12px', minWidth: '32px' }}>
          3
        </button>
        <button className="btn btn-outline" style={{ padding: '6px 12px', minWidth: '32px' }}>
          4
        </button>
        <button className="btn btn-outline" style={{ padding: '6px 10px' }}>
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
};
