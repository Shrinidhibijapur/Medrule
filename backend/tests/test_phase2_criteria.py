import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app, DATA_DIR
from app.models.policy import Policy, PolicyLifecycleStatus
from app.models.criteria import (
    CriterionRule,
    CriterionType,
    LogicOperator,
    ComparisonOperator,
    VerificationStatus,
    PolicyRuleset,
    VerificationGateRequest,
)
from app.models.evaluation import CriterionStatus, Verdict, DecisionOutcome
from app.services.criteria_service import CriteriaService, PolicyVerificationGateError

client = TestClient(app)

@pytest.fixture
def criteria_service():
    return CriteriaService(DATA_DIR)

@pytest.fixture
def sample_approved_uhc_policy():
    return Policy(
        id="P-UHC-CT-2026",
        policy_id="POL-UHC-CT",
        insurer="United Healthcare",
        policy_name="CT Scan of Head / Brain",
        version="2026.1",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan of Head with Contrast",
        cpt_codes=["70450", "70460"],
        effective_date="2026-01-01",
        sha256_checksum="681f8ececb53bcacf5e0950b6a8058284dfc468d63c517ea2355a781cedc00a7",
        total_pages=4,
        lifecycle_status=PolicyLifecycleStatus.APPROVED_FOR_USE,
        criteria=[]
    )

@pytest.fixture
def sample_unverified_ruleset():
    return PolicyRuleset(
        policy_id="P-UHC-CT-TEST",
        policy_name="Test Policy",
        policy_version="1.0",
        policy_checksum="test_checksum_12345",
        procedure_type="CT Scan",
        verification_status=VerificationStatus.DRAFT,
        rules=[
            CriterionRule(
                id="TEST-CRIT-001",
                policy_id="P-UHC-CT-TEST",
                policy_version="1.0",
                section_number="Section 1.1",
                section_name="Test Symptom Indication",
                source_page=1,
                source_text="Patient must demonstrate documented symptoms.",
                plain_english_description="Requirement: Documented symptoms.",
                criterion_type=CriterionType.CRITERION,
                is_mandatory=True,
                fact_key="symptoms_present",
                verification_status=VerificationStatus.DRAFT
            ),
            CriterionRule(
                id="TEST-CRIT-002",
                policy_id="P-UHC-CT-TEST",
                policy_version="1.0",
                section_number="Section 1.2",
                section_name="Duration Requirement",
                source_page=2,
                source_text="Symptoms must persist for at least 6 weeks.",
                plain_english_description="Requirement: Duration >= 6 weeks.",
                criterion_type=CriterionType.DURATION,
                is_mandatory=True,
                fact_key="symptom_duration",
                comparison_op=">=",
                threshold_value=6.0,
                threshold_unit="weeks",
                verification_status=VerificationStatus.DRAFT
            )
        ]
    )

# --- 1. Structured Criteria & Rule Evaluation Tests ---

def test_simple_criterion_met_and_not_met(criteria_service, sample_approved_uhc_policy):
    rule = CriterionRule(
        id="CRIT-IND-01",
        policy_id="P-UHC-CT-2026",
        policy_version="2026.1",
        section_number="Section 4.2.1",
        section_name="Neurological Symptoms",
        source_page=1,
        source_text="Patient must have documented focal or generalized neurological symptoms.",
        plain_english_description="Requirement: Focal or generalized neurological symptoms.",
        criterion_type=CriterionType.CRITERION,
        is_mandatory=True,
        fact_key="neuro_symptoms"
    )

    # Case A: MET
    facts_met = {"neuro_symptoms": {"value": True, "excerpt": "Chronic atypical headaches with dizziness", "source_page": 1}}
    res_met, _ = criteria_service.evaluate_rule(rule, facts_met, sample_approved_uhc_policy)
    assert res_met.status == CriterionStatus.MET
    assert res_met.ui_symbol == "✅"
    assert res_met.ui_label == "Satisfied"
    assert "Section 4.2.1" in res_met.policy_citation

    # Case B: NOT_MET
    facts_unmet = {"neuro_symptoms": {"value": False, "excerpt": "No neurological symptoms documented on exam", "source_page": 1}}
    res_unmet, _ = criteria_service.evaluate_rule(rule, facts_unmet, sample_approved_uhc_policy)
    assert res_unmet.status == CriterionStatus.NOT_MET
    assert res_unmet.ui_symbol == "❌"
    assert res_unmet.ui_label == "Not met"

