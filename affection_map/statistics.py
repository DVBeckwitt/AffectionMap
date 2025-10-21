"""Statistical helpers with optional SciPy integration."""
from __future__ import annotations

import numpy as np

try:  # pragma: no cover - SciPy may be unavailable in some environments
    from scipy.stats import pearsonr as _pearsonr  # type: ignore
except Exception:  # pragma: no cover - fallback path when SciPy is missing
    _pearsonr = None  # type: ignore


def pearson_correlation(first: np.ndarray, second: np.ndarray) -> float:
    """Return the Pearson correlation coefficient for the provided arrays.

    The function first tries to delegate to :func:`scipy.stats.pearsonr` when it
    is available. If SciPy cannot be imported the calculation falls back to the
    NumPy implementation which offers the same semantics for our 1-D inputs.
    """

    first_arr = np.asarray(first, dtype=float)
    second_arr = np.asarray(second, dtype=float)

    if first_arr.shape != second_arr.shape:
        raise ValueError("Correlation arrays must have identical shapes")

    if _pearsonr is not None:
        corr, _ = _pearsonr(first_arr, second_arr)
        return float(corr)

    # NumPy's corrcoef returns a 2x2 matrix when called with two vectors. The
    # off-diagonal entry contains the Pearson correlation coefficient.
    coeffs = np.corrcoef(first_arr, second_arr)
    return float(coeffs[0, 1])


__all__ = ["pearson_correlation"]
