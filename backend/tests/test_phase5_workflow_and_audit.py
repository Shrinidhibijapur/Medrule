import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app, note_extractor_service, registry_service, criteria_service
from app.models.note import ClinicalNoteRecord, ExtractedFact, ClinicalFactStatus
from app.models.policy import Policy, PolicyLifecycleStatus, PolicySection
from app.models.criteria import PolicyRuleset, CriterionRule, CriterionType, VerificationStatus, ReviewerSignoff
from app.models.evaluation import Verdict, DecisionOutcome

client = TestClient(app)

@pytest.fixture
def phase5_test_case_and_policy(tmp_path):
    """Sets up an approved policy and verified ruleset with a clinical note case for Phase 5 tests."""
    policy_id = "P-PHASE5-UHC"
    checksum = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"

    policy = Policy(
        id=policy_id,
        insurer="United Healthcare",
        policy_name="Computed Tomography Head Phase 5 Test",
        version="2026.1",
        effective_date="2026-01-01",
        procedure_type="CT",
        procedure_full_name="CT Head Scan",
        cpt_codes=["70450", "70460"],
        plan="Commercial",
        lifecycle_status=PolicyLifecycleStatus.APPROVED_FOR_USE,
        approved_by="Dr. Sarah Jenkins",
        sha256_checksum=checksum,
        sections=[
            PolicySection(
                id="sec_1",
                section_number="4.1",
                heading="Acute Symptoms",
                page_number=1,
                content="Documented acute neurological symptoms.",
                character_count=40
            )
        ]
    )
    registry_service._policies_cache[policy_id] = policy

    ruleset = PolicyRuleset(
        policy_id=policy_id,
        policy_name=policy.policy_name,
        policy_version="2026.1",
        policy_checksum=checksum,
        procedure_type="CT Scan",
        verification_status=VerificationStatus.APPROVED_VERIFIED,
        signoff=ReviewerSignoff(
            primary_reviewer="Dr. Sarah Jenkins, MD",
            primary_reviewer_role="Medical Director",
            secondary_reviewer="Marcus Vance, RN",
            secondary_reviewer_role="Auditor",
            signed_off_at="2026-01-01T00:00:00Z",
            policy_checksum=checksum,
            source_criteria_count=1,
            encoded_criteria_count=1,
            side_by_side_verified=True,
            plain_english_verified=True
        ),
        rules=[
            CriterionRule(
                id="P5-CRIT-01",
                policy_id=policy_id,
                policy_version="2026.1",
                section_number="4.1",
                section_name="Acute Symptoms",
                criterion_type=CriterionType.CRITERION,
                source_page=1,
                source_text="Documented acute neurological symptoms.",
                fact_key="acute_neuro_symptoms",
                is_mandatory=True,
                verification_status=VerificationStatus.APPROVED_VERIFIED,
                plain_english_description="Acute symptoms mandatory"
            )
        ]
    )
    criteria_service.save_ruleset(ruleset)

    case_id = "CASE-PHASE5-001"
    note_record = ClinicalNoteRecord(
        case_id=case_id,
        patient_name="Eleanor Vance",
        patient_age=48,
        gender="F",
        facility="Riverside Regional Medical Center",
        date_of_visit="2026-10-15",
        procedure_requested="CT Scan of Head with Contrast",
        insurance_plan="United Healthcare",
        policy_id=policy_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        facts={
            "acute_neuro_symptoms": ExtractedFact(
                fact_key="acute_neuro_symptoms",
                label="Acute Neurological Symptoms",
                value=False,
                status=ClinicalFactStatus.EXPLICIT,
                excerpt="Patient denies acute neurological deficits.",
                source_page=1,
                confidence=0.95
            )
        }
    )
    note_extractor_service.save_note_record(note_record)
    return case_id, policy_id


def test_phase5_dashboard_stats_endpoint_matches_cases(phase5_test_case_and_policy):
    """Requirement 6: Dashboard stats derive dynamically from real backend cases."""
    case_id, policy_id = phase5_test_case_and_policy

    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()

    assert "total_reviews" in data
    assert "approved_count" in data
    assert "not_approved_count" in data
    assert "pending_count" in data
    assert "recent_reviews" in data
    assert data["is_synthetic_demo"] is True

    # Total reviews must match note_extractor_service cases count
    cases = note_extractor_service.list_note_records()
    assert data["total_reviews"] == len(cases)

    # Eleanor Vance must be present in recent reviews
    recent_names = [r["patient_name"] for r in data["recent_reviews"]]
    assert "Eleanor Vance" in recent_names


