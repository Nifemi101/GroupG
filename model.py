"""
model.py
========
Domain (business) models for the Engineering Project Management System.

Same OOP structure as the finance tracker, applied to a different domain:

* ABSTRACTION   -> TeamMember is an Abstract Base Class. It defines *what*
                   every team member must be able to do (get_role(),
                   max_capacity()) without saying *how* for any one role.
* INHERITANCE   -> Engineer, ProjectManager, and QAEngineer all inherit
                   shared behaviour (name/email validation, describe()) from
                   TeamMember.
* POLYMORPHISM  -> member.get_role() and member.max_capacity() behave
                   differently depending on which concrete role class the
                   object actually is.
* ENCAPSULATION -> Internal state (_name, _email, ...) is only reachable
                   through validated @property accessors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class TaskPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


# --------------------------------------------------------------------------- #
# ABSTRACTION: TeamMember defines the contract every role must follow
# --------------------------------------------------------------------------- #
class TeamMember(ABC):
    """Abstract base class representing any person on an engineering team."""

    def __init__(self, name: str, email: str, member_id: Optional[int] = None):
        self._id = member_id
        self.name = name            # routed through the setter -> validated
        self.email = email          # routed through the setter -> validated

    # ---------------- ENCAPSULATION: validated properties ----------------
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Name cannot be empty.")
        self._name = value.strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not value or "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Please enter a valid email address.")
        self._email = value.strip()

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value

    # ---------------- ABSTRACTION: subclasses MUST implement these -------
    @abstractmethod
    def get_role(self) -> str:
        """Return this member's role title, e.g. 'Engineer'."""
        raise NotImplementedError

    @abstractmethod
    def max_capacity(self) -> int:
        """Maximum number of active tasks this role can comfortably carry
        at once. Used to warn against overloading a team member when
        allocating new tasks."""
        raise NotImplementedError

    # ---------------- POLYMORPHISM: shared call, subclass-specific result --
    def describe(self) -> str:
        return f"{self.name} ({self.get_role()}) - {self.email}"

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "name": self._name,
            "email": self._email,
            "role": self.get_role(),
            "max_capacity": self.max_capacity(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._name}>"


class Engineer(TeamMember):
    """A hands-on engineer building the actual system."""

    def get_role(self) -> str:
        return "Engineer"

    def max_capacity(self) -> int:
        return 5


class ProjectManager(TeamMember):
    """Coordinates the project; can juggle more concurrent tasks since they
    are typically administrative/oversight tasks rather than deep-focus work."""

    def get_role(self) -> str:
        return "Project Manager"

    def max_capacity(self) -> int:
        return 8


class QAEngineer(TeamMember):
    """Tests and verifies work produced by Engineers."""

    def get_role(self) -> str:
        return "QA Engineer"

    def max_capacity(self) -> int:
        return 6


# --------------------------------------------------------------------------- #
# Task allocation & progress tracking
# --------------------------------------------------------------------------- #
@dataclass
class Task:
    """A single unit of work belonging to a project, optionally assigned to
    a team member. Progress and deadline together drive `status`, the same
    way Budget.status worked in the finance tracker -- one property, used
    everywhere the GUI needs to know "how is this doing?"."""
    title: str
    project_id: int
    deadline: date
    member_id: Optional[int] = None       # None = unassigned
    priority: str = TaskPriority.MEDIUM.value
    description: str = ""
    task_id: Optional[int] = None
    progress: int = 0                      # 0-100

    def update_progress(self, percent: int) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("Progress must be between 0 and 100.")
        self.progress = percent

    @property
    def is_complete(self) -> bool:
        return self.progress >= 100

    @property
    def days_remaining(self) -> int:
        return (self.deadline - date.today()).days

    @property
    def status(self) -> str:
        if self.is_complete:
            return "Completed"
        days = self.days_remaining
        if days < 0:
            return "Overdue"
        if days <= 3:
            return "Due Soon"
        return "In Progress"


# --------------------------------------------------------------------------- #
# Project registration
# --------------------------------------------------------------------------- #
@dataclass
class Project:
    """A project the engineering team is delivering. Progress and task_count
    are populated from outside (by DatabaseManager, aggregating this
    project's real tasks) rather than set directly -- the same pattern
    Budget used for `spent` in the finance tracker."""
    name: str
    description: str
    deadline: date
    project_id: Optional[int] = None
    created_date: date = field(default_factory=date.today)
    progress: float = 0.0      # average progress % across this project's tasks
    task_count: int = 0

    @property
    def days_remaining(self) -> int:
        return (self.deadline - date.today()).days

    @property
    def status(self) -> str:
        if self.task_count == 0:
            return "Not Started"
        if self.progress >= 100:
            return "Completed"
        if self.days_remaining < 0:
            return "Overdue"
        if self.days_remaining <= 7:
            return "Due Soon"
        return "In Progress"