import io
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app, registry_service, criteria_service, note_extractor_service
from app.models.policy import Policy, PolicyLifecycleStatus, PolicySection
from app.models.criteria import (
    CriterionRule,
    CriterionType,
    LogicOperator,
    ComparisonOperator,
    VerificationStatus,
    ReviewerSignoff,
    PolicyRuleset,
    VerificationGateRequest,
    CriteriaEvaluationRequest,
)
from app.models.evaluation import (
    CriterionStatus,
    Verdict,
    DecisionOutcome,
    EvaluationReport,
)
from app.models.note import (
    ClinicalNoteRecord,
    ExtractedFact,
    ClinicalFactStatus,
    FactCorrectionRequest,
    FactFlagRequest,
)
from app.services.criteria_service import PolicyVerificationGateError

client = TestClient(app)

@pytest.fixture
def approved_test_policy_and_ruleset(tmp_path):
    """Sets up an approved policy and verified ruleset for Phase 4 evaluation tests."""
    policy_id = "P-TEST-CT-PHASE4"
    policy_checksum = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    policy = Policy(
        id=policy_id,
        insurer="United Healthcare",
        policy_name="Computed Tomography (CT) Head - Diagnostic Imaging",
        version="2026.1",
        effective_date="2026-01-01",
        procedure_type="CT",
        procedure_full_name="Computed Tomography, Head or Brain (Diagnostic)",
        cpt_codes=["70450", "70460", "70470"],
        plan="Commercial & Medicare Advantage",
        lifecycle_status=PolicyLifecycleStatus.APPROVED_FOR_USE,
        approved_by="Dr. Sarah Jenkins, MD, Medical Director",
        approved_at="2026-01-05T09:00:00Z",
        sha256_checksum=policy_checksum,
        storage_path="",
        sections=[
            PolicySection(
                id="sec_1",
                section_number="1.1",
                heading="Acute Focal Neurologic Deficit",
                page_number=2,
                content="Head CT is indicated for acute focal neurologic deficit.",
                character_count=57
            ),
            PolicySection(
                id="sec_2",
                section_number="1.2",
                heading="Conservative Treatment",
                page_number=2,
                content="Trial of conservative treatment for >= 6 weeks.",
                character_count=48
            ),
            PolicySection(
                id="sec_3",
                section_number="1.3",
                heading="General Exclusions",
                page_number=4,
                content="Recent normal CT within 30 days is an exclusion.",
                character_count=49
            ),
        ]
    )
    registry_service._policies_cache[policy_id] = policy

    signoff = ReviewerSignoff(
        primary_reviewer="Dr. Sarah Jenkins, MD",
        primary_reviewer_role="Medical Director",
        secondary_reviewer="Dr. Mark Lin, MD",
        secondary_reviewer_role="Clinical Associate",
        signed_off_at="2026-01-05T10:00:00Z",
        policy_checksum=policy_checksum,
        source_criteria_count=4,
        encoded_criteria_count=4,
        side_by_side_verified=True,
        plain_english_verified=True,
        notes="Phase 4 Test Policy Sign-off"
    )

    rules = [
        CriterionRule(
            id="CRIT-4-01",
            policy_id=policy_id,
            policy_version="2026.1",
            section_number="1.1",
            section_name="Acute Focal Neurologic Deficit",
            criterion_type=CriterionType.CRITERION,
            source_page=2,
            source_text="Documentation of acute focal neurologic deficit (e.g., hemiparesis, aphasia).",
            fact_key="focal_neuro_deficit",
            is_mandatory=True,
            verification_status=VerificationStatus.APPROVED_VERIFIED,
            plain_english_description="Documentation of acute focal neurologic deficit."
        ),
        CriterionRule(
            id="CRIT-4-02",
            policy_id=policy_id,
            policy_version="2026.1",
            section_number="1.2",
            section_name="Conservative Treatment Duration",
            criterion_type=CriterionType.DURATION,
            source_page=2,
            source_text="Trial of conservative treatment persisting for >= 6 weeks.",
            fact_key="symptom_duration_weeks",
            threshold_value=6.0,
            threshold_unit="weeks",
            comparison_op=">=",
            is_mandatory=True,
            verification_status=VerificationStatus.APPROVED_VERIFIED,
            plain_english_description="Symptom trial duration must be at least 6 weeks."
        ),
        CriterionRule(
            id="CRIT-4-03",
            policy_id=policy_id,
            policy_version="2026.1",
            section_number="1.3",
            section_name="Recent Normal Head CT",
            criterion_type=CriterionType.EXCLUSION,
            source_page=4,
            source_text="Recent normal CT within 30 days is a contraindication.",
            fact_key="recent_normal_ct_within_30_days",
            is_mandatory=False,
            is_exclusion=True,
            verification_status=VerificationStatus.APPROVED_VERIFIED,
            plain_english_description="Recent normal CT within 30 days is excluded."
        ),
        CriterionRule(
            id="CRIT-4-04",
            policy_id=policy_id,
            policy_version="2026.1",
            section_number="1.4",
            section_name="Guidance Notes",
            criterion_type=CriterionType.NOTE_EXPLANATORY,
            source_page=4,
            source_text="Routine follow-up without clinical change is generally not indicated.",
            verification_status=VerificationStatus.APPROVED_VERIFIED,
            plain_english_description="Explanatory clinical guidance note."
        ),
    ]

    ruleset = PolicyRuleset(
        policy_id=policy_id,
        policy_name=policy.policy_name,
        policy_version="2026.1",
        procedure_type="CT",
        policy_checksum=policy_checksum,
        rules=rules,
        verification_status=VerificationStatus.APPROVED_VERIFIED,
        signoff=signoff,
        last_updated="2026-01-05T10:00:00Z"
    )
    criteria_service.save_ruleset(ruleset)

    yield policy, ruleset

    # Cleanup
    if policy_id in registry_service._policies_cache:
        del registry_service._policies_cache[policy_id]
    ruleset_file = criteria_service._get_ruleset_file(policy_id)
    if ruleset_file.exists():
        ruleset_file.unlink()


