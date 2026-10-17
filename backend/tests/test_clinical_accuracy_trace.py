import io
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app, criteria_service, registry_service, note_extractor_service
from app.core.deps import get_current_user
from app.models.auth import UserRole, AuthenticatedUser, Permission, ROLE_PERMISSIONS
from app.models.policy import Policy, PolicyLifecycleStatus
from app.models.note import ClinicalNoteRecord, ClinicalFactStatus, FactCorrectionRequest
from app.models.evaluation import CriterionStatus, DecisionOutcome
from app.services.criteria_service import PolicyMismatchError, PolicyVerificationGateError
from app.services.agent_service import AgentService
from tests.test_phase8_auth import get_token_for_role

client = TestClient(app)

@pytest.fixture
def reviewer_token():
    return get_token_for_role(UserRole.REVIEWER_MD, username="dr_trace_tester")

@pytest.fixture
def synthetic_lumbar_mri_note():
    """Synthetic clinical note record representing an Ambetter Lumbar Spine MRI order."""
    extractor = note_extractor_service
    # 2 pages of synthetic notes
    p1 = (
        "Patient: Test Patient DOB: 01/01/1970\n"
        "DOS: 04/09/2026\n"
        "Insurance: Ambetter\n"
        "Order: MRI of Lumbar Spine without Contrast\n"
        "Chief Complaint: Low back pain rated 7/10 with radiculopathy into right lower extremity.\n"
        "Physical Exam: Gait disturbance noted. Straight leg raise positive on right.\n"
        "Plan: Prescribe lumbar brace L0650 and setup TF ESI injection. Discussed home exercises."
    )
    p2 = (
        "Atlantic Advanced Spine\n"
        "Review of past imaging studies: Degenerative disc disease L4-L5.\n"
        "Medications: Magnesium Citrate 200mg daily.\n"
        "Signed electronically by Dr. Test Clinician, MD."
    )
    record = ClinicalNoteRecord(
        case_id="CASE-SYNTHETIC-AMBETTER-MRI-001",
        patient_name="Synthetic Patient A",
        patient_age=55,
        gender="M",
        dob="01/01/1970",
        facility="Riverside Spine Clinic",
        date_of_visit="04/09/2026",
        procedure_requested="MRI of Lumbar Spine without Contrast",
        procedure_type="Advanced Imaging",
        insurance_plan="Ambetter",
        policy_id="P-UHC-CT-2026", # Incompatible UHC CT policy
        policy_version="2026.1",
        organization_id="org_riverside",
        chief_complaint="Low back pain and radiculopathy",
        original_filename="synthetic_lumbar_note.pdf",
        storage_path="storage/notes/synthetic_lumbar_note.pdf",
        sha256_checksum="abc123def4567890syntheticchecksum",
        total_pages=2,
        scanned_pages_count=0,
        overall_quality="HIGH",
        ocr_engine_status="Native Digital",
        facts=extractor._extract_clinical_facts([(1, p1), (2, p2)], "P-UHC-CT-2026"),
        raw_pages_text=[{"page_number": 1, "text": p1}, {"page_number": 2, "text": p2}],
        is_synthetic=True,
        created_at="2026-04-09T10:00:00Z",
        updated_at="2026-04-09T10:00:00Z"
    )
    extractor.save_note_record(record)
    return record


