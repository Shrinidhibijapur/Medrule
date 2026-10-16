import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.models.policy import (
    Policy,
    PolicyLifecycleStatus,
    PolicySection,
    PolicySearchResult,
    ExtractionQualityReport,
)

class PolicyRegistryError(Exception):
    pass

class DuplicatePolicyError(PolicyRegistryError):
    pass

class VersionConflictError(PolicyRegistryError):
    pass

class PolicyRegistryService:
    def __init__(self, data_dir: Optional[Path] = None, storage_dir: Optional[Path] = None):
        root = Path(__file__).resolve().parent.parent.parent.parent
        self.data_dir = data_dir or (root / "data" / "policies")
        self.storage_dir = storage_dir or (root / "backend" / "storage" / "policies")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._policies_cache: Dict[str, Policy] = {}
        self.load_all_policies()

    def load_all_policies(self):
        """Loads all policy JSON records from data directory into memory."""
        self._policies_cache.clear()
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Support both old and expanded schemas
                    if "lifecycle_status" not in data:
                        data["lifecycle_status"] = PolicyLifecycleStatus.NEEDS_REVIEW
                    policy = Policy(**data)
                    self._policies_cache[policy.id] = policy
            except Exception as e:
                print(f"Warning: Failed to load policy file {file.name}: {e}")

    def get_all(self, status: Optional[PolicyLifecycleStatus] = None) -> List[Policy]:
        policies = list(self._policies_cache.values())
        if status:
            return [p for p in policies if p.lifecycle_status == status]
        return policies

    def get_by_id(self, policy_id: str) -> Optional[Policy]:
        return self._policies_cache.get(policy_id)

    def register_policy_upload(
        self,
        file_bytes: bytes,
        filename: str,
        insurer: str,
        policy_name: str,
        version: str,
        procedure_type: str,
        procedure_full_name: str,
        effective_date: str,
        cpt_codes: List[str],
        plan: str,
        sections: List[PolicySection],
        quality_report: ExtractionQualityReport,
        checksum: str
    ) -> Policy:
        """
        Registers a newly uploaded policy PDF, ensuring version conflict and duplicate prevention.
        """
        # Formulate canonical policy ID
        # e.g. POL-UHC-CT-2026-1
        sanitized_ins = "".join(c for c in insurer if c.isalnum()).upper()[:4]
        sanitized_proc = "".join(c for c in procedure_type if c.isalnum()).upper()[:3]
        sanitized_ver = version.replace(".", "-")
        policy_id = f"POL-{sanitized_ins}-{sanitized_proc}-{sanitized_ver}"

        # 1. Check for duplicates or version collisions
        for existing in self._policies_cache.values():
            if existing.insurer.lower() == insurer.lower() and existing.procedure_type.lower() == procedure_type.lower():
                # Check version conflict
                if existing.version == version:
                    if existing.sha256_checksum == checksum:
                        raise DuplicatePolicyError(
                            f"Policy '{policy_name}' version {version} is already registered with identical checksum."
                        )
                    else:
                        raise VersionConflictError(
                            f"Policy '{policy_name}' version {version} already exists with a different file. "
                            f"Silent overwrites are prohibited. Please increment the version number."
                        )

        # 2. Store original file safely
        stored_filename = f"{checksum[:12]}_{filename}"
        storage_path = self.storage_dir / stored_filename
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

        # 3. Create Policy instance in NEEDS_REVIEW status
        policy = Policy(
            id=policy_id,
            policy_id=f"POL-{sanitized_ins}-{sanitized_proc}",
            insurer=insurer,
            policy_name=policy_name,
            plan=plan,
            version=version,
            procedure_type=procedure_type,
            procedure_full_name=procedure_full_name,
            cpt_codes=cpt_codes,
            effective_date=effective_date,
            upload_date=now_str[:10],
            sha256_checksum=checksum,
            original_filename=filename,
            storage_path=str(storage_path),
            total_pages=quality_report.total_pages,
            lifecycle_status=PolicyLifecycleStatus.NEEDS_REVIEW,
            criteria=[],  # Criteria are encoded in Phase 2
            sections=sections,
            extraction_report=quality_report,
            created_at=now_str,
            updated_at=now_str
        )

        # Save to disk
        json_file = self.data_dir / f"{policy_id.lower()}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(policy.model_dump(), f, indent=2)

        self._policies_cache[policy.id] = policy
        return policy

    def update_status(self, policy_id: str, new_status: PolicyLifecycleStatus) -> Policy:
        """Transitions policy lifecycle status."""
        policy = self.get_by_id(policy_id)
        if not policy:
            raise PolicyRegistryError(f"Policy '{policy_id}' not found.")

        policy.lifecycle_status = new_status
        policy.updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

        # Persist update
        json_file = self.data_dir / f"{policy.id.lower()}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(policy.model_dump(), f, indent=2)

        return policy

    def search_sections(
        self,
        query: str,
        approved_only: bool = True,
        insurer: Optional[str] = None
    ) -> List[PolicySearchResult]:
        """
        Searches extracted text sections across policies.
        Restricted to APPROVED_FOR_USE policies by default.
        """
        query_lower = query.lower()
        results: List[PolicySearchResult] = []

        for policy in self._policies_cache.values():
            if approved_only and policy.lifecycle_status != PolicyLifecycleStatus.APPROVED_FOR_USE:
                continue

            if insurer and policy.insurer.lower() != insurer.lower():
                continue

            for sec in policy.sections:
                content_lower = sec.content.lower()
                heading_lower = sec.heading.lower()

                if query_lower in content_lower or query_lower in heading_lower:
                    # Extract snippet surrounding match
                    start_idx = content_lower.find(query_lower)
                    if start_idx != -1:
                        snippet_start = max(0, start_idx - 50)
                        snippet_end = min(len(sec.content), start_idx + len(query) + 80)
                        snippet = ("..." if snippet_start > 0 else "") + sec.content[snippet_start:snippet_end] + "..."
                    else:
                        snippet = sec.content[:120] + "..."

                    results.append(PolicySearchResult(
                        policy_id=policy.id,
                        policy_name=policy.policy_name,
                        version=policy.version,
                        insurer=policy.insurer,
                        section_id=sec.id,
                        section_number=sec.section_number,
                        heading=sec.heading,
                        page_number=sec.page_number,
                        matched_snippet=snippet,
                        lifecycle_status=policy.lifecycle_status
                    ))

        return results
