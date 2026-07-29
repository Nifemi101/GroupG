# Engineering Project Management System — Project Recap

A desktop application for planning engineering work: registering projects,
building a team, allocating tasks to people, tracking each task's progress,
and watching deadlines. It's a Tkinter GUI on top of a small SQLite database,
with a reporting layer that turns the raw data into summaries, charts, and
exports.

The codebase is deliberately structured as an object-oriented teaching
project. It mirrors an earlier "finance tracker" and applies the same four
OOP pillars to a new domain:

- **Abstraction** — base classes define *what* something must do without
  saying *how* (`TeamMember`, `BaseTab`).
- **Inheritance** — concrete classes reuse shared behaviour from those bases
  (`Engineer`/`ProjectManager`/`QAEngineer`; each GUI tab).
- **Polymorphism** — the same call behaves differently depending on the real
  object (`member.get_role()`, `tab.refresh()`).
- **Encapsulation** — internal state is reachable only through validated
  property accessors (`TeamMember.name`, `.email`).

## Architecture at a glance

The app is split into four layers, each depending only on the one below it:

```
  GUI layer        gui/app.py + gui/*_tab.py   (Tkinter windows and tabs)
      |            reaches shared resources through the controller (app.py)
      v
  Reporting layer  reports.py                  (summaries, charts, exports)
      |            reads data only via DatabaseManager
      v
  Persistence      database.py                 (all SQL lives here)
      |            returns model objects, never raw rows
      v
  Domain models    model.py                    (TeamMember, Task, Project)
```

Key rule that keeps the layers clean: **nothing skips a layer.** Tabs never
write SQL and never talk to each other directly — they go through the
controller (`app.py`), which owns the single `DatabaseManager` and
`ReportGenerator`. The reporting layer never touches the GUI. The database
layer hands back real domain objects (an `Engineer`, a `Task`), not rows.

Three SQLite tables back the whole thing: `team_members`, `projects`, and
`tasks` (each task references a project, and optionally a member).


## What each file does

### `model.py` — the domain (business) objects

Defines the "things" the app manages, with no knowledge of the database or GUI.

- **`TaskPriority`** — an `Enum` of the four priority levels (Low, Medium,
  High, Critical). Using an enum means the rest of the code refers to
  `TaskPriority.HIGH.value` instead of loose strings.
- **`TeamMember` (Abstract Base Class)** — represents any person on the team.
  This is the **abstraction** pillar: it declares two abstract methods every
  role must implement — `get_role()` (the title) and `max_capacity()` (how
  many active tasks the role can carry) — without deciding the answers.
  It also owns **encapsulation**: `name` and `email` are `@property`
  accessors that validate on assignment (empty name rejected, email must
  contain `@` and a dotted domain), so an invalid member object can never
  exist. `describe()` and `to_dict()` are shared helpers.
- **`Engineer` / `ProjectManager` / `QAEngineer`** — concrete subclasses
  (**inheritance**). Each only supplies its own `get_role()` and
  `max_capacity()` (5 / 8 / 6). Calling `member.get_role()` on a mixed list
  returns different answers per object — that's **polymorphism**.
- **`Task` (dataclass)** — one unit of work: title, project, deadline,
  optional assignee, priority, description, progress (0–100). Its computed
  `@property` values are the important part: `is_complete` (progress ≥ 100),
  `days_remaining` (deadline minus today), and `status` — which turns those
  into one of `Completed / Overdue / Due Soon / In Progress`. The whole app
  reads `task.status` rather than recomputing that logic.
- **`Project` (dataclass)** — a project with a deadline. Its `progress` and
  `task_count` are **not stored**; they're filled in live by the database
  layer from the project's real tasks. `status` adds a `Not Started` state
  for projects with no tasks yet.

### `database.py` — persistence (all SQL lives here)

- **`DatabaseManager`** — a **singleton** (`__new__` returns the same
  instance every time) wrapping one SQLite connection. On first init it
  creates the three tables if they don't exist and enables foreign keys.
- **`ROLE_CLASSES`** — a dict mapping the role string stored in the DB back
  to the right class. This is what lets the DB rebuild a real `Engineer`
  object from a plain row.
