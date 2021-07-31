"""
Variable management for the studio. Creates and manages variables making them available
for widgets with variable and text-variable properties
"""
# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #
import functools
import tkinter as tk

import studio.ui.editors as editors
from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import ScrolledFrame, Button, MenuButton, Frame, Label
from studio.feature._base import BaseFeature
from studio.lib.variables import VariableItem, VariableManager


class VariablePane(BaseFeature):
    name = "Variablepane"
    icon = "text"

    _defaults = {
        **BaseFeature._defaults,
        "side": "right"
    }

    _definitions = {
        "name": {
            "name": "name",
            "type": "text",
        }
    }

    def __init__(self, master, studio=None, **cnf):
        super().__init__(master, studio, **cnf)
        f = Frame(self, **self.style.surface)
        f.pack(side="top", fill="both", expand=True, pady=4)
        f.pack_propagate(0)

        self._variable_pane = ScrolledFrame(f, width=150)
        self._variable_pane.place(x=0, y=0, relwidth=0.4, relheight=1)

        self._detail_pane = ScrolledFrame(f, width=150)
        self._detail_pane.place(relx=0.4, y=0, relwidth=0.6, relheight=1, x=15, width=-20)

        self._search_btn = Button(self._header, image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)
        self._add = MenuButton(self._header, **self.style.button)
        self._add.configure(image=get_icon_image("add", 15, 15))
        self._add.pack(side="right")
        self._delete_btn = Button(self._header, image=get_icon_image("delete", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._delete_btn.pack(side="right")
        self._delete_btn.on_click(self._delete)
        self._var_types_menu = self.make_menu(
            self._get_add_menu(),
            self._add, title="Add variable")
        self._var_types_menu.configure(tearoff=True)
        self._add.config(menu=self._var_types_menu)
        self._selected = None
        self._links = {}
        self._overlay = Label(f, **self.style.text_passive, text="Add variables", compound="top")
        self._overlay.configure(image=get_icon_image("add", 25, 25))
        self._show_overlay(True)
        self._editors = []

    def start_search(self, *_):
        if self.variables:
            super().start_search()
            self._variable_pane.scroll_to_start()

    def on_search_query(self, query):
        matches = []
        self._variable_pane.clear_children()
        for item in self.variables:
            if query in item.name:
                self._show(item)
                matches.append(item)

        if not matches:
            self._show_overlay(True, text="No matches found", image=get_icon_image("search", 25, 25))
        else:
            self.select(matches[0])
            self._show_overlay(False)

    def on_search_clear(self):
        self.on_search_query("")
        self._show_overlay(False)
        super().on_search_clear()

    def _get_add_menu(self):
        _types = VariableItem._types
        return [(
            tk.COMMAND,
            _types[i].get("name"),
            get_icon_image(_types[i].get("icon"), 14, 14),
            functools.partial(self.add_var, i), {}
        ) for i in _types]

    def create_menu(self):
        return (
            ("cascade", "Add", get_icon_image("add", 14, 14), None, {"menu": self._get_add_menu()}),
            ("command", "Delete", get_icon_image("delete", 14, 14), self._delete, {}),
            ("command", "Search", get_icon_image("search", 14, 14), self.start_search, {}),
        )

    def _show_overlay(self, flag=True, **kwargs):
        if flag:
            self._overlay.lift()
            self._overlay.configure(**kwargs)
            self._overlay.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self._overlay.place_forget()

    def add_var(self, var_type, **kw):
        var = var_type(self.studio)
        item_count = len(list(filter(lambda x: x.var_type == var_type, self.variables))) + 1
        name = kw.get('name', f"{var_type.__name__}_{item_count}")
        value = kw.get('value')
        item = VariableItem(self._variable_pane.body, var, name)
        item.bind("<Button-1>", lambda e: self.select(item))
        if value is not None:
            item.set(value)
        VariableManager.add(item)
        self._show(item)
        self._show_overlay(False)
        self.select(item)

    def delete_var(self, var):
        self._hide(var)
        VariableManager.remove(var)

    def _delete(self, *_):
        if self._selected:
            self.delete_var(self._selected)
        if self.variables:
            self.select(self.variables[0])
        else:
            self._show_overlay(True)

    def clear_variables(self):
        # the list is likely to change during iteration, create local copy
        variables = list(self.variables)
        for var in variables:
            self.delete_var(var)
        self._show_overlay(True)

    @property
    def variables(self):
        return VariableManager.variables

    def select(self, item):
        if item == self._selected:
            return
        item.select()
        if self._selected:
            self._selected.deselect()
        self._selected = item
        self._detail_for(item)

    def _show(self, item):
        item.pack(side="top", fill="x")

    def _hide(self, item):
        item.pack_forget()

    def _detail_for(self, variable):
        self._detail_pane.clear_children()
        Label(self._detail_pane.body, **self.style.text_passive,
              text="Type", anchor="w").pack(fill="x", side="top")
        Label(self._detail_pane.body, **self.style.text,
              text=variable.var_type_name, anchor="w").pack(fill="x", side="top")
        Label(self._detail_pane.body, **self.style.text_passive,
              text="Name", anchor="w").pack(fill="x", side="top")
        name = editors.get_editor(self._detail_pane.body, self._definitions["name"])
        name.pack(side="top", fill="x")
        name.set(variable.name)
        name.on_change(variable.set_name)
        Label(self._detail_pane.body, **self.style.text_passive,
              text="Value", anchor="w").pack(fill="x", side="top")
        value = editors.get_editor(self._detail_pane.body, variable.definition)
        value.set(variable.value)
        value.pack(side="top", fill="x")
        value.on_change(variable.set)

    def on_session_clear(self):
        self.clear_variables()
