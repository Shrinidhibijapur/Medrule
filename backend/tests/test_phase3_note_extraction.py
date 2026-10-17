import io
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app, DATA_DIR
from app.models.note import (
    ClinicalNoteRecord,
    ClinicalFactStatus,
    ExtractedFact,
    FactCorrectionRequest,
    FactFlagRequest,
)
from app.services.note_extractor import ClinicalNoteExtractorService, OCRService
from tests.pdf_test_helpers import (
    generate_scanned_mock_pdf,
    generate_sample_clinical_note_pdf,
    generate_contradictory_clinical_note_pdf,
    generate_adversarial_prompt_injection_note_pdf,
    generate_abbreviated_clinical_note_pdf,
)

client = TestClient(app)

@pytest.fixture
def extractor_service(tmp_path):
    storage_dir = tmp_path / "storage"
    notes_dir = tmp_path / "notes"
    return ClinicalNoteExtractorService(data_dir=tmp_path, storage_dir=storage_dir)

def test_digital_note_extraction_with_page_citations(extractor_service):
    """
    1. Tests multi-page digital note extraction.
    Verifies that facts are extracted with exact page numbers and explicit status.
    """
    pdf_bytes = generate_sample_clinical_note_pdf(
        patient_name="John Doe",
        age=42,
        symptom_duration="persisting for 3 months",
        conservative_tx="Trial of conservative treatment over past 8 weeks without improvement",
        neuro_exam="Neurological examination abnormal: focal asymmetry and mild ataxia",
        indication="Rule out intracranial pathology or space-occupying lesion",
        procedure="CT Scan of Head with Contrast",
        contrast_rationale="Contrast clinically indicated for further diagnostic evaluation"
    )

    record = extractor_service.extract_note(
        file_bytes=pdf_bytes,
        filename="john_doe_clinical_note.pdf",
        policy_id="P-UHC-CT-2026"
    )

    assert record.patient_name == "John Doe"
    assert record.patient_age == 42
    assert record.total_pages == 3
    assert record.scanned_pages_count == 0
    assert record.overall_quality == "HIGH"
    assert record.is_synthetic is True

    facts = record.facts
    assert "neurological_symptoms" in facts
    assert facts["neurological_symptoms"].value is True
    assert facts["neurological_symptoms"].status == ClinicalFactStatus.EXPLICIT
    assert facts["neurological_symptoms"].source_page == 1
    assert "headaches" in facts["neurological_symptoms"].excerpt.lower()

    assert "symptom_duration_weeks" in facts
    assert facts["symptom_duration_weeks"].value == 12.0  # 3 months = 12 weeks
    assert facts["symptom_duration_weeks"].status == ClinicalFactStatus.EXPLICIT
    assert facts["symptom_duration_weeks"].source_page == 1

    assert "conservative_treatment_attempted" in facts
    assert facts["conservative_treatment_attempted"].value is True
    assert facts["conservative_treatment_attempted"].source_page == 2

    assert "neurological_exam_abnormal" in facts
    assert facts["neurological_exam_abnormal"].value is True
    assert facts["neurological_exam_abnormal"].source_page == 2

    assert "rule_out_pathology" in facts
    assert facts["rule_out_pathology"].value is True
    assert facts["rule_out_pathology"].source_page == 3

    assert "contrast_requested" in facts
    assert facts["contrast_requested"].value is True
    assert facts["contrast_requested"].source_page in (1, 3)

