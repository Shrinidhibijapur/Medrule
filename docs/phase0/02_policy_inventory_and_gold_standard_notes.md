# MedRule Phase 0 — Policy Inventory & Gold Standard Clinical Notes

**Document ID:** MEDRULE-PHASE0-02  
**Version:** 1.0.0  
**Status:** Approved Baseline  
**Date:** October 2026  

---

## 1. Authoritative Policy Inventory

The system operates strictly on ingested, human-verified policy rulebooks. Each policy is identified by unique ID, insurer name, effective policy year, applicable clinical procedure, and strict criteria definitions.

### 1.1 Policy P-UHC-CT-2026: United Healthcare CT Scan of the Head / Brain
- **Insurer:** United Healthcare (Commercial / Medicare Advantage)
- **Policy Title:** Computed Tomography (CT) of the Head / Brain Clinical Coverage Guideline
- **Policy Version / Year:** 2026.1 (Effective Jan 1, 2026)
- **Procedure Code:** CPT 70450 (without contrast), 70460 (with contrast), 70470 (without and with contrast)
- **Document Canonical Ref:** `doc_uhc_ct_head_2026.pdf` (Checksum: `sha256:7e9a8f...`)
- **Number of Pages:** 14 pages
- **Format:** Digital text PDF with structured tables and numbered clinical indication subsections.

#### Structured Criteria Definition

| Rule ID | Section | Criterion / Requirement | Evidence Target | Logic Role |
|---|---|---|---|---|
| **R1** | §4.2.1 | **Clinical Indication:** Patient must exhibit documented neurological symptoms or signs (e.g., severe persistent headaches, dizziness, focal signs, visual disturbances). | Chief Complaint, HPI, Symptoms | Mandatory (AND) |
| **R2** | §4.2.2 | **Duration of Symptoms:** Symptoms must persist for $\ge 6$ weeks of persistent or worsening presentation. | Symptom duration | Mandatory (AND) |
| **R3** | §4.2.3 | **Previous Conservative Treatment:** Documented trial of conservative therapy (pharmacotherapy, rest, observation) attempted without adequate resolution. | Previous treatment history | Mandatory (AND) |
| **R4** | §4.2.4 | **Documented Clinical Findings:** Documented abnormal physical or neurological examination findings by a licensed clinician. | Physical exam / Neurological exam | Mandatory (AND) |
| **R5** | §4.2.5 | **Rule Out Serious Pathology:** Explicit clinical objective to rule out intracranial mass, hemorrhage, hydrocephalus, or acute intracranial pathology. | Physician Impression / Assessment | Mandatory (AND) |
| **R6** | §4.2.6 | **Contrast Justification:** If intravenous contrast is requested, clinical indication for contrast enhancement must be stated (e.g., evaluation of suspected mass/vascular pathology). | Contrast justification | Conditional (Required if contrast requested) |

- **Decision Logic:** `Approved` if $R1 \land R2 \land R3 \land R4 \land R5 \land (\neg \text{ContrastRequested} \lor R6)$ are all `Met`. If any criterion is `Not met` or `Not documented`, the request is `Not approved`.

---

### 1.2 Policy P-AET-MRI-2026: Aetna Lumbar Spine MRI Coverage Policy
- **Insurer:** Aetna
- **Policy Title:** Magnetic Resonance Imaging (MRI) of the Lumbar Spine
- **Policy Version / Year:** 2026.2 (Effective March 15, 2026)
- **Procedure Code:** CPT 72148 (without contrast), 72149 (with contrast)
- **Document Canonical Ref:** `doc_aetna_mri_lumbar_2026.pdf`
- **Number of Pages:** 18 pages

#### Structured Criteria Definition

| Rule ID | Section | Criterion / Requirement | Evidence Target | Logic Role |
|---|---|---|---|---|
| **M1** | §3.1.1 | **Radiculopathy / Nerve Root Compression:** Documented radiating pain, numbness, tingling, or weakness adhering to dermatomal/myotomal distribution. | Neurological Exam | Pathway A (OR) |
| **M2** | §3.1.2 | **Conservative Therapy:** At least 6 weeks of structured conservative treatment (physical therapy, NSAIDs, chiropractic) within past 6 months. | Conservative Treatment | Mandatory (AND) |
| **M3** | §3.1.3 | **Red Flag Symptoms:** Cauda equina symptoms (loss of bowel/bladder control, saddle anesthesia), progressive motor deficit, or suspected malignancy. | Red Flags | Pathway B (Immediate Exception) |
| **M4** | §3.1.4 | **Recent Plain Radiographs:** Prior X-ray of lumbar spine completed within past 12 months. | Prior Imaging | Mandatory (AND, unless Red Flag) |

