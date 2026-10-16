import React from 'react';
import { ViewMode } from '../types';
import { 
  LayoutDashboard, 
  FilePlus2, 
  BookOpen, 
  FolderArchive, 
  BookMarked, 
  Settings,
  MessageSquare,
  Sprout
} from 'lucide-react';

interface SidebarProps {
  currentView: ViewMode;
  onNavigate: (view: ViewMode) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate }) => {
  const navItems = [
    { id: 'dashboard' as ViewMode, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'new_review' as ViewMode, label: 'New Review', icon: FilePlus2 },
    { id: 'ask_medrule' as ViewMode, label: 'Ask MedRule', icon: MessageSquare },
    { id: 'policy_library' as ViewMode, label: 'Policy Library', icon: BookOpen },
    { id: 'cases_history' as ViewMode, label: 'Cases', icon: FolderArchive },
    { id: 'terminology' as ViewMode, label: 'Terminology', icon: BookMarked },
    { id: 'settings' as ViewMode, label: 'Settings', icon: Settings },
  ];

  return (
    <aside style={{
      width: '240px',
      backgroundColor: 'var(--bg-surface-subtle)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      height: '100vh',
      position: 'sticky',
      top: 0
    }}>
      <div>
        {/* Brand Header */}
        <div style={{
          padding: '28px 24px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <Sprout size={24} color="#315B45" />
          <span style={{
            fontSize: '20px',
            fontWeight: '700',
            letterSpacing: '-0.5px',
            color: 'var(--text-primary)'
          }}>MedAuth</span>
        </div>

        {/* Navigation list */}
        <nav style={{ padding: '0 12px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id || 
              (item.id === 'new_review' && ['extracted_doc', 'extracted_info', 'criteria_evaluation', 'detailed_analysis', 'authorization_decision'].includes(currentView)) ||
              (item.id === 'cases_history' && currentView === 'cases_history');

            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  backgroundColor: isActive ? '#E5E2DA' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontSize: '14px',
                  fontWeight: isActive ? '600' : '500',
                  cursor: 'pointer',
                  textAlign: 'left',
                  marginBottom: '4px',
                  transition: 'background-color 0.15s ease'
                }}
              >
                <Icon size={18} color={isActive ? '#315B45' : '#6D7069'} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Footer Profile */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          backgroundColor: '#D1CDC2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: '700',
          fontSize: '13px',
          color: 'var(--text-primary)'
        }}>
          SB
        </div>
        <div>
          <div style={{ fontSize: '13px', fontWeight: '600' }}>Shrinidhi</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Reviewer</div>
        </div>
      </div>
    </aside>
  );
};