def test_phase4_all_criteria_statuses(approved_test_policy_and_ruleset):
    """
    Requirement 4 & 5:
    Preserve distinct statuses: MET, NOT_MET, NOT_DOCUMENTED, UNCLEAR_CONFLICTING, NOT_APPLICABLE.
    Never convert missing, unreadable, uncertain, or contradictory evidence into NOT_MET.
    """
    policy, _ = approved_test_policy_and_ruleset

    # 1. MET status test
    facts_met = {
        "focal_neuro_deficit": ExtractedFact(
            fact_key="focal_neuro_deficit",
            label="Focal Neuro Deficit",
            value=True,
            status=ClinicalFactStatus.EXPLICIT,
            excerpt="Patient exhibits right-sided hemiparesis and facial droop.",
            source_page=2,
            confidence=0.98
        ),
        "symptom_duration_weeks": ExtractedFact(
            fact_key="symptom_duration_weeks",
            label="Symptom Duration",
            value=8.0,
            status=ClinicalFactStatus.EXPLICIT,
            excerpt="Symptoms present for 8 weeks.",
            source_page=2,
            confidence=0.95
        ),
        "recent_normal_ct_within_30_days": ExtractedFact(
            fact_key="recent_normal_ct_within_30_days",
            label="Recent Normal CT",
            value=False,
            status=ClinicalFactStatus.EXPLICIT,
            excerpt="No prior imaging on record.",
            source_page=3,
            confidence=0.95
        )
    }

    report_met = criteria_service.evaluate_policy_case(
        policy=policy,
        case_id="CASE-P4-MET",
        patient_name="Alice Smith",
        facts=facts_met
    )

    assert report_met.verdict == Verdict.APPROVED
    assert report_met.decision_outcome == DecisionOutcome.APPROVED
    assert not report_met.requires_human_review

    crit_01 = next(r for r in report_met.criteria_results if r.rule_id == "CRIT-4-01")
    assert crit_01.status == CriterionStatus.MET
    assert crit_01.ui_symbol == "✅"
    assert crit_01.ui_label == "Satisfied"
    assert "hemiparesis" in crit_01.evidence_excerpt
    assert crit_01.source_page == 2

    # 2. NOT_DOCUMENTED status test (Distinct from clinical denial!)
    facts_missing = {
        "focal_neuro_deficit": ExtractedFact(
            fact_key="focal_neuro_deficit",
            label="Focal Neuro Deficit",
            value=None,
            status=ClinicalFactStatus.ABSENT,
            excerpt=None,
            source_page=None,
            confidence=1.0
        ),
        "symptom_duration_weeks": 8.0,
        "recent_normal_ct_within_30_days": False
    }

    report_missing = criteria_service.evaluate_policy_case(
        policy=policy,
        case_id="CASE-P4-MISSING",
        patient_name="Bob Jones",
        facts=facts_missing
    )

    # Missing documentation must produce ADDITIONAL_DOCUMENTATION_REQUIRED, NOT clinical DENIED
    assert report_missing.decision_outcome == DecisionOutcome.ADDITIONAL_DOCUMENTATION_REQUIRED
    assert report_missing.verdict == Verdict.NOT_APPROVED
    assert report_missing.requires_human_review
    assert any("not contain documentation" in report_missing.verdict_sentence for _ in [1])

    crit_missing = next(r for r in report_missing.criteria_results if r.rule_id == "CRIT-4-01")
    assert crit_missing.status == CriterionStatus.NOT_DOCUMENTED
    assert crit_missing.ui_label == "Not documented"
    assert crit_missing.status != CriterionStatus.NOT_MET

    # 3. UNCLEAR_CONFLICTING status test
    facts_unclear = {
        "focal_neuro_deficit": ExtractedFact(
            fact_key="focal_neuro_deficit",
            label="Focal Neuro Deficit",
            value=None,
            status=ClinicalFactStatus.CONFLICTING,
            excerpt="Contradictory findings: Page 1 states mild weakness, Page 2 states non-focal exam.",
            source_page=1,
            confidence=0.5
        ),
        "symptom_duration_weeks": 8.0,
        "recent_normal_ct_within_30_days": False
    }

    report_unclear = criteria_service.evaluate_policy_case(
        policy=policy,
        case_id="CASE-P4-UNCLEAR",
        patient_name="Charlie Brown",
        facts=facts_unclear
    )

    assert report_unclear.decision_outcome == DecisionOutcome.CANNOT_BE_DETERMINED
    assert report_unclear.verdict == Verdict.CANNOT_BE_DETERMINED
    assert report_unclear.requires_human_review

    crit_unclear = next(r for r in report_unclear.criteria_results if r.rule_id == "CRIT-4-01")
    assert crit_unclear.status == CriterionStatus.UNCLEAR_CONFLICTING
    assert crit_unclear.ui_label == "Unclear"

    # 4. NOT_MET status test (Clinical failure / contraindication)
    facts_not_met = {
        "focal_neuro_deficit": ExtractedFact(
            fact_key="focal_neuro_deficit",
            label="Focal Neuro Deficit",
            value=False,
            status=ClinicalFactStatus.EXPLICIT,
            excerpt="Neurological examination is completely normal without focal deficits.",
            source_page=2,
            confidence=0.99
        ),
        "symptom_duration_weeks": 8.0,
        "recent_normal_ct_within_30_days": False
    }

    report_not_met = criteria_service.evaluate_policy_case(
        policy=policy,
        case_id="CASE-P4-NOT-MET",
        patient_name="David Clark",
        facts=facts_not_met
    )

    assert report_not_met.decision_outcome == DecisionOutcome.DENIED
    assert report_not_met.verdict == Verdict.NOT_APPROVED
    crit_failed = next(r for r in report_not_met.criteria_results if r.rule_id == "CRIT-4-01")
    assert crit_failed.status == CriterionStatus.NOT_MET

    # 5. NOT_APPLICABLE status test (Explanatory Note)
    crit_note = next(r for r in report_met.criteria_results if r.rule_id == "CRIT-4-04")
    assert crit_note.status == CriterionStatus.NOT_APPLICABLE
    assert crit_note.ui_symbol == "–"


