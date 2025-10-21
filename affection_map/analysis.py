"""Core data analysis for the AffectionMap application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.stats import pearsonr

CATEGORIES: List[str] = [
    "Words of Affirmation",
    "Acts of Service",
    "Receiving Gifts",
    "Quality Time",
    "Physical Touch",
]


@dataclass
class PersonProfile:
    """Container for an individual's love language values."""

    name: str
    giving: np.ndarray
    receiving: np.ndarray


def correlation(first: np.ndarray, second: np.ndarray) -> float:
    """Return Pearson's r. np.nan if either input lacks variance or lengths mismatch."""
    x = np.asarray(first, dtype=float).ravel()
    y = np.asarray(second, dtype=float).ravel()

    if x.shape != y.shape:
        raise ValueError("correlation requires arrays of equal length")

    n = x.size
    if n < 2:
        return float("nan")

    # r is undefined if either sample variance is ~0
    if np.isclose(np.var(x, ddof=1), 0.0) or np.isclose(np.var(y, ddof=1), 0.0):
        return float("nan")

    r, _ = pearsonr(x, y)
    return float(r)


def close_loop(values: np.ndarray) -> np.ndarray:
    """Append the first value to the end so radar plots close properly."""
    return np.concatenate((values, [values[0]]))


def polar_angles(category_count: int | None = None) -> List[float]:
    """Return evenly spaced polar angles for the provided category count."""
    total = category_count or len(CATEGORIES)
    angles = np.linspace(0, 2 * np.pi, total, endpoint=False).tolist()
    angles += angles[:1]
    return angles


def build_explanation(
    person_a: PersonProfile,
    person_b: PersonProfile,
    corr_a_to_b: float,
    corr_b_to_a: float,
) -> str:
    """Generate narrative text describing how two profiles align."""
    summary = [
        interpret_correlation(
            person_a.name,
            person_b.name,
            corr_a_to_b,
            "how well what they like to give matches what their partner enjoys receiving",
        ),
        interpret_correlation(
            person_b.name,
            person_a.name,
            corr_b_to_a,
            "how well their giving style lands for their partner",
        ),
    ]

    strongest_alignment = np.argmax((person_a.giving + person_b.receiving) / 2)
    closest_alignment = np.argmin(np.abs(person_a.giving - person_b.receiving))
    largest_gap = np.argmax(np.abs(person_a.giving - person_b.receiving))

    summary.append(
        f"\nGreatest shared enthusiasm: {CATEGORIES[strongest_alignment]} - both of you score high here."
    )
    summary.append(
        f"Most aligned expectations: {CATEGORIES[closest_alignment]} - your giving and receiving are closest here."
    )
    summary.append(
        f"Largest gap: {CATEGORIES[largest_gap]} - discuss preferences here to bridge differences."
    )

    return "\n\n".join(summary)


def interpret_correlation(giver: str, receiver: str, value: float, description: str) -> str:
    """Summarize the strength and direction of Pearson's r with clearer buckets."""
    if not np.isfinite(value):
        return (
            f"{giver} → {receiver}: r is undefined. "
            f"Insufficient variation to assess {description}."
        )

    abs_r = abs(value)
    if abs_r >= 0.90:
        strength = "near perfect"
    elif abs_r >= 0.70:
        strength = "strong"
    elif abs_r >= 0.40:
        strength = "moderate"
    elif abs_r >= 0.20:
        strength = "weak"
    else:
        strength = "minimal or mixed"

    direction = "alignment" if value >= 0 else "inverse alignment"
    return f"{giver} → {receiver}: r = {value:.2f}. {strength} {direction} in {description}."
