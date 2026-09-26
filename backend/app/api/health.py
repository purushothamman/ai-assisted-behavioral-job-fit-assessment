"""
api/health.py
Health / readiness endpoints.
No authentication required — used by load balancers and CI pipelines.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.client import get_supabase_admin

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic liveness probe."""
    return {"status": "ok", "version": get_settings().app_version}


@router.get("/health/db")
async def db_health_check():
    """
    Readiness probe — verifies that the Supabase connection is alive.
    Runs a lightweight query against the profiles table.
    """
    try:
        db = get_supabase_admin()
        # A COUNT query is cheap and tests the connection end-to-end.
        result = db.table("profiles").select("id", count="exact").limit(1).execute()
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": "unreachable", "detail": str(exc)}