def test_phase4_and_or_minimum_count_logic(approved_test_policy_and_ruleset):
    """Requirement 3: Test AND/OR and MINIMUM_COUNT logic group evaluation."""
    policy, _ = approved_test_policy_and_ruleset

    # Create composite logic rules
    group_rule = CriterionRule(
        id="GRP-AND-01",
        policy_id=policy.id,
        policy_version="2026.1",
        section_number="2.0",
        section_name="Combined Clinical Criteria",
        source_page=1,
        source_text="Combined clinical criteria",
        plain_english_description="Combined clinical criteria",
        criterion_type=CriterionType.LOGIC_GROUP,
        operator=LogicOperator.AND,
        children=[
            CriterionRule(
                id="SUB-A",
                policy_id=policy.id,
                policy_version="2026.1",
                section_number="2.1",
                section_name="Sub A",
                criterion_type=CriterionType.CRITERION,
                fact_key="fact_a",
                source_page=1,
                source_text="Sub requirement A",
                plain_english_description="Sub requirement A"
            ),
            CriterionRule(
                id="SUB-B",
                policy_id=policy.id,
                policy_version="2026.1",
                section_number="2.2",
                section_name="Sub B",
                criterion_type=CriterionType.CRITERION,
                fact_key="fact_b",
                source_page=1,
                source_text="Sub requirement B",
                plain_english_description="Sub requirement B"
            )
        ]
    )

    # When both met: AND is MET
    res, children = criteria_service.evaluate_rule(group_rule, {"fact_a": True, "fact_b": True}, policy)
    assert res.status == CriterionStatus.MET

    # When one is missing: AND is NOT_DOCUMENTED (never NOT_MET)
    res_miss, _ = criteria_service.evaluate_rule(group_rule, {"fact_a": True, "fact_b": None}, policy)
    assert res_miss.status == CriterionStatus.NOT_DOCUMENTED

    # When one is explicitly False: AND is NOT_MET
    res_fail, _ = criteria_service.evaluate_rule(group_rule, {"fact_a": True, "fact_b": False}, policy)
    assert res_fail.status == CriterionStatus.NOT_MET

    # Test OR logic
    or_rule = CriterionRule(
        id="GRP-OR-01",
        policy_id=policy.id,
        policy_version="2026.1",
        section_number="3.0",
        section_name="Alternative Indications",
        source_page=1,
        source_text="Alternative indications",
        plain_english_description="Alternative indications",
        criterion_type=CriterionType.LOGIC_GROUP,
        operator=LogicOperator.OR,
        children=[
            CriterionRule(
                id="ALT-1",
                policy_id=policy.id,
                policy_version="2026.1",
                section_number="3.1",
                section_name="Alt 1",
                criterion_type=CriterionType.CRITERION,
                fact_key="alt_1",
                source_page=1,
                source_text="Alt requirement 1",
                plain_english_description="Alt requirement 1"
            ),
            CriterionRule(
                id="ALT-2",
                policy_id=policy.id,
                policy_version="2026.1",
                section_number="3.2",
                section_name="Alt 2",
                criterion_type=CriterionType.CRITERION,
                fact_key="alt_2",
                source_page=1,
                source_text="Alt requirement 2",
                plain_english_description="Alt requirement 2"
            )
        ]
    )

    # One met is sufficient for OR
    res_or, _ = criteria_service.evaluate_rule(or_rule, {"alt_1": True, "alt_2": False}, policy)
    assert res_or.status == CriterionStatus.MET

    # Test MINIMUM_COUNT logic
    min_rule = CriterionRule(
        id="GRP-MIN-01",
        policy_id=policy.id,
        policy_version="2026.1",
        section_number="4.0",
        section_name="High-Risk Features (Min 2)",
        source_page=1,
        source_text="High-risk features (min 2)",
        plain_english_description="High-risk features (min 2)",
        criterion_type=CriterionType.LOGIC_GROUP,
        operator=LogicOperator.MINIMUM_COUNT,
        min_count=2,
        children=[
            CriterionRule(id="F1", policy_id=policy.id, policy_version="2026.1", section_number="4.1", section_name="Feature 1", source_page=1, source_text="Feature 1", plain_english_description="Feature 1", fact_key="f1"),
            CriterionRule(id="F2", policy_id=policy.id, policy_version="2026.1", section_number="4.2", section_name="Feature 2", source_page=1, source_text="Feature 2", plain_english_description="Feature 2", fact_key="f2"),
            CriterionRule(id="F3", policy_id=policy.id, policy_version="2026.1", section_number="4.3", section_name="Feature 3", source_page=1, source_text="Feature 3", plain_english_description="Feature 3", fact_key="f3")
        ]
    )

    res_min_pass, _ = criteria_service.evaluate_rule(min_rule, {"f1": True, "f2": True, "f3": False}, policy)
    assert res_min_pass.status == CriterionStatus.MET

    res_min_fail, _ = criteria_service.evaluate_rule(min_rule, {"f1": True, "f2": False, "f3": False}, policy)
    assert res_min_fail.status == CriterionStatus.NOT_MET


