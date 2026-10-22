"""
services/report_service.py
Service layer for Phase 8 Assessment Reports & Recruiter Dashboard.

Responsibilities:
  1. Gathers complete context:
     - Candidate session details
     - Job behavioral requirements
     - Approved interview questions
     - Candidate raw responses
     - NLP response scores & evidence
     - Deterministic alignment results
  2. Synthesizes a structured AssessmentReportRead payload.
  3. Formulates targeted, objective interview inquiry prompts.
  4. Enforces ethical compliance safeguards (no automated hire/reject decisions).
  5. Safely handles incomplete assessments and unassessed competencies.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.db.client import get_supabase_admin
from app.services.alignment_service import AlignmentService
from app.services.job_service import JobService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

COMPLIANCE_DISCLAIMER = (
    "This report provides deterministic behavioral analytics and evidence to assist human interviewers. "
    "Antigravity does NOT produce automated hire/reject recommendations or employment decisions. "
    "All hiring decisions must be made by qualified human recruiters using holistic evaluation criteria."
)


def _format_label(name: str) -> str:
    """Format dimension identifier into Title Case."""
    return name.replace("_", " ").title()


class ReportService:
    """Stateless service for generating comprehensive assessment reports."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))

    @staticmethod
    def _parse_json_field(value: Any) -> Any:
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return []

    def _get_framework_version_label(self, framework_version_id: Optional[str]) -> tuple[str, Optional[str]]:
        """
        FS-1: Resolve human-readable framework version string from the
        framework_versions table using the stored FK.  The jobs table only
        carries the FK (framework_version_id); there are NO version_number or
        version_name columns on jobs.

        Returns
        -------
        (label_str, version_id_str)
          label_str   e.g. "v2 - Competency Framework 2026"
          version_id  the UUID as a string, or None
        """
        if not framework_version_id:
            return "v1.0 - Default Behavioral Framework", None
        try:
            result = (
                self._db.table("framework_versions")
                .select("id, version_number, name")
                .eq("id", str(framework_version_id))
                .limit(1)
                .execute()
            )
            self._raise_if_error(result)
            rows = result.data or []
            if rows:
                row = rows[0]
                label = f"v{row.get('version_number', 1)} - {row.get('name', 'Behavioral Framework')}"
                return label, str(row["id"])
        except Exception as exc:
            logger.warning("Could not resolve framework version label for %s: %s", framework_version_id, exc)
        return f"v? - Framework {str(framework_version_id)[:8]}", str(framework_version_id)

    # ── Fetch raw data ────────────────────────────────────────────────────────

    def _get_questions_by_job(self, job_id: str) -> List[dict]:
        """Fetch all approved interview questions for a job with dimension names."""
        result = (
            self._db.table("interview_questions")
            .select("id, job_id, dimension_id, question, type, difficulty, indicators, approved")
            .eq("job_id", job_id)
            .eq("approved", True)
            .execute()
        )
        self._raise_if_error(result)
        questions = result.data or []

        # Join dimension names
        if questions:
            dim_ids = list({q["dimension_id"] for q in questions if q.get("dimension_id")})
            if dim_ids:
                dim_res = (
                    self._db.table("behavioral_dimensions")
                    .select("id, name")
                    .in_("id", dim_ids)
                    .execute()
                )
                self._raise_if_error(dim_res)
                dim_map = {d["id"]: d["name"] for d in (dim_res.data or [])}
                for q in questions:
                    q["dimension_name"] = dim_map.get(q.get("dimension_id"), "unknown")

        return questions

    def _get_responses_by_session(self, session_id: str) -> List[dict]:
        """Fetch candidate responses for a session."""
        result = (
            self._db.table("candidate_responses")
            .select("id, session_id, question_id, answer, created_at")
            .eq("session_id", session_id)
            .execute()
        )
        self._raise_if_error(result)
        return result.data or []

    def _get_scores_by_session(self, session_id: str) -> List[dict]:
        """Fetch response_scores for a session."""
        result = (
            self._db.table("response_scores")
            .select("id, session_id, question_id, response_id, dimension_name, normalized_score, confidence, status, indicators_matched, total_indicators, evidence")
            .eq("session_id", session_id)
            .execute()
        )
        self._raise_if_error(result)
        return result.data or []

    # ── Build Inquiry Prompts ─────────────────────────────────────────────────

    def _generate_inquiry_prompts(
        self,
        dimension_alignments: List[dict],
        areas_for_review: List[str],
    ) -> List[str]:
        """
        Generate structured, objective interview inquiry prompts for the recruiter.
        Helps recruiters dive deeper into areas flagged for review during live interview.
        """
        prompts: List[str] = []

        for dim in dimension_alignments:
            dim_lbl = dim.get("dimension_label") or _format_label(dim.get("dimension_name", ""))
            status = dim.get("status")
            c_score = dim.get("candidate_score", 0.0)
            j_wt = dim.get("job_weight", 0.0)

            if status == "missing":
                prompts.append(
                    f"Behavioral inquiry on {dim_lbl}: 'This role emphasizes {dim_lbl} (weight: {j_wt}). "
                    "Can you share an experience where you applied this competency in a high-stakes project?'"
                )
            elif status == "assessed" and j_wt >= 65.0 and c_score < 65.0:
                prompts.append(
                    f"Situational follow-up on {dim_lbl}: 'Can you walk us through a time when you encountered "
                    f"conflict or ambiguity regarding {dim_lbl}? How did you resolve it?'"
                )
            elif dim.get("confidence", 1.0) < 0.45:
                prompts.append(
                    f"Detail expansion on {dim_lbl}: 'Could you elaborate with a specific STAR example of how you handle "
                    f"{dim_lbl} in day-to-day work?'"
                )

        if not prompts:
            prompts.append(
                "Candidate responses demonstrated solid alignment across all assessed requirements. "
                "Recommend focusing live discussion on team culture fit and technical deep-dives."
            )

        return prompts

    # ── Main Report Builder ───────────────────────────────────────────────────

    def get_assessment_report(self, session_id: str) -> Optional[dict]:
        """
        Assemble the full, explainable assessment report for a candidate session.
        Returns None if session does not exist.
        """
        sess_svc = SessionService()
        session = sess_svc.get_session(session_id)
        if not session:
            return None

        job_id = str(session["job_id"])
        job_svc = JobService()
        job = job_svc.get_job(job_id)
        job_title = job.get("title") if job else "Unknown Role"

        is_complete = session.get("status") == "completed"

        # 1. Fetch questions, responses, scores
        questions = self._get_questions_by_job(job_id)
        responses = self._get_responses_by_session(session_id)
        resp_map = {str(r["question_id"]): r for r in responses}

        scores = self._get_scores_by_session(session_id)
        score_map = {str(s["question_id"]): s for s in scores}

        # 2. Alignment resolution
        align_svc = AlignmentService()
        alignment = align_svc.get_alignment(session_id)

        # If completed and scores exist but alignment hasn't been persisted yet, calculate now
        if not alignment and is_complete and scores:
            try:
                alignment = align_svc.calculate_and_save_alignment(session_id)
            except Exception as exc:
                logger.warning("Auto-alignment calculation failed in report: %s", exc)

        # 3. Assemble Question & Evidence Items
        questions_evidence: List[dict] = []
        for q in questions:
            qid_str = str(q["id"])
            resp = resp_map.get(qid_str)
            sc = score_map.get(qid_str)

            dim_name = q.get("dimension_name", "unknown")
            dim_lbl = _format_label(dim_name)

            evidence_items: List[dict] = []
            if sc and sc.get("evidence"):
                raw_ev = self._parse_json_field(sc["evidence"])
                for ev in raw_ev:
                    evidence_items.append({
                        "indicator_name": ev.get("indicator") or ev.get("indicator_name", "Indicator"),
                        "matched":        bool(ev.get("matched", False)),
                        "level":          ev.get("level", "none"),
                        "similarity":     float(ev.get("similarity", 0.0)),
                        "evidence_text":  ev.get("evidence_text"),
                    })

            answer_text = resp.get("answer") or resp.get("response_text") if resp else None
            word_count = len(answer_text.split()) if answer_text else (resp.get("word_count", 0) if resp else 0)

            questions_evidence.append({
                "question_id":        UUID(qid_str),
                "question_text":      q.get("question", ""),
                "dimension_name":     dim_name,
                "dimension_label":    dim_lbl,
                "question_type":      q.get("type", "behavioral"),
                "difficulty":         q.get("difficulty", "medium"),
                "candidate_response": answer_text,
                "word_count":         word_count,
                "response_score":     int(sc.get("normalized_score")) if sc and sc.get("normalized_score") is not None else None,
                "confidence":         float(sc.get("confidence", 0.0)) if sc else 0.0,
                "status":             sc.get("status") if sc else ("submitted" if resp else "unanswered"),
                "evidence":           evidence_items,
            })

        # 4. Assemble Dimension Breakdown
        raw_dim_alignments = (alignment or {}).get("dimension_alignments", [])
        dimension_breakdown: List[dict] = []

        for dim in raw_dim_alignments:
            d_name = dim.get("dimension_name", "unknown")
            d_lbl = dim.get("dimension_label") or _format_label(d_name)
            j_wt = float(dim.get("job_weight", 0.0))
            c_score = float(dim.get("candidate_score", 0.0))
            gap = round(c_score - j_wt, 1)

            # Count indicators for this dimension from scores
            matched_ind = sum(s.get("indicators_matched", 0) for s in scores if s.get("dimension_name") == d_name)
            total_ind = sum(s.get("total_indicators", 0) for s in scores if s.get("dimension_name") == d_name)

            dimension_breakdown.append({
                "dimension_name":     d_name,
                "dimension_label":    d_lbl,
                "job_weight":         j_wt,
                "weight_percentage":  float(dim.get("weight_percentage", 0.0)),
                "candidate_score":    c_score,
                "benchmark_gap":      gap,
                "contribution":       float(dim.get("contribution", 0.0)),
                "status":             dim.get("status", "assessed"),
                "confidence":         float(dim.get("confidence", 0.0)),
                "response_count":     int(dim.get("response_count", 0)),
                "indicators_matched": matched_ind,
                "total_indicators":   total_ind,
            })

        # 5. Assemble Executive Summary
        overall_score = float((alignment or {}).get("overall_score", 0.0))
        total_weight = int((alignment or {}).get("total_weight", 0))
        assessed_count = int((alignment or {}).get("assessed_dimensions_count", 0))
        total_dims = int((alignment or {}).get("total_dimensions_count", len(dimension_breakdown)))
        avg_conf = float((alignment or {}).get("average_confidence", 0.0))
        strengths = (alignment or {}).get("strengths", [])
        areas_for_review = (alignment or {}).get("areas_for_review", [])
        inquiry_prompts = self._generate_inquiry_prompts(dimension_breakdown, areas_for_review)

        executive_summary = {
            "overall_alignment_score":   overall_score,
            "total_job_weight":          total_weight,
            "assessed_dimensions_count": assessed_count,
            "total_dimensions_count":    total_dims,
            "average_confidence":        avg_conf,
            "is_complete":               is_complete,
            "strengths":                 strengths,
            "areas_for_review":          areas_for_review,
            "inquiry_prompts":           inquiry_prompts,
        }

        now_utc = datetime.now(timezone.utc)

        # FS-1: Resolve correct framework version label via FK join instead of
        # reading nonexistent job.framework_version_number / job.framework_version_name.
        fw_version_id = job.get("framework_version_id") if job else None
        fw_label, fw_id_str = self._get_framework_version_label(fw_version_id)

        # Phase D (OV-1, OV-4): Recruiter review assembly & warnings
        recruiter_review = None
        if alignment and (
            alignment.get("reviewed_at")
            or alignment.get("review_action")
            or alignment.get("recruiter_notes")
            or alignment.get("override_score") is not None
        ):
            recruiter_review = {
                "reviewed_at": alignment.get("reviewed_at"),
                "reviewed_by": alignment.get("reviewed_by"),
                "review_action": alignment.get("review_action"),
                "recruiter_notes": alignment.get("recruiter_notes"),
                "override_score": float(alignment["override_score"]) if alignment.get("override_score") is not None else None,
            }

        report_warnings: List[str] = []
        tot_q = len(questions)
        tot_r = len(responses)

        if tot_q > 0 and tot_r < tot_q:
            report_warnings.append(
                f"Sample-size notice: Candidate responded to {tot_r} of {tot_q} questions. Missing responses are marked as unassessed."
            )
        if tot_r < 3:
            report_warnings.append(
                f"Sample-size notice: Only {tot_r} response(s) submitted (minimum recommended for reliable assessment is 3). Interpret competency alignments with caution."
            )

        if avg_conf < 0.45 and tot_r > 0:
            report_warnings.append(
                f"Evidence-quality notice: Low average similarity confidence ({round(avg_conf, 2)}). Text similarity with rubric indicators was below optimal threshold."
            )

        for dim in dimension_breakdown:
            d_conf = dim.get("confidence", 0.0)
            if dim.get("status") == "assessed" and d_conf < 0.40:
                report_warnings.append(
                    f"Evidence-quality notice: Dimension '{dim.get('dimension_label')}' scored with low semantic confidence ({round(d_conf, 2)}). Supplemental interview inquiry recommended."
                )

        report_warnings.append(
            "Fairness caveat: Model alignment scores and similarity metrics evaluate pattern matching on submitted responses only. "
            "Passing score thresholds does NOT prove absence of bias. Human recruiter judgment is required for all hiring decisions."
        )

        return {
            "session_id":          UUID(session_id),
            "job_id":              UUID(job_id),
            "job_title":           job_title,
            "candidate_name":      session.get("candidate_name") or "Candidate",
            "candidate_email":     session.get("candidate_email") or "",
            "status":              session.get("status", "pending"),
            "submitted_at":        session.get("submitted_at"),
            "created_at":          session.get("created_at"),
            "executive_summary":   executive_summary,
            "dimension_breakdown": dimension_breakdown,
            "questions_evidence":  questions_evidence,
            "compliance_notice":   COMPLIANCE_DISCLAIMER,
            "warnings":            report_warnings,
            "recruiter_review":    recruiter_review,
            "metadata": {
                "total_questions":      len(questions),
                "total_responses":      len(responses),
                "total_scores":         len(scores),
                "framework_version":    fw_label,
                "framework_version_id": fw_id_str,
                "warnings":             report_warnings,
                "recruiter_review":     recruiter_review,
            },
            "generated_at":        now_utc,
        }

    # ── Job Sessions Summary ──────────────────────────────────────────────────

    def get_job_reports_summary(self, job_id: str) -> List[dict]:
        """
        Return a concise summary of all candidate assessment sessions for a job.
        Used on the recruiter dashboard to display candidate rankings and statuses.
        """
        sess_svc = SessionService()
        sessions = sess_svc.list_sessions(job_id)
        if not sessions:
            return []

        align_svc = AlignmentService()
        alignments = align_svc.list_alignments_for_job(job_id)
        align_map = {str(a["session_id"]): a for a in alignments}

        output: List[dict] = []
        for s in sessions:
            sid = str(s["id"])
            align = align_map.get(sid)

            top_str = None
            if align and align.get("strengths"):
                top_str = align["strengths"][0]

            top_rev = None
            if align and align.get("areas_for_review"):
                top_rev = align["areas_for_review"][0]

            output.append({
                "session_id":              UUID(sid),
                "candidate_name":          s.get("candidate_name") or "Candidate",
                "candidate_email":         s.get("candidate_email") or "",
                "status":                  s.get("status", "pending"),
                "submitted_at":            s.get("submitted_at"),
                "overall_alignment_score": align.get("overall_score") if align else None,
                "top_strength":            top_str,
                "primary_review_area":     top_rev,
                "is_scored":               align is not None,
            })

        # Sort: scored candidates with highest alignment first, then by date
        output.sort(
            key=lambda x: (
                x["overall_alignment_score"] is not None,
                x["overall_alignment_score"] or 0.0,
            ),
            reverse=True,
        )

        return output
