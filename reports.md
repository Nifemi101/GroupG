# Engineering Project Management System - Detailed Project Report

**Group G** | Python, Tkinter, SQLite, Matplotlib | July 2026

---

## Table of Contents

1. [Introduction](#chapter-1-introduction)
2. [Technologies Used](#chapter-2-technologies-used)
3. [System Architecture](#chapter-3-system-architecture)
4. [Database Design](#chapter-4-database-design)
5. [model.py - The Domain Models](#chapter-5-modelpy---the-domain-models)
6. [database.py - The Persistence Layer](#chapter-6-databasepy---the-persistence-layer)
7. [reports.py - The Reporting Layer](#chapter-7-reportspy---the-reporting-layer)
8. [gui/base.py - The Shared Tab Contract](#chapter-8-guibasepy---the-shared-tab-contract)
9. [gui/utils.py - Shared Helpers](#chapter-9-guiutilspy---shared-helpers)
10. [gui/app.py - The Main Window and Controller](#chapter-10-guiapppy---the-main-window-and-controller)
11. [gui/dashboard_tab.py - The Overview Screen](#chapter-11-guidashboard_tabpy---the-overview-screen)
12. [gui/projects_tab.py - Project Registration](#chapter-12-guiprojects_tabpy---project-registration)
13. [gui/team_tab.py - Team Management](#chapter-13-guiteam_tabpy---team-management)
14. [gui/tasks_tab.py - Task Allocation and Progress](#chapter-14-guitasks_tabpy---task-allocation-and-progress)
15. [gui/reports_tab.py - Reporting and Export](#chapter-15-guireports_tabpy---reporting-and-export)
16. [Development Steps and Key Decisions](#chapter-16-development-steps-and-key-decisions)
17. [Running the Application](#chapter-17-running-the-application)
18. [Conclusion](#chapter-18-conclusion)

---

## Chapter 1: Introduction

The Engineering Project Management System (EPMS) is a desktop application
that helps an engineering team plan and monitor its work. It covers six
core features:

1. **Project registration** - create projects with deadlines and descriptions.
2. **Team member assignment** - register people under one of three roles
   (Engineer, Project Manager, QA Engineer).
3. **Task allocation** - create tasks inside a project and assign them to a
   team member, with a built-in guard against overloading anyone.
4. **Progress tracking** - update each task's progress from 0 to 100 percent;
   project progress is derived automatically from its tasks.
5. **Deadline monitoring** - the dashboard flags overdue tasks and tasks due
   within the next seven days.
6. **Reporting and visualization** - pie and bar charts summarising task
   status, team workload, and project progress, plus CSV and text exports.

Beyond its practical purpose, the codebase is deliberately structured as an
object-oriented programming showcase. It mirrors the design of an earlier
finance tracker project and demonstrates the four OOP pillars in working
code:

- **Abstraction** - abstract base classes define what something must do
  without saying how (`TeamMember` in the models, `BaseTab` in the GUI).
- **Inheritance** - concrete classes reuse shared behaviour from those bases
  (the three role classes; every GUI tab).
- **Polymorphism** - one call site, many behaviours (`member.get_role()`,
  `member.max_capacity()`, `tab.refresh()`).
- **Encapsulation** - internal state is only reachable through validated
  property accessors (`TeamMember.name`, `TeamMember.email`).

## Chapter 2: Technologies Used

| Technology | Role in the project |
|---|---|
| Python 3 | Implementation language for every layer |
| Tkinter / ttk | The GUI toolkit: windows, notebook tabs, forms, tables |
| SQLite (sqlite3) | Embedded, file-based database; no server required |
| Matplotlib | Chart rendering, embedded into Tkinter via `FigureCanvasTkAgg` |
| csv (standard library) | Task-list export |

The only third-party dependency is Matplotlib (listed in
`requirements.txt`). Everything else ships with Python, which keeps the
project easy to install and run on any machine.

## Chapter 3: System Architecture

The application is split into four layers. Each layer depends only on the
layer directly below it:

```
  GUI layer        gui/app.py + gui/*_tab.py   (windows and tabs)
      |            reaches shared resources through the controller
      v
  Reporting layer  reports.py                  (summaries, charts, exports)
      |            reads data only via DatabaseManager
      v
  Persistence      database.py                 (all SQL lives here)
      |            returns model objects, never raw rows
      v
  Domain models    model.py                    (TeamMember, Task, Project)
```

Three rules keep the layers clean:

- **Nothing skips a layer.** Tabs never write SQL and never import each
  other. They reach shared state through the controller (`gui/app.py`),
  which owns the single `DatabaseManager` and `ReportGenerator`.
- **The database returns real objects.** Callers receive an `Engineer` or a
  `Task`, never a raw SQLite row, so model behaviour (validation, computed
  status) is always available.
- **Calculation lives below presentation.** The GUI displays values; it does
  not compute them. Status logic lives in the models, aggregation in the
  database and reporting layers.

A change made on one tab (a new member, a finished task) is pushed to every
other tab through `controller.refresh_all()`, so all screens always agree.

## Chapter 4: Database Design

The schema is three tables in one SQLite file (`data/epms.db`), created
automatically on first run:

```
team_members (id, name, email, role)
    role is CHECK-constrained to the three known role titles

projects (id, name, description, deadline, created_date)

tasks (id, title, project_id -> projects.id,
       member_id -> team_members.id (nullable),
       deadline, priority, description,
       progress CHECK(progress BETWEEN 0 AND 100))
```

Decisions taken:

- **Foreign keys are enforced** (`PRAGMA foreign_keys = ON`), so a task can
  never point at a project or member that does not exist.
- **`member_id` is nullable** because a task can be created before anyone is
  assigned to it, and because deleting a member unassigns (rather than
  deletes) their tasks.
- **Derived values are not stored.** A project's progress and task count,
  and a task's status, are computed live. Stored copies could drift out of
  date; computed ones cannot.
- **Dates are stored as ISO text** (`YYYY-MM-DD`), the conventional SQLite
  approach, and converted back to `date` objects by the row factories.

<!-- SECTION:A -->
## Chapter 5: model.py - The Domain Models

**What it handles:** the "things" the application manages, with no knowledge
of the database or the GUI.

**How the code works:**

- `TaskPriority` is an `Enum` with four levels (Low, Medium, High,
  Critical). The rest of the code refers to `TaskPriority.HIGH.value`
  instead of loose strings, so a typo cannot invent a fifth priority.
- `TeamMember` is an abstract base class representing any person on the
  team. It declares two abstract methods every role must implement:
  `get_role()` (the role title) and `max_capacity()` (how many active tasks
  that role can comfortably carry). It also implements shared behaviour:
  `describe()`, `to_dict()`, and validated `name` / `email` properties.
  The setters reject empty names and malformed emails, so an invalid member
  object can never exist anywhere in the program.
- `Engineer`, `ProjectManager`, and `QAEngineer` are small concrete
  subclasses. Each supplies only its role title and capacity (5, 8, and 6
  respectively). The Project Manager's higher number reflects that their
  tasks are typically oversight work rather than deep-focus work.
- `Task` is a dataclass holding title, project, deadline, optional assignee,
  priority, description, and progress. Its computed properties carry the
  business logic: `is_complete` (progress at 100), `days_remaining`
  (deadline minus today), and `status`, which resolves to one of
  `Completed`, `Overdue`, `Due Soon` (three days or less), or
  `In Progress`. The whole application reads `task.status` instead of
  re-deriving the rules.
- `Project` is a dataclass whose `progress` and `task_count` fields are
  filled in from outside by the database layer, aggregated from the
  project's real tasks. Its own `status` property adds a `Not Started`
  state for projects with no tasks and uses a wider seven-day
  `Due Soon` window.

**Decisions taken:**

- Roles are classes rather than a role string on one Member class, because
  behaviour (capacity) differs per role. This is what makes the capacity
  check polymorphic instead of a chain of if-statements.
- Validation lives in the model setters, not in the GUI, so every entry
  point gets the same rules for free.
- Status is computed, never stored, so it can never disagree with the
  progress and deadline it derives from.

## Chapter 6: database.py - The Persistence Layer

**What it handles:** every read and write to SQLite. No other module
contains SQL.

**How the code works:**

- `DatabaseManager` is a **singleton**: `__new__` returns the same instance
  every time, and an `_initialised` guard stops `__init__` from re-running.
  The whole app therefore shares one connection, opened with
  `PRAGMA foreign_keys = ON` and a `sqlite3.Row` row factory.
- `_create_tables()` runs an idempotent `CREATE TABLE IF NOT EXISTS` script
  on startup, so a fresh machine needs no setup step.
- `ROLE_CLASSES` maps the role string stored in the database back to the
  correct class. `_row_to_member()` uses it to rebuild a real `Engineer` or
  `QAEngineer` object from a plain row, which is what lets polymorphism
  survive a round trip through the database.
- Member methods: `add_member`, `get_members`, `delete_member`, and
  `active_task_count` (unfinished tasks a member currently carries, used by
  the overload warnings).
- Project methods: `add_project`, `get_projects`, `get_project`, and
  `delete_project`. `_row_to_project()` runs a `COUNT` / `AVG` query over
  the project's tasks to fill in the live `progress` and `task_count`.
- Task methods: `add_task`, `update_task_progress` (range-checked),
  `reassign_task`, `get_tasks` (with optional project and member filters
  built safely with placeholders), and `delete_task`.

**Decisions taken:**

- **Singleton connection** rather than opening connections ad hoc: one
  source of truth, no locking surprises, trivial cleanup on exit.
- **Deleting a member unassigns their tasks instead of deleting them.**
  Removing a person should not silently erase task history; the work items
  remain and can be reassigned.
- **Deleting a project deletes its tasks**, because a task cannot exist
  without its project. The GUI warns the user before doing this.
- **Every query uses parameter placeholders**, never string formatting, so
  user input cannot inject SQL.

## Chapter 7: reports.py - The Reporting Layer

**What it handles:** turning raw data into summaries, Matplotlib figures,
and export files. No aggregation or chart-building leaks into the GUI.

**How the code works:**

- `STATUS_COLORS` is the single place a status maps to a colour (green for
  Completed, blue for In Progress, yellow for Due Soon, red for Overdue,
  grey for Not Started). The charts read it, so a colour means the same
  thing on every screen.
- Summary methods do the counting and grouping: `task_status_breakdown`,
  `project_status_breakdown`, `team_workload` (active tasks per member),
  `upcoming_deadlines(days)` (unfinished tasks due within the window,
  sorted soonest first), `overdue_tasks`, and `project_progress_summary`.
- Chart methods (`figure_task_status_pie`, `figure_team_workload_bar`,
  `figure_project_progress_bar`) each return a Matplotlib `Figure`. Every
  figure is created with `constrained_layout=True` and handles the
  empty-database case by drawing a friendly message instead of an empty
  chart. The workload bar forces integer ticks (no fractional tasks) and
  labels each bar; the progress bar leaves headroom past 100 percent so the
  labels never touch the edge.
- Export methods: `export_csv` writes the full task list with project and
  assignee names resolved, and `export_text_report` writes a plain-text
  status summary with overdue and due-soon sections.

**Decisions taken:**

- The module sets the headless **Agg backend** as its default, so reports
  can be generated in scripts and tests without a display; the GUI supplies
  its own Tk canvas when embedding.
- `constrained_layout` replaced one-shot `tight_layout()` calls during
  development, because the layout must recompute when the GUI stretches the
  canvas to fill its frame (see Chapter 16).
- Charts return `Figure` objects rather than drawing to the screen, keeping
  the reporting layer completely independent of Tkinter.


<!-- SECTION:C -->
<!-- SECTION:D -->
