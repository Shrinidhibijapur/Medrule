"""
MedRule Phase 0 — Acceptance & Deliverables Verification Test Suite
Verifies all exit criteria for Phase 0 as defined in MedRule_Implementation_Plan.md
"""

import json
from pathlib import Path
import pytest

from app.models.policy import Policy
from app.models.evaluation import CriterionStatus, Verdict
from app.engine.rules_engine import DeterministicRulesEngine

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DOCS_DIR = ROOT_DIR / "docs" / "phase0"

class TestPhase0Deliverables:
    """Task 1 & 2: Verification of required documentation deliverables"""

    @pytest.mark.parametrize("filename", [
        "01_repo_and_architecture_map.md",
        "02_policy_inventory_and_gold_standard_notes.md",
        "03_requirements_traceability_matrix.md",
        "04_status_semantics_and_verdict_engine_spec.md",
        "05_privacy_security_and_governance.md",
    ])
    def test_deliverable_document_exists(self, filename: str):
        doc_path = DOCS_DIR / filename
        assert doc_path.exists(), f"Deliverable {filename} is missing from docs/phase0"
        assert doc_path.stat().st_size > 100, f"Deliverable {filename} is empty or incomplete"

    def test_ui_reference_assets_complete(self):
        ui_dir = ROOT_DIR / "medauth_ui_slides_separate_images"
        assert ui_dir.exists(), "medauth_ui_slides_separate_images directory is missing"
        slides = list(ui_dir.glob("*.png"))
        assert len(slides) == 9, f"Expected 9 UI reference slides, found {len(slides)}"

class TestPhase0PolicyRegistry:
    """Task 4: Inventory and schema validation of authoritative policy rulebooks"""

    def test_uhc_ct_head_policy_schema(self):
        policy_file = DATA_DIR / "policies" / "united_healthcare_ct_head_2026.json"
        assert policy_file.exists(), "UHC CT Head 2026 policy JSON is missing"

        with open(policy_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        policy = Policy(**data)
        assert policy.id == "P-UHC-CT-2026"
        assert policy.insurer == "United Healthcare"
        assert policy.lifecycle_status == "APPROVED_FOR_USE"
        assert len(policy.criteria) == 6, "Expected 6 evaluated clinical criteria"

class TestPhase0StatusSemantics:
    """Task 9 & Plan §2.3: Met, Not met, Not documented, and layout rules"""

    def test_status_met_maps_to_green_check(self):
        policy_file = DATA_DIR / "policies" / "united_healthcare_ct_head_2026.json"
        with open(policy_file, "r", encoding="utf-8") as f:
            policy = Policy(**json.load(f))

        crit = policy.criteria[0]  # R1
        res = DeterministicRulesEngine.evaluate_criterion(
            crit, {"neurological_symptoms": {"value": True, "source_page": 1}}
        )
        assert res.status == CriterionStatus.MET
        assert res.ui_symbol == "✅"
        assert res.ui_label == "Satisfied"

    def test_status_not_documented_maps_to_red_cross_with_reason(self):
        policy_file = DATA_DIR / "policies" / "united_healthcare_ct_head_2026.json"
        with open(policy_file, "r", encoding="utf-8") as f:
            policy = Policy(**json.load(f))

        crit = policy.criteria[0]
        res = DeterministicRulesEngine.evaluate_criterion(crit, {})  # Missing fact
        assert res.status == CriterionStatus.NOT_DOCUMENTED
        assert res.ui_symbol == "❌"
        assert res.ui_label == "Not documented"

    def test_reasoning_strictly_precedes_verdict_sentence(self):
        policy_file = DATA_DIR / "policies" / "united_healthcare_ct_head_2026.json"
        note_file = DATA_DIR / "notes" / "case_001_john_doe_ct_head.json"

        with open(policy_file, "r", encoding="utf-8") as f:
            policy = Policy(**json.load(f))
        with open(note_file, "r", encoding="utf-8") as f:
            note = json.load(f)

        report = DeterministicRulesEngine.evaluate_case(
            case_id=note["case_id"],
            patient_name=note["patient_name"],
            policy=policy,
            facts=note["extracted_facts"]
        )

        assert len(report.key_reasoning) > 0, "Key reasoning bullets must be populated"
        assert "All required clinical criteria are satisfied" in report.key_reasoning[0]
        assert report.verdict == Verdict.APPROVED
        assert "Approval of a CT Scan requires" in report.verdict_sentence

class TestPhase0GoldStandards:
    """Task 5 & Plan §10.5: Gold standard test harness against expert expectations"""

    def test_gold_standard_case_001_riverside_ct_scan(self):
        policy_file = DATA_DIR / "policies" / "united_healthcare_ct_head_2026.json"
        note_file = DATA_DIR / "notes" / "case_001_john_doe_ct_head.json"
        bench_file = DATA_DIR / "gold_standards" / "expected_evaluations.json"

        with open(policy_file, "r", encoding="utf-8") as f:
            policy = Policy(**json.load(f))
        with open(note_file, "r", encoding="utf-8") as f:
            note = json.load(f)
        with open(bench_file, "r", encoding="utf-8") as f:
            benchmarks = json.load(f)["benchmarks"]

        bench = next(b for b in benchmarks if b["case_id"] == "CASE-2026-001")

        report = DeterministicRulesEngine.evaluate_case(
            case_id=note["case_id"],
            patient_name=note["patient_name"],
            policy=policy,
            facts=note["extracted_facts"]
        )

        assert report.verdict.value == bench["expected_verdict"]

        for cr in report.criteria_results:
            exp = bench["expected_criteria"][cr.rule_id]
            assert cr.status.value == exp["status"]

class TestPhase0FrontendArtifacts:
    """UI Verification: Verification of frontend components and production build"""

    def test_frontend_components_present(self):
        fe_src = ROOT_DIR / "frontend" / "src"
        assert (fe_src / "App.tsx").exists(), "Frontend App.tsx is missing"
        assert (fe_src / "views" / "LoginView.tsx").exists(), "LoginView is missing"
        assert (fe_src / "views" / "DashboardView.tsx").exists(), "DashboardView is missing"
        assert (fe_src / "views" / "NewReviewView.tsx").exists(), "NewReviewView is missing"
        assert (fe_src / "views" / "CriteriaEvaluationView.tsx").exists(), "CriteriaEvaluationView is missing"
        assert (fe_src / "views" / "AuthorizationDecisionView.tsx").exists(), "AuthorizationDecisionView is missing"
        assert (fe_src / "views" / "AskMedRuleView.tsx").exists(), "AskMedRuleView is missing"

    def test_frontend_production_build_verified(self):
        fe_dist = ROOT_DIR / "frontend" / "dist" / "index.html"
        assert fe_dist.exists(), "Frontend build bundle (dist/index.html) is missing. Run 'npm run build' in frontend."
