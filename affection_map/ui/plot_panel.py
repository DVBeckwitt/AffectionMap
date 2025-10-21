"""Matplotlib radar chart integration for the AffectionMap UI."""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import ttk

from ..analysis import CATEGORIES, PersonProfile, close_loop, polar_angles
from .themes import DEFAULT_THEME, Theme


class RadarPlotPanel:
    """Display side-by-side radar charts for the current profiles."""

    def __init__(self, parent: ttk.Frame, *, theme: Theme = DEFAULT_THEME) -> None:
        self._container = ttk.Frame(parent)
        self._container.columnconfigure(0, weight=1)
        self._container.rowconfigure(0, weight=1)

        self._figure = Figure(figsize=(6.2, 4.8), tight_layout=True)
        self._axes = (
            self._figure.add_subplot(1, 2, 1, polar=True),
            self._figure.add_subplot(1, 2, 2, polar=True),
        )
        self._canvas = FigureCanvasTkAgg(self._figure, master=self._container)
        self._canvas_widget = self._canvas.get_tk_widget()
        self._canvas_widget.grid(row=0, column=0, sticky="nsew")

        self._angles = np.asarray(polar_angles(), dtype=float)
        self._base_angles = self._angles[:-1]

        self._theme = theme
        self._configure_axes()

        self._last_profiles: Optional[Tuple[PersonProfile, PersonProfile]] = None
        self._last_correlations: Tuple[float, float] = (0.0, 0.0)

    @property
    def container(self) -> ttk.Frame:
        return self._container

    @property
    def theme(self) -> Theme:
        return self._theme

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._configure_axes()
        if self._last_profiles is not None:
            self.render(*self._last_profiles, correlations=self._last_correlations)

    def render(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
        *,
        correlations: Tuple[float, float] | None = None,
    ) -> None:
        self._last_profiles = (person_a, person_b)
        if correlations is None:
            correlations = self._last_correlations
        else:
            self._last_correlations = correlations

        theme = self._theme
        for axis in self._axes:
            axis.clear()
            axis.set_facecolor(theme.background)
            axis.set_theta_offset(np.pi / 2)
            axis.set_theta_direction(-1)
            axis.set_ylim(0, 10)
            axis.set_xticks(self._base_angles)
            axis.set_xticklabels(CATEGORIES, fontsize=9)
            axis.grid(color=theme.grid, linestyle="--", linewidth=0.7)
            axis.set_yticks(np.linspace(0, 10, 6))
            axis.set_yticklabels(["0", "2", "4", "6", "8", "10"], fontsize=8)
            axis.set_rlabel_position(0)

        a_loop = close_loop(person_a.giving)
        b_loop = close_loop(person_b.receiving)
        theme_a = theme.series_colors["a_to_b"]
        self._plot_series(
            self._axes[0],
            self._angles,
            a_loop,
            b_loop,
            f"{person_a.name} → {person_b.name}",
            self._format_subtitle(correlations[0]),
            theme_a,
        )

        b_giving = close_loop(person_b.giving)
        a_receiving = close_loop(person_a.receiving)
        theme_b = theme.series_colors["b_to_a"]
        self._plot_series(
            self._axes[1],
            self._angles,
            b_giving,
            a_receiving,
            f"{person_b.name} → {person_a.name}",
            self._format_subtitle(correlations[1]),
            theme_b,
        )

        self._canvas.draw_idle()

    def save_figure(self, path: str) -> None:
        self._figure.savefig(path)

    def _configure_axes(self) -> None:
        self._figure.patch.set_facecolor(self._theme.background)
        for axis in self._axes:
            axis.set_facecolor(self._theme.background)
            axis.grid(color=self._theme.grid)

    @staticmethod
    def _format_subtitle(value: float) -> str:
        if np.isfinite(value):
            return f"Giving matches receiving (r = {value:.2f})"
        return "Giving matches receiving (r undefined)"

    @staticmethod
    def _plot_series(
        axis,
        angles: np.ndarray,
        giving_values: np.ndarray,
        receiving_values: np.ndarray,
        title: str,
        subtitle: str,
        color: str,
    ) -> None:
        axis.plot(angles, giving_values, color=color, linewidth=2.0, label="Giving")
        axis.fill(angles, giving_values, color=color, alpha=0.15)
        axis.plot(angles, receiving_values, color=color, linestyle="--", linewidth=2.0, label="Receiving")
        axis.set_title(title, fontsize=11, pad=16)
        axis.legend(loc="upper left", bbox_to_anchor=(1.02, 1.02), frameon=True)
        axis.text(
            np.pi / 2,
            10.4,
            subtitle,
            ha="center",
            va="bottom",
            fontsize=9,
            color=color,
        )
