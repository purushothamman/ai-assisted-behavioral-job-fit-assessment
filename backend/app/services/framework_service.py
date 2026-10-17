"""
services/framework_service.py
Platform administration service for behavioral dimensions, indicators,
and framework versioning.

Guarantees:
  1. Only authorized administrators can modify the framework.
  2. Safe archiving: dimensions referenced in historical jobs or questions are
     archived rather than deleted to prevent foreign key errors.
  3. Framework versioning: publishing freezes an immutable snapshot of all active
     dimensions and indicators. Historical assessments retain their exact original
     competencies and indicators.
  4. Pre-activation validation: ensures dimensions and indicators meet strict
     quality standards before a version can be published.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.schemas import register_valid_dimension
from app.db.client import get_supabase_admin
from app.schemas.dimensions import (
    DimensionCreate,
    DimensionReorderItem,
    DimensionUpdate,
    FrameworkValidationResult,
    FrameworkVersionPublish,
    IndicatorCreate,
    IndicatorUpdate,
)

logger = logging.getLogger(__name__)


def _safe_data(result) -> Optional[Any]:
    """
    Return result.data safely, handling None result objects.
    Some supabase-py versions return None from .execute() when there are no rows
    (especially with .maybe_single()). We replace all maybe_single() with .limit(1)
    and use this helper to safely extract the first row.
    """
    if result is None:
        return None
    return getattr(result, "data", None)


class FrameworkService:
    """Stateless administration service for the behavioral assessment framework."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    @staticmethod
    def _raise_if_error(result) -> None:
        """Raise RuntimeError if Supabase returned an error. Safely handles None results."""
        if result is None:
            return  # No result object = no error (empty result set)
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error in FrameworkService: %s", result.error)
            raise RuntimeError(str(result.error))

    def _fetch_one(self, table: str, select: str, **filters) -> Optional[dict]:
        """
        Fetch a single row from a table using .limit(1) instead of .maybe_single().
        Avoids the None-result bug in supabase-py when no rows match.
        """
        query = self._db.table(table).select(select)
        for col, val in filters.items():
            query = query.eq(col, val)
        result = query.limit(1).execute()
        self._raise_if_error(result)
        data = _safe_data(result)
        return data[0] if data else None

    # ── Versions ──────────────────────────────────────────────────────────────

    def list_versions(self) -> List[dict]:
        """Return all published and draft framework versions, newest first."""
        result = (
            self._db.table("framework_versions")
            .select(
                "id, version_number, name, description, status, "
                "dimensions_snapshot, created_at, activated_at, created_by"
            )
            .order("version_number", desc=True)
            .execute()
        )
        self._raise_if_error(result)
        return _safe_data(result) or []

    def get_active_version(self) -> Optional[dict]:
        """Return the currently active framework version."""
        result = (
            self._db.table("framework_versions")
            .select(
                "id, version_number, name, description, status, "
                "dimensions_snapshot, created_at, activated_at, created_by"
            )
            .eq("status", "active")
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        self._raise_if_error(result)
        data = _safe_data(result)
        return data[0] if data else None

    def get_version(self, version_id: str) -> Optional[dict]:
        """Return a single framework version by ID."""
        return self._fetch_one(
            "framework_versions",
            "id, version_number, name, description, status, dimensions_snapshot, created_at, activated_at, created_by",
            id=version_id,
        )

    # ── Dimensions (Admin) ────────────────────────────────────────────────────

    def list_dimensions_admin(self, include_archived: bool = True) -> List[dict]:
        """
        Return all dimensions for admin management, enriched with indicator counts
        and embedded indicators list.
        """
        query = (
            self._db.table("behavioral_dimensions")
            .select("id, name, description, is_active, status, order_index, created_at, updated_at")
            .order("order_index", desc=False)
            .order("name", desc=False)
        )
        if not include_archived:
            query = query.neq("status", "archived")

        dim_res = query.execute()
        self._raise_if_error(dim_res)
        dimensions = _safe_data(dim_res) or []

        if not dimensions:
            return []

        # Fetch all indicators
        dim_ids = [str(d["id"]) for d in dimensions]
        ind_res = (
            self._db.table("behavioral_indicators")
            .select("id, dimension_id, name, description, example_behaviors, order_index, is_active, created_at, updated_at")
            .in_("dimension_id", dim_ids)
            .order("order_index", desc=False)
            .order("name", desc=False)
            .execute()
        )
        self._raise_if_error(ind_res)
        indicators = _safe_data(ind_res) or []

        # Group indicators by dimension_id
        ind_by_dim: Dict[str, List[dict]] = {str(d["id"]): [] for d in dimensions}
        for ind in indicators:
            d_id = str(ind.get("dimension_id"))
            if d_id in ind_by_dim:
                ind_by_dim[d_id].append(ind)

        # Check references across job_requirements and interview_questions
        referenced_ids = set()
        try:
            req_check = self._db.table("job_requirements").select("dimension_id").execute()
            for r in (_safe_data(req_check) or []):
                if r.get("dimension_id"):
                    referenced_ids.add(str(r["dimension_id"]))
            q_check = self._db.table("interview_questions").select("dimension_id").execute()
            for q in (_safe_data(q_check) or []):
                if q.get("dimension_id"):
                    referenced_ids.add(str(q["dimension_id"]))
        except Exception:
            pass

        for d in dimensions:
            d_id = str(d["id"])
            d["indicators"] = ind_by_dim.get(d_id, [])
            d["indicator_count"] = len(d["indicators"])
            d["is_referenced"] = d_id in referenced_ids

        return dimensions

    def get_dimension_admin(self, dimension_id: str) -> Optional[dict]:
        """Return a single dimension with full indicators and reference usage count."""
        dim = self._fetch_one(
            "behavioral_dimensions",
            "id, name, description, is_active, status, order_index, created_at, updated_at",
            id=dimension_id,
        )
        if not dim:
            return None

        dim = dict(dim)

        # Fetch indicators
        ind_res = (
            self._db.table("behavioral_indicators")
            .select("id, dimension_id, name, description, example_behaviors, order_index, is_active, created_at, updated_at")
            .eq("dimension_id", dimension_id)
            .order("order_index", desc=False)
            .order("name", desc=False)
            .execute()
        )
        self._raise_if_error(ind_res)
        dim["indicators"] = _safe_data(ind_res) or []
        dim["indicator_count"] = len(dim["indicators"])

        # Check references count in job_requirements
        try:
            req_check = (
                self._db.table("job_requirements")
                .select("id")
                .eq("dimension_id", dimension_id)
                .execute()
            )
            data = _safe_data(req_check)
            dim["referenced_jobs_count"] = len(data) if data else 0
        except Exception:
            dim["referenced_jobs_count"] = 0

        return dim

    def create_dimension(self, payload: DimensionCreate) -> dict:
        """Create a new behavioral dimension with optional initial indicators."""
        # Check name uniqueness — use _fetch_one to avoid maybe_single() None bug
        existing = self._fetch_one(
            "behavioral_dimensions", "id", name=payload.name
        )
        if existing:
            raise ValueError(f"Dimension '{payload.name}' already exists.")

        dim_row = {
            "name": payload.name,
            "description": payload.description,
            "is_active": payload.is_active,
            "status": payload.status,
            "order_index": payload.order_index,
        }

        try:
            dim_res = (
                self._db.table("behavioral_dimensions")
                .insert(dim_row)
                .select("id, name, description, is_active, status, order_index, created_at, updated_at")
                .execute()
            )
            self._raise_if_error(dim_res)
        except Exception as exc:
            logger.error(
                "Supabase insert failed for behavioral_dimensions. Row: %s. Error: %s",
                dim_row, exc, exc_info=True,
            )
            raise

        data = _safe_data(dim_res)
        created_dim = data[0] if data else dim_row

        # Register in runtime AI validator
        register_valid_dimension(payload.name)

        # Insert initial indicators if provided
        created_indicators = []
        if payload.initial_indicators and created_dim.get("id"):
            ind_rows = [
                {
                    "dimension_id": created_dim["id"],
                    "name": ind.name,
                    "description": ind.description,
                    "example_behaviors": ind.example_behaviors,
                    "order_index": ind.order_index,
                    "is_active": True,
                }
                for ind in payload.initial_indicators
            ]
            try:
                ind_res = (
                    self._db.table("behavioral_indicators")
                    .insert(ind_rows)
                    .select("id, dimension_id, name, description, example_behaviors, order_index, is_active, created_at, updated_at")
                    .execute()
                )
                self._raise_if_error(ind_res)
                created_indicators = _safe_data(ind_res) or []
            except Exception as exc:
                logger.error(
                    "Supabase insert failed for initial indicators. Rows: %s. Error: %s",
                    ind_rows, exc, exc_info=True,
                )
                raise

        created_dim["indicators"] = created_indicators
        created_dim["indicator_count"] = len(created_indicators)
        return created_dim

    def update_dimension(self, dimension_id: str, payload: DimensionUpdate) -> dict:
        """Update dimension fields."""
        existing = self._fetch_one(
            "behavioral_dimensions", "id, name", id=dimension_id
        )
        if not existing:
            raise ValueError("Dimension not found.")

        update_data = {
            k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None
        }

        # Check name conflict if renaming
        if "name" in update_data and update_data["name"] != existing.get("name"):
            conflict = self._fetch_one(
                "behavioral_dimensions", "id", name=update_data["name"]
            )
            if conflict and str(conflict.get("id")) != str(dimension_id):
                raise ValueError(f"Dimension name '{update_data['name']}' is already in use.")
            register_valid_dimension(update_data["name"])

        if not update_data:
            return self.get_dimension_admin(dimension_id) or existing

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        res = (
            self._db.table("behavioral_dimensions")
            .update(update_data)
            .eq("id", dimension_id)
            .execute()
        )
        self._raise_if_error(res)
        return self.get_dimension_admin(dimension_id) or existing

    def archive_or_delete_dimension(self, dimension_id: str) -> dict:
        """
        Safely archive or delete a dimension.
        If referenced in job_requirements or interview_questions, archives (is_active=False, status='archived')
        to preserve historical assessments. If unreferenced, safely deletes.
        """
        dim = self._fetch_one("behavioral_dimensions", "id, name", id=dimension_id)
        if not dim:
            raise ValueError("Dimension not found.")

        # Check references
        is_referenced = False
        try:
            req_res = (
                self._db.table("job_requirements")
                .select("id")
                .eq("dimension_id", dimension_id)
                .limit(1)
                .execute()
            )
            data = _safe_data(req_res)
            if data and len(data) > 0:
                is_referenced = True
        except Exception:
            pass

        if not is_referenced:
            try:
                q_res = (
                    self._db.table("interview_questions")
                    .select("id")
                    .eq("dimension_id", dimension_id)
                    .limit(1)
                    .execute()
                )
                data = _safe_data(q_res)
                if data and len(data) > 0:
                    is_referenced = True
            except Exception:
                pass

        if is_referenced:
            arch_res = (
                self._db.table("behavioral_dimensions")
                .update({
                    "is_active": False,
                    "status": "archived",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", dimension_id)
                .execute()
            )
            self._raise_if_error(arch_res)
            return {
                "action": "archived",
                "id": dimension_id,
                "name": dim["name"],
                "message": (
                    f"Dimension '{dim['name']}' is referenced by historical jobs/assessments "
                    "and was safely archived rather than deleted to protect assessment integrity."
                ),
            }
        else:
            del_res = (
                self._db.table("behavioral_dimensions")
                .delete()
                .eq("id", dimension_id)
                .execute()
            )
            self._raise_if_error(del_res)
            return {
                "action": "deleted",
                "id": dimension_id,
                "name": dim["name"],
                "message": f"Dimension '{dim['name']}' was successfully deleted.",
            }

    def reorder_dimensions(self, items: List[DimensionReorderItem]) -> List[dict]:
        """Update display ordering for a list of dimensions."""
        for item in items:
            self._db.table("behavioral_dimensions").update(
                {"order_index": item.order_index, "updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", str(item.id)).execute()
        return self.list_dimensions_admin(include_archived=True)

    # ── Indicators (Admin) ────────────────────────────────────────────────────

    def add_indicator(self, dimension_id: str, payload: IndicatorCreate) -> dict:
        """Add an observable indicator to a dimension."""
        # Check dimension exists
        dim = self._fetch_one("behavioral_dimensions", "id", id=dimension_id)
        if not dim:
            raise ValueError("Dimension not found.")

        # Check duplicate name within this dimension
        dup = self._fetch_one(
            "behavioral_indicators", "id",
            dimension_id=dimension_id, name=payload.name,
        )
        if dup:
            raise ValueError(f"Indicator '{payload.name}' already exists in this dimension.")

        row = {
            "dimension_id": dimension_id,
            "name": payload.name,
            "description": payload.description,
            "example_behaviors": payload.example_behaviors,
            "order_index": payload.order_index,
            "is_active": True,
        }
        try:
            res = (
                self._db.table("behavioral_indicators")
                .insert(row)
                .select("id, dimension_id, name, description, example_behaviors, order_index, is_active, created_at, updated_at")
                .execute()
            )
            self._raise_if_error(res)
        except Exception as exc:
            logger.error(
                "Supabase insert failed for behavioral_indicators. Row: %s. Error: %s",
                row, exc, exc_info=True,
            )
            raise
        data = _safe_data(res)
        return data[0] if data else row

    def update_indicator(self, indicator_id: str, payload: IndicatorUpdate) -> dict:
        """Update an indicator row."""
        existing = self._fetch_one(
            "behavioral_indicators", "id, dimension_id, name", id=indicator_id
        )
        if not existing:
            raise ValueError("Indicator not found.")

        update_data = {
            k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None
        }

        # If name is changed, check for conflict within the same dimension
        if "name" in update_data and update_data["name"] != existing.get("name"):
            conflict = self._fetch_one(
                "behavioral_indicators", "id",
                dimension_id=existing["dimension_id"], name=update_data["name"],
            )
            if conflict and str(conflict.get("id")) != str(indicator_id):
                raise ValueError(f"Indicator name '{update_data['name']}' is already in use in this dimension.")

        if not update_data:
            return existing

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = (
            self._db.table("behavioral_indicators")
            .update(update_data)
            .eq("id", indicator_id)
            .execute()
        )
        self._raise_if_error(res)
        data = _safe_data(res)
        return data[0] if data else update_data

    def delete_indicator(self, indicator_id: str) -> dict:
        """Delete an indicator row."""
        res = (
            self._db.table("behavioral_indicators")
            .delete()
            .eq("id", indicator_id)
            .execute()
        )
        self._raise_if_error(res)
        return {"action": "deleted", "id": indicator_id}

    # ── Validation & Publishing ───────────────────────────────────────────────

    def validate_framework(self) -> FrameworkValidationResult:
        """
        Validate the current framework state prior to version activation:
          - Minimum 3 active dimensions.
          - Each active dimension must have at least 2 active observable indicators.
          - Valid descriptions and names.
          - No duplicate names.
        """
        dimensions = self.list_dimensions_admin(include_archived=False)
        active_dims = [d for d in dimensions if d.get("is_active") and d.get("status") == "active"]

        errors: List[str] = []
        warnings: List[str] = []

        if len(active_dims) < 3:
            errors.append(f"Framework must have at least 3 active dimensions (currently {len(active_dims)}).")

        seen_dim_names = set()
        total_indicators = 0

        for d in active_dims:
            name = d.get("name", "")
            if name in seen_dim_names:
                errors.append(f"Duplicate dimension name detected: '{name}'.")
            seen_dim_names.add(name)

            indicators = d.get("indicators", [])
            active_inds = [i for i in indicators if i.get("is_active", True)]
            total_indicators += len(active_inds)

            if len(active_inds) < 2:
                errors.append(
                    f"Dimension '{name}' has only {len(active_inds)} active indicators. Minimum required is 2."
                )

            # Check indicator descriptions and duplicates
            seen_ind_names = set()
            for ind in active_inds:
                ind_name = ind.get("name", "")
                if ind_name in seen_ind_names:
                    errors.append(f"Dimension '{name}' has duplicate indicator: '{ind_name}'.")
                seen_ind_names.add(ind_name)

                if not ind.get("description") or len(ind.get("description", "").strip()) < 5:
                    errors.append(
                        f"Indicator '{ind_name}' in dimension '{name}' has an insufficient description."
                    )

        if len(active_dims) > 12:
            warnings.append(
                f"Having {len(active_dims)} dimensions may lengthen candidate assessments significantly."
            )

        return FrameworkValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            active_dimension_count=len(active_dims),
            total_indicator_count=total_indicators,
        )

    def publish_version(
        self,
        payload: FrameworkVersionPublish,
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Publish and activate a new framework version.
        Validates integrity, freezes snapshot, supersedes previous active version.
        """
        val_result = self.validate_framework()
        if not val_result.valid:
            raise ValueError(
                f"Framework validation failed: {'; '.join(val_result.errors)}"
            )

        # Build snapshot from active dimensions
        active_dims = self.list_dimensions_admin(include_archived=False)
        snapshot = []
        for d in active_dims:
            if not d.get("is_active") or d.get("status") != "active":
                continue
            active_indicators = [
                {
                    "id": str(i.get("id")),
                    "name": i.get("name"),
                    "description": i.get("description"),
                    "example_behaviors": i.get("example_behaviors"),
                    "order_index": i.get("order_index", 0),
                    "is_active": i.get("is_active", True),
                }
                for i in d.get("indicators", [])
                if i.get("is_active", True)
            ]
            snapshot.append({
                "id": str(d.get("id")),
                "name": d.get("name"),
                "description": d.get("description"),
                "order_index": d.get("order_index", 0),
                "status": d.get("status"),
                "is_active": d.get("is_active"),
                "indicators": active_indicators,
            })

        # Determine next version number
        versions = self.list_versions()
        max_v = max([v.get("version_number", 0) for v in versions], default=0)
        next_v = max_v + 1

        now = datetime.now(timezone.utc).isoformat()

        # Archive existing active version(s)
        try:
            self._db.table("framework_versions").update({"status": "archived"}).eq("status", "active").execute()
        except Exception as exc:
            logger.warning("Could not archive existing active versions: %s", exc)

        # Insert new active version
        version_row = {
            "version_number": next_v,
            "name": payload.name,
            "description": payload.description or f"Framework Version {next_v}",
            "status": "active",
            "dimensions_snapshot": snapshot,
            "activated_at": now,
            "created_by": created_by,
        }

        res = (
            self._db.table("framework_versions")
            .insert(version_row)
            .select("id, version_number, name, description, status, dimensions_snapshot, created_at, activated_at, created_by")
            .execute()
        )
        self._raise_if_error(res)
        data = _safe_data(res)
        created_version = data[0] if data else version_row

        logger.info("Successfully published Framework Version %d: %s", next_v, payload.name)
        return created_version
