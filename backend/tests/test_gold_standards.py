import json
from pathlib import Path
from app.models.policy import Policy
from app.models.evaluation import Verdict
from app.engine.rules_engine import DeterministicRulesEngine

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def test_gold_standard_case_001_john_doe():
    policy_path = DATA_DIR / "policies" / "united_healthcare_ct_head_2026.json"
    note_path = DATA_DIR / "notes" / "case_001_john_doe_ct_head.json"
    bench_path = DATA_DIR / "gold_standards" / "expected_evaluations.json"

    with open(policy_path, "r", encoding="utf-8") as f:
        policy = Policy(**json.load(f))
    with open(note_path, "r", encoding="utf-8") as f:
        note_data = json.load(f)
    with open(bench_path, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)["benchmarks"]

    bench = next(b for b in benchmarks if b["case_id"] == "CASE-2026-001")

    report = DeterministicRulesEngine.evaluate_case(
        case_id=note_data["case_id"],
        patient_name=note_data["patient_name"],
        policy=policy,
        facts=note_data["extracted_facts"]
    )

    # 1. Verify Verdict matches expected
    assert report.verdict.value == bench["expected_verdict"]

    # 2. Verify all criteria match expected status
    for cr in report.criteria_results:
        exp = bench["expected_criteria"][cr.rule_id]
        assert cr.status.value == exp["status"], f"Mismatch on {cr.rule_id}: got {cr.status.value}, expected {exp['status']}"
        assert cr.ui_symbol == "✅"
