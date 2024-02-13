# ======================================================================= #
# Copyright (C) 2024 Hoverset Group.                                      #
# ======================================================================= #

from __future__ import annotations

import tkinter
from studio.selection import Selection


class DebugSelection(Selection):

    def __init__(self, widget):
        super().__init__(widget)
        self.widgets: list[tkinter.Widget] = []

    def set(self, widgets: list[tkinter.Widget] | tkinter.Widget):
        if isinstance(widgets, tkinter.Widget):
            widgets = [widgets]
        if self.widgets == widgets:
            return
        self.widgets = list(widgets)
        self._on_change()

    def _reduce_hierarchy(self):
        pass

    def is_same_parent(self) -> bool:
        if not self.widgets:
            return False
        return all(w.winfo_parent() == self.widgets[0].winfo_parent() for w in self.widgets)

    def siblings(self, widget):
        if not self.widgets:
            return []
        return [w for w in self.widgets if w.winfo_parent() == widget.winfo_parent()]

