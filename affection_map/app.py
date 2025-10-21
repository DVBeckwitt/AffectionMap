"""Graphical interface for exploring love language alignment."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, cast

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import tkinter as tk
from tkinter import ttk, messagebox

from .analysis import (
    CATEGORIES,
    PersonProfile,
    build_explanation,
    close_loop,
    correlation,
    polar_angles,
)


class LoveLanguageApp:
    """Tkinter application that captures inputs and shows compatibility plots."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("AffectionMap – Love Language Alignment")

        self._input_widgets: Dict[str, Dict[str, List[ttk.Scale]]] = {}
        self.canvas: FigureCanvasTkAgg | None = None
        self._figure: Figure | None = None
        self._axes: Tuple | None = None
        self._plot_artists: Dict[str, Dict[str, object]] = {}
        self.text_var = tk.StringVar()
        self._live_update_job: Optional[str] = None
        self._insights_current = False

        self._build_layout()

        # Ensure the initial layout determines a comfortable minimum size while
        # keeping the window resizable if additional content (like longer
        # explanations) requires more room.
        self.master.update_idletasks()
        self.master.minsize(self.master.winfo_width(), self.master.winfo_height())
        self.text_var.set(
            "Adjust the sliders to explore how preferences shift. "
            "Click Generate Compatibility Report for detailed insights."
        )
        self.master.after_idle(self._refresh_live_preview)

    def _build_layout(self) -> None:
        container = ttk.Frame(self.master, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(
            container,
            text="Compare how two people prefer to give and receive love.",
            font=("Helvetica", 16, "bold"),
        )
        header.pack(anchor=tk.W)

        self._create_input_section(container)
        self._create_action_section(container)
        self._create_results_section(container)

    def _create_input_section(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent, padding=(0, 15, 0, 10))
        section.pack(fill=tk.X)

        instructions = ttk.Label(
            section,
            text=(
                "Use the sliders to choose how strongly each love language resonates, from "
                "Not at all to Most Important (0 to 10)."
            ),
            wraplength=720,
        )
        instructions.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        self._create_person_frame(section, "person_a", "Person A", 1, 0)
        self._create_person_frame(section, "person_b", "Person B", 1, 1)

    def _create_person_frame(
        self, parent: ttk.Frame, key: str, title: str, row: int, column: int
    ) -> None:
        frame = ttk.Labelframe(parent, text=title, padding=15)
        frame.grid(row=row, column=column, padx=10, sticky=tk.N)

        name_label = ttk.Label(frame, text="Name:")
        name_label.grid(row=0, column=0, sticky=tk.W)
        name_entry = ttk.Entry(frame, width=22)
        name_entry.grid(row=0, column=1, sticky=tk.W)

        giving_label = ttk.Label(frame, text="Giving")
        giving_label.grid(row=1, column=1, pady=(10, 0))
        receiving_label = ttk.Label(frame, text="Receiving")
        receiving_label.grid(row=1, column=2, pady=(10, 0))

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        giving_sliders: List[ttk.Scale] = []
        receiving_sliders: List[ttk.Scale] = []

        for idx, category in enumerate(CATEGORIES, start=2):
            ttk.Label(frame, text=category).grid(
                row=idx, column=0, padx=(0, 10), pady=2, sticky=tk.W
            )

            giving_container, giving_slider = self._create_slider_widget(frame)
            giving_container.grid(row=idx, column=1, padx=5, pady=2, sticky=tk.EW)
            giving_sliders.append(giving_slider)

            receiving_container, receiving_slider = self._create_slider_widget(frame)
            receiving_container.grid(row=idx, column=2, padx=5, pady=2, sticky=tk.EW)
            receiving_sliders.append(receiving_slider)

        self._input_widgets[key] = {
            "name": name_entry,  # type: ignore[assignment]
            "giving": giving_sliders,
            "receiving": receiving_sliders,
        }

    def _create_slider_widget(self, parent: ttk.Frame) -> Tuple[ttk.Frame, ttk.Scale]:
        markers = [
            "Not at all",
            "A little",
            "A lot",
            "Very Important",
            "Most Important",
        ]

        container = ttk.Frame(parent)
        container.columnconfigure(0, weight=1)

        display_var = tk.StringVar(value="5.00")

        slider = ttk.Scale(container, from_=0.0, to=10.0, orient=tk.HORIZONTAL)
        slider.set(5.0)
        slider.grid(row=0, column=0, sticky=tk.EW)

        value_label = ttk.Label(container, textvariable=display_var, width=6, anchor=tk.E)
        value_label.grid(row=0, column=1, padx=(8, 0))

        legend = ttk.Frame(container)
        legend.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(4, 0))
        for idx, label in enumerate(markers):
            legend.columnconfigure(idx, weight=1)
            ttk.Label(legend, text=label, font=("Helvetica", 8)).grid(
                row=0, column=idx
            )

        def _update_display(value: str) -> None:
            rounded = round(float(value), 2)
            display_var.set(f"{rounded:.2f}")

        def _on_slider_change(value: str) -> None:
            _update_display(value)
            self._schedule_live_update()

        slider.configure(command=_on_slider_change)
        _update_display("5.0")

        return container, slider

    def _create_action_section(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent)
        section.pack(fill=tk.X, pady=(5, 15))

        style = ttk.Style()
        style.configure(
            "Generate.TButton",
            font=("Helvetica", 12, "bold"),
            padding=(20, 10),
        )

        button = ttk.Button(
            section,
            text="Generate Compatibility Report",
            style="Generate.TButton",
            command=self._on_generate,
        )
        button.pack(pady=10)

    def _create_results_section(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent)
        section.pack(fill=tk.BOTH, expand=True)

        self.plot_frame = ttk.Frame(section)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        explanation_frame = ttk.Frame(section, padding=(15, 0, 0, 0))
        explanation_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        explanation_title = ttk.Label(
            explanation_frame, text="Compatibility Insights", font=("Helvetica", 14, "bold")
        )
        explanation_title.pack(anchor=tk.W)

        self.explanation_label = ttk.Label(
            explanation_frame,
            textvariable=self.text_var,
            wraplength=320,
            justify=tk.LEFT,
        )
        self.explanation_label.pack(anchor=tk.W, pady=(10, 0))

        scale_description = (
            "Correlation scale (r):\n"
            "-1 – Opposite priorities; when one values a language more, the other values it less.\n"
            "0 – No consistent relationship between the two sets of priorities.\n"
            "+1 – Perfect alignment; both people value each language similarly."
        )
        self.correlation_scale_label = ttk.Label(
            explanation_frame,
            text=scale_description,
            wraplength=320,
            justify=tk.LEFT,
            font=("Helvetica", 9),
        )
        self.correlation_scale_label.pack(anchor=tk.W, pady=(15, 0))

    def _collect_slider_values(self, sliders: List[ttk.Scale]) -> List[float]:
        values: List[float] = []
        for widget in sliders:
            value = round(float(widget.get()), 2)
            if not 0 <= value <= 10:
                raise ValueError("Scores must be between 0 and 10.")
            values.append(value)
        return values

    def _gather_profile(self, key: str, *, require_name: bool) -> PersonProfile:
        widgets = self._input_widgets[key]
        name_entry: ttk.Entry = widgets["name"]  # type: ignore[assignment]
        name = name_entry.get().strip()
        if not name:
            if require_name:
                name_entry.focus_set()
                default_label = "Person A" if key == "person_a" else "Person B"
                raise ValueError(
                    f"Please enter a name for {default_label} before generating a report."
                )
            name = "Person A" if key == "person_a" else "Person B"

        giving = np.array(self._collect_slider_values(widgets["giving"]))
        receiving = np.array(self._collect_slider_values(widgets["receiving"]))
        return PersonProfile(name=name, giving=giving, receiving=receiving)

    def _extract_profile(self, key: str) -> PersonProfile:
        profile = self._gather_profile(key, require_name=True)
        if profile.name:
            return profile
        raise ValueError("Invalid profile configuration.")

    def _schedule_live_update(self) -> None:
        if self._live_update_job is not None:
            self.master.after_cancel(self._live_update_job)
        # Update quickly so the radar charts closely track slider movement.
        # A 10 ms delay keeps the UI responsive while providing very smooth
        # visual feedback when users drag the scales in small increments.
        self._live_update_job = self.master.after(10, self._refresh_live_preview)

    def _refresh_live_preview(self) -> None:
        self._live_update_job = None
        person_a = self._gather_profile("person_a", require_name=False)
        person_b = self._gather_profile("person_b", require_name=False)
        self._render_plot(person_a, person_b, correlations=None)
        if self._insights_current:
            self.text_var.set(
                "Values updated. Click Generate Compatibility Report to refresh the insights."
            )
            self._insights_current = False

    def _on_generate(self) -> None:
        try:
            person_a = self._extract_profile("person_a")
            person_b = self._extract_profile("person_b")
        except ValueError as error:  # pragma: no cover - GUI path
            messagebox.showerror("Invalid input", str(error))
            return

        untouched_profiles = [
            profile.name
            for profile in (person_a, person_b)
            if self._uses_default_scores(profile)
        ]
        if untouched_profiles:
            messagebox.showwarning(
                "Adjust the sliders",
                (
                    "The following profiles still have every slider at 5.00: "
                    + ", ".join(untouched_profiles)
                    + ". Adjust the sliders to reflect real preferences before relying on this report."
                ),
            )

        self._render_report(person_a, person_b)

    def _render_report(self, person_a: PersonProfile, person_b: PersonProfile) -> None:
        corr_a_to_b = correlation(person_a.giving, person_b.receiving)
        corr_b_to_a = correlation(person_b.giving, person_a.receiving)

        self._render_plot(person_a, person_b, correlations=(corr_a_to_b, corr_b_to_a))

        explanation = build_explanation(person_a, person_b, corr_a_to_b, corr_b_to_a)
        self.text_var.set(explanation)
        self._insights_current = True

    @staticmethod
    def _uses_default_scores(profile: PersonProfile) -> bool:
        return bool(
            np.allclose(profile.giving, 5.0)
            and np.allclose(profile.receiving, 5.0)
        )

    def _ensure_plot_canvas(self, angles: np.ndarray) -> None:
        if self.canvas is not None and self._axes is not None and self._figure is not None:
            return

        figure = Figure(figsize=(7.5, 5), dpi=100)
        axes_array = figure.subplots(1, 2, subplot_kw={"projection": "polar"})
        axes_tuple = tuple(np.ravel(axes_array))

        for ax in axes_tuple:
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(CATEGORIES, fontsize=8)
            ax.set_yticks(np.arange(0, 11, 2))
            ax.set_ylim(0, 10)

        figure.suptitle(
            "Love Language Alignment: Giving vs Receiving",
            fontsize=14,
            fontweight="bold",
        )
        figure.tight_layout()

        self._figure = figure
        self._axes = axes_tuple

        self.canvas = FigureCanvasTkAgg(figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _update_polygon(polygon, angles: np.ndarray, values: np.ndarray) -> None:
        polygon.set_xy(np.column_stack((angles, values)))

    def _clear_scale_artists(self, artists: Dict[str, object]) -> None:
        scale_artists = artists.get("scale_artists")
        if scale_artists:
            for element in cast(List[object], scale_artists):
                element.remove()
        artists["scale_artists"] = []

    def _update_correlation_scale(
        self,
        ax,
        artists: Dict[str, object],
        correlation_value: float | None,
    ) -> None:
        if correlation_value is None:
            if artists:
                self._clear_scale_artists(artists)
            return

        start_x, end_x = 0.2, 0.8
        y = -0.12

        self._clear_scale_artists(artists)
        scale_artists = []

        base_line = Line2D(
            [start_x, end_x],
            [y, y],
            transform=ax.transAxes,
            color="#444444",
            linewidth=1,
        )
        ax.add_line(base_line)
        scale_artists.append(base_line)

        for tick_value in (-1, 0, 1):
            position = start_x + ((tick_value + 1) / 2) * (end_x - start_x)
            tick = Line2D(
                [position, position],
                [y - 0.025, y + 0.025],
                transform=ax.transAxes,
                color="#444444",
                linewidth=1,
            )
            ax.add_line(tick)
            scale_artists.append(tick)

            label = ax.text(
                position,
                y - 0.055,
                f"{tick_value:+.0f}" if tick_value else "0",
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=9,
            )
            scale_artists.append(label)

        marker_position = start_x + ((np.clip(correlation_value, -1.0, 1.0) + 1) / 2) * (
            end_x - start_x
        )
        marker = Line2D(
            [marker_position],
            [y],
            marker="o",
            markersize=6,
            color="#C44E52",
            transform=ax.transAxes,
        )
        ax.add_line(marker)
        scale_artists.append(marker)

        marker_label = ax.text(
            0.5,
            y - 0.12,
            f"r = {correlation_value:.2f}",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=9,
            color="#C44E52",
        )
        scale_artists.append(marker_label)

        artists["scale_artists"] = scale_artists

    def _update_profile_plot(
        self,
        key: str,
        ax,
        angles: np.ndarray,
        giving_values: np.ndarray,
        receiving_values: np.ndarray,
        title: str,
        giving_label: str,
        receiving_label: str,
        correlation_value: float | None,
    ) -> None:
        artists = self._plot_artists.get(key)
        if not artists:
            giving_line, = ax.plot(
                angles,
                giving_values,
                color="#55A868",
                linewidth=2,
                label=giving_label,
            )
            giving_fill = ax.fill(angles, giving_values, color="#55A868", alpha=0.25)[0]
            receiving_line, = ax.plot(
                angles,
                receiving_values,
                color="#4C72B0",
                linewidth=2,
                label=receiving_label,
            )
            receiving_fill = ax.fill(angles, receiving_values, color="#4C72B0", alpha=0.25)[0]
            legend = ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
            artists = {
                "giving_line": giving_line,
                "giving_fill": giving_fill,
                "receiving_line": receiving_line,
                "receiving_fill": receiving_fill,
                "legend": legend,
                "scale_artists": [],
            }
            self._plot_artists[key] = artists
        else:
            giving_line = artists["giving_line"]
            giving_line.set_data(angles, giving_values)
            giving_line.set_label(giving_label)
            self._update_polygon(artists["giving_fill"], angles, giving_values)

            receiving_line = artists["receiving_line"]
            receiving_line.set_data(angles, receiving_values)
            receiving_line.set_label(receiving_label)
            self._update_polygon(artists["receiving_fill"], angles, receiving_values)

            legend = artists["legend"]
            legend.remove()
            artists["legend"] = ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

        ax.set_title(title, pad=15, fontsize=11)
        self._update_correlation_scale(ax, artists, correlation_value)

    def _render_plot(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
        *,
        correlations: Tuple[float, float] | None,
    ) -> None:
        person_a_loop_giving = close_loop(person_a.giving)
        person_a_loop_receiving = close_loop(person_a.receiving)
        person_b_loop_giving = close_loop(person_b.giving)
        person_b_loop_receiving = close_loop(person_b.receiving)

        angles = np.asarray(polar_angles(), dtype=float)

        self._ensure_plot_canvas(angles)

        if not self._axes:
            return

        title_left = f"{person_a.name} → {person_b.name}"
        title_right = f"{person_b.name} → {person_a.name}"
        self._update_profile_plot(
            "a_to_b",
            self._axes[0],
            angles,
            person_a_loop_giving,
            person_b_loop_receiving,
            title_left,
            f"{person_a.name} Giving",
            f"{person_b.name} Receiving",
            correlations[0] if correlations is not None else None,
        )

        self._update_profile_plot(
            "b_to_a",
            self._axes[1],
            angles,
            person_b_loop_giving,
            person_a_loop_receiving,
            title_right,
            f"{person_b.name} Giving",
            f"{person_a.name} Receiving",
            correlations[1] if correlations is not None else None,
        )

        if self.canvas is not None:
            self.canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    LoveLanguageApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
