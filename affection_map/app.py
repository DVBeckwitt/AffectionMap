"""Graphical interface for exploring love language alignment."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, cast

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

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

        self._input_widgets: Dict[str, Dict[str, object]] = {}
        self.canvas: FigureCanvasTkAgg | None = None
        self._figure: Figure | None = None
        self._axes: Tuple | None = None
        self._plot_artists: Dict[str, Dict[str, object]] = {}
        self.text_var = tk.StringVar()
        self._live_update_job: Optional[str] = None
        self._insights_current = False
        self.scale_canvas: tk.Canvas | None = None
        self._default_names = {"person_a": "A", "person_b": "B"}
        self._scale_markers: Dict[str, Dict[str, object | None]] = {
            "a_to_b": {
                "value": None,
                "marker": None,
                "label": None,
                "label_text": "A → B",
                "color": "#C44E52",
            },
            "b_to_a": {
                "value": None,
                "marker": None,
                "label": None,
                "label_text": "B → A",
                "color": "#4C72B0",
            },
        }
        self._scale_margin = 35
        self._scale_mid_y = 46

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
                "Not at all to Essential (0 to 10). Points near the edge of the radar "
                "charts show love languages that matter more."
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
        default_name = self._default_names[key]
        name_var = tk.StringVar(value=default_name)
        name_entry = ttk.Entry(frame, width=22, textvariable=name_var)
        name_entry.grid(row=0, column=1, sticky=tk.W)

        def _handle_focus_in(event: tk.Event) -> None:
            if name_entry.get().strip() == default_name:
                name_entry.delete(0, tk.END)

        def _handle_focus_out(event: tk.Event) -> None:
            if not name_entry.get().strip():
                name_entry.insert(0, default_name)
            self._schedule_live_update()

        name_entry.bind("<FocusIn>", _handle_focus_in)
        name_entry.bind("<FocusOut>", _handle_focus_out)

        def _on_name_change(*_: object) -> None:
            self._schedule_live_update()

        name_var.trace_add("write", _on_name_change)

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

            show_markers = idx == len(CATEGORIES) + 1
            giving_container, giving_slider = self._create_slider_widget(
                frame, show_markers=show_markers
            )
            giving_container.grid(row=idx, column=1, padx=5, pady=2, sticky=tk.EW)
            giving_sliders.append(giving_slider)

            receiving_container, receiving_slider = self._create_slider_widget(
                frame, show_markers=show_markers
            )
            receiving_container.grid(row=idx, column=2, padx=5, pady=2, sticky=tk.EW)
            receiving_sliders.append(receiving_slider)

        self._input_widgets[key] = {
            "name": name_entry,
            "name_var": name_var,
            "giving": giving_sliders,
            "receiving": receiving_sliders,
        }

    def _create_slider_widget(
        self, parent: ttk.Frame, *, show_markers: bool = True
    ) -> Tuple[ttk.Frame, ttk.Scale]:
        markers = [
            ("Not at all", tk.W),
            ("Essential", tk.E),
        ]

        container = ttk.Frame(parent)
        container.columnconfigure(0, weight=1)

        display_var = tk.StringVar(value="5.00")

        slider = ttk.Scale(container, from_=0.0, to=10.0, orient=tk.HORIZONTAL)
        slider.set(5.0)
        slider.grid(row=0, column=0, sticky=tk.EW)

        value_label = ttk.Label(container, textvariable=display_var, width=6, anchor=tk.E)
        value_label.grid(row=0, column=1, padx=(8, 0))

        if show_markers:
            legend = ttk.Frame(container)
            legend.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(4, 0))
            for idx, (label, anchor) in enumerate(markers):
                legend.columnconfigure(idx, weight=1)
                ttk.Label(legend, text=label, font=("Helvetica", 8)).grid(
                    row=0, column=idx, sticky=anchor
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

        content = ttk.Frame(section)
        content.pack(fill=tk.X)
        content.columnconfigure(0, weight=0)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        button = ttk.Button(
            content,
            text="Generate Compatibility Report",
            style="Generate.TButton",
            command=self._on_generate,
        )
        button.grid(row=0, column=0, sticky=tk.W, pady=10)

        style.configure(
            "Save.TButton",
            font=("Helvetica", 10),
            padding=(14, 6),
        )

        save_button = ttk.Button(
            content,
            text="Save Love Language Figure…",
            style="Save.TButton",
            command=self._on_save_figure,
        )
        save_button.grid(row=1, column=0, sticky=tk.W)

        scale_container = self._create_correlation_scale(content)
        scale_container.grid(row=0, column=1, sticky=tk.NSEW, padx=(20, 0), pady=10)

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

    def _create_correlation_scale(self, parent: ttk.Frame) -> ttk.Frame:
        scale_container = ttk.Frame(parent, padding=(0, 0, 0, 0))

        title = ttk.Label(
            scale_container,
            text="Correlation scale (r)",
            font=("Helvetica", 11, "bold"),
        )
        title.pack(anchor=tk.W)

        self.scale_canvas = tk.Canvas(
            scale_container,
            height=110,
            highlightthickness=0,
        )
        self.scale_canvas.pack(fill=tk.X, expand=False, pady=(8, 0))
        self.scale_canvas.bind("<Configure>", self._redraw_scale)
        self._redraw_scale()

        return scale_container

    def _redraw_scale(self, event: tk.Event | None = None) -> None:
        if self.scale_canvas is None:
            return

        canvas = self.scale_canvas
        canvas.delete("scale_static")

        width = canvas.winfo_width()
        if width <= 2:
            width = int(canvas.cget("width"))

        margin = self._scale_margin
        mid_y = self._scale_mid_y

        canvas.create_line(
            margin,
            mid_y,
            width - margin,
            mid_y,
            fill="#444444",
            width=2,
            tags="scale_static",
        )

        labels = {
            -1.0: "Opposite priorities",
            0.0: "No consistent relationship",
            1.0: "Perfect alignment",
        }

        for value, description in labels.items():
            position = self._scale_value_to_x(value)
            canvas.create_line(
                position,
                mid_y - 8,
                position,
                mid_y + 8,
                fill="#444444",
                width=2,
                tags="scale_static",
            )
            display_value = "0" if value == 0 else f"{value:+.0f}"
            canvas.create_text(
                position,
                mid_y - 18,
                text=display_value,
                font=("Helvetica", 10, "bold"),
                fill="#444444",
                tags="scale_static",
            )
            canvas.create_text(
                position,
                mid_y + 26,
                text=description,
                font=("Helvetica", 9),
                fill="#444444",
                tags="scale_static",
            )

        self._reposition_scale_markers()

    def _scale_value_to_x(self, value: float) -> float:
        if self.scale_canvas is None:
            return float(self._scale_margin)

        width = self.scale_canvas.winfo_width()
        if width <= 2:
            width = int(self.scale_canvas.cget("width"))

        span = width - 2 * self._scale_margin
        if span <= 0:
            span = 1

        normalized = (np.clip(value, -1.0, 1.0) + 1) / 2
        return self._scale_margin + normalized * span

    def _reposition_scale_markers(self) -> None:
        if self.scale_canvas is None:
            return

        for key in self._scale_markers:
            self._draw_scale_marker(key)

    def _draw_scale_marker(self, key: str) -> None:
        if self.scale_canvas is None:
            return

        marker_info = self._scale_markers[key]
        marker = marker_info.get("marker")
        label = marker_info.get("label")
        if marker is not None:
            self.scale_canvas.delete(marker)
            marker_info["marker"] = None
        if label is not None:
            self.scale_canvas.delete(label)
            marker_info["label"] = None

        value = marker_info.get("value")
        if value is None:
            return

        position = self._scale_value_to_x(cast(float, value))
        radius = 6
        marker = self.scale_canvas.create_oval(
            position - radius,
            self._scale_mid_y - radius,
            position + radius,
            self._scale_mid_y + radius,
            fill=cast(str, marker_info["color"]),
            outline="",
        )
        marker_info["marker"] = marker

        label_text = cast(str, marker_info.get("label_text", ""))
        if label_text:
            label = self.scale_canvas.create_text(
                position,
                self._scale_mid_y - 32,
                text=label_text,
                font=("Helvetica", 9, "bold"),
                fill=cast(str, marker_info["color"]),
            )
            marker_info["label"] = label

    def _update_scale_markers(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
        corr_a_to_b: float,
        corr_b_to_a: float,
    ) -> None:
        if self.scale_canvas is None:
            return

        labels = {
            "a_to_b": self._format_scale_label(
                person_a.name,
                person_b.name,
                self._default_names["person_a"],
                self._default_names["person_b"],
            ),
            "b_to_a": self._format_scale_label(
                person_b.name,
                person_a.name,
                self._default_names["person_b"],
                self._default_names["person_a"],
            ),
        }
        markers = {
            "a_to_b": corr_a_to_b,
            "b_to_a": corr_b_to_a,
        }

        for key, value in markers.items():
            marker_info = self._scale_markers[key]
            marker_info["value"] = value
            marker_info["label_text"] = labels[key]
            self._draw_scale_marker(key)

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
            name = self._default_names[key]

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
        self._render_plot(person_a, person_b)
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

        self._render_plot(person_a, person_b)

        explanation = build_explanation(person_a, person_b, corr_a_to_b, corr_b_to_a)
        self.text_var.set(explanation)
        self._insights_current = True
        self._update_scale_markers(person_a, person_b, corr_a_to_b, corr_b_to_a)

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

        category_angles = np.degrees(angles[:-1])

        for ax in axes_tuple:
            labels = ax.set_thetagrids(
                category_angles,
                labels=CATEGORIES,
                frac=1.1,
            )
            for label in labels:
                label.set_fontsize(9)

            ax.tick_params(axis="x", pad=4)
            ax.set_yticks(np.arange(0, 11, 2))
            ax.set_ylim(0, 10)

        figure.suptitle(
            "Love Language Alignment: Giving vs Receiving",
            fontsize=14,
            fontweight="bold",
        )
        figure.subplots_adjust(left=0.08, right=0.78, top=0.84, bottom=0.12, wspace=0.45)

        figure.text(
            0.5,
            0.02,
            "Farther from the center means that love language carries more importance.",
            ha="center",
            fontsize=9,
            color="#333333",
        )

        self._figure = figure
        self._axes = axes_tuple

        self.canvas = FigureCanvasTkAgg(figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _update_polygon(polygon, angles: np.ndarray, values: np.ndarray) -> None:
        polygon.set_xy(np.column_stack((angles, values)))

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
            legend = ax.legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1.02),
                borderaxespad=0.0,
                frameon=True,
            )
            artists = {
                "giving_line": giving_line,
                "giving_fill": giving_fill,
                "receiving_line": receiving_line,
                "receiving_fill": receiving_fill,
                "legend": legend,
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
            artists["legend"] = ax.legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1.02),
                borderaxespad=0.0,
                frameon=True,
            )

        ax.set_title(title, pad=15, fontsize=11)

    def _render_plot(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
    ) -> None:
        person_a_loop_giving = close_loop(person_a.giving)
        person_a_loop_receiving = close_loop(person_a.receiving)
        person_b_loop_giving = close_loop(person_b.giving)
        person_b_loop_receiving = close_loop(person_b.receiving)

        angles = np.asarray(polar_angles(), dtype=float)

        self._ensure_plot_canvas(angles)

        if not self._axes:
            return

        self._scale_markers["a_to_b"]["label_text"] = self._format_scale_label(
            person_a.name,
            person_b.name,
            self._default_names["person_a"],
            self._default_names["person_b"],
        )
        self._scale_markers["b_to_a"]["label_text"] = self._format_scale_label(
            person_b.name,
            person_a.name,
            self._default_names["person_b"],
            self._default_names["person_a"],
        )
        self._reposition_scale_markers()

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
        )

        if self.canvas is not None:
            self.canvas.draw_idle()

    def _format_scale_label(
        self, source: str, target: str, default_source: str, default_target: str
    ) -> str:
        source_clean = source.strip() or default_source
        target_clean = target.strip() or default_target
        return f"{source_clean} → {target_clean}"

    def _on_save_figure(self) -> None:
        if self._figure is None:
            messagebox.showinfo(
                "Nothing to save",
                "Create a compatibility preview before saving the figure.",
            )
            return

        file_path = filedialog.asksaveasfilename(
            title="Save love language figure",
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("SVG Image", "*.svg"),
                ("All Files", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            self._figure.savefig(file_path)
        except Exception as error:  # pragma: no cover - GUI path
            messagebox.showerror("Save failed", str(error))


def main() -> None:
    root = tk.Tk()
    LoveLanguageApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
