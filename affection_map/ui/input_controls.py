"""Widgets that capture profile information for AffectionMap."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable

import numpy as np
import tkinter as tk
from tkinter import ttk

from ..analysis import CATEGORIES, PersonProfile

OnProfilesChanged = Callable[[Dict[str, PersonProfile]], None]
OnThemeChanged = Callable[[str], None]


@dataclass
class _ValueControl:
    var: tk.DoubleVar
    scale: ttk.Scale
    spinbox: ttk.Spinbox


@dataclass
class _PersonControls:
    name_var: tk.StringVar
    giving: Dict[str, _ValueControl]
    receiving: Dict[str, _ValueControl]


class ProfileInputPanel:
    """Collects user inputs for the two compared people."""

    def __init__(
        self,
        parent: ttk.Frame,
        *,
        on_profiles_changed: OnProfilesChanged,
        on_theme_changed: OnThemeChanged,
        theme_names: Iterable[str],
        default_theme: str,
    ) -> None:
        self._container = ttk.Frame(parent, padding=(0, 0, 16, 0))

        self._on_profiles_changed = on_profiles_changed
        self._on_theme_changed = on_theme_changed
        self._suspend_callbacks = False

        self._people: Dict[str, _PersonControls] = {}

        self._build_header(theme_names, default_theme)
        self._build_people_rows()

    @property
    def container(self) -> ttk.Frame:
        return self._container

    def profiles(self) -> Dict[str, PersonProfile]:
        return {
            person_id: self._build_profile(person_id, controls)
            for person_id, controls in self._people.items()
        }

    def set_profiles(self, profiles: Dict[str, PersonProfile]) -> None:
        self._suspend_callbacks = True
        try:
            for person_id, controls in self._people.items():
                profile = profiles.get(person_id)
                if profile is None:
                    continue

                controls.name_var.set(profile.name)
                for category, value in zip(CATEGORIES, profile.giving):
                    self._set_value(controls.giving[category], float(value))
                for category, value in zip(CATEGORIES, profile.receiving):
                    self._set_value(controls.receiving[category], float(value))
        finally:
            self._suspend_callbacks = False
            self._notify_change()

    def _build_header(self, theme_names: Iterable[str], default_theme: str) -> None:
        header = ttk.Label(
            self._container,
            text="Compare how two people prefer to give and receive love.",
            font=("Helvetica", 16, "bold"),
        )
        header.grid(row=0, column=0, sticky="w")

        instructions = ttk.Label(
            self._container,
            text=(
                "Adjust each slider or spinbox to rate how strongly a love language resonates "
                "from 0 (not at all) to 10 (essential)."
            ),
            wraplength=360,
        )
        instructions.grid(row=1, column=0, sticky="w", pady=(8, 18))

        theme_frame = ttk.Frame(self._container)
        theme_frame.grid(row=2, column=0, sticky="w", pady=(0, 18))

        ttk.Label(theme_frame, text="Color theme:").grid(row=0, column=0, padx=(0, 6))
        self._theme_var = tk.StringVar(value=default_theme)
        self._theme_combo = ttk.Combobox(
            theme_frame,
            state="readonly",
            values=list(theme_names),
            textvariable=self._theme_var,
            width=14,
        )
        self._theme_combo.grid(row=0, column=1)
        self._theme_combo.bind("<<ComboboxSelected>>", self._handle_theme_changed)

    def _build_people_rows(self) -> None:
        people_frame = ttk.Frame(self._container)
        people_frame.grid(row=3, column=0, sticky="nsew")
        people_frame.columnconfigure(0, weight=1)
        people_frame.columnconfigure(1, weight=1)

        self._people["person_a"] = self._build_person_section(people_frame, "Person A", column=0)
        self._people["person_b"] = self._build_person_section(people_frame, "Person B", column=1)

    def _build_person_section(self, parent: ttk.Frame, title: str, *, column: int) -> _PersonControls:
        frame = ttk.LabelFrame(parent, text=title, padding=(12, 12))
        frame.grid(row=0, column=column, padx=(0, 12) if column == 0 else (12, 0), sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=0)

        name_var = tk.StringVar(value=title.split()[-1])
        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=name_var)
        entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        name_var.trace_add("write", self._notify_change)

        giving_controls = self._build_value_table(frame, "Giving", start_row=1)
        receiving_controls = self._build_value_table(frame, "Receiving", start_row=1 + len(CATEGORIES))

        return _PersonControls(name_var=name_var, giving=giving_controls, receiving=receiving_controls)

    def _build_value_table(self, parent: ttk.Frame, label: str, *, start_row: int) -> Dict[str, _ValueControl]:
        ttk.Label(parent, text=f"{label} preferences", font=("Helvetica", 10, "bold")).grid(
            row=start_row, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )

        controls: Dict[str, _ValueControl] = {}
        for offset, category in enumerate(CATEGORIES, start=1):
            row = start_row + offset
            ttk.Label(parent, text=category).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar(value=5.0)
            var.trace_add("write", self._notify_change)

            scale = ttk.Scale(parent, from_=0.0, to=10.0, variable=var, orient=tk.HORIZONTAL)
            scale.grid(row=row, column=1, sticky="ew", padx=(0, 6))

            spinbox = ttk.Spinbox(
                parent,
                from_=0.0,
                to=10.0,
                increment=0.5,
                textvariable=var,
                width=5,
                validate="focusout",
                validatecommand=(parent.register(self._validate_spinbox_value), "%P", "%W"),
            )
            spinbox.grid(row=row, column=2, sticky="ew")

            controls[category] = _ValueControl(var=var, scale=scale, spinbox=spinbox)

        return controls

    def _validate_spinbox_value(self, value: str, widget_name: str) -> bool:
        widget = self._container.nametowidget(widget_name)
        if value.strip() == "":
            if isinstance(widget, ttk.Spinbox):
                widget.delete(0, tk.END)
                widget.insert(0, "0.0")
            return True

        try:
            numeric = float(value)
        except ValueError:
            return False

        numeric = min(10.0, max(0.0, numeric))
        if isinstance(widget, ttk.Spinbox):
            widget.delete(0, tk.END)
            widget.insert(0, f"{numeric:.2f}")
        return True

    def _build_profile(self, person_id: str, controls: _PersonControls) -> PersonProfile:
        giving = np.array([controls.giving[category].var.get() for category in CATEGORIES], dtype=float)
        receiving = np.array([controls.receiving[category].var.get() for category in CATEGORIES], dtype=float)
        return PersonProfile(name=controls.name_var.get().strip() or person_id.title(), giving=giving, receiving=receiving)

    def _set_value(self, control: _ValueControl, value: float) -> None:
        value = float(min(10.0, max(0.0, value)))
        control.var.set(value)

    def _notify_change(self, *_: object) -> None:
        if self._suspend_callbacks:
            return
        profiles = self.profiles()
        self._on_profiles_changed(profiles)

    def _handle_theme_changed(self, *_: object) -> None:
        if self._suspend_callbacks:
            return
        self._on_theme_changed(self._theme_var.get())

    def select_theme(self, theme_name: str) -> None:
        if theme_name not in self._theme_combo.cget("values"):
            return
        self._theme_var.set(theme_name)
        self._handle_theme_changed()
