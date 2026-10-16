import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Compass, ArrowLeft, LayoutDashboard, FolderArchive, BookOpen } from 'lucide-react';

export const NotFoundView: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{
      maxWidth: '720px',
      margin: '60px auto',
      textAlign: 'center',
      padding: '0 20px'
    }}>
      <div className="card" style={{
        padding: '48px 36px',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-md)'
      }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          backgroundColor: '#EBF3EE',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px auto'
        }}>
          <Compass size={32} color="#315B45" />
        </div>

        <span style={{
          display: 'inline-block',
          fontSize: '12px',
          fontWeight: '700',
          letterSpacing: '1px',
          textTransform: 'uppercase',
          color: '#315B45',
          backgroundColor: '#EAF5EE',
          padding: '4px 12px',
          borderRadius: '9999px',
          marginBottom: '14px'
        }}>
          404 — Route Not Found
        </span>

        <h1 style={{
          fontSize: '28px',
          fontWeight: '700',
          color: 'var(--text-primary)',
          letterSpacing: '-0.5px',
          marginBottom: '12px'
        }}>
          Screen or Resource Unavailable
        </h1>

        <p style={{
          fontSize: '15px',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          maxWidth: '520px',
          margin: '0 auto 28px auto'
        }}>
          The URL you requested does not correspond to a recognized MedRule screen, review stage, or policy record. You can navigate back or use one of the primary application destinations below.
        </p>

        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px',
          justifyContent: 'center',
          marginBottom: '28px'
        }}>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary"
            style={{ padding: '10px 22px' }}
          >
            <LayoutDashboard size={16} />
            <span>Return to Dashboard</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/cases')}
            className="btn btn-outline"
            style={{ padding: '10px 20px' }}
          >
            <FolderArchive size={16} />
            <span>Cases History</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/policies')}
            className="btn btn-outline"
            style={{ padding: '10px 20px' }}
          >
            <BookOpen size={16} />
            <span>Policy Library</span>
          </button>
        </div>

        <div style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '20px',
          fontSize: '13px',
          color: 'var(--text-muted)'
        }}>
          <button
            type="button"
            onClick={() => navigate(-1)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px',
              fontWeight: '500'
            }}
          >
            <ArrowLeft size={14} />
            <span>Go back to previous page</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotFoundView;