# 1. Ambetter lumbar MRI with only a UHC head CT policy available -> POLICY_MISMATCH
def test_ambetter_lumbar_mri_fails_closed_against_uhc_ct_policy(synthetic_lumbar_mri_note, reviewer_token):
    uhc_policy = registry_service.get_by_id("P-UHC-CT-2026")
    assert uhc_policy is not None

    # Direct compatibility check detects mismatch
    is_compat, status, reasons, req_policy = criteria_service.validate_policy_compatibility(uhc_policy, synthetic_lumbar_mri_note)
    assert is_compat is False
    assert status == "POLICY_MISMATCH"
    assert any("Payer Mismatch" in r or "Modality Mismatch" in r for r in reasons)

    # Deterministic criteria evaluation raises PolicyMismatchError
    with pytest.raises(PolicyMismatchError) as exc_info:
        criteria_service.evaluate_note_record(policy=uhc_policy, note_record=synthetic_lumbar_mri_note)
    assert "POLICY_MISMATCH" in str(exc_info.value)

    # API Evaluation endpoint returns 422
    res = client.post(
        f"/api/cases/{synthetic_lumbar_mri_note.case_id}/evaluate",
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 422
    assert "mismatch" in res.json()["detail"].lower()

    # Agent Chat refuses to evaluate under wrong rulebook and returns POLICY_MISMATCH trace
    chat_res = client.post(
        "/api/agent/chat",
        json={"message": "Can this Ambetter lumbar MRI be approved?", "case_id": synthetic_lumbar_mri_note.case_id},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["compatibility_status"] == "POLICY_MISMATCH"
    assert "POLICY INCOMPATIBILITY DETECTED" in chat_data["response"]
    assert chat_data["evaluation"] is None
    assert chat_data["trace"]["compatibility_status"] == "POLICY_MISMATCH"


# 2. A two-page PDF -> no generated citation to page 3 or higher
def test_two_page_document_no_citation_to_page_3_or_higher(synthetic_lumbar_mri_note):
    assert synthetic_lumbar_mri_note.total_pages == 2

    # Narrative with out-of-bounds citations must be caught by consistency validator
    bad_narrative = "The physician recommended lumbar support on page 3 and physical therapy on page 4."
    passed, notes, validated = AgentService.validate_narrative_consistency(
        narrative=bad_narrative,
        note_record=synthetic_lumbar_mri_note,
        evaluation_report=None
    )
    assert passed is False
    assert any("exceeds the uploaded document's valid page range" in n for n in notes)
    assert "Clinical Governance Consistency Warning" in validated

    # Extracted facts must clamp any page outside bounds
    for k, f in synthetic_lumbar_mri_note.facts.items():
        if f.source_page is not None:
            assert 1 <= f.source_page <= synthetic_lumbar_mri_note.total_pages


# 3. Source note lacks a home exercise duration -> no generated claim of a 13-month exercise program
def test_no_claim_of_13_month_home_exercise_program(synthetic_lumbar_mri_note):
    fabricated_narrative = (
        "The patient completed a physician-directed home exercise program lasting from January 1, 2024, "
        "through January 31, 2025 (13 consecutive months)."
    )
    passed, notes, validated = AgentService.validate_narrative_consistency(
        narrative=fabricated_narrative,
        note_record=synthetic_lumbar_mri_note,
        evaluation_report=None
    )
    assert passed is False
    assert any("13-month home exercise program" in n for n in notes)


# 4. Source note mentions a treatment plan but not completion -> no claim that treatment was completed
def test_treatment_plan_not_claimed_as_completed():
    text = "Treatment Plan: Patient requests to proceed with TF ESI. Plan to start physical therapy next week."
    fact = note_extractor_service._extract_fact_conservative_treatment_attempted([(1, text)])
    assert fact.status == ClinicalFactStatus.ABSENT
    assert fact.value is None or fact.value is False


# 5. A fact is ABSENT -> narrative must not present it as explicitly present
def test_absent_fact_not_presented_as_present(synthetic_lumbar_mri_note):
    synthetic_lumbar_mri_note.facts["conservative_treatment_attempted"].status = ClinicalFactStatus.ABSENT
    synthetic_lumbar_mri_note.facts["conservative_treatment_attempted"].value = None

    narrative_asserting_present = "The patient successfully completed conservative treatment as documented."
    passed, notes, _ = AgentService.validate_narrative_consistency(
        narrative=narrative_asserting_present,
        note_record=synthetic_lumbar_mri_note,
        evaluation_report=None
    )
    assert passed is False
    assert any("conservative treatment was completed, but extracted fact status is ABSENT" in n for n in notes)


# 6. Allergy history undocumented -> must not become "patient has no allergy"
def test_undocumented_allergy_is_not_patient_has_no_allergy():
    text_no_allergy = "Patient presents with headache. Physical examination is normal."
    fact = note_extractor_service._extract_fact_contrast_anaphylaxis_unmitigated([(1, text_no_allergy)])
    assert fact.status == ClinicalFactStatus.ABSENT
    assert fact.value is None


# 7. Note, extracted facts, evaluation and response use identical identifiers
def test_identical_identifiers_across_pipeline(reviewer_token):
    res = client.get("/api/agent/trace/CASE-2026-001", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res.status_code == 200
    trace = res.json()
    assert trace["case_id"] == "CASE-2026-001"
    assert trace["document_id"] == "CASE-2026-001"
    assert trace["document_sha256"] != ""
    assert trace["valid_page_count"] >= 1
    for f in trace["extracted_facts"]:
        assert f["source_document_id"] == "CASE-2026-001"
        if f["source_page"]:
            assert f["source_page"] <= trace["valid_page_count"]
    # Verify narrative validation status is NOT_APPLICABLE when LLM was not invoked
    assert trace["llm_invoked"] is False
    assert trace["narrative_validation_status"] == "NOT_APPLICABLE"
    assert trace["narrative_validation_passed"] is None


# 8. Switching encounters or new note invalidates stale evaluations
def test_switching_encounters_invalidates_stale_data(synthetic_lumbar_mri_note, reviewer_token):
    # Query case A (UHC Head CT)
    res_a = client.post(
        "/api/agent/chat",
        json={"message": "Status of head CT?", "case_id": "CASE-2026-001"},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res_a.status_code == 200
    assert res_a.json()["case_id"] == "CASE-2026-001"

    # Query case B (Ambetter Lumbar MRI)
    res_b = client.post(
        "/api/agent/chat",
        json={"message": "Status of lumbar MRI?", "case_id": synthetic_lumbar_mri_note.case_id},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res_b.status_code == 200
    assert res_b.json()["case_id"] == synthetic_lumbar_mri_note.case_id
    assert res_b.json()["compatibility_status"] == "POLICY_MISMATCH"
    assert res_b.json()["evaluation"] is None


# 9. Missing or unverified policy -> fail closed
def test_unverified_policy_fails_closed(reviewer_token):
    draft_policy = Policy(
        id="POL-DRAFT-001",
        policy_id="POL-DRAFT-001",
        policy_name="Draft Experimental Policy",
        insurer="United Healthcare",
        version="0.1-DRAFT",
        effective_date="2026-01-01",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan of Head with Contrast",
        lifecycle_status=PolicyLifecycleStatus.DRAFT,
        sections=[]
    )
    record = note_extractor_service.get_note_record("CASE-2026-001")
    assert record is not None

    with pytest.raises(PolicyVerificationGateError):
        criteria_service.validate_policy_compatibility(draft_policy, record)


# 10. Deterministic result unchanged when LLM is disabled or returns conflicting text
def test_deterministic_engine_unaltered_by_llm_output(reviewer_token):
    # 1. Deterministic baseline
    eval_res = client.post(
        "/api/cases/CASE-2026-001/evaluate",
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert eval_res.status_code == 200
    det_report = eval_res.json()
    baseline_outcome = det_report["decision_outcome"]

    # 2. Agent chat without Groq key -> fallback uses identical evaluation
    chat_fallback = client.post(
        "/api/agent/chat",
        json={"message": "Can this be approved?", "case_id": "CASE-2026-001"},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert chat_fallback.status_code == 200
    fb_data = chat_fallback.json()
    assert fb_data["evaluation"]["decision_outcome"] == baseline_outcome

    # 3. Agent chat with mocked contradictory Groq response (claims 13-month home exercise and cites page 9)
    with patch.object(AgentService, "call_groq_api", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = (
            "The patient completed a 13-month home exercise program documented on page 9.",
            "llama-3.3-70b-versatile",
            None
        )
        chat_llm = client.post(
            "/api/agent/chat",
            json={
                "message": "Can this be approved?",
                "case_id": "CASE-2026-001",
                "groq_api_key": "gsk_synthetic_key_1234567890123456"
            },
            headers={"Authorization": f"Bearer {reviewer_token}"}
        )
        assert chat_llm.status_code == 200
        llm_data = chat_llm.json()
        assert llm_data["evaluation"]["decision_outcome"] == baseline_outcome
        # Contradiction is caught and flagged with warning in response
        assert "Clinical Governance Consistency Warning" in llm_data["response"]
        assert "sole authoritative record" in llm_data["response"]


# 11. Groq activation/API-key instructions no longer appear in clinical workspace
def test_no_groq_promotional_instructions_in_chat(reviewer_token):
    res = client.post(
        "/api/agent/chat",
        json={"message": "What criteria are required?", "case_id": "CASE-2026-001"},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    resp_text = res.json()["response"]
    assert "Activate Groq Fast LLM" not in resp_text
    assert "Enter your Groq API key" not in resp_text
    assert "gsk_" not in resp_text
    assert "console.groq.com" not in resp_text


# 12. Trace accurately links criteria results to rulebook version and evidence sources
def test_trace_links_criteria_to_rulebook_and_evidence(reviewer_token):
    res = client.get("/api/agent/trace/CASE-2026-001", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res.status_code == 200
    trace = res.json()
    assert trace["selected_policy_id"] == "P-UHC-CT-2026"
    assert trace["policy_version"] == "2026.1"
    assert len(trace["criteria_results"]) > 0

    for cr in trace["criteria_results"]:
        assert cr["rule_id"] != ""
        assert cr["policy_citation"] != ""
        assert cr["deterministic_status"] in ["MET", "NOT_MET", "NOT_DOCUMENTED", "NOT_APPLICABLE"]
        if cr["evidence_page"]:
            assert 1 <= cr["evidence_page"] <= trace["valid_page_count"]


# 13. Human corrections are recorded in audit trail and invalidate cached evaluation
def test_human_correction_recorded_in_audit_and_trace(reviewer_token):
    correction_payload = {
        "fact_key": "neurological_symptoms",
        "corrected_status": "EXPLICIT",
        "corrected_value": True,
        "reason": "Clinician confirmed ataxia documented in chart.",
        "reviewer_name": "Dr. Test Reviewer"
    }
    res = client.patch(
        "/api/notes/CASE-2026-001/facts/neurological_symptoms",
        json=correction_payload,
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200

    # Verify trace reflects the human override
    trace_res = client.get("/api/agent/trace/CASE-2026-001", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert trace_res.status_code == 200
    trace = trace_res.json()
    assert len(trace["human_overrides"]) > 0
    assert any(ov["action"] == "FACT_OVERRIDE" for ov in trace["human_overrides"])


# 14. Authentication and tenant isolation remain strictly enforced
def test_auth_and_tenant_isolation_enforced():
    # 1. Unauthenticated request without token/override must fail
    saved_override = app.dependency_overrides.pop(get_current_user, None)
    try:
        res_unauth = client.post("/api/agent/chat", json={"message": "hello"})
        assert res_unauth.status_code in [401, 403]
    finally:
        if saved_override:
            app.dependency_overrides[get_current_user] = saved_override

    # 2. Cross-tenant access blocked: user from org_other cannot access org_riverside case
    other_org_user = AuthenticatedUser(
        user_id="usr_other_tenant",
        username="dr_other_tenant",
        email="dr_other@otherhealth.org",
        full_name="Dr. Other Organization",
        role=UserRole.REVIEWER_MD,
        organization_id="org_other_hospital",
        permissions=set(ROLE_PERMISSIONS[UserRole.REVIEWER_MD])
    )
    app.dependency_overrides[get_current_user] = lambda: other_org_user
    try:
        res_cross = client.post(
            "/api/agent/chat",
            json={"message": "Can this be approved?", "case_id": "CASE-2026-001"}
        )
        assert res_cross.status_code in [403, 404]
    finally:
        if saved_override:
            app.dependency_overrides[get_current_user] = saved_override
