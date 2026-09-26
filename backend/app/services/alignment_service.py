"""
services/alignment_service.py
Database interactions and orchestration for Phase 7 Job-Candidate Alignment.

Responsibilities:
  1. Retrieve candidate session information.
  2. Retrieve confirmed behavioral requirements and weights for the job.
  3. Retrieve evaluated candidate response scores from response_scores.
  4. Call the pure deterministic alignment calculator.
  5. Upsert alignment results into the session_alignments table.
  6. Fetch stored alignment records for a single session or all sessions under a job.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.alignment.calculator import calculate_alignment
from app.db.client import get_supabase_admin
from app.services.job_requirement_service import JobRequirementService

logger = logging.getLogger(__name__)


class AlignmentService:
    """Stateless service — one instance per request."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))

    @staticmethod
    def _parse_json_field(value: Any) -> Any:
        """Safely parse a JSONB field that may be a str or already a deserialized object."""
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return []

    # ── Fetch Session ─────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Optional[dict]:
        """Fetch session row by ID."""
        result = (
            self._db.table("interview_sessions")
            .select("id, job_id, candidate_name, candidate_email, status, submitted_at")
            .eq("id", session_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data

    # ── Fetch Job Title ───────────────────────────────────────────────────────

    def get_job_title(self, job_id: str) -> str:
        """Return the job title, or 'Unknown Job' if not found."""
        result = (
            self._db.table("jobs")
            .select("title")
            .eq("id", job_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data["title"] if result.data else "Unknown Job"

    # ── Fetch Candidate Scores ────────────────────────────────────────────────

    def get_response_scores(self, session_id: str) -> List[dict]:
        """Return all response_scores for a session."""
        result = (
            self._db.table("response_scores")
            .select("id, dimension_name, normalized_score, confidence, status, indicators_matched, total_indicators")
            .eq("session_id", session_id)
            .execute()
        )
        self._raise_if_error(result)
        return result.data or []

    # ── Fetch Job Requirements ────────────────────────────────────────────────

    def get_job_requirements(self, job_id: str) -> List[dict]:
        """Return all behavioral requirements for a job with dimension names."""
        req_svc = JobRequirementService()
        return req_svc.list_requirements(job_id)

    # ── Calculate & Save Alignment ────────────────────────────────────────────

    def calculate_and_save_alignment(self, session_id: str) -> dict:
        """
        Orchestrate alignment calculation and persist to session_alignments.
        Returns the enriched alignment record.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        job_id = str(session["job_id"])
        job_title = self.get_job_title(job_id)
        candidate_name = session.get("candidate_name") or "Candidate"

        requirements = self.get_job_requirements(job_id)
        response_scores = self.get_response_scores(session_id)

        # Calculate using the deterministic math engine
        calc_result = calculate_alignment(
            job_requirements=requirements,
            candidate_scores=response_scores,
            candidate_name=candidate_name,
            job_title=job_title,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        row_to_upsert = {
            "session_id":           session_id,
            "job_id":               job_id,
            "overall_score":        calc_result["overall_score"],
            "dimension_alignments": calc_result["dimension_alignments"],
            "strengths":            calc_result["strengths"],
            "areas_for_review":     calc_result["areas_for_review"],
            "metadata":             calc_result["metadata"],
            "calculated_at":        now_iso,
        }

        # Upsert into session_alignments (unique on session_id)
        upsert_res = (
            self._db.table("session_alignments")
            .upsert(row_to_upsert, on_conflict="session_id")
            .execute()
        )
        self._raise_if_error(upsert_res)

        saved_data = upsert_res.data[0] if (upsert_res.data and len(upsert_res.data) > 0) else row_to_upsert

        return {
            "id":                        saved_data.get("id"),
            "session_id":                session_id,
            "job_id":                    job_id,
            "candidate_name":            candidate_name,
            "job_title":                 job_title,
            "overall_score":             calc_result["overall_score"],
            "total_weight":              calc_result["total_weight"],
            "total_dimensions_count":    calc_result["total_dimensions_count"],
            "assessed_dimensions_count": calc_result["assessed_dimensions_count"],
            "average_confidence":        calc_result["average_confidence"],
            "dimension_alignments":      calc_result["dimension_alignments"],
            "strengths":                 calc_result["strengths"],
            "areas_for_review":          calc_result["areas_for_review"],
            "metadata":                  calc_result["metadata"],
            "calculated_at":             saved_data.get("calculated_at", now_iso),
        }

    # ── Get Stored Alignment ──────────────────────────────────────────────────

    def get_alignment(self, session_id: str) -> Optional[dict]:
        """Fetch previously calculated alignment for a session, or None."""
        result = (
            self._db.table("session_alignments")
            .select("id, session_id, job_id, overall_score, dimension_alignments, strengths, areas_for_review, metadata, calculated_at")
            .eq("session_id", session_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        if not result.data:
            return None

        row = result.data
        session = self.get_session(session_id)
        candidate_name = session.get("candidate_name", "Candidate") if session else "Candidate"
        job_id = str(row["job_id"])
        job_title = self.get_job_title(job_id)

        dim_alignments = self._parse_json_field(row.get("dimension_alignments"))
        strengths = self._parse_json_field(row.get("strengths"))
        areas_for_review = self._parse_json_field(row.get("areas_for_review"))
        meta = self._parse_json_field(row.get("metadata"))

        total_weight = sum(d.get("job_weight", 0) for d in dim_alignments if d.get("status") in ("assessed", "missing"))
        assessed_count = sum(1 for d in dim_alignments if d.get("status") == "assessed")
        confs = [d.get("confidence", 0) for d in dim_alignments if d.get("status") == "assessed"]
        avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0

        return {
            "id":                        row.get("id"),
            "session_id":                session_id,
            "job_id":                    job_id,
            "candidate_name":            candidate_name,
            "job_title":                 job_title,
            "overall_score":             float(row.get("overall_score", 0.0)),
            "total_weight":              int(total_weight),
            "total_dimensions_count":    len([d for d in dim_alignments if d.get("status") in ("assessed", "missing")]),
            "assessed_dimensions_count": assessed_count,
            "average_confidence":        avg_conf,
            "dimension_alignments":      dim_alignments,
            "strengths":                 strengths,
            "areas_for_review":          areas_for_review,
            "metadata":                  meta,
            "calculated_at":             row.get("calculated_at"),
        }

    # ── List Alignments for Job ───────────────────────────────────────────────

    def list_alignments_for_job(self, job_id: str) -> List[dict]:
        """Fetch all calculated session alignments for a given job."""
        result = (
            self._db.table("session_alignments")
            .select("id, session_id, job_id, overall_score, dimension_alignments, strengths, areas_for_review, metadata, calculated_at")
            .eq("job_id", job_id)
            .order("overall_score", desc=True)
            .execute()
        )
        self._raise_if_error(result)
        rows = result.data or []
        if not rows:
            return []

        job_title = self.get_job_title(job_id)

        # Batch fetch session info
        session_ids = [r["session_id"] for r in rows]
        sess_res = (
            self._db.table("interview_sessions")
            .select("id, candidate_name, candidate_email, status")
            .in_("id", session_ids)
            .execute()
        )
        self._raise_if_error(sess_res)
        sess_map = {s["id"]: s for s in (sess_res.data or [])}

        output: List[dict] = []
        for r in rows:
            sid = r["session_id"]
            sess = sess_map.get(sid, {})
            c_name = sess.get("candidate_name") or "Candidate"
            dim_alignments = self._parse_json_field(r.get("dimension_alignments"))
            strengths = self._parse_json_field(r.get("strengths"))
            areas_for_review = self._parse_json_field(r.get("areas_for_review"))
            meta = self._parse_json_field(r.get("metadata"))

            total_weight = sum(d.get("job_weight", 0) for d in dim_alignments if d.get("status") in ("assessed", "missing"))
            assessed_count = sum(1 for d in dim_alignments if d.get("status") == "assessed")
            confs = [d.get("confidence", 0) for d in dim_alignments if d.get("status") == "assessed"]
            avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0

            output.append({
                "id":                        r.get("id"),
                "session_id":                sid,
                "job_id":                    job_id,
                "candidate_name":            c_name,
                "job_title":                 job_title,
                "overall_score":             float(r.get("overall_score", 0.0)),
                "total_weight":              int(total_weight),
                "total_dimensions_count":    len([d for d in dim_alignments if d.get("status") in ("assessed", "missing")]),
                "assessed_dimensions_count": assessed_count,
                "average_confidence":        avg_conf,
                "dimension_alignments":      dim_alignments,
                "strengths":                 strengths,
                "areas_for_review":          areas_for_review,
                "metadata":                  meta,
                "calculated_at":             r.get("calculated_at"),
            })

        return output
