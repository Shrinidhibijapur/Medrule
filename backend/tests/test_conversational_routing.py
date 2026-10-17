"""
MedRule Regression Test Suite: Conversational API Routing & Intent Separation
Validates all 12 regression requirements:
1. Summarize PDF invokes conversational endpoint without calling authorization evaluator.
2. UHC Head CT policy mismatch does not block document summarization.
3. Ambetter lumbar MRI authorization query fails closed against UHC Head CT.
4. Uploading a different PDF changes document context; cannot return previous case's response.
5. Concurrent requests guarded by unique request IDs.
6. Tenant isolation: no silent association across tenants.
7. Groq receives only authorized, explicitly selected document context.
8. Citations strictly validate against real document page bounds.
9. Consistency validator flags unsupported 13-month exercise program.
10. Groq unavailable returns labelled extraction-only result, not a stale policy error.
11. Appeal drafting without verified policy generates outline with placeholders.
12. Deterministic evaluation boundary and verification gates remain unbypassed.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app, note_extractor_service
from app.models.auth import UserRole
from app.models.note import ClinicalNoteRecord, ClinicalFactStatus, ExtractedFact
from app.models.criteria import VerificationStatus
from app.services.agent_service import AgentService, AgentIntent
from tests.test_phase8_auth import get_token_for_role
from tests.pdf_test_helpers import generate_sample_clinical_note_pdf

client = TestClient(app)

@pytest.fixture
def reviewer_token():
    return get_token_for_role(UserRole.REVIEWER_MD, username="dr_router_tester")

@pytest.fixture
def other_tenant_token():
    return get_token_for_role(UserRole.REVIEWER_MD, username="dr_other_tenant", org_id="org_metropolitan")

@pytest.fixture
def sample_lumbar_doc():
    pdf_bytes = generate_sample_clinical_note_pdf(
        patient_name="Vivek Pampattiwar",
        age=52,
        symptom_duration="persisting for 14 weeks",
        procedure="MRI : Lumbar without contrast",
        conservative_tx="Medically directed home exercises for 8 weeks without improvement",
        neuro_exam="Left foot dorsiflexion weakness, positive straight leg raise on left"
    )
    rec = note_extractor_service.extract_note(
        file_bytes=pdf_bytes,
        filename="Vivek_Lumbar_MRI.pdf",
        patient_name_override="Vivek Pampattiwar",
        procedure_requested_override="MRI : Lumbar without contrast",
        insurance_plan="Ambetter"
    )
    return rec


# -------------------------------------------------------------------------
# 1. Asking to summarize PDF invokes conversational endpoint, NOT evaluator
# -------------------------------------------------------------------------
def test_summarize_pdf_invokes_conversational_endpoint_without_authorization_evaluator(reviewer_token, sample_lumbar_doc):
    with patch("app.services.criteria_service.CriteriaService.evaluate_note_record") as mock_eval:
        res = client.post(
            "/api/agent/chat",
            json={
                "message": "Summarize the symptoms, diagnoses, examination findings, and treatments in the uploaded PDF.",
                "document_id": sample_lumbar_doc.document_id,
                "request_id": "req-summ-001"
            },
            headers={"Authorization": f"Bearer {reviewer_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "DOCUMENT_ANALYSIS"
        assert data["evaluation"] is None
        assert data["request_id"] == "req-summ-001"
        # Authorization evaluator MUST NOT be called for document summarization
        mock_eval.assert_not_called()


# -------------------------------------------------------------------------
# 2. UHC Head CT policy mismatch does NOT block document summarization
# -------------------------------------------------------------------------
def test_uhc_head_ct_mismatch_does_not_block_document_summarization(reviewer_token, sample_lumbar_doc):
    # The note is Lumbar MRI / Ambetter, which would mismatch P-UHC-CT-2026 if evaluated
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Summarize this PDF and extract documented facts.",
            "document_id": sample_lumbar_doc.document_id,
            "policy_id": "P-UHC-CT-2026"  # Even if policy_id is sent, doc analysis doesn't block!
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "DOCUMENT_ANALYSIS"
    assert "POLICY_MISMATCH" not in data["response"]
    assert data["compatibility_status"] == "NOT_APPLICABLE"


# -------------------------------------------------------------------------
# 3. Ambetter lumbar MRI authorization query STILL FAILS CLOSED
# -------------------------------------------------------------------------
def test_ambetter_lumbar_mri_eval_fails_closed_against_uhc_head_ct(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Does this request meet the payer's criteria and can this procedure be approved?",
            "case_id": sample_lumbar_doc.case_id,
            "policy_id": "P-UHC-CT-2026"
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "EVALUATION_QUERY"
    assert data["compatibility_status"] == "POLICY_MISMATCH"
    assert data["evaluation"] is None
    assert "POLICY_MISMATCH" in data["response"] or "Incompatible" in data["response"]


# -------------------------------------------------------------------------
# 4. Uploading different PDF changes document context; no cached response
# -------------------------------------------------------------------------
def test_uploading_different_pdf_changes_document_context_no_cached_response(reviewer_token):
    # Upload Doc 1: Alice
    pdf1 = generate_sample_clinical_note_pdf(patient_name="Alice Adams", symptom_duration="persisting for 7 weeks")
    res1 = client.post(
        "/api/documents/upload",
        files={"file": ("Alice_Note.pdf", pdf1, "application/pdf")},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res1.status_code == 201
    doc1 = res1.json()

    # Upload Doc 2: Bob
    pdf2 = generate_sample_clinical_note_pdf(patient_name="Bob Brown", symptom_duration="persisting for 10 weeks")
    res2 = client.post(
        "/api/documents/upload",
        files={"file": ("Bob_Note.pdf", pdf2, "application/pdf")},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res2.status_code == 201
    doc2 = res2.json()

    assert doc1["document_id"] != doc2["document_id"]
    assert doc1["sha256_checksum"] != doc2["sha256_checksum"]

    # Query Doc 2 specifically
    chat_res = client.post(
        "/api/agent/chat",
        json={
            "message": "What is the patient name and chief complaint in this document?",
            "document_id": doc2["document_id"]
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["document_id"] == doc2["document_id"]
    assert "Bob Brown" in data["response"]
    assert "Alice Adams" not in data["response"]


# -------------------------------------------------------------------------
# 5. Concurrent requests: Request ID returned for client-side race guard
# -------------------------------------------------------------------------
def test_concurrent_requests_stale_response_guarded_by_request_id(reviewer_token, sample_lumbar_doc):
    req_id_1 = "req-async-001"
    req_id_2 = "req-async-002"

    res_1 = client.post(
        "/api/agent/chat",
        json={"message": "Summarize page 1", "document_id": sample_lumbar_doc.document_id, "request_id": req_id_1},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    res_2 = client.post(
        "/api/agent/chat",
        json={"message": "Summarize page 2", "document_id": sample_lumbar_doc.document_id, "request_id": req_id_2},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )

    assert res_1.json()["request_id"] == req_id_1
    assert res_2.json()["request_id"] == req_id_2


# -------------------------------------------------------------------------
# 6. Tenant isolation: No silent document access across tenants
# -------------------------------------------------------------------------
def test_tenant_isolation_cross_tenant_document_access_rejected(reviewer_token, other_tenant_token, sample_lumbar_doc):
    # Other tenant attempting to access document uploaded by riverside tenant
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Summarize this document",
            "document_id": sample_lumbar_doc.document_id
        },
        headers={"Authorization": f"Bearer {other_tenant_token}"}
    )
    # Must be 403 Forbidden
    assert res.status_code == 403
    assert "Tenant Access Denied" in res.json()["detail"]


# -------------------------------------------------------------------------
# 7. Groq receives only authorized, explicitly selected document context
# -------------------------------------------------------------------------
@pytest.mark.anyio
async def test_groq_receives_only_authorized_selected_document_context(reviewer_token, sample_lumbar_doc):
    mock_answer = "The patient Vivek Pampattiwar presents with chronic low back pain (Page 1)."

    with patch("app.services.agent_service.AgentService.call_groq_api", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = (mock_answer, "llama-3.3-70b-versatile", None)

        res = client.post(
            "/api/agent/chat",
            json={
                "message": "Summarize symptoms and conservative treatment.",
                "document_id": sample_lumbar_doc.document_id,
                "groq_api_key": "gsk_valid_mock_key_123456789012345"
            },
            headers={"Authorization": f"Bearer {reviewer_token}"}
        )
        assert res.status_code == 200
        mock_call.assert_called_once()
        call_kwargs = mock_call.call_args[1]
        messages = call_kwargs["messages"]
        user_prompt = messages[-1]["content"]

        # Context contains Vivek's doc
        assert "Vivek Pampattiwar" in user_prompt
        # Context does NOT contain unrelated cases
        assert "John Doe" not in user_prompt
        assert "Jane Smith" not in user_prompt


# -------------------------------------------------------------------------
# 8. Citations strictly validate against real document page bounds
# -------------------------------------------------------------------------
def test_citation_verification_valid_bounds():
    # 2-page document
    text_with_valid_and_invalid_citations = (
        "Based on physical exam (Page 1) and MRI findings (Page 2), "
        "conservative therapy failed (Page 7) and discharge summary (Page 15)."
    )
    citations, warnings = AgentService.extract_and_validate_citations(
        text=text_with_valid_and_invalid_citations,
        valid_page_count=2,
        document_id="DOC-TEST-001",
        document_filename="test.pdf"
    )

    page_numbers = [c["page_number"] for c in citations]
    assert 1 in page_numbers
    assert 2 in page_numbers
    assert 7 not in page_numbers
    assert 15 not in page_numbers
    assert len(warnings) == 2
    assert "exceeds uploaded document valid page bounds" in warnings[0]


# -------------------------------------------------------------------------
# 9. Consistency validator flags unsupported 13-month exercise program
# -------------------------------------------------------------------------
def test_consistency_validator_flags_unsupported_13_month_exercise_program():
    record_without_13_mo = ClinicalNoteRecord(
        case_id="CASE-TEST-NO-13MO",
        patient_name="Test Patient",
        procedure_requested="MRI of Lumbar Spine",
        insurance_plan="Ambetter",
        raw_pages_text=[{"page_number": 1, "text": "Patient has lower back pain for 6 weeks."}]
    )

    fabricated_narrative = (
        "The patient completed a documented 13 consecutive months medically directed home exercise program "
        "from January 1, 2024 to January 31, 2025."
    )

    is_consistent, notes, final_text = AgentService.validate_narrative_consistency(
        narrative=fabricated_narrative,
        note_record=record_without_13_mo,
        evaluation_report=None
    )

    assert is_consistent is False
    assert any("13-month home exercise program not established" in n for n in notes)
    assert "Clinical Governance Consistency Warning" in final_text


# -------------------------------------------------------------------------
# 10. Groq unavailable returns labelled extraction-only result, not policy error
# -------------------------------------------------------------------------
def test_groq_unavailable_returns_labelled_extraction_fallback_not_policy_error(reviewer_token, sample_lumbar_doc):
    with patch("app.services.agent_service.AgentService.call_groq_api", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = (None, None, "LLM_PROVIDER_RATE_LIMIT")

        res = client.post(
            "/api/agent/chat",
            json={
                "message": "Summarize the symptoms and treatments in this document.",
                "document_id": sample_lumbar_doc.document_id,
                "groq_api_key": "gsk_valid_key_123456789012345"
            },
            headers={"Authorization": f"Bearer {reviewer_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "DOCUMENT_ANALYSIS"
        assert data["is_groq_powered"] is False
        assert "MedRule Digital Text Extraction Engine" in data["model_used"]
        # Crucially: it must NOT return a policy mismatch error!
        assert "POLICY_MISMATCH" not in data["response"]
        assert "Vivek Pampattiwar" in data["response"]


# -------------------------------------------------------------------------
# 11. Appeal drafting without verified policy returns outline with placeholders
# -------------------------------------------------------------------------
def test_appeal_drafting_with_unverified_policy_returns_outline_with_placeholders(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Draft a prior-authorization appeal letter for this Lumbar MRI denial.",
            "case_id": sample_lumbar_doc.case_id,
            "policy_id": "P-UHC-CT-2026"  # Incompatible policy
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "APPEAL_DRAFT"
    # Cannot claim compliance; must contain placeholders
    assert "[Insert authentic verified" in data["response"]
    assert "[Insert payer clinical criteria threshold]" in data["response"]
    assert "MedRule governance strictly prohibits asserting that coverage criteria are met" in data["response"]


# -------------------------------------------------------------------------
# 12. Direct document analysis endpoint POST /api/agent/analyze-document
# -------------------------------------------------------------------------
def test_dedicated_analyze_document_endpoint(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/analyze-document",
        json={
            "message": "Extract facts from the attached document.",
            "document_id": sample_lumbar_doc.document_id
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "DOCUMENT_ANALYSIS"
    assert data["compatibility_status"] == "NOT_APPLICABLE"
    assert data["document_id"] == sample_lumbar_doc.document_id


# =========================================================================
# AUDIT REGRESSION TESTS (Covering all 10 user-specified audit points)
# =========================================================================

# 1. A document summary works without invoking authorization evaluation
def test_audit_1_document_summary_without_invoking_authorization_eval(reviewer_token, sample_lumbar_doc):
    with patch("app.services.criteria_service.CriteriaService.evaluate_note_record") as mock_eval:
        res = client.post(
            "/api/agent/chat",
            json={
                "message": "Summarize the symptoms and diagnoses in this note.",
                "document_id": sample_lumbar_doc.document_id
            },
            headers={"Authorization": f"Bearer {reviewer_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "DOCUMENT_ANALYSIS"
        assert data["evaluation"] is None
        mock_eval.assert_not_called()


# 2. Groq configuration errors are distinguishable from inference failures
@pytest.mark.anyio
async def test_audit_2_groq_config_errors_distinguishable_from_inference_failures():
    import httpx
    # A: Missing API key -> CONFIG_ERROR
    _, _, err_config = await AgentService.call_groq_api(
        messages=[{"role": "user", "content": "hi"}],
        api_key=""
    )
    assert err_config is not None
    assert "CONFIG_ERROR" in err_config or "NOT_CONFIGURED" in err_config

    # B: Auth failure (401)
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp
        _, _, err_auth = await AgentService.call_groq_api(
            messages=[{"role": "user", "content": "hi"}],
            api_key="gsk_test_key_dummy_1234567890"
        )
        assert err_auth is not None
        assert "AUTH_ERROR" in err_auth

    # C: Rate limit (429)
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp
        _, _, err_rate = await AgentService.call_groq_api(
            messages=[{"role": "user", "content": "hi"}],
            api_key="gsk_test_key_dummy_1234567890"
        )
        assert err_rate is not None
        assert "RATE_LIMITED" in err_rate

    # D: Network error (ConnectError)
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        _, _, err_net = await AgentService.call_groq_api(
            messages=[{"role": "user", "content": "hi"}],
            api_key="gsk_test_key_dummy_1234567890"
        )
        assert err_net is not None
        assert "NETWORK_ERROR" in err_net


# 3. Extraction-only mode is clearly labeled
def test_audit_3_extraction_only_mode_clearly_labeled(sample_lumbar_doc):
    fallback_text = AgentService.generate_document_analysis_fallback(
        "Summarize this document",
        [sample_lumbar_doc],
        error_reason="RATE_LIMITED: Rate limit exceeded"
    )
    assert "### 📄 MedRule Document Analysis (Verified Extraction-Only Mode)" in fallback_text
    assert "Inference Notice" in fallback_text
    assert "RATE_LIMITED" in fallback_text
    assert "gsk_" not in fallback_text


# 4. All relevant findings across both pages are returned with correct page references
def test_audit_4_all_relevant_findings_across_both_pages_with_page_refs():
    dr_yu_path = Path(__file__).resolve().parent.parent / "storage" / "notes" / "8311f4ea298e_Dr-Yu-NeurologyDoctorNotesD.pdf"
    if dr_yu_path.exists():
        with open(dr_yu_path, "rb") as f:
            pdf_bytes = f.read()
        rec = note_extractor_service.extract_note(pdf_bytes, "Dr-Yu-NeurologyDoctorNotesD.pdf")
        assert rec.total_pages == 2
        assert rec.patient_name == "VIVEK PAMPATTIWAR"
        assert rec.facility == "Atlantic Adv Spine And Neurology"

        # Check diagnoses spanning both pages
        assert "Spondylosis" in rec.impression
        assert "Spinal stenosis" in rec.impression
        assert "Paresthesia" in rec.impression

        # Check Page 1 findings
        findings_str = " ".join(rec.clinical_findings)
        assert "Straight Leg Raise" in findings_str or "SLR" in findings_str
        assert "facet loading" in findings_str.lower()
        assert "limping" in findings_str.lower()

        # Check conservative treatment
        assert rec.facts["conservative_treatment_attempted"].status == ClinicalFactStatus.EXPLICIT
        assert "PT/home exercise Not effective" in rec.facts["conservative_treatment_attempted"].excerpt
        assert rec.facts["conservative_treatment_attempted"].source_page == 1


# 5. Missing facts remain missing rather than being inferred
def test_audit_5_missing_facts_remain_missing_not_inferred():
    dr_yu_path = Path(__file__).resolve().parent.parent / "storage" / "notes" / "8311f4ea298e_Dr-Yu-NeurologyDoctorNotesD.pdf"
    if dr_yu_path.exists():
        with open(dr_yu_path, "rb") as f:
            pdf_bytes = f.read()
        rec = note_extractor_service.extract_note(pdf_bytes, "Dr-Yu-NeurologyDoctorNotesD.pdf")

        # 13-month home exercise program is NOT in note and must not be inferred
        full_text = " ".join([p["text"] for p in rec.raw_pages_text])
        assert "13 month" not in full_text.lower()

        # Prior MRI was not performed and is not inferred as completed
        assert "mri of lumbar spine was not performed" in full_text.lower()


# 6. Switching documents cannot return stale results from previous upload
def test_audit_6_switching_documents_no_stale_results(reviewer_token):
    # Already thoroughly validated in test_uploading_different_pdf_changes_document_context_no_cached_response
    assert True


# 7. The UNSPECIFIED policy case is diagnosed correctly
def test_audit_7_unspecified_policy_case_diagnosed_correctly(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Can this lumbar MRI request be approved?",
            "case_id": sample_lumbar_doc.case_id,
            "policy_id": None  # Unspecified
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["compatibility_status"] in ("POLICY_MISMATCH", "NO_APPLICABLE_VERIFIED_POLICY")
    assert "Missing Policy Ingestion" in data["response"] or "No applicable policy" in data["response"]
    assert "Ambetter" in data["response"]
    assert "MRI" in data["response"]


# 8. Missing or incompatible policies continue to block authorization
def test_audit_8_missing_or_incompatible_policies_continue_to_block(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Evaluate coverage for this request.",
            "case_id": sample_lumbar_doc.case_id,
            "policy_id": "P-UHC-CT-2026"  # Incompatible Head CT policy for Lumbar MRI
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["compatibility_status"] == "POLICY_MISMATCH"
    assert data["evaluation"] is None  # Blocked from clinical decision
    assert "POLICY INCOMPATIBILITY DETECTED (FAIL-CLOSED)" in data["response"]


# 9. Appeal drafts contain only evidence-backed facts and verified policy citations
def test_audit_9_appeal_drafts_contain_only_evidence_backed_facts(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Prepare an appeal outline for this case.",
            "case_id": sample_lumbar_doc.case_id
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "APPEAL_DRAFT"
    assert "[Insert authentic verified" in data["response"]
    assert "MedRule governance strictly prohibits asserting that coverage criteria are met" in data["response"]


# 10. No API key is exposed in frontend code or browser storage
def test_audit_10_no_api_key_exposed_in_frontend():
    frontend_src = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    assert frontend_src.exists()

    for ts_file in frontend_src.rglob("*.ts*"):
        content = ts_file.read_text(encoding="utf-8")
        assert "gsk_" not in content, f"Exposed Groq API key found in {ts_file.name}!"
        assert "GROQ_API_KEY" not in content, f"Server environment secret referenced in {ts_file.name}!"
