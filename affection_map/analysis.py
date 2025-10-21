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
    """Return the Pearson correlation between two value arrays."""
    if np.all(first == first[0]) or np.all(second == second[0]):
        return 0.0
    corr, _ = pearsonr(first, second)
    return float(corr)


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
        (
            f"\nGreatest shared enthusiasm: {CATEGORIES[strongest_alignment]} — both of you score "
            "high here, so this language may feel especially natural together."
        )
    )
    summary.append(
        (
            f"Most aligned expectations: {CATEGORIES[closest_alignment]} — your giving and receiving "
            "scores are the closest match in this area."
        )
    )
    summary.append(
        (
            f"Greatest mismatch: {CATEGORIES[largest_gap]} — focus on sharing preferences here to bridge "
            "the gap between how one of you gives and the other prefers to receive."
        )
    )

    return "\n\n".join(summary)


def interpret_correlation(giver: str, receiver: str, value: float, description: str) -> str:
    """Return text summarising the strength of a correlation value."""
    strength = "low"
    if value >= 0.75:
        strength = "very strong"
    elif value >= 0.5:
        strength = "strong"
    elif value >= 0.25:
        strength = "moderate"
    elif value <= -0.25:
        strength = "challenging"

    return (
        f"{giver} → {receiver}: r = {value:.2f}. This indicates {strength} alignment in {description}."
    )
