"""
gui/app.py
==========
Main application window and entry point for the Engineering Project
Management System.

This is the `controller` every tab reaches through. It owns the two shared
resources -- a DatabaseManager (persistence) and a ReportGenerator (summaries
and charts) -- and hands them, plus a refresh_all() hook, to each tab via the
BaseTab constructor. The tabs never talk to the database or each other
directly; they go through this window, which is what keeps a change made on
one tab (a new member, a deleted project) visible on all the others.
"""

import os
import sys

# Make the project root importable no matter how this file is launched
# (python gui/app.py, python -m gui.app, or from an IDE run button), so both
# `from gui.*` and the top-level `model`/`database`/`reports` modules resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk

from database import DatabaseManager
from reports import ReportGenerator

from gui.dashboard_tab import DashboardTab
from gui.projects_tab import ProjectsTab
from gui.team_tab import TeamTab
from gui.tasks_tab import TasksTab
from gui.reports_tab import ReportsTab
from gui.students_tab import StudentsTab

# (Tab class, notebook label) in display order. self.tabs is built from this,
# so the notebook order and the refresh order always stay in step.
TABS = [
    (DashboardTab, "Dashboard"),
    (ProjectsTab, "Projects"),
    (TeamTab, "Team"),
    (TasksTab, "Tasks"),
    (ReportsTab, "Reports"),
    (StudentsTab, "Students"),
]


class EPMSApp(tk.Tk):
    """The main window: builds the notebook, owns db + reports, and exposes
    refresh_all() so any tab can push its changes out to every other tab."""

    def __init__(self):
        super().__init__()
        self.title("Engineering Project Management System")
        self.geometry("1024x720")
        self.minsize(900, 640)

        # Shared resources handed to every tab (see BaseTab.__init__).
        self.db = DatabaseManager()
        self.reports = ReportGenerator(self.db)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tabs = []
        for tab_cls, label in TABS:
            tab = tab_cls(self.notebook, self)
            self.notebook.add(tab, text=label)
            self.tabs.append(tab)

        # Refreshing the tab the user just switched to keeps its data current
        # without paying to rebuild every other tab's charts on each click.
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------- controller --
    def refresh_all(self) -> None:
        """Reload every tab from the database. Called at startup and by any
        tab after it mutates data others depend on (a new project changes the
        Tasks dropdown, a completed task changes the Dashboard chart, ...)."""
        for tab in self.tabs:
            tab.refresh()

    def _on_tab_changed(self, _event) -> None:
        self.tabs[self.notebook.index("current")].refresh()

    def _on_close(self) -> None:
        self.db.close()
        self.destroy()


def main() -> None:
    EPMSApp().mainloop()


if __name__ == "__main__":
    main()