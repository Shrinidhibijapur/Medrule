# MedRule Phase 0 — Requirements Traceability Matrix

**Document ID:** MEDRULE-PHASE0-03  
**Version:** 1.0.0  
**Status:** Approved Baseline  
**Date:** October 2026  

---

## 1. Stakeholder Voicemail Requirements Mapping

| ID | Stakeholder Requirement (Voicemail) | Implementation Design Element | Verification Test | Phase 0 Status |
|---|---|---|---|---|
| **REQ-VM-01** | Sole authority must be the rulebook | Deterministic engine evaluates only approved policy registry records (§2.1, §3.1) | `test_rulebook_authority_boundary` | Verified |
| **REQ-VM-02** | Outside rulebook only for terminology from authenticated sources | Hardened TerminologyService with strict domain allowlist (§2.2) | `test_terminology_allowlist_enforcement` | Verified |
| **REQ-VM-03** | Agent is "trained" on rulebook (Ingestion & structured representation) | Policy JSON registry with human validation gate (§3.1a, Phase 1) | `test_policy_schema_validation` | Verified |
| **REQ-VM-04** | ChatGPT-like interface: Upload note, ask "Can the CT scan / MRI be approved?" | Ask MedRule conversational view + structured card rendering (§5.3.0) | Interactive chat view + question parser tests | Verified |
| **REQ-VM-05** | Chart of all conditions, sub-conditions, and groups | Criteria Evaluation table & Detailed Analysis views (Slides 06, 07) | `test_criteria_chart_generation` | Verified |
| **REQ-VM-06** | Green check (✅) for satisfied, red cross (❌) for not satisfied | Binary status visualization with engine sub-labels (§2.3, Slide 06) | `test_binary_status_visualization` | Verified |
| **REQ-VM-07** | Conclusion explains minimum requirements met/unmet, then approves/not | Templated conclusion builder with exact rule minimum breakdown (§4.1) | `test_verdict_template_structure` | Verified |
| **REQ-VM-08** | Detailed reasoning must precede the final verdict | Enforced layout in engine report generator: reasoning before verdict (§4.1) | `test_reasoning_precedes_verdict` | Verified |
| **REQ-VM-09** | Owner knows true results and tests against agent | Automated Gold Standard verification harness (§10.5) | `verify_phase0.py --gold-standards` | Verified |

---

## 2. Core Functional Requirements Traceability

| Req ID | Description | Source Section | Verification Mechanism | Status |
|---|---|---|---|---|
| **FR-01** | Document Intake & Multi-format Support (PDF, JPG, PNG) | §3.2, Slide 03 | Validation of MIME type, checksum, file size <= 10MB | Verified |
| **FR-02** | Structured Fact Extraction with Page Citations | §2.4, Slide 05 | Extraction parser with source excerpt & page pointer | Verified |
| **FR-03** | Deterministic Policy Rules Engine (AND/OR/Threshold) | §3.1, §6.1 | Deterministic engine unit test suite | Verified |
| **FR-04** | Status Semantics (Met, Not met, Not documented, Unclear, N/A) | §2.3, §7 (P0) | Status enum validator & mapping rules | Verified |
| **FR-05** | No Blue UI Constraint | §5.1 | CSS stylesheet design token audit | Verified |
| **FR-06** | UI Alignment with Reference Slides (01-09) | MedAuth Slides | Visual inspection & component hierarchy | Verified |
| **FR-07** | Human Review Gate & Audit Logging | §1.1, §6.1 | Audit trail record creation for all assessments | Verified |
| **FR-08** | Exportable Assessment Summary Report | §4.1, Slide 08 | Downloadable structured evaluation summary | Verified |
