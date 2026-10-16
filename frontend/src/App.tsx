import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ClinicalNoteRecord, EvaluationReport, ViewMode } from './types';
import { apiFetch } from './api/client';
import { Sidebar } from './components/Sidebar';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginView } from './views/LoginView';
import { DashboardView } from './views/DashboardView';
import { NewReviewView } from './views/NewReviewView';
import { CasesHistoryView } from './views/CasesHistoryView';
import { AskMedRuleView } from './views/AskMedRuleView';
import { PolicyLibraryView } from './views/PolicyLibraryView';
import { TerminologyView } from './views/TerminologyView';
import { SettingsView } from './views/SettingsView';
import { CaseWorkflowView } from './views/CaseWorkflowView';
import { NotFoundView } from './views/NotFoundView';

export const App: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [activeCaseRecord, setActiveCaseRecord] = useState<ClinicalNoteRecord | null>(null);
  const [activeEvaluationReport, setActiveEvaluationReport] = useState<EvaluationReport | null>(null);

  useEffect(() => {
    // Initial fetch of default canonical demo case CASE-2026-001 from backend using authenticated client
    apiFetch('http://localhost:8000/api/notes/CASE-2026-001')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setActiveCaseRecord(data);
      })
      .catch(() => {});
  }, []);

  const defaultCaseId = activeCaseRecord?.case_id || 'CASE-2026-001';

  // Handle onNavigate for backwards compatibility
  const handleViewModeNavigate = (targetView: ViewMode) => {
    switch (targetView) {
      case 'dashboard':
        navigate('/dashboard');
        break;
      case 'new_review':
        navigate('/review/new');
        break;
      case 'extracted_doc':
        navigate(`/cases/${defaultCaseId}/document`);
        break;
      case 'extracted_info':
        navigate(`/cases/${defaultCaseId}/facts`);
        break;
      case 'criteria_evaluation':
        navigate(`/cases/${defaultCaseId}/evaluation`);
        break;
      case 'detailed_analysis':
        navigate(`/cases/${defaultCaseId}/analysis`);
        break;
      case 'authorization_decision':
        navigate(`/cases/${defaultCaseId}/decision`);
        break;
      case 'cases_history':
        navigate('/cases');
        break;
      case 'ask_medrule':
        navigate('/ask');
        break;
      case 'policy_library':
        navigate('/policies');
        break;
      case 'terminology':
        navigate('/terminology');
        break;
      case 'settings':
        navigate('/settings');
        break;
      case 'login':
        navigate('/login');
        break;
      default:
        navigate('/dashboard');
    }
  };

  // Login page renders full-bleed without app sidebar
  if (location.pathname === '/login') {
    return <LoginView onLoginSuccess={() => navigate('/dashboard')} />;
  }

  return (
    <div className="app-container">
      <Sidebar onNavigate={handleViewModeNavigate} />
      <main className="main-content">
        <Routes>
          {/* Top-Level Primary Routes */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardView
                  onNavigate={handleViewModeNavigate}
                  onSelectCaseRecord={(rec) => {
                    setActiveCaseRecord(rec);
                    setActiveEvaluationReport(null);
                  }}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/review/new"
            element={
              <ProtectedRoute allowedRoles={['Reviewer MD', 'Nurse Auditor']} requiredPermission="case:upload">
                <NewReviewView
                  onNavigate={handleViewModeNavigate}
                  activeCaseRecord={activeCaseRecord}
                  onSelectCaseRecord={(rec) => {
                    setActiveCaseRecord(rec);
                    setActiveEvaluationReport(null);
                  }}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases"
            element={
              <ProtectedRoute requiredPermission="case:view">
                <CasesHistoryView
                  onNavigate={handleViewModeNavigate}
                  onSelectCaseRecord={(rec) => {
                    setActiveCaseRecord(rec);
                    setActiveEvaluationReport(null);
                  }}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ask"
            element={
              <ProtectedRoute>
                <AskMedRuleView onNavigate={handleViewModeNavigate} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/policies"
            element={
              <ProtectedRoute>
                <PolicyLibraryView onNavigate={handleViewModeNavigate} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/terminology"
            element={
              <ProtectedRoute>
                <TerminologyView onNavigate={handleViewModeNavigate} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute allowedRoles={['System Admin']} requiredPermission="settings:manage">
                <SettingsView onNavigate={handleViewModeNavigate} />
              </ProtectedRoute>
            }
          />

          {/* Review Stage Routes with Case ID Context */}
          <Route
            path="/cases/:caseId/document"
            element={
              <ProtectedRoute requiredPermission="case:view">
                <CaseWorkflowView
                  stage="document"
                  activeCaseRecord={activeCaseRecord}
                  setActiveCaseRecord={setActiveCaseRecord}
                  activeEvaluationReport={activeEvaluationReport}
                  setActiveEvaluationReport={setActiveEvaluationReport}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId/facts"
            element={
              <ProtectedRoute requiredPermission="case:view">
                <CaseWorkflowView
                  stage="facts"
                  activeCaseRecord={activeCaseRecord}
                  setActiveCaseRecord={setActiveCaseRecord}
                  activeEvaluationReport={activeEvaluationReport}
                  setActiveEvaluationReport={setActiveEvaluationReport}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId/evaluation"
            element={
              <ProtectedRoute allowedRoles={['Reviewer MD', 'Nurse Auditor']} requiredPermission="evaluation:run">
                <CaseWorkflowView
                  stage="evaluation"
                  activeCaseRecord={activeCaseRecord}
                  setActiveCaseRecord={setActiveCaseRecord}
                  activeEvaluationReport={activeEvaluationReport}
                  setActiveEvaluationReport={setActiveEvaluationReport}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId/analysis"
            element={
              <ProtectedRoute requiredPermission="case:view">
                <CaseWorkflowView
                  stage="analysis"
                  activeCaseRecord={activeCaseRecord}
                  setActiveCaseRecord={setActiveCaseRecord}
                  activeEvaluationReport={activeEvaluationReport}
                  setActiveEvaluationReport={setActiveEvaluationReport}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId/decision"
            element={
              <ProtectedRoute requiredPermission="decision:export">
                <CaseWorkflowView
                  stage="decision"
                  activeCaseRecord={activeCaseRecord}
                  setActiveCaseRecord={setActiveCaseRecord}
                  activeEvaluationReport={activeEvaluationReport}
                  setActiveEvaluationReport={setActiveEvaluationReport}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId"
            element={<Navigate to={`/cases/${defaultCaseId}/decision`} replace />}
          />

          {/* Review workflow aliases */}
          <Route
            path="/review/document"
            element={<Navigate to={`/cases/${defaultCaseId}/document`} replace />}
          />
          <Route
            path="/review/facts"
            element={<Navigate to={`/cases/${defaultCaseId}/facts`} replace />}
          />
          <Route
            path="/review/evaluation"
            element={<Navigate to={`/cases/${defaultCaseId}/evaluation`} replace />}
          />
          <Route
            path="/review/analysis"
            element={<Navigate to={`/cases/${defaultCaseId}/analysis`} replace />}
          />
          <Route
            path="/review/decision"
            element={<Navigate to={`/cases/${defaultCaseId}/decision`} replace />}
          />

          {/* Catch-all 404 Route */}
          <Route path="*" element={<NotFoundView />} />
        </Routes>
      </main>
    </div>
  );
};

export default App;
