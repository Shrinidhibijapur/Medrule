import React, { useState } from 'react';
import { Send, Paperclip, Sparkles, Check, X, ShieldAlert, ArrowRight } from 'lucide-react';
import { ViewMode } from '../types';
import { mockJohnDoeCase } from '../mockData';

interface AskMedRuleViewProps {
  onNavigate: (view: ViewMode) => void;
}

export const AskMedRuleView: React.FC<AskMedRuleViewProps> = ({ onNavigate }) => {
  const [messages, setMessages] = useState<Array<{
    sender: 'user' | 'agent';
    text?: string;
    showReport?: boolean;
  }>>([
    {
      sender: 'agent',
      text: "Hello! I am MedRule, your policy-driven authorization assistant. Upload a clinical note and ask a coverage question (e.g. 'Based on this doctor's note and the United Healthcare policy, can the CT scan be approved?')."
    }
  ]);
  const [inputText, setInputText] = useState("Based on this note, can the CT scan of head be approved?");
  const [attachedFile, setAttachedFile] = useState<string | null>("John_Doe_Clinical_Note_Riverside.pdf");
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSend = () => {
    if (!inputText.trim()) return;

    const userMsg = { sender: 'user' as const, text: inputText };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsProcessing(true);

    setTimeout(() => {
      setIsProcessing(false);
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          showReport: true
        }
      ]);
    }, 700);
  };

  return (
    <div style={{ maxWidth: '950px', height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: '700', letterSpacing: '-0.5px', marginBottom: '4px' }}>
          Ask MedRule (Interactive Agent)
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px' }}>
          Evaluate authorization requests using ingested rulebooks as authority
        </p>
      </div>

      {/* Messages Scroll Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        paddingRight: '12px',
        marginBottom: '20px'
      }}>
        {messages.map((m, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start'
            }}
          >
            {m.sender === 'user' ? (
              <div style={{
                backgroundColor: 'var(--primary)',
                color: '#FFFFFF',
                borderRadius: '16px 16px 4px 16px',
                padding: '14px 20px',
                maxWidth: '75%',
                fontSize: '14.5px',
                boxShadow: 'var(--shadow-sm)'
              }}>
                {m.text}
                {attachedFile && (
                  <div style={{
                    marginTop: '8px',
                    fontSize: '12px',
                    backgroundColor: 'rgba(255,255,255,0.15)',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <Paperclip size={12} />
                    <span>{attachedFile}</span>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ width: '100%', maxWidth: m.showReport ? '100%' : '80%' }}>
                {m.text && (
                  <div style={{
                    backgroundColor: '#FFFFFF',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '16px 16px 16px 4px',
                    padding: '14px 20px',
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                    boxShadow: 'var(--shadow-sm)'
                  }}>
                    {m.text}
                  </div>
                )}

                {/* Structured Report Card inside Thread (§5.3.0, §4.1) */}
                {m.showReport && (
                  <div className="card" style={{ padding: '24px', border: '1px solid var(--success-border)', backgroundColor: '#FFFFFF' }}>
                    {/* Confirmation Chips */}
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '8px',
                      marginBottom: '18px',
                      paddingBottom: '12px',
                      borderBottom: '1px solid var(--border-subtle)'
                    }}>
                      <span style={{ fontSize: '12px', padding: '4px 10px', backgroundColor: '#F0EFEA', borderRadius: '4px', fontWeight: '600' }}>
                        Insurer: United Healthcare
                      </span>
                      <span style={{ fontSize: '12px', padding: '4px 10px', backgroundColor: '#F0EFEA', borderRadius: '4px', fontWeight: '600' }}>
                        Plan: Commercial Advantage
                      </span>
                      <span style={{ fontSize: '12px', padding: '4px 10px', backgroundColor: '#F0EFEA', borderRadius: '4px', fontWeight: '600' }}>
                        Procedure: CT Scan of Head
                      </span>
                      <span style={{ fontSize: '12px', padding: '4px 10px', backgroundColor: '#F0EFEA', borderRadius: '4px', fontWeight: '600' }}>
                        Policy: UHC-2026.1
                      </span>
                    </div>

                    <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '14px' }}>
                      Criterion-by-Criterion Assessment Chart
                    </h3>

                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', marginBottom: '18px' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#FAF9F6', borderBottom: '1px solid var(--border-subtle)' }}>
                          <th style={{ padding: '8px 12px', fontWeight: '600' }}>Rule</th>
                          <th style={{ padding: '8px 12px', fontWeight: '600' }}>Policy Condition</th>
                          <th style={{ padding: '8px 12px', fontWeight: '600' }}>Note Evidence</th>
                          <th style={{ padding: '8px 12px', fontWeight: '600' }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {mockJohnDoeCase.criteria_results.map(cr => (
                          <tr key={cr.rule_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>R{cr.rule_id}</td>
                            <td style={{ padding: '10px 12px', fontWeight: '600' }}>{cr.criterion_name}</td>
                            <td style={{ padding: '10px 12px' }}>"{cr.evidence_excerpt}"</td>
                            <td style={{ padding: '10px 12px' }}>
                              <span style={{ color: 'var(--success)', fontWeight: '700' }}>✅ Satisfied</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {/* Detailed Reasoning BEFORE verdict sentence */}
                    <div style={{ backgroundColor: '#FAF9F6', padding: '14px 18px', borderRadius: 'var(--radius-sm)', marginBottom: '18px' }}>
                      <strong style={{ fontSize: '13.5px', color: 'var(--text-primary)', display: 'block', marginBottom: '6px' }}>
                        Policy Evaluation Reasoning:
                      </strong>
                      <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        <li>All 6 evaluated criteria are satisfied with direct evidence from medical encounter.</li>
                        <li>Symptoms duration of 3 months exceeds minimum threshold of 6 weeks.</li>
                        <li>Documented trial of conservative therapy without clinical resolution.</li>
                        <li>Indication specifically documents rule-out of intracranial pathology.</li>
                      </ul>
                    </div>

                    {/* Verdict Sentence */}
                    <div style={{
                      padding: '12px 16px',
                      backgroundColor: 'var(--success-bg)',
                      border: '1px solid var(--success-border)',
                      borderRadius: 'var(--radius-sm)',
                      marginBottom: '16px'
                    }}>
                      <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--success)', marginBottom: '4px' }}>
                        Conclusion: Approved
                      </div>
                      <p style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                        Approval of a CT scan requires documented neurological signs persisting ≥ 6 weeks, conservative therapy trial, abnormal findings, rule-out indication, and contrast justification. Conditions R1-R6 are satisfied and meet that minimum. Therefore the CT scan request can be approved.
                      </p>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                      <button
                        onClick={() => onNavigate('authorization_decision')}
                        className="btn btn-primary"
                        style={{ padding: '8px 16px', fontSize: '13px' }}
                      >
                        <span>Open Decision Workspace</span>
                        <ArrowRight size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {isProcessing && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '13px' }}>
            <Sparkles size={16} className="animate-spin" />
            <span>Evaluating note evidence against policy rulebook...</span>
          </div>
        )}
      </div>

      {/* Composer Input Bar */}
      <div style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 16px',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <label style={{ cursor: 'pointer', padding: '6px' }}>
          <Paperclip size={18} color="var(--text-secondary)" />
          <input
            type="file"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                setAttachedFile(e.target.files[0].name);
              }
            }}
          />
        </label>

        {attachedFile && (
          <span style={{
            fontSize: '12px',
            backgroundColor: '#FAF9F6',
            border: '1px solid var(--border-subtle)',
            padding: '4px 8px',
            borderRadius: '4px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            {attachedFile}
            <button onClick={() => setAttachedFile(null)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>
              <X size={12} />
            </button>
          </span>
        )}

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask: 'Based on this note, can the CT scan be approved?'"
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            fontSize: '14px',
            backgroundColor: 'transparent'
          }}
        />

        <button
          onClick={handleSend}
          className="btn btn-primary"
          style={{ padding: '8px 14px' }}
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
};
