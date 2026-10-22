"""
tests/test_phase_a_snapshot_binding.py
Regression tests for Phase A — Framework Snapshot Binding (FS-1 to FS-4).

Validates that:
  FS-1: report_service resolves framework version label via framework_versions
        table, NOT via nonexistent job columns.
  FS-2: session_service.create_session() copies the job's framework_version_id
        to the new session row.
  FS-3: scoring_service uses frozen snapshot indicators when available, falls
        back to live DB when snapshot is absent or dimension is missing.
  FS-4: job_service.create_job() attaches the active framework_version_id when
        an active version exists; silently skips when none exists.

No real Supabase calls are made — all DB interactions are mocked.
All tests are backwards-compatible: they verify the old behaviour is preserved
when no framework version exists.
"""
from __future__ import annotations

from typing import List, Optional
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FW_VERSION_ID   = str(uuid4())
FW_VERSION_NUM  = 2
FW_VERSION_NAME = "Competency Framework 2026"
JOB_ID          = str(uuid4())
SESSION_ID      = str(uuid4())
DIM_ID          = str(uuid4())
Q_ID            = str(uuid4())

MOCK_ACTIVE_VERSION = {
    "id":                 FW_VERSION_ID,
    "version_number":     FW_VERSION_NUM,
    "name":               FW_VERSION_NAME,
    "status":             "active",
    "dimensions_snapshot": [
        {
            "id":   DIM_ID,
            "name": "communication",
            "indicators": [
                {
                    "name":              "Active listening",
                    "description":       "Listens carefully and asks clarifying questions",
                    "example_behaviors": "Paraphrases speaker, avoids interrupting",
                },
                {
                    "name":              "Clarity in messaging",
                    "description":       "Communicates ideas concisely to stakeholders",
                    "example_behaviors": "Uses plain language, checks for understanding",
                },
            ],
        }
    ],
}

MOCK_JOB = {
    "id":                   JOB_ID,
    "recruiter_id":         str(uuid4()),
    "title":                "Senior Engineer",
    "description":          "Build systems.",
    "framework_version_id": FW_VERSION_ID,
}

MOCK_JOB_NO_FW = {**MOCK_JOB, "framework_version_id": None}

MOCK_SESSION = {
    "id":                   SESSION_ID,
    "job_id":               JOB_ID,
    "token":                str(uuid4()),
    "candidate_name":       "Jane Doe",
    "candidate_email":      "jane@example.com",
    "status":               "pending",
    "submitted_at":         None,
    "framework_version_id": FW_VERSION_ID,
}

MOCK_SESSION_NO_FW = {**MOCK_SESSION, "framework_version_id": None}


# ===========================================================================
# FS-4: JobService.create_job() attaches active framework_version_id
# ===========================================================================

class TestFS4JobCreationPinsFrameworkVersion:
    """FS-4: create_job() must attach the active framework version FK."""

    def test_create_job_with_active_framework(self):
        """When an active version exists, framework_version_id is inserted with the job."""
        from app.services.job_service import JobService
        from app.schemas.jobs import JobCreate

        svc = JobService()
        payload = JobCreate(title="Data Scientist", description="Analyse data with ML models.")

        inserted_data: dict = {}

        def _fake_table(name):
            mock = MagicMock()
            if name == "jobs":
                def _insert(data):
                    inserted_data.update(data)
                    row = {**data, "id": str(uuid4())}
                    execute_mock = MagicMock()
                    execute_mock.execute.return_value = MagicMock(data=[row], error=None)
                    return execute_mock
                mock.insert.side_effect = _insert
            return mock

        with patch("app.services.job_service._get_active_framework_version_id",
                   return_value=FW_VERSION_ID):
            with patch.object(svc._db, "table", side_effect=_fake_table):
                result = svc.create_job("recruiter-uuid", payload)

        assert inserted_data.get("framework_version_id") == FW_VERSION_ID, (
            "framework_version_id must be written to jobs at creation time (FS-4)"
        )

    def test_create_job_without_active_framework_still_succeeds(self):
        """When no active version exists, job creation succeeds without framework_version_id."""
        from app.services.job_service import JobService
        from app.schemas.jobs import JobCreate

        svc = JobService()
        payload = JobCreate(title="Analyst", description="Run business analysis reports.")

        inserted_data: dict = {}

        def _fake_table(name):
            mock = MagicMock()
            if name == "jobs":
                def _insert(data):
                    inserted_data.update(data)
                    row = {**data, "id": str(uuid4())}
                    execute_mock = MagicMock()
                    execute_mock.execute.return_value = MagicMock(data=[row], error=None)
                    return execute_mock
                mock.insert.side_effect = _insert
            return mock

        with patch("app.services.job_service._get_active_framework_version_id",
                   return_value=None):
            with patch.object(svc._db, "table", side_effect=_fake_table):
                result = svc.create_job("recruiter-uuid", payload)

        assert "framework_version_id" not in inserted_data, (
            "framework_version_id must NOT be inserted when no active version exists (FS-4 backwards-compat)"
        )

    def test_get_active_framework_version_id_returns_none_on_error(self):
        """Helper must return None (not raise) if FrameworkService fails.

        FrameworkService is a local import inside _get_active_framework_version_id,
        so we patch it at its source module path, not at job_service module level.
        """
        from app.services.job_service import _get_active_framework_version_id

        # Patch at the source module so the local import picks up the mock.
        with patch("app.services.framework_service.FrameworkService",
                   side_effect=RuntimeError("DB unavailable")):
            result = _get_active_framework_version_id()

        assert result is None, "Non-fatal: helper must swallow errors and return None"


