"""
gui/projects_tab.py
====================
Project registration screen (feature i.).

Lets the user register a new project with a deadline, then lists every
project with its LIVE progress and status -- both calculated by
DatabaseManager from that project's real tasks (see database.py's
_row_to_project), not typed in or stored directly. Row colours reuse the
exact same STATUS_COLORS palette as the Reports charts, so a project's
colour means the same thing everywhere in the app.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.base import BaseTab
from gui.utils import parse_date
from model import Project


class ProjectsTab(BaseTab):
    """Concrete tab: inherits BaseTab, implements build_ui() and refresh()."""

    def build_ui(self) -> None:
        # ---------------- "Register Project" form ----------------
        form = ttk.LabelFrame(self, text="Register Project", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Project Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=28).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Deadline (YYYY-MM-DD):").grid(row=0, column=2, sticky="w", padx=5)
        self.deadline_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.deadline_var, width=14).grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Description:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.desc_var, width=55).grid(
            row=1, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Button(form, text="Register Project", command=self.add_project).grid(
            row=2, column=0, columnspan=4, pady=10)

        # ---------------- projects table ----------------
        table_frame = ttk.LabelFrame(self, text="Projects", padding=10)
        table_frame.pack(fill="both", expand=True)

        cols = ("name", "deadline", "days_left", "progress", "tasks", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        widths = {"name": 180, "deadline": 100, "days_left": 90,
                  "progress": 90, "tasks": 70, "status": 110}
        headers = {"name": "Project", "deadline": "Deadline", "days_left": "Days Left",
                   "progress": "Progress", "tasks": "Tasks", "status": "Status"}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        ttk.Button(self, text="Delete Selected Project", command=self.delete_selected).pack(pady=8)

    # -------------------------------------------------------------- actions --
    def add_project(self) -> None:
        name = self.name_var.get().strip()
        try:
            if not name:
                raise ValueError("Please enter a project name.")
            deadline = parse_date(self.deadline_var.get(), "deadline")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        project = Project(name, self.desc_var.get().strip(), deadline)
        self.controller.db.add_project(project)
        self.name_var.set("")
        self.deadline_var.set("")
        self.desc_var.set("")
        self.refresh()
        self.controller.refresh_all()   # Tasks tab's project dropdown needs the new project too

    def delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        project_id = int(self.tree.item(selected[0])["tags"][-1])
        if not messagebox.askyesno(
                "Delete Project",
                "Deleting this project will also delete all of its tasks. Continue?"):
            return
        self.controller.db.delete_project(project_id)
        self.refresh()
        self.controller.refresh_all()

    # -------------------------------------------------------------- BaseTab --
    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for p in self.controller.db.get_projects():
            self.tree.insert(
                "", "end",
                values=(p.name, p.deadline, p.days_remaining,
                        f"{p.progress}%", p.task_count, p.status),
                tags=(str(p.project_id),),
            )
            