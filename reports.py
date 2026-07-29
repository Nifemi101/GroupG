"""
reports.py
==========
Reporting, deadline monitoring, and workload analysis for the Engineering
Project Management System (features v & vi).

Same separation-of-concerns pattern as the finance tracker: ReportGenerator
turns raw rows fetched through DatabaseManager into summaries and matplotlib
figures, so no aggregation or chart-building logic leaks into the GUI layer.
"""

import csv
from collections import defaultdict
from typing import List

import matplotlib
matplotlib.use("Agg")  # headless-safe default; the GUI supplies its own TkAgg canvas
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from database import DatabaseManager
from model import Task

STATUS_COLORS = {
    "Completed": "#2e7d32",
    "In Progress": "#1565c0",
    "Due Soon": "#f9a825",
    "Overdue": "#c62828",
    "Not Started": "#757575",
}


class ReportGenerator:
    """Builds summaries, charts, and exports from the application's data."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ---------------------------------------------------------- summaries --
    def task_status_breakdown(self) -> dict:
        counts: dict = defaultdict(int)
        for t in self.db.get_tasks():
            counts[t.status] += 1
        return dict(counts)

    def project_status_breakdown(self) -> dict:
        counts: dict = defaultdict(int)
        for p in self.db.get_projects():
            counts[p.status] += 1
        return dict(counts)

    def team_workload(self) -> dict:
        """Active (not-yet-complete) task count per team member -- shows
        who's overloaded and who has room for more work."""
        return {m.name: self.db.active_task_count(m.id) for m in self.db.get_members()}

    def upcoming_deadlines(self, days_ahead: int = 7) -> List[Task]:
        """Unfinished tasks due within the next N days -- feeds the
        Dashboard's deadline-monitoring alerts."""
        tasks = [t for t in self.db.get_tasks()
                 if not t.is_complete and 0 <= t.days_remaining <= days_ahead]
        return sorted(tasks, key=lambda t: t.days_remaining)

    def overdue_tasks(self) -> List[Task]:
        tasks = [t for t in self.db.get_tasks() if t.status == "Overdue"]
        return sorted(tasks, key=lambda t: t.days_remaining)

    def project_progress_summary(self) -> List[tuple]:
        """(project_name, progress_percent, status) for every project."""
        return [(p.name, p.progress, p.status) for p in self.db.get_projects()]

    # ------------------------------------------------------------- charts --
    def figure_task_status_pie(self):
        data = self.task_status_breakdown()
        fig, ax = plt.subplots(figsize=(5, 4), constrained_layout=True)
        if not data:
            ax.text(0.5, 0.5, "No tasks recorded yet", ha="center", va="center")
            ax.axis("off")
            return fig
        colors = [STATUS_COLORS.get(k, "#999999") for k in data]
        ax.pie(data.values(), labels=data.keys(), autopct="%1.1f%%",
               startangle=90, colors=colors)
        ax.set_title("Task Status Breakdown", pad=16)
        return fig

    def figure_team_workload_bar(self):
        data = self.team_workload()
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        if not data:
            ax.text(0.5, 0.5, "No team members yet", ha="center", va="center")
            ax.axis("off")
            return fig
        names, counts = list(data.keys()), list(data.values())
        bars = ax.bar(names, counts, color="#1565c0")
        ax.set_title("Team Workload (Active Tasks)", pad=16)
        ax.set_ylabel("Active Tasks")
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))  # no fractional tasks
        for b in bars:
            ax.annotate(f"{int(b.get_height())}",
                        (b.get_x() + b.get_width() / 2, b.get_height()),
                        ha="center", va="bottom")
        ax.set_ylim(0, max(max(counts, default=1) * 1.25, 1))
        return fig

    def figure_project_progress_bar(self):
        data = self.project_progress_summary()
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        if not data:
            ax.text(0.5, 0.5, "No projects registered yet", ha="center", va="center")
            ax.axis("off")
            return fig
        names = [d[0] for d in data]
        progress = [d[1] for d in data]
        colors = [STATUS_COLORS.get(d[2], "#999999") for d in data]
        bars = ax.barh(names, progress, color=colors)
        ax.set_xlim(0, 110)   # headroom so the %-label never touches the edge
        ax.set_xlabel("Progress (%)")
        ax.set_title("Project Progress", pad=16)
        for b in bars:
            ax.annotate(f"{b.get_width():.0f}%",
                        (b.get_width(), b.get_y() + b.get_height() / 2),
                        ha="left", va="center", xytext=(4, 0), textcoords="offset points")
        return fig

    # ------------------------------------------------------------- export --
    def export_csv(self, path: str) -> None:
        tasks = self.db.get_tasks()
        members = {m.id: m.name for m in self.db.get_members()}
        projects = {p.project_id: p.name for p in self.db.get_projects()}
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Task", "Project", "Assigned To", "Deadline",
                              "Priority", "Progress", "Status"])
            for t in tasks:
                writer.writerow([
                    t.title, projects.get(t.project_id, "Unknown"),
                    members.get(t.member_id, "Unassigned"), t.deadline,
                    t.priority, f"{t.progress}%", t.status,
                ])

    def export_text_report(self, path: str) -> None:
        status_counts = self.task_status_breakdown()
        overdue = self.overdue_tasks()
        due_soon = self.upcoming_deadlines(7)
        with open(path, "w", encoding="utf-8") as f:
            f.write("ENGINEERING PROJECT STATUS REPORT\n")
            f.write("=" * 42 + "\n\n")
            f.write("Task status summary:\n")
            for status, count in status_counts.items():
                f.write(f"  - {status:<15} {count}\n")
            f.write(f"\nOverdue tasks: {len(overdue)}\n")
            for t in overdue:
                f.write(f"  - {t.title} ({abs(t.days_remaining)} days overdue)\n")
            f.write(f"\nDue within 7 days: {len(due_soon)}\n")
            for t in due_soon:
                f.write(f"  - {t.title} (due in {t.days_remaining} days)\n")