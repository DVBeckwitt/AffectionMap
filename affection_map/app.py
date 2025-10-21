"""Graphical interface for exploring love language alignment."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

from .analysis import PersonProfile, build_explanation, correlation
from .io import ProfileDataError, dump_profiles_to_file, load_profiles_from_file
from .ui import DEFAULT_THEME, ProfileInputPanel, RadarPlotPanel, ReportPanel, THEMES, Theme


class LoveLanguageApp:
    """Tkinter application that captures inputs and shows compatibility plots."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("AffectionMap – Love Language Alignment")
        self.master.geometry("1200x720")

        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        container = ttk.Frame(master, padding=20)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        self._profiles: Dict[str, PersonProfile] = {}
        self._current_theme: Theme = DEFAULT_THEME
        self._current_correlations: Tuple[float, float] = (0.0, 0.0)

        self._build_action_bar(container)

        self._input_panel = ProfileInputPanel(
            container,
            on_profiles_changed=self._on_profiles_changed,
            on_theme_changed=self._on_theme_changed,
            theme_names=THEMES.keys(),
            default_theme=self._current_theme.name,
        )
        self._input_panel.container.grid(row=1, column=0, sticky="nsew")

        visual_frame = ttk.Frame(container)
        visual_frame.grid(row=1, column=1, sticky="nsew")
        visual_frame.columnconfigure(0, weight=1)
        visual_frame.rowconfigure(0, weight=3)
        visual_frame.rowconfigure(1, weight=2)

        self._plot_panel = RadarPlotPanel(visual_frame, theme=self._current_theme)
        self._plot_panel.container.grid(row=0, column=0, sticky="nsew")

        self._report_panel = ReportPanel(visual_frame)
        self._report_panel.container.grid(row=1, column=0, sticky="nsew")

        self.master.after_idle(self._initialize_defaults)

    # ------------------------------------------------------------------ UI setup
    def _build_action_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        bar.columnconfigure(4, weight=1)

        ttk.Button(bar, text="Import Profiles…", command=self._on_import_profiles).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(bar, text="Export Profiles…", command=self._on_export_profiles).grid(
            row=0, column=1, padx=8
        )
        ttk.Button(bar, text="Save Figure…", command=self._on_save_figure).grid(row=0, column=2, padx=8)
        ttk.Button(bar, text="Generate Compatibility Report", command=self._on_generate_report).grid(
            row=0, column=3, padx=8
        )

    def _initialize_defaults(self) -> None:
        self._on_profiles_changed(self._input_panel.profiles())
        summary = (
            "Adjust the sliders or type directly into the spinboxes to describe how each person "
            "gives and receives love."
        )
        self._report_panel.set_summary(summary)
        self._report_panel.set_report("")

    # ------------------------------------------------------------------ Event handlers
    def _on_profiles_changed(self, profiles: Dict[str, PersonProfile]) -> None:
        self._profiles = profiles
        person_a = profiles.get("person_a")
        person_b = profiles.get("person_b")
        if not person_a or not person_b:
            return

        corr_a_to_b = correlation(person_a.giving, person_b.receiving)
        corr_b_to_a = correlation(person_b.giving, person_a.receiving)
        self._current_correlations = (corr_a_to_b, corr_b_to_a)

        self._plot_panel.render(person_a, person_b, correlations=self._current_correlations)

        summary = (
            f"{self._format_corr_summary(person_a.name, person_b.name, corr_a_to_b)}\n"
            f"{self._format_corr_summary(person_b.name, person_a.name, corr_b_to_a)}\n"
            "Select 'Generate Compatibility Report' for tailored insights."
        )
        self._report_panel.set_summary(summary)

    def _on_theme_changed(self, theme_name: str) -> None:
        self._current_theme = THEMES.get(theme_name, DEFAULT_THEME)
        self._plot_panel.set_theme(self._current_theme)

    @staticmethod
    def _format_corr_summary(giver: str, receiver: str, value: float) -> str:
        if np.isfinite(value):
            return f"{giver} → {receiver}: r = {value:.2f}"
        return f"{giver} → {receiver}: r is undefined"

    def _on_generate_report(self) -> None:
        person_a = self._profiles.get("person_a")
        person_b = self._profiles.get("person_b")
        if not person_a or not person_b:
            messagebox.showinfo("Incomplete profiles", "Provide information for both people first.")
            return

        report = build_explanation(
            person_a,
            person_b,
            corr_a_to_b=self._current_correlations[0],
            corr_b_to_a=self._current_correlations[1],
        )
        self._report_panel.set_report(report)
        self._report_panel.set_summary(
            "Narrative generated from the current love language preferences."
        )

    def _on_save_figure(self) -> None:
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
            self._plot_panel.save_figure(file_path)
        except Exception as error:  # pragma: no cover - GUI path
            messagebox.showerror("Save failed", str(error))

    def _on_import_profiles(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Import profiles",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            profiles = load_profiles_from_file(path)
        except (OSError, ProfileDataError, ValueError) as error:  # pragma: no cover - GUI path
            messagebox.showerror("Import failed", str(error))
            return

        self._input_panel.set_profiles(profiles)
        messagebox.showinfo("Import complete", f"Loaded profiles from {path.name}.")

    def _on_export_profiles(self) -> None:
        if not self._profiles:
            messagebox.showinfo("Nothing to export", "Adjust the profiles before exporting.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export profiles",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            dump_profiles_to_file(path, self._profiles)
        except OSError as error:  # pragma: no cover - GUI path
            messagebox.showerror("Export failed", str(error))
            return

        messagebox.showinfo("Export complete", f"Saved profiles to {path.name}.")


def main() -> None:
    root = tk.Tk()
    LoveLanguageApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
