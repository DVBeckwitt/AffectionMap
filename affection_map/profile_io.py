"""Utilities for serializing and deserializing love language profiles."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import json

import numpy as np

from .analysis import CATEGORIES, PersonProfile

PROFILE_SCHEMA = "affection_map_profile"
PROFILE_VERSION = 1


def profile_to_payload(profile: PersonProfile) -> Dict[str, Any]:
    """Return a JSON-serialisable payload for *profile*."""

    return {
        "schema": PROFILE_SCHEMA,
        "version": PROFILE_VERSION,
        "name": profile.name,
        "categories": list(CATEGORIES),
        "giving": profile.giving.astype(float).tolist(),
        "receiving": profile.receiving.astype(float).tolist(),
    }


def _extract_values(payload: Mapping[str, Any], key: str) -> np.ndarray:
    raw_values = payload.get(key)
    if not isinstance(raw_values, (list, tuple)):
        raise ValueError(f"'{key}' must be a list of numbers")

    array = np.asarray(raw_values, dtype=float)
    if array.ndim != 1 or array.size != len(CATEGORIES):
        raise ValueError(
            f"'{key}' must contain {len(CATEGORIES)} numeric values"
        )

    if not np.all(np.isfinite(array)):
        raise ValueError(f"'{key}' contains non-finite values")

    if np.any((array < 0.0) | (array > 10.0)):
        raise ValueError(f"'{key}' values must be between 0 and 10")

    return array.astype(float)


def payload_to_profile(payload: Mapping[str, Any]) -> PersonProfile:
    """Convert *payload* to a :class:`PersonProfile`."""

    if not isinstance(payload, Mapping):
        raise ValueError("Profile payload must be a mapping")

    schema = payload.get("schema")
    if schema not in (None, PROFILE_SCHEMA):
        raise ValueError("Unrecognised profile schema")

    version = payload.get("version")
    if version not in (None, PROFILE_VERSION):
        raise ValueError("Unsupported profile version")

    categories = payload.get("categories")
    if categories is not None and list(categories) != list(CATEGORIES):
        raise ValueError("Profile categories do not match this application")

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Profile 'name' must be a non-empty string")

    giving = _extract_values(payload, "giving")
    receiving = _extract_values(payload, "receiving")

    return PersonProfile(name=name.strip(), giving=giving, receiving=receiving)


def dump_profile_to_file(profile: PersonProfile, path: str | Path) -> None:
    """Write *profile* to *path* as JSON."""

    file_path = Path(path)
    payload = profile_to_payload(profile)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def load_profile_from_file(path: str | Path) -> PersonProfile:
    """Load a :class:`PersonProfile` from *path*."""

    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as error:
        raise ValueError("File is not valid JSON") from error

    return payload_to_profile(payload)

