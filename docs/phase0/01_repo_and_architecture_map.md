# MedRule Phase 0 — Repository & Architecture Baseline Map

**Document ID:** MEDRULE-PHASE0-01  
**Version:** 1.0.0  
**Status:** Approved Baseline  
**Date:** October 2026  

---

## 1. System Overview

MedRule is a rulebook-driven medical insurance authorization decision-support platform designed to assess whether requested imaging procedures (CT scan, MRI) meet applicable insurer policy criteria using supplied rulebooks as the sole coverage authority.

The system enforces:
1. **Rulebook-as-Authority:** Decisions stem exclusively from approved, ingested policy criteria.
2. **Deterministic Logic:** A transparent rules engine evaluates Boolean AND/OR, group, count, and threshold logic.
3. **Traceability:** Every evaluated criterion links to exact doctor's note evidence and policy citations (section, page).
4. **Distinction of Uncertainty:** Missing documentation is explicitly tagged `Not documented` (rendered as ❌ with reason sub-label) to avoid misclassifying unprovided paperwork as clinical failure.
5. **Human Review Guardrail:** All outcomes are decision-support preliminary assessments requiring authorized human clinical reviewer sign-off.
6. **No-Blue Healthcare Design:** Executive enterprise palette utilizing warm off-white (`#F7F6F2`), forest green (`#315B45`), accessible status indicators, and clean typography.

---

## 2. Repository Architecture & Layout

```
Medrule/
├── .git/                                # Git version control
├── .gitignore                           # Git ignore rules
├── MedRule_Implementation_Plan.md       # Master specification and implementation blueprint
├── medauth_ui_slides_separate_images/   # Reference UI visual mockups (Slides 01-09)
├── verify_phase0.py                     # Automated Phase 0 exit criteria & gold-standard verification runner
│
├── docs/
│   └── phase0/                          # Phase 0 formal deliverables
│       ├── 01_repo_and_architecture_map.md
│       ├── 02_policy_inventory_and_gold_standard_notes.md
│       ├── 03_requirements_traceability_matrix.md
│       ├── 04_status_semantics_and_verdict_engine_spec.md
│       └── 05_privacy_security_and_governance.md
│
├── data/                                # Structured policies, clinical notes, and benchmarks
│   ├── policies/                        # Ingested and human-validated policy representations
│   │   ├── united_healthcare_ct_head_2026.json
│   │   └── aetna_mri_lumbar_spine_2026.json
│   ├── notes/                           # Standard clinical consultation notes
│   │   ├── case_001_john_doe_ct_head.json
│   │   ├── case_002_jane_smith_mri_lumbar.json
│   │   ├── case_003_robert_lee_ct_sinus.json
│   │   └── case_004_emily_davis_mri_brain.json
│   └── gold_standards/                  # Verified expected outcomes for regression tests
│       └── expected_evaluations.json
│
├── backend/                             # Python 3.11+ / FastAPI Services & Rules Engine
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI application entrypoint with REST endpoints
│   │   ├── models/                      # Pydantic data schemas
│   │   │   ├── __init__.py
│   │   │   ├── policy.py                # Policy, section, criterion models
│   │   │   ├── clinical.py              # Clinical fact and note models
│   │   │   ├── evaluation.py            # Evaluation request, result, and report models
│   │   │   └── case.py                  # Case lifecycle and audit event models
│   │   ├── engine/                      # Deterministic Policy Rules Engine
│   │   │   ├── __init__.py
│   │   │   ├── rules_engine.py          # Deterministic logic evaluation core
│   │   │   └── templates.py             # Formatted conclusion templates (reasoning before verdict)
│   │   ├── services/                    # Business services
│   │   │   ├── __init__.py
│   │   │   ├── policy_service.py        # Ingestion, validation, retrieval
│   │   │   ├── fact_extractor.py        # Clinical note fact extraction
│   │   │   └── case_service.py          # Case history & audit persistence
│   └── tests/                           # Backend test suite
│       ├── __init__.py
│       ├── test_rules_engine.py         # Unit tests for status semantics & Boolean logic
│       ├── test_gold_standards.py       # Regression harness against domain expert results
│       └── test_api.py                  # API integration test suite
│
└── frontend/                            # React 18+ / TypeScript / Vite Web Application
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── index.css                    # Design system tokens, warm off-white/forest palette
        ├── App.tsx                      # Root navigation, screen routing, state store
        ├── main.tsx                     # React root mount
        ├── types/                       # Shared TypeScript interface definitions
        │   └── index.ts
        ├── components/                  # Reusable UI components
        │   ├── Sidebar.tsx              # MedAuth brand navigation sidebar
        │   ├── Header.tsx               # Top header with user profile & action triggers
        │   ├── StatusBadge.tsx          # Accessible status pills (Met, Not Met, In Review)
        │   └── Modal.tsx                # Rulebook source preview modal
        ├── views/                       # Slide-exact screen views (01-09 + Ask MedRule)
        │   ├── LoginView.tsx            # Slide 01: Split auth screen with organic motif
        │   ├── DashboardView.tsx        # Slide 02: KPI metrics & Recent Reviews
        │   ├── NewReviewView.tsx        # Slide 03: 3-step wizard with file intake & presets
        │   ├── ExtractedDocumentView.tsx# Slide 04: Multi-page document viewer
        │   ├── ExtractedInfoView.tsx    # Slide 05: Patient & Clinical structured cards
        │   ├── CriteriaEvaluationView.tsx# Slide 06: Policy criteria check table
        │   ├── DetailedAnalysisView.tsx # Slide 07: Policy citations & detailed breakdown
        │   ├── AuthorizationDecisionView.tsx # Slide 08: Decision banner, checklist & export
        │   ├── CasesHistoryView.tsx     # Slide 09: Full audit history with search/filter
        │   └── AskMedRuleView.tsx       # Primary conversational chat interface (§5.3.0)
        └── mockData/                    # Baseline test fixtures matching slides
            └── index.ts
```

---

## 3. Technology Stack & Runtimes

| Component | Technology | Version | Rationale |
|---|---|---|---|
| **Runtime (BE)** | Python | 3.11.5 | High performance, rich ecosystem for NLP/document parsing. |
| **Framework (BE)** | FastAPI + Pydantic v2 | ^0.110.0 | High speed async endpoints, strict OpenAPI schema validation. |
| **Testing (BE)** | Pytest | ^8.0.0 | Unit, integration, and gold-standard regression test runner. |
| **Runtime (FE)** | Node.js | v20.20.2 | LTS JavaScript runtime. |
| **Build Tool (FE)**| Vite | ^5.2.0 | Instant HMR, lightweight modern ES module bundling. |
| **Framework (FE)** | React + TypeScript | 18.2 / 5.4 | Type-safe UI components, maintainable enterprise structure. |
| **Styling** | Vanilla CSS Design System | CSS Variables | Zero extraneous dependencies; complete color token control. |
| **Icons** | Lucide React | ^0.350.0 | Clean, accessible SVG line icons. |

---

## 4. Environment & Deployment Baseline

- **Local Development URL (FE):** `http://localhost:5173`
- **Backend API URL:** `http://localhost:8000`
- **API Documentation:** `http://localhost:8000/docs` (OpenAPI Swagger)
- **Local Storage Strategy:** Local state + memory store with pre-loaded demo fixtures, allowing full offline operation without cloud dependency.