- **Decision Logic:** `Approved` if $(M3 = \text{Met}) \lor ((M1 = \text{Met}) \land (M2 = \text{Met}) \land (M4 = \text{Met}))$.

---

## 2. Gold Standard Sample Clinical Notes & Expected Benchmark Outcomes

In accordance with Section 10.5 of the Implementation Blueprint, the following reference cases serve as the gold-standard evaluation harness.

### Case 001: John Doe — CT Head with Contrast (Reference UI Case)
- **File Reference:** `case_001_john_doe_ct_head.json`
- **Patient:** John Doe (42 years, Male, DOB: 01/15/1980)
- **Facility:** Riverside Medical Center (Encounter Date: 10/05/2026)
- **Requested Procedure:** CT Scan of Head with Contrast (CPT 70460)
- **Insurance Plan:** United Healthcare (Policy: P-UHC-CT-2026)
- **Clinical Summary:**
  - *Chief Complaint:* Persistent severe headaches and dizziness for 3 months with associated visual disturbances.
  - *Previous Treatment:* 8-week conservative trial of NSAIDs and migraine regimen without symptomatic improvement.
  - *Physical Exam:* Abnormal cranial nerve findings; mild ataxia.
  - *Physician Impression:* Rule out intracranial pathology / mass; CT scan with contrast clinically justified.
- **Criterion-by-Criterion Expected Results:**
  - `R1`: **Met (✅)** — *"Recurrent severe headaches, dizziness, visual disturbances"* (Page 1)
  - `R2`: **Met (✅)** — *"Present for 3 months (exceeds 6-week minimum)"* (Page 1)
  - `R3`: **Met (✅)** — *"Conservative treatment attempted (no improvement)"* (Page 1)
  - `R4`: **Met (✅)** — *"Neurological examination abnormal"* (Page 2)
  - `R5`: **Met (✅)** — *"Rule out intracranial pathology"* (Page 2)
  - `R6`: **Met (✅)** — *"Clinically indicated for further evaluation of suspected intracranial pathology"* (Page 2)
- **Expected Verdict:** **Approved**  
- **Expected Verdict Sentence:** *"Approval of a CT scan requires documented neurological signs persisting $\ge 6$ weeks, trial of conservative therapy, abnormal exam findings, rule-out indication, and contrast justification. Conditions R1, R2, R3, R4, R5, R6 are satisfied and meet that minimum. Therefore the CT scan request can be approved."*

---

### Case 002: Jane Smith — MRI Lumbar Spine (Documentation Failure Case)
- **File Reference:** `case_002_jane_smith_mri_lumbar.json`
- **Patient:** Jane Smith (38 years, Female, DOB: 06/22/1988)
- **Requested Procedure:** MRI Lumbar Spine without Contrast (CPT 72148)
- **Insurance Plan:** Aetna (Policy: P-AET-MRI-2026)
- **Clinical Summary:** Low back pain radiating into left calf for 4 weeks. No physical therapy records, no prior X-rays documented. No red flag symptoms.
- **Criterion-by-Criterion Expected Results:**
  - `M1`: **Met (✅)** — Radicular symptoms documented.
  - `M2`: **Not satisfied (❌ Not documented)** — Conservative therapy trial duration < 6 weeks and uncompleted.
  - `M3`: **Not met (❌ Not met)** — No red flags present.
  - `M4`: **Not satisfied (❌ Not documented)** — Plain radiographs not found in record.
- **Expected Verdict:** **Not approved (Documentation Incomplete)**  
- **Human Review Flag:** YES (Documentation deficiency).

---

### Case 003: Robert Lee — CT Scan (Approved Repeat Case)
- **File Reference:** `case_003_robert_lee_ct_sinus.json`
- **Patient:** Robert Lee (55 years, Male)
- **Insurance Plan:** Blue Cross Blue Shield (BCBS)
- **Expected Verdict:** **Approved**

---

### Case 004: Emily Davis — MRI Brain (Ambiguous / Conflicting Review Case)
- **File Reference:** `case_004_emily_davis_mri_brain.json`
- **Patient:** Emily Davis (29 years, Female)
- **Insurance Plan:** Cigna
- **Expected Verdict:** **Cannot be determined — Human Review Required** (Unclear / conflicting clinical statements regarding scan indication).
