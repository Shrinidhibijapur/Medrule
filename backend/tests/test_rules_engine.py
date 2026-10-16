import pytest
from app.models.policy import Policy, Criterion
from app.models.evaluation import CriterionStatus, Verdict
from app.engine.rules_engine import DeterministicRulesEngine

def test_single_criterion_met():
    criterion = Criterion(
        id="R1",
        section="§4.2.1",
        name="Clinical Indication",
        requirement="Patient has symptoms",
        mandatory=True,
        fact_key="symptoms"
    )
    facts = {
        "symptoms": {"value": True, "excerpt": "Headaches noted", "source_page": 1}
    }
    result = DeterministicRulesEngine.evaluate_criterion(criterion, facts)
    assert result.status == CriterionStatus.MET
    assert result.ui_symbol == "✅"
    assert result.ui_label == "Satisfied"

def test_single_criterion_not_documented():
    criterion = Criterion(
        id="R3",
        section="§4.2.3",
        name="Previous Treatment",
        requirement="Conservative therapy",
        mandatory=True,
        fact_key="conservative_treatment"
    )
    facts = {}  # Empty facts
    result = DeterministicRulesEngine.evaluate_criterion(criterion, facts)
    assert result.status == CriterionStatus.NOT_DOCUMENTED
    assert result.ui_symbol == "❌"
    assert result.ui_label == "Not documented"

def test_numeric_duration_threshold():
    criterion = Criterion(
        id="R2",
        section="§4.2.2",
        name="Duration",
        requirement=">= 6 weeks",
        mandatory=True,
        fact_key="duration",
        min_value=6
    )
    # Exceeds threshold
    assert DeterministicRulesEngine.evaluate_criterion(
        criterion, {"duration": {"value": 12, "source_page": 1}}
    ).status == CriterionStatus.MET

    # Below threshold
    assert DeterministicRulesEngine.evaluate_criterion(
        criterion, {"duration": {"value": 4, "source_page": 1}}
    ).status == CriterionStatus.NOT_MET

def test_reasoning_precedes_verdict():
    policy = Policy(
        id="P-TEST",
        insurer="Test Insurer",
        policy_name="Test Policy",
        version="2026",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan Test",
        effective_date="2026-01-01",
        criteria=[
            Criterion(id="T1", section="§1", name="Test", requirement="Req", fact_key="f1")
        ]
    )
    report = DeterministicRulesEngine.evaluate_case(
        case_id="C1",
        patient_name="Test Patient",
        policy=policy,
        facts={"f1": {"value": True, "excerpt": "ok", "source_page": 1}}
    )
    assert len(report.key_reasoning) > 0
    assert report.verdict == Verdict.APPROVED
    assert "Therefore the CT Scan request can be approved." in report.verdict_sentence
