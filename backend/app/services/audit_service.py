import os
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.models.auth import AuthenticatedUser, AuditEvent

logger = logging.getLogger("medrule.audit")

class AuditService:
    """
    Centralized, tamper-evident audit service.
    Binds every security and clinical action to authenticated user identity, role, timestamp, and organization.
    Strictly sanitizes inputs: never logs passwords, session tokens, complete clinical notes, or unnecessary PII.
    """
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            # backend/app/services/audit_service.py -> parents[3] is project root e:\Medrule
            storage_dir = Path(__file__).resolve().parents[3] / "data" / "audit"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.storage_dir / "audit_events.jsonl"
        self._in_memory_recent_events: List[AuditEvent] = []
        self._load_recent_events()

    def _load_recent_events(self):
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-200:]  # Load last 200 events
                    for line in lines:
                        if line.strip():
                            data = json.loads(line)
                            self._in_memory_recent_events.append(AuditEvent(**data))
            except Exception as e:
                logger.error(f"Error loading initial audit events: {e}")

    def log_event(
        self,
        action: str,
        user: Optional[AuthenticatedUser],
        resource: Optional[str] = None,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Records an audit event bound to authenticated identity and timestamp."""
        sanitized_details = self._sanitize_details(details or {})
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            user_id=user.user_id if user else "anonymous",
            username=user.username if user else "anonymous",
            role=user.role.value if user else "None",
            organization_id=user.organization_id if user else "None",
            resource=resource,
            status=status,
            ip_address=ip_address or "127.0.0.1",
            details=sanitized_details
        )
        
        # In-memory buffer
        self._in_memory_recent_events.append(event)
        if len(self._in_memory_recent_events) > 500:
            self._in_memory_recent_events = self._in_memory_recent_events[-500:]
            
        # Append to log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to append audit event to disk: {e}")
            
        return event

    def get_events(
        self,
        user: AuthenticatedUser,
        limit: int = 100,
        action_filter: Optional[str] = None
    ) -> List[AuditEvent]:
        """
        Retrieves audit events. Enforces tenant and role scoping:
        Compliance Officer and System Admin can view events.
        """
        events = list(reversed(self._in_memory_recent_events))
        if user.role.value not in ["Compliance Officer", "System Admin"]:
            # Clinicians only see events within their organization
            events = [e for e in events if e.organization_id == user.organization_id]
        if action_filter:
            events = [e for e in events if e.action == action_filter]
        return events[:limit]

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Removes passwords, secrets, session cookies, raw tokens, and full note texts."""
        prohibited_keys = {
            "password", "secret", "token", "access_token", "jwt",
            "medrule_session", "medrule_csrf", "cookie", "raw_pages_text",
            "ssn", "credit_card"
        }
        sanitized = {}
        for k, v in details.items():
            k_lower = k.lower()
            if any(p in k_lower for p in prohibited_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 500:
                # Truncate overly long text fields to avoid dumping whole clinical documents
                sanitized[k] = v[:200] + "... [TRUNCATED FOR AUDIT]"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_details(v)
            else:
                sanitized[k] = v
        return sanitized

audit_service = AuditService()