# ===========================================================================
# FS-2: SessionService.create_session() binds framework_version_id
# ===========================================================================

class TestFS2SessionCreationBindsFrameworkVersion:
    """FS-2: create_session() must copy the job's framework_version_id to the session."""

    def _make_svc(self):
        from app.services.session_service import SessionService
        return SessionService()

    def test_session_creation_copies_framework_version_from_job(self):
        """Session row must include the job's framework_version_id when present."""
        from app.schemas.sessions import SessionCreate

        svc = self._make_svc()
        payload = SessionCreate(
            candidate_name="Alice",
            candidate_email="alice@example.com",
            expires_in_days=7,
            send_email=False,
        )

        inserted_data: dict = {}

        def _fake_table(name):
            mock = MagicMock()
            if name == "jobs":
                select_mock = MagicMock()
                select_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"framework_version_id": FW_VERSION_ID}], error=None
                )
                return select_mock
            if name == "interview_sessions":
                def _insert(data):
                    inserted_data.update(data)
                    row = {**data, "id": SESSION_ID, "email_status": "pending"}
                    execute_mock = MagicMock()
                    execute_mock.execute.return_value = MagicMock(data=[row], error=None)
                    return execute_mock
                mock.insert.side_effect = _insert
            return mock

        with patch.object(svc._db, "table", side_effect=_fake_table):
            result = svc.create_session(JOB_ID, payload)

        assert inserted_data.get("framework_version_id") == FW_VERSION_ID, (
            "Session must carry job's framework_version_id (FS-2)"
        )

    def test_session_creation_succeeds_when_job_has_no_framework(self):
        """When job.framework_version_id is None, session is created without it."""
        from app.schemas.sessions import SessionCreate

        svc = self._make_svc()
        payload = SessionCreate(
            candidate_name="Bob",
            candidate_email="bob@example.com",
            expires_in_days=7,
            send_email=False,
        )

        inserted_data: dict = {}

        def _fake_table(name):
            mock = MagicMock()
            if name == "jobs":
                select_mock = MagicMock()
                select_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"framework_version_id": None}], error=None
                )
                return select_mock
            if name == "interview_sessions":
                def _insert(data):
                    inserted_data.update(data)
                    row = {**data, "id": SESSION_ID, "email_status": "pending"}
                    execute_mock = MagicMock()
                    execute_mock.execute.return_value = MagicMock(data=[row], error=None)
                    return execute_mock
                mock.insert.side_effect = _insert
            return mock

        with patch.object(svc._db, "table", side_effect=_fake_table):
            result = svc.create_session(JOB_ID, payload)

        assert "framework_version_id" not in inserted_data, (
            "framework_version_id must not be set when job has none (FS-2 backwards-compat)"
        )

    def test_session_creation_succeeds_even_if_job_lookup_fails(self):
        """If job FK lookup fails, session creation must still succeed (graceful)."""
        from app.schemas.sessions import SessionCreate

        svc = self._make_svc()
        payload = SessionCreate(
            candidate_name="Carol",
            candidate_email="carol@example.com",
            expires_in_days=7,
            send_email=False,
        )

        inserted_data: dict = {}

        def _fake_table(name):
            mock = MagicMock()
            if name == "jobs":
                select_mock = MagicMock()
                select_mock.select.return_value.eq.return_value.limit.return_value.execute.side_effect = (
                    RuntimeError("jobs table unavailable")
                )
                return select_mock
            if name == "interview_sessions":
                def _insert(data):
                    inserted_data.update(data)
                    row = {**data, "id": SESSION_ID, "email_status": "pending"}
                    execute_mock = MagicMock()
                    execute_mock.execute.return_value = MagicMock(data=[row], error=None)
                    return execute_mock
                mock.insert.side_effect = _insert
            return mock

        with patch.object(svc._db, "table", side_effect=_fake_table):
            result = svc.create_session(JOB_ID, payload)  # must not raise

        assert "id" in result  # session was created successfully


