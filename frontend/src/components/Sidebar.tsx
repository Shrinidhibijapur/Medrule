import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ViewMode, UserRole } from '../types';
import { 
  LayoutDashboard, 
  FilePlus2, 
  BookOpen, 
  FolderArchive, 
  BookMarked, 
  Settings,
  MessageSquare,
  Sprout,
  LogOut,
  LogIn,
  LucideIcon,
  ShieldCheck,
  Building2
} from 'lucide-react';

interface SidebarProps {
  currentView?: ViewMode;
  onNavigate?: (view: ViewMode) => void;
}

interface NavItem {
  id: ViewMode;
  label: string;
  path: string;
  icon: LucideIcon;
  matchPrefix?: string[];
  requiredPermission?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = location.pathname;
  const { user, logout, hasPermission } = useAuth();

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { id: 'new_review', label: 'New Review', path: '/review/new', icon: FilePlus2, matchPrefix: ['/review/new'], requiredPermission: 'case:upload' },
    { id: 'ask_medrule', label: 'Ask MedRule', path: '/ask', icon: MessageSquare, matchPrefix: ['/ask'] },
    { id: 'policy_library', label: 'Policy Library', path: '/policies', icon: BookOpen, matchPrefix: ['/policies'] },
    { id: 'cases_history', label: 'Cases', path: '/cases', icon: FolderArchive, matchPrefix: ['/cases'], requiredPermission: 'case:view' },
    { id: 'terminology', label: 'Terminology', path: '/terminology', icon: BookMarked, matchPrefix: ['/terminology'] },
    { id: 'settings', label: 'Settings', path: '/settings', icon: Settings, matchPrefix: ['/settings'], requiredPermission: 'settings:manage' },
  ];

  const handleItemClick = (item: NavItem) => {
    if (onNavigate) {
      onNavigate(item.id);
    }
    navigate(item.path);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isItemActive = (item: NavItem) => {
    if (item.path === '/dashboard') {
      return currentPath === '/' || currentPath === '/dashboard';
    }
    if (item.path === '/review/new') {
      return currentPath === '/review/new';
    }
    if (item.path === '/cases') {
      return currentPath.startsWith('/cases');
    }
    if (item.matchPrefix) {
      return item.matchPrefix.some(p => currentPath.startsWith(p));
    }
    return currentPath === item.path;
  };

  const getInitials = (name?: string): string => {
    if (!name) return 'MD';
    const parts = name.replace(/^(Dr\.|Mr\.|Ms\.|Mrs\.)\s*/i, '').trim().split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const getRoleBadgeColor = (role?: UserRole): { bg: string; text: string } => {
    switch (role) {
      case 'Reviewer MD':
        return { bg: '#E5EDE7', text: '#315B45' };
      case 'Nurse Auditor':
        return { bg: '#FEF3C7', text: '#B45309' };
      case 'Compliance Officer':
        return { bg: '#F3F4F6', text: '#374151' };
      case 'System Admin':
        return { bg: '#FEE2E2', text: '#991B1B' };
      default:
        return { bg: '#EBE9E1', text: '#4B5563' };
    }
  };

  const roleColors = getRoleBadgeColor(user?.role);

  return (
    <aside style={{
      width: '240px',
      backgroundColor: 'var(--bg-surface-subtle, #F7F6F2)',
      borderRight: '1px solid var(--border-subtle, #E5E2DA)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100vh',
      position: 'sticky',
      top: 0,
      fontFamily: 'var(--font-sans)',
    }}>
      <div>
        {/* Brand Header */}
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          style={{
            padding: '24px 20px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
            width: '100%',
          }}
          aria-label="MedRule Dashboard Home"
        >
          <Sprout size={24} color="#315B45" />
          <span style={{
            fontSize: '20px',
            fontWeight: '700',
            letterSpacing: '-0.5px',
            color: 'var(--text-primary, #1C201D)',
          }}>MedRule</span>
        </button>

        {/* Tenant Organization Pill */}
        {user?.organization_id && (
          <div style={{
            padding: '0 16px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            color: '#6D7069',
          }}>
            <Building2 size={13} color="#6D7069" />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.organization_id === 'org_riverside' ? 'Riverside Regional' : user.organization_id}
            </span>
          </div>
        )}

        {/* Navigation list */}
        <nav style={{ padding: '0 12px' }} aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isItemActive(item) || (currentView && currentView === item.id);
            const isRestricted = item.requiredPermission && !hasPermission(item.requiredPermission);

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleItemClick(item)}
                aria-current={active ? 'page' : undefined}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm, 6px)',
                  border: 'none',
                  backgroundColor: active ? '#E5E2DA' : 'transparent',
                  color: active ? 'var(--text-primary, #1C201D)' : isRestricted ? '#9CA3AF' : 'var(--text-secondary, #6D7069)',
                  fontSize: '14px',
                  fontWeight: active ? '600' : '500',
                  cursor: 'pointer',
                  textAlign: 'left',
                  marginBottom: '4px',
                  transition: 'background-color 0.15s ease',
                  opacity: isRestricted ? 0.75 : 1,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon size={18} color={active ? '#315B45' : isRestricted ? '#A3A39D' : '#6D7069'} />
                  <span>{item.label}</span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Authenticated User Footer & Logout */}
      <div style={{
        padding: '14px 16px',
        borderTop: '1px solid var(--border-subtle, #E5E2DA)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '8px',
        backgroundColor: '#F3F1EC',
      }}>
        {user ? (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
              <div style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: '#D1CDC2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: '700',
                fontSize: '12px',
                color: '#1C201D',
                flexShrink: 0,
              }}>
                {getInitials(user.full_name)}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{
                  fontSize: '12px',
                  fontWeight: '600',
                  lineHeight: 1.2,
                  color: '#1C201D',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {user.full_name}
                </div>
                <span style={{
                  display: 'inline-block',
                  fontSize: '10px',
                  fontWeight: 600,
                  backgroundColor: roleColors.bg,
                  color: roleColors.text,
                  padding: '1px 6px',
                  borderRadius: '3px',
                  marginTop: '2px',
                }}>
                  {user.role}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              title="Terminate Authenticated Session"
              aria-label="Terminate Authenticated Session"
              style={{
                background: 'none',
                border: 'none',
                color: '#6D7069',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <LogOut size={16} />
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => navigate('/login')}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '8px',
              backgroundColor: '#EBE9E1',
              border: '1px solid #D5D2C7',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              color: '#315B45',
              cursor: 'pointer',
            }}
          >
            <LogIn size={15} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
