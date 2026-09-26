"""
tests/test_health.py
Tests for the /health and /health/db endpoints.
These run without auth and without a real Supabase connection.
"""
from unittest.mock import MagicMock, patch


def test_health_ok(client):
    """GET /health should always return 200 with status=ok."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_health_db_connected(client):
    """
    GET /health/db should return status=ok when Supabase responds.
    We mock the admin client to avoid a real network call.
    """
    mock_result = MagicMock()
    mock_result.data = [{"id": "abc"}]

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_result

    with patch("app.api.health.get_supabase_admin", return_value=mock_db):
        response = client.get("/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "connected"


def test_health_db_unreachable(client):
    """
    GET /health/db should return status=error (not 500) when DB is unreachable.
    """
    with patch("app.api.health.get_supabase_admin", side_effect=Exception("connection refused")):
        response = client.get("/health/db")

    assert response.status_code == 200  # endpoint returns 200 with error body
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "unreachable"
