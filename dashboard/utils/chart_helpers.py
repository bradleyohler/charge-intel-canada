from __future__ import annotations


def coverage_score_color(score: float) -> str:
    if score >= 70:
        return "#2ecc71"
    elif score >= 40:
        return "#f1c40f"
    else:
        return "#e74c3c"


def format_rate(rate: float | None) -> str:
    if rate is None:
        return "N/A"
    return f"${rate:.4f}/kWh"