def test_and_group_logic(criteria_service, sample_approved_uhc_policy):
    rule_a = CriterionRule(
        id="CRIT-A", policy_id="P-UHC-CT-2026", policy_version="2026.1",
        section_number="4.1", section_name="A", source_page=1, source_text="Req A",
        plain_english_description="Req A", fact_key="fact_a"
    )
    rule_b = CriterionRule(
        id="CRIT-B", policy_id="P-UHC-CT-2026", policy_version="2026.1",
        section_number="4.2", section_name="B", source_page=1, source_text="Req B",
        plain_english_description="Req B", fact_key="fact_b"
    )
    group_and = CriterionRule(
        id="GRP-AND", policy_id="P-UHC-CT-2026", policy_version="2026.1",
        section_number="4.0", section_name="Mandatory Group", source_page=1,
        source_text="Both A and B are required", plain_english_description="Both A and B required",
        criterion_type=CriterionType.LOGIC_GROUP, operator=LogicOperator.AND,
        children=[rule_a, rule_b]
    )

    # Both met -> MET
    facts_both = {"fact_a": {"value": True}, "fact_b": {"value": True}}
    res, _ = criteria_service.evaluate_rule(group_and, facts_both, sample_approved_uhc_policy)
    assert res.status == CriterionStatus.MET
    assert res.ui_symbol == "✅"

    # One not met -> NOT_MET
    facts_one = {"fact_a": {"value": True}, "fact_b": {"value": False}}
    res, _ = criteria_service.evaluate_rule(group_and, facts_one, sample_approved_uhc_policy)
    assert res.status == CriterionStatus.NOT_MET
    assert res.ui_symbol == "❌"

def test_or_group_logic(criteria_service, sample_approved_uhc_policy):
    path_1 = CriterionRule(
        id="PATH-1", policy_id="P-UHC-CT-2026", policy_version="2026.1",
        section_number="5.1", section_name="Pathway 1", source_page=1, source_text="Req 1",
        plain_english_description="Req 1", fact_key="path_1"
    )
    path_2 = CriterionRule(
        id="PATH-2", policy_id="P-UHC-CT-2026", policy_version="2026.1",
        section_number="5.2", section_name="Pathway 2", source_page=1, source_text="Req 2",
        plain_english_description="Req 2", fact_key="path_2"
    )
    group_or = CriterionRule(
        id="GRP-OR", policy_id="P-UHC-CT-2026", policy_version="2026.1",
        section_number="5.0", section_name="Alternative Pathways", source_page=1,
        source_text="Either 1 or 2", plain_english_description="Either 1 or 2",
        criterion_type=CriterionType.LOGIC_GROUP, operator=LogicOperator.OR,
        children=[path_1, path_2]
    )

    # 1 of 2 met -> MET
    facts = {"path_1": {"value": False}, "path_2": {"value": True}}
    res, _ = criteria_service.evaluate_rule(group_or, facts, sample_approved_uhc_policy)
    assert res.status == CriterionStatus.MET
    assert res.ui_symbol == "✅"

def test_minimum_count_group_logic(criteria_service, sample_approved_uhc_policy):
    c1 = CriterionRule(id="C1", policy_id="P", policy_version="1", section_number="1", section_name="1", source_page=1, source_text="1", plain_english_description="1", fact_key="c1")
    c2 = CriterionRule(id="C2", policy_id="P", policy_version="1", section_number="2", section_name="2", source_page=1, source_text="2", plain_english_description="2", fact_key="c2")
    c3 = CriterionRule(id="C3", policy_id="P", policy_version="1", section_number="3", section_name="3", source_page=1, source_text="3", plain_english_description="3", fact_key="c3")

    min_group = CriterionRule(
        id="GRP-MIN-2", policy_id="P", policy_version="1", section_number="0", section_name="Min 2 of 3",
        source_page=1, source_text="At least 2 of 3 required", plain_english_description="At least 2 of 3",
        criterion_type=CriterionType.LOGIC_GROUP, operator=LogicOperator.MINIMUM_COUNT, min_count=2,
        children=[c1, c2, c3]
    )

    # 2 met -> MET
    facts_2 = {"c1": {"value": True}, "c2": {"value": True}, "c3": {"value": False}}
    res, _ = criteria_service.evaluate_rule(min_group, facts_2, sample_approved_uhc_policy)
    assert res.status == CriterionStatus.MET

    # Only 1 met -> NOT_MET
    facts_1 = {"c1": {"value": True}, "c2": {"value": False}, "c3": {"value": False}}
    res, _ = criteria_service.evaluate_rule(min_group, facts_1, sample_approved_uhc_policy)
    assert res.status == CriterionStatus.NOT_MET

