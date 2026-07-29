"""
database.py
============
Persistence layer for the Engineering Project Management System.

Same DatabaseManager singleton + SQLite pattern as the finance tracker:
every other module reaches the database only through this class's
high-level methods (add_project, get_tasks, ...) and never writes SQL
directly. Three tables this time: team_members, projects, tasks.
"""

import sqlite3
from pathlib import Path
from datetime import date
from typing import List, Optional

from model import TeamMember, Engineer, ProjectManager, QAEngineer, Project, Task

DB_PATH = Path(__file__).resolve().parent / "data" / "epms.db"

# Maps the role string stored in the database back to the correct class --
# this is what lets get_members() hand back real Engineer/ProjectManager/
# QAEngineer objects instead of some generic "member" type.
ROLE_CLASSES = {
    "Engineer": Engineer,
    "Project Manager": ProjectManager,
    "QA Engineer": QAEngineer,
}


class DatabaseManager:
    """Singleton wrapper around the application's SQLite database."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Path = DB_PATH):
        if getattr(self, "_initialised", False):
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._initialised = True

    def _create_tables(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS team_members (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            email TEXT NOT NULL,
            role  TEXT NOT NULL CHECK(role IN ('Engineer','Project Manager','QA Engineer'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            description  TEXT,
            deadline     TEXT NOT NULL,
            created_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            project_id  INTEGER NOT NULL REFERENCES projects(id),
            member_id   INTEGER REFERENCES team_members(id),
            deadline    TEXT NOT NULL,
            priority    TEXT NOT NULL DEFAULT 'Medium',
            description TEXT,
            progress    INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100)
        );
        """)
        self.conn.commit()

    # ---------------------------------------------------------- team members --
    def add_member(self, member: TeamMember) -> int:
        cur = self.conn.execute(
            "INSERT INTO team_members (name, email, role) VALUES (?,?,?)",
            (member.name, member.email, member.get_role()),
        )
        self.conn.commit()
        member.id = cur.lastrowid
        return cur.lastrowid

    def get_members(self) -> List[TeamMember]:
        rows = self.conn.execute("SELECT * FROM team_members ORDER BY name").fetchall()
        return [self._row_to_member(r) for r in rows]

    @staticmethod
    def _row_to_member(row: sqlite3.Row) -> TeamMember:
        """Factory: turns a DB row back into the correct TeamMember subclass
        -- polymorphism re-entering the picture, same as _row_to_transaction
        did in the finance tracker."""
        cls = ROLE_CLASSES[row["role"]]
        return cls(row["name"], row["email"], row["id"])

    def delete_member(self, member_id: int) -> None:
        # Unassign (don't delete) any tasks this member was handling --
        # removing a person shouldn't silently wipe out their task history.
        self.conn.execute("UPDATE tasks SET member_id = NULL WHERE member_id = ?", (member_id,))
        self.conn.execute("DELETE FROM team_members WHERE id = ?", (member_id,))
        self.conn.commit()

    def active_task_count(self, member_id: int) -> int:
        """How many not-yet-complete tasks this member currently carries --
        used to warn against overloading someone past their max_capacity()."""
        return self.conn.execute(
            "SELECT COUNT(*) c FROM tasks WHERE member_id=? AND progress < 100",
            (member_id,),
        ).fetchone()["c"]

    # -------------------------------------------------------------- projects --
    def add_project(self, project: Project) -> int:
        cur = self.conn.execute(
            "INSERT INTO projects (name, description, deadline, created_date) VALUES (?,?,?,?)",
            (project.name, project.description, project.deadline.isoformat(),
             project.created_date.isoformat()),
        )
        self.conn.commit()
        project.project_id = cur.lastrowid
        return cur.lastrowid

    def get_projects(self) -> List[Project]:
        rows = self.conn.execute("SELECT * FROM projects ORDER BY deadline").fetchall()
        return [self._row_to_project(r) for r in rows]

    def get_project(self, project_id: int) -> Optional[Project]:
        row = self.conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return self._row_to_project(row) if row else None

    def _row_to_project(self, row: sqlite3.Row) -> Project:
        # Progress/task_count are never stored directly -- they're
        # calculated live from this project's real tasks, the same way
        # Budget.spent was calculated from real expense transactions.
        agg = self.conn.execute(
            "SELECT COUNT(*) n, COALESCE(AVG(progress), 0) p FROM tasks WHERE project_id=?",
            (row["id"],),
        ).fetchone()
        return Project(
            name=row["name"], description=row["description"] or "",
            deadline=date.fromisoformat(row["deadline"]), project_id=row["id"],
            created_date=date.fromisoformat(row["created_date"]),
            progress=round(agg["p"], 1), task_count=agg["n"],
        )

    def delete_project(self, project_id: int) -> None:
        self.conn.execute("DELETE FROM tasks WHERE project_id=?", (project_id,))
        self.conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
        self.conn.commit()

    # ----------------------------------------------------------------- tasks --
    def add_task(self, task: Task) -> int:
        cur = self.conn.execute(
            "INSERT INTO tasks (title, project_id, member_id, deadline, priority, description, progress) "
            "VALUES (?,?,?,?,?,?,?)",
            (task.title, task.project_id, task.member_id, task.deadline.isoformat(),
             task.priority, task.description, task.progress),
        )
        self.conn.commit()
        task.task_id = cur.lastrowid
        return cur.lastrowid

    def update_task_progress(self, task_id: int, progress: int) -> None:
        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100.")
        self.conn.execute("UPDATE tasks SET progress=? WHERE id=?", (progress, task_id))
        self.conn.commit()

    def reassign_task(self, task_id: int, member_id: Optional[int]) -> None:
        self.conn.execute("UPDATE tasks SET member_id=? WHERE id=?", (member_id, task_id))
        self.conn.commit()

    def get_tasks(self, project_id: Optional[int] = None,
                  member_id: Optional[int] = None) -> List[Task]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if project_id is not None:
            query += " AND project_id=?"
            params.append(project_id)
        if member_id is not None:
            query += " AND member_id=?"
            params.append(member_id)
        query += " ORDER BY deadline"
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_task(r) for r in rows]

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            title=row["title"], project_id=row["project_id"],
            deadline=date.fromisoformat(row["deadline"]), member_id=row["member_id"],
            priority=row["priority"], description=row["description"] or "",
            task_id=row["id"], progress=row["progress"],
        )

    def delete_task(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()