def test_phase5_case_export_text_and_json(phase5_test_case_and_policy):
    """Requirement 4: Downloadable audit report export in TXT and JSON formats."""
    case_id, policy_id = phase5_test_case_and_policy

    # Evaluate case first
    eval_res = client.post(f"/api/cases/{case_id}/evaluate")
    assert eval_res.status_code == 200

    # 1. Text export
    res_txt = client.get(f"/api/cases/{case_id}/export?format=txt")
    assert res_txt.status_code == 200
    assert "text/plain" in res_txt.headers["content-type"]
    assert f"attachment; filename=\"MedRule_Audit_{case_id}.txt\"" in res_txt.headers["content-disposition"]
    text_content = res_txt.text

    assert "MEDRULE PRIOR AUTHORIZATION AUDIT PACKAGE" in text_content
    assert "[DEMO / SYNTHETIC CASE - NOT A CLINICAL DECISION]" in text_content
    assert f"Case Identifier        : {case_id}" in text_content
    assert "Patient Name           : Eleanor Vance" in text_content
    assert "Policy PDF Checksum" in text_content
    assert "P5-CRIT-01" in text_content
    assert "DEVELOPMENT / DEMO MODE ONLY: Synthetic Clinical Records" in text_content

    # 2. JSON export
    res_json = client.get(f"/api/cases/{case_id}/export?format=json")
    assert res_json.status_code == 200
    data = res_json.json()

    assert data["export_type"] == "MEDRULE_AUDIT_PACKAGE"
    assert data["is_synthetic_demo"] is True
    assert data["case_id"] == case_id
    assert data["patient_name"] == "Eleanor Vance"
    assert data["evaluation"]["verdict"] == "NOT_APPROVED"
    assert "acute_neuro_symptoms" in data["clinical_facts"]
    assert "DEVELOPMENT/DEMO MODE ONLY" in data["governance_notice"]


def test_phase5_export_invalid_case_id_returns_404():
    """Requirement 4: Handle non-existent cases gracefully with 404."""
    res = client.get("/api/cases/NON_EXISTENT_CASE_9999/export")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_phase5_human_in_the_loop_override_and_automatic_reevaluation(phase5_test_case_and_policy):
    """
    Requirement 5: Reviewer correction records identity, justification,
    and automatically triggers reevaluation of the policy decision.
    """
    case_id, policy_id = phase5_test_case_and_policy

    # Initially value is False -> NOT_APPROVED
    eval_initial = client.post(f"/api/cases/{case_id}/evaluate")
    assert eval_initial.json()["verdict"] == "NOT_APPROVED"

    # Reviewer corrects the fact to True with audit justification
    correction_payload = {
        "fact_key": "acute_neuro_symptoms",
        "corrected_value": True,
        "corrected_status": "EXPLICIT",
        "reviewer_name": "Dr. Sarah Jenkins, MD",
        "reason": "Neurology consult note on page 2 documents sudden right-sided hemiparesis."
    }

    patch_res = client.patch(
        f"/api/notes/{case_id}/facts/acute_neuro_symptoms",
        json=correction_payload
    )
    assert patch_res.status_code == 200
    updated_record = patch_res.json()

    # Verify audit trail and override stored
    fact = updated_record["facts"]["acute_neuro_symptoms"]
    assert fact["value"] is True
    assert fact["reviewer_override"]["is_overridden"] is True
    assert fact["reviewer_override"]["overridden_by"] == "Dr. Sarah Jenkins, MD"
    assert "hemiparesis" in fact["reviewer_override"]["reason"]

    # Verify audit trail entry appended
    audit_actions = [ev["action"] for ev in updated_record["audit_trail"]]
    assert "FACT_OVERRIDE" in audit_actions

    # Verify automatic reevaluation occurred and outcome promoted to APPROVED
    assert updated_record["latest_outcome"] == "APPROVED"
    assert updated_record["latest_evaluation"]["verdict"] == "APPROVED"


def test_phase5_end_to_end_synthetic_workflow(phase5_test_case_and_policy):
    """
    Requirement 1 & 9: Complete end-to-end synthetic workflow
    Upload/load note -> Inspect facts -> Apply Clinician Correction -> Reevaluate -> Export Audit Report.
    """
    case_id, policy_id = phase5_test_case_and_policy

    # 1. Fetch case record (simulating UI navigation to extracted_doc / extracted_info)
    case_res = client.get(f"/api/cases/{case_id}")
    assert case_res.status_code == 200
    record = case_res.json()
    assert record["patient_name"] == "Eleanor Vance"

    # 2. Fact review & correction (simulating Human-in-the-Loop review)
    correct_res = client.patch(
        f"/api/notes/{case_id}/facts/acute_neuro_symptoms",
        json={
            "fact_key": "acute_neuro_symptoms",
            "corrected_value": True,
            "corrected_status": "EXPLICIT",
            "reviewer_name": "Dr. Marcus Vance, MD",
            "reason": "Verified clinical examination records confirming acute symptoms."
        }
    )
    assert correct_res.status_code == 200

    # 3. Deterministic Evaluation (simulating Criteria Evaluation view)
    eval_res = client.post(f"/api/cases/{case_id}/evaluate")
    assert eval_res.status_code == 200
    report = eval_res.json()

    assert report["verdict"] == "APPROVED"
    assert report["is_synthetic_demo"] is True
    assert report["verdict_sentence"].startswith("[DEMO / SYNTHETIC CASE - NOT A CLINICAL DECISION]")

    # 4. Export Audit Report
    export_res = client.get(f"/api/cases/{case_id}/export?format=txt")
    assert export_res.status_code == 200
    assert "APPROVED" in export_res.text
    assert "Dr. Marcus Vance, MD" in export_res.text
