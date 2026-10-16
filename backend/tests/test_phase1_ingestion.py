import pytest
from app.services.pdf_extractor import PDFExtractorService
from app.services.policy_registry import (
    PolicyRegistryService,
    DuplicatePolicyError,
    VersionConflictError,
)
from app.models.policy import PolicyLifecycleStatus
from tests.pdf_test_helpers import (
    generate_sample_policy_pdf,
    generate_scanned_mock_pdf,
)

def test_pdf_extraction_page_boundaries():
    pdf_bytes = generate_sample_policy_pdf()
    pages, quality, sections = PDFExtractorService.extract_document(pdf_bytes)

    assert len(pages) == 3
    assert pages[0]["page_number"] == 1
    assert "Coverage Scope" in pages[0]["text"]
    assert pages[1]["page_number"] == 2
    assert "Duration of Symptoms" in pages[1]["text"]
    assert quality.overall_quality == "HIGH"
    assert quality.scanned_pages_count == 0

def test_scanned_pdf_detection():
    scanned_bytes = generate_scanned_mock_pdf()
    pages, quality, sections = PDFExtractorService.extract_document(scanned_bytes)

    assert len(pages) == 2
    assert quality.scanned_pages_count == 2
    assert quality.overall_quality == "LOW_NEEDS_OCR"
    assert 1 in quality.low_confidence_pages
    assert 2 in quality.low_confidence_pages

def test_section_parsing_and_citations():
    pdf_bytes = generate_sample_policy_pdf()
    pages, quality, sections = PDFExtractorService.extract_document(pdf_bytes)

    sec_numbers = [s.section_number for s in sections]
    assert any("4.2.1" in s for s in sec_numbers)
    assert any("4.2.2" in s for s in sec_numbers)

    # Check page linking
    sec_422 = next(s for s in sections if "4.2.2" in s.section_number)
    assert sec_422.page_number == 2

def test_sha256_checksum():
    pdf_bytes = generate_sample_policy_pdf()
    hash1 = PDFExtractorService.compute_sha256(pdf_bytes)
    hash2 = PDFExtractorService.compute_sha256(pdf_bytes)
    assert hash1 == hash2
    assert len(hash1) == 64

def test_policy_registration_and_lifecycle(tmp_path):
    data_dir = tmp_path / "data"
    storage_dir = tmp_path / "storage"
    service = PolicyRegistryService(data_dir=data_dir, storage_dir=storage_dir)

    pdf_bytes = generate_sample_policy_pdf()
    pages, quality, sections = PDFExtractorService.extract_document(pdf_bytes)
    checksum = PDFExtractorService.compute_sha256(pdf_bytes)

    # Register
    policy = service.register_policy_upload(
        file_bytes=pdf_bytes,
        filename="Aetna_Head_CT.pdf",
        insurer="Aetna",
        policy_name="Computed Tomography Guidelines",
        version="2026.1",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan of Head",
        effective_date="2026-03-01",
        cpt_codes=["70450"],
        plan="Choice POS II",
        sections=sections,
        quality_report=quality,
        checksum=checksum
    )

    # Starts in NEEDS_REVIEW
    assert policy.lifecycle_status == PolicyLifecycleStatus.NEEDS_REVIEW
    assert (storage_dir / f"{checksum[:12]}_Aetna_Head_CT.pdf").exists()

    # Lifecycle transition
    updated = service.update_status(policy.id, PolicyLifecycleStatus.APPROVED_FOR_USE)
    assert updated.lifecycle_status == PolicyLifecycleStatus.APPROVED_FOR_USE

