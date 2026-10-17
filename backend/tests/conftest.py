"""
tests/conftest.py
Shared pytest fixtures.

Strategy
--------
1. Load .env.test BEFORE any app module is imported so pydantic-settings
   can find the required SUPABASE_* fields (stub values — no real DB).
2. Patch the Supabase client factory so no real network calls are made.
3. Override auth dependencies (get_current_user, require_recruiter, require_admin)
   to bypass JWT validation while testing role-based access.
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
from app.main import app                                                        # noqa: E402
from app.core.security import get_current_user, require_admin, require_recruiter # noqa: E402

# ── Mock auth users ───────────────────────────────────────────────────────────
MOCK_RECRUITER = {
    "id": "11111111-1111-1111-1111-111111111111",
    "email": "recruiter@test.com",
    "role": "recruiter",
}

MOCK_ADMIN = {
    "id": "99999999-9999-9999-9999-999999999999",
    "email": "admin@test.com",
    "role": "admin",
}


def override_get_current_user():
    return MOCK_RECRUITER


def override_require_recruiter():
    return MOCK_RECRUITER


def override_require_admin():
    return MOCK_ADMIN


# ── 3. Supabase admin client mock (shared across the session) ─────────────────
def _make_mock_db() -> MagicMock:
    """
    Returns a MagicMock that mimics the supabase-py client well enough
    for the tests that don't explicitly patch services.
    """
    mock = MagicMock()
    mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    mock.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
    return mock


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    TestClient with recruiter authentication override.
    get_current_user returns MOCK_RECRUITER (role='recruiter').
    require_recruiter succeeds; require_admin fails with 403 Forbidden.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_recruiter] = override_require_recruiter

    with patch("app.db.client.get_supabase_admin", return_value=_make_mock_db()), \
         patch("app.db.client.get_supabase_anon",  return_value=_make_mock_db()):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def admin_client() -> TestClient:
    """
    TestClient with administrator authentication override.
    get_current_user, require_recruiter, and require_admin all succeed with MOCK_ADMIN.
    """
    app.dependency_overrides[get_current_user] = override_require_admin
    app.dependency_overrides[require_admin] = override_require_admin
    app.dependency_overrides[require_recruiter] = override_require_admin

    with patch("app.db.client.get_supabase_admin", return_value=_make_mock_db()), \
         patch("app.db.client.get_supabase_anon",  return_value=_make_mock_db()):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides[require_recruiter] = override_require_recruiter
