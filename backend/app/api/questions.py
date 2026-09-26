"""
api/questions.py
Endpoints for AI question generation and question management.

Routes
------
POST   /jobs/{job_id}/questions/generate    Groq: generate interview questions
GET    /jobs/{job_id}/questions             List all questions for a job
PATCH  /questions/{question_id}             Edit / approve a single question
DELETE /questions/{question_id}             Delete a single question

Auth: all endpoints require recruiter JWT.
Ownership: job_id cross-checked on every request.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.groq_client import GroqError
from app.ai.question_generator import generate_questions
from app.core.security import require_recruiter
from app.schemas.common import APIResponse
from app.schemas.questions import QuestionRead, QuestionUpdate
from app.services.job_requirement_service import JobRequirementService
from app.services.job_service import JobService
from app.services.question_service import QuestionService

router = APIRouter(tags=["Questions"])


# ── Dependency factories ───────────────────────────────────────────────────

def _get_job_svc() -> JobService:
    return JobService()


def _get_req_svc() -> JobRequirementService:
    return JobRequirementService()


def _get_q_svc() -> QuestionService:
    return QuestionService()


# ── Shared ownership helper ────────────────────────────────────────────────

def _assert_job_ownership(job_id: str, recruiter_id: str, job_svc: JobService) -> dict:
    """Raise 404 if the job doesn't exist or doesn't belong to the recruiter."""
    job = job_svc.get_job(job_id, recruiter_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── POST /jobs/{job_id}/questions/generate ────────────────────────────────

@router.post(
    "/jobs/{job_id}/questions/generate",
    response_model=APIResponse[List[QuestionRead]],
    status_code=status.HTTP_201_CREATED,
)
async def generate_questions_endpoint(
    job_id: UUID,
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    req_svc: JobRequirementService = Depends(_get_req_svc),
    q_svc: QuestionService = Depends(_get_q_svc),
):
    """
    Trigger Groq to generate behavioral interview questions.

    1. Validates job ownership.
    2. Loads confirmed behavioral requirements.
    3. Calls Groq to generate 2-3 questions per dimension.
    4. Deletes previous questions and inserts the new batch.
    5. Advances job status to 'questions_generated'.
    6. Returns the list of saved questions.
    """
    job = _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    if not job.get("description"):
        raise HTTPException(
            status_code=422,
            detail="Job must have a description before questions can be generated.",
        )

    # Load confirmed requirements
    try:
        requirements = req_svc.list_requirements(str(job_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    confirmed = [r for r in requirements if r.get("confirmed")]
    if not confirmed:
        raise HTTPException(
            status_code=422,
            detail=(
                "No confirmed behavioral requirements found. "
                "Please confirm at least one requirement before generating questions."
            ),
        )

    # Call Groq
    try:
        questions = generate_questions(
            title=job["title"],
            description=job.get("description", ""),
            requirements=requirements,
        )
    except GroqError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Save to DB
    try:
        saved = q_svc.save_questions(str(job_id), questions)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Advance job status
    try:
        job_svc.update_job(str(job_id), current_user["id"], _QuestionStatus())
    except Exception:
        pass  # Non-fatal

    return APIResponse(
        message=f"Generated {len(saved)} interview questions.",
        data=saved,
    )


class _QuestionStatus:
    """Duck-typed payload for advancing job status."""
    def model_dump(self, exclude_none=True):  # noqa: D102
        return {"status": "questions_generated"}


# ── GET /jobs/{job_id}/questions ──────────────────────────────────────────

@router.get(
    "/jobs/{job_id}/questions",
    response_model=APIResponse[List[QuestionRead]],
)
async def list_questions(
    job_id: UUID,
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    q_svc: QuestionService = Depends(_get_q_svc),
):
    """List all interview questions for a job."""
    _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    try:
        questions = q_svc.list_questions(str(job_id))
        return APIResponse(data=questions)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── PATCH /questions/{question_id} ────────────────────────────────────────

@router.patch(
    "/questions/{question_id}",
    response_model=APIResponse[QuestionRead],
)
async def update_question(
    question_id: UUID,
    payload: QuestionUpdate,
    job_id: UUID = Query(..., description="Job ID for ownership verification"),
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    q_svc: QuestionService = Depends(_get_q_svc),
):
    """
    Edit or approve a single interview question.
    Requires job_id as a query param for ownership verification.
    """
    _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    update_data = payload.model_dump(exclude_none=True)
    try:
        updated = q_svc.update_question(str(question_id), str(job_id), update_data)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not updated:
        raise HTTPException(status_code=404, detail="Question not found")

    return APIResponse(message="Question updated", data=updated)


# ── DELETE /questions/{question_id} ───────────────────────────────────────

@router.delete(
    "/questions/{question_id}",
    response_model=APIResponse[None],
)
async def delete_question(
    question_id: UUID,
    job_id: UUID = Query(..., description="Job ID for ownership verification"),
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    q_svc: QuestionService = Depends(_get_q_svc),
):
    """Delete a single interview question."""
    _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    try:
        deleted = q_svc.delete_question(str(question_id), str(job_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")

    return APIResponse(message="Question deleted")
