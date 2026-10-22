"""
services/audit_service.py
Persistent, secure audit logging service for recruiter oversight and administrative governance.

Security & Privacy:
  - Strictly prevents logging sensitive credentials (passwords, JWTs, API keys, tokens).
  - Sanitizes detail dictionaries before persistence.
  - Persists to Supabase audit_logs table with in-memory fallback for test/dev environments.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.db.client import get_supabase_admin

logger = logging.getLogger(__name__)

# Sensitive keys that must NEVER be written to audit logs
FORBIDDEN_DETAIL_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
    "api_key",
    "cookie",
    "credentials",
    "private_key",
    "smtp_password",
    "groq_api_key",
}

# In-memory fallback for testing / pre-migration environments
_FALLBACK_AUDIT_LOGS: List[Dict[str, Any]] = []


def sanitize_audit_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Recursively remove sensitive credentials, tokens, and passwords from audit detail payloads.
    """
    if not details:
        return {}
    sanitized: Dict[str, Any] = {}
    for k, v in details.items():
        key_lower = str(k).lower()
        if any(bad in key_lower for bad in FORBIDDEN_DETAIL_KEYS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_details(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_audit_details(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


class AuditService:
    """Service for recording and querying immutable audit trails."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase audit_logs DB error: %s", result.error)
            raise RuntimeError(str(result.error))

    def log_event(
        self,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        action: str = "",
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        # Keyword aliases
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record an immutable audit log entry.
        Never logs passwords, tokens, or raw secrets.
        """
        res_actor_id = actor_id or user_id
        res_actor_role = actor_role or user_role or "recruiter"
        res_target_type = target_type or entity_type or "system"
        res_target_id = str(target_id or entity_id or "")

        log_id = str(uuid4())
        now_utc = datetime.now(timezone.utc)
        safe_details = sanitize_audit_details(details)

        row = {
            "id":          log_id,
            "actor_id":    res_actor_id,
            "actor_role":  res_actor_role,
            "user_id":     res_actor_id,
            "user_role":   res_actor_role,
            "action":      action,
            "target_type": res_target_type,
            "target_id":   res_target_id,
            "entity_type": res_target_type,
            "entity_id":   res_target_id,
            "details":     safe_details,
            "ip_address":  ip_address,
            "user_agent":  user_agent[:255] if user_agent else None,
            "created_at":  now_utc.isoformat(),
        }

        # Try persisting to Supabase audit_logs table
        try:
            db_row = {
                "id":          log_id,
                "actor_id":    res_actor_id,
                "actor_role":  res_actor_role,
                "action":      action,
                "target_type": res_target_type,
                "target_id":   res_target_id,
                "details":     json.dumps(safe_details),
                "ip_address":  ip_address,
                "user_agent":  user_agent[:255] if user_agent else None,
                "created_at":  now_utc.isoformat(),
            }
            result = self._db.table("audit_logs").insert(db_row).execute()
            self._raise_if_error(result)
        except Exception as exc:
            logger.warning(
                "Could not persist audit log to Supabase table (stored in memory fallback): %s", exc
            )

        _FALLBACK_AUDIT_LOGS.append(row)
        return row

    def get_audit_history(
        self,
        target_type: str,
        target_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit history for a specific entity."""
        return self.list_logs(target_type=target_type, target_id=target_id, limit=limit)

    def list_logs(
        self,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query audit log entries."""
        try:
            query = self._db.table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
            if target_type:
                query = query.eq("target_type", target_type)
            if target_id:
                query = query.eq("target_id", str(target_id))
            if actor_id:
                query = query.eq("actor_id", str(actor_id))

            result = query.execute()
            self._raise_if_error(result)
            rows = result.data or []
            if rows:
                parsed_rows = []
                for r in rows:
                    d = dict(r)
                    if isinstance(d.get("details"), str):
                        try:
                            d["details"] = json.loads(d["details"])
                        except Exception:
                            d["details"] = {}
                    parsed_rows.append(d)
                return parsed_rows
        except Exception as exc:
            logger.warning("Could not query audit logs from Supabase: %s", exc)

        # Fallback to memory
        filtered = _FALLBACK_AUDIT_LOGS
        if target_type:
            filtered = [r for r in filtered if r.get("target_type") == target_type]
        if target_id:
            filtered = [r for r in filtered if r.get("target_id") == str(target_id)]
        if actor_id:
            filtered = [r for r in filtered if r.get("actor_id") == str(actor_id)]
        return sorted(filtered, key=lambda x: x["created_at"], reverse=True)[:limit]