def test_scanned_pdf_detection_and_quality_score(extractor_service):
    """
    2. Tests scanned-page detection on empty/image PDFs.
    Verifies that low character density is detected, quality is LOW_NEEDS_OCR,
    and facts are safely marked ABSENT without hallucination.
    """
    scanned_bytes = generate_scanned_mock_pdf()

    record = extractor_service.extract_note(
        file_bytes=scanned_bytes,
        filename="scanned_hospital_note.pdf",
        policy_id="P-UHC-CT-2026"
    )

    assert record.total_pages == 2
    assert record.scanned_pages_count == 2
    assert record.overall_quality == "LOW_NEEDS_OCR"
    assert "OCR" in record.ocr_engine_status or "manual" in record.ocr_engine_status

    # Missing facts must NOT be hallucinated or filled from general medical knowledge
    assert record.facts["neurological_symptoms"].status == ClinicalFactStatus.ABSENT
    assert record.facts["neurological_symptoms"].value is None
    assert record.facts["symptom_duration_weeks"].status == ClinicalFactStatus.ABSENT
    assert record.facts["conservative_treatment_attempted"].status == ClinicalFactStatus.ABSENT

def test_facts_spread_across_pages(extractor_service):
    """
    3. Confirms facts distributed across pages 1, 2, and 3 retain distinct page numbers.
    """
    pdf_bytes = generate_sample_clinical_note_pdf()
    record = extractor_service.extract_note(pdf_bytes, "multipage_case.pdf")

    p1_facts = [k for k, f in record.facts.items() if f.source_page == 1]
    p2_facts = [k for k, f in record.facts.items() if f.source_page == 2]
    p3_facts = [k for k, f in record.facts.items() if f.source_page == 3]

    assert len(p1_facts) > 0, "Expected facts on page 1"
    assert len(p2_facts) > 0, "Expected facts on page 2"
    assert len(p3_facts) > 0, "Expected facts on page 3"
    assert "symptom_duration_weeks" in p1_facts
    assert "neurological_exam_abnormal" in p2_facts

def test_missing_facts_status_absent(extractor_service):
    """
    4. Tests that unmentioned facts strictly produce ABSENT status with None value.
    """
    pdf = io.BytesIO()
    from fpdf import FPDF
    f = FPDF()
    f.add_page()
    f.set_font("Helvetica", "B", 12)
    f.cell(0, 10, "Patient with mild tension headache.")
    f.output(pdf)

    record = extractor_service.extract_note(pdf.getvalue(), "sparse_note.pdf")

    # Neurological symptoms are mentioned (headache)
    assert record.facts["neurological_symptoms"].status == ClinicalFactStatus.EXPLICIT

    # But conservative treatment, exam, pathology, and contrast are completely absent
    assert record.facts["conservative_treatment_attempted"].status == ClinicalFactStatus.ABSENT
    assert record.facts["conservative_treatment_attempted"].value is None
    assert record.facts["conservative_treatment_attempted"].excerpt is None
    assert record.facts["conservative_treatment_attempted"].confidence == 1.0

    assert record.facts["rule_out_pathology"].status == ClinicalFactStatus.ABSENT
    assert record.facts["rule_out_pathology"].value is None

def test_contradictory_evidence_detection(extractor_service):
    """
    5. Tests contradictory evidence handling (e.g. 2 weeks duration vs 4 months duration,
    and normal exam vs abnormal exam with ataxia).
    Must mark CONFLICTING status and not arbitrarily choose a winner.
    """
    contra_pdf = generate_contradictory_clinical_note_pdf()
    record = extractor_service.extract_note(contra_pdf, "conflicting_case.pdf")

    duration_fact = record.facts["symptom_duration_weeks"]
    assert duration_fact.status == ClinicalFactStatus.CONFLICTING
    assert duration_fact.value is None
    assert duration_fact.confidence <= 0.60
    assert "contradictory" in duration_fact.excerpt.lower() or "vs" in duration_fact.excerpt.lower()

    exam_fact = record.facts["neurological_exam_abnormal"]
    assert exam_fact.status == ClinicalFactStatus.CONFLICTING
    assert exam_fact.value is None
    assert "contradictory" in exam_fact.excerpt.lower() or "vs" in exam_fact.excerpt.lower()

