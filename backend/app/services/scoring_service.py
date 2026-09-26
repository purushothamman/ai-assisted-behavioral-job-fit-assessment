"""
services/scoring_service.py
Database interactions for Phase 6 response scoring.

Responsibilities:
  1. Fetch all candidate_responses for a session.
  2. For each response, fetch the associated question + indicators.
  3. Call the scoring analyzer for each response.
  4. Persist scores into the response_scores table.
  5. Return structured results.

Uses the admin (service-role) Supabase client throughout so RLS does not
block reads of candidate_responses or writes to response_scores.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.db.client import get_supabase_admin
from app.scoring.analyzer import analyze_response_safe
from app.scoring.rubric import DimensionScore

logger = logging.getLogger(__name__)


class ScoringService:
    """Stateless service — one instance per request is fine."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))

    @staticmethod
    def _parse_json_field(value) -> list:
        """Safely parse a JSONB field that may be a str or already a list."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return []

    # ── Fetch session ─────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Optional[dict]:
        """Return the session row or None."""
        result = (
            self._db.table("interview_sessions")
            .select("id, job_id, candidate_name, candidate_email, status, submitted_at")
            .eq("id", session_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data

    # ── Fetch existing scores ─────────────────────────────────────────────────

    def get_scores(self, session_id: str) -> List[dict]:
        """Return all response_scores rows for a session, newest first."""
        result = (
            self._db.table("response_scores")
            .select(
                "id, session_id, question_id, response_id, dimension_name, "
                "normalized_score, raw_score, confidence, indicators_matched, "
                "total_indicators, status, evidence, scored_at"
            )
            .eq("session_id", session_id)
            .order("scored_at", desc=False)
            .execute()
        )
        self._raise_if_error(result)
        rows = result.data or []
        # Normalise evidence JSONB to list
        for row in rows:
            row["evidence"] = self._parse_json_field(row.get("evidence", []))
        return rows

    # ── Fetch responses for a session ────────────────────────────────────────

    def get_responses(self, session_id: str) -> List[dict]:
        """Return all candidate_responses rows for the session."""
        result = (
            self._db.table("candidate_responses")
            .select("id, session_id, question_id, answer, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        self._raise_if_error(result)
        return result.data or []

    # ── Fetch question with enriched indicator data ───────────────────────────

    def get_question_with_indicators(self, question_id: str) -> Optional[dict]:
        """
        Fetch a question row and enrich it with:
          - dimension_name (from behavioral_dimensions)
          - full indicator objects (name, description, example_behaviors)
            matched by the indicator names stored in interview_questions.indicators
        """
        # 1. Fetch the question
        q_result = (
            self._db.table("interview_questions")
            .select("id, job_id, dimension_id, question, type, difficulty, indicators")
            .eq("id", question_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(q_result)
        if not q_result.data:
            return None

        question = dict(q_result.data)
        question["indicators"] = self._parse_json_field(question.get("indicators", []))

        if not question.get("dimension_id"):
            question["dimension_name"] = None
            question["indicator_objects"] = []
            return question

        # 2. Fetch dimension name
        dim_result = (
            self._db.table("behavioral_dimensions")
            .select("id, name")
            .eq("id", question["dimension_id"])
            .maybe_single()
            .execute()
        )
        self._raise_if_error(dim_result)
        question["dimension_name"] = (dim_result.data or {}).get("name", "unknown")

        # 3. Fetch full indicator objects by name (for embedding texts)
        indicator_names: List[str] = question["indicators"]
        indicator_objs = []
        if indicator_names:
            ind_result = (
                self._db.table("behavioral_indicators")
                .select("id, name, description, example_behaviors")
                .eq("dimension_id", question["dimension_id"])
                .in_("name", indicator_names)
                .execute()
            )
            self._raise_if_error(ind_result)
            db_map = {ind["name"].lower(): ind for ind in (ind_result.data or []) if ind.get("name")}
            for raw_name in indicator_names:
                if not raw_name or not isinstance(raw_name, str):
                    continue
                name_clean = raw_name.strip()
                name_key = name_clean.lower()
                if name_key in db_map:
                    indicator_objs.append(db_map[name_key])
                else:
                    indicator_objs.append({
                        "id": None,
                        "name": name_clean,
                        "description": name_clean,
                        "example_behaviors": "",
                    })
        question["indicator_objects"] = indicator_objs

        return question

    # ── Build indicator text for embedding ────────────────────────────────────

    @staticmethod
    def build_indicator_text(indicator: dict) -> str:
        """
        Concatenate indicator name + description + example_behaviors into
        a single string for embedding.
        """
        parts = [indicator.get("name", "")]
        desc  = indicator.get("description") or ""
        exs   = indicator.get("example_behaviors") or ""
        if desc:
            parts.append(desc)
        if exs:
            parts.append(exs)
        return ". ".join(p.strip() for p in parts if p.strip())

    # ── Score a session ───────────────────────────────────────────────────────

    def score_session(self, session_id: str) -> List[dict]:
        """
        Run the full scoring pipeline for all responses in a session.

        Steps:
          1. Fetch all candidate_responses.
          2. For each response: fetch question + indicators.
          3. Run analyze_response_safe().
          4. Upsert results into response_scores.
          5. Return the list of saved score rows.

        Returns
        -------
        List[dict]  — one dict per response (matches ResponseScoreRead fields)
        """
        responses = self.get_responses(session_id)
        if not responses:
            logger.info("No responses found for session %s — nothing to score.", session_id)
            return []

        scored_at = datetime.now(timezone.utc).isoformat()
        saved_rows = []

        for resp in responses:
            response_id = str(resp["id"])
            question_id = str(resp["question_id"])
            answer      = resp.get("answer", "")

            question = self.get_question_with_indicators(question_id)
            if question is None:
                logger.warning("Question %s not found — skipping response %s", question_id, response_id)
                continue

            dimension_name = question.get("dimension_name") or "unknown"
            indicator_objs = question.get("indicator_objects") or []
            indicator_names = [ind.get("name", "") for ind in indicator_objs]
            indicator_texts = [self.build_indicator_text(ind) for ind in indicator_objs]

            # Run the NLP pipeline
            dim_score: DimensionScore = analyze_response_safe(
                answer=answer,
                dimension_name=dimension_name,
                indicator_names=indicator_names,
                indicator_texts=indicator_texts,
            )

            # Serialize evidence for JSONB storage
            evidence_json = [
                {
                    "indicator_name": e.indicator_name,
                    "similarity":     e.similarity,
                    "score":          e.score,
                    "matched":        e.matched,
                    "level":          e.level,
                }
                for e in dim_score.evidence
            ]

            row = {
                "session_id":         session_id,
                "question_id":        question_id,
                "response_id":        response_id,
                "dimension_name":     dim_score.dimension_name,
                "normalized_score":   dim_score.normalized_score,
                "raw_score":          dim_score.raw_score,
                "confidence":         dim_score.confidence,
                "indicators_matched": dim_score.indicators_matched,
                "total_indicators":   dim_score.total_indicators,
                "status":             dim_score.status,
                "evidence":           json.dumps(evidence_json),
                "scored_at":          scored_at,
            }

            # Upsert on response_id (safe to re-score)
            upsert_result = (
                self._db.table("response_scores")
                .upsert(row, on_conflict="response_id")
                .execute()
            )
            self._raise_if_error(upsert_result)
            if upsert_result.data:
                saved = dict(upsert_result.data[0])
                saved["evidence"] = evidence_json   # return parsed, not raw JSON string
                saved_rows.append(saved)

        logger.info(
            "Scored %d/%d responses for session %s.",
            len(saved_rows), len(responses), session_id,
        )
        return saved_rows

    # ── Fetch job title for summary ───────────────────────────────────────────

    def get_job_title(self, job_id: str) -> str:
        """Return job title or 'Unknown'."""
        result = (
            self._db.table("jobs")
            .select("title")
            .eq("id", job_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return (result.data or {}).get("title", "Unknown")
