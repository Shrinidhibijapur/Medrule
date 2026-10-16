import React from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { ShieldAlert, ArrowLeft, RefreshCw, LogIn, Lock } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
  requiredPermission?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
  requiredPermission,
}) => {
  const { user, isLoading, hasRole, hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // 1. Loading State
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: '#F7F6F2',
        color: '#1C201D',
        fontFamily: 'var(--font-sans)',
      }}>
        <div style={{
          padding: '36px',
          backgroundColor: '#FFFFFF',
          borderRadius: 'var(--radius-lg, 12px)',
          border: '1px solid var(--border-subtle, #E5E2DA)',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.04)',
          textAlign: 'center',
          maxWidth: '420px',
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            backgroundColor: '#EBE9E1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <Lock size={22} color="#315B45" />
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: '#1C201D' }}>
            Verifying Reviewer Session
          </h2>
          <p style={{ fontSize: '13px', color: '#6D7069', margin: 0 }}>
            Validating cryptographic credentials and role permissions...
          </p>
        </div>
      </div>
    );
  }

  // 2. Unauthenticated State
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 3. Role / Permission Check (Forbidden State 403)
  const isRoleAuthorized = allowedRoles ? hasRole(allowedRoles) : true;
  const isPermissionAuthorized = requiredPermission ? hasPermission(requiredPermission) : true;

  if (!isRoleAuthorized || !isPermissionAuthorized) {
    return (
      <div style={{
        padding: '60px 40px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '80vh',
        fontFamily: 'var(--font-sans)',
      }}>
        <div style={{
          maxWidth: '560px',
          width: '100%',
          backgroundColor: '#FFFFFF',
          border: '1px solid var(--border-subtle, #E5E2DA)',
          borderRadius: 'var(--radius-lg, 12px)',
          padding: '36px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', marginBottom: '20px' }}>
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '8px',
              backgroundColor: '#FEF3C7',
              border: '1px solid #F59E0B',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <ShieldAlert size={24} color="#B45309" />
            </div>
            <div>
              <h1 style={{
                fontSize: '20px',
                fontWeight: 700,
                color: '#1C201D',
                margin: '0 0 4px 0',
              }}>
                403 — Access Restricted
              </h1>
              <p style={{ fontSize: '13px', color: '#6D7069', margin: 0 }}>
                Least-Privilege Role Authorization Gate
              </p>
            </div>
          </div>

          <div style={{
            backgroundColor: '#FAFAF8',
            border: '1px solid #EBE9E1',
            borderRadius: 'var(--radius-sm, 6px)',
            padding: '16px',
            marginBottom: '24px',
            fontSize: '13px',
            lineHeight: 1.6,
          }}>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ color: '#6D7069' }}>Authenticated User: </span>
              <strong style={{ color: '#1C201D' }}>{user.full_name}</strong>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ color: '#6D7069' }}>Active Role: </span>
              <span style={{
                backgroundColor: '#EBE9E1',
                padding: '2px 8px',
                borderRadius: '4px',
                fontWeight: 600,
                color: '#315B45',
              }}>
                {user.role}
              </span>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ color: '#6D7069' }}>Assigned Organization: </span>
              <strong style={{ color: '#1C201D' }}>{user.organization_id}</strong>
            </div>
            {allowedRoles && (
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #E5E2DA' }}>
                <span style={{ color: '#6D7069' }}>Authorized Roles for this Screen: </span>
                <span style={{ fontWeight: 600, color: '#B45309' }}>
                  {allowedRoles.join(', ')}
                </span>
              </div>
            )}
          </div>

          <p style={{
            fontSize: '13px',
            color: '#6D7069',
            marginBottom: '24px',
            lineHeight: 1.5,
          }}>
            MedRule enforces clinical and administrative least privilege. Your role does not carry authorization to modify or view this resource. Direct backend API requests for this resource are likewise protected with server-side 403 enforcement.
          </p>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="btn btn-primary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                fontSize: '13px',
              }}
            >
              <ArrowLeft size={16} />
              <span>Return to Dashboard</span>
            </button>
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="btn btn-outline"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                fontSize: '13px',
                backgroundColor: '#FAF9F6',
              }}
            >
              <LogIn size={16} />
              <span>Switch Active Role</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 4. Authorized
  return <>{children}</>;
};

export default ProtectedRoute;
