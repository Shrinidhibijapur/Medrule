import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Send, 
  Paperclip, 
  Sparkles, 
  X, 
  ArrowRight, 
  AlertCircle, 
  FileText, 
  Check, 
  AlertTriangle,
  Key,
  Copy,
  CheckCircle2,
  Settings,
  Bot,
  User,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  RefreshCw,
  FileCheck,
  Activity,
  FileSearch,
  BookOpen
} from 'lucide-react';
import { ViewMode, EvaluationReport, ClinicalNoteRecord, VerifiedClaimItem } from '../types';
import { apiFetch } from '../api/client';

interface AskMedRuleViewProps {
  onNavigate?: (view: ViewMode) => void;
  onSelectCaseRecord?: (record: ClinicalNoteRecord) => void;
  onEvaluationReportChange?: (report: EvaluationReport) => void;
}

interface AgentCitationItem {
  document_id?: string;
  document_filename?: string;
  page_number: number;
  excerpt?: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  modelUsed?: string;
  isGroq?: boolean;
  attachedFile?: string;
  report?: EvaluationReport;
  error?: string;
  intent?: string;
  documentId?: string;
  citations?: AgentCitationItem[];
  verifiedClaims?: VerifiedClaimItem[];
  warnings?: string[];
}

interface ActiveDocumentState {
  id: string;
  filename: string;
  totalPages: number;
  sha256?: string;
  rawPagesText?: Array<{ page_number: number; text: string }>;
  facts?: Record<string, any>;
  patientName?: string;
  procedure?: string;
  insurer?: string;
  facility?: string;
  dateOfVisit?: string;
  caseId?: string;
}

interface SampleCaseOption {
  id: string;
  name: string;
  procedure: string;
  insurer: string;
  desc: string;
  defaultPrompt: string;
}

const SAMPLE_CASES: SampleCaseOption[] = [
  {
    id: 'CASE-2026-001',
    name: 'John Doe (Encounter: 10/05/2026)',
    procedure: 'CT Scan of Head with Contrast',
    insurer: 'United Healthcare',
    desc: 'Atypical headache, 9 weeks duration, pronator drift (Approved under P-UHC-CT-2026)',
    defaultPrompt: 'Based on this note, can the CT scan of head be approved under UHC criteria?'
  },
  {
    id: 'CASE-2026-002',
    name: 'Jane Smith (Encounter: 10/08/2026)',
    procedure: 'CT Scan of Head with Contrast',
    insurer: 'United Healthcare',
    desc: 'Acute headache, 2 weeks duration (Unmet duration requirement under P-UHC-CT-2026)',
    defaultPrompt: 'Why does Jane Smith fail the guideline duration criteria for Head CT?'
  },
  {
    id: 'CASE-2026-003',
    name: 'Robert Chen (Encounter: 10/11/2026)',
    procedure: 'CT Scan of Head with Contrast',
    insurer: 'United Healthcare',
    desc: 'Persistent headache, missing conservative therapy trial (Documentation needed)',
    defaultPrompt: 'What clinical evidence is missing from Robert Chen\'s records before this request can be approved?'
  },
  {
    id: 'CASE-VIVEK-002',
    name: 'Vivek Pampattiwar (DOS: 02/26/2025)',
    procedure: 'MRI : Lumbar without contrast',
    insurer: 'Ambetter',
    desc: 'Lumbar MRI clinical encounter: Conservative therapy documented (Policy mismatch against P-UHC-CT-2026)',
    defaultPrompt: 'Summarize the symptoms, diagnoses, examination findings, and treatments in this clinical note.'
  },
  {
    id: 'CASE-VIVEK-001',
    name: 'Vivek Pampattiwar (DOS: 01/09/2025)',
    procedure: 'MRI : Lumbar without contrast',
    insurer: 'Ambetter',
    desc: 'Initial consultation: Spondylosis, spinal stenosis with neurogenic claudication',
    defaultPrompt: 'What indications and examination findings are documented in this consultation?'
  }
];

