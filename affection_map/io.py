"""Import/export helpers for AffectionMap profiles."""
from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Sequence
from typing import Dict

import numpy as np

from .analysis import CATEGORIES, PersonProfile


class ProfileDataError(RuntimeError):
    """Raised when an imported profile payload is malformed."""


def profiles_to_payload(profiles: Dict[str, PersonProfile]) -> Dict[str, object]:
    return {
        person_id: {
            "name": profile.name,
            "giving": profile.giving.tolist(),
            "receiving": profile.receiving.tolist(),
        }
        for person_id, profile in profiles.items()
    }


def payload_to_profiles(payload: Dict[str, object]) -> Dict[str, PersonProfile]:
    profiles: Dict[str, PersonProfile] = {}
    for person_id in ("person_a", "person_b"):
        raw = payload.get(person_id)
        if not isinstance(raw, dict):
            raise ProfileDataError(f"Missing profile data for {person_id}")

        name = str(raw.get("name", ""))
        giving = _coerce_values(raw.get("giving"), person_id, "giving")
        receiving = _coerce_values(raw.get("receiving"), person_id, "receiving")

        profiles[person_id] = PersonProfile(name=name, giving=giving, receiving=receiving)
    return profiles


def _coerce_values(values: object, person_id: str, key: str) -> np.ndarray:
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise ProfileDataError(f"{person_id}.{key} must be a sequence")

    numeric = []
    for value in values:
        try:
            numeric.append(float(value))
        except (TypeError, ValueError) as error:  # pragma: no cover - defensive
            raise ProfileDataError(f"{person_id}.{key} contains non-numeric values") from error

    if len(numeric) != len(CATEGORIES):
        raise ProfileDataError(
            f"{person_id}.{key} must contain {len(CATEGORIES)} values (found {len(numeric)})"
        )

    arr = np.asarray(numeric, dtype=float)
    arr = np.clip(arr, 0.0, 10.0)
    return arr


def dump_profiles_to_file(path: Path, profiles: Dict[str, PersonProfile]) -> None:
    data = profiles_to_payload(profiles)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_profiles_from_file(path: Path) -> Dict[str, PersonProfile]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProfileDataError("Profile file must contain a JSON object")
    return payload_to_profiles(data)


__all__ = [
    "ProfileDataError",
    "profiles_to_payload",
    "payload_to_profiles",
    "dump_profiles_to_file",
    "load_profiles_from_file",
]
