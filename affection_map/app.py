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

        self._profiles: Dict[str, Dict[str, object]] = {}
        self.canvas: FigureCanvasTkAgg | None = None
        self._figure: Figure | None = None
        self._axes: Tuple | None = None
        self._plot_artists: Dict[str, Dict[str, object]] = {}
        self.text_var = tk.StringVar()
        self._live_update_job: Optional[str] = None
        self._insights_current = False
        self.canvas_container: ttk.Frame | None = None
        self._scale_axis = None
        self._default_names = {"person_a": "A", "person_b": "B"}
        self._switch_person_labels: Dict[str, ttk.Label] = {}
        self._switch_name_entries: Dict[str, ttk.Entry] = {}
        self._switch_button_text = tk.StringVar()
        self._handle_lookup: Dict[Tuple[str, str], Tuple[str, str]] = {
            ("person_a", "giving"): ("a_to_b", "giving_handle"),
            ("person_a", "receiving"): ("b_to_a", "receiving_handle"),
            ("person_b", "giving"): ("b_to_a", "giving_handle"),
            ("person_b", "receiving"): ("a_to_b", "receiving_handle"),
        }
        self._active_person_var = tk.StringVar(value="person_a")
        self._angles = np.asarray(polar_angles(), dtype=float)
        self._base_angles = self._angles[:-1]
        self._canvas_cids: List[int] = []
        self._drag_state: Optional[Dict[str, object]] = None
        self._drag_angle_threshold = np.deg2rad(22.5)
        self._scale_markers: Dict[str, Dict[str, object | None]] = {
            "a_to_b": {
                "value": None,
                "artist": None,
                "label_artist": None,
                "label_text": "A → B",
                "color": "#C44E52",
            },
            "b_to_a": {
                "value": None,
                "artist": None,
                "label_artist": None,
                "label_text": "B → A",
                "color": "#4C72B0",
            },
        }

        self._build_layout()

        # Ensure the initial layout determines a comfortable minimum size while
        # keeping the window resizable if additional content (like longer
        # explanations) requires more room.
        self.master.update_idletasks()
        self.master.minsize(self.master.winfo_width(), self.master.winfo_height())
        self.text_var.set(
            "Use the toggle to choose whose preferences to adjust, then drag the "
            "handles on the radar charts. Click Generate Compatibility Report for "
            "detailed insights."
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
                "Use the toggle above the charts to choose whose preferences to adjust, then drag the "
                "circular handles on the radar charts to set how strongly each love "
                "language resonates (0 to 10)."
            ),
            wraplength=720,
        )
        instructions.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        self._create_person_frame(section, "person_a", "Person A", 2, 0)
        self._create_person_frame(section, "person_b", "Person B", 2, 1)

    def _create_active_profile_switch(self, parent: ttk.Frame) -> None:
        style = ttk.Style()
        style.configure(
            "PersonSwitch.TCheckbutton",
            font=("Helvetica", 10, "bold"),
            padding=(16, 6),
            indicatoron=False,
        )
        style.map(
            "PersonSwitch.TCheckbutton",
            relief=[("selected", "sunken"), ("!selected", "raised")],
        )

        switch_frame = ttk.Frame(parent, padding=(0, 0, 0, 12))
        switch_frame.pack(side=tk.TOP, anchor=tk.CENTER)

        ttk.Label(
            switch_frame,
            text="Adjusting preferences for:",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor=tk.CENTER)

        controls = ttk.Frame(switch_frame)
        controls.pack(anchor=tk.CENTER, pady=(6, 0))

        profile_a = self._profiles.get("person_a", {})
        profile_b = self._profiles.get("person_b", {})

        default_a = self._default_names.get("person_a", "")
        default_b = self._default_names.get("person_b", "")

        if "name_var" not in profile_a:
            profile_a["name_var"] = tk.StringVar(value=default_a)
        if "name_var" not in profile_b:
            profile_b["name_var"] = tk.StringVar(value=default_b)

        name_var_a = cast(tk.StringVar, profile_a["name_var"])
        name_var_b = cast(tk.StringVar, profile_b["name_var"])

        label_a = ttk.Label(controls, text=f"{profile_a.get('title', 'Person A')}:", font=("Helvetica", 10))
        label_a.grid(row=0, column=0, padx=(0, 6))
        entry_a = ttk.Entry(controls, width=18, textvariable=name_var_a, justify=tk.CENTER)
        entry_a.grid(row=0, column=1, padx=(0, 12))

        toggle = ttk.Checkbutton(
            controls,
            textvariable=self._switch_button_text,
            variable=self._active_person_var,
            onvalue="person_b",
            offvalue="person_a",
            style="PersonSwitch.TCheckbutton",
            command=self._on_active_person_changed,
            takefocus=False,
        )
        toggle.grid(row=0, column=2, padx=(0, 12))

        label_b = ttk.Label(controls, text=f"{profile_b.get('title', 'Person B')}:", font=("Helvetica", 10))
        label_b.grid(row=0, column=3, padx=(12, 6))
        entry_b = ttk.Entry(controls, width=18, textvariable=name_var_b, justify=tk.CENTER)
        entry_b.grid(row=0, column=4)

        self._switch_person_labels["person_a"] = label_a
        self._switch_person_labels["person_b"] = label_b
        self._switch_name_entries["person_a"] = entry_a
        self._switch_name_entries["person_b"] = entry_b

        profile_a["name_entry"] = entry_a
        profile_b["name_entry"] = entry_b

        def _make_focus_handlers(var: tk.StringVar, default_value: str):
            def _handle_focus_in(event: tk.Event) -> None:
                if var.get().strip() == default_value:
                    event.widget.selection_range(0, tk.END)

            def _handle_focus_out(event: tk.Event) -> None:
                if not var.get().strip():
                    var.set(default_value)
                self._schedule_live_update()

            return _handle_focus_in, _handle_focus_out

        focus_in_a, focus_out_a = _make_focus_handlers(name_var_a, default_a)
        focus_in_b, focus_out_b = _make_focus_handlers(name_var_b, default_b)

        entry_a.bind("<FocusIn>", focus_in_a)
        entry_a.bind("<FocusOut>", focus_out_a)
        entry_b.bind("<FocusIn>", focus_in_b)
        entry_b.bind("<FocusOut>", focus_out_b)

        self._profiles["person_a"] = profile_a
        self._profiles["person_b"] = profile_b
        self._update_switch_appearance()

    def _on_active_person_changed(self) -> None:
        self._update_switch_appearance()
        self._update_handle_visibility()
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _display_name_for(self, key: str) -> str:
        default_name = self._default_names.get(key, key)
        profile = self._profiles.get(key)
        if not profile:
            return default_name

        title = cast(str, profile.get("title", ""))
        name_var = cast(tk.StringVar, profile.get("name_var"))
        display_name = name_var.get().strip() if name_var else ""
        display_name = display_name or default_name
        return f"{title}: {display_name}" if title else display_name

    def _update_switch_appearance(self) -> None:
        active_key = self._active_person_var.get()
        inactive_key = "person_b" if active_key == "person_a" else "person_a"

        if self._switch_button_text is not None:
            self._switch_button_text.set(
                f"Switch to {self._display_name_for(inactive_key)}"
            )

        for key, label in self._switch_person_labels.items():
            if not label:
                continue
            font = ("Helvetica", 10, "bold") if key == active_key else ("Helvetica", 10)
            label.configure(font=font)

        for key, entry in self._switch_name_entries.items():
            if not entry:
                continue
            font = ("Helvetica", 10, "bold") if key == active_key else ("Helvetica", 10)
            entry.configure(font=font)

    def _create_person_frame(
        self, parent: ttk.Frame, key: str, title: str, row: int, column: int
    ) -> None:
        frame = ttk.Labelframe(parent, text=title, padding=15)
        frame.grid(row=row, column=column, padx=10, sticky=tk.N)

        default_name = self._default_names[key]
        name_var = tk.StringVar(value=default_name)

        def _on_name_change(*_: object) -> None:
            self._update_switch_appearance()
            self._schedule_live_update()
        name_var.trace_add("write", _on_name_change)

        ttk.Label(
            frame,
            text="Drag the radar chart handles to adjust this person's giving and "
            "receiving preferences.",
            wraplength=240,
        ).grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky=tk.W)

        profile_info: Dict[str, object] = {
            "frame": frame,
            "name_var": name_var,
            "giving": np.full(len(CATEGORIES), 5.0, dtype=float),
            "receiving": np.full(len(CATEGORIES), 5.0, dtype=float),
            "title": title,
        }

        self._profiles[key] = profile_info

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

    def _create_results_section(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent)
        section.pack(fill=tk.BOTH, expand=True)

        self.plot_frame = ttk.Frame(section)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_active_profile_switch(self.plot_frame)

        self.canvas_container = ttk.Frame(self.plot_frame)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

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

    def _setup_scale_axis(self, axis) -> None:
        self._scale_axis = axis
        axis.clear()
        axis.set_xlim(-1.05, 1.05)
        axis.set_ylim(-0.5, 0.7)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.axis("off")
        axis.set_title("Correlation scale (r)", loc="left", fontsize=11, fontweight="bold", pad=16)

        axis.hlines(0, -1.0, 1.0, color="#444444", linewidth=2, zorder=1)

        labels = {
            -1.0: "Opposite priorities",
            0.0: "No consistent relationship",
            1.0: "Perfect alignment",
        }

        for value, description in labels.items():
            axis.vlines(value, -0.08, 0.08, color="#444444", linewidth=2, zorder=1)
            display_value = "0" if value == 0 else f"{value:+.0f}"
            axis.text(
                value,
                0.18,
                display_value,
                fontsize=10,
                fontweight="bold",
                color="#444444",
                ha="center",
                va="bottom",
                zorder=2,
            )
            axis.text(
                value,
                -0.28,
                description,
                fontsize=9,
                color="#444444",
                ha="center",
                va="top",
                zorder=2,
            )

        for marker_info in self._scale_markers.values():
            artist = marker_info.get("artist")
            if artist is not None:
                try:
                    artist.remove()
                except ValueError:
                    pass
                marker_info["artist"] = None
            label_artist = marker_info.get("label_artist")
            if label_artist is not None:
                label_artist.remove()
                marker_info["label_artist"] = None

        self._reposition_scale_markers()

    @staticmethod
    def _scale_value_to_coordinate(value: float) -> float:
        return float(np.clip(value, -1.0, 1.0))

    def _reposition_scale_markers(self) -> None:
        if self._scale_axis is None:
            return

        for key in self._scale_markers:
            self._draw_scale_marker(key)

    def _draw_scale_marker(self, key: str) -> None:
        if self._scale_axis is None:
            return

        marker_info = self._scale_markers[key]
        value = marker_info.get("value")
        artist = marker_info.get("artist")
        label_artist = marker_info.get("label_artist")

        if value is None:
            if artist is not None:
                artist.remove()
                marker_info["artist"] = None
            if label_artist is not None:
                label_artist.remove()
                marker_info["label_artist"] = None
            return

        x_position = self._scale_value_to_coordinate(cast(float, value))
        color = cast(str, marker_info["color"])
        label_text = cast(str, marker_info.get("label_text", ""))

        if artist is None:
            artist = self._scale_axis.plot(
                [x_position],
                [0.0],
                marker="o",
                markersize=9,
                color=color,
                markeredgecolor="white",
                markeredgewidth=1.2,
                linestyle="",
                zorder=5,
            )[0]
            marker_info["artist"] = artist
        else:
            artist.set_data([x_position], [0.0])
            artist.set_color(color)
            artist.set_markeredgecolor("white")

        if label_text:
            if label_artist is None:
                label_artist = self._scale_axis.text(
                    x_position,
                    0.42,
                    label_text,
                    fontsize=9,
                    fontweight="bold",
                    color=color,
                    ha="center",
                    va="bottom",
                    zorder=5,
                )
                marker_info["label_artist"] = label_artist
            else:
                label_artist.set_position((x_position, 0.42))
                label_artist.set_text(label_text)
                label_artist.set_color(color)
        elif label_artist is not None:
            label_artist.remove()
            marker_info["label_artist"] = None

    def _update_scale_markers(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
        corr_a_to_b: float,
        corr_b_to_a: float,
    ) -> None:
        if self._scale_axis is None:
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

    def _gather_profile(self, key: str, *, require_name: bool) -> PersonProfile:
        profile_info = self._profiles[key]
        name_entry = cast(ttk.Entry, profile_info["name_entry"])
        name_var = cast(tk.StringVar, profile_info["name_var"])
        name = name_var.get().strip()
        if not name:
            if require_name:
                name_entry.focus_set()
                default_label = "Person A" if key == "person_a" else "Person B"
                raise ValueError(
                    f"Please enter a name for {default_label} before generating a report."
                )
            name = self._default_names[key]

        giving = cast(np.ndarray, profile_info["giving"]).astype(float, copy=True)
        receiving = cast(np.ndarray, profile_info["receiving"]).astype(float, copy=True)
        return PersonProfile(name=name, giving=giving, receiving=receiving)

    def _extract_profile(self, key: str) -> PersonProfile:
        profile = self._gather_profile(key, require_name=True)
        if profile.name:
            return profile
        raise ValueError("Invalid profile configuration.")

    def _schedule_live_update(self) -> None:
        if self._live_update_job is not None:
            self.master.after_cancel(self._live_update_job)
        # Update quickly so the radar charts closely track handle movement while
        # typing names or making other quick adjustments.
        # A 10 ms delay keeps the UI responsive while providing very smooth
        # visual feedback when users drag the handles in small increments.
        self._live_update_job = self.master.after(10, self._refresh_live_preview)

    def _refresh_live_preview(self) -> None:
        self._live_update_job = None
        person_a = self._gather_profile("person_a", require_name=False)
        person_b = self._gather_profile("person_b", require_name=False)
        self._render_plot(person_a, person_b)
        self._mark_insights_stale()

    def _mark_insights_stale(self) -> None:
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
                "Adjust the handles",
                (
                    "The following profiles still have every handle at 5.00: "
                    + ", ".join(untouched_profiles)
                    + ". Drag the radar chart handles to reflect real preferences before relying on this report."
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

    def _ensure_plot_canvas(self) -> None:
        if self.canvas is not None and self._axes is not None and self._figure is not None:
            return

        figure = Figure(figsize=(7.5, 5.6), dpi=100)
        grid = figure.add_gridspec(nrows=2, ncols=2, height_ratios=[4, 1], hspace=0.35, wspace=0.45)
        axes_tuple = tuple(
            figure.add_subplot(grid[0, index], projection="polar") for index in range(2)
        )

        for ax in axes_tuple:
            ax.set_xticks(self._base_angles)
            ax.set_xticklabels(CATEGORIES, fontsize=8)
            ax.set_yticks(np.arange(0, 11, 2))
            ax.set_ylim(0, 10)
            ax.tick_params(axis="x", pad=12)

        scale_axis = figure.add_subplot(grid[1, :])
        self._setup_scale_axis(scale_axis)

        figure.suptitle(
            "Love Language Alignment: Giving vs Receiving",
            fontsize=14,
            fontweight="bold",
        )
        figure.subplots_adjust(left=0.08, right=0.82, top=0.86, bottom=0.16)

        self._figure = figure
        self._axes = axes_tuple

        parent = self.canvas_container or self.plot_frame

        self.canvas = FigureCanvasTkAgg(figure, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._connect_canvas_events()

    def _connect_canvas_events(self) -> None:
        if self.canvas is None or self._canvas_cids:
            return
        self._canvas_cids = [
            self.canvas.mpl_connect("button_press_event", self._on_canvas_press),
            self.canvas.mpl_connect("motion_notify_event", self._on_canvas_motion),
            self.canvas.mpl_connect("button_release_event", self._on_canvas_release),
        ]

    def _closest_angle(self, theta: float) -> Tuple[int, float]:
        differences = np.abs((theta - self._base_angles + np.pi) % (2 * np.pi) - np.pi)
        index = int(np.argmin(differences))
        return index, float(differences[index])

    def _get_handle_artist(
        self, person_key: str, mode: str
    ) -> Tuple[object | None, object | None, str | None]:
        mapping = self._handle_lookup.get((person_key, mode))
        if mapping is None:
            return None, None, None
        axis_key, handle_key = mapping
        artists = self._plot_artists.get(axis_key)
        if not artists:
            return None, None, None
        handle = artists.get(handle_key)
        axis = artists.get("axis")
        return handle, axis, axis_key

    def _set_profile_value(self, person_key: str, mode: str, index: int, value: float) -> None:
        profile = self._profiles.get(person_key)
        if not profile:
            return
        if value is None or not np.isfinite(value):
            return
        values = cast(np.ndarray, profile[mode])
        clamped = float(np.clip(value, 0.0, 10.0))
        values[index] = clamped
        self._mark_insights_stale()
        self._update_visuals_from_profiles()

    def _update_visuals_from_profiles(self) -> None:
        person_a = self._gather_profile("person_a", require_name=False)
        person_b = self._gather_profile("person_b", require_name=False)
        self._render_plot(person_a, person_b)

    def _on_canvas_press(self, event) -> None:
        if getattr(event, "button", None) != 1 or event.inaxes is None:
            return
        if event.xdata is None or event.ydata is None:
            return

        active_person = self._active_person_var.get()
        for mode in ("giving", "receiving"):
            handle, axis, axis_key = self._get_handle_artist(active_person, mode)
            if handle is None or axis is None:
                continue
            if not getattr(handle, "get_visible", lambda: False)():
                continue
            if event.inaxes != axis:
                continue

            index, difference = self._closest_angle(event.xdata)
            if difference > self._drag_angle_threshold:
                continue

            self._drag_state = {
                "person": active_person,
                "mode": mode,
                "index": index,
                "axis_key": axis_key,
            }
            self._set_profile_value(active_person, mode, index, event.ydata)
            break

    def _on_canvas_motion(self, event) -> None:
        if not self._drag_state:
            return
        axis_key = cast(str, self._drag_state.get("axis_key"))
        artists = self._plot_artists.get(axis_key, {})
        axis = artists.get("axis")
        if axis is None or event.inaxes != axis:
            return
        if event.ydata is None:
            return

        self._set_profile_value(
            cast(str, self._drag_state["person"]),
            cast(str, self._drag_state["mode"]),
            cast(int, self._drag_state["index"]),
            event.ydata,
        )

    def _on_canvas_release(self, event) -> None:
        if getattr(event, "button", None) != 1:
            return
        self._drag_state = None

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
            giving_handle = ax.scatter(
                angles[:-1],
                giving_values[:-1],
                s=80,
                color="#55A868",
                edgecolors="white",
                linewidths=1.2,
                zorder=5,
            )
            receiving_handle = ax.scatter(
                angles[:-1],
                receiving_values[:-1],
                s=80,
                color="#4C72B0",
                edgecolors="white",
                linewidths=1.2,
                zorder=5,
            )
            legend = ax.legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1.02),
                borderaxespad=0.0,
                frameon=True,
            )
            artists = {
                "axis": ax,
                "giving_line": giving_line,
                "giving_fill": giving_fill,
                "giving_handle": giving_handle,
                "receiving_line": receiving_line,
                "receiving_fill": receiving_fill,
                "receiving_handle": receiving_handle,
                "legend": legend,
            }
            self._plot_artists[key] = artists
        else:
            artists["axis"] = ax
            giving_line = artists["giving_line"]
            giving_line.set_data(angles, giving_values)
            giving_line.set_label(giving_label)
            self._update_polygon(artists["giving_fill"], angles, giving_values)
            giving_handle = artists.get("giving_handle")
            if giving_handle is not None:
                giving_handle.set_offsets(
                    np.column_stack((angles[:-1], giving_values[:-1]))
                )

            receiving_line = artists["receiving_line"]
            receiving_line.set_data(angles, receiving_values)
            receiving_line.set_label(receiving_label)
            self._update_polygon(artists["receiving_fill"], angles, receiving_values)
            receiving_handle = artists.get("receiving_handle")
            if receiving_handle is not None:
                receiving_handle.set_offsets(
                    np.column_stack((angles[:-1], receiving_values[:-1]))
                )

            legend = artists["legend"]
            legend.remove()
            artists["legend"] = ax.legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1.02),
                borderaxespad=0.0,
                frameon=True,
            )

        ax.set_title(title, pad=15, fontsize=11)

    def _update_handle_visibility(self) -> None:
        active_person = self._active_person_var.get()
        for (person_key, _), (axis_key, handle_key) in self._handle_lookup.items():
            artists = self._plot_artists.get(axis_key)
            if not artists:
                continue
            handle = artists.get(handle_key)
            if handle is None:
                continue
            handle.set_visible(person_key == active_person)

    def _render_plot(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
    ) -> None:
        person_a_loop_giving = close_loop(person_a.giving)
        person_a_loop_receiving = close_loop(person_a.receiving)
        person_b_loop_giving = close_loop(person_b.giving)
        person_b_loop_receiving = close_loop(person_b.receiving)

        angles = self._angles

        self._ensure_plot_canvas()

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

        self._update_handle_visibility()
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
