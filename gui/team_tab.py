"""
gui/team_tab.py
================
Team member assignment screen (feature ii.).

Lets the user register team members under one of three roles (Engineer,
Project Manager, QA Engineer) and shows each person's current workload
against their role's capacity -- reusing member.max_capacity() from
model.py and db.active_task_count() from database.py rather than
recalculating either here.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.base import BaseTab
from database import ROLE_CLASSES  # {"Engineer": Engineer, "Project Manager": ProjectManager, ...}


class TeamTab(BaseTab):
    """Concrete tab: inherits BaseTab, implements build_ui() and refresh()."""

    def build_ui(self) -> None:
        # ---------------- "Add Team Member" form ----------------
        form = ttk.LabelFrame(self, text="Add Team Member", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=22).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Email:").grid(row=0, column=2, sticky="w", padx=5)
        self.email_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.email_var, width=25).grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Role:").grid(row=0, column=4, sticky="w", padx=5)
        self.role_var = tk.StringVar(value="Engineer")
        ttk.Combobox(form, textvariable=self.role_var, values=list(ROLE_CLASSES.keys()),
                     state="readonly", width=16).grid(row=0, column=5, padx=5)

        ttk.Button(form, text="Add Member", command=self.add_member).grid(
            row=1, column=0, columnspan=6, pady=10)

        # ---------------- team table ----------------
        table_frame = ttk.LabelFrame(self, text="Team", padding=10)
        table_frame.pack(fill="both", expand=True)

        cols = ("name", "email", "role", "workload")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        widths = {"name": 160, "email": 220, "role": 140, "workload": 140}
        headers = {"name": "Name", "email": "Email", "role": "Role",
                   "workload": "Active Tasks / Capacity"}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        # Flag anyone at or over their role's capacity, same red/green
        # language used for budgets in the finance tracker.
        self.tree.tag_configure("overloaded", background="#f2dede")
        self.tree.tag_configure("ok", background="#dff0d8")

        ttk.Button(self, text="Delete Selected", command=self.delete_selected).pack(pady=8)

    # -------------------------------------------------------------- actions --
    def add_member(self) -> None:
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        role_cls = ROLE_CLASSES[self.role_var.get()]
        try:
            member = role_cls(name, email)     # validation lives in model.py
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        self.controller.db.add_member(member)
        self.name_var.set("")
        self.email_var.set("")
        self.refresh()
        self.controller.refresh_all()   # Projects/Tasks dropdowns need the new member too

    def delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        member_id = int(self.tree.item(selected[0])["tags"][-1])
        self.controller.db.delete_member(member_id)
        self.refresh()
        self.controller.refresh_all()

    # -------------------------------------------------------------- BaseTab --
    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for m in self.controller.db.get_members():
            active = self.controller.db.active_task_count(m.id)
            capacity = m.max_capacity()
            tag = "overloaded" if active >= capacity else "ok"
            self.tree.insert(
                "", "end",
                values=(m.name, m.email, m.get_role(), f"{active} / {capacity}"),
                tags=(tag, str(m.id)),
            )