def test_conditional_prerequisite(criteria_service, sample_approved_uhc_policy):
    cond_rule = CriterionRule(
        id="CRIT-CONTRAST",
        policy_id="P-UHC-CT-2026",
        policy_version="2026.1",
        section_number="Section 4.2.6",
        section_name="IV Contrast Rationale",
        source_page=4,
        source_text="Explicit diagnostic rationale for contrast must be documented.",
        plain_english_description="Conditional: Contrast justification required when contrast is requested.",
        criterion_type=CriterionType.CRITERION,
        is_mandatory=False,
        conditional_prerequisite="contrast_requested",
        fact_key="contrast_justified"
    )

    # When contrast is NOT requested: status is NOT_APPLICABLE with "–"
    facts_no_contrast = {"contrast_requested": {"value": False}}
    res, _ = criteria_service.evaluate_rule(cond_rule, facts_no_contrast, sample_approved_uhc_policy)
    assert res.status == CriterionStatus.NOT_APPLICABLE
    assert res.ui_symbol == "–"

    # When contrast IS requested and justified: status is MET with "✅"
    facts_contrast_met = {
        "contrast_requested": {"value": True},
        "contrast_justified": {"value": True, "excerpt": "Contrast needed to evaluate vascular malformation"}
    }
    res_met, _ = criteria_service.evaluate_rule(cond_rule, facts_contrast_met, sample_approved_uhc_policy)
    assert res_met.status == CriterionStatus.MET
    assert res_met.ui_symbol == "✅"

def test_duration_and_numeric_thresholds(criteria_service, sample_approved_uhc_policy):
    duration_rule = CriterionRule(
        id="CRIT-DUR",
        policy_id="P-UHC-CT-2026",
        policy_version="2026.1",
        section_number="Section 4.2.2",
        section_name="Symptom Duration",
        source_page=2,
        source_text="Symptoms must persist for at least 6 weeks.",
        plain_english_description="Symptoms must persist >= 6 weeks.",
        criterion_type=CriterionType.DURATION,
        fact_key="headache_weeks",
        comparison_op=">=",
        threshold_value=6.0,
        threshold_unit="weeks"
    )

    # 8 weeks >= 6 -> MET
    res_pass, _ = criteria_service.evaluate_rule(duration_rule, {"headache_weeks": {"value": 8}}, sample_approved_uhc_policy)
    assert res_pass.status == CriterionStatus.MET

    # 4 weeks < 6 -> NOT_MET
    res_fail, _ = criteria_service.evaluate_rule(duration_rule, {"headache_weeks": {"value": 4}}, sample_approved_uhc_policy)
    assert res_fail.status == CriterionStatus.NOT_MET

def test_exclusion_logic_causes_denial(criteria_service, sample_approved_uhc_policy):
    excl_rule = CriterionRule(
        id="EXCL-ALLERGY",
        policy_id="P-UHC-CT-2026",
        policy_version="2026.1",
        section_number="Section 4.2.7",
        section_name="Anaphylactic Contrast Allergy",
        source_page=4,
        source_text="Severe prior anaphylaxis to iodinated contrast without pre-medication protocol is contraindicated.",
        plain_english_description="Exclusion: Anaphylactic contrast allergy.",
        criterion_type=CriterionType.EXCLUSION,
        is_exclusion=True,
        fact_key="contrast_anaphylaxis"
    )

    # Allergy is present (value=True) -> NOT_MET / Exclusion triggered
    res_excl, _ = criteria_service.evaluate_rule(excl_rule, {"contrast_anaphylaxis": {"value": True, "excerpt": "Prior anaphylaxis to iodinated dye"}}, sample_approved_uhc_policy)
    assert res_excl.status == CriterionStatus.NOT_MET
    assert res_excl.ui_symbol == "❌"
    assert res_excl.ui_label == "Exclusion Present"

# --- 2. Missing Documentation Semantics & Uncertainty ---