def test_clinical_abbreviations_recognition(extractor_service):
    """
    6. Tests recognition of standard clinical abbreviations ('HA', 'wks', 'PT', 'R/O', 'SOL').
    """
    abbr_pdf = generate_abbreviated_clinical_note_pdf()
    record = extractor_service.extract_note(abbr_pdf, "abbreviated_note.pdf")

    assert record.facts["neurological_symptoms"].value is True
    assert record.facts["neurological_symptoms"].status == ClinicalFactStatus.EXPLICIT

    assert record.facts["symptom_duration_weeks"].value == 8.0
    assert record.facts["symptom_duration_weeks"].status == ClinicalFactStatus.EXPLICIT

    assert record.facts["conservative_treatment_attempted"].value is True
    assert record.facts["rule_out_pathology"].value is True
    assert record.facts["contrast_requested"].value is True

def test_low_confidence_unclear_extraction(extractor_service):
    """
    7. Tests low-confidence and unclear evidence when vague timeframes are used ('recently').
    """
    pdf = io.BytesIO()
    from fpdf import FPDF
    f = FPDF()
    f.add_page()
    f.set_font("Helvetica", "", 12)
    f.multi_cell(0, 8, "Patient reports headaches started recently. Tried resting at home.")
    f.output(pdf)

    record = extractor_service.extract_note(pdf.getvalue(), "vague_note.pdf")

    duration_fact = record.facts["symptom_duration_weeks"]
    assert duration_fact.status == ClinicalFactStatus.UNCLEAR
    assert duration_fact.confidence < 0.70

def test_prompt_injection_safety_untrusted_data(extractor_service):
    """
    8. Tests adversarial injection attempts embedded within uploaded document content.
    The service must treat document content as passive text data, detect injection phrases,
    and add a security warning to the audit trail without executing instructions.
    """
    adversarial_pdf = generate_adversarial_prompt_injection_note_pdf()
    record = extractor_service.extract_note(adversarial_pdf, "adversarial_payload.pdf")

    # Document text was NOT executed as system commands
    # Check duration extracted from actual text (1 week)
    assert record.facts["symptom_duration_weeks"].value == 1.0
    assert record.facts["conservative_treatment_attempted"].status == ClinicalFactStatus.ABSENT

    # Audit trail must contain the detected security warning
    sec_entries = [a for a in record.audit_trail if a.get("action") == "SECURITY_WARNING"]
    assert len(sec_entries) > 0
    assert "prompt injection" in sec_entries[0]["details"].lower()

def test_auditable_fact_correction_and_override(extractor_service):
    """
    9. Tests clinician manual correction and override workflow.
    Ensures that modifications preserve original history, update status, and record reviewer reason.
    """
    pdf_bytes = generate_sample_clinical_note_pdf()
    record = extractor_service.extract_note(pdf_bytes, "test_override.pdf")
    case_id = record.case_id

    # Clinician corrects duration from 12 weeks to 16 weeks based on prior visit note
    correction = FactCorrectionRequest(
        fact_key="symptom_duration_weeks",
        corrected_value=16.0,
        corrected_status=ClinicalFactStatus.EXPLICIT,
        reviewer_name="Dr. Sarah Jenkins, MD",
        reason="Prior neurology note from August establishes 16 weeks duration rather than 12."
    )

    updated = extractor_service.apply_fact_override(case_id, correction)

    fact = updated.facts["symptom_duration_weeks"]
    assert fact.value == 16.0
    assert fact.status == ClinicalFactStatus.EXPLICIT
    assert fact.reviewer_override is not None
    assert fact.reviewer_override.is_overridden is True
    assert fact.reviewer_override.overridden_by == "Dr. Sarah Jenkins, MD"
    assert fact.reviewer_override.original_value == 12.0
    assert "August" in fact.reviewer_override.reason

    # Audit trail records FACT_OVERRIDE
    audit = updated.audit_trail
    override_event = next(e for e in audit if e.get("action") == "FACT_OVERRIDE")
    assert override_event["fact_key"] == "symptom_duration_weeks"
    assert override_event["reviewer"] == "Dr. Sarah Jenkins, MD"

