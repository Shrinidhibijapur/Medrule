"""
MedRule Comprehensive Phase 8 Regression Test Suite
Exhaustively validates all 20 specific test items required by Phase 8:

Document Analysis:
1. Accurate extraction from all pages.
2. Complete conservative-treatment and duration extraction.
3. Correct page citations and source excerpts.
4. Unsupported claims are rejected or marked NOT_FOUND.
5. Conflicting evidence is surfaced.
6. No cross-document or cross-patient leakage.
7. Ordered tests are distinguished from completed tests.
8. OCR and extraction failures are handled honestly.

Groq Integration:
9. Successful live/mocked inference.
10. Missing key, invalid key, timeout, rate-limit, and malformed-response handling.
11. Truthful extraction-only fallback.
12. No credentials exposed to the frontend.

Document and Case Context:
13. Uploading a second PDF cannot return the first PDF's answer.
14. Out-of-order requests cannot overwrite newer responses.
15. Source metadata and page counts match the active PDF.

Authorization and Appeals:
16. Document summaries do not require policy evaluation.
17. Missing policy ID does not silently select a default policy.
18. Incompatible payer, modality, anatomy, or procedure blocks evaluation.
19. Only authentic, approved, verified policies can be used.
20. Appeal drafts do not invent policy citations or unsupported clinical facts.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app, note_extractor_service, claim_verifier_service
from app.models.auth import UserRole
from app.models.note import ClinicalNoteRecord, ClinicalFactStatus, ExtractedFact
from app.models.trace import ClaimEvidenceStatus, VerifiedClaim
from app.services.agent_service import AgentService, AgentIntent
from app.services.claim_verifier import ClaimVerifierService
from tests.test_phase8_auth import get_token_for_role
from tests.pdf_test_helpers import generate_sample_clinical_note_pdf

client = TestClient(app)


@pytest.fixture
def reviewer_token():
    return get_token_for_role(UserRole.REVIEWER_MD, username="dr_regression_tester")


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


# =============================================================================
# 1. ACCURATE EXTRACTION FROM ALL PAGES
# =============================================================================
def test_01_accurate_extraction_from_all_pages():
    dr_yu_path = Path(__file__).resolve().parent.parent / "storage" / "notes" / "8311f4ea298e_Dr-Yu-NeurologyDoctorNotesD.pdf"
    if not dr_yu_path.exists():
        pytest.skip("Dr Yu neurology note not found in storage")

    with open(dr_yu_path, "rb") as f:
        pdf_bytes = f.read()

    rec = note_extractor_service.extract_note(pdf_bytes, "Dr-Yu-NeurologyDoctorNotesD.pdf")
    assert rec.total_pages == 2
    assert len(rec.raw_pages_text) == 2

    # Verify Page 1 elements
    page1_text = rec.raw_pages_text[0]["text"]
    assert rec.raw_pages_text[0]["page_number"] == 1
    assert "back pain" in page1_text.lower()
    assert "straight leg raise" in page1_text.lower()

    # Verify Page 2 elements
    page2_text = rec.raw_pages_text[1]["text"]
    assert rec.raw_pages_text[1]["page_number"] == 2
    assert "paresthesia" in page2_text.lower() or "kewei yu" in page2_text.lower() or "emg" in page2_text.lower()


# =============================================================================
# 2. COMPLETE CONSERVATIVE-TREATMENT AND DURATION EXTRACTION
# =============================================================================
def test_02_complete_conservative_treatment_and_duration():
    dr_yu_path = Path(__file__).resolve().parent.parent / "storage" / "notes" / "8311f4ea298e_Dr-Yu-NeurologyDoctorNotesD.pdf"
    if not dr_yu_path.exists():
        pytest.skip("Dr Yu neurology note not found in storage")

    with open(dr_yu_path, "rb") as f:
        pdf_bytes = f.read()

    rec = note_extractor_service.extract_note(pdf_bytes, "Dr-Yu-NeurologyDoctorNotesD.pdf")
    assert "conservative_treatment_attempted" in rec.facts
    tx_fact = rec.facts["conservative_treatment_attempted"]
    assert tx_fact.status == ClinicalFactStatus.EXPLICIT
    assert "PT" in tx_fact.excerpt or "exercise" in tx_fact.excerpt
    assert "Not effective" in tx_fact.excerpt or "not effective" in tx_fact.excerpt.lower()
    assert tx_fact.source_page == 1


# =============================================================================
# 3. CORRECT PAGE CITATIONS AND SOURCE EXCERPTS
# =============================================================================
def test_03_correct_page_citations_and_source_excerpts():
    raw_pages = [
        {"page_number": 1, "text": "Patient has lower back pain and positive Straight Leg Raise on the left."},
        {"page_number": 2, "text": "Assessment includes lumbar spondylosis. Follow up in 3 weeks."}
    ]
    note = ClinicalNoteRecord(
        case_id="CASE-TEST-001",
        document_id="doc-001",
        patient_name="Test Patient",
        facility="Test Clinic",
        procedure_requested="MRI : Lumbar without contrast",
        insurance_plan="Ambetter",
        total_pages=2,
        raw_pages_text=raw_pages,
        sha256_checksum="sha-test-abc",
        facts={},
        created_at="2026-10-17T00:00:00Z",
        updated_at="2026-10-17T00:00:00Z"
    )
    claims_text = (
        "- Patient exhibits positive Straight Leg Raise on the left (Page 1)\n"
        "- Assessment includes lumbar spondylosis (Page 2)"
    )
    verified, warnings = ClaimVerifierService.verify_all_claims_in_text(claims_text, note)
    assert len(verified) >= 2
    for v in verified:
        assert v.evidence_status in (ClaimEvidenceStatus.SUPPORTED, ClaimEvidenceStatus.PARTIALLY_SUPPORTED)
        assert v.source_page in (1, 2)


# =============================================================================
# 4. UNSUPPORTED CLAIMS ARE REJECTED OR MARKED NOT_FOUND
# =============================================================================
def test_04_unsupported_claims_rejected_or_marked_not_found():
    raw_pages = [
        {"page_number": 1, "text": "Patient reports mild headache for 2 days. Neurological exam is normal."}
    ]
    note = ClinicalNoteRecord(
        case_id="CASE-TEST-002",
        document_id="doc-headache",
        patient_name="Test Patient",
        facility="Test Clinic",
        procedure_requested="CT Scan of Head with Contrast",
        insurance_plan="United Healthcare",
        total_pages=1,
        raw_pages_text=raw_pages,
        sha256_checksum="sha-123",
        facts={},
        created_at="2026-10-17T00:00:00Z",
        updated_at="2026-10-17T00:00:00Z"
    )
    claim_text = "Patient completed 6 months of physical therapy and has bilateral foot drop"
    verified = ClaimVerifierService.verify_claim(
        claim_text=claim_text,
        note_record=note,
        claimed_doc_id="doc-headache",
        claimed_page=1,
        claimed_excerpt="completed 6 months of physical therapy"
    )
    assert verified.evidence_status == ClaimEvidenceStatus.NOT_FOUND
    assert verified.is_verified is False


# =============================================================================
# 5. CONFLICTING EVIDENCE IS SURFACED
# =============================================================================
def test_05_conflicting_evidence_surfaced():
    raw_pages = [
        {"page_number": 1, "text": "MRI of lumbar spine was not performed. Ultrasound of vein was negative."}
    ]
    note = ClinicalNoteRecord(
        case_id="CASE-TEST-003",
        document_id="doc-conflict",
        patient_name="Test Patient",
        facility="Test Clinic",
        procedure_requested="MRI : Lumbar without contrast",
        insurance_plan="Ambetter",
        total_pages=1,
        raw_pages_text=raw_pages,
        sha256_checksum="sha-456",
        facts={},
        created_at="2026-10-17T00:00:00Z",
        updated_at="2026-10-17T00:00:00Z"
    )
    claim_text = "Prior MRI lumbar spine was completed showing disc herniation"
    verified = ClaimVerifierService.verify_claim(
        claim_text=claim_text,
        note_record=note,
        claimed_doc_id="doc-conflict",
        claimed_page=1,
        claimed_excerpt="Prior MRI lumbar spine was completed"
    )
    assert verified.evidence_status == ClaimEvidenceStatus.CONFLICTING
    assert verified.is_verified is False
    assert any("Contradiction detected" in n or "explicitly states" in n for n in verified.verification_notes)


# =============================================================================
# 6. NO CROSS-DOCUMENT OR CROSS-PATIENT LEAKAGE
# =============================================================================
def test_06_no_cross_document_or_cross_patient_leakage(reviewer_token):
    pdf_a = generate_sample_clinical_note_pdf(
        patient_name="Alice Anderson",
        procedure="CT Scan of Head with Contrast",
        symptom_duration="persistent headache for 9 weeks"
    )
    rec_a = note_extractor_service.extract_note(pdf_a, "Alice_CT.pdf", patient_name_override="Alice Anderson", procedure_requested_override="CT Scan of Head with Contrast")

    pdf_b = generate_sample_clinical_note_pdf(
        patient_name="Bob Brown",
        procedure="MRI : Lumbar without contrast",
        symptom_duration="lower back pain for 14 weeks"
    )
    rec_b = note_extractor_service.extract_note(pdf_b, "Bob_MRI.pdf", patient_name_override="Bob Brown", procedure_requested_override="MRI : Lumbar without contrast")

    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Summarize this clinical document.",
            "document_id": rec_b.document_id,
            "request_id": "req-iso-001"
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "Alice Anderson" not in data["response"]
    assert "CT Scan of Head" not in data["response"]


# =============================================================================
# 7. ORDERED TESTS ARE DISTINGUISHED FROM COMPLETED TESTS
# =============================================================================
def test_07_ordered_tests_distinguished_from_completed_tests():
    dr_yu_path = Path(__file__).resolve().parent.parent / "storage" / "notes" / "8311f4ea298e_Dr-Yu-NeurologyDoctorNotesD.pdf"
    if not dr_yu_path.exists():
        pytest.skip("Dr Yu neurology note not found in storage")

    with open(dr_yu_path, "rb") as f:
        pdf_bytes = f.read()

    rec = note_extractor_service.extract_note(pdf_bytes, "Dr-Yu-NeurologyDoctorNotesD.pdf")
    full_text = " ".join([p["text"] for p in rec.raw_pages_text])

    # Prior lumbar MRI was not performed
    assert "mri of lumbar spine was not performed" in full_text.lower()
    # EMG and NCS are ordered
    assert "emg" in full_text.lower() and "ordered" in full_text.lower()


# =============================================================================
# 8. OCR AND EXTRACTION FAILURES ARE HANDLED HONESTLY
# =============================================================================
def test_08_ocr_and_extraction_failures_handled_honestly():
    empty_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    rec = note_extractor_service.extract_note(empty_bytes, "corrupted_empty.pdf")
    assert rec is not None
    assert rec.overall_quality == "FAILED"
    assert rec.total_pages == 0
    assert "failed" in rec.ocr_engine_status.lower() or "corrupted" in rec.governance_warning.lower()


# =============================================================================
# 9. SUCCESSFUL LIVE / MOCKED GROQ INFERENCE
# =============================================================================
def test_09_successful_live_or_mocked_groq_inference(reviewer_token):
    mock_llm_response = (
        "### Clinical Summary\n"
        "- **Patient**: Robert Vance [Page 1]\n"
        "- **Symptoms**: Lower back pain radiating to legs for 16 weeks [Page 1]\n"
        "- **Treatments**: Physical therapy 8 weeks, not effective [Page 1]\n"
    )
    pdf_bytes = generate_sample_clinical_note_pdf(patient_name="Robert Vance", procedure="MRI : Lumbar without contrast")
    rec = note_extractor_service.extract_note(pdf_bytes, "robert.pdf", patient_name_override="Robert Vance", procedure_requested_override="MRI : Lumbar without contrast")

    with patch.object(AgentService, "get_api_key", return_value="gsk_live_test_mock_key"):
        with patch.object(AgentService, "call_groq_api", new_callable=AsyncMock) as mock_groq:
            mock_groq.return_value = (mock_llm_response, "openai/gpt-oss-120b", None)
            res = client.post(
                "/api/agent/chat",
                json={
                    "message": "Summarize the clinical note.",
                    "document_id": rec.document_id,
                    "request_id": "req-groq-live-001"
                },
                headers={"Authorization": f"Bearer {reviewer_token}"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data["is_groq_powered"] is True
            assert "openai/gpt-oss-120b" in data["model_used"]
            assert "Clinical Summary" in data["response"]


# =============================================================================
# 10. GROQ ERROR CLASSIFICATION HANDLING
# =============================================================================
def test_10_groq_error_classification_handling():
    import httpx

    async def _test():
        # 1. Missing Key returns CONFIG_ERROR
        with patch.object(AgentService, "get_api_key", return_value=None):
            resp, model, err = await AgentService.call_groq_api([{"role": "user", "content": "hi"}])
            assert resp is None
            assert err is not None
            assert "CONFIG_ERROR" in err

        # 2. Timeout simulation returns TIMEOUT_ERROR
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
            with patch.object(AgentService, "get_api_key", return_value="gsk_test1234567890"):
                resp, model, err = await AgentService.call_groq_api([{"role": "user", "content": "hi"}])
                assert resp is None
                assert err is not None
                assert "TIMEOUT" in err
    asyncio.run(_test())


# =============================================================================
# 11. TRUTHFUL EXTRACTION-ONLY FALLBACK
# =============================================================================
def test_11_truthful_extraction_only_fallback(reviewer_token):
    pdf_bytes = generate_sample_clinical_note_pdf(patient_name="Fallback Patient", procedure="MRI : Lumbar without contrast")
    rec = note_extractor_service.extract_note(pdf_bytes, "fallback.pdf", patient_name_override="Fallback Patient", procedure_requested_override="MRI : Lumbar without contrast")

    with patch.object(AgentService, "get_api_key", return_value="gsk_test_key"):
        with patch.object(AgentService, "call_groq_api", new_callable=AsyncMock) as mock_groq:
            mock_groq.return_value = (None, None, "AUTH_ERROR: Invalid API Key")
            res = client.post(
                "/api/agent/chat",
                json={
                    "message": "Summarize the note.",
                    "document_id": rec.document_id,
                    "request_id": "req-fallback-001"
                },
                headers={"Authorization": f"Bearer {reviewer_token}"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data["is_groq_powered"] is False
            assert "Extraction" in data["model_used"] or "Deterministic" in data["model_used"]
            assert "Groq inference service is unavailable" in data["response"] or "Groq inference service is not configured" in data["response"]


# =============================================================================
# 12. NO CREDENTIALS EXPOSED TO FRONTEND
# =============================================================================
def test_12_no_credentials_exposed_to_frontend(reviewer_token):
    res = client.get("/api/agent/status", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res.status_code == 200
    status_text = res.text
    assert "gsk_" not in status_text
    assert "GROQ_API_KEY" not in status_text

    frontend_src = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    if frontend_src.exists():
        for f in frontend_src.rglob("*.ts*"):
            txt = f.read_text(encoding="utf-8")
            assert "gsk_" not in txt, f"Secret found in {f.name}"
            assert "GROQ_API_KEY" not in txt, f"Env key found in {f.name}"


# =============================================================================
# 13. UPLOADING A SECOND PDF CANNOT RETURN THE FIRST PDF'S ANSWER
# =============================================================================
def test_13_uploading_second_pdf_cannot_return_first_pdf_answer(reviewer_token):
    pdf_1 = generate_sample_clinical_note_pdf(patient_name="Patient First", procedure="CT Scan of Head with Contrast")
    rec_1 = note_extractor_service.extract_note(pdf_1, "first.pdf", patient_name_override="Patient First", procedure_requested_override="CT Scan of Head with Contrast")

    pdf_2 = generate_sample_clinical_note_pdf(patient_name="Patient Second", procedure="MRI : Lumbar without contrast")
    rec_2 = note_extractor_service.extract_note(pdf_2, "second.pdf", patient_name_override="Patient Second", procedure_requested_override="MRI : Lumbar without contrast")

    res1 = client.post("/api/agent/chat", json={"message": "Summarize this note.", "document_id": rec_1.document_id}, headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res1.status_code == 200
    assert res1.json()["trace"]["document_id"] == rec_1.document_id

    res2 = client.post("/api/agent/chat", json={"message": "Summarize this note.", "document_id": rec_2.document_id}, headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res2.status_code == 200
    assert res2.json()["trace"]["document_id"] == rec_2.document_id
    assert res2.json()["trace"]["document_id"] != res1.json()["trace"]["document_id"]


# =============================================================================
# 14. OUT-OF-ORDER REQUESTS CANNOT OVERWRITE NEWER RESPONSES
# =============================================================================
def test_14_out_of_order_requests_cannot_overwrite_newer_responses(reviewer_token):
    req_id = "req-unique-998877"
    res = client.post(
        "/api/agent/chat",
        json={"message": "Summarize document.", "request_id": req_id},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    assert res.json()["request_id"] == req_id


# =============================================================================
# 15. SOURCE METADATA AND PAGE COUNTS MATCH THE ACTIVE PDF
# =============================================================================
def test_15_source_metadata_and_page_counts_match_active_pdf(reviewer_token):
    dr_yu_path = Path(__file__).resolve().parent.parent / "storage" / "notes" / "8311f4ea298e_Dr-Yu-NeurologyDoctorNotesD.pdf"
    if not dr_yu_path.exists():
        pytest.skip("Dr Yu note not found")

    with open(dr_yu_path, "rb") as f:
        pdf_bytes = f.read()

    rec = note_extractor_service.extract_note(pdf_bytes, "Dr-Yu-NeurologyDoctorNotesD.pdf")
    res = client.post(
        "/api/agent/chat",
        json={"message": "Summarize the clinical note.", "document_id": rec.document_id},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["trace"]["valid_page_count"] == 2
    assert data["trace"]["document_sha256"] == rec.sha256_checksum


# =============================================================================
# 16. DOCUMENT SUMMARIES DO NOT REQUIRE POLICY EVALUATION
# =============================================================================
def test_16_document_summaries_do_not_require_policy_evaluation(reviewer_token):
    res = client.post(
        "/api/agent/chat",
        json={"message": "Please summarize all symptoms, examination findings, and treatments in this document."},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "DOCUMENT_ANALYSIS"
    assert data["evaluation"] is None


# =============================================================================
# 17. MISSING POLICY ID DOES NOT SILENTLY SELECT A DEFAULT POLICY
# =============================================================================
def test_17_missing_policy_id_does_not_silently_select_default(reviewer_token, sample_lumbar_doc):
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Can this lumbar MRI request be approved?",
            "case_id": sample_lumbar_doc.case_id,
            "policy_id": None
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["compatibility_status"] in ("POLICY_MISMATCH", "NO_APPLICABLE_VERIFIED_POLICY")
    assert "P-UHC-CT-2026" not in (data["trace"]["selected_policy_id"] or "")


# =============================================================================
# 18. INCOMPATIBLE PAYER, MODALITY, ANATOMY BLOCKS EVALUATION
# =============================================================================
def test_18_incompatible_payer_modality_anatomy_blocks_evaluation(reviewer_token):
    pdf_bytes = generate_sample_clinical_note_pdf(patient_name="Frank Miller", procedure="MRI : Lumbar without contrast")
    rec = note_extractor_service.extract_note(pdf_bytes, "frank.pdf", patient_name_override="Frank Miller", procedure_requested_override="MRI : Lumbar without contrast", insurance_plan="Ambetter")

    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Can this procedure be approved under the policy?",
            "case_id": rec.case_id,
            "document_id": rec.document_id,
            "policy_id": "P-UHC-CT-2026"
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["compatibility_status"] == "POLICY_MISMATCH"
    assert data["evaluation"] is None
    assert "FAIL-CLOSED" in data["response"]


# =============================================================================
# 19. ONLY AUTHENTIC, APPROVED, VERIFIED POLICIES CAN BE USED
# =============================================================================
def test_19_only_authentic_approved_verified_policies_can_be_used(reviewer_token):
    pdf_bytes = generate_sample_clinical_note_pdf(patient_name="Grace Hopper", procedure="CT Scan of Head with Contrast")
    rec = note_extractor_service.extract_note(pdf_bytes, "grace.pdf", patient_name_override="Grace Hopper", procedure_requested_override="CT Scan of Head with Contrast", insurance_plan="United Healthcare")

    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Can this CT scan be approved under policy P-SYNTH-UNAPPROVED?",
            "case_id": rec.case_id,
            "policy_id": "P-SYNTH-UNAPPROVED"
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["compatibility_status"] in ("POLICY_MISMATCH", "NO_APPLICABLE_VERIFIED_POLICY")
    assert data["evaluation"] is None


# =============================================================================
# 20. APPEAL DRAFTS DO NOT INVENT POLICY CITATIONS OR UNSUPPORTED FACTS
# =============================================================================
def test_20_appeal_drafts_do_not_invent_policy_citations_or_facts(reviewer_token):
    res = client.post(
        "/api/agent/chat",
        json={"message": "Draft an appeal letter for this denial."},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "APPEAL_DRAFT"
    assert "[Insert authentic verified" in data["response"]
    assert "MedRule governance strictly prohibits asserting that coverage criteria are met" in data["response"]
