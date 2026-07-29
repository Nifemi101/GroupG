"""
gui/base.py
===========
Abstract base class shared by every screen ("tab") in the application.

Identical role to the finance tracker's BaseTab: an ABC that forces every
concrete tab (Dashboard, Projects, Team, Tasks, Reports) to implement
build_ui() and refresh(). The main window then calls tab.refresh() on
whichever tab is active without needing to know which concrete subclass
it's dealing with -- Abstraction + Inheritance enabling Polymorphism.
"""

from abc import ABC, abstractmethod
from tkinter import ttk


class BaseTab(ttk.Frame, ABC):
    """Common parent for every notebook page in the application."""

    def __init__(self, parent, controller):
        super().__init__(parent, padding=15)
        # `controller` is the main app window; it exposes shared resources
        # (db, reports, refresh_all()) to every tab.
        self.controller = controller
        self.build_ui()

    @abstractmethod
    def build_ui(self) -> None:
        """Construct and lay out every widget this tab needs."""
        raise NotImplementedError

    @abstractmethod
    def refresh(self) -> None:
        """Reload this tab's on-screen data from the database."""
        raise NotImplementedError