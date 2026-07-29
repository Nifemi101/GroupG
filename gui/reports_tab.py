"""
gui/reports_tab.py
==================
Reporting & data-export screen (features v & vi).

Pure view over ReportGenerator: embeds the three matplotlib charts it
builds (task-status pie, team-workload bar, project-progress bar) and wires
its two exporters (CSV task list, plain-text status report) to Save-As
dialogs. No aggregation or chart-building happens here -- the same split the
finance tracker's Reports tab used, keeping presentation in the GUI layer
and calculation in reports.py.
"""

from tkinter import ttk, filedialog, messagebox

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gui.base import BaseTab
from gui.utils import theme_facecolor


class ReportsTab(BaseTab):
    """Concrete tab: inherits BaseTab, implements build_ui() and refresh()."""

    def build_ui(self) -> None:
        # ---------------- export bar ----------------
        export_bar = ttk.LabelFrame(self, text="Export", padding=10)
        export_bar.pack(fill="x", pady=(0, 10))
        ttk.Button(export_bar, text="Export Tasks to CSV...",
                   command=self.export_csv).pack(side="left", padx=5)
        ttk.Button(export_bar, text="Export Status Report...",
                   command=self.export_text).pack(side="left", padx=5)

        # ---------------- charts (2x2 grid: pie + workload on top, progress below) --
        charts = ttk.Frame(self)
        charts.pack(fill="both", expand=True)
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        charts.rowconfigure(0, weight=1)
        charts.rowconfigure(1, weight=1)

        self._status_frame = ttk.LabelFrame(charts, text="Task Status", padding=8)
        self._status_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))

        self._workload_frame = ttk.LabelFrame(charts, text="Team Workload", padding=8)
        self._workload_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 5))

        self._progress_frame = ttk.LabelFrame(charts, text="Project Progress", padding=8)
        self._progress_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5, 0))

        # One canvas per chart frame; rebuilt from scratch on every refresh().
        self._canvases: dict = {}

    # ---------------- chart embedding ----------------
    def _embed(self, frame, fig) -> None:
        """Swap a freshly-built figure into `frame`, disposing the old canvas
        and closing the old figure so repeated refreshes don't leak."""
        old = self._canvases.get(frame)
        if old is not None:
            old.get_tk_widget().destroy()

        bg = theme_facecolor(self)
        fig.set_facecolor(bg)
        for ax in fig.get_axes():
            ax.set_facecolor(bg)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvases[frame] = canvas
        plt.close(fig)

    # ---------------- exports ----------------
    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Tasks to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="tasks.csv",
        )
        if not path:
            return
        try:
            self.controller.reports.export_csv(path)
        except OSError as e:
            messagebox.showerror("Export Failed", str(e))
            return
        messagebox.showinfo("Export Complete", f"Tasks exported to:\n{path}")

    def export_text(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Status Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="project_status_report.txt",
        )
        if not path:
            return
        try:
            self.controller.reports.export_text_report(path)
        except OSError as e:
            messagebox.showerror("Export Failed", str(e))
            return
        messagebox.showinfo("Export Complete", f"Report exported to:\n{path}")

    # -------------------------------------------------------------- BaseTab --
    def refresh(self) -> None:
        rg = self.controller.reports
        self._embed(self._status_frame, rg.figure_task_status_pie())
        self._embed(self._workload_frame, rg.figure_team_workload_bar())
        self._embed(self._progress_frame, rg.figure_project_progress_bar())