def test_flag_fact_for_review(extractor_service):
    """
    10. Tests clinician flagging of ambiguous fact for secondary review.
    """
    pdf_bytes = generate_sample_clinical_note_pdf()
    record = extractor_service.extract_note(pdf_bytes, "test_flag.pdf")
    case_id = record.case_id

    flag_req = FactFlagRequest(
        fact_key="conservative_treatment_attempted",
        reviewer_name="Marcus Vance, RN",
        reason="Physical therapy notes are pending from outside facility."
    )

    updated = extractor_service.flag_fact_for_review(case_id, flag_req)
    fact = updated.facts["conservative_treatment_attempted"]
    assert fact.is_flagged_for_review is True
    assert "Physical therapy" in fact.flag_reason

    flag_event = next(e for e in updated.audit_trail if e.get("action") == "FACT_FLAGGED")
    assert flag_event["reviewer"] == "Marcus Vance, RN"

def test_api_note_upload_validation_and_streaming():
    """
    11. Tests HTTP API endpoints for note upload, validation, retrieval, and document streaming.
    """
    # 1. Non-PDF upload rejected
    bad_resp = client.post(
        "/api/notes/upload",
        files={"file": ("notes.txt", b"plain text notes", "text/plain")},
        data={"policy_id": "P-UHC-CT-2026"}
    )
    assert bad_resp.status_code == 400
    assert "PDF" in bad_resp.json()["detail"]

    # 2. Empty file rejected
    empty_resp = client.post(
        "/api/notes/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        data={"policy_id": "P-UHC-CT-2026"}
    )
    assert empty_resp.status_code == 400

    # 3. Valid PDF upload succeeds
    valid_pdf = generate_sample_clinical_note_pdf(patient_name="Jane Doe", age=38)
    upload_resp = client.post(
        "/api/notes/upload",
        files={"file": ("jane_doe_note.pdf", valid_pdf, "application/pdf")},
        data={
            "policy_id": "P-UHC-CT-2026",
            "patient_name": "Jane Doe",
            "facility": "Riverside Medical Center"
        }
    )
    assert upload_resp.status_code == 201
    note_data = upload_resp.json()
    case_id = note_data["case_id"]
    try:
        assert note_data["patient_name"] == "Jane Doe"
        assert note_data["is_synthetic"] is True

        # 4. GET note by case_id
        get_resp = client.get(f"/api/notes/{case_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["case_id"] == case_id

        # 5. GET note document streams original PDF
        doc_resp = client.get(f"/api/notes/{case_id}/document")
        assert doc_resp.status_code == 200
        assert doc_resp.headers["content-type"] == "application/pdf"
        assert len(doc_resp.content) > 100

        # 6. PATCH fact correction via API
        patch_resp = client.patch(
            f"/api/notes/{case_id}/facts/symptom_duration_weeks",
            json={
                "fact_key": "symptom_duration_weeks",
                "corrected_value": 14.0,
                "corrected_status": "EXPLICIT",
                "reviewer_name": "Dr. Sarah Jenkins, MD",
                "reason": "Corrected per intake notes"
            }
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["facts"]["symptom_duration_weeks"]["value"] == 14.0
    finally:
        # Clean up temporary test case file
        from app.main import DATA_DIR
        import os
        temp_case_file = os.path.join(DATA_DIR, "notes", f"{case_id}.json")
        if os.path.exists(temp_case_file):
            os.remove(temp_case_file)

def test_ocr_capability_reporting():
    """
    12. Tests explicit OCR subsystem status reporting.
    """
    resp = client.get("/api/notes/ocr-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ocr_available" in data
    assert "status" in data
    assert "fallback_mode" in data
    assert "supported_formats" in data
