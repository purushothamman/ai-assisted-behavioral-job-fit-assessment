"""
fairness/
Dedicated demographic fairness evaluation & audit package.

Exclusively for platform administrators to evaluate demographic parity difference (DPD),
equal opportunity difference (EOD), and subgroup recall on controlled evaluation datasets.
Demographic data is strictly partitioned from candidate scoring and live hiring pipelines.
"""
from app.fairness.metrics import calculate_fairness_metrics

__all__ = ["calculate_fairness_metrics"]
