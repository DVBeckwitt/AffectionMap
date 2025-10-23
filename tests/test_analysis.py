import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))

from affection_map.analysis import correlation


def test_correlation_matches_perfect_positive() -> None:
    x = np.array([0, 2, 4, 6, 8], float)
    y = x + 3.7
    assert np.isclose(correlation(x, y), 1.0)


def test_correlation_matches_perfect_negative() -> None:
    x = np.array([0, 2, 4, 6, 8], float)
    y = -2 * x
    assert np.isclose(correlation(x, y), -1.0)


def test_correlation_handles_constant_vectors() -> None:
    x = np.array([0, 2, 4, 6, 8], float)
    c = np.full(5, 5.0)
    assert not np.isfinite(correlation(c, x))
    assert not np.isfinite(correlation(c, c))


def test_correlation_invariant_to_translation_and_scale() -> None:
    x = np.array([0, 2, 4, 6, 8], float)
    z = 10 - x
    assert np.isclose(correlation(x, z), -1.0)