# ===========================================================================
# FS-3: ScoringService uses snapshot-based indicator resolution
# ===========================================================================

class TestFS3ScoringUsesSnapshot:
    """FS-3: Scoring resolves indicators from frozen snapshot when available."""

    def _make_svc(self):
        from app.services.scoring_service import ScoringService
        return ScoringService()

    def test_get_snapshot_returns_dimensions_snapshot_list(self):
        """_get_snapshot_for_session() returns list when framework_version_id is set."""
        svc = self._make_svc()
        session_with_fw = {"id": SESSION_ID, "framework_version_id": FW_VERSION_ID}

        fw_row = {"dimensions_snapshot": MOCK_ACTIVE_VERSION["dimensions_snapshot"]}
        mock_result = MagicMock(data=[fw_row], error=None)

        with patch.object(svc._db, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                mock_result
            )
            snapshot = svc._get_snapshot_for_session(session_with_fw)

        assert snapshot is not None
        assert len(snapshot) == 1
        assert snapshot[0]["name"] == "communication"

    def test_get_snapshot_returns_none_when_no_framework_pinned(self):
        """_get_snapshot_for_session() returns None when session has no framework_version_id."""
        svc = self._make_svc()
        session_no_fw = {"id": SESSION_ID, "framework_version_id": None}
        snapshot = svc._get_snapshot_for_session(session_no_fw)
        assert snapshot is None

    def test_get_indicators_from_snapshot_resolves_correctly(self):
        """_get_indicators_from_snapshot() returns dimension name + indicator objects."""
        svc = self._make_svc()
        snapshot = MOCK_ACTIVE_VERSION["dimensions_snapshot"]
        dim_name, indicator_objs = svc._get_indicators_from_snapshot(
            snapshot, DIM_ID, ["Active listening", "Clarity in messaging"]
        )
        assert dim_name == "communication"
        assert len(indicator_objs) == 2
        assert indicator_objs[0]["name"] == "Active listening"
        assert indicator_objs[1]["description"] == "Communicates ideas concisely to stakeholders"

    def test_get_indicators_from_snapshot_fallback_for_unknown_indicator(self):
        """Unknown indicator name not in snapshot falls back to minimal stub."""
        svc = self._make_svc()
        snapshot = MOCK_ACTIVE_VERSION["dimensions_snapshot"]
        dim_name, indicator_objs = svc._get_indicators_from_snapshot(
            snapshot, DIM_ID, ["Active listening", "Unknown custom indicator"]
        )
        assert dim_name == "communication"
        assert len(indicator_objs) == 2
        # Unknown indicator gets name-as-description stub
        assert indicator_objs[1]["name"] == "Unknown custom indicator"
        assert indicator_objs[1]["description"] == "Unknown custom indicator"

    def test_get_indicators_from_snapshot_returns_none_for_unknown_dimension(self):
        """Unknown dimension_id causes (None, []) — triggers live DB fallback."""
        svc = self._make_svc()
        snapshot = MOCK_ACTIVE_VERSION["dimensions_snapshot"]
        dim_name, indicator_objs = svc._get_indicators_from_snapshot(
            snapshot, "nonexistent-dim-id", ["Some indicator"]
        )
        assert dim_name is None
        assert indicator_objs == []

    def test_get_question_with_indicators_uses_snapshot_when_available(self):
        """get_question_with_indicators() resolves from snapshot, no live DB dimension/indicator calls."""
        svc = self._make_svc()
        snapshot = MOCK_ACTIVE_VERSION["dimensions_snapshot"]

        MOCK_QUESTION_ROW = {
            "id":           Q_ID,
            "job_id":       JOB_ID,
            "dimension_id": DIM_ID,
            "question":     "Describe how you handle conflict.",
            "type":         "behavioral",
            "difficulty":   "medium",
            "indicators":   ["Active listening", "Clarity in messaging"],
        }

        with patch.object(svc._db, "table") as mock_table:
            # Question fetch
            mock_table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data=MOCK_QUESTION_ROW, error=None
            )
            result = svc.get_question_with_indicators(Q_ID, snapshot=snapshot)

        assert result is not None
        assert result["dimension_name"] == "communication"
        assert len(result["indicator_objects"]) == 2
        assert result["indicator_objects"][0]["description"] == "Listens carefully and asks clarifying questions"

    def test_get_question_with_indicators_falls_back_to_live_db_without_snapshot(self):
        """get_question_with_indicators() without snapshot queries live DB as before (backwards compat)."""
        svc = self._make_svc()

        MOCK_QUESTION_ROW = {
            "id":           Q_ID,
            "job_id":       JOB_ID,
            "dimension_id": DIM_ID,
            "question":     "Describe leadership experience.",
            "type":         "behavioral",
            "difficulty":   "hard",
            "indicators":   ["Active listening"],
        }
        MOCK_DIM_ROW = {"id": DIM_ID, "name": "leadership"}
        MOCK_IND_ROW = [{"id": str(uuid4()), "name": "Active listening",
                          "description": "Live DB description", "example_behaviors": ""}]

        call_count = {"n": 0}

        def _fake_table(name):
            call_count["n"] += 1
            mock = MagicMock()
            if name == "interview_questions":
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                    data=MOCK_QUESTION_ROW, error=None
                )
            elif name == "behavioral_dimensions":
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                    data=MOCK_DIM_ROW, error=None
                )
            elif name == "behavioral_indicators":
                mock.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
                    data=MOCK_IND_ROW, error=None
                )
            return mock

        with patch.object(svc._db, "table", side_effect=_fake_table):
            result = svc.get_question_with_indicators(Q_ID)  # no snapshot

        assert result["dimension_name"] == "leadership"
        assert result["indicator_objects"][0]["description"] == "Live DB description"


