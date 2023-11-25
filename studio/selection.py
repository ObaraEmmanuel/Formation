# ======================================================================= #
# Copyright (C) 2023 Hoverset Group.                                      #
# ======================================================================= #

from __future__ import annotations
from studio.lib.pseudo import PseudoWidget


class Selection:

    def __init__(self, widget):
        self.widget = widget
        self.widgets: list[PseudoWidget] = []
        self._reduced = []

    def set(self, widgets: list[PseudoWidget] | PseudoWidget):
        if isinstance(widgets, PseudoWidget):
            widgets = [widgets]
        if self.widgets == widgets:
            return
        self.widgets = list(widgets)
        self._on_change()

    def add(self, widget):
        if widget in self.widgets:
            return
        self.widgets.append(widget)
        self._on_change()

    def remove(self, widget):
        if widget not in self.widgets:
            return
        self.widgets.remove(widget)
        self._on_change()

    def clear(self):
        if not self.widgets:
            return
        self.widgets.clear()
        self._on_change()

    def toggle(self, widget):
        if widget in self.widgets:
            self.remove(widget)
        else:
            self.add(widget)

    def _on_change(self):
        self.widget.event_generate("<<SelectionChanged>>")
        self._reduce_hierarchy()

    def _reduce_hierarchy(self):
        self._reduced = []
        selected = set(self.widgets)

        for widget in self.widgets:
            current = widget.layout

            while current:
                if current in selected:
                    break
                current = current.layout
            else:
                self._reduced.append(widget)
        return self._reduced

    def compact(self):
        return self._reduced

    def is_single(self) -> bool:
        return len(self.widgets) == 1

    def is_same_type(self) -> bool:
        if not self.widgets:
            return False
        return all(isinstance(w, type(self.widgets[0])) for w in self.widgets)

    def is_same_parent(self) -> bool:
        if not self.widgets:
            return False
        return all(w.layout == self.widgets[0].layout for w in self.widgets)

    def siblings(self, widget):
        if not self.widgets:
            return []
        return [w for w in self.widgets if w.layout == widget.layout]

    def __iter__(self):
        return iter(self.widgets)

    def __len__(self):
        return len(self.widgets)

    def __getitem__(self, index):
        return self.widgets[index]

    def __contains__(self, item):
        return item in self.widgets

    def __str__(self):
        return str(self.widgets)

    def __repr__(self):
        return repr(self.widgets)

    def __bool__(self):
        return bool(self.widgets)

    def __eq__(self, other):
        if isinstance(other, Selection):
            return self.widgets == other.widgets
        return self.widgets == other

    def __ne__(self, other):
        if isinstance(other, Selection):
            return self.widgets != other.widgets
        return self.widgets != other
    