def test_duplicate_upload_prevention(tmp_path):
    service = PolicyRegistryService(data_dir=tmp_path / "data", storage_dir=tmp_path / "storage")
    pdf_bytes = generate_sample_policy_pdf()
    pages, quality, sections = PDFExtractorService.extract_document(pdf_bytes)
    checksum = PDFExtractorService.compute_sha256(pdf_bytes)

    service.register_policy_upload(
        file_bytes=pdf_bytes,
        filename="Aetna_CT.pdf",
        insurer="Aetna",
        policy_name="CT Guideline",
        version="2026.1",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan",
        effective_date="2026-01-01",
        cpt_codes=["70450"],
        plan="Standard",
        sections=sections,
        quality_report=quality,
        checksum=checksum
    )

    # Second identical upload must raise DuplicatePolicyError
    with pytest.raises(DuplicatePolicyError):
        service.register_policy_upload(
            file_bytes=pdf_bytes,
            filename="Aetna_CT_Copy.pdf",
            insurer="Aetna",
            policy_name="CT Guideline",
            version="2026.1",
            procedure_type="CT Scan",
            procedure_full_name="CT Scan",
            effective_date="2026-01-01",
            cpt_codes=["70450"],
            plan="Standard",
            sections=sections,
            quality_report=quality,
            checksum=checksum
        )

def test_version_overwrite_conflict_prevention(tmp_path):
    service = PolicyRegistryService(data_dir=tmp_path / "data", storage_dir=tmp_path / "storage")
    pdf_bytes1 = generate_sample_policy_pdf(version="2026.1")
    pages1, quality1, sections1 = PDFExtractorService.extract_document(pdf_bytes1)
    checksum1 = PDFExtractorService.compute_sha256(pdf_bytes1)

    service.register_policy_upload(
        file_bytes=pdf_bytes1,
        filename="Aetna_v1.pdf",
        insurer="Aetna",
        policy_name="CT Guideline",
        version="2026.1",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan",
        effective_date="2026-01-01",
        cpt_codes=["70450"],
        plan="Standard",
        sections=sections1,
        quality_report=quality1,
        checksum=checksum1
    )

    # Upload different PDF with the SAME version string
    pdf_bytes2 = generate_sample_policy_pdf(policy_name="Different CT Content", version="2026.1")
    pages2, quality2, sections2 = PDFExtractorService.extract_document(pdf_bytes2)
    checksum2 = PDFExtractorService.compute_sha256(pdf_bytes2)

    with pytest.raises(VersionConflictError):
        service.register_policy_upload(
            file_bytes=pdf_bytes2,
            filename="Aetna_modified.pdf",
            insurer="Aetna",
            policy_name="CT Guideline",
            version="2026.1",
            procedure_type="CT Scan",
            procedure_full_name="CT Scan",
            effective_date="2026-01-01",
            cpt_codes=["70450"],
            plan="Standard",
            sections=sections2,
            quality_report=quality2,
            checksum=checksum2
        )

def test_search_restricted_to_approved(tmp_path):
    service = PolicyRegistryService(data_dir=tmp_path / "data", storage_dir=tmp_path / "storage")
    pdf_bytes = generate_sample_policy_pdf()
    pages, quality, sections = PDFExtractorService.extract_document(pdf_bytes)
    checksum = PDFExtractorService.compute_sha256(pdf_bytes)

    policy = service.register_policy_upload(
        file_bytes=pdf_bytes,
        filename="Test_Policy.pdf",
        insurer="BCBS",
        policy_name="BCBS CT Criteria",
        version="2026.1",
        procedure_type="CT Scan",
        procedure_full_name="CT Scan",
        effective_date="2026-01-01",
        cpt_codes=["70450"],
        plan="PPO",
        sections=sections,
        quality_report=quality,
        checksum=checksum
    )

    # While NEEDS_REVIEW, search with approved_only=True returns 0 results
    res_unapproved = service.search_sections("Duration", approved_only=True)
    assert len(res_unapproved) == 0

    # Search with approved_only=False returns matches
    res_all = service.search_sections("Duration", approved_only=False)
    assert len(res_all) > 0

    # Once APPROVED, returns results
    service.update_status(policy.id, PolicyLifecycleStatus.APPROVED_FOR_USE)
    res_approved = service.search_sections("Duration", approved_only=True)
    assert len(res_approved) > 0
    assert res_approved[0].page_number == 2
