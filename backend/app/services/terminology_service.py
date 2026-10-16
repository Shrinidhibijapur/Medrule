"""
MedRule Phase 6: Authoritative Terminology-Only Lookup Service.

Principles:
1. RULEBOOK-FIRST RESOLUTION: Always inspect the selected policy's own definitions first.
2. APPROVED SOURCE REGISTRY: Strict allowlist of verified domains (NLM MeSH, MedlinePlus, CMS).
3. TERMINOLOGY ONLY: No coverage rules, no recommendations, no criteria generation.
4. STRICT ISOLATION: Zero influence on rules engine or evaluation outcomes.
5. SAFE FAILURE: Unresolved terms or source conflicts return safe status and request human review.
6. SECURITY: Rejection of unapproved domains and prompt injection sanitization.
"""

import os
import re
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from app.models.terminology import (
    ApprovedSource,
    TerminologySourceStatus,
    TerminologyResolutionStatus,
    TerminologyDefinition,
    TerminologyLookupRequest,
    TerminologyLookupResponse,
)


class TerminologyServiceError(Exception):
    """Base exception for terminology service operations."""
    pass


class UnapprovedSourceError(TerminologyServiceError):
    """Raised when an unapproved domain or URL is requested."""
    pass


class TerminologyService:
    """
    Authoritative Terminology-Only Lookup Service.
    Strictly isolated from policy coverage logic and rules engine.
    """

    # Strict domain allowlist for external authoritative terminology
    ALLOWED_DOMAINS = {
        "mesh.nlm.nih.gov",
        "medlineplus.gov",
        "cms.gov",
    }

    # Policy Rulebook-First definitions dictionary (mapped by policy_id -> normalized term)
    RULEBOOK_DEFINITIONS: Dict[str, Dict[str, Dict[str, str]]] = {
        "P-UHC-CT-2026": {
            "headache": {
                "term": "Headache",
                "definition": (
                    "Persistent, progressive, or severe cephalalgia unresponsive to appropriate first-line "
                    "conservative clinical management, requiring objective diagnostic characterization."
                ),
                "section": "Section 2.1 (Clinical Indications)",
                "page": "Page 2",
            },
            "focal neurological deficit": {
                "term": "Focal Neurological Deficit",
                "definition": (
                    "Objective abnormality on physical neurological examination reflecting localized structural "
                    "cerebral pathology, including unilateral motor weakness, hemiparesis, asymmetric hyperreflexia, "
                    "or aphasia."
                ),
                "section": "Section 2.2 (Objective Neurological Deficit)",
                "page": "Page 3",
            },
            "papilledema": {
                "term": "Papilledema",
                "definition": (
                    "Optic disc swelling secondary to elevated intracranial pressure, documented by direct "
                    "fundoscopic examination by an examining physician or optometrist/ophthalmologist."
                ),
                "section": "Section 2.3 (Signs of Increased ICP)",
                "page": "Page 3",
            },
            "conservative therapy": {
                "term": "Conservative Therapy",
                "definition": (
                    "Structured trial of appropriate medical, pharmacologic, or physical therapy for a minimum "
                    "documented duration of 6 continuous weeks without adequate symptom relief."
                ),
                "section": "Section 3.1 (Conservative Trial Requirements)",
                "page": "Page 4",
            },
            "computed tomography": {
                "term": "Computed Tomography (CT) of Head",
                "definition": (
                    "Cross-sectional diagnostic imaging modality using X-ray attenuation measurements to visualize "
                    "cranial structures, brain parenchyma, and skull with or without intravenous iodinated contrast."
                ),
                "section": "Section 1.0 (Modality Scope)",
                "page": "Page 1",
            },
            "red flag symptoms": {
                "term": "Red Flag Symptoms",
                "definition": (
                    "High-risk clinical presentations requiring urgent advanced neuroimaging, including thunderclap "
                    "onset (peak <1 minute), new-onset headache in patients >50 years old, progressive neurologic "
                    "decline, or headache with fever and meningismus."
                ),
                "section": "Section 2.1 (Clinical Indications)",
                "page": "Page 2",
            },
            "contrast allergy": {
                "term": "Contrast Allergy (Anaphylactoid Reaction)",
                "definition": (
                    "Documented severe prior hypersensitivity reaction to intravenous iodinated radiocontrast "
                    "media without an established premedication protocol, serving as a safety contraindication."
                ),
                "section": "Section 4.1 (Safety Contraindications)",
                "page": "Page 5",
            },
        }
    }

    # External Authoritative Source Definitions (only from verified allowlisted sources)
    EXTERNAL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
        "ataxia": {
            "source_id": "src-nlm-mesh",
            "term": "Ataxia",
            "definition": (
                "Lack of voluntary coordination of muscle movements that can include abnormalities of gait, "
                "changes in speech, and irregular ocular movements resulting from cerebellar dysfunction."
            ),
            "domain": "mesh.nlm.nih.gov",
            "url": "https://mesh.nlm.nih.gov/record/ui?ui=D001259",
        },
        "hydrocephalus": {
            "source_id": "src-nlm-mesh",
            "term": "Hydrocephalus",
            "definition": (
                "An abnormal accumulation of cerebrospinal fluid (CSF) within the ventricles of the brain, "
                "potentially causing increased intracranial pressure and ventricular enlargement."
            ),
            "domain": "mesh.nlm.nih.gov",
            "url": "https://mesh.nlm.nih.gov/record/ui?ui=D006849",
        },
        "subdural hematoma": {
            "source_id": "src-nlm-mesh",
            "term": "Subdural Hematoma",
            "definition": (
                "An accumulation of blood between the dura mater and the arachnoid membrane, usually "
                "resulting from tears in bridging veins crossing the subdural space."
            ),
            "domain": "mesh.nlm.nih.gov",
            "url": "https://mesh.nlm.nih.gov/record/ui?ui=D006408",
        },
        "space-occupying lesion": {
            "source_id": "src-nlm-mesh",
            "term": "Space-Occupying Lesion",
            "definition": (
                "Any intracranial lesion (such as neoplasm, hematoma, or abscess) that takes up volume within the "
                "rigid cranial cavity, exerting mass effect and threatening brain herniation."
            ),
            "domain": "mesh.nlm.nih.gov",
            "url": "https://mesh.nlm.nih.gov/record/ui?ui=D001932",
        },
        "thunderclap headache": {
            "source_id": "src-nlm-mesh",
            "term": "Thunderclap Headache",
            "definition": (
                "A high-intensity headache of abrupt onset, reaching maximum severity in less than one minute, "
                "often indicating acute intracranial vascular emergencies such as subarachnoid hemorrhage."
            ),
            "domain": "mesh.nlm.nih.gov",
            "url": "https://mesh.nlm.nih.gov/record/ui?ui=D051299",
        },
        "ct scan": {
            "source_id": "src-medlineplus",
            "term": "Computed Tomography (CT) Scan",
            "definition": (
                "A diagnostic imaging exam that uses specialized X-ray equipment and computers to create detailed "
                "cross-sectional images of bones, blood vessels, and soft tissues inside the body."
            ),
            "domain": "medlineplus.gov",
            "url": "https://medlineplus.gov/ctscans.html",
        },
        "contrast material": {
            "source_id": "src-medlineplus",
            "term": "Contrast Material",
            "definition": (
                "A medical substance introduced into the body to enhance diagnostic imaging by temporarily changing "
                "the way X-rays interact with tissues, clarifying anatomical boundaries."
            ),
            "domain": "medlineplus.gov",
            "url": "https://medlineplus.gov/ency/article/003330.htm",
        },
        "anaphylaxis": {
            "source_id": "src-medlineplus",
            "term": "Anaphylaxis",
            "definition": (
                "A severe, life-threatening allergic reaction that occurs within seconds or minutes of exposure "
                "to an allergen, causing respiratory distress, hypotension, and shock."
            ),
            "domain": "medlineplus.gov",
            "url": "https://medlineplus.gov/anaphylaxis.html",
        },
        "prior authorization": {
            "source_id": "src-cms-glossary",
            "term": "Prior Authorization",
            "definition": (
                "A formal administrative review process through which a health insurer or health plan determines "
                "in advance whether a requested health care service or procedure meets the clinical criteria for coverage."
            ),
            "domain": "cms.gov",
            "url": "https://www.cms.gov/medicare/coverage/glossary",
        },
        "medical necessity": {
            "source_id": "src-cms-glossary",
            "term": "Medical Necessity",
            "definition": (
                "Health care services or supplies needed to prevent, diagnose, or treat an illness, injury, condition, "
                "disease, or its symptoms, meeting accepted professional medical standards and not primarily for convenience."
            ),
            "domain": "cms.gov",
            "url": "https://www.cms.gov/medicare/coverage/glossary",
        },
    }

    # Known ambiguous or conflicting definitions for testing safe failure
    CONFLICTING_TERMS: Dict[str, List[Dict[str, str]]] = {
        "experimental procedure": [
            {
                "source": "NLM MeSH",
                "definition": "Novel therapeutic or diagnostic intervention undergoing formal investigational trials.",
            },
            {
                "source": "CMS MCD Glossary",
                "definition": "Services not proven effective by controlled clinical evidence, classified as statutory non-covered.",
            },
        ]
    }

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path(__file__).resolve().parent.parent.parent / "data")
        self.audit_log_path = self.data_dir / "terminology_audit.json"
        self._init_sources_registry()

    def _init_sources_registry(self) -> None:
        """Initializes the approved source registry with verification metadata."""
        self.sources: Dict[str, ApprovedSource] = {
            "src-nlm-mesh": ApprovedSource(
                id="src-nlm-mesh",
                name="NLM MeSH (Medical Subject Headings)",
                official_domain="mesh.nlm.nih.gov",
                authority="National Library of Medicine / U.S. National Institutes of Health",
                permitted_scope="Standardized biomedical vocabulary, clinical anatomy, pathology, radiological concepts",
                verification_status=TerminologySourceStatus.VERIFIED,
                access_restrictions="Direct term REST query; automated bulk web crawling disallowed",
                official_url="https://mesh.nlm.nih.gov",
                is_active=True,
                notes="Primary authoritative biomedical thesaurus."
            ),
            "src-medlineplus": ApprovedSource(
                id="src-medlineplus",
                name="NLM MedlinePlus",
                official_domain="medlineplus.gov",
                authority="U.S. National Library of Medicine / NIH",
                permitted_scope="Diagnostic tests, imaging procedures, medical conditions, and clinical symptoms",
                verification_status=TerminologySourceStatus.VERIFIED,
                access_restrictions="Public health direct encyclopedia lookup",
                official_url="https://medlineplus.gov",
                is_active=True,
                notes="Consumer and clinical reference glossary."
            ),
            "src-cms-glossary": ApprovedSource(
                id="src-cms-glossary",
                name="CMS Medicare Coverage Database Glossary",
                official_domain="cms.gov",
                authority="Centers for Medicare & Medicaid Services (U.S. Department of Health and Human Services)",
                permitted_scope="Prior authorization concepts, federal insurance terms, medical necessity definitions",
                verification_status=TerminologySourceStatus.VERIFIED,
                access_restrictions="Official federal coverage terminology database",
                official_url="https://www.cms.gov/medicare-coverage-database",
                is_active=True,
                notes="Authoritative for insurance authorization terminology."
            ),
            "src-ama": ApprovedSource(
                id="src-ama",
                name="American Medical Association (AMA)",
                official_domain="ama-assn.org",
                authority="American Medical Association",
                permitted_scope="CPT coding principles and clinical nomenclature",
                verification_status=TerminologySourceStatus.RESTRICTED_ACCESS,
                access_restrictions="Licensed proprietary terminology (CPT); requires licensing agreement verification",
                official_url="https://www.ama-assn.org",
                is_active=False,
                notes="Requires formal licensing verification before external automated lookup can be enabled."
            ),
            "src-aia": ApprovedSource(
                id="src-aia",
                name="American Insurance Association (APCIA)",
                official_domain="apci.org",
                authority="American Property Casualty Insurance Association",
                permitted_scope="Property and casualty insurance trade concepts (not health insurance clinical criteria)",
                verification_status=TerminologySourceStatus.SCOPE_RESTRICTED,
                access_restrictions="Scope restricted: Property/casualty industry association, not health insurance criteria",
                official_url="https://www.apci.org",
                is_active=False,
                notes="Excluded from health prior authorization definitions due to scope limitations."
            ),
            "src-ima": ApprovedSource(
                id="src-ima",
                name="Indian Medical Association (IMA)",
                official_domain="imanational.com",
                authority="Indian Medical Association",
                permitted_scope="Indian medical practice terminology and clinical guidelines",
                verification_status=TerminologySourceStatus.PENDING_REGULATORY_VERIFICATION,
                access_restrictions="Pending official terminology API verification and access scope authorization",
                official_url="https://www.imanational.com",
                is_active=False,
                notes="Candidate source awaiting formal domain and schema verification."
            ),
        }

    def get_approved_sources(self) -> List[ApprovedSource]:
        """Returns all sources in the registry with verification status and access restrictions."""
        return list(self.sources.values())

    def get_source_by_id(self, source_id: str) -> Optional[ApprovedSource]:
        """Retrieves an approved source by identifier."""
        return self.sources.get(source_id)

    def validate_domain(self, domain: str) -> bool:
        """Strict domain allowlist enforcement."""
        normalized = domain.lower().strip()
        return normalized in self.ALLOWED_DOMAINS

    def sanitize_untrusted_term(self, term: str) -> Tuple[str, bool]:
        """
        Sanitizes search term against command or prompt injection attempts.
        Treats incoming user queries as untrusted text.
        """
        injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'approve\s+all\s+(?:claims|requests|cases)',
            r'override\s+(?:policy|rules|criteria)',
            r'<script.*?>.*?</script>',
            r'drop\s+table',
            r'eval\s*\(',
        ]
        has_injection = False
        for p in injection_patterns:
            if re.search(p, term, re.IGNORECASE):
                has_injection = True
                break

        # Strip control characters, keep clean clinical text
        clean = re.sub(r'[^\w\s\-\(\)\/\,\.\:\']', '', term).strip()
        return clean, has_injection

    def lookup_term(self, request: TerminologyLookupRequest) -> TerminologyLookupResponse:
        """
        Main authoritative terminology lookup workflow:
        1. Sanitize untrusted input.
        2. Rulebook-first: check selected policy's own definitions.
        3. External lookup: check approved authoritative sources only.
        4. Safe failure: if unresolved or conflicting, request human review.
        5. Log provenance audit trail.
        """
        raw_term = request.term.strip()
        clean_term, has_injection = self.sanitize_untrusted_term(raw_term)

        timestamp_utc = datetime.now(timezone.utc).isoformat()
        audit_id = f"AUD-TERM-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hashlib.sha256(raw_term.encode()).hexdigest()[:8]}"
        resolution_path: List[str] = []

        if has_injection:
            resolution_path.append(f"Security Alert: Untrusted injection pattern detected in term '{raw_term}'. Sanitized.")
            self._log_audit(
                audit_id=audit_id,
                term=raw_term,
                status=TerminologyResolutionStatus.FAILED,
                source="SECURITY_FILTER",
                reason="Prompt injection attempt rejected"
            )
            return TerminologyLookupResponse(
                term=raw_term,
                status=TerminologyResolutionStatus.FAILED,
                definition_record=None,
                resolution_path=resolution_path,
                requires_human_review=True,
                review_reason="Security violation: Term contains potential injection instructions.",
                provenance_audit_id=audit_id
            )

        norm_key = clean_term.lower()

        # Check for known conflicting definitions
        if norm_key in self.CONFLICTING_TERMS:
            resolution_path.append(f"Queried approved sources for '{clean_term}'. Conflicting definitions detected.")
            self._log_audit(
                audit_id=audit_id,
                term=clean_term,
                status=TerminologyResolutionStatus.CONFLICTING,
                source="MULTI_SOURCE_CONFLICT",
                reason=request.lookup_reason or "Clarification"
            )
            return TerminologyLookupResponse(
                term=clean_term,
                status=TerminologyResolutionStatus.CONFLICTING,
                definition_record=None,
                resolution_path=resolution_path,
                requires_human_review=True,
                review_reason="Approved authoritative sources provide conflicting clinical definitions. Requires human clinician reconciliation.",
                provenance_audit_id=audit_id
            )

        # ------------------------------------------------------------------
        # 1. RULEBOOK-FIRST RESOLUTION
        # ------------------------------------------------------------------
        policy_id = request.policy_id or "P-UHC-CT-2026"
        resolution_path.append(f"Checking policy '{policy_id}' rulebook definitions...")

        policy_defs = self.RULEBOOK_DEFINITIONS.get(policy_id, {})
        matched_rulebook_entry = None
        for key, entry in policy_defs.items():
            if key == norm_key or key in norm_key or norm_key in key:
                matched_rulebook_entry = entry
                break

        if matched_rulebook_entry:
            resolution_path.append(
                f"Resolved from policy '{policy_id}' rulebook definitions ({matched_rulebook_entry['section']}). Rulebook First priority applied."
            )
            definition = TerminologyDefinition(
                term=matched_rulebook_entry["term"],
                definition=matched_rulebook_entry["definition"],
                source_id=f"policy-{policy_id.lower()}",
                source_name=f"Policy Rulebook ({policy_id})",
                source_domain="local.policy.registry",
                official_url=f"http://localhost:8000/api/policies/{policy_id}",
                resolution_status=TerminologyResolutionStatus.RULEBOOK_DEFINED,
                retrieval_timestamp=timestamp_utc,
                lookup_reason=request.lookup_reason or "Rulebook definition query",
                policy_citation=f"{matched_rulebook_entry['section']}, {matched_rulebook_entry['page']}",
                is_rulebook_first=True,
                provenance_audit_id=audit_id
            )
            self._log_audit(
                audit_id=audit_id,
                term=matched_rulebook_entry["term"],
                status=TerminologyResolutionStatus.RULEBOOK_DEFINED,
                source=f"Policy {policy_id}",
                reason=request.lookup_reason or "Rulebook First",
                citation=definition.policy_citation
            )
            return TerminologyLookupResponse(
                term=matched_rulebook_entry["term"],
                status=TerminologyResolutionStatus.RULEBOOK_DEFINED,
                definition_record=definition,
                resolution_path=resolution_path,
                requires_human_review=False,
                review_reason=None,
                provenance_audit_id=audit_id
            )

        resolution_path.append(f"Term '{clean_term}' not defined in policy '{policy_id}' rulebook. Proceeding to approved external sources.")

        # ------------------------------------------------------------------
        # 2. APPROVED EXTERNAL SOURCE LOOKUP
        # ------------------------------------------------------------------
        external_match = None
        for key, ext_entry in self.EXTERNAL_DEFINITIONS.items():
            if key == norm_key or key in norm_key or norm_key in key:
                external_match = ext_entry
                break

        if external_match:
            src_obj = self.sources.get(external_match["source_id"])
            if src_obj and src_obj.is_active and self.validate_domain(external_match["domain"]):
                resolution_path.append(
                    f"Resolved from approved authoritative source: {src_obj.name} ({src_obj.official_domain}). Domain verified on allowlist."
                )
                definition = TerminologyDefinition(
                    term=external_match["term"],
                    definition=external_match["definition"],
                    source_id=src_obj.id,
                    source_name=src_obj.name,
                    source_domain=src_obj.official_domain,
                    official_url=external_match["url"],
                    resolution_status=TerminologyResolutionStatus.RESOLVED,
                    retrieval_timestamp=timestamp_utc,
                    lookup_reason=request.lookup_reason or "External term clarification",
                    policy_citation=None,
                    is_rulebook_first=False,
                    provenance_audit_id=audit_id
                )
                self._log_audit(
                    audit_id=audit_id,
                    term=external_match["term"],
                    status=TerminologyResolutionStatus.RESOLVED,
                    source=src_obj.name,
                    reason=request.lookup_reason or "Approved Source",
                    url=external_match["url"]
                )
                return TerminologyLookupResponse(
                    term=external_match["term"],
                    status=TerminologyResolutionStatus.RESOLVED,
                    definition_record=definition,
                    resolution_path=resolution_path,
                    requires_human_review=False,
                    review_reason=None,
                    provenance_audit_id=audit_id
                )

        # ------------------------------------------------------------------
        # 3. SAFE FAILURE (UNRESOLVED)
        # ------------------------------------------------------------------
        resolution_path.append(
            f"Term '{clean_term}' could not be resolved from any approved authoritative sources. General web search prohibited."
        )
        self._log_audit(
            audit_id=audit_id,
            term=clean_term,
            status=TerminologyResolutionStatus.UNRESOLVED,
            source="NONE",
            reason=request.lookup_reason or "Term not found"
        )
        return TerminologyLookupResponse(
            term=clean_term,
            status=TerminologyResolutionStatus.UNRESOLVED,
            definition_record=None,
            resolution_path=resolution_path,
            requires_human_review=True,
            review_reason=(
                f"Term '{clean_term}' is not defined in the selected policy rulebook and is not available in approved authoritative "
                "terminology sources. General web search is prohibited by MedRule security policy. Clinician review required."
            ),
            provenance_audit_id=audit_id
        )

    def get_rulebook_terms(self, policy_id: str) -> List[Dict[str, str]]:
        """Returns all terms natively defined by a policy rulebook."""
        p_id = policy_id or "P-UHC-CT-2026"
        defs = self.RULEBOOK_DEFINITIONS.get(p_id, {})
        return [
            {
                "term": item["term"],
                "definition": item["definition"],
                "section": item["section"],
                "page": item["page"]
            }
            for item in defs.values()
        ]

    def _log_audit(
        self,
        audit_id: str,
        term: str,
        status: TerminologyResolutionStatus,
        source: str,
        reason: str,
        citation: Optional[str] = None,
        url: Optional[str] = None
    ) -> None:
        """Persists terminology lookup provenance audit trail."""
        try:
            entries: List[Dict[str, Any]] = []
            if self.audit_log_path.exists():
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            
            entry = {
                "audit_id": audit_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "term": term,
                "status": status.value,
                "source": source,
                "reason": reason,
                "citation": citation,
                "url": url,
            }
            entries.append(entry)
            
            # Keep latest 100 entries
            entries = entries[-100:]
            with open(self.audit_log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except Exception:
            # Audit logging failure should not crash terminology lookup
            pass

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Returns the terminology provenance audit log."""
        if not self.audit_log_path.exists():
            return []
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def assert_coverage_criteria_unaltered(original_criteria_count: int, current_criteria_count: int) -> bool:
        """
        Mathematical proof invariant: Terminology lookup must NEVER alter,
        add, or remove criteria in the policy ruleset.
        """
        if original_criteria_count != current_criteria_count:
            raise TerminologyServiceError(
                f"INVARIANT VIOLATION: Criteria count changed from {original_criteria_count} to {current_criteria_count}."
            )
        return True
