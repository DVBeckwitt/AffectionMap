from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from affection_map.analysis import CATEGORIES, PersonProfile
from affection_map.profile_io import (
    PROFILE_SCHEMA,
    PROFILE_VERSION,
    dump_profile_to_file,
    load_profile_from_file,
    payload_to_profile,
    profile_to_payload,
)


def _sample_profile(name: str = "Casey") -> PersonProfile:
    values = np.arange(len(CATEGORIES), dtype=float)
    return PersonProfile(name=name, giving=values + 1, receiving=values + 2)


def test_profile_to_payload_roundtrip(tmp_path: Path) -> None:
    profile = _sample_profile()
    payload = profile_to_payload(profile)

    assert payload["schema"] == PROFILE_SCHEMA
    assert payload["version"] == PROFILE_VERSION
    assert payload["name"] == profile.name
    assert payload["categories"] == CATEGORIES
    assert payload["giving"] == pytest.approx(profile.giving.tolist())
    assert payload["receiving"] == pytest.approx(profile.receiving.tolist())

    file_path = tmp_path / "profile.json"
    dump_profile_to_file(profile, file_path)

    with file_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    reloaded = payload_to_profile(raw)
    np.testing.assert_allclose(reloaded.giving, profile.giving)
    np.testing.assert_allclose(reloaded.receiving, profile.receiving)
    assert reloaded.name == profile.name


def test_payload_to_profile_rejects_invalid_categories() -> None:
    profile = _sample_profile()
    payload = profile_to_payload(profile)
    payload["categories"] = list(reversed(CATEGORIES))

    with pytest.raises(ValueError):
        payload_to_profile(payload)


def test_payload_to_profile_rejects_out_of_range_values() -> None:
    profile = _sample_profile()
    payload = profile_to_payload(profile)
    payload["giving"][0] = 11

    with pytest.raises(ValueError):
        payload_to_profile(payload)


def test_load_profile_from_file_rejects_invalid_json(tmp_path: Path) -> None:
    file_path = tmp_path / "broken.json"
    file_path.write_text("not json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_profile_from_file(file_path)
