"""
alignment/calculator.py
Deterministic, explainable job-candidate behavioral alignment engine.

Formula:
  Overall Alignment Score = sum(candidate_score_i * job_weight_i) / sum(job_weight_i)

Key Guarantees:
  1. 100% deterministic pure Python math (zero Groq / LLM calls).
  2. Explainable: every dimension's point contribution is explicitly calculated:
     contribution_i = candidate_score_i * (job_weight_i / sum_weights)
     sum(contribution_i) == overall_score
  3. Safe: gracefully handles missing dimensions, zero/invalid weights, empty inputs,
     and division-by-zero edge cases.
  4. Compliant: strictly produces objective analytical observations (strengths and
     review areas). NEVER generates automated hire/reject recommendations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _normalize_dim_name(name: Optional[str]) -> str:
    """Normalize dimension name to lowercase stripped string."""
    if not name or not isinstance(name, str):
        return "unknown"
    return name.strip().lower()


def _format_dim_label(name: str) -> str:
    """Format dimension name for user-friendly display (e.g. 'decision_making' -> 'Decision Making')."""
    return name.replace("_", " ").title()


def calculate_alignment(
    job_requirements: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    candidate_name: str = "",
    job_title: str = "",
) -> Dict[str, Any]:
    """
    Calculate the deterministic weighted alignment between job behavioral requirements
    and a candidate's evaluated response scores.

    Parameters:
      job_requirements: List of dicts representing job requirements, each containing:
        - dimension_name (str)
        - importance (int/float, 0-100)
        - confirmed (bool, optional)
      candidate_scores: List of dicts representing candidate response scores, each containing:
        - dimension_name (str)
        - normalized_score (int/float, 0-100)
        - confidence (float, 0.0-1.0)
        - status (str, e.g. 'scored')
      candidate_name: Optional candidate name for display
      job_title: Optional job title for display

    Returns:
      Dict with overall_score, dimension_alignments, strengths, areas_for_review, and metadata.
    """
    # ── 1. Filter and resolve job requirements ─────────────────────────────
    # If any requirements are confirmed by recruiter, prioritize confirmed ones
    confirmed_reqs = [r for r in (job_requirements or []) if r.get("confirmed")]
    active_reqs = confirmed_reqs if confirmed_reqs else (job_requirements or [])

    # Map requirement dimensions and weights
    # Normalize weights: must be non-negative numeric
    req_map: Dict[str, Dict[str, Any]] = {}
    for r in active_reqs:
        dim = _normalize_dim_name(r.get("dimension_name"))
        if dim == "unknown":
            continue

        raw_importance = r.get("importance", 50)
        try:
            importance = float(raw_importance)
        except (TypeError, ValueError):
            importance = 50.0

        # Clamp weight between 0 and 100
        importance = max(0.0, min(100.0, importance))

        # If duplicate, keep the highest importance
        if dim not in req_map or importance > req_map[dim]["importance"]:
            req_map[dim] = {
                "dimension_name": dim,
                "importance": importance,
                "reason": r.get("reason", ""),
            }

    # ── 2. Aggregate candidate scores per dimension ─────────────────────────
    # A candidate may have answered multiple questions per dimension.
    scores_by_dim: Dict[str, List[float]] = {}
    conf_by_dim: Dict[str, List[float]] = {}
    counts_by_dim: Dict[str, int] = {}

    for s in (candidate_scores or []):
        dim = _normalize_dim_name(s.get("dimension_name"))
        if dim == "unknown":
            continue

        status = s.get("status", "scored")
        # Only aggregate successfully scored responses
        if status == "scored":
            try:
                norm_score = float(s.get("normalized_score", 0))
                norm_score = max(0.0, min(100.0, norm_score))
            except (TypeError, ValueError):
                norm_score = 0.0

            try:
                conf = float(s.get("confidence", 0.0))
                conf = max(0.0, min(1.0, conf))
            except (TypeError, ValueError):
                conf = 0.0

            scores_by_dim.setdefault(dim, []).append(norm_score)
            conf_by_dim.setdefault(dim, []).append(conf)
            counts_by_dim[dim] = counts_by_dim.get(dim, 0) + 1

    # ── 3. Calculate dimension-level alignments ─────────────────────────────
    total_weight = sum(r["importance"] for r in req_map.values())

    dimension_alignments: List[Dict[str, Any]] = []
    assessed_count = 0

    # Process all required dimensions first
    all_dims = list(req_map.keys())
    # Add any dimensions the candidate was evaluated on that were not in requirements
    for c_dim in scores_by_dim.keys():
        if c_dim not in req_map:
            all_dims.append(c_dim)

    for dim in all_dims:
        is_required = dim in req_map
        req_info = req_map.get(dim)
        job_weight = req_info["importance"] if req_info else 0.0

        weight_pct = round((job_weight / total_weight) * 100.0, 1) if total_weight > 0 else 0.0

        if dim in scores_by_dim and scores_by_dim[dim]:
            dim_scores = scores_by_dim[dim]
            candidate_score = round(sum(dim_scores) / len(dim_scores), 1)
            dim_confs = conf_by_dim.get(dim, [0.0])
            dim_conf = round(sum(dim_confs) / len(dim_confs), 2)
            resp_count = counts_by_dim.get(dim, 0)
            status = "assessed" if is_required else "unweighted"
            if is_required:
                assessed_count += 1
        else:
            candidate_score = 0.0
            dim_conf = 0.0
            resp_count = 0
            status = "missing"

        # Points contributed to the overall 0-100 alignment score
        if is_required and total_weight > 0:
            contribution = round(candidate_score * (job_weight / total_weight), 1)
        else:
            contribution = 0.0

        dimension_alignments.append({
            "dimension_name": dim,
            "dimension_label": _format_dim_label(dim),
            "job_weight": round(job_weight, 1),
            "weight_percentage": weight_pct,
            "candidate_score": candidate_score,
            "contribution": contribution,
            "status": status,
            "confidence": dim_conf,
            "response_count": resp_count,
        })

    # Sort dimension alignments: required dimensions by weight descending, then unweighted
    dimension_alignments.sort(
        key=lambda x: (x["status"] != "unweighted", x["job_weight"], x["candidate_score"]),
        reverse=True,
    )

    # ── 4. Calculate overall weighted alignment score ───────────────────────
    # sum(candidate_score * job_weight) / sum(job_weight)
    if total_weight > 0:
        weighted_sum = sum(
            d["candidate_score"] * d["job_weight"]
            for d in dimension_alignments
            if d["status"] in ("assessed", "missing")
        )
        raw_overall = weighted_sum / total_weight
        overall_score = round(max(0.0, min(100.0, raw_overall)), 1)
    else:
        # If no requirements or total weight is 0, fallback to simple mean of assessed scores
        assessed_scores = [d["candidate_score"] for d in dimension_alignments if d["status"] == "assessed"]
        overall_score = round(sum(assessed_scores) / len(assessed_scores), 1) if assessed_scores else 0.0

    # Overall average confidence across assessed dimensions
    assessed_confs = [d["confidence"] for d in dimension_alignments if d["status"] == "assessed"]
    avg_conf = round(sum(assessed_confs) / len(assessed_confs), 2) if assessed_confs else 0.0

    # ── 5. Generate Explainable Strengths & Review Areas ─────────────────────
    # Strictly objective observations. No automated hiring decisions.
    strengths: List[str] = []
    areas_for_review: List[str] = []

    for item in dimension_alignments:
        dim_lbl = item["dimension_label"]
        c_score = item["candidate_score"]
        j_wt = item["job_weight"]
        contrib = item["contribution"]
        st = item["status"]

        if st == "missing":
            areas_for_review.append(
                f"Missing evaluation for '{dim_lbl}' (Job Weight: {j_wt}): "
                "No candidate response was recorded for this behavioral requirement."
            )
        elif st == "assessed":
            # Strengths: high candidate score on important dimension
            if c_score >= 75.0 and j_wt >= 30.0:
                strengths.append(
                    f"Strong behavioral alignment in '{dim_lbl}' (Score: {c_score}/100, Job Weight: {j_wt}): "
                    f"Demonstrated clear indicators, contributing +{contrib} pts to overall alignment."
                )

            # Areas for review: lower candidate score on high-priority dimension
            if j_wt >= 70.0 and c_score < 60.0:
                areas_for_review.append(
                    f"Priority competency gap in '{dim_lbl}' (Score: {c_score}/100, Job Weight: {j_wt}): "
                    "This competency is high priority for the role. Recommend exploring situational examples during interview."
                )
            elif j_wt >= 40.0 and c_score < 50.0:
                areas_for_review.append(
                    f"Review opportunity in '{dim_lbl}' (Score: {c_score}/100, Job Weight: {j_wt}): "
                    "Score was below expected benchmark for this requirement."
                )

            # Confidence review
            if item["confidence"] > 0 and item["confidence"] < 0.45:
                areas_for_review.append(
                    f"Low confidence ({int(item['confidence'] * 100)}%) for '{dim_lbl}': "
                    "Candidate answer was brief; consider asking for more detail."
                )

    # General strength check if candidate is broadly solid
    all_assessed_scores = [d["candidate_score"] for d in dimension_alignments if d["status"] == "assessed"]
    if all_assessed_scores and all(s >= 70.0 for s in all_assessed_scores) and len(all_assessed_scores) >= 2:
        strengths.insert(0, "Consistent proficiency demonstrated across all evaluated behavioral requirements.")

    # Fallback notices if empty
    if not strengths and overall_score >= 60.0:
        strengths.append("Demonstrated acceptable baseline behavioral responses across required competencies.")
    elif not strengths:
        strengths.append("Responses met baseline completion criteria; refer to specific dimension scores.")

    if not areas_for_review:
        areas_for_review.append("No critical competency gaps identified across evaluated dimensions.")

    return {
        "candidate_name": candidate_name,
        "job_title": job_title,
        "overall_score": overall_score,
        "total_weight": int(total_weight),
        "total_dimensions_count": len(req_map),
        "assessed_dimensions_count": assessed_count,
        "average_confidence": avg_conf,
        "dimension_alignments": dimension_alignments,
        "strengths": strengths,
        "areas_for_review": areas_for_review,
        "metadata": {
            "is_weighted": total_weight > 0,
            "has_unassessed_dimensions": any(d["status"] == "missing" for d in dimension_alignments),
        },
    }