def test_missing_documentation_distinct_from_clinical_failure(criteria_service, sample_approved_uhc_policy):
    """
    Mandatory safeguard: A missing document is NOT a clinical failure.
    Outcome must be ADDITIONAL_DOCUMENTATION_REQUIRED, not an outright clinical denial.
    """
    facts_partial = {
        "neurological_symptoms": {"value": True, "excerpt": "Persistent daily headaches"},
        "symptom_duration_weeks": {"value": 8.0, "excerpt": "8 weeks duration"},
        # conservative_treatment_attempted is omitted (NOT_DOCUMENTED)
        "neurological_exam_abnormal": {"value": True, "excerpt": "Right-sided hyperreflexia"},
        "rule_out_pathology": {"value": True, "excerpt": "Rule out intracranial neoplasm"}
    }

    report = criteria_service.evaluate_policy_case(
        policy=sample_approved_uhc_policy,
        case_id="CASE-DOC-MISSING",
        patient_name="Alex Doe",
        facts=facts_partial
    )

    assert report.decision_outcome == DecisionOutcome.ADDITIONAL_DOCUMENTATION_REQUIRED
    assert report.verdict == Verdict.NOT_APPROVED
    assert report.requires_human_review is True
    # Reason clearly states missing documentation
    assert any("Missing clinical documentation" in r for r in report.key_reasoning)
    assert "re-assessed once the missing records are submitted" in report.verdict_sentence

def test_unclear_conflicting_evidence_triggers_cannot_be_determined(criteria_service, sample_approved_uhc_policy):
    facts_unclear = {
        "neurological_symptoms": {"value": True, "is_unclear": True, "excerpt": "Conflicting notes: patient denies and reports headache"},
        "symptom_duration_weeks": {"value": 8.0},
        "conservative_treatment_attempted": {"value": True},
        "neurological_exam_abnormal": {"value": True},
        "rule_out_pathology": {"value": True}
    }

    report = criteria_service.evaluate_policy_case(
        policy=sample_approved_uhc_policy,
        case_id="CASE-UNCLEAR",
        patient_name="Alex Doe",
        facts=facts_unclear
    )

    assert report.decision_outcome == DecisionOutcome.CANNOT_BE_DETERMINED
    assert report.verdict == Verdict.CANNOT_BE_DETERMINED
    assert report.requires_human_review is True
    assert any("Ambiguous or conflicting" in r for r in report.key_reasoning)

# --- 3. Policy Verification Gate & Audit Safeguards ---

def test_verification_gate_requires_independent_second_reviewer(criteria_service, sample_approved_uhc_policy, sample_unverified_ruleset):
    criteria_service.save_ruleset(sample_unverified_ruleset)

    # Attempt with identical reviewer -> Rejected
    same_reviewer_req = VerificationGateRequest(
        primary_reviewer="Dr. Sarah Jenkins",
        primary_reviewer_role="Medical Director",
        secondary_reviewer="Dr. Sarah Jenkins",  # Same reviewer!
        secondary_reviewer_role="Medical Director",
        source_criteria_count=2,
        side_by_side_verified=True,
        plain_english_verified=True
    )

    with pytest.raises(PolicyVerificationGateError, match="must be an independent individual"):
        criteria_service.verify_ruleset_gate(sample_approved_uhc_policy, same_reviewer_req)

def test_verification_gate_detects_checksum_mismatch(criteria_service, sample_unverified_ruleset):
    # Ruleset checksum differs from policy checksum
    test_policy = Policy(
        id=sample_unverified_ruleset.policy_id,
        insurer="Test Insurer",
        policy_name="Test Policy",
        version="1.0",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan Test",
        effective_date="2026-01-01",
        sha256_checksum="expected_checksum_correct",
        lifecycle_status=PolicyLifecycleStatus.APPROVED_FOR_USE
    )
    sample_unverified_ruleset.policy_checksum = "mismatched_checksum_99999"
    criteria_service.save_ruleset(sample_unverified_ruleset)

    gate_req = VerificationGateRequest(
        primary_reviewer="Dr. Sarah Jenkins",
        primary_reviewer_role="Medical Director",
        secondary_reviewer="Marcus Vance",
        secondary_reviewer_role="Clinical Auditor",
        source_criteria_count=2,
        side_by_side_verified=True,
        plain_english_verified=True
    )

    with pytest.raises(PolicyVerificationGateError, match="PDF checksum mismatch"):
        criteria_service.verify_ruleset_gate(test_policy, gate_req)

