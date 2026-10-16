import React, { useState, useEffect } from 'react';
import { ViewMode, ClinicalNoteRecord, EvaluationReport } from './types';
import { Sidebar } from './components/Sidebar';
import { LoginView } from './views/LoginView';
import { DashboardView } from './views/DashboardView';
import { NewReviewView } from './views/NewReviewView';
import { ExtractedDocumentView } from './views/ExtractedDocumentView';
import { ExtractedInfoView } from './views/ExtractedInfoView';
import { CriteriaEvaluationView } from './views/CriteriaEvaluationView';
import { DetailedAnalysisView } from './views/DetailedAnalysisView';
import { AuthorizationDecisionView } from './views/AuthorizationDecisionView';
import { CasesHistoryView } from './views/CasesHistoryView';
import { AskMedRuleView } from './views/AskMedRuleView';
import { PolicyLibraryView } from './views/PolicyLibraryView';
import { TerminologyView } from './views/TerminologyView';
import { SettingsView } from './views/SettingsView';

export const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');
  const [activeCaseRecord, setActiveCaseRecord] = useState<ClinicalNoteRecord | null>(null);
  const [activeEvaluationReport, setActiveEvaluationReport] = useState<EvaluationReport | null>(null);

  useEffect(() => {
    // Attempt initial load of canonical demo case CASE-2026-001 from backend
    fetch('http://localhost:8000/api/notes/CASE-2026-001')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setActiveCaseRecord(data);
      })
      .catch(() => {});
  }, []);

  if (!isLoggedIn) {
    return <LoginView onLoginSuccess={() => setIsLoggedIn(true)} />;
  }

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <DashboardView
            onNavigate={setCurrentView}
            onSelectCaseRecord={(rec) => {
              setActiveCaseRecord(rec);
              setActiveEvaluationReport(null);
            }}
          />
        );
      case 'new_review':
        return (
          <NewReviewView
            onNavigate={setCurrentView}
            onSelectCaseRecord={(rec) => {
              setActiveCaseRecord(rec);
              setActiveEvaluationReport(null);
            }}
            activeCaseRecord={activeCaseRecord}
          />
        );
      case 'extracted_doc':
        return (
          <ExtractedDocumentView
            onNavigate={setCurrentView}
            caseRecord={activeCaseRecord}
          />
        );
      case 'extracted_info':
        return (
          <ExtractedInfoView
            onNavigate={setCurrentView}
            caseRecord={activeCaseRecord}
            onCaseRecordUpdated={(rec) => {
              setActiveCaseRecord(rec);
              setActiveEvaluationReport(null);
            }}
          />
        );
      case 'criteria_evaluation':
        return (
          <CriteriaEvaluationView 
            onNavigate={setCurrentView} 
            caseRecord={activeCaseRecord}
            evaluationReport={activeEvaluationReport}
            onEvaluationReportChange={setActiveEvaluationReport}
          />
        );
      case 'detailed_analysis':
        return (
          <DetailedAnalysisView 
            onNavigate={setCurrentView} 
            evaluationReport={activeEvaluationReport}
            caseRecord={activeCaseRecord}
          />
        );
      case 'authorization_decision':
        return (
          <AuthorizationDecisionView 
            onNavigate={setCurrentView} 
            evaluationReport={activeEvaluationReport}
            caseRecord={activeCaseRecord}
          />
        );
      case 'cases_history':
        return (
          <CasesHistoryView
            onNavigate={setCurrentView}
            onSelectCaseRecord={(rec) => {
              setActiveCaseRecord(rec);
              setActiveEvaluationReport(null);
            }}
          />
        );
      case 'ask_medrule':
        return <AskMedRuleView onNavigate={setCurrentView} />;
      case 'policy_library':
        return <PolicyLibraryView onNavigate={setCurrentView} />;
      case 'terminology':
        return <TerminologyView onNavigate={setCurrentView} />;
      case 'settings':
        return <SettingsView onNavigate={setCurrentView} />;
      default:
        return (
          <DashboardView
            onNavigate={setCurrentView}
            onSelectCaseRecord={(rec) => {
              setActiveCaseRecord(rec);
              setActiveEvaluationReport(null);
            }}
          />
        );
    }
  };

  return (
    <div className="app-container">
      <Sidebar currentView={currentView} onNavigate={setCurrentView} />
      <main className="main-content">
        {renderCurrentView()}
      </main>
    </div>
  );
};

export default App;