def test_phase4_numeric_and_duration_thresholds(approved_test_policy_and_ruleset):
    """Requirement 3: Test numeric thresholds and duration comparisons."""
    policy, _ = approved_test_policy_and_ruleset

    rule_dur = CriterionRule(
        id="DUR-01",
        policy_id=policy.id,
        policy_version="2026.1",
        section_number="1.2",
        section_name="Conservative Management",
        source_page=1,
        source_text="Conservative management trial >= 6 weeks",
        plain_english_description="Conservative management trial >= 6 weeks",
        criterion_type=CriterionType.DURATION,
        threshold_value=6.0,
        comparison_op=">=",
        threshold_unit="weeks",
        fact_key="duration"
    )

    # >= 6 satisfied by 6.0
    res_6, _ = criteria_service.evaluate_rule(rule_dur, {"duration": 6.0}, policy)
    assert res_6.status == CriterionStatus.MET

    # >= 6 satisfied by 10.0
    res_10, _ = criteria_service.evaluate_rule(rule_dur, {"duration": 10.0}, policy)
    assert res_10.status == CriterionStatus.MET

    # >= 6 failed by 4.0
    res_4, _ = criteria_service.evaluate_rule(rule_dur, {"duration": 4.0}, policy)
    assert res_4.status == CriterionStatus.NOT_MET


