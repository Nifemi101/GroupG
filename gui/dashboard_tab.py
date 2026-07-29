"""
gui/dashboard_tab.py
=====================
Dashboard / overview screen -- the first thing the user sees.

Pulls together small pieces from every other part of the app: project/task
counts from DatabaseManager, and deadline-monitoring alerts (feature v) +
a quick chart from ReportGenerator. Nothing is calculated here -- it all
reuses logic already written, tested, and used elsewhere in the app.
"""

import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gui.base import BaseTab
from gui.utils import theme_facecolor


class DashboardTab(BaseTab):
    """Concrete tab: inherits BaseTab, implements build_ui() and refresh()."""

    def build_ui(self) -> None:
        # ---------------- summary stat row ----------------
        self.stats_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.stats_var,
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 10))

        # ---------------- deadline alerts ----------------
        alerts_frame = ttk.LabelFrame(self, text="Deadline Alerts", padding=10)
        alerts_frame.pack(fill="x", pady=(0, 10))
        self.alerts_container = ttk.Frame(alerts_frame)
        self.alerts_container.pack(fill="x")

        # ---------------- quick chart ----------------
        self.chart_frame = ttk.LabelFrame(self, text="Task Status Overview", padding=10)
        self.chart_frame.pack(fill="both", expand=True)
        self._canvas = None

    # -------------------------------------------------------------- BaseTab --
    def refresh(self) -> None:
        db = self.controller.db
        rg = self.controller.reports

        projects = db.get_projects()
        tasks = db.get_tasks()
        members = db.get_members()
        completed = sum(1 for t in tasks if t.is_complete)

        self.stats_var.set(
            f"Projects: {len(projects)}    Tasks: {len(tasks)} "
            f"({completed} completed)    Team Members: {len(members)}"
        )

        # ---- deadline alerts: overdue first (most urgent), then due-soon ----
        for widget in self.alerts_container.winfo_children():
            widget.destroy()

        overdue = rg.overdue_tasks()
        due_soon = rg.upcoming_deadlines(7)

        if not overdue and not due_soon:
            ttk.Label(self.alerts_container, text="No urgent deadlines. You're on track.",
                      foreground="#2e7d32").pack(anchor="w")
        else:
            for t in overdue:
                ttk.Label(self.alerts_container,
                          text=f"OVERDUE: {t.title} ({abs(t.days_remaining)} days overdue)",
                          foreground="#c62828").pack(anchor="w")
            for t in due_soon:
                ttk.Label(self.alerts_container,
                          text=f"Due Soon: {t.title} (due in {t.days_remaining} days)",
                          foreground="#a67c00").pack(anchor="w")

        # ---- quick chart ----
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
        fig = rg.figure_task_status_pie()
        bg = theme_facecolor(self)
        fig.set_facecolor(bg)
        for ax in fig.get_axes():
            ax.set_facecolor(bg)
        self._canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)