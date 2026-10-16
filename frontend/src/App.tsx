import React, { useState } from 'react';
import { ViewMode } from './types';
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

export const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');

  if (!isLoggedIn) {
    return <LoginView onLoginSuccess={() => setIsLoggedIn(true)} />;
  }

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return <DashboardView onNavigate={setCurrentView} />;
      case 'new_review':
        return <NewReviewView onNavigate={setCurrentView} />;
      case 'extracted_doc':
        return <ExtractedDocumentView onNavigate={setCurrentView} />;
      case 'extracted_info':
        return <ExtractedInfoView onNavigate={setCurrentView} />;
      case 'criteria_evaluation':
        return <CriteriaEvaluationView onNavigate={setCurrentView} />;
      case 'detailed_analysis':
        return <DetailedAnalysisView onNavigate={setCurrentView} />;
      case 'authorization_decision':
        return <AuthorizationDecisionView onNavigate={setCurrentView} />;
      case 'cases_history':
        return <CasesHistoryView onNavigate={setCurrentView} />;
      case 'ask_medrule':
        return <AskMedRuleView onNavigate={setCurrentView} />;
      case 'policy_library':
        return <DetailedAnalysisView onNavigate={setCurrentView} />;
      case 'terminology':
      case 'settings':
        return <CasesHistoryView onNavigate={setCurrentView} />;
      default:
        return <DashboardView onNavigate={setCurrentView} />;
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
