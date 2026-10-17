import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ClinicalNoteRecord, EvaluationReport, ViewMode } from '../types';
import { apiFetch } from '../api/client';
import { ExtractedDocumentView } from './ExtractedDocumentView';
import { ExtractedInfoView } from './ExtractedInfoView';
import { CriteriaEvaluationView } from './CriteriaEvaluationView';
import { DetailedAnalysisView } from './DetailedAnalysisView';
import { AuthorizationDecisionView } from './AuthorizationDecisionView';
import { 
  FileText, 
  CheckSquare, 
  FileSpreadsheet, 
  BarChart2, 
  Award, 
  RefreshCw, 
  AlertCircle, 
  ArrowLeft,
  ChevronRight,
  Check
} from 'lucide-react';

export type CaseStage = 'document' | 'facts' | 'evaluation' | 'analysis' | 'decision';

interface CaseWorkflowViewProps {
  stage: CaseStage;
  activeCaseRecord: ClinicalNoteRecord | null;
  setActiveCaseRecord: (record: ClinicalNoteRecord | null) => void;
  activeEvaluationReport: EvaluationReport | null;
  setActiveEvaluationReport: (report: EvaluationReport | null) => void;
}

export const CaseWorkflowView: React.FC<CaseWorkflowViewProps> = ({
  stage,
  activeCaseRecord,
  setActiveCaseRecord,
  activeEvaluationReport,
  setActiveEvaluationReport,
}) => {
  const { caseId: paramCaseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const caseId = paramCaseId || activeCaseRecord?.case_id || 'CASE-2026-001';

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Fetch case record if missing or ID changed
  const loadCaseRecord = useCallback(async (targetCaseId: string) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      let rec: ClinicalNoteRecord | null = null;
      const resCase = await apiFetch(`http://localhost:8000/api/cases/${targetCaseId}`);
      if (resCase.ok) {
        rec = await resCase.json();
      } else {
        const resNote = await apiFetch(`http://localhost:8000/api/notes/${targetCaseId}`);
        if (resNote.ok) {
          rec = await resNote.json();
        }
      }

      if (!rec) {
        throw new Error(`Case ${targetCaseId} was not found in the MedRule clinical repository.`);
      }

      setActiveCaseRecord(rec);

      // If we are in evaluation, analysis, or decision stage, also retrieve evaluation report
      if (['evaluation', 'analysis', 'decision'].includes(stage)) {
        try {
          const evalRes = await apiFetch(`http://localhost:8000/api/cases/${targetCaseId}/evaluate`, {
            method: 'POST'
          });
          if (evalRes.ok) {
            const evalReport: EvaluationReport = await evalRes.json();
            setActiveEvaluationReport(evalReport);
          }
        } catch (evalErr) {
          console.warn('Could not auto-evaluate case on direct load:', evalErr);
        }
      }
    } catch (err: any) {
      console.error('CaseWorkflow load error:', err);
      setLoadError(err.message || `Failed to load case ${targetCaseId}`);
    } finally {
      setIsLoading(false);
    }
  }, [stage, setActiveCaseRecord, setActiveEvaluationReport]);

  useEffect(() => {
    if (!activeCaseRecord || activeCaseRecord.case_id !== caseId) {
      loadCaseRecord(caseId);
    } else if (['evaluation', 'analysis', 'decision'].includes(stage) && (!activeEvaluationReport || activeEvaluationReport.case_id !== caseId)) {
      // Fetch evaluation if missing
      apiFetch(`http://localhost:8000/api/cases/${caseId}/evaluate`, { method: 'POST' })
        .then(res => res.ok ? res.json() : null)
        .then(report => {
          if (report) setActiveEvaluationReport(report);
        })
        .catch(() => {});
    }
  }, [caseId, activeCaseRecord, activeEvaluationReport, stage, loadCaseRecord, setActiveEvaluationReport]);

  // Navigate translator for child views
  const handleWorkflowNavigate = (targetView: ViewMode) => {
    switch (targetView) {
      case 'dashboard':
        navigate('/dashboard');
        break;
      case 'new_review':
        navigate('/review/new');
        break;
      case 'extracted_doc':
        navigate(`/cases/${caseId}/document`);
        break;
      case 'extracted_info':
        navigate(`/cases/${caseId}/facts`);
        break;
      case 'criteria_evaluation':
        navigate(`/cases/${caseId}/evaluation`);
        break;
      case 'detailed_analysis':
        navigate(`/cases/${caseId}/analysis`);
        break;
      case 'authorization_decision':
        navigate(`/cases/${caseId}/decision`);
        break;
      case 'cases_history':
        navigate('/cases');
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
      case 'ask_medrule':
        navigate('/ask');
        break;
      default:
        navigate('/dashboard');
    }
  };

  const stagesList = [
    { key: 'document' as CaseStage, label: 'Document Review', icon: FileText, path: `/cases/${caseId}/document` },
    { key: 'facts' as CaseStage, label: 'Extracted Facts & Audit', icon: CheckSquare, path: `/cases/${caseId}/facts` },
    { key: 'evaluation' as CaseStage, label: 'Criteria Evaluation', icon: FileSpreadsheet, path: `/cases/${caseId}/evaluation` },
    { key: 'analysis' as CaseStage, label: 'Detailed Analysis', icon: BarChart2, path: `/cases/${caseId}/analysis` },
    { key: 'decision' as CaseStage, label: 'Authorization Decision', icon: Award, path: `/cases/${caseId}/decision` },
  ];

  if (isLoading && !activeCaseRecord) {
    return (
      <div style={{
        maxWidth: '800px',
        margin: '60px auto',
        textAlign: 'center',
        padding: '40px 20px'
      }}>
        <div className="card" style={{ padding: '48px 24px' }}>
          <RefreshCw
            size={36}
            color="#315B45"
            style={{ animation: 'spin 1.2s linear infinite', margin: '0 auto 16px auto', display: 'block' }}
          />
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>
            Loading Case Record
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            Retrieving clinical note facts and evaluation trail for <strong>{caseId}</strong>...
          </p>
        </div>
      </div>
    );
  }

  if (loadError && !activeCaseRecord) {
    return (
      <div style={{ maxWidth: '720px', margin: '40px auto', padding: '0 20px' }}>
        <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            backgroundColor: '#FDF1F0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto'
          }}>
            <AlertCircle size={28} color="#B33A32" />
          </div>

          <h2 style={{ fontSize: '22px', fontWeight: '700', color: '#B33A32', marginBottom: '10px' }}>
            Case Could Not Be Loaded
          </h2>

          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.5 }}>
            {loadError}
          </p>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              type="button"
              onClick={() => loadCaseRecord(caseId)}
              className="btn btn-outline"
            >
              <RefreshCw size={15} />
              <span>Retry Loading</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/cases')}
              className="btn btn-primary"
            >
              <ArrowLeft size={15} />
              <span>Return to Cases History</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Workflow Stage Progress Navigation */}
      <div style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 16px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: 'var(--shadow-sm)'
      }}>
        {/* Case Context Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <button
            type="button"
            onClick={() => navigate('/cases')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: 0,
              fontSize: '13px',
              fontWeight: '500'
            }}
          >
            Cases
          </button>
          <ChevronRight size={14} color="var(--text-muted)" />
          <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
            {caseId}
          </span>
          {activeCaseRecord?.patient_name && (
            <span style={{ color: 'var(--text-muted)' }}>
              ({activeCaseRecord.patient_name})
            </span>
          )}
        </div>

        {/* Stage Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {stagesList.map((item, index) => {
            const currentIndex = stagesList.findIndex(s => s.key === stage);
            const isCurrent = stage === item.key;
            const isCompleted = currentIndex > index;
            const Icon = item.icon;

            return (
              <button
                key={item.key}
                type="button"
                onClick={() => navigate(item.path)}
                aria-current={isCurrent ? 'step' : undefined}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: isCurrent ? '1px solid #C8E6D3' : isCompleted ? '1px solid #D6E8DC' : '1px solid transparent',
                  backgroundColor: isCurrent ? '#EAF5EE' : isCompleted ? '#F4F9F6' : 'transparent',
                  color: isCurrent ? '#26734D' : isCompleted ? '#315B45' : 'var(--text-secondary)',
                  fontSize: '13px',
                  fontWeight: isCurrent ? '700' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <span style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  backgroundColor: isCurrent ? '#315B45' : isCompleted ? '#315B45' : '#E5E2DA',
                  color: '#FFFFFF',
                  fontSize: '11px',
                  fontWeight: '700',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {isCompleted ? <Check size={11} strokeWidth={3} /> : index + 1}
                </span>
                <Icon size={14} color={isCurrent || isCompleted ? '#315B45' : undefined} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Render Active Stage Screen */}
      {stage === 'document' && (
        <ExtractedDocumentView
          onNavigate={handleWorkflowNavigate}
          caseRecord={activeCaseRecord}
        />
      )}

      {stage === 'facts' && (
        <ExtractedInfoView
          onNavigate={handleWorkflowNavigate}
          caseRecord={activeCaseRecord}
          onCaseRecordUpdated={(updated) => {
            setActiveCaseRecord(updated);
            setActiveEvaluationReport(null);
          }}
        />
      )}

      {stage === 'evaluation' && (
        <CriteriaEvaluationView
          onNavigate={handleWorkflowNavigate}
          caseRecord={activeCaseRecord}
          evaluationReport={activeEvaluationReport}
          onEvaluationReportChange={setActiveEvaluationReport}
        />
      )}

      {stage === 'analysis' && (
        <DetailedAnalysisView
          onNavigate={handleWorkflowNavigate}
          caseRecord={activeCaseRecord}
          evaluationReport={activeEvaluationReport}
        />
      )}

      {stage === 'decision' && (
        <AuthorizationDecisionView
          onNavigate={handleWorkflowNavigate}
          caseRecord={activeCaseRecord}
          evaluationReport={activeEvaluationReport}
        />
      )}
    </div>
  );
};

export default CaseWorkflowView;
