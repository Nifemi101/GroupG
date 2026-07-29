"""
gui/tasks_tab.py
=================
Task allocation & progress tracking screen (features iii & iv).

The most interconnected tab in the app -- its dropdowns are built from
live Projects and Team Members data, and allocating a task checks the
assignee's current workload against member.max_capacity() (model.py)
before letting it through, warning rather than silently overloading them.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.base import BaseTab
from gui.utils import parse_date
from model import Task, TaskPriority

UNASSIGNED = "Unassigned"
ALL_PROJECTS = "All Projects"
ALL_MEMBERS = "All Members"

# Priority -> row text colour for the tasks table (ttk.Treeview can't colour a
# single cell, only a whole row's foreground).
PRIORITY_COLORS = {
    TaskPriority.LOW.value: "#2e7d32",       # green  -- safe / low urgency
    TaskPriority.MEDIUM.value: "#f9a825",    # amber  -- moderate
    TaskPriority.HIGH.value: "#c62828",      # red    -- urgent
    TaskPriority.CRITICAL.value: "#f57c00",  # orange -- warning / top priority
}


class TasksTab(BaseTab):
    """Concrete tab: inherits BaseTab, implements build_ui() and refresh()."""

    def build_ui(self) -> None:
        # ---------------- "Allocate Task" form ----------------
        form = ttk.LabelFrame(self, text="Allocate Task", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Title:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var, width=25).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Project:").grid(row=0, column=2, sticky="w", padx=5)
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(form, textvariable=self.project_var,
                                           state="readonly", width=20)
        self.project_combo.grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Assign To:").grid(row=0, column=4, sticky="w", padx=5)
        self.member_var = tk.StringVar(value=UNASSIGNED)
        self.member_combo = ttk.Combobox(form, textvariable=self.member_var,
                                          state="readonly", width=20)
        self.member_combo.grid(row=0, column=5, padx=5)

        ttk.Label(form, text="Deadline (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.deadline_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.deadline_var, width=14).grid(row=1, column=1, padx=5, sticky="w")

        ttk.Label(form, text="Priority:").grid(row=1, column=2, sticky="w", padx=5)
        self.priority_var = tk.StringVar(value=TaskPriority.MEDIUM.value)
        ttk.Combobox(form, textvariable=self.priority_var,
                     values=[p.value for p in TaskPriority],
                     state="readonly", width=12).grid(row=1, column=3, padx=5, sticky="w")

        ttk.Label(form, text="Description:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.desc_var, width=60).grid(
            row=2, column=1, columnspan=5, sticky="we", padx=5)

        ttk.Button(form, text="Allocate Task", command=self.add_task).grid(
            row=3, column=0, columnspan=6, pady=10)

        # ---------------- filter row ----------------
        filter_row = ttk.Frame(self)
        filter_row.pack(fill="x", pady=(0, 5))
        ttk.Label(filter_row, text="Filter by Project:").pack(side="left", padx=(0, 5))
        self.filter_project_var = tk.StringVar(value=ALL_PROJECTS)
        self.filter_project_combo = ttk.Combobox(filter_row, textvariable=self.filter_project_var,
                                                   state="readonly", width=20)
        self.filter_project_combo.pack(side="left", padx=(0, 15))
        self.filter_project_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_row, text="Filter by Member:").pack(side="left", padx=(0, 5))
        self.filter_member_var = tk.StringVar(value=ALL_MEMBERS)
        self.filter_member_combo = ttk.Combobox(filter_row, textvariable=self.filter_member_var,
                                                  state="readonly", width=20)
        self.filter_member_combo.pack(side="left")
        self.filter_member_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # ---------------- tasks table ----------------
        table_frame = ttk.LabelFrame(self, text="Tasks", padding=10)
        table_frame.pack(fill="both", expand=True)

        cols = ("title", "project", "assigned", "deadline", "priority", "progress", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        widths = {"title": 160, "project": 130, "assigned": 130, "deadline": 95,
                  "priority": 80, "progress": 80, "status": 100}
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        # Priority sets the row's text colour; the background stays default
        # (white) so the coloured text carries all the meaning here.
        for priority, color in PRIORITY_COLORS.items():
            self.tree.tag_configure(f"prio:{priority}", foreground=color)

        # ---------------- progress / reassignment controls ----------------
        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=8)

        ttk.Label(controls, text="Progress %:").pack(side="left", padx=(0, 5))
        self.progress_var = tk.StringVar()
        ttk.Spinbox(controls, from_=0, to=100, textvariable=self.progress_var,
                    width=6).pack(side="left", padx=(0, 5))
        ttk.Button(controls, text="Update Progress", command=self.update_progress).pack(
            side="left", padx=(0, 20))

        ttk.Label(controls, text="Reassign To:").pack(side="left", padx=(0, 5))
        self.reassign_var = tk.StringVar(value=UNASSIGNED)
        self.reassign_combo = ttk.Combobox(controls, textvariable=self.reassign_var,
                                            state="readonly", width=20)
        self.reassign_combo.pack(side="left", padx=(0, 5))
        ttk.Button(controls, text="Reassign", command=self.reassign_task).pack(
            side="left", padx=(0, 20))

        ttk.Button(controls, text="Delete Selected Task", command=self.delete_selected).pack(side="left")

    # -------------------------------------------------------------- lookups --
    def _project_lookup(self) -> dict:
        """{'Project Name': project_id} for every project."""
        return {p.name: p.project_id for p in self.controller.db.get_projects()}

    def _member_lookup(self) -> dict:
        """{'Name (Role)': member_id} for every team member."""
        return {f"{m.name} ({m.get_role()})": m.id for m in self.controller.db.get_members()}

    def _selected_task_id(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return int(self.tree.item(selected[0])["tags"][-1])

    # -------------------------------------------------------------- actions --
    def add_task(self) -> None:
        title = self.title_var.get().strip()
        projects = self._project_lookup()
        members = self._member_lookup()
        try:
            if not title:
                raise ValueError("Please enter a task title.")
            if self.project_var.get() not in projects:
                raise ValueError("Please select a project.")
            deadline = parse_date(self.deadline_var.get(), "deadline")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        project_id = projects[self.project_var.get()]
        member_id = members.get(self.member_var.get())  # None for "Unassigned"

        # Warn (don't block) if this would push the assignee past their
        # role's capacity -- see TeamMember.max_capacity() in model.py.
        if member_id is not None:
            db = self.controller.db
            member = next(m for m in db.get_members() if m.id == member_id)
            active = db.active_task_count(member_id)
            if active >= member.max_capacity():
                proceed = messagebox.askyesno(
                    "Member at Capacity",
                    f"{member.name} already has {active}/{member.max_capacity()} active "
                    f"tasks as a {member.get_role()}. Assign this task anyway?")
                if not proceed:
                    return

        task = Task(title, project_id, deadline, member_id,
                    self.priority_var.get(), self.desc_var.get().strip())
        self.controller.db.add_task(task)
        self.title_var.set("")
        self.deadline_var.set("")
        self.desc_var.set("")
        self.refresh()
        self.controller.refresh_all()   # Dashboard/Projects/Team all depend on tasks too

    def update_progress(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            messagebox.showinfo("No Task Selected", "Select a task first.")
            return
        try:
            progress = int(self.progress_var.get())
            self.controller.db.update_task_progress(task_id, progress)
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e) or "Enter a whole number 0-100.")
            return
        self.refresh()
        self.controller.refresh_all()

    def reassign_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            messagebox.showinfo("No Task Selected", "Select a task first.")
            return
        member_id = self._member_lookup().get(self.reassign_var.get())
        self.controller.db.reassign_task(task_id, member_id)
        self.refresh()
        self.controller.refresh_all()

    def delete_selected(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        self.controller.db.delete_task(task_id)
        self.refresh()
        self.controller.refresh_all()

    # -------------------------------------------------------------- BaseTab --
    def refresh(self) -> None:
        db = self.controller.db
        projects = self._project_lookup()
        members = self._member_lookup()
        project_names_by_id = {v: k for k, v in projects.items()}
        member_names_by_id = {v: k for k, v in members.items()}

        # Keep every dropdown in sync with current data -- new projects or
        # team members show up here without the user reopening the tab.
        self.project_combo["values"] = list(projects.keys())
        self.member_combo["values"] = [UNASSIGNED] + list(members.keys())
        self.reassign_combo["values"] = [UNASSIGNED] + list(members.keys())
        self.filter_project_combo["values"] = [ALL_PROJECTS] + list(projects.keys())
        self.filter_member_combo["values"] = [ALL_MEMBERS] + list(members.keys())

        filter_project_id = projects.get(self.filter_project_var.get())
        filter_member_id = members.get(self.filter_member_var.get())

        self.tree.delete(*self.tree.get_children())
        for t in db.get_tasks(project_id=filter_project_id, member_id=filter_member_id):
            self.tree.insert(
                "", "end",
                values=(t.title, project_names_by_id.get(t.project_id, "Unknown"),
                        member_names_by_id.get(t.member_id, UNASSIGNED),
                        t.deadline, t.priority, f"{t.progress}%", t.status),
                tags=(f"prio:{t.priority}", str(t.task_id)),
            )