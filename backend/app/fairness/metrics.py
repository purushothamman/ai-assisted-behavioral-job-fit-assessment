"""
fairness/metrics.py
Pure Python, deterministic calculation of demographic fairness metrics:
  - Demographic Parity Difference (DPD) & Selection Rates
  - Equal Opportunity Difference (EOD) & Subgroup Recall (True Positive Rate)
  - Adverse Impact Ratio (Four-Fifths / 80% Rule)
  - Subgroup Sample Size Verification & Reliability Warnings

Design Principles:
  1. 100% deterministic, LLM-free, external API-free mathematics.
  2. Explicit zero-denominator guards — never raises ZeroDivisionError or emits NaN.
  3. Ground-truth validation: EOD is strictly calculated ONLY when valid outcome
     labels exist for all evaluated groups.
  4. Explicit limitations and small-sample warnings (default threshold N < 30).
  5. Never infers or fabricates demographic attributes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_MIN_SAMPLE_SIZE = 30
DEFAULT_SCORE_THRESHOLD = 70.0


@dataclass
class SubgroupMetrics:
    """Calculated metrics for a single demographic subgroup."""
    group: str
    sample_count: int
    selection_count: int
    selection_rate: Optional[float]
    rate_difference_from_reference: Optional[float] = None
    adverse_impact_ratio: Optional[float] = None
    ground_truth_positives: Optional[int] = None
    ground_truth_negatives: Optional[int] = None
    true_positives: Optional[int] = None
    false_positives: Optional[int] = None
    false_negatives: Optional[int] = None
    true_negatives: Optional[int] = None
    recall: Optional[float] = None  # True Positive Rate: TP / (TP + FN)
    recall_difference_from_reference: Optional[float] = None
    has_sample_warning: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass
class FairnessMetricsResult:
    """Complete demographic fairness evaluation report."""
    sensitive_attribute: str
    reference_group: str
    total_samples: int
    evaluated_threshold: float
    has_ground_truth: bool
    demographic_parity_difference: Optional[float]  # max(SR) - min(SR)
    equal_opportunity_difference: Optional[float]   # max(TPR) - min(TPR), None if no GT
    subgroup_metrics: List[SubgroupMetrics]
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


def _resolve_binary_prediction(
    score: Optional[float],
    prediction: Optional[int],
    threshold: float,
) -> Optional[int]:
    """
    Resolve binary selection outcome (1 = qualified/selected, 0 = not).
    If prediction is explicitly provided (0 or 1), use it.
    Else if score is provided, apply score >= threshold.
    Returns None if neither is available.
    """
    if prediction is not None and prediction in (0, 1):
        return int(prediction)
    if score is not None:
        try:
            return 1 if float(score) >= threshold else 0
        except (ValueError, TypeError):
            return None
    return None


def calculate_fairness_metrics(
    records: List[Dict[str, Any]],
    sensitive_attribute: str = "demographic_group",
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
    reference_group: Optional[str] = None,
) -> FairnessMetricsResult:
    """
    Calculate demographic parity difference, equal opportunity difference,
    and subgroup recall across groups in an evaluation dataset.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        List of records. Each record must contain:
          - 'group' (or record[sensitive_attribute]): str
          - 'score' (float 0-100) OR 'prediction' (int 0 or 1)
          - 'ground_truth': optional int (0 or 1, or None)
    sensitive_attribute : str
        Human-readable name of the evaluated attribute (e.g. 'gender', 'age_group').
    score_threshold : float
        Cutoff score for binary qualification when scores are provided (default 70.0).
    min_sample_size : int
        Observation count below which a sample-size warning is issued (default 30).
    reference_group : Optional[str]
        Subgroup to compare disparities against. If None, the group with the largest
        sample size is selected as the baseline reference.

    Returns
    -------
    FairnessMetricsResult
        Structured audit report containing subgroup rates, disparities, warnings,
        and scientific limitations.
    """
    warnings: List[str] = []
    limitations: List[str] = [
        "Demographic parity and equal opportunity measure fundamentally distinct notions of algorithmic fairness. "
        "Satisfying one does not imply or guarantee satisfaction of the other.",
        f"A Demographic Parity Difference near 0 does not prove the absence of systemic bias; "
        f"it reflects parity solely for the decision threshold ({score_threshold}) on this evaluated sample.",
        "Audits evaluate aggregate statistical properties of the submitted dataset and do not generalize to unobserved distributions.",
        "Demographic attributes must NEVER be used for individual candidate scoring, ranking, or automated hiring decisions.",
    ]

    if not records:
        return FairnessMetricsResult(
            sensitive_attribute=sensitive_attribute,
            reference_group=reference_group or "none",
            total_samples=0,
            evaluated_threshold=score_threshold,
            has_ground_truth=False,
            demographic_parity_difference=None,
            equal_opportunity_difference=None,
            subgroup_metrics=[],
            warnings=["Evaluation dataset is empty. No metrics could be calculated."],
            limitations=limitations,
        )

    # 1. Group records by demographic group
    groups_data: Dict[str, List[Dict[str, Any]]] = {}
    total_valid_records = 0

    for idx, r in enumerate(records):
        raw_group = r.get("group") or r.get(sensitive_attribute)
        if raw_group is None:
            warnings.append(f"Record at index {idx} omitted: missing group value.")
            continue
        g_name = str(raw_group).strip()
        if not g_name:
            warnings.append(f"Record at index {idx} omitted: empty group string.")
            continue

        pred = _resolve_binary_prediction(r.get("score"), r.get("prediction"), score_threshold)
        if pred is None:
            warnings.append(f"Record at index {idx} omitted: missing both valid score and prediction.")
            continue

        gt = r.get("ground_truth")
        gt_val: Optional[int] = None
        if gt is not None:
            try:
                gt_int = int(gt)
                if gt_int in (0, 1):
                    gt_val = gt_int
            except (ValueError, TypeError):
                gt_val = None

        if g_name not in groups_data:
            groups_data[g_name] = []
        groups_data[g_name].append({
            "prediction": pred,
            "ground_truth": gt_val,
        })
        total_valid_records += 1

    if not groups_data:
        return FairnessMetricsResult(
            sensitive_attribute=sensitive_attribute,
            reference_group=reference_group or "none",
            total_samples=0,
            evaluated_threshold=score_threshold,
            has_ground_truth=False,
            demographic_parity_difference=None,
            equal_opportunity_difference=None,
            subgroup_metrics=[],
            warnings=["No valid records found after schema filtering."] + warnings,
            limitations=limitations,
        )

    if len(groups_data) < 2:
        warnings.append(
            f"Dataset contains only 1 group ('{next(iter(groups_data.keys()))}'). "
            "Disparity metrics (DPD/EOD) require at least 2 distinct demographic groups."
        )

    # 2. Check dataset sample size
    if total_valid_records < min_sample_size:
        warnings.append(
            f"Total sample count ({total_valid_records}) is below the minimum recommended "
            f"threshold ({min_sample_size}). Disparity metrics have high sampling error."
        )

    # 3. Determine reference group
    if reference_group and reference_group in groups_data:
        ref_group_name = reference_group
    else:
        # Default to group with largest sample count
        ref_group_name = max(groups_data.keys(), key=lambda g: len(groups_data[g]))

    # 4. Check ground-truth availability across all records
    gt_record_count = sum(
        1 for items in groups_data.values() for item in items if item["ground_truth"] is not None
    )
    has_full_ground_truth = (gt_record_count == total_valid_records) and (gt_record_count > 0)
    has_partial_ground_truth = (0 < gt_record_count < total_valid_records)

    if has_partial_ground_truth:
        warnings.append(
            f"Ground-truth outcome labels are partially missing ({gt_record_count}/{total_valid_records} present). "
            "Equal Opportunity Difference was not calculated to prevent biased attrition estimation."
        )
    elif gt_record_count == 0:
        warnings.append(
            "Ground-truth outcome labels are unavailable in this dataset. "
            "Equal Opportunity Difference (EOD) and Subgroup Recall were not calculated."
        )

    # 5. Compute per-subgroup metrics
    subgroup_results: List[SubgroupMetrics] = []
    selection_rates: Dict[str, float] = {}
    recalls: Dict[str, Optional[float]] = {}
    eod_computable_for_all_groups = has_full_ground_truth and len(groups_data) >= 2

    for g_name, items in groups_data.items():
        n_g = len(items)
        subgroup_warns: List[str] = []

        if n_g < min_sample_size:
            subgroup_warns.append(
                f"Subgroup '{g_name}' has {n_g} observations (< {min_sample_size}). "
                "Estimates for this subgroup exhibit high sampling variance."
            )

        # Selection rate
        sel_count = sum(item["prediction"] for item in items)
        sel_rate = round(sel_count / n_g, 4) if n_g > 0 else None
        if sel_rate is not None:
            selection_rates[g_name] = sel_rate

        # Ground truth / Recall calculations
        gt_pos: Optional[int] = None
        gt_neg: Optional[int] = None
        tp: Optional[int] = None
        fp: Optional[int] = None
        fn: Optional[int] = None
        tn: Optional[int] = None
        recall: Optional[float] = None

        if has_full_ground_truth:
            gt_pos = sum(1 for it in items if it["ground_truth"] == 1)
            gt_neg = sum(1 for it in items if it["ground_truth"] == 0)
            tp = sum(1 for it in items if it["prediction"] == 1 and it["ground_truth"] == 1)
            fp = sum(1 for it in items if it["prediction"] == 1 and it["ground_truth"] == 0)
            fn = sum(1 for it in items if it["prediction"] == 0 and it["ground_truth"] == 1)
            tn = sum(1 for it in items if it["prediction"] == 0 and it["ground_truth"] == 0)

            if gt_pos > 0:
                recall = round(tp / gt_pos, 4)
                recalls[g_name] = recall
            else:
                recall = None
                recalls[g_name] = None
                subgroup_warns.append(
                    f"Subgroup '{g_name}' has 0 positive ground-truth outcomes. Recall is undefined."
                )
                eod_computable_for_all_groups = False

        subgroup_results.append(SubgroupMetrics(
            group=g_name,
            sample_count=n_g,
            selection_count=sel_count,
            selection_rate=sel_rate,
            ground_truth_positives=gt_pos,
            ground_truth_negatives=gt_neg,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            recall=recall,
            has_sample_warning=n_g < min_sample_size,
            warnings=subgroup_warns,
        ))

    # 6. Reference group baseline comparisons & adverse impact ratios
    ref_rate = selection_rates.get(ref_group_name)
    ref_recall = recalls.get(ref_group_name)

    for sm in subgroup_results:
        # Rate difference from reference
        if sm.selection_rate is not None and ref_rate is not None:
            sm.rate_difference_from_reference = round(sm.selection_rate - ref_rate, 4)

            # Adverse Impact Ratio (selection_rate / ref_rate)
            if ref_rate > 0:
                air = round(sm.selection_rate / ref_rate, 4)
                sm.adverse_impact_ratio = air
                if air < 0.80 and sm.group != ref_group_name:
                    sm.warnings.append(
                        f"Adverse Impact Ratio ({air:.2f}) is below 0.80 (Four-Fifths Rule threshold) "
                        f"relative to reference group '{ref_group_name}'."
                    )
            elif sm.selection_rate == 0:
                sm.adverse_impact_ratio = 1.0
            else:
                sm.adverse_impact_ratio = None

        # Recall difference from reference
        if sm.recall is not None and ref_recall is not None:
            sm.recall_difference_from_reference = round(sm.recall - ref_recall, 4)

    # 7. Global Disparity Metrics
    # Demographic Parity Difference: max(SR) - min(SR) across all groups
    dpd: Optional[float] = None
    if len(selection_rates) >= 2:
        rates = list(selection_rates.values())
        dpd = round(max(rates) - min(rates), 4)

    # Equal Opportunity Difference: max(TPR) - min(TPR) across all groups
    eod: Optional[float] = None
    valid_recalls = [r for r in recalls.values() if r is not None]
    if eod_computable_for_all_groups and len(valid_recalls) == len(groups_data) and len(valid_recalls) >= 2:
        eod = round(max(valid_recalls) - min(valid_recalls), 4)
    elif has_full_ground_truth and not eod_computable_for_all_groups:
        warnings.append(
            "Equal Opportunity Difference could not be computed because one or more subgroups "
            "have zero positive ground-truth instances."
        )

    return FairnessMetricsResult(
        sensitive_attribute=sensitive_attribute,
        reference_group=ref_group_name,
        total_samples=total_valid_records,
        evaluated_threshold=score_threshold,
        has_ground_truth=has_full_ground_truth,
        demographic_parity_difference=dpd,
        equal_opportunity_difference=eod,
        subgroup_metrics=subgroup_results,
        warnings=warnings,
        limitations=limitations,
    )
