"""Weighted scoring and Long/Short setup classification."""

from __future__ import annotations


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def trend_alignment(price: float, sma20: float | None, sma50: float | None, sma200: float | None) -> float:
    """Returns a value in [-1, 1]. Positive = bullish stack, negative = bearish stack."""
    checks = []
    if sma20 is not None:
        checks.append(1 if price > sma20 else -1)
    if sma20 is not None and sma50 is not None:
        checks.append(1 if sma20 > sma50 else -1)
    if sma50 is not None and sma200 is not None:
        checks.append(1 if sma50 > sma200 else -1)
    if not checks:
        return 0.0
    return sum(checks) / len(checks)


def compute_score(rvol_value: float, gap_pct_value: float, trend_alignment_value: float,
                   atr_pct_value: float, weights: dict[str, float]) -> float:
    rvol_score = _clip01(rvol_value / 5.0)
    gap_score = _clip01(abs(gap_pct_value) / 10.0)
    trend_score = _clip01(abs(trend_alignment_value))
    atr_score = _clip01(atr_pct_value / 5.0)

    total_weight = sum(weights.values()) or 1.0
    weighted = (
        weights.get("rvol", 0) * rvol_score
        + weights.get("gap", 0) * gap_score
        + weights.get("trend", 0) * trend_score
        + weights.get("atr_pct", 0) * atr_score
    )
    return round((weighted / total_weight) * 100, 2)


def classify_setup(gap_pct_value: float, trend_alignment_value: float, min_gap_pct: float) -> str | None:
    if gap_pct_value >= min_gap_pct:
        return "Long Watch"
    if gap_pct_value <= -min_gap_pct:
        return "Short Watch"
    return None
