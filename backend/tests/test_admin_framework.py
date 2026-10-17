"""
tests/test_admin_framework.py
Comprehensive test suite for Phase 11 Admin-Managed Behavioral Framework & Versioning.

Covers:
  1. Authorization: Enforcing require_admin (401 unauthenticated, 403 recruiter, 200 admin).
  2. Dimension CRUD: Create, read, update, safe archive/delete, reorder.
  3. Indicator CRUD: Add, update, delete indicators per dimension.
  4. Validation: Pre-activation checks (min dimensions, min indicators, uniqueness).
  5. Versioning: Immutable snapshot freezing, version increment, superseding past versions.
  6. Pipeline Compatibility: Job analysis, Groq questions, deterministic NLP scoring,
     weighted alignment, and historical assessment immutability.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.ai.job_analyzer import build_dynamic_system_prompt
from app.ai.question_generator import build_dynamic_question_system_prompt
from app.ai.question_schemas import GeneratedQuestion
from app.ai.schemas import DimensionRequirement, register_valid_dimension
from app.alignment.calculator import calculate_alignment
from app.core.security import require_admin, require_recruiter
from app.main import app
from app.scoring.analyzer import analyze_response
from app.scoring.rubric import DimensionScore, aggregate_dimension_score


# ── Sample Data ───────────────────────────────────────────────────────────────

DIM_ID_1 = str(uuid4())
DIM_ID_2 = str(uuid4())
DIM_ID_CUSTOM = str(uuid4())
IND_ID_1 = str(uuid4())
IND_ID_2 = str(uuid4())
VER_ID_1 = str(uuid4())

SAMPLE_ACTIVE_DIMS = [
    {
        "id": DIM_ID_1,
        "name": "communication",
        "description": "Ability to convey clear ideas and listen actively",
        "is_active": True,
        "status": "active",
        "order_index": 0,
        "indicators": [
            {"id": str(uuid4()), "dimension_id": DIM_ID_1, "name": "clarity", "description": "Expresses ideas clearly", "is_active": True},
            {"id": str(uuid4()), "dimension_id": DIM_ID_1, "name": "active_listening", "description": "Listens attentively", "is_active": True},
        ],
    },
    {
        "id": DIM_ID_2,
        "name": "teamwork",
        "description": "Collaborates toward shared team goals",
        "is_active": True,
        "status": "active",
        "order_index": 1,
        "indicators": [
            {"id": str(uuid4()), "dimension_id": DIM_ID_2, "name": "collaboration", "description": "Works cooperatively", "is_active": True},
            {"id": str(uuid4()), "dimension_id": DIM_ID_2, "name": "supportiveness", "description": "Helps teammates", "is_active": True},
        ],
    },
    {
        "id": DIM_ID_CUSTOM,
        "name": "systems_thinking",
        "description": "Evaluates complex technical systems and trade-offs",
        "is_active": True,
        "status": "active",
        "order_index": 2,
        "indicators": [
            {"id": str(uuid4()), "dimension_id": DIM_ID_CUSTOM, "name": "architecture_evaluation", "description": "Considers architectural constraints", "is_active": True},
            {"id": str(uuid4()), "dimension_id": DIM_ID_CUSTOM, "name": "tradeoff_analysis", "description": "Weighs latency vs complexity trade-offs", "is_active": True},
        ],
    },
]


# =============================================================================
# 1. AUTHORIZATION TESTS
# =============================================================================

class TestAdminAuthorization:
    """Ensure management endpoints strictly reject unauthorized callers."""

    def test_anonymous_request_rejected(self):
        """Unauthenticated requests must receive HTTP 401 Unauthorized."""
        # Clean client without any dependency overrides
        with TestClient(app) as raw_client:
            resp = raw_client.get("/api/admin/dimensions")
            assert resp.status_code == 401

    def test_recruiter_role_rejected_with_403(self, client: TestClient):
        """Authenticated recruiters attempting admin operations must receive HTTP 403 Forbidden."""
        # `client` has require_recruiter overridden with role='recruiter'
        resp = client.get("/api/admin/dimensions")
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]

    def test_recruiter_rejected_from_framework_publish(self, client: TestClient):
        """Recruiters cannot publish or activate framework versions."""
        payload = {"name": "Malicious Version", "description": "Should fail"}
        resp = client.post("/api/admin/framework/publish", json=payload)
        assert resp.status_code == 403

    def test_admin_role_allowed(self, admin_client: TestClient):
        """Authenticated platform administrators can access management endpoints."""
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.list_dimensions_admin.return_value = SAMPLE_ACTIVE_DIMS
            resp = admin_client.get("/api/admin/dimensions")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert len(data) == 3


# =============================================================================
# 2. DIMENSION CRUD & MANAGEMENT TESTS
# =============================================================================

class TestDimensionManagement:
    """Test administrative CRUD operations for behavioral dimensions."""

    def test_list_dimensions_admin(self, admin_client: TestClient):
        """Admin can list all dimensions with indicator details."""
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.list_dimensions_admin.return_value = SAMPLE_ACTIVE_DIMS
            resp = admin_client.get("/api/admin/dimensions?include_archived=true")
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 3

    def test_create_dimension_success(self, admin_client: TestClient):
        """Admin can create a new dimension with initial indicators."""
        new_dim = {
            "name": "strategic_thinking",
            "description": "Aligns technical vision with long-term business goals",
            "is_active": True,
            "status": "active",
            "order_index": 3,
            "initial_indicators": [
                {
                    "name": "vision_alignment",
                    "description": "Translates high-level strategy into execution",
                    "order_index": 0,
                },
                {
                    "name": "anticipates_trends",
                    "description": "Identifies architectural hurdles ahead of time",
                    "order_index": 1,
                },
            ],
        }

        new_dim_id = str(uuid4())
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.create_dimension.return_value = {
                "id": new_dim_id,
                **new_dim,
                "indicators": [
                    {"id": str(uuid4()), "dimension_id": new_dim_id, **i}
                    for i in new_dim["initial_indicators"]
                ],
                "indicator_count": 2,
            }
            resp = admin_client.post("/api/admin/dimensions", json=new_dim)
            assert resp.status_code == 201
            data = resp.json()["data"]
            assert data["name"] == "strategic_thinking"

    def test_create_dimension_invalid_name_fails(self, admin_client: TestClient):
        """Invalid dimension slug (e.g. non-identifier characters) fails Pydantic validation with 422."""
        invalid_dim = {
            "name": "123 Invalid Name!",
            "description": "This description is valid and sufficiently long",
        }
        resp = admin_client.post("/api/admin/dimensions", json=invalid_dim)
        assert resp.status_code == 422

    def test_create_duplicate_dimension_rejected(self, admin_client: TestClient):
        """Attempting to create a dimension with an existing name returns 422."""
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.create_dimension.side_effect = ValueError("Dimension 'communication' already exists.")
            resp = admin_client.post(
                "/api/admin/dimensions",
                json={"name": "communication", "description": "Duplicate dimension test description"},
            )
            assert resp.status_code == 422
            assert "already exists" in resp.json()["detail"]

    def test_update_dimension_success(self, admin_client: TestClient):
        """Admin can update dimension description and status."""
        dim_id = str(uuid4())
        update_payload = {
            "description": "Updated comprehensive description of leadership and coordination",
            "is_active": True,
            "status": "active",
        }
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.update_dimension.return_value = {
                "id": dim_id,
                "name": "leadership",
                **update_payload,
            }
            resp = admin_client.put(f"/api/admin/dimensions/{dim_id}", json=update_payload)
            assert resp.status_code == 200
            assert resp.json()["data"]["description"] == update_payload["description"]

    def test_safe_archive_dimension_when_referenced(self, admin_client: TestClient):
        """Referenced dimensions are safely archived to prevent breaking historical assessments."""
        dim_id = str(uuid4())
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.archive_or_delete_dimension.return_value = {
                "action": "archived",
                "id": dim_id,
                "name": "communication",
                "message": "Dimension is referenced by historical jobs; safely archived.",
            }
            resp = admin_client.delete(f"/api/admin/dimensions/{dim_id}")
            assert resp.status_code == 200
            assert resp.json()["data"]["action"] == "archived"

    def test_reorder_dimensions(self, admin_client: TestClient):
        """Admin can update order_index across multiple dimensions."""
        reorder_payload = {
            "items": [
                {"id": DIM_ID_2, "order_index": 0},
                {"id": DIM_ID_1, "order_index": 1},
            ]
        }
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.reorder_dimensions.return_value = SAMPLE_ACTIVE_DIMS
            resp = admin_client.patch("/api/admin/dimensions/reorder", json=reorder_payload)
            assert resp.status_code == 200


# =============================================================================
# 3. INDICATOR MANAGEMENT TESTS
# =============================================================================

class TestIndicatorManagement:
    """Test administrative indicator CRUD."""

    def test_add_indicator(self, admin_client: TestClient):
        """Admin can add an indicator to an existing dimension."""
        dim_id = str(uuid4())
        ind_payload = {
            "name": "root_cause_analysis",
            "description": "Investigates underlying failure mechanisms rather than surface symptoms",
            "example_behaviors": "Conducts post-mortems and traces stacktraces",
            "order_index": 0,
        }
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.add_indicator.return_value = {
                "id": str(uuid4()),
                "dimension_id": dim_id,
                **ind_payload,
            }
            resp = admin_client.post(f"/api/admin/dimensions/{dim_id}/indicators", json=ind_payload)
            assert resp.status_code == 201
            assert resp.json()["data"]["name"] == "root_cause_analysis"

    def test_update_indicator(self, admin_client: TestClient):
        """Admin can update an indicator's description and example behaviors."""
        ind_id = str(uuid4())
        payload = {
            "description": "Updated deep-dive investigation description",
            "example_behaviors": "Examines log anomalies",
        }
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.update_indicator.return_value = {
                "id": ind_id,
                "name": "root_cause_analysis",
                **payload,
            }
            resp = admin_client.put(f"/api/admin/indicators/{ind_id}", json=payload)
            assert resp.status_code == 200

    def test_delete_indicator(self, admin_client: TestClient):
        """Admin can remove an indicator."""
        ind_id = str(uuid4())
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.delete_indicator.return_value = {"action": "deleted", "id": ind_id}
            resp = admin_client.delete(f"/api/admin/indicators/{ind_id}")
            assert resp.status_code == 200


