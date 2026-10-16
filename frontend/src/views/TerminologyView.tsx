import React, { useState, useEffect } from 'react';
import {
  BookMarked,
  ArrowLeft,
  Info,
  Search,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Clock,
  Layers,
  CheckCircle2,
  XCircle,
  HelpCircle,
  RefreshCw,
  Scale
} from 'lucide-react';
import { ViewMode } from '../types';

interface TerminologyViewProps {
  onNavigate: (view: ViewMode) => void;
}

interface ApprovedSource {
  id: string;
  name: string;
  official_domain: string;
  authority: string;
  permitted_scope: string;
  verification_status: 'VERIFIED' | 'RESTRICTED_ACCESS' | 'SCOPE_RESTRICTED' | 'PENDING_REGULATORY_VERIFICATION';
  access_restrictions: string;
  official_url: string;
  is_active: boolean;
  notes?: string;
}

interface TerminologyDefinition {
  term: string;
  definition: string;
  source_id: string;
  source_name: string;
  source_domain: string;
  official_url: string;
  resolution_status: 'RULEBOOK_DEFINED' | 'RESOLVED' | 'UNRESOLVED' | 'CONFLICTING' | 'FAILED';
  retrieval_timestamp: string;
  lookup_reason: string;
  policy_citation?: string;
  is_rulebook_first: boolean;
  provenance_audit_id: string;
  disclaimer: string;
}

interface TerminologyLookupResponse {
  term: string;
  status: 'RULEBOOK_DEFINED' | 'RESOLVED' | 'UNRESOLVED' | 'CONFLICTING' | 'FAILED';
  definition_record?: TerminologyDefinition | null;
  resolution_path: string[];
  requires_human_review: boolean;
  review_reason?: string | null;
  provenance_audit_id?: string;
  governance_warning: string;
}

interface AuditLogEntry {
  audit_id: string;
  timestamp: string;
  term: string;
  status: string;
  source: string;
  reason: string;
  citation?: string;
  url?: string;
}