def test_phase4_exclusion_contraindication_causes_denial(approved_test_policy_and_ruleset):
    """Requirement 3 & 6: Test exclusion contraindication causing denial."""
    policy, _ = approved_test_policy_and_ruleset

    # Case has all positive indications, but has exclusion present
    facts_with_exclusion = {
        "focal_neuro_deficit": True,
        "symptom_duration_weeks": 8.0,
        "recent_normal_ct_within_30_days": True  # Contraindication present!
    }

    report = criteria_service.evaluate_policy_case(
        policy=policy,
        case_id="CASE-P4-EXCLUSION",
        patient_name="Eve White",
        facts=facts_with_exclusion
    )

    assert report.verdict == Verdict.NOT_APPROVED
    assert report.decision_outcome == DecisionOutcome.DENIED
    assert report.requires_human_review
    assert any("contraindication" in reason.lower() for reason in report.review_reasons)

    excl_crit = next(r for r in report.criteria_results if r.rule_id == "CRIT-4-03")
    assert excl_crit.is_exclusion
    assert excl_crit.status == CriterionStatus.NOT_MET
    assert excl_crit.ui_label == "Exclusion Present"


def test_phase4_conditional_prerequisite_rule(approved_test_policy_and_ruleset):
    """Requirement 3: Test conditional rules with prerequisites."""
    policy, _ = approved_test_policy_and_ruleset

    cond_rule = CriterionRule(
        id="COND-01",
        policy_id=policy.id,
        policy_version="2026.1",
        section_number="5.1",
        section_name="Severe Trauma Evaluation",
        source_page=1,
        source_text="GCS < 13 following traumatic head injury.",
        plain_english_description="GCS < 13 following traumatic head injury.",
        criterion_type=CriterionType.CRITERION,
        conditional_prerequisite="trauma_present",
        fact_key="gcs_score_under_13"
    )

    # When trauma_present is False/None, criterion is NOT_APPLICABLE
    res_na, _ = criteria_service.evaluate_rule(cond_rule, {"trauma_present": False, "gcs_score_under_13": True}, policy)
    assert res_na.status == CriterionStatus.NOT_APPLICABLE

    # When trauma_present is True, criterion is evaluated
    res_met, _ = criteria_service.evaluate_rule(cond_rule, {"trauma_present": True, "gcs_score_under_13": True}, policy)
    assert res_met.status == CriterionStatus.MET