# =============================================================================
# 4. VALIDATION & VERSIONING TESTS
# =============================================================================

class TestValidationAndVersioning:
    """Test framework validation and version publishing."""

    def test_validate_framework_endpoint(self, admin_client: TestClient):
        """Validation endpoint returns integrity report with active counts."""
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.validate_framework.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "active_dimension_count": 3,
                "total_indicator_count": 6,
            }
            resp = admin_client.post("/api/admin/framework/validate")
            assert resp.status_code == 200
            assert resp.json()["data"]["valid"] is True

    def test_publish_version_success(self, admin_client: TestClient):
        """Publishing creates an activated version with frozen snapshot."""
        payload = {
            "name": "v2.0 - Systems Engineering Behavioral Framework",
            "description": "Includes systems_thinking competency",
        }
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.publish_version.return_value = {
                "id": str(uuid4()),
                "version_number": 2,
                "name": payload["name"],
                "description": payload["description"],
                "status": "active",
                "dimensions_snapshot": SAMPLE_ACTIVE_DIMS,
            }
            resp = admin_client.post("/api/admin/framework/publish", json=payload)
            assert resp.status_code == 201
            data = resp.json()["data"]
            assert data["version_number"] == 2
            assert data["status"] == "active"

    def test_publish_version_validation_failure_rejected(self, admin_client: TestClient):
        """If framework fails integrity validation, publishing raises 422."""
        payload = {"name": "Invalid Release", "description": "Test"}
        with patch("app.api.admin_framework.FrameworkService") as MockSvc:
            MockSvc.return_value.publish_version.side_effect = ValueError(
                "Framework validation failed: Framework must have at least 3 active dimensions."
            )
            resp = admin_client.post("/api/admin/framework/publish", json=payload)
            assert resp.status_code == 422
            assert "validation failed" in resp.json()["detail"]