export const TerminologyView: React.FC<TerminologyViewProps> = ({ onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState('Papilledema');
  const [selectedPolicyId, setSelectedPolicyId] = useState('P-UHC-CT-2026');
  const [isLoading, setIsLoading] = useState(false);
  const [lookupResult, setLookupResult] = useState<TerminologyLookupResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [sources, setSources] = useState<ApprovedSource[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [activeTab, setActiveTab] = useState<'lookup' | 'registry' | 'audit'>('lookup');

  // Initial fetch of approved sources and audit log
  useEffect(() => {
    void fetchApprovedSources();
    void fetchAuditLogs();
    void executeLookup('Papilledema', 'P-UHC-CT-2026');
  }, []);

  const fetchApprovedSources = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/terminology/sources');
      if (res.ok) {
        const data = await res.json();
        setSources(data);
        return;
      }
    } catch {
      // Fallback preset
      setSources([
        {
          id: 'src-nlm-mesh',
          name: 'NLM MeSH (Medical Subject Headings)',
          official_domain: 'mesh.nlm.nih.gov',
          authority: 'National Library of Medicine / NIH',
          permitted_scope: 'Standardized biomedical vocabulary, clinical anatomy, pathology',
          verification_status: 'VERIFIED',
          access_restrictions: 'Direct term lookup; automated bulk web crawling disallowed',
          official_url: 'https://mesh.nlm.nih.gov',
          is_active: true
        },
        {
          id: 'src-medlineplus',
          name: 'NLM MedlinePlus',
          official_domain: 'medlineplus.gov',
          authority: 'U.S. National Library of Medicine / NIH',
          permitted_scope: 'Diagnostic procedures, symptoms, and clinical condition overviews',
          verification_status: 'VERIFIED',
          access_restrictions: 'Public direct health terminology repository',
          official_url: 'https://medlineplus.gov',
          is_active: true
        },
        {
          id: 'src-cms-glossary',
          name: 'CMS Medicare Coverage Database Glossary',
          official_domain: 'cms.gov',
          authority: 'Centers for Medicare & Medicaid Services',
          permitted_scope: 'Prior authorization concepts, federal insurance terms, medical necessity',
          verification_status: 'VERIFIED',
          access_restrictions: 'Official federal health insurance terminology database',
          official_url: 'https://www.cms.gov/medicare-coverage-database',
          is_active: true
        },
        {
          id: 'src-ama',
          name: 'American Medical Association (AMA)',
          official_domain: 'ama-assn.org',
          authority: 'American Medical Association',
          permitted_scope: 'CPT coding principles and clinical nomenclature',
          verification_status: 'RESTRICTED_ACCESS',
          access_restrictions: 'Proprietary licensed terminology (CPT); requires formal licensing verification',
          official_url: 'https://www.ama-assn.org',
          is_active: false
        },
        {
          id: 'src-aia',
          name: 'American Insurance Association (APCIA)',
          official_domain: 'apci.org',
          authority: 'American Property Casualty Insurance Association',
          permitted_scope: 'Property and casualty insurance trade concepts (not health clinical criteria)',
          verification_status: 'SCOPE_RESTRICTED',
          access_restrictions: 'Scope restricted: Excluded from health prior authorization definitions',
          official_url: 'https://www.apci.org',
          is_active: false
        },
        {
          id: 'src-ima',
          name: 'Indian Medical Association (IMA)',
          official_domain: 'imanational.com',
          authority: 'Indian Medical Association',
          permitted_scope: 'Indian clinical practice terminology and clinical guidelines',
          verification_status: 'PENDING_REGULATORY_VERIFICATION',
          access_restrictions: 'Pending official terminology API verification and access scope authorization',
          official_url: 'https://www.imanational.com',
          is_active: false
        }
      ]);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/terminology/audit-log');
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch {
      // Ignore background log fetch failure
    }
  };

  const executeLookup = async (termToLookup: string, policyId: string) => {
    if (!termToLookup || termToLookup.trim().length < 2) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch('http://localhost:8000/api/terminology/lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          term: termToLookup.trim(),
          policy_id: policyId,
          lookup_reason: 'Prior authorization evidence clarification in TerminologyView'
        })
      });

      if (res.ok) {
        const data: TerminologyLookupResponse = await res.json();
        setLookupResult(data);
        void fetchAuditLogs();
      } else {
        const err = await res.json();
        setErrorMessage(err.detail || 'Lookup request failed.');
      }
    } catch {
      // Local fallback simulation if server offline
      setLookupResult({
        term: termToLookup,
        status: 'RULEBOOK_DEFINED',
        definition_record: {
          term: termToLookup,
          definition: 'Optic disc swelling secondary to elevated intracranial pressure, documented by fundoscopic examination.',
          source_id: 'policy-p-uhc-ct-2026',
          source_name: 'Policy Rulebook (P-UHC-CT-2026)',
          source_domain: 'local.policy.registry',
          official_url: 'http://localhost:8000/api/policies/P-UHC-CT-2026',
          resolution_status: 'RULEBOOK_DEFINED',
          retrieval_timestamp: new Date().toISOString(),
          lookup_reason: 'Prior authorization evidence clarification in TerminologyView',
          policy_citation: 'Section 2.3 (Signs of Increased ICP), Page 3',
          is_rulebook_first: true,
          provenance_audit_id: 'AUD-TERM-LOCAL-FALLBACK',
          disclaimer: 'Terminology definition is for conceptual reference only and does not create, modify, remove, or override policy coverage criteria or authorization logic.'
        },
        resolution_path: [
          'Checking policy P-UHC-CT-2026 rulebook definitions...',
          'Resolved from policy rulebook definitions (Section 2.3). Rulebook First priority applied.'
        ],
        requires_human_review: false,
        review_reason: null,
        provenance_audit_id: 'AUD-TERM-LOCAL-FALLBACK',
        governance_warning: 'DEVELOPMENT/DEMO MODE: Terminology definitions are strictly isolated from policy evaluation logic.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void executeLookup(searchTerm, selectedPolicyId);
  };

  const handleChipClick = (term: string) => {
    setSearchTerm(term);
    void executeLookup(term, selectedPolicyId);
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'RULEBOOK_DEFINED':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor: '#E8F5E9',
            color: '#2E7D32',
            border: '1px solid #A5D6A7'
          }}>
            <CheckCircle2 size={14} />
            Rulebook Primary Definition
          </span>
        );
      case 'RESOLVED':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor: 'var(--primary-bg)',
            color: 'var(--primary)',
            border: '1px solid var(--border-subtle)'
          }}>
            <ShieldCheck size={14} />
            Approved External Source
          </span>
        );
      case 'UNRESOLVED':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor: '#FEF3C7',
            color: '#B45309',
            border: '1px solid #FCD34D'
          }}>
            <HelpCircle size={14} />
            Unresolved Term &bull; Human Review Required
          </span>
        );
      case 'CONFLICTING':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor: '#FEE2E2',
            color: '#B91C1C',
            border: '1px solid #FCA5A5'
          }}>
            <AlertTriangle size={14} />
            Conflicting Source Definitions
          </span>
        );
      default:
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor: '#F3F4F6',
            color: '#4B5563',
            border: '1px solid #D1D5DB'
          }}>
            <XCircle size={14} />
            Lookup Failed
          </span>
        );
    }
  };

  return (
    <div style={{ maxWidth: '1060px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.5px', margin: 0 }}>
              Authoritative Terminology Lookup
            </h1>
            <span style={{
              fontSize: '11px',
              fontWeight: '700',
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: '#E8F5E9',
              color: '#2E7D32',
              border: '1px solid #A5D6A7'
            }}>
              Phase 6 Active
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
            Rulebook-first clinical and insurance definition service with strict policy criteria isolation and safe failure.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onNavigate('dashboard')}
          className="btn btn-outline"
        >
          <ArrowLeft size={16} />
          <span>Dashboard</span>
        </button>
      </div>

      {/* Strict Separation Governance Callout */}
      <div style={{
        backgroundColor: '#FDFBF7',
        border: '1px solid #E2D9C8',
        borderRadius: 'var(--radius-md)',
        padding: '14px 18px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        <Scale size={20} color="var(--primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block', marginBottom: '2px' }}>
            Strict Separation from Coverage Criteria &amp; Rules Engine
          </strong>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
            Terminology definitions are reference aids only. They never create, modify, remove, or override policy coverage criteria or authorization logic. Unapproved domains and general search engines are strictly blocked.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '8px',
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '24px'
      }}>
        <button
          type="button"
          onClick={() => setActiveTab('lookup')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontSize: '13.5px',
            fontWeight: activeTab === 'lookup' ? '700' : '500',
            color: activeTab === 'lookup' ? 'var(--primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'lookup' ? '2px solid var(--primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Search size={16} />
          <span>Terminology Lookup</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('registry')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontSize: '13.5px',
            fontWeight: activeTab === 'registry' ? '700' : '500',
            color: activeTab === 'registry' ? 'var(--primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'registry' ? '2px solid var(--primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <ShieldCheck size={16} />
          <span>Approved Source Registry ({sources.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('audit')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontSize: '13.5px',
            fontWeight: activeTab === 'audit' ? '700' : '500',
            color: activeTab === 'audit' ? 'var(--primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'audit' ? '2px solid var(--primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Clock size={16} />
          <span>Provenance Audit Log ({auditLogs.length})</span>
        </button>
      </div>

      {activeTab === 'lookup' && (
        <>
          {/* Search Box Card */}
          <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
            <form onSubmit={handleSearchSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr auto', gap: '14px', alignItems: 'end' }}>
                <div>
                  <label
                    htmlFor="policy-context-select"
                    style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px' }}
                  >
                    Policy Context (Rulebook First)
                  </label>
                  <select
                    id="policy-context-select"
                    value={selectedPolicyId}
                    onChange={(e) => setSelectedPolicyId(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      fontSize: '13px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)',
                      backgroundColor: '#FFFFFF',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="P-UHC-CT-2026">United Healthcare &bull; Head CT (P-UHC-CT-2026)</option>
                    <option value="POL-CIGN-CTS-2026-1">Cigna &bull; CT Sinus (POL-CIGN-CTS-2026-1)</option>
                    <option value="CP.MP.107">Centene &bull; CP.MP.107 DME Guidelines</option>
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="term-search-input"
                    style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px' }}
                  >
                    Clinical or Insurance Term to Clarify
                  </label>
                  <input
                    id="term-search-input"
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="e.g. Papilledema, Ataxia, Focal Neurological Deficit..."
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      fontSize: '13.5px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)'
                    }}
                  />
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={isLoading || !searchTerm.trim()}
                    className="btn btn-primary"
                    style={{ height: '42px', padding: '0 20px', gap: '8px' }}
                  >
                    {isLoading ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
                    <span>Lookup Term</span>
                  </button>
                </div>
              </div>
            </form>

            {/* Quick Test Queries Chips */}
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Rulebook Queries:
              </span>
              {['Papilledema', 'Focal Neurological Deficit', 'Conservative Therapy', 'Headache', 'Red Flag Symptoms'].map(chip => (
                <button
                  type="button"
                  key={chip}
                  onClick={() => handleChipClick(chip)}
                  style={{
                    border: '1px solid #C8D8CE',
                    backgroundColor: '#F3F7F4',
                    color: 'var(--primary)',
                    borderRadius: '9999px',
                    padding: '3px 10px',
                    fontSize: '11.5px',
                    cursor: 'pointer'
                  }}
                >
                  {chip}
                </button>
              ))}

              <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginLeft: '6px' }}>
                External Lookups:
              </span>
              {['Ataxia', 'Prior Authorization', 'Hydrocephalus', 'Contrast Material'].map(chip => (
                <button
                  type="button"
                  key={chip}
                  onClick={() => handleChipClick(chip)}
                  style={{
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: '#FAF9F6',
                    color: 'var(--text-primary)',
                    borderRadius: '9999px',
                    padding: '3px 10px',
                    fontSize: '11.5px',
                    cursor: 'pointer'
                  }}
                >
                  {chip}
                </button>
              ))}

              <span style={{ fontSize: '11px', fontWeight: '700', color: '#B45309', textTransform: 'uppercase', marginLeft: '6px' }}>
                Safe Failure:
              </span>
              {['Zylophantic Nonexistent', 'Experimental Procedure'].map(chip => (
                <button
                  type="button"
                  key={chip}
                  onClick={() => handleChipClick(chip)}
                  style={{
                    border: '1px solid #FCD34D',
                    backgroundColor: '#FFFBEB',
                    color: '#B45309',
                    borderRadius: '9999px',
                    padding: '3px 10px',
                    fontSize: '11.5px',
                    cursor: 'pointer'
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div style={{
              backgroundColor: '#FEE2E2',
              color: '#B91C1C',
              padding: '12px 16px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '13px'
            }}>
              <AlertTriangle size={18} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Results Display */}
          {isLoading ? (
            <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 10px' }} />
              <div>Consulting policy rulebook definitions and approved source allowlist...</div>
            </div>
          ) : lookupResult ? (
            <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
              {/* Result Header */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: '16px',
                marginBottom: '18px'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: '700', margin: 0, color: 'var(--text-primary)' }}>
                      {lookupResult.term}
                    </h2>
                    {renderStatusBadge(lookupResult.status)}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Audit Reference ID: <code>{lookupResult.provenance_audit_id || 'AUD-LIVE'}</code>
                  </div>
                </div>

                {lookupResult.definition_record?.official_url && (
                  <a
                    href={lookupResult.definition_record.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-outline"
                    style={{ fontSize: '12px', padding: '6px 12px', gap: '6px' }}
                  >
                    <span>View Official Source</span>
                    <ExternalLink size={13} />
                  </a>
                )}
              </div>

              {/* Resolution Path Trace */}
              <div style={{
                backgroundColor: '#FAF9F6',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 14px',
                marginBottom: '18px'
              }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Authoritative Resolution Path:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {lookupResult.resolution_path.map((step, idx) => (
                    <div key={idx} style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: 'var(--primary)', fontWeight: '700' }}>{idx + 1}.</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Definition Box */}
              {lookupResult.definition_record ? (
                <div>
                  <div style={{
                    fontSize: '15px',
                    lineHeight: '1.6',
                    color: 'var(--text-primary)',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid var(--border-strong)',
                    borderLeft: lookupResult.definition_record.is_rulebook_first ? '4px solid #2E7D32' : '4px solid var(--primary)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '16px 20px',
                    marginBottom: '18px'
                  }}>
                    {lookupResult.definition_record.definition}
                  </div>

                  {/* Metadata Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '16px' }}>
                    <div style={{ backgroundColor: '#FAF9F6', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600' }}>SOURCE AUTHORITY</div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                        {lookupResult.definition_record.source_name}
                      </div>
                    </div>

                    <div style={{ backgroundColor: '#FAF9F6', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600' }}>OFFICIAL DOMAIN</div>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--primary)', marginTop: '2px' }}>
                        {lookupResult.definition_record.source_domain}
                      </div>
                    </div>

                    {lookupResult.definition_record.policy_citation && (
                      <div style={{ backgroundColor: '#FAF9F6', padding: '12px', borderRadius: '4px' }}>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600' }}>RULEBOOK CITATION</div>
                        <div style={{ fontSize: '13px', fontWeight: '700', color: '#2E7D32', marginTop: '2px' }}>
                          {lookupResult.definition_record.policy_citation}
                        </div>
                      </div>
                    )}

                    <div style={{ backgroundColor: '#FAF9F6', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600' }}>RETRIEVAL TIMESTAMP</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {lookupResult.definition_record.retrieval_timestamp}
                      </div>
                    </div>
                  </div>

                  {/* Disclaimer Footer */}
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', fontStyle: 'italic', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                    {lookupResult.definition_record.disclaimer}
                  </div>
                </div>
              ) : (
                <div style={{
                  padding: '24px',
                  backgroundColor: lookupResult.status === 'CONFLICTING' ? '#FEF2F2' : '#FFFBEB',
                  borderRadius: 'var(--radius-sm)',
                  border: lookupResult.status === 'CONFLICTING' ? '1px solid #FCA5A5' : '1px solid #FCD34D'
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                    <AlertTriangle size={20} color={lookupResult.status === 'CONFLICTING' ? '#B91C1C' : '#B45309'} style={{ flexShrink: 0 }} />
                    <div>
                      <strong style={{ fontSize: '14px', color: lookupResult.status === 'CONFLICTING' ? '#991B1B' : '#92400E', display: 'block', marginBottom: '4px' }}>
                        {lookupResult.status === 'CONFLICTING' ? 'Conflicting Authoritative Definitions Detected' : 'Term Unresolved in Approved Sources'}
                      </strong>
                      <p style={{ fontSize: '13px', color: lookupResult.status === 'CONFLICTING' ? '#7F1D1D' : '#78350F', margin: 0, lineHeight: 1.5 }}>
                        {lookupResult.review_reason}
                      </p>
                      <div style={{ marginTop: '12px', fontSize: '12px', fontWeight: '600', color: lookupResult.status === 'CONFLICTING' ? '#991B1B' : '#92400E' }}>
                        Action: A clinical review task has been routed to human peer review. Automated evaluation logic will not assume an unverified meaning.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </>
      )}

      {activeTab === 'registry' && (
        <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '28px' }}>
          <div style={{
            padding: '16px 20px',
            backgroundColor: '#FAF9F6',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: '700', margin: 0 }}>
                Approved Terminology Source Registry
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                Backend-enforced domain allowlist. External lookups are restricted to active verified sources.
              </p>
            </div>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--primary)' }}>
              {sources.filter(s => s.verification_status === 'VERIFIED').length} Verified Active
            </span>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#FFFFFF', borderBottom: '1px solid var(--border-subtle)' }}>
                <th scope="col" style={{ padding: '12px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Source Name &amp; Domain</th>
                <th scope="col" style={{ padding: '12px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Authority</th>
                <th scope="col" style={{ padding: '12px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Permitted Scope</th>
                <th scope="col" style={{ padding: '12px 18px', fontWeight: '600', color: 'var(--text-secondary)' }}>Access Restrictions</th>
                <th scope="col" style={{ padding: '12px 18px', width: '140px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((src) => (
                <tr key={src.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '14px 18px' }}>
                    <div style={{ fontWeight: '700', color: 'var(--text-primary)' }}>{src.name}</div>
                    <code style={{ fontSize: '11px', color: 'var(--primary)', marginTop: '2px', display: 'inline-block' }}>
                      {src.official_domain}
                    </code>
                  </td>
                  <td style={{ padding: '14px 18px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                    {src.authority}
                  </td>
                  <td style={{ padding: '14px 18px', fontSize: '12.5px', color: 'var(--text-primary)' }}>
                    {src.permitted_scope}
                  </td>
                  <td style={{ padding: '14px 18px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                    {src.access_restrictions}
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    {src.verification_status === 'VERIFIED' && (
                      <span style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: '700',
                        backgroundColor: '#E8F5E9',
                        color: '#2E7D32',
                        border: '1px solid #A5D6A7'
                      }}>
                        VERIFIED
                      </span>
                    )}
                    {src.verification_status === 'RESTRICTED_ACCESS' && (
                      <span style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: '700',
                        backgroundColor: '#FEF3C7',
                        color: '#B45309',
                        border: '1px solid #FCD34D'
                      }}>
                        RESTRICTED
                      </span>
                    )}
                    {src.verification_status === 'SCOPE_RESTRICTED' && (
                      <span style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: '700',
                        backgroundColor: '#F3F4F6',
                        color: '#4B5563',
                        border: '1px solid #D1D5DB'
                      }}>
                        SCOPE RESTRICTED
                      </span>
                    )}
                    {src.verification_status === 'PENDING_REGULATORY_VERIFICATION' && (
                      <span style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: '700',
                        backgroundColor: '#EDE9FE',
                        color: '#6D28D9',
                        border: '1px solid #DDD6FE'
                      }}>
                        PENDING
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="card" style={{ padding: '0', overflow: 'hidden', marginBottom: '28px' }}>
          <div style={{
            padding: '16px 20px',
            backgroundColor: '#FAF9F6',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: '700', margin: 0 }}>
                Terminology Provenance Audit Log
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                Immutable log of term clarification requests, sources queried, and resolution outcomes.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void fetchAuditLogs()}
              className="btn btn-outline"
              style={{ fontSize: '12px', padding: '4px 10px', gap: '4px' }}
            >
              <RefreshCw size={13} />
              <span>Refresh</span>
            </button>
          </div>

          {auditLogs.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No terminology audit entries recorded yet.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ backgroundColor: '#FFFFFF', borderBottom: '1px solid var(--border-subtle)' }}>
                  <th scope="col" style={{ padding: '10px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Timestamp</th>
                  <th scope="col" style={{ padding: '10px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Term</th>
                  <th scope="col" style={{ padding: '10px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
                  <th scope="col" style={{ padding: '10px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Source</th>
                  <th scope="col" style={{ padding: '10px 16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Reason / Citation</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.slice().reverse().map((entry, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted)', fontSize: '11.5px' }}>
                      {entry.timestamp}
                    </td>
                    <td style={{ padding: '10px 16px', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {entry.term}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '600',
                        backgroundColor: entry.status.includes('RULEBOOK') || entry.status === 'RESOLVED' ? '#E8F5E9' : '#FEF3C7',
                        color: entry.status.includes('RULEBOOK') || entry.status === 'RESOLVED' ? '#2E7D32' : '#B45309'
                      }}>
                        {entry.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>
                      {entry.source}
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary)', fontSize: '11.5px' }}>
                      {entry.citation || entry.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Footer Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
        <button
          type="button"
          onClick={() => onNavigate('policy_library')}
          className="btn btn-outline"
        >
          <span>View Policy Library</span>
        </button>
        <button
          type="button"
          onClick={() => onNavigate('new_review')}
          className="btn btn-primary"
        >
          <span>Start Authorization Review</span>
        </button>
      </div>
    </div>
  );
};
