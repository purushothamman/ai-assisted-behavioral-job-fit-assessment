"""
tests/test_schemas.py
Unit tests for Pydantic schema validation logic.
No DB or auth required — pure Python validation tests.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.jobs import JobCreate, JobStatus, JobUpdate


class TestJobCreate:
    def test_valid_job(self):
        j = JobCreate(
            title="Data Engineer",
            description="Build data pipelines for the organisation.",
        )
        assert j.title == "Data Engineer"
        assert j.status if hasattr(j, "status") else True  # status not on create

    def test_title_stripped(self):
        j = JobCreate(title="  ML Engineer  ", description="Some description here.")
        assert j.title == "ML Engineer"

    def test_title_too_short(self):
        with pytest.raises(ValidationError):
            JobCreate(title="X", description="Some description here.")

    def test_description_too_short(self):
        with pytest.raises(ValidationError):
            JobCreate(title="Valid Title", description="Short")

    def test_blank_title_raises(self):
        with pytest.raises(ValidationError):
            JobCreate(title="   ", description="Some valid description text.")


class TestJobUpdate:
    def test_all_none_is_valid(self):
        """An empty patch payload is allowed — nothing is changed."""
        u = JobUpdate()
        assert u.model_dump(exclude_none=True) == {}

    def test_status_enum_valid(self):
        u = JobUpdate(status=JobStatus.ACTIVE)
        assert u.status == "active"

    def test_status_enum_invalid(self):
        with pytest.raises(ValidationError):
            JobUpdate(status="unknown_status")
