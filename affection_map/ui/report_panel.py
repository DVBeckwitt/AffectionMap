"""Widgets responsible for displaying compatibility insights."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ReportPanel:
    def __init__(self, parent: ttk.Frame) -> None:
        self._container = ttk.Frame(parent, padding=(12, 8, 0, 0))
        self._container.columnconfigure(0, weight=1)
        self._container.rowconfigure(1, weight=1)

        title = ttk.Label(
            self._container,
            text="Compatibility insights",
            font=("Helvetica", 14, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        self._summary_var = tk.StringVar(
            value="Adjust profiles and generate a compatibility report for tailored advice."
        )
        self._summary_label = ttk.Label(
            self._container,
            textvariable=self._summary_var,
            wraplength=420,
            justify=tk.LEFT,
        )
        self._summary_label.grid(row=1, column=0, sticky="ew", pady=(6, 8))

        self._text = tk.Text(
            self._container,
            width=50,
            height=12,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Helvetica", 10),
        )
        self._text.grid(row=2, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self._container, orient=tk.VERTICAL, command=self._text.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self._text.configure(yscrollcommand=scrollbar.set)

    @property
    def container(self) -> ttk.Frame:
        return self._container

    def set_summary(self, message: str) -> None:
        self._summary_var.set(message)

    def set_report(self, content: str) -> None:
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        if content:
            self._text.insert(tk.END, content)
        self._text.configure(state=tk.DISABLED)