def test_evaluation_blocked_when_policy_unapproved(criteria_service, sample_approved_uhc_policy):
    # Set policy to DRAFT / NEEDS_REVIEW
    sample_approved_uhc_policy.lifecycle_status = PolicyLifecycleStatus.NEEDS_REVIEW

    with pytest.raises(PolicyVerificationGateError, match="Policy Gate Blocked"):
        criteria_service.evaluate_policy_case(
            policy=sample_approved_uhc_policy,
            case_id="CASE-BLOCK",
            patient_name="Test Patient",
            facts={}
        )

def test_reasoning_strictly_precedes_verdict_sentence(criteria_service, sample_approved_uhc_policy):
    facts_all_met = {
        "neurological_symptoms": {"value": True, "excerpt": "Focal symptoms present"},
        "symptom_duration_weeks": {"value": 8.0, "excerpt": "8 weeks duration"},
        "conservative_treatment_attempted": {"value": True, "excerpt": "Tried NSAIDs"},
        "neurological_exam_abnormal": {"value": True, "excerpt": "Asymmetry noted"},
        "rule_out_pathology": {"value": True, "excerpt": "Rule out lesion"}
    }

    report = criteria_service.evaluate_policy_case(
        policy=sample_approved_uhc_policy,
        case_id="CASE-VERIFIED",
        patient_name="Alex Doe",
        facts=facts_all_met
    )

    assert report.decision_outcome == DecisionOutcome.APPROVED
    assert report.verdict == Verdict.APPROVED
    assert len(report.key_reasoning) > 0
    # Confirm key_reasoning appears in report before verdict
    dict_repr = report.model_dump() if hasattr(report, "model_dump") else report.dict()
    keys = list(dict_repr.keys())
    assert keys.index("key_reasoning") < keys.index("verdict_sentence")

# --- 4. API Endpoint Integration Tests ---

def test_api_get_policy_criteria():
    res = client.get("/api/policies/P-UHC-CT-2026/criteria")
    assert res.status_code == 200
    data = res.json()
    assert data["policy_id"] == "P-UHC-CT-2026"
    assert len(data["rules"]) > 0
    assert data["verification_status"] == "APPROVED_VERIFIED"

def test_api_criteria_evaluate_endpoint():
    payload = {
        "policy_id": "P-UHC-CT-2026",
        "case_id": "CASE-API-TEST",
        "patient_name": "API Patient",
        "patient_facts": {
            "neurological_symptoms": {"value": True, "excerpt": "Severe daily headaches"},
            "symptom_duration_weeks": {"value": 10.0, "excerpt": "10 weeks duration"},
            "conservative_treatment_attempted": {"value": True, "excerpt": "Tried physical therapy and medications"},
            "neurological_exam_abnormal": {"value": True, "excerpt": "Papilledema and reflex asymmetry"},
            "rule_out_pathology": {"value": True, "excerpt": "Rule out intracranial mass"}
        }
    }
    res = client.post("/api/criteria/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verdict"] == "APPROVED"
    assert data["decision_outcome"] == "APPROVED"
    assert len(data["criteria_results"]) > 0
    assert data["verification_gate_verified"] is True

def test_api_evaluate_blocks_draft_ruleset(criteria_service):
    """Verifies that POST /api/evaluate cannot bypass unverified DRAFT criteria rulesets."""
    ruleset_file = criteria_service._get_ruleset_file("P-UHC-CT-2026")
    original_content = ruleset_file.read_text(encoding="utf-8")
    try:
        # Save draft version
        draft_ruleset = PolicyRuleset(
            policy_id="P-UHC-CT-2026",
            policy_name="CT Scan",
            policy_version="2026.1",
            policy_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            procedure_type="CT Scan",
            verification_status=VerificationStatus.DRAFT,
            rules=[]
        )
        criteria_service.save_ruleset(draft_ruleset)

        payload = {
            "case_id": "TEST-BYPASS",
            "patient_name": "Test Bypass",
            "policy_id": "P-UHC-CT-2026",
            "facts": {}
        }
        res = client.post("/api/evaluate", json=payload)
        assert res.status_code == 400
        assert "Policy Verification Gate Blocked" in res.json()["detail"]
    finally:
        ruleset_file.write_text(original_content, encoding="utf-8")