def test_phase4_reviewer_override_propagation_and_audit(approved_test_policy_and_ruleset):
    """
    Requirement 2, 5 & 9:
    Reviewer corrections on stored note records propagate to criteria evaluation,
    preserving clinician name, reason, and override status.
    """
    policy, _ = approved_test_policy_and_ruleset

    # Create note record with absent fact
    case_id = "CASE-P4-OVERRIDE-TEST"
    note_record = ClinicalNoteRecord(
        case_id=case_id,
        patient_name="Grace Hopper",
        procedure_requested="CT Head",
        policy_id=policy.id,
        facts={
            "focal_neuro_deficit": ExtractedFact(
                fact_key="focal_neuro_deficit",
                label="Focal Neuro Deficit",
                value=None,
                status=ClinicalFactStatus.ABSENT,
                excerpt=None,
                source_page=None,
                confidence=1.0
            ),
            "symptom_duration_weeks": ExtractedFact(
                fact_key="symptom_duration_weeks",
                label="Duration",
                value=8.0,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="8 weeks of headache",
                source_page=1,
                confidence=0.95
            ),
            "recent_normal_ct_within_30_days": ExtractedFact(
                fact_key="recent_normal_ct_within_30_days",
                label="Recent CT",
                value=False,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="No prior scans",
                source_page=1,
                confidence=0.95
            )
        }
    )
    note_extractor_service.save_note_record(note_record)

    # Evaluate before override -> should be ADDITIONAL_DOCUMENTATION_REQUIRED
    report_before = criteria_service.evaluate_note_record(policy, note_record)
    assert report_before.decision_outcome == DecisionOutcome.ADDITIONAL_DOCUMENTATION_REQUIRED

    # Apply reviewer override via API / service
    override_req = FactCorrectionRequest(
        fact_key="focal_neuro_deficit",
        corrected_value=True,
        corrected_status=ClinicalFactStatus.EXPLICIT,
        reviewer_name="Dr. Eleanor Vance, MD",
        reason="Found explicit left-sided hemiparesis documented on page 2 progress note."
    )
    updated_record = note_extractor_service.apply_fact_override(case_id, override_req)

    # Evaluate after override
    report_after = criteria_service.evaluate_note_record(policy, updated_record)
    assert report_after.decision_outcome == DecisionOutcome.APPROVED
    assert report_after.verdict == Verdict.APPROVED

    crit_overridden = next(r for r in report_after.criteria_results if r.rule_id == "CRIT-4-01")
    assert crit_overridden.status == CriterionStatus.MET
    assert crit_overridden.reviewer_overridden is True
    assert crit_overridden.reviewer_override_by == "Dr. Eleanor Vance, MD"
    assert "left-sided hemiparesis" in crit_overridden.reviewer_override_reason
    assert "Dr. Eleanor Vance, MD" in crit_overridden.comment


