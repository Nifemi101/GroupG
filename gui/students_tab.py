"""
gui/students_tab.py
====================
Group roster tab.

Shows the name and matriculation number of every student in the group.
Static/hardcoded list -- no database involvement.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import BaseTab

# Hardcoded group roster: (name, matric number)
STUDENTS = [
    ("Raphael Umameh", "Eng23cpe037"),
    ("ABU-MOHAMMED ABUBAKAR SODIQ", "ENG23CPE019"),
    ("Adejoh Triumph", "ENG23CPEO20"),
]


class StudentsTab(BaseTab):
    """Concrete tab: inherits BaseTab, implements build_ui() and refresh()."""

    def build_ui(self) -> None:
        table_frame = ttk.LabelFrame(self, text="Group Members", padding=10)
        table_frame.pack(fill="both", expand=True)

        cols = ("name", "matric")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        widths = {"name": 260, "matric": 160}
        headers = {"name": "Name", "matric": "Matric Number"}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for name, matric in STUDENTS:
            self.tree.insert("", "end", values=(name, matric))