# MedRule Phase 0 — Status Semantics & Verdict Engine Specification

**Document ID:** MEDRULE-PHASE0-04  
**Version:** 1.0.0  
**Status:** Approved Baseline  
**Date:** October 2026  

---

## 1. Status Semantics (Section 2.3)

The engine recognizes six explicit clinical evidence statuses. In the user interface chart, these map strictly to binary indicators (✅ or ❌) with contextual sub-labels:

| Internal Engine Status | UI Chart Symbol | Sub-Label | Logic Contribution | Definition |
|---|---|---|---|---|
| `MET` | ✅ Green Check | "Satisfied" / "Met" | Satisfies criterion | Note explicitly documents required clinical evidence. |
| `NOT_MET` | ❌ Red Cross | "Not met" | Fails criterion | Note explicitly contradicts requirement or proves non-fulfillment. |
| `NOT_DOCUMENTED` | ❌ Red Cross | "Not documented" | Fails criterion (Missing) | Note contains no documentation regarding this criterion. |
| `UNCLEAR_CONFLICTING`| ❌ Red Cross | "Unclear" | Fails & Flags Review | Ambiguous or conflicting statements found in the record. |
| `POLICY_AMBIGUITY` | ❌ Red Cross | "Policy ambiguity" | Cannot evaluate | Policy clause itself cannot be safely or deterministically interpreted. |
| `NOT_APPLICABLE` | – Grey Dash | "N/A" | Excluded | Policy explicitly makes this criterion inapplicable (e.g. contrast when no contrast requested). |

---

## 2. Verdict Determination Rules (Section 3.3 & 4.1)

1. **Approved:**
   - Evaluated policy logic resolves to `True` using exclusively criteria evaluated as `MET`.
   - No mandatory criteria are in `NOT_MET`, `NOT_DOCUMENTED`, `UNCLEAR_CONFLICTING`, or `POLICY_AMBIGUITY`.

2. **Not Approved:**
   - Evaluated policy logic resolves to `False`.
   - If any missing requirement is due to `NOT_DOCUMENTED`, the report explicitly distinguishes documentation absence from clinical contraindication.

3. **Cannot Be Determined:**
   - Applied when `POLICY_AMBIGUITY` occurs, note is unreadable, or procedure/plan mismatch prevents safe evaluation. Routes unconditionally to human reviewer.

---

## 3. Mandatory Layout: Reasoning Precedes Verdict (Section 4.1)

All generated evaluation summaries must strictly format the conclusion block with **detailed reasoning first**, followed by the **verdict sentence**:

```
[Key Reasoning Bullet Points]
- Criterion R1: Satisfied (Headaches, dizziness present)
- Criterion R2: Satisfied (Duration 3 months >= 6 weeks)
...
[Verdict Sentence]
"Approval of a [CT scan] requires [policy logic]. Conditions [IDs] are satisfied and meet that minimum. Therefore the [CT scan] request can be approved."
```
