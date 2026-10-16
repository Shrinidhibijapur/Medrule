"""
MedRule Phase 7: Frontend Routing and UX Refinement Test Suite
Validates:
1. Direct route endpoints, data availability, and state restoration on refresh.
2. Route schema compliance and valid param handling (/cases/{caseId}/...).
3. Case context preservation and invalid ID rejection (404).
4. Frontend route architecture, Not Found page, and stage workflow transitions.
5. Strict adherence to MedRule design system (warm off-white/forest green, no blue tokens).
6. Honest Phase 8 roadmap labelling for Login and Settings.
"""

import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_SRC = FRONTEND_DIR / "src"

CANONICAL_CASE_ID = "CASE-2026-001"
INVALID_CASE_ID = "CASE-NONEXISTENT-999"


class TestPhase7RouteDataIntegrity:
    """Verifies that all frontend routes have valid backend data sources for direct loading and refresh."""

    def test_dashboard_route_endpoint(self):
        """Validates /dashboard route backend metrics."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_reviews" in data
        assert "approved_count" in data
        assert "recent_reviews" in data
        assert data.get("is_synthetic_demo") is True

    def test_policy_library_route_endpoint(self):
        """Validates /policies route backend listing."""
        response = client.get("/api/policies")
        assert response.status_code == 200
        policies = response.json()
        assert isinstance(policies, list)
        assert len(policies) > 0
        assert any(p.get("id") == "P-UHC-CT-2026" or p.get("policy_id") == "P-UHC-CT-2026" for p in policies)

    def test_cases_history_route_endpoint(self):
        """Validates /cases route backend listing."""
        response = client.get("/api/cases")
        assert response.status_code == 200
        cases = response.json()
        assert isinstance(cases, list)
        assert len(cases) > 0
        assert any(c["case_id"] == CANONICAL_CASE_ID for c in cases)

    def test_case_stage_direct_load_and_refresh_data(self):
        """
        Validates that refreshing /cases/:caseId/document, /facts, /evaluation,
        /analysis, or /decision can fetch the stored record.
        """
        # Case record direct load
        res_case = client.get(f"/api/cases/{CANONICAL_CASE_ID}")
        assert res_case.status_code == 200
        rec = res_case.json()
        assert rec["case_id"] == CANONICAL_CASE_ID
        assert "John Doe" in rec["patient_name"]
        assert "facts" in rec
        assert len(rec["facts"]) > 0

        # Note document text/pdf retrieval
        res_doc = client.get(f"/api/notes/{CANONICAL_CASE_ID}/document")
        assert res_doc.status_code == 200
        assert res_doc.headers["content-type"] in ["application/pdf", "text/plain"]

        # Evaluation report direct restoration on refresh
        res_eval = client.post(f"/api/cases/{CANONICAL_CASE_ID}/evaluate")
        assert res_eval.status_code == 200
        report = res_eval.json()
        assert report["case_id"] == CANONICAL_CASE_ID
        assert report["verdict"] in ["APPROVED", "NOT_APPROVED", "CANNOT_BE_DETERMINED"]
        assert len(report["criteria_results"]) > 0

    def test_case_stage_direct_load_invalid_id_returns_404(self):
        """Direct loading of an invalid case ID must fail safely with HTTP 404."""
        res_case = client.get(f"/api/cases/{INVALID_CASE_ID}")
        assert res_case.status_code == 404

        res_note = client.get(f"/api/notes/{INVALID_CASE_ID}")
        assert res_note.status_code == 404

        res_doc = client.get(f"/api/notes/{INVALID_CASE_ID}/document")
        assert res_doc.status_code == 404

        res_eval = client.post(f"/api/cases/{INVALID_CASE_ID}/evaluate")
        assert res_eval.status_code == 404

    def test_terminology_route_endpoints(self):
        """Validates /terminology route backend sources and lookup."""
        res_sources = client.get("/api/terminology/sources")
        assert res_sources.status_code == 200
        sources = res_sources.json()
        assert len(sources) >= 5

        res_lookup = client.post("/api/terminology/lookup", json={
            "term": "papilledema",
            "policy_id": "P-UHC-CT-2026"
        })
        assert res_lookup.status_code == 200
        data = res_lookup.json()
        assert data["term"].lower() == "papilledema"
        assert data["status"] in ["RULEBOOK_DEFINED", "RESOLVED"]


class TestPhase7FrontendRouteArchitecture:
    """Verifies frontend routing files, URL patterns, components, and design consistency."""

    def test_router_files_exist(self):
        """Confirms required router views and components exist."""
        assert (FRONTEND_SRC / "views" / "NotFoundView.tsx").exists()
        assert (FRONTEND_SRC / "views" / "CaseWorkflowView.tsx").exists()
        assert (FRONTEND_SRC / "views" / "LoginView.tsx").exists()
        assert (FRONTEND_SRC / "views" / "SettingsView.tsx").exists()
        assert (FRONTEND_SRC / "components" / "Sidebar.tsx").exists()
        assert (FRONTEND_SRC / "App.tsx").exists()

    def test_app_routing_paths_configured(self):
        """Confirms App.tsx defines all sensible routes requested in Phase 7."""
        app_content = (FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")
        required_paths = [
            "/dashboard",
            "/review/new",
            "/cases",
            "/policies",
            "/terminology",
            "/settings",
            "/ask",
            "/cases/:caseId/document",
            "/cases/:caseId/facts",
            "/cases/:caseId/evaluation",
            "/cases/:caseId/analysis",
            "/cases/:caseId/decision",
            "/cases/:caseId",
            "*",  # 404 catch-all
        ]
        for path in required_paths:
            assert f'path="{path}"' in app_content, f"Path {path} missing from App.tsx"

    def test_not_found_view_has_recovery_navigation(self):
        """Confirms NotFoundView provides accessible recovery links to Dashboard and Cases."""
        nf_content = (FRONTEND_SRC / "views" / "NotFoundView.tsx").read_text(encoding="utf-8")
        assert "404" in nf_content
        assert "/dashboard" in nf_content
        assert "/cases" in nf_content
        assert "Return to Dashboard" in nf_content

    def test_case_workflow_view_handles_all_stages(self):
        """Confirms CaseWorkflowView handles document, facts, evaluation, analysis, and decision."""
        workflow_content = (FRONTEND_SRC / "views" / "CaseWorkflowView.tsx").read_text(encoding="utf-8")
        for stage in ["document", "facts", "evaluation", "analysis", "decision"]:
            assert f"stage === '{stage}'" in workflow_content or f'stage === "{stage}"' in workflow_content
        # Check automatic restoration on refresh
        assert "api/cases/" in workflow_content
        assert "api/cases/${targetCaseId}/evaluate" in workflow_content or "api/cases/${caseId}/evaluate" in workflow_content

    def test_login_view_governance_notice_and_no_fake_auth(self):
        """Confirms LoginView has honest governance notice and no client-side token exposure."""
        login_content = (FRONTEND_SRC / "views" / "LoginView.tsx").read_text(encoding="utf-8")
        assert "PHASE 8" in login_content.upper()
        # Ensures tokens are never stored in localStorage or exposed via client-side cookie manipulation
        assert "localStorage.setItem" not in login_content
        assert "localStorage.getItem" not in login_content
        assert "setcookie" not in login_content.lower()

    def test_settings_view_accurate_labelling(self):
        """Confirms SettingsView accurately labels active Phase 2-6 governance and Phase 8 auth."""
        settings_content = (FRONTEND_SRC / "views" / "SettingsView.tsx").read_text(encoding="utf-8")
        assert "Active Governance Controls" in settings_content
        assert "Phase 8" in settings_content
        assert "OpenID Connect (OIDC)" in settings_content

    def test_sidebar_uses_route_paths(self):
        """Confirms Sidebar uses browser URLs rather than only in-memory flags."""
        sidebar_content = (FRONTEND_SRC / "components" / "Sidebar.tsx").read_text(encoding="utf-8")
        assert "/dashboard" in sidebar_content
        assert "/review/new" in sidebar_content
        assert "/policies" in sidebar_content
        assert "/cases" in sidebar_content
        assert "/terminology" in sidebar_content
        assert "/settings" in sidebar_content
        assert "useLocation" in sidebar_content

    def test_no_blue_ui_color_system(self):
        """Confirms MedRule design tokens remain warm off-white and forest green, with strictly no blue UI."""
        css_content = (FRONTEND_SRC / "index.css").read_text(encoding="utf-8")
        # Check CSS root variables
        assert "--primary: #315B45" in css_content
        assert "--bg-main: #F7F6F2" in css_content
        # Ensure no blue primary color
        assert "#0000FF" not in css_content
        assert "#1E40AF" not in css_content
        assert "#3B82F6" not in css_content

    def test_frontend_production_build_exists(self):
        """Confirms production distribution bundle is built and contains index.html."""
        dist_dir = FRONTEND_DIR / "dist"
        assert dist_dir.exists(), "frontend/dist does not exist"
        assert (dist_dir / "index.html").exists(), "frontend/dist/index.html is missing"