- **Member methods** — `add_member`, `get_members`, `delete_member` (which
  *unassigns* a person's tasks rather than deleting them), and
  `active_task_count` (unfinished tasks a member carries — drives the
  overload warnings).
- **Project methods** — `add_project`, `get_projects`, `get_project`,
  `delete_project` (cascades to its tasks). `_row_to_project` is where a
  project's live `progress`/`task_count` get calculated with a `COUNT`/`AVG`
  query over its tasks.
- **Task methods** — `add_task`, `update_task_progress`, `reassign_task`,
  `get_tasks` (with optional project/member filters), `delete_task`.
- **Row factories** (`_row_to_member`, `_row_to_project`, `_row_to_task`) —
  convert raw SQLite rows into the model objects above, so callers never see
  a raw row.

### `reports.py` — summaries, charts, and exports

- **`STATUS_COLORS`** — the one place a status maps to a colour, reused by
  both the charts and the table row tints so "red means Overdue" everywhere.
- **`ReportGenerator`** — takes a `DatabaseManager` and turns its data into:
  - **Summaries** — `task_status_breakdown`, `project_status_breakdown`,
    `team_workload`, `upcoming_deadlines(days)`, `overdue_tasks`,
    `project_progress_summary`. These do the counting/grouping so the GUI
    doesn't have to.
  - **Charts** — `figure_task_status_pie`, `figure_team_workload_bar`,
    `figure_project_progress_bar`. Each returns a matplotlib `Figure` (using
    `constrained_layout` so titles don't clip when the canvas is resized) and
    handles the empty-data case gracefully.
  - **Exports** — `export_csv` (task list) and `export_text_report` (a
    plain-text status summary with overdue and due-soon sections).


### `gui/base.py` — the shared tab contract

- **`BaseTab` (Abstract Base Class, extends `ttk.Frame`)** — the parent of
  every screen. Its `__init__` stores the `controller` (the main window) and
  calls `build_ui()`. It declares two abstract methods every tab must
  implement: `build_ui()` (lay out the widgets once) and `refresh()` (reload
  on-screen data from the database). Because they share this contract, the
  main window can call `tab.refresh()` on any tab without knowing which
  concrete class it is — **polymorphism** again.

### `gui/utils.py` — small shared helpers

- **`parse_date(text, field_name)`** — turns user-typed text into a `date`,
  accepting several common formats (`YYYY-MM-DD`, `DD/MM/YYYY`, etc.) so a
  typo in separators isn't a hard wall. Raises a friendly `ValueError` on
  genuinely bad input, which the calling tab catches and shows in a dialog.
- **`tint(hex_color)`** — lightens a saturated chart colour into a pastel
  suitable as a table-row background. Shared by the Projects and Tasks tabs
  so a status colour looks consistent everywhere.

### `gui/app.py` — the main window and entry point

- **`EPMSApp` (extends `tk.Tk`)** — the **controller** every tab reaches
  through. It owns the single `DatabaseManager` and `ReportGenerator` and
  exposes them as `self.db` / `self.reports`, plus a `refresh_all()` hook.
  It builds a `ttk.Notebook`, instantiates each tab from the `TABS` list
  (Dashboard, Projects, Team, Tasks, Reports) in order, and refreshes the
  active tab whenever the user switches to it (so charts aren't rebuilt for
  every tab on every click). On close it shuts the DB connection cleanly.
  A `sys.path` shim at the top makes the project root importable however the
  file is launched (`python gui/app.py`, `python -m gui.app`, or an IDE run
  button).
- **`main()`** — constructs the window and starts the Tk event loop.

### `gui/dashboard_tab.py` — the overview screen

The first thing the user sees. A pure view: it calculates nothing itself.
`refresh()` pulls project/task/member counts from the DB, deadline alerts
from `reports.overdue_tasks()` and `upcoming_deadlines(7)` (overdue shown
first in red, due-soon in amber), and embeds the task-status pie chart.

### `gui/projects_tab.py` — project registration

A form to register a project (name, deadline, description) and a table of
every project with its **live** progress, task count, and status — all
calculated by the database layer, not typed in. Row background colours reuse
`STATUS_COLORS` via `tint()`. Deleting a project warns first, because it
cascades to that project's tasks.

### `gui/team_tab.py` — team member management

A form to register a member under one of the three roles, and a table showing
each person's active-task count against their role's `max_capacity()`. Anyone
at or over capacity is flagged with a red row tint; others green. Deleting a
member unassigns their tasks rather than deleting them.

### `gui/tasks_tab.py` — task allocation and progress (the busiest tab)

The most interconnected screen. Its dropdowns are built live from current
projects and members. Allocating a task checks the assignee's workload
against `max_capacity()` and **warns rather than blocks** if it would
overload them. The table supports filtering by project and by member, and
inline controls update progress, reassign, or delete the selected task. Row
**background** encodes status (via `STATUS_COLORS`); row **text colour**
encodes priority (`PRIORITY_COLORS`: Low green, Medium amber, High red,
Critical orange) — the two layer cleanly because ttk can colour a row's
foreground and background independently.

### `gui/reports_tab.py` — reporting and export

Embeds all three `reports.py` charts in a 2×2 grid (task-status pie and
team-workload bar on top, project-progress bar spanning the bottom) and wires
two buttons to the CSV and text-report exporters via Save-As dialogs. Each
chart is rebuilt on `refresh()` with `FigureCanvasTkAgg` and the old figure
closed to avoid leaks. Charts are recoloured to the live ttk theme background
so they blend into the window instead of sitting on white.

## How a typical action flows through the layers

Take **allocating a task** as the end-to-end example:

1. The user fills the form on the **Tasks tab** and clicks Allocate.
2. `TasksTab.add_task()` validates input (title present, project chosen,
   deadline parseable via `parse_date`), then checks the assignee's workload
   against `max_capacity()` and warns if over.
3. It builds a `Task` **model object** and calls `controller.db.add_task()`.
4. **`DatabaseManager`** writes one row of SQL and commits.
5. The tab calls `self.refresh()` (reload its own table) and
   `controller.refresh_all()` — so the **Dashboard** counts and pie chart,
   the **Projects** progress/status (recomputed from tasks), and the **Team**
   workload all update to reflect the new task.

The same pattern holds throughout: **GUI validates and calls the controller →
database persists → `refresh_all()` fans the change out to every tab.** Each
layer has one job, which is what makes the app easy to reason about and
extend.