def test_phase4_api_cases_evaluate_endpoint(approved_test_policy_and_ruleset):
    """Requirement 8 & 9: Test POST /api/cases/{case_id}/evaluate endpoint."""
    policy, _ = approved_test_policy_and_ruleset

    case_id = "CASE-P4-API-EVAL"
    note_record = ClinicalNoteRecord(
        case_id=case_id,
        patient_name="Helen Troy",
        procedure_requested="Head CT Diagnostic",
        policy_id=policy.id,
        facts={
            "focal_neuro_deficit": ExtractedFact(
                fact_key="focal_neuro_deficit",
                label="Focal Neuro Deficit",
                value=True,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="Acute aphasia and facial weakness",
                source_page=1,
                confidence=0.98
            ),
            "symptom_duration_weeks": ExtractedFact(
                fact_key="symptom_duration_weeks",
                label="Duration",
                value=7.0,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="Persistent for 7 weeks",
                source_page=1,
                confidence=0.95
            ),
            "recent_normal_ct_within_30_days": ExtractedFact(
                fact_key="recent_normal_ct_within_30_days",
                label="Prior Scan",
                value=False,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="First neuro evaluation",
                source_page=1,
                confidence=0.95
            )
        }
    )
    note_extractor_service.save_note_record(note_record)

    response = client.post(f"/api/cases/{case_id}/evaluate")
    assert response.status_code == 200
    data = response.json()

    assert data["case_id"] == case_id
    assert data["patient_name"] == "Helen Troy"
    assert data["verdict"] == "APPROVED"
    assert data["decision_outcome"] == "APPROVED"
    assert data["is_synthetic_demo"] is True
    assert "DEVELOPMENT/DEMO MODE ONLY" in data["governance_notice"]
    assert len(data["criteria_results"]) >= 4
    assert len(data["key_reasoning"]) >= 1


def test_phase4_invalid_case_id_returns_404():
    """Requirement 9: Invalid case ID returns HTTP 404."""
    response = client.post("/api/cases/NON_EXISTENT_CASE_9999/evaluate")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_phase4_verification_gate_blocks_unapproved_policy(approved_test_policy_and_ruleset):
    """
    Requirement 7 & 9:
    Verification gate blocks evaluation if policy is not APPROVED_FOR_USE.
    """
    policy, _ = approved_test_policy_and_ruleset
    policy.lifecycle_status = PolicyLifecycleStatus.NEEDS_REVIEW
    registry_service._policies_cache[policy.id] = policy

    case_id = "CASE-GATE-TEST"
    note_record = ClinicalNoteRecord(
        case_id=case_id,
        patient_name="Gate Test Patient",
        procedure_requested="Head CT",
        policy_id=policy.id,
        facts={}
    )
    note_extractor_service.save_note_record(note_record)

    response = client.post(f"/api/cases/{case_id}/evaluate")
    assert response.status_code == 400
    assert "Policy Gate Blocked" in response.json()["detail"]


def test_phase4_verification_gate_blocks_unverified_ruleset(approved_test_policy_and_ruleset):
    """
    Requirement 7 & 9:
    Verification gate blocks evaluation if ruleset is not APPROVED_VERIFIED.
    """
    policy, ruleset = approved_test_policy_and_ruleset
    ruleset.verification_status = VerificationStatus.DRAFT
    criteria_service.save_ruleset(ruleset)

    case_id = "CASE-RULESET-GATE-TEST"
    note_record = ClinicalNoteRecord(
        case_id=case_id,
        patient_name="Ruleset Gate Patient",
        procedure_requested="Head CT",
        policy_id=policy.id,
        facts={}
    )
    note_extractor_service.save_note_record(note_record)

    response = client.post(f"/api/cases/{case_id}/evaluate")
    assert response.status_code == 400
    assert "Policy Verification Gate Blocked" in response.json()["detail"]


def test_phase4_verification_gate_rejects_empty_placeholder_checksum(approved_test_policy_and_ruleset):
    """
    Regression Test (Priority Check 1 & 2):
    Verification gate must explicitly reject the empty-file SHA-256 placeholder
    (e3b0c442...b855) on both policy and ruleset.
    """
    policy, ruleset = approved_test_policy_and_ruleset
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    policy.sha256_checksum = empty_hash
    registry_service._policies_cache[policy.id] = policy

    with pytest.raises(PolicyVerificationGateError) as exc_info:
        criteria_service.evaluate_policy_case(
            policy=policy,
            case_id="CASE-EMPTY-HASH",
            patient_name="Empty Hash Test",
            facts={}
        )
    assert "empty or placeholder checksum" in str(exc_info.value).lower()


