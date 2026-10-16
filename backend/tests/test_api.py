import io
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app, DATA_DIR
from tests.pdf_test_helpers import generate_sample_policy_pdf

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "Phase 1" in data["phase"]

def test_api_list_policies():
    res = client.get("/api/policies")
    assert res.status_code == 200
    policies = res.json()
    assert len(policies) >= 1
    assert any(p["id"] == "P-UHC-CT-2026" for p in policies)

def test_api_get_policy_by_id():
    res = client.get("/api/policies/P-UHC-CT-2026")
    assert res.status_code == 200
    data = res.json()
    assert data["insurer"] == "United Healthcare"
    assert len(data["sections"]) >= 6

def test_api_search_policy_sections():
    # Search for "Intracranial" in approved policies
    res = client.get("/api/policies/search/sections?query=Intracranial&approved_only=true")
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 1
    assert any("Pathology" in r["heading"] or "Section 4.2.5" in r["section_number"] for r in results)

def test_api_policy_upload_workflow():
    uid = uuid.uuid4().hex[:6]
    test_version = f"2026.test_{uid}"
    pdf_bytes = generate_sample_policy_pdf(insurer="Humana", policy_name=f"Spine CT {uid}", version=test_version)
    file_payload = (f"Humana_Spine_{uid}.pdf", io.BytesIO(pdf_bytes), "application/pdf")

    res = client.post(
        "/api/policies/upload",
        files={"file": file_payload},
        data={
            "insurer": f"Humana_{uid}",
            "policy_name": f"Spine CT Guideline {uid}",
            "version": test_version,
            "procedure_type": "CT Scan",
            "procedure_full_name": "CT Scan of Lumbar Spine",
            "effective_date": "2026-05-01",
            "plan": "Humana Gold Plus",
            "cpt_codes": "72125, 72126"
        }
    )
    assert res.status_code == 201
    created = res.json()
    assert test_version in created["version"]
    assert created["lifecycle_status"] == "NEEDS_REVIEW"
    assert created["total_pages"] == 3
    assert len(created["sections"]) >= 3

    # Lifecycle state transition to APPROVED_FOR_USE
    pol_id = created["id"]
    patch_res = client.patch(
        f"/api/policies/{pol_id}/status",
        json={"status": "APPROVED_FOR_USE"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["lifecycle_status"] == "APPROVED_FOR_USE"

    # Cleanup test json file if needed
    test_json = DATA_DIR / "policies" / f"{pol_id.lower()}.json"
    if test_json.exists():
        test_json.unlink()

def test_api_evaluation_blocks_unapproved_policy():
    uid = uuid.uuid4().hex[:6]
    test_version = f"2026.pending_{uid}"
    pdf_bytes = generate_sample_policy_pdf(insurer="Cigna", policy_name=f"Pending CT {uid}", version=test_version)
    file_payload = (f"Cigna_{uid}.pdf", io.BytesIO(pdf_bytes), "application/pdf")

    res = client.post(
        "/api/policies/upload",
        files={"file": file_payload},
        data={
            "insurer": f"Cigna_{uid}",
            "policy_name": f"Pending CT Policy {uid}",
            "version": test_version,
            "procedure_type": "CT Scan",
            "procedure_full_name": "CT Scan",
            "effective_date": "2026-01-01",
            "cpt_codes": "70450"
        }
    )
    assert res.status_code == 201
    pending_id = res.json()["id"]

    eval_res = client.post(
        "/api/evaluate",
        json={
            "case_id": "TEST-001",
            "patient_name": "Test Patient",
            "policy_id": pending_id,
            "facts": {}
        }
    )
    assert eval_res.status_code == 400
    assert "must be approved by an authorized reviewer before use in evaluations" in eval_res.json()["detail"]

    # Cleanup test json file
    test_json = DATA_DIR / "policies" / f"{pending_id.lower()}.json"
    if test_json.exists():
        test_json.unlink()
