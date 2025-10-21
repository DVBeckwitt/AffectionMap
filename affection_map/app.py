"""Graphical interface for exploring love language alignment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.stats import pearsonr
import tkinter as tk
from tkinter import ttk, messagebox

CATEGORIES: List[str] = [
    "Words of Affirmation",
    "Acts of Service",
    "Receiving Gifts",
    "Quality Time",
    "Physical Touch",
]


@dataclass
class PersonProfile:
    """Container for an individual's love language values."""

    name: str
    giving: np.ndarray
    receiving: np.ndarray


class LoveLanguageApp:
    """Tkinter application that captures inputs and shows compatibility plots."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("AffectionMap – Love Language Alignment")
        self.master.geometry("1100x720")

        self._input_widgets: Dict[str, Dict[str, List[ttk.Scale]]] = {}
        self.canvas: FigureCanvasTkAgg | None = None
        self.text_var = tk.StringVar()

        self._build_layout()

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
                row=0, column=idx, sticky=tk.CENTER
            )

        def _update_display(value: str) -> None:
            rounded = round(float(value), 2)
            display_var.set(f"{rounded:.2f}")

        slider.configure(command=_update_display)
        _update_display("5.0")

        return container, slider

    def _create_action_section(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent)
        section.pack(fill=tk.X, pady=(5, 15))

        button = ttk.Button(section, text="Generate Compatibility Report", command=self._on_generate)
        button.pack(pady=5)

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

    def _collect_slider_values(self, sliders: List[ttk.Scale]) -> List[float]:
        values: List[float] = []
        for widget in sliders:
            value = round(float(widget.get()), 2)
            if not 0 <= value <= 10:
                raise ValueError("Scores must be between 0 and 10.")
            values.append(value)
        return values

    def _extract_profile(self, key: str) -> PersonProfile:
        widgets = self._input_widgets[key]
        name = widgets["name"].get().strip()  # type: ignore[assignment]
        if not name:
            name = "Person A" if key == "person_a" else "Person B"

        giving = np.array(self._collect_slider_values(widgets["giving"]))
        receiving = np.array(self._collect_slider_values(widgets["receiving"]))
        return PersonProfile(name=name, giving=giving, receiving=receiving)

    def _on_generate(self) -> None:
        try:
            person_a = self._extract_profile("person_a")
            person_b = self._extract_profile("person_b")
        except ValueError as error:  # pragma: no cover - GUI path
            messagebox.showerror("Invalid input", str(error))
            return

        self._render_report(person_a, person_b)

    def _render_report(self, person_a: PersonProfile, person_b: PersonProfile) -> None:
        person_a_loop_giving = self._close_loop(person_a.giving)
        person_a_loop_receiving = self._close_loop(person_a.receiving)
        person_b_loop_giving = self._close_loop(person_b.giving)
        person_b_loop_receiving = self._close_loop(person_b.receiving)

        corr_a_to_b = self._correlation(person_a.giving, person_b.receiving)
        corr_b_to_a = self._correlation(person_b.giving, person_a.receiving)

        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        figure = Figure(figsize=(7.5, 5), dpi=100)
        axes = figure.subplots(1, 2, subplot_kw={"projection": "polar"})

        angles = self._angles()

        self._plot_profile(
            axes[0],
            angles,
            person_a_loop_giving,
            person_b_loop_receiving,
            f"{person_a.name} → {person_b.name} (r = {corr_a_to_b:.2f})",
            f"{person_a.name} Giving",
            f"{person_b.name} Receiving",
        )

        self._plot_profile(
            axes[1],
            angles,
            person_b_loop_giving,
            person_a_loop_receiving,
            f"{person_b.name} → {person_a.name} (r = {corr_b_to_a:.2f})",
            f"{person_b.name} Giving",
            f"{person_a.name} Receiving",
        )

        figure.suptitle("Love Language Alignment: Giving vs Receiving", fontsize=14, fontweight="bold")
        figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        explanation = self._build_explanation(person_a, person_b, corr_a_to_b, corr_b_to_a)
        self.text_var.set(explanation)

    @staticmethod
    def _correlation(first: np.ndarray, second: np.ndarray) -> float:
        if np.all(first == first[0]) or np.all(second == second[0]):
            return 0.0
        corr, _ = pearsonr(first, second)
        return float(corr)

    @staticmethod
    def _close_loop(values: np.ndarray) -> np.ndarray:
        return np.concatenate((values, [values[0]]))

    @staticmethod
    def _angles() -> List[float]:
        angles = np.linspace(0, 2 * np.pi, len(CATEGORIES), endpoint=False).tolist()
        angles += angles[:1]
        return angles

    def _plot_profile(
        self,
        ax,
        angles: List[float],
        giving_values: np.ndarray,
        receiving_values: np.ndarray,
        title: str,
        giving_label: str,
        receiving_label: str,
    ) -> None:
        ax.plot(angles, giving_values, color="#55A868", linewidth=2, label=giving_label)
        ax.fill(angles, giving_values, color="#55A868", alpha=0.25)
        ax.plot(angles, receiving_values, color="#4C72B0", linewidth=2, label=receiving_label)
        ax.fill(angles, receiving_values, color="#4C72B0", alpha=0.25)
        ax.set_title(title, pad=15, fontsize=11)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(CATEGORIES, fontsize=8)
        ax.set_yticks(np.arange(0, 11, 2))
        ax.set_ylim(0, 10)
        ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

    def _build_explanation(
        self,
        person_a: PersonProfile,
        person_b: PersonProfile,
        corr_a_to_b: float,
        corr_b_to_a: float,
    ) -> str:
        summary = [
            self._interpret_correlation(
                person_a.name,
                person_b.name,
                corr_a_to_b,
                "how well what they like to give matches what their partner enjoys receiving",
            ),
            self._interpret_correlation(
                person_b.name,
                person_a.name,
                corr_b_to_a,
                "how well their giving style lands for their partner",
            ),
        ]

        strongest_alignment = np.argmax((person_a.giving + person_b.receiving) / 2)
        weakest_alignment = np.argmin(np.abs(person_a.giving - person_b.receiving))

        summary.append(
            f"\nGreatest shared enthusiasm: {CATEGORIES[strongest_alignment]} — both of you score "
            "high here, so this language may feel especially natural together."
        )
        summary.append(
            f"Most aligned expectations: {CATEGORIES[weakest_alignment]} — your giving and receiving "
            "scores are the closest match in this area."
        )

        return "\n\n".join(summary)

    @staticmethod
    def _interpret_correlation(giver: str, receiver: str, value: float, description: str) -> str:
        strength = "low"
        if value >= 0.75:
            strength = "very strong"
        elif value >= 0.5:
            strength = "strong"
        elif value >= 0.25:
            strength = "moderate"
        elif value <= -0.25:
            strength = "challenging"

        return (
            f"{giver} → {receiver}: r = {value:.2f}. This indicates {strength} alignment in {description}."
        )


def main() -> None:
    root = tk.Tk()
    LoveLanguageApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