export const AskMedRuleView: React.FC<AskMedRuleViewProps> = ({ 
  onNavigate,
  onSelectCaseRecord,
  onEvaluationReportChange
}) => {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const latestRequestIdRef = useRef<string | null>(null);

  // Active Context & Case State
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [activeDocument, setActiveDocument] = useState<ActiveDocumentState | null>(null);
  const [activeNoteRecord, setActiveNoteRecord] = useState<ClinicalNoteRecord | null>(null);
  const [activeEvaluation, setActiveEvaluation] = useState<EvaluationReport | null>(null);
  const [activeTrace, setActiveTrace] = useState<any | null>(null);
  const [attachedFileName, setAttachedFileName] = useState<string | null>(null);
  const [activeRightTab, setActiveRightTab] = useState<'evidence' | 'criteria' | 'document' | 'trace'>('evidence');

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      sender: 'agent',
      timestamp: '12:00 PM',
      modelUsed: 'MedRule Conversational Copilot',
      isGroq: false,
      intent: 'DOCUMENT_ANALYSIS',
      text: `### MedRule Clinical Authorization Copilot

Welcome to the Ask MedRule conversational copilot. MedRule routes clinical requests by intent:

1. **📄 Document Analysis (AI-Assisted & Grounded)**:
   Attach any clinical note PDF to extract symptoms, diagnoses, physical exams, and documented therapies with verified page citations—without requiring an insurance policy.

2. **⚡ Prior-Authorization Criteria (Deterministic Rules Engine)**:
   Select a verified clinical encounter and payer rulebook to execute deterministic, auditable prior-authorization evaluations. Incompatible policies fail closed safely with \`POLICY_MISMATCH\`.

3. **✍️ Appeal Drafting (Evidence-Based)**:
   Generate clinical appeal outlines grounded in documented records and applicable policy citations.

*To get started, attach a PDF using the paperclip icon or select a sample encounter below.*`
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  const loadCaseContext = async (caseId: string) => {
    if (!caseId) {
      setActiveEvaluation(null);
      setActiveTrace(null);
      return;
    }

    try {
      // Invalidate stale evaluation & trace
      setActiveEvaluation(null);
      setActiveTrace(null);

      // 1. Fetch note record
      const noteRes = await apiFetch(`http://localhost:8000/api/notes/${caseId}`);
      if (noteRes.ok) {
        const noteData: ClinicalNoteRecord = await noteRes.json();
        setActiveNoteRecord(noteData);
        if (onSelectCaseRecord) onSelectCaseRecord(noteData);

        // Bind document context
        setActiveDocument({
          id: noteData.document_id || noteData.case_id,
          filename: noteData.original_filename || `${caseId}.pdf`,
          totalPages: noteData.total_pages || 1,
          sha256: noteData.sha256_checksum,
          rawPagesText: noteData.raw_pages_text || [],
          facts: noteData.facts || {},
          patientName: noteData.patient_name,
          procedure: noteData.procedure_requested,
          insurer: noteData.insurance_plan,
          facility: noteData.facility,
          dateOfVisit: noteData.date_of_visit,
          caseId: noteData.case_id
        });
        setAttachedFileName(noteData.original_filename || `${caseId}.pdf`);

        // 2. Evaluate against policy (only if note has a policy_id)
        if (noteData.policy_id) {
          try {
            const evalRes = await apiFetch(`http://localhost:8000/api/cases/${caseId}/evaluate`, { method: 'POST' });
            if (evalRes.ok) {
              const evalData: EvaluationReport = await evalRes.json();
              setActiveEvaluation(evalData);
              if (onEvaluationReportChange) onEvaluationReportChange(evalData);
            } else {
              setActiveEvaluation(null);
            }
          } catch (evalErr) {
            console.warn('Evaluation skipped or policy mismatch:', evalErr);
            setActiveEvaluation(null);
          }
        } else {
          setActiveEvaluation(null);
        }

        // 3. Fetch structured decision trace
        try {
          const traceRes = await apiFetch(`http://localhost:8000/api/agent/trace/${caseId}`);
          if (traceRes.ok) {
            const traceData = await traceRes.json();
            setActiveTrace(traceData);
          }
        } catch (traceErr) {
          console.warn('Trace not loaded:', traceErr);
        }
      }
    } catch (e) {
      console.warn('Could not load case context:', e);
    }
  };

  const handleSelectSampleCase = async (caseOption: SampleCaseOption) => {
    setSelectedCaseId(caseOption.id);
    setActiveDocument(null);
    setActiveEvaluation(null);
    setActiveTrace(null);
    setAttachedFileName(`${caseOption.name.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`);
    setInputText(caseOption.defaultPrompt);
    await loadCaseContext(caseOption.id);
  };

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await apiFetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData
      });

      if (!uploadRes.ok) {
        const errData = await uploadRes.json().catch(() => ({ detail: 'Document upload failed' }));
        throw new Error(errData.detail || `Upload failed with status ${uploadRes.status}`);
      }

      const docData = await uploadRes.json();
      
      // Explicit context handling: new document has its own document ID, checksum, page count
      const newDocState: ActiveDocumentState = {
        id: docData.document_id,
        filename: docData.filename,
        totalPages: docData.total_pages,
        sha256: docData.sha256_checksum,
        rawPagesText: docData.raw_pages_text || [],
        facts: docData.facts || {},
        patientName: docData.patient_name,
        procedure: docData.procedure_requested,
        insurer: docData.insurance_plan,
        caseId: docData.case_id
      };

      setActiveDocument(newDocState);
      setAttachedFileName(docData.filename);
      // Invalidate stale case association so new upload is not bound to a previous case or policy
      setSelectedCaseId('');
      setActiveEvaluation(null);
      setActiveTrace(null);

      // Create a compatible ClinicalNoteRecord object for tabs
      const noteRec: ClinicalNoteRecord = {
        case_id: docData.case_id || docData.document_id,
        document_id: docData.document_id,
        patient_name: docData.patient_name || 'Uploaded Document Patient',
        patient_age: undefined,
        gender: undefined,
        facility: 'Clinical Note Source',
        date_of_visit: docData.date_of_visit,
        procedure_requested: docData.procedure_requested || 'Unspecified Clinical Procedure',
        insurance_plan: docData.insurance_plan || 'Unspecified Insurance',
        policy_id: undefined,
        total_pages: docData.total_pages,
        original_filename: docData.filename,
        sha256_checksum: docData.sha256_checksum,
        storage_path: undefined,
        scanned_pages_count: 0,
        overall_quality: 'HIGH',
        ocr_engine_status: 'Ready',
        is_synthetic: true,
        governance_warning: '',
        facts: docData.facts || {},
        raw_pages_text: docData.raw_pages_text || [],
        audit_trail: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setActiveNoteRecord(noteRec);
      if (onSelectCaseRecord) onSelectCaseRecord(noteRec);

      // Add a system confirmation message
      setMessages(prev => [
        ...prev,
        {
          id: `doc-uploaded-${Date.now()}`,
          sender: 'agent',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          modelUsed: 'MedRule Document Ingestion Engine',
          intent: 'DOCUMENT_ANALYSIS',
          isGroq: false,
          text: `📄 **Document Attached Successfully**: \`${docData.filename}\`\n\n- **Document ID**: \`${docData.document_id}\`\n- **Valid Pages**: ${docData.total_pages} Page${docData.total_pages === 1 ? '' : 's'}\n- **Checksum (SHA-256)**: \`${docData.sha256_checksum ? docData.sha256_checksum.substring(0, 16) + '...' : 'Verified'}\`\n- **Extracted Facts**: ${Object.keys(docData.facts || {}).length} clinical elements recognized\n\nYou can now ask document-analysis questions (e.g. *"Summarize symptoms and treatments"*, *"Extract conservative therapy"*, or *"What does page 1 say?"*) without requiring an insurance policy.`
        }
      ]);
    } catch (err: any) {
      alert(`Document upload error: ${err.message || 'Failed to process document'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSend = async (customPrompt?: string) => {
    const query = (customPrompt || inputText).trim();
    if (!query || isProcessing) return;

    // Unique request ID for version & out-of-order response check
    const reqId = `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
    latestRequestIdRef.current = reqId;

    const userMessageId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      attachedFile: attachedFileName || undefined
    };

    setMessages(prev => [...prev, userMsg]);
    if (!customPrompt) setInputText('');
    setIsProcessing(true);

    try {
      // Resolve document IDs: pass ONLY the explicitly selected document(s)
      const docIds: string[] = [];
      if (activeDocument?.id) {
        docIds.push(activeDocument.id);
      } else if (activeNoteRecord?.document_id) {
        docIds.push(activeNoteRecord.document_id);
      } else if (selectedCaseId) {
        docIds.push(selectedCaseId);
      }

      // Call the intent-routing agent chat endpoint
      const chatRes = await apiFetch('http://localhost:8000/api/agent/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: query,
          case_id: selectedCaseId || undefined,
          document_id: activeDocument?.id || undefined,
          document_ids: docIds.length > 0 ? docIds : undefined,
          request_id: reqId,
          history: messages.slice(-6).map(m => ({
            role: m.sender === 'user' ? 'user' : 'assistant',
            content: m.text
          }))
        })
      });

      if (!chatRes.ok) {
        const errData = await chatRes.json().catch(() => ({ detail: 'Agent query failed' }));
        throw new Error(errData.detail || `Server returned HTTP ${chatRes.status}`);
      }

      const agentData = await chatRes.json();

      // Invalidation & Stale Response Guard: if another request was dispatched after this one, drop this response
      if (latestRequestIdRef.current && agentData.request_id && agentData.request_id !== latestRequestIdRef.current) {
        console.warn('Ignoring stale response for outdated request ID:', agentData.request_id);
        return;
      }

      if (agentData.evaluation) {
        setActiveEvaluation(agentData.evaluation);
        if (onEvaluationReportChange) onEvaluationReportChange(agentData.evaluation);
      } else {
        setActiveEvaluation(null);
      }
      if (agentData.trace) {
        setActiveTrace(agentData.trace);
      }

      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: 'agent',
        text: agentData.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelUsed: agentData.model_used,
        isGroq: agentData.is_groq_powered,
        intent: agentData.intent,
        documentId: agentData.document_id,
        citations: agentData.citations,
        verifiedClaims: agentData.verified_claims,
        warnings: agentData.warnings,
        report: agentData.evaluation
      };

      setMessages(prev => [...prev, agentMsg]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `agent-err-${Date.now()}`,
          sender: 'agent',
          text: `⚠️ **Unable to complete request**: ${err.message || 'Connection error'}. Please check if the backend is running.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          error: err.message
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  const getIntentBadge = (intent?: string) => {
    switch (intent) {
      case 'DOCUMENT_ANALYSIS':
        return (
          <span style={{
            fontSize: '10.5px',
            backgroundColor: '#EBF3EE',
            color: 'var(--primary)',
            border: '1px solid var(--success-border)',
            padding: '2px 7px',
            borderRadius: '4px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <FileSearch size={11} />
            <span>Document Analysis (AI-Assisted)</span>
          </span>
        );
      case 'EVALUATION_QUERY':
        return (
          <span style={{
            fontSize: '10.5px',
            backgroundColor: '#FEF3C7',
            color: '#92400E',
            border: '1px solid #FCD34D',
            padding: '2px 7px',
            borderRadius: '4px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <ShieldCheck size={11} />
            <span>Policy Evaluation (Deterministic)</span>
          </span>
        );
      case 'APPEAL_DRAFT':
        return (
          <span style={{
            fontSize: '10.5px',
            backgroundColor: '#EDE9FE',
            color: '#5B21B6',
            border: '1px solid #C4B5FD',
            padding: '2px 7px',
            borderRadius: '4px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <BookOpen size={11} />
            <span>Appeal Draft</span>
          </span>
        );
      case 'WORKFLOW_QUERY':
        return (
          <span style={{
            fontSize: '10.5px',
            backgroundColor: '#F0EFEA',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border-subtle)',
            padding: '2px 7px',
            borderRadius: '4px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <Activity size={11} />
            <span>Clinical Workflow</span>
          </span>
        );
      default:
        return null;
    }
  };

  // Render markdown with nice clinical styling
  const renderFormattedMarkdown = (text: string) => {
    const lines = text.split('\n');
    return (
      <div style={{ lineHeight: 1.6, fontSize: '14px' }}>
        {lines.map((line, idx) => {
          if (line.startsWith('### ')) {
            return (
              <h4 key={idx} style={{ fontSize: '15px', fontWeight: 700, margin: '12px 0 6px 0', color: 'var(--text-primary)' }}>
                {line.replace('### ', '')}
              </h4>
            );
          }
          if (line.startsWith('## ')) {
            return (
              <h3 key={idx} style={{ fontSize: '16px', fontWeight: 700, margin: '14px 0 8px 0', color: 'var(--text-primary)' }}>
                {line.replace('## ', '')}
              </h3>
            );
          }
          if (line.startsWith('> ')) {
            return (
              <div key={idx} style={{
                backgroundColor: 'rgba(217, 119, 6, 0.08)',
                borderLeft: '3px solid #D97706',
                padding: '8px 12px',
                borderRadius: '0 6px 6px 0',
                margin: '8px 0',
                fontSize: '13px',
                color: '#92400E'
              }}>
                {line.replace('> ', '')}
              </div>
            );
          }
          if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            const rawContent = line.trim().replace(/^[-*]\s+/, '');
            return (
              <div key={idx} style={{ display: 'flex', gap: '8px', marginBottom: '4px', paddingLeft: '8px' }}>
                <span style={{ color: 'var(--primary)', fontWeight: 700 }}>•</span>
                <span dangerouslySetInnerHTML={{ __html: formatBoldAndCode(rawContent) }} />
              </div>
            );
          }
          if (line.trim() === '---') {
            return <hr key={idx} style={{ border: 'none', borderTop: '1px solid var(--border-subtle)', margin: '12px 0' }} />;
          }
          if (!line.trim()) {
            return <div key={idx} style={{ height: '6px' }} />;
          }
          return (
            <p key={idx} style={{ margin: '0 0 6px 0' }} dangerouslySetInnerHTML={{ __html: formatBoldAndCode(line) }} />
          );
        })}
      </div>
    );
  };

  const formatBoldAndCode = (content: string) => {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code style="background:#F0EFEA;padding:2px 5px;border-radius:4px;font-size:12px;color:#1E3A2F;">$1</code>');
  };

  return (
    <div style={{ 
      height: 'calc(100vh - 84px)', 
      display: 'flex', 
      flexDirection: 'column', 
      padding: '0 16px 12px 16px',
      overflow: 'hidden'
    }}>
      {/* Top Header Bar */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        paddingBottom: '12px', 
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '12px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '22px', fontWeight: 700, margin: 0, letterSpacing: '-0.3px' }}>
              Ask MedRule (Interactive Agent)
            </h1>
            <span style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontWeight: 600,
              backgroundColor: '#EBF3EE',
              color: 'var(--primary)',
              border: '1px solid var(--success-border)'
            }}>
              ⚡ Grounded Document Analysis & Deterministic Policy Gating
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '2px 0 0 0' }}>
            Conversational document analysis and policy prior-authorization evaluation with strict intent separation
          </p>
        </div>

        {/* Right Header Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => {
              setMessages([
                {
                  id: `reset-${Date.now()}`,
                  sender: 'agent',
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  text: 'Chat cleared. Attach a clinical note PDF or select an encounter to begin.'
                }
              ]);
            }}
            className="btn btn-secondary"
            style={{ padding: '6px 10px', fontSize: '12px' }}
            title="Start fresh conversation"
          >
            <RefreshCw size={13} />
            <span>Reset Chat</span>
          </button>
        </div>
      </div>

      {/* Main Dual-Panel Workspace */}
      <div style={{ 
        flex: 1, 
        display: 'grid', 
        gridTemplateColumns: '1.25fr 0.95fr', 
        gap: '16px', 
        minHeight: 0,
        overflow: 'hidden'
      }}>
        {/* ========================================================================= */}
        {/* LEFT PANEL: Chat Stream & Message Composer */}
        {/* ========================================================================= */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          backgroundColor: '#FFFFFF',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-sm)',
          overflow: 'hidden',
          minHeight: 0
        }}>
          {/* Quick Suggested Prompt Chips */}
          <div style={{ 
            padding: '8px 12px', 
            backgroundColor: '#FAF9F6', 
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            overflowX: 'auto',
            whiteSpace: 'nowrap'
          }}>
            <Sparkles size={13} color="var(--primary)" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-secondary)', flexShrink: 0 }}>
              Queries:
            </span>
            <button
              onClick={() => handleSend("Summarize the symptoms, diagnoses, examination findings, and treatments in the uploaded PDF.")}
              style={{
                fontSize: '11.5px',
                padding: '4px 8px',
                borderRadius: '12px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: '#FFFFFF',
                cursor: 'pointer',
                color: 'var(--text-primary)'
              }}
            >
              📄 Summarize Document
            </button>
            <button
              onClick={() => handleSend("Extract all conservative treatment, therapies, and clinical durations documented in this note.")}
              style={{
                fontSize: '11.5px',
                padding: '4px 8px',
                borderRadius: '12px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: '#FFFFFF',
                cursor: 'pointer',
                color: 'var(--text-primary)'
              }}
            >
              🔍 Extract Conservative Treatment
            </button>
            <button
              onClick={() => handleSend("Does this request meet the payer's prior-authorization criteria under the applicable policy?")}
              style={{
                fontSize: '11.5px',
                padding: '4px 8px',
                borderRadius: '12px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: '#FFFFFF',
                cursor: 'pointer',
                color: 'var(--text-primary)'
              }}
            >
              ⚡ Evaluate Prior-Auth Criteria
            </button>
            <button
              onClick={() => handleSend("Draft an evidence-based prior-authorization appeal letter citing documented findings.")}
              style={{
                fontSize: '11.5px',
                padding: '4px 8px',
                borderRadius: '12px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: '#FFFFFF',
                cursor: 'pointer',
                color: 'var(--text-primary)'
              }}
            >
              ✍️ Draft Appeal
            </button>
          </div>

          {/* Messages Scroll Area */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            backgroundColor: '#FAFAF8'
          }}>
            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start'
                }}
              >
                {m.sender === 'user' ? (
                  // User Message Bubble
                  <div style={{
                    backgroundColor: 'var(--primary)',
                    color: '#FFFFFF',
                    borderRadius: '14px 14px 4px 14px',
                    padding: '12px 16px',
                    maxWidth: '82%',
                    fontSize: '14px',
                    boxShadow: 'var(--shadow-sm)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px', opacity: 0.85, fontSize: '11px' }}>
                      <User size={12} />
                      <span>Reviewer Query • {m.timestamp}</span>
                    </div>
                    <div>{m.text}</div>
                    {m.attachedFile && (
                      <div style={{
                        marginTop: '8px',
                        fontSize: '11.5px',
                        backgroundColor: 'rgba(255,255,255,0.18)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}>
                        <Paperclip size={11} />
                        <span>{m.attachedFile}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  // Agent Message Bubble
                  <div style={{
                    backgroundColor: '#FFFFFF',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '14px 14px 14px 4px',
                    padding: '14px 18px',
                    width: '100%',
                    maxWidth: '92%',
                    boxShadow: 'var(--shadow-sm)'
                  }}>
                    {/* Header info */}
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      borderBottom: '1px solid var(--border-subtle)',
                      paddingBottom: '6px',
                      marginBottom: '10px',
                      gap: '8px',
                      flexWrap: 'wrap'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <Bot size={15} color="var(--primary)" />
                        <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                          MedRule Copilot
                        </span>
                        {getIntentBadge(m.intent)}
                        {m.modelUsed && (
                          <span style={{
                            fontSize: '10px',
                            backgroundColor: m.isGroq ? '#EBF3EE' : '#F0EFEA',
                            color: m.isGroq ? 'var(--primary)' : 'var(--text-secondary)',
                            padding: '1px 6px',
                            borderRadius: '4px',
                            fontWeight: 600
                          }}>
                            {m.modelUsed}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          onClick={() => copyToClipboard(m.text, m.id)}
                          style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '11px',
                            color: copiedMsgId === m.id ? 'var(--success)' : 'var(--text-muted)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 4px'
                          }}
                          title="Copy response to clipboard"
                        >
                          {copiedMsgId === m.id ? <Check size={12} /> : <Copy size={12} />}
                          <span>{copiedMsgId === m.id ? 'Copied' : 'Copy'}</span>
                        </button>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{m.timestamp}</span>
                      </div>
                    </div>

                    {/* Markdown Body */}
                    {renderFormattedMarkdown(m.text)}

                    {/* Citations Section */}
                    {m.citations && m.citations.length > 0 && (
                      <div style={{
                        marginTop: '12px',
                        paddingTop: '8px',
                        borderTop: '1px dashed var(--border-subtle)',
                        fontSize: '12px'
                      }}>
                        <div style={{ 
                          fontWeight: 600, 
                          color: 'var(--text-secondary)', 
                          marginBottom: '6px', 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: '6px' 
                        }}>
                          <FileText size={12} color="var(--primary)" />
                          <span>Grounded Source Citations:</span>
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {m.citations.map((c, idx) => (
                            <span 
                              key={idx} 
                              style={{
                                backgroundColor: '#FAF9F6',
                                border: '1px solid var(--border-subtle)',
                                borderRadius: '4px',
                                padding: '3px 8px',
                                fontSize: '11px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                              title={c.excerpt ? `"${c.excerpt}"` : undefined}
                            >
                              <strong style={{ color: 'var(--primary)' }}>Page {c.page_number}</strong>
                              {c.document_filename && (
                                <span style={{ color: 'var(--text-muted)' }}>({c.document_filename})</span>
                              )}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Claim-Level Evidence Verification Layer */}
                    {m.verifiedClaims && m.verifiedClaims.length > 0 && (
                      <div style={{
                        marginTop: '12px',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        backgroundColor: '#F8FAFC',
                        border: '1px solid #E2E8F0',
                        fontSize: '12px'
                      }}>
                        <div style={{
                          fontWeight: 700,
                          color: '#334155',
                          marginBottom: '8px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          flexWrap: 'wrap',
                          gap: '6px'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <ShieldCheck size={14} color="#059669" />
                            <span>Claim-Level Evidence Verification ({m.verifiedClaims.length} Claims Evaluated)</span>
                          </div>
                          <span style={{ fontSize: '10.5px', color: '#64748B', fontWeight: 500 }}>
                            Document: {m.documentId ? m.documentId.substring(0, 8) + '...' : 'Active Note'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {m.verifiedClaims.map((claim, cIdx) => {
                            const isSupported = claim.evidence_status === 'SUPPORTED';
                            const isPartial = claim.evidence_status === 'PARTIALLY_SUPPORTED';
                            const isConflicting = claim.evidence_status === 'CONFLICTING';

                            const badgeBg = isSupported ? '#DEF7EC' : (isPartial ? '#FEF3C7' : (isConflicting ? '#FFE4E6' : '#FEE2E2'));
                            const badgeColor = isSupported ? '#03543F' : (isPartial ? '#92400E' : (isConflicting ? '#9F1239' : '#991B1B'));
                            const badgeBorder = isSupported ? '#86EFAC' : (isPartial ? '#FCD34D' : (isConflicting ? '#FDA4AF' : '#FCA5A5'));

                            return (
                              <div
                                key={cIdx}
                                style={{
                                  padding: '7px 10px',
                                  borderRadius: '5px',
                                  backgroundColor: '#FFFFFF',
                                  border: '1px solid #E2E8F0',
                                  fontSize: '11.5px'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                                  <span style={{ fontWeight: 600, color: '#1E293B', flex: 1 }}>
                                    {claim.claim_text}
                                  </span>
                                  <span style={{
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    backgroundColor: badgeBg,
                                    color: badgeColor,
                                    border: `1px solid ${badgeBorder}`,
                                    whiteSpace: 'nowrap'
                                  }}>
                                    {claim.evidence_status}
                                  </span>
                                </div>
                                {claim.evidence_excerpt && (
                                  <div style={{ color: '#475569', fontStyle: 'italic', marginBottom: '3px' }}>
                                    "{claim.evidence_excerpt}"
                                  </div>
                                )}
                                <div style={{ display: 'flex', gap: '10px', fontSize: '10.5px', color: '#64748B', flexWrap: 'wrap' }}>
                                  {claim.source_page && <span>Page: <strong>{claim.source_page}</strong></span>}
                                  {claim.source_document_sha256 && (
                                    <span>SHA-256: <code>{claim.source_document_sha256.substring(0, 10)}...</code></span>
                                  )}
                                  {claim.verification_notes && (
                                    <span style={{ color: isConflicting ? '#B91C1C' : '#64748B' }}>
                                      {claim.verification_notes}
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Validation Warnings */}
                    {m.warnings && m.warnings.length > 0 && (
                      <div style={{ 
                        marginTop: '10px', 
                        padding: '6px 10px', 
                        borderRadius: '6px', 
                        backgroundColor: '#FEF3C7', 
                        border: '1px solid #FCD34D', 
                        fontSize: '11.5px', 
                        color: '#92400E' 
                      }}>
                        <strong>⚠️ Validation Notice:</strong>
                        <ul style={{ margin: '2px 0 0 0', paddingLeft: '16px' }}>
                          {m.warnings.map((w, idx) => (
                            <li key={idx}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Action Bar */}
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'flex-end', 
                      gap: '8px', 
                      marginTop: '12px',
                      paddingTop: '8px',
                      borderTop: '1px solid var(--border-subtle)'
                    }}>
                      <button
                        onClick={() => setActiveRightTab('evidence')}
                        style={{
                          fontSize: '11.5px',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: '1px solid var(--border-subtle)',
                          backgroundColor: '#FAF9F6',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <FileText size={12} color="var(--primary)" />
                        <span>Inspect Document Evidence</span>
                      </button>

                      {activeEvaluation && (
                        <button
                          onClick={() => setActiveRightTab('criteria')}
                          style={{
                            fontSize: '11.5px',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            border: '1px solid var(--border-subtle)',
                            backgroundColor: '#FAF9F6',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <ShieldCheck size={12} color="var(--primary)" />
                          <span>Inspect Rule Criteria</span>
                        </button>
                      )}

                      <button
                        onClick={() => setActiveRightTab('trace')}
                        style={{
                          fontSize: '11.5px',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          backgroundColor: 'var(--primary)',
                          color: '#FFFFFF',
                          border: 'none',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <Activity size={12} />
                        <span>View Decision Trace</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {isProcessing && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '10px', 
                color: 'var(--text-secondary)', 
                fontSize: '13px',
                padding: '10px 14px',
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
                width: 'fit-content'
              }}>
                <Sparkles size={16} className="animate-spin" color="var(--primary)" />
                <span>MedRule Copilot is analyzing clinical documentation & evaluating criteria...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Composer Bar */}
          <div style={{
            padding: '12px 16px',
            backgroundColor: '#FFFFFF',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            {/* Context Selector & Attached File Bar */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', fontSize: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Encounter Context:</span>
                <select
                  value={selectedCaseId}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (!val) {
                      setSelectedCaseId('');
                      setActiveEvaluation(null);
                      setActiveTrace(null);
                      if (!activeDocument) {
                        setActiveNoteRecord(null);
                        setAttachedFileName(null);
                      }
                    } else {
                      const match = SAMPLE_CASES.find(c => c.id === val);
                      if (match) handleSelectSampleCase(match);
                    }
                  }}
                  style={{
                    padding: '3px 8px',
                    fontSize: '12px',
                    borderRadius: '4px',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: '#FAF9F6',
                    cursor: 'pointer',
                    fontWeight: 600,
                    maxWidth: '280px'
                  }}
                >
                  <option value="">-- No Encounter (Standalone Document Analysis) --</option>
                  {SAMPLE_CASES.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} - {c.procedure}
                    </option>
                  ))}
                </select>
              </div>

              {attachedFileName && (
                <span style={{
                  fontSize: '11.5px',
                  backgroundColor: '#EBF3EE',
                  border: '1px solid var(--success-border)',
                  color: 'var(--primary)',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <FileCheck size={12} />
                  <span style={{ fontWeight: 600 }}>{attachedFileName}</span>
                  {activeDocument?.totalPages && (
                    <span style={{ fontSize: '10.5px', opacity: 0.85 }}>({activeDocument.totalPages}p)</span>
                  )}
                  {activeDocument?.id && (
                    <span style={{ fontSize: '10px', fontFamily: 'monospace', opacity: 0.8 }} title={`Document ID: ${activeDocument.id}`}>
                      ID: {activeDocument.id.substring(0, 8)}
                    </span>
                  )}
                  {activeDocument?.sha256 && (
                    <span style={{ fontSize: '10px', fontFamily: 'monospace', opacity: 0.75 }} title={`SHA-256: ${activeDocument.sha256}`}>
                      SHA: {activeDocument.sha256.substring(0, 8)}...
                    </span>
                  )}
                  <button 
                    onClick={() => {
                      setAttachedFileName(null);
                      setActiveDocument(null);
                      if (!selectedCaseId) {
                        setActiveNoteRecord(null);
                        setActiveEvaluation(null);
                        setActiveTrace(null);
                      }
                    }} 
                    style={{ border: 'none', background: 'none', cursor: 'pointer', padding: 0, color: 'inherit' }}
                    title="Detach PDF"
                  >
                    <X size={11} />
                  </button>
                </span>
              )}
            </div>

            {/* Input Composer Box */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: '#FAF9F6',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '6px 12px'
            }}>
              {/* Attach PDF File Button */}
              <label 
                style={{ cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }} 
                title="Attach any clinical note PDF from computer for grounded document analysis"
              >
                <Paperclip size={18} color="var(--text-secondary)" />
                <input
                  type="file"
                  accept=".pdf"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      const file = e.target.files[0];
                      handleFileUpload(file);
                    }
                  }}
                />
              </label>

              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={attachedFileName ? `Ask about "${attachedFileName}" (e.g. summarize symptoms, check treatments)...` : "Ask any document analysis, criteria, or appeal question..."}
                disabled={isProcessing}
                style={{
                  flex: 1,
                  border: 'none',
                  outline: 'none',
                  fontSize: '13.5px',
                  backgroundColor: 'transparent',
                  color: 'var(--text-primary)'
                }}
              />

              <button
                onClick={() => handleSend()}
                disabled={isProcessing || !inputText.trim()}
                className="btn btn-primary"
                style={{ 
                  padding: '8px 14px', 
                  borderRadius: '6px', 
                  opacity: (!inputText.trim() || isProcessing) ? 0.6 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Send size={14} />
                <span style={{ fontSize: '13px' }}>Send</span>
              </button>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* RIGHT PANEL: Live Clinical & Policy Inspector */}
        {/* ========================================================================= */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          backgroundColor: '#FFFFFF',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-sm)',
          overflow: 'hidden',
          minHeight: 0
        }}>
          {/* Tab Navigation Header */}
          <div style={{ 
            display: 'flex', 
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: '#FAF9F6',
            padding: '4px 8px 0 8px',
            gap: '4px'
          }}>
            <button
              onClick={() => setActiveRightTab('evidence')}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeRightTab === 'evidence' ? '2px solid var(--primary)' : '2px solid transparent',
                backgroundColor: 'transparent',
                color: activeRightTab === 'evidence' ? 'var(--primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <FileText size={13} />
              <span>Extracted Evidence</span>
            </button>

            <button
              onClick={() => setActiveRightTab('criteria')}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeRightTab === 'criteria' ? '2px solid var(--primary)' : '2px solid transparent',
                backgroundColor: 'transparent',
                color: activeRightTab === 'criteria' ? 'var(--primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <ShieldCheck size={13} />
              <span>Policy Criteria</span>
            </button>

            <button
              onClick={() => setActiveRightTab('document')}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeRightTab === 'document' ? '2px solid var(--primary)' : '2px solid transparent',
                backgroundColor: 'transparent',
                color: activeRightTab === 'document' ? 'var(--primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <FileCheck size={13} />
              <span>Document Text</span>
            </button>

            <button
              onClick={() => setActiveRightTab('trace')}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeRightTab === 'trace' ? '2px solid var(--primary)' : '2px solid transparent',
                backgroundColor: 'transparent',
                color: activeRightTab === 'trace' ? 'var(--primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginLeft: 'auto'
              }}
            >
              <Activity size={13} color="var(--primary)" />
              <span>Decision Trace</span>
            </button>
          </div>

          {/* Right Panel Body */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {/* TAB 1: EXTRACTED NOTE EVIDENCE */}
            {activeRightTab === 'evidence' && (
              <div>
                {/* Patient Summary Card */}
                {(activeNoteRecord || activeDocument) ? (
                  <div style={{
                    backgroundColor: '#FAF9F6',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '14px',
                    marginBottom: '16px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0 }}>
                        {activeNoteRecord?.patient_name || activeDocument?.patientName || 'Clinical Subject'}
                      </h3>
                      <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: '#EBF3EE', color: 'var(--primary)', fontWeight: 600 }}>
                        {activeDocument?.id || activeNoteRecord?.case_id || selectedCaseId || 'DOC-STANDALONE'}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                      <div><strong>DOS:</strong> {activeNoteRecord?.date_of_visit || activeDocument?.dateOfVisit || 'N/A'}</div>
                      <div><strong>Insurer:</strong> {activeNoteRecord?.insurance_plan || activeDocument?.insurer || 'Not specified'}</div>
                      <div><strong>Order:</strong> {activeNoteRecord?.procedure_requested || activeDocument?.procedure || 'Unspecified'}</div>
                      <div><strong>Facility:</strong> {activeNoteRecord?.facility || activeDocument?.facility || 'Document Ingestion Source'}</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px dashed var(--border-subtle)', marginBottom: '16px' }}>
                    <FileText size={24} color="var(--text-secondary)" style={{ margin: '0 auto 8px auto', opacity: 0.6 }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, margin: '0 0 4px 0' }}>No Document or Case Loaded</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                      Attach a PDF or select an encounter to inspect extracted evidence facts.
                    </p>
                  </div>
                )}

                {/* Conservative Therapy Dynamic Card (if fact exists) */}
                {activeNoteRecord?.facts?.conservative_therapy && (
                  <div style={{
                    backgroundColor: '#EBF3EE',
                    border: '1px solid var(--success-border)',
                    borderRadius: '8px',
                    padding: '12px 14px',
                    marginBottom: '16px',
                    fontSize: '12.5px'
                  }}>
                    <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={14} />
                      <span>Documented Conservative Therapy</span>
                    </div>
                    <p style={{ margin: 0, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                      {activeNoteRecord.facts.conservative_therapy.excerpt || String(activeNoteRecord.facts.conservative_therapy.value || 'Documented')}
                    </p>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Source: Page {activeNoteRecord.facts.conservative_therapy.source_page || 1} • Status: {activeNoteRecord.facts.conservative_therapy.status}
                    </div>
                  </div>
                )}

                {/* Extracted Facts List */}
                <h4 style={{ fontSize: '13px', fontWeight: 700, margin: '0 0 10px 0', color: 'var(--text-primary)' }}>
                  Clinical Fact Extractions ({Object.keys(activeNoteRecord?.facts || activeDocument?.facts || {}).length} elements)
                </h4>

                {Object.keys(activeNoteRecord?.facts || activeDocument?.facts || {}).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries((activeNoteRecord?.facts || activeDocument?.facts) as Record<string, any>).map(([key, fact]) => (
                      <div key={key} style={{
                        padding: '10px 12px',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        fontSize: '12px',
                        backgroundColor: '#FFFFFF'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{fact.label || key}</span>
                          <span style={{
                            fontSize: '10.5px',
                            fontWeight: 700,
                            padding: '1px 6px',
                            borderRadius: '3px',
                            backgroundColor: fact.status === 'EXPLICIT' ? '#EBF3EE' : (fact.status === 'ABSENT' ? '#FEF3C7' : '#FDF2F2'),
                            color: fact.status === 'EXPLICIT' ? 'var(--primary)' : (fact.status === 'ABSENT' ? '#92400E' : 'var(--danger)')
                          }}>
                            {fact.status}
                          </span>
                        </div>
                        {fact.excerpt && (
                          <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: '2px' }}>
                            "{fact.excerpt}"
                          </div>
                        )}
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Page: {fact.source_page || 1} • Confidence: {Math.round((fact.confidence || 0.95) * 100)}%
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
                    No extracted clinical facts currently available.
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: POLICY CRITERIA CHECKLIST */}
            {activeRightTab === 'criteria' && (
              <div>
                {activeEvaluation ? (
                  <div>
                    <div style={{ marginBottom: '14px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>
                          {activeEvaluation.policy_id} Rulebook Criteria
                        </h3>
                        <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', backgroundColor: '#EBF3EE', color: 'var(--primary)', fontWeight: 600 }}>
                          Deterministic Evaluation ✅
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                        {activeEvaluation.procedure} • Insurer: {activeEvaluation.insurer}
                      </p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {activeEvaluation.criteria_results?.map((cr) => (
                        <div key={cr.rule_id} style={{
                          padding: '10px 12px',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '6px',
                          fontSize: '12px',
                          backgroundColor: '#FFFFFF'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontWeight: 600 }}>{cr.criterion_name}</span>
                            <span style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              color: cr.status === 'MET' ? 'var(--success)' : (cr.status === 'NOT_DOCUMENTED' ? '#D97706' : 'var(--danger)')
                            }}>
                              {cr.status === 'MET' ? '✅ Satisfied' : (cr.status === 'NOT_DOCUMENTED' ? '⚠️ Missing' : '❌ Not Met')}
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: '11.5px', marginBottom: '4px' }}>
                            <strong>Mandate:</strong> {cr.requirement}
                          </div>
                          {cr.evidence_excerpt && (
                            <div style={{ fontSize: '11.5px', fontStyle: 'italic', color: 'var(--text-primary)', backgroundColor: '#FAF9F6', padding: '4px 6px', borderRadius: '4px' }}>
                              "{cr.evidence_excerpt}" (Page {cr.source_page || 1})
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px dashed var(--border-subtle)' }}>
                    <ShieldCheck size={28} color="var(--primary)" style={{ margin: '0 auto 8px auto', opacity: 0.7 }} />
                    <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 6px 0' }}>No Active Policy Evaluation</h4>
                    <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                      Document analysis operates freely on uploaded clinical notes without requiring an insurance policy.
                      To run deterministic criteria evaluation, select a clinical encounter with an applicable verified payer rulebook.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: DOCUMENT TEXT INSPECTOR */}
            {activeRightTab === 'document' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, margin: 0 }}>
                      Digital Text Stream ({activeNoteRecord?.total_pages || activeDocument?.totalPages || 1} Pages)
                    </h4>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                      ID: {activeDocument?.id || activeNoteRecord?.document_id || activeNoteRecord?.case_id || 'DOC-STANDALONE'}
                    </span>
                  </div>
                  {activeNoteRecord?.case_id && (
                    <a
                      href={`http://localhost:8000/api/notes/${activeNoteRecord.case_id}/document`}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        fontSize: '11.5px',
                        color: 'var(--primary)',
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontWeight: 600
                      }}
                    >
                      <span>Open Native PDF</span>
                      <ExternalLink size={11} />
                    </a>
                  )}
                </div>

                <div style={{
                  backgroundColor: '#FAF9F6',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '12px',
                  fontSize: '11.5px',
                  fontFamily: 'monospace',
                  lineHeight: 1.5,
                  maxHeight: '460px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  color: 'var(--text-primary)'
                }}>
                  {(activeNoteRecord?.raw_pages_text || activeDocument?.rawPagesText || []).length > 0 ? (
                    (activeNoteRecord?.raw_pages_text || activeDocument?.rawPagesText || []).map((p: any, idx: number) => (
                      <div key={idx} style={{ marginBottom: '14px' }}>
                        <div style={{ fontWeight: 700, color: 'var(--primary)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '2px', marginBottom: '6px' }}>
                          --- PAGE {p.page_number} ---
                        </div>
                        {p.text}
                      </div>
                    ))
                  ) : (
                    <div>No raw text stream recorded for this document.</div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 4: AGENT DECISION TRACE & PROVENANCE */}
            {activeRightTab === 'trace' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                  <div>
                    <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Activity size={16} color="var(--primary)" />
                      Agent Decision Trace & Provenance
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                      Auditable trace linking query intent, document hash, valid page bounds, policy compatibility, and evaluation provenance.
                    </p>
                  </div>
                  {activeTrace?.trace_id && (
                    <span style={{ fontSize: '11px', fontFamily: 'monospace', padding: '3px 8px', borderRadius: '4px', backgroundColor: '#F0EFEA', border: '1px solid var(--border-subtle)' }}>
                      {activeTrace.trace_id}
                    </span>
                  )}
                </div>

                {!activeTrace ? (
                  <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px dashed var(--border-subtle)' }}>
                    <Activity size={24} color="var(--text-secondary)" style={{ margin: '0 auto 8px auto', opacity: 0.6 }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, margin: '0 0 4px 0' }}>No Active Decision Trace</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                      Send a conversational query or select an encounter to generate an auditable decision trace.
                    </p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {/* SECTION 1: REQUEST & INTENT */}
                    <div style={{ backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '12px 14px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        1. Request & Intent Classification
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                        <div><strong>Intent:</strong> <span style={{ fontWeight: 700, color: 'var(--primary)' }}>{activeTrace.intent || 'DOCUMENT_ANALYSIS'}</span></div>
                        <div><strong>Case ID:</strong> <span style={{ fontFamily: 'monospace' }}>{activeTrace.case_id || 'None (Standalone)'}</span></div>
                        <div><strong>Patient:</strong> {activeTrace.patient_name || 'N/A'}</div>
                        <div><strong>Payer:</strong> {activeTrace.payer || 'Not applicable'}</div>
                        <div><strong>Requested Service:</strong> {activeTrace.requested_service || 'Document Analysis'}</div>
                        <div><strong>Contrast Status:</strong> {activeTrace.contrast_status || 'N/A'}</div>
                      </div>
                    </div>

                    {/* SECTION 2: UPLOADED DOCUMENTS & BOUNDS */}
                    <div style={{ backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '12px 14px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        2. Document Provenance & Page Bounds
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px', marginBottom: '8px' }}>
                        <div><strong>Document:</strong> {activeTrace.document_filename || 'Uploaded Document'}</div>
                        <div><strong>Extraction Status:</strong> <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{activeTrace.extraction_status || 'EXTRACTED'}</span></div>
                        <div><strong>Valid Page Count:</strong> <strong>{activeTrace.valid_page_count || 1} {activeTrace.valid_page_count === 1 ? 'Page' : 'Pages'}</strong></div>
                        <div><strong>Document ID:</strong> <span style={{ fontFamily: 'monospace' }}>{activeTrace.document_id || 'DOC-STANDALONE'}</span></div>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace', marginBottom: '8px', wordBreak: 'break-all' }}>
                        SHA-256: {activeTrace.document_sha256 || 'Verified'}
                      </div>
                      <div style={{ fontSize: '11.5px', padding: '6px 10px', borderRadius: '6px', backgroundColor: '#EBF3EE', border: '1px solid var(--success-border)', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <ShieldCheck size={14} />
                        <span><strong>Citation Guard Active:</strong> Valid citations constrained strictly to Pages 1–{activeTrace.valid_page_count || 1}.</span>
                      </div>
                    </div>

                    {/* SECTION 3: POLICY COMPATIBILITY */}
                    <div style={{ 
                      backgroundColor: activeTrace.compatibility_status === 'COMPATIBLE' ? '#FAF9F6' : (activeTrace.compatibility_status === 'NOT_APPLICABLE' ? '#FAF9F6' : '#FEF2F2'), 
                      borderRadius: '8px', 
                      border: `1px solid ${activeTrace.compatibility_status === 'COMPATIBLE' || activeTrace.compatibility_status === 'NOT_APPLICABLE' ? 'var(--border-subtle)' : '#FCA5A5'}`, 
                      padding: '12px 14px' 
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-secondary)' }}>
                          3. Policy Compatibility & Lifecycle Gate
                        </div>
                        <span style={{ 
                          fontSize: '11px', 
                          fontWeight: 700, 
                          padding: '2px 8px', 
                          borderRadius: '12px',
                          backgroundColor: activeTrace.compatibility_status === 'COMPATIBLE' ? '#DEF7EC' : (activeTrace.compatibility_status === 'NOT_APPLICABLE' ? '#F0EFEA' : '#FDE8E8'),
                          color: activeTrace.compatibility_status === 'COMPATIBLE' ? '#03543F' : (activeTrace.compatibility_status === 'NOT_APPLICABLE' ? 'var(--text-secondary)' : '#9B1C1C')
                        }}>
                          {activeTrace.compatibility_status || 'NOT_APPLICABLE'}
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                        <div><strong>Policy ID:</strong> {activeTrace.selected_policy_id || 'None (Document Analysis)'}</div>
                        <div><strong>Policy Version:</strong> {activeTrace.policy_version || 'None'}</div>
                      </div>

                      {activeTrace.compatibility_status !== 'COMPATIBLE' && activeTrace.compatibility_status !== 'NOT_APPLICABLE' && activeTrace.compatibility_reasons?.length > 0 && (
                        <div style={{ marginTop: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: '#FFFFFF', border: '1px solid #FCA5A5', color: '#991B1B', fontSize: '12px' }}>
                          <strong>Blocker Notice:</strong>
                          <ul style={{ margin: '4px 0 0 0', paddingLeft: '18px' }}>
                            {activeTrace.compatibility_reasons.map((r: string, idx: number) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* SECTION 4: LLM NARRATIVE VALIDATION */}
                    <div style={{ backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '12px 14px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        4. LLM Narrative & Evidence Consistency
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px', marginBottom: '8px' }}>
                        <div><strong>LLM Invoked:</strong> {activeTrace.llm_invoked ? `Yes (${activeTrace.llm_model || 'Groq'})` : 'No (Deterministic Engine)'}</div>
                        <div><strong>Validation Status:</strong> <span style={{
                          fontWeight: 700,
                          color: activeTrace.narrative_validation_passed ? 'var(--primary)' : 'var(--text-secondary)'
                        }}>
                          {activeTrace.narrative_validation_status || (activeTrace.narrative_validation_passed ? 'PASSED' : 'CHECKED')}
                        </span></div>
                      </div>
                    </div>

                    {/* SECTION 5: CLAIM-LEVEL EVIDENCE VERIFICATION */}
                    {activeTrace.verified_claims && activeTrace.verified_claims.length > 0 && (
                      <div style={{ backgroundColor: '#FAF9F6', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '12px 14px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-secondary)' }}>
                            5. Claim-Level Evidence Verification ({activeTrace.verified_claims.length} Claims)
                          </div>
                          <span style={{ fontSize: '11px', color: 'var(--primary)', fontWeight: 600 }}>
                            {activeTrace.verified_claims.filter((c: any) => c.evidence_status === 'SUPPORTED').length} Supported
                          </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {activeTrace.verified_claims.map((claim: any, idx: number) => (
                            <div key={idx} style={{ padding: '6px 8px', borderRadius: '4px', backgroundColor: '#FFFFFF', border: '1px solid var(--border-subtle)', fontSize: '11.5px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', marginBottom: '2px' }}>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{claim.claim_text}</span>
                                <span style={{
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  padding: '1px 5px',
                                  borderRadius: '3px',
                                  backgroundColor: claim.evidence_status === 'SUPPORTED' ? '#DEF7EC' : (claim.evidence_status === 'PARTIALLY_SUPPORTED' ? '#FEF3C7' : '#FEE2E2'),
                                  color: claim.evidence_status === 'SUPPORTED' ? '#03543F' : (claim.evidence_status === 'PARTIALLY_SUPPORTED' ? '#92400E' : '#991B1B')
                                }}>
                                  {claim.evidence_status}
                                </span>
                              </div>
                              {claim.evidence_excerpt && (
                                <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '11px' }}>
                                  "{claim.evidence_excerpt}" (Page {claim.source_page || 1})
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AskMedRuleView;
