# MedRule Phase 0 — Privacy, Security & Governance Baseline

**Document ID:** MEDRULE-PHASE0-05  
**Version:** 1.0.0  
**Status:** Approved Baseline  
**Date:** October 2026  

---

## 1. External Terminology Governance (Section 2.2)

- Outside the rulebook, queries are strictly constrained to terminology definitions.
- General Google searches or arbitrary URL lookups are disabled by design.
- The approved domain allowlist for Phase 0 / MVP:
  - `ama-assn.org` (American Medical Association - definitions only)
  - `nlm.nih.gov` / `medlineplus.gov` (National Library of Medicine Medical Dictionary)
  - `cms.gov` (Centers for Medicare & Medicaid Services Glossary)
- In the initial offline/local baseline, external network queries are defaulted to offline glossary mode.

---

## 2. Protected Health Information (PHI) & Data Retention

- Minimal PHI principle: patient identifiers are scrubbed or tokenized to case IDs where feasible.
- Encrypted storage: in-transit and at-rest standards for document storage.
- Immutable audit log: every upload, evaluation, human override, and report export generates a timestamped audit event with user identifier.
- Human Review Boundary: MedRule produces preliminary clinical decision-support reports, not final binding decisions. An authorized human reviewer must approve any determination.