# =============================================================================
# 5. DYNAMIC FRAMEWORK & PIPELINE COMPATIBILITY
# =============================================================================

class TestPipelineCompatibilityWithCustomDimensions:
    """
    Verify that custom dimensions added to the framework flow through
    job analysis, question generation, deterministic scoring, and alignment.
    """

    def test_custom_dimension_pydantic_registration(self):
        """Newly registered dimension is accepted by DimensionRequirement schema."""
        custom_name = "data_governance"
        register_valid_dimension(custom_name)

        req = DimensionRequirement(
            dimension=custom_name,
            importance=85,
            reason="Ensures privacy compliance and data security policies are maintained.",
        )
        assert req.dimension == "data_governance"
        assert req.importance == 85

    def test_dynamic_job_analyzer_prompt_generation(self):
        """Job analyzer system prompt includes all active framework dimensions."""
        prompt = build_dynamic_system_prompt(SAMPLE_ACTIVE_DIMS)
        assert "systems_thinking" in prompt
        assert "communication" in prompt
        assert "teamwork" in prompt
        assert "architecture_evaluation" in prompt

    def test_dynamic_question_generator_prompt_generation(self):
        """Question generator prompt includes confirmed custom dimensions."""
        confirmed_dims = ["systems_thinking", "leadership"]
        prompt = build_dynamic_question_system_prompt(confirmed_dims)
        assert "systems_thinking" in prompt
        assert "leadership" in prompt

    def test_custom_dimension_question_schema_validation(self):
        """Generated question schema accepts questions for custom registered dimensions."""
        register_valid_dimension("systems_thinking")
        q = GeneratedQuestion(
            dimension="systems_thinking",
            question="Describe a scenario where you had to evaluate trade-offs between consistency and availability.",
            type="behavioral",
            difficulty="hard",
            indicators=["tradeoff_analysis", "architecture_evaluation"],
        )
        assert q.dimension == "systems_thinking"
        assert len(q.indicators) == 2

    def test_custom_dimension_deterministic_nlp_rubric_scoring(self):
        """
        Deterministic NLP rubric accurately scores candidate answers against
        custom indicators without calling Groq.
        """
        candidate_answer = (
            "In our distributed architecture, we had to balance latency and consistency. "
            "I conducted a thorough trade-off analysis between eventual consistency and strict serializability, "
            "evaluating our SLA constraints before selecting Postgres replication with read replicas."
        )
        indicator_names = ["tradeoff_analysis", "irrelevant_indicator"]
        indicator_texts = [
            "Weighs latency, consistency, and operational complexity trade-offs. Evaluates architectural trade-offs systematically.",
            "Demonstrates conflict resolution during budget negotiations. Negotiates budget cuts calmly.",
        ]

        score_res = analyze_response(
            answer=candidate_answer,
            dimension_name="systems_thinking",
            indicator_names=indicator_names,
            indicator_texts=indicator_texts,
        )

        assert score_res.dimension_name == "systems_thinking"
        assert 0 <= score_res.normalized_score <= 100
        assert score_res.indicators_matched >= 1
        assert len(score_res.evidence) == 2
        tradeoff_ev = [e for e in score_res.evidence if e.indicator_name == "tradeoff_analysis"][0]
        assert tradeoff_ev.level in ("strong", "partial")

    def test_custom_dimension_deterministic_alignment_calculation(self):
        """Deterministic alignment calculator includes custom dimensions accurately."""
        job_reqs = [
            {"dimension_name": "systems_thinking", "importance": 90, "confirmed": True},
            {"dimension_name": "communication", "importance": 60, "confirmed": True},
        ]
        candidate_scores = [
            {"dimension_name": "systems_thinking", "normalized_score": 80, "confidence": 0.85, "status": "scored"},
            {"dimension_name": "communication", "normalized_score": 70, "confidence": 0.80, "status": "scored"},
        ]

        alignment = calculate_alignment(
            job_requirements=job_reqs,
            candidate_scores=candidate_scores,
            candidate_name="Alex River",
            job_title="Principal Architect",
        )

        # Expected overall score: (80*90 + 70*60) / (90+60) = (7200 + 4200) / 150 = 11400 / 150 = 76.0
        assert alignment["overall_score"] == 76.0
        assert len(alignment["dimension_alignments"]) == 2
        sys_align = [d for d in alignment["dimension_alignments"] if d["dimension_name"] == "systems_thinking"][0]
        assert sys_align["candidate_score"] == 80.0
        assert sys_align["weight_percentage"] == 60.0  # 90 / 150 = 60%
        # Point contribution: 80 * (90/150) = 48.0
        assert sys_align["contribution"] == 48.0