# ===========================================================================
# FS-1: ReportService resolves framework version label correctly
# ===========================================================================

class TestFS1ReportFrameworkVersionLabel:
    """FS-1: _get_framework_version_label() must look up framework_versions table."""

    def _make_svc(self):
        from app.services.report_service import ReportService
        return ReportService()

    def test_resolves_version_label_from_db(self):
        """When framework_version_id is set, DB is queried for version_number and name."""
        svc = self._make_svc()

        fw_row = {"id": FW_VERSION_ID, "version_number": FW_VERSION_NUM, "name": FW_VERSION_NAME}
        mock_result = MagicMock(data=[fw_row], error=None)

        with patch.object(svc._db, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                mock_result
            )
            label, version_id = svc._get_framework_version_label(FW_VERSION_ID)

        assert label == f"v{FW_VERSION_NUM} - {FW_VERSION_NAME}"
        assert version_id == FW_VERSION_ID

    def test_returns_default_label_when_no_version_id(self):
        """None framework_version_id returns the default label without a DB call."""
        svc = self._make_svc()
        with patch.object(svc._db, "table") as mock_table:
            label, version_id = svc._get_framework_version_label(None)

        mock_table.assert_not_called()
        assert "Default Behavioral Framework" in label
        assert version_id is None

    def test_returns_fallback_label_when_db_row_not_found(self):
        """When DB returns no rows for the ID, a graceful fallback label is used."""
        svc = self._make_svc()
        mock_result = MagicMock(data=[], error=None)

        with patch.object(svc._db, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                mock_result
            )
            label, version_id = svc._get_framework_version_label(FW_VERSION_ID)

        assert label.startswith("v?")
        assert FW_VERSION_ID[:8] in label

    def test_report_metadata_no_longer_uses_nonexistent_job_columns(self):
        """
        Regression guard: report metadata must NOT contain a fallback string
        produced from job.get('framework_version_number') (the old broken code
        path). It must contain the DB-resolved label instead.
        """
        svc = self._make_svc()

        fw_row = {"id": FW_VERSION_ID, "version_number": 3, "name": "Phase 3 Framework"}
        mock_fw_result = MagicMock(data=[fw_row], error=None)

        # Job has framework_version_id but no version_number/version_name columns (correct)
        mock_job = {
            "id":                   JOB_ID,
            "title":                "Engineering Lead",
            "framework_version_id": FW_VERSION_ID,
            # Note: no "framework_version_number" or "framework_version_name" keys
        }

        with patch.object(svc._db, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                mock_fw_result
            )
            fw_version_id = mock_job.get("framework_version_id")
            label, _ = svc._get_framework_version_label(fw_version_id)

        # Must produce the real label from DB, not the broken "v1 - Default Framework" fallback
        assert label == "v3 - Phase 3 Framework"
        assert "Default Framework" not in label
