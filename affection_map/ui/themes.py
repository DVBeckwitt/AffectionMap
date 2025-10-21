"""Color themes for the AffectionMap radar charts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Theme:
    """Visual settings for a single radar plot rendering."""

    name: str
    background: str
    grid: str
    series_colors: Dict[str, str]


THEMES = {
    "Classic": Theme(
        name="Classic",
        background="#ffffff",
        grid="#d0d0d0",
        series_colors={
            "a_to_b": "#C44E52",
            "b_to_a": "#4C72B0",
        },
    ),
    "Sunset": Theme(
        name="Sunset",
        background="#fff6e5",
        grid="#f0c9a6",
        series_colors={
            "a_to_b": "#F05A71",
            "b_to_a": "#8B5CF6",
        },
    ),
    "Forest": Theme(
        name="Forest",
        background="#f3f8f4",
        grid="#a5c1a7",
        series_colors={
            "a_to_b": "#2F855A",
            "b_to_a": "#2B6CB0",
        },
    ),
}


DEFAULT_THEME = THEMES["Classic"]

__all__ = ["Theme", "THEMES", "DEFAULT_THEME"]