def test_phase4_verification_gate_detects_checksum_mismatch(approved_test_policy_and_ruleset):
    """
    Regression Test (Priority Check 2):
    Verification gate must reject evaluation when policy checksum does not match ruleset checksum.
    """
    policy, ruleset = approved_test_policy_and_ruleset
    policy.sha256_checksum = "1111222233334444555566667777888899990000111122223333444455556666"
    ruleset.policy_checksum = "aaaabbbbccccddddeeeeffff0000111122223333444455556666777788889999"
    registry_service._policies_cache[policy.id] = policy
    criteria_service.save_ruleset(ruleset)

    with pytest.raises(PolicyVerificationGateError) as exc_info:
        criteria_service.evaluate_policy_case(
            policy=policy,
            case_id="CASE-MISMATCH",
            patient_name="Mismatch Test",
            facts={}
        )
    assert "checksum" in str(exc_info.value).lower()
    assert "does not match" in str(exc_info.value).lower()


def test_phase4_verification_gate_validates_physical_disk_file_bytes(tmp_path, approved_test_policy_and_ruleset):
    """
    Regression Test (Priority Check 2):
    Verification gate must compute hash from actual physical file bytes on disk and reject tampering.
    """
    policy, ruleset = approved_test_policy_and_ruleset
    fake_pdf = tmp_path / "tampered_policy.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 modified tampered contents")

    policy.storage_path = str(fake_pdf)
    policy.sha256_checksum = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    ruleset.policy_checksum = policy.sha256_checksum
    registry_service._policies_cache[policy.id] = policy
    criteria_service.save_ruleset(ruleset)

    with pytest.raises(PolicyVerificationGateError) as exc_info:
        criteria_service.evaluate_policy_case(
            policy=policy,
            case_id="CASE-TAMPERED",
            patient_name="Tampered PDF Test",
            facts={}
        )
    assert "physical pdf on disk does not match" in str(exc_info.value).lower()


def test_phase4_demo_verdict_sentence_and_watermark_labelled(approved_test_policy_and_ruleset):
    """
    Regression Test (Priority Check 3):
    All evaluation responses must explicitly prefix verdict_sentence with
    '[DEMO / SYNTHETIC CASE - NOT A CLINICAL DECISION]' and set is_synthetic_demo = True.
    """
    policy, ruleset = approved_test_policy_and_ruleset
    report = criteria_service.evaluate_policy_case(
        policy=policy,
        case_id="CASE-DEMO-LABEL",
        patient_name="Demo Patient",
        facts={
            "focal_neuro_deficit": {"value": True, "status": "explicit"},
            "symptom_duration_weeks": {"value": 7.0, "status": "explicit"},
            "recent_normal_ct_within_30_days": {"value": False, "status": "explicit"}
        }
    )

    assert report.is_synthetic_demo is True
    assert report.verdict == Verdict.APPROVED
    assert report.verdict_sentence.startswith("[DEMO / SYNTHETIC CASE - NOT A CLINICAL DECISION]")
    assert "DEVELOPMENT/DEMO MODE ONLY: Synthetic Clinical Records" in report.governance_notice


def test_phase4_api_evaluate_blocks_unverified_and_missing_rulesets(approved_test_policy_and_ruleset):
    """
    Regression Test (Priority Check 3):
    API POST /api/evaluate endpoint must reject policies without a verified ruleset.
    """
    policy, ruleset = approved_test_policy_and_ruleset

    # Test missing ruleset
    missing_policy = Policy(
        id="P-NO-RULESET",
        insurer="United Healthcare",
        policy_name="No Ruleset Policy",
        version="2026.1",
        effective_date="2026-01-01",
        procedure_type="CT",
        procedure_full_name="CT Head",
        cpt_codes=["70450"],
        plan="Commercial",
        lifecycle_status=PolicyLifecycleStatus.APPROVED_FOR_USE,
        approved_by="Dr. Jenkins",
        sha256_checksum="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    )
    registry_service._policies_cache[missing_policy.id] = missing_policy

    res = client.post("/api/evaluate", json={
        "case_id": "CASE-MISSING-RULESET",
        "patient_name": "Test Missing Ruleset",
        "policy_id": missing_policy.id,
        "facts": {}
    })
    assert res.status_code == 400
    assert "no criteria ruleset found" in res.json()["detail"].lower()

