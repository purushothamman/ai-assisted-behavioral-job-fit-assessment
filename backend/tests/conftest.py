"""
tests/conftest.py
Shared pytest fixtures for Phase 1 tests.

Strategy
--------
1. Load .env.test BEFORE any app module is imported so pydantic-settings
   can find the required SUPABASE_* fields (stub values — no real DB).
2. Patch the Supabase client factory so no real network calls are made.
3. Override the `require_recruiter` auth dependency to bypass JWT validation.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# ── 1. Load test env vars BEFORE importing app ────────────────────────────────
_env_test = Path(__file__).parent.parent / ".env.test"
load_dotenv(_env_test, override=True)

# ── 2. Now it's safe to import the app ───────────────────────────────────────
from app.main import app                          # noqa: E402
from app.core.security import require_recruiter   # noqa: E402

# ── Mock auth user ────────────────────────────────────────────────────────────
MOCK_RECRUITER = {
    "id": "11111111-1111-1111-1111-111111111111",
    "email": "recruiter@test.com",
    "role": "recruiter",
}


def override_require_recruiter():
    """Bypass Supabase JWT validation for tests."""
    return MOCK_RECRUITER


# ── 3. Supabase admin client mock (shared across the session) ─────────────────
def _make_mock_db() -> MagicMock:
    """
    Returns a MagicMock that mimics the supabase-py client well enough
    for the tests that don't explicitly patch JobService/ProfileService.
    """
    mock = MagicMock()
    # Default: table().select().execute() returns empty data
    mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    return mock


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    TestClient with:
      - Auth dependency overridden (no real JWT needed)
      - Supabase admin client mocked (no real DB calls on startup)
    """
    app.dependency_overrides[require_recruiter] = override_require_recruiter

    with patch("app.db.client.get_supabase_admin", return_value=_make_mock_db()), \
         patch("app.db.client.get_supabase_anon",  return_value=_make_mock_db()):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
