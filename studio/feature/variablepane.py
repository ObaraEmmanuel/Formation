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
from studio.i18n import _


class VariablePane(BaseFeature):
    name = "Variablepane"
    display_name = _("Variables")
    icon = "text"

    _defaults = {
        **BaseFeature._defaults,
        "side": "right",
        "visible": False,
    }

    _definitions = {
        "name": {
            "name": "name",
            "type": "text",
        }
    }

    _empty_message = _("No variables added")

    def __init__(self, master, studio=None, **cnf):
        super().__init__(master, studio, **cnf)
        f = Frame(self, **self.style.surface)
        f.pack(side="top", fill="both", expand=True, pady=4)
        f.pack_propagate(0)

        self._variable_pane = ScrolledFrame(f, width=150)
        self._variable_pane.place(x=0, y=0, relwidth=0.4, relheight=1)

        self._detail_pane = ScrolledFrame(f, width=150)
        self._detail_pane.place(relx=0.4, y=0, relwidth=0.6, relheight=1, x=15, width=-20)

        Label(
            self._detail_pane.body, **self.style.text_passive,
            text=_("Type"), anchor="w"
        ).pack(side="top", fill="x")
        self.var_type_lbl = Label(
            self._detail_pane.body, **self.style.text, anchor="w"
        )
        self.var_type_lbl.pack(side="top", fill="x")
        Label(
            self._detail_pane.body, **self.style.text_passive,
            text=_("Name"), anchor="w"
        ).pack(side="top", fill="x")
        self.var_name = editors.get_editor(self._detail_pane.body, self._definitions["name"])
        self.var_name.pack(side="top", fill="x")
        Label(
            self._detail_pane.body, **self.style.text_passive,
            text=_("Value"), anchor="w"
        ).pack(fill="x", side="top")
        self._editors = {}
        self._editor = None

        self._search_btn = Button(self._header, image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)
        self._search_query = None

        self._add = MenuButton(self._header, **self.style.button)
        self._add.configure(image=get_icon_image("add", 15, 15))
        self._add.pack(side="right")
        self._delete_btn = Button(self._header, image=get_icon_image("delete", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._delete_btn.pack(side="right")
        self._delete_btn.on_click(self._delete)
        self._var_types_menu = self.make_menu(
            self._get_add_menu(),
            self._add, title=_("Add variable"))
        self._var_types_menu.configure(tearoff=True)
        self._add.config(menu=self._var_types_menu)
        self._selected = None
        self._links = {}
        self._overlay = Label(f, **self.style.text_passive, text=self._empty_message, compound="top")
        self._overlay.configure(image=get_icon_image("add", 25, 25))
        self._show_overlay(True)

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
            self._show_overlay(True, text=_("No matches found"), image=get_icon_image("search", 25, 25))
        else:
            self.select(matches[0])
            self._show_overlay(False)
        self._search_query = query

    def on_search_clear(self):
        self.on_search_query("")
        self._search_query = None
        # remove overlay if we have variables otherwise show it
        self._show_overlay(not self.variables)
        super().on_search_clear()

    def _get_add_menu(self):
        _types = VariableItem._types
        return [(
            tk.COMMAND,
            _types[i].get("name"),
            get_icon_image(_types[i].get("icon"), 18, 18),
            functools.partial(self.menu_add_var, i), {}
        ) for i in _types]

    def create_menu(self):
        return (
            ("cascade", _("Add"), get_icon_image("add", 18, 18), None, {"menu": self._get_add_menu()}),
            ("command", _("Delete"), get_icon_image("delete", 18, 18), self._delete, {}),
            ("command", _("Search"), get_icon_image("search", 18, 18), self.start_search, {}),
        )

    def _show_overlay(self, flag=True, **kwargs):
        if flag:
            kwargs["text"] = kwargs.get("text", self._empty_message)
            kwargs["image"] = kwargs.get("image", get_icon_image("add", 25, 25))
            self._overlay.lift()
            self._overlay.configure(**kwargs)
            self._overlay.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self._overlay.place_forget()

    def menu_add_var(self, var_type, **kw):
        item = self.add_var(var_type, **kw)
        self.select(item)

    def add_var(self, var_type, **kw):
        var = var_type(self.studio)
        item_count = len(list(filter(lambda x: x.var_type == var_type, self.variables))) + 1
        name = kw.get('name', f"{var_type.__name__}_{item_count}")
        value = kw.get('value')
        item = VariableItem(self._variable_pane.body, var, name)
        item.bind("<Button-1>", lambda e: self.select(item))
        if value is not None:
            item.set(value)

        self._show(item)
        self._show_overlay(False)
        if self._search_query is not None:
            # reapply search if any
            self.on_search_query(self._search_query)
        elif not self.variables:
            self.select(item)
        VariableManager.add(item)
        return item

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
        return VariableManager.variables()

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

    def _get_editor(self, variable):
        editor_type = variable.definition["type"]
        if not self._editors.get(editor_type):
            # we do not have that type of editor yet, create it
            self._editors[editor_type] = editors.get_editor(self._detail_pane.body, variable.definition)
        return self._editors[editor_type]

    def refresh(self):
        # redraw variables for current context
        self._variable_pane.body.clear_children()
        has_selection = False
        if not self.variables:
            self._show_overlay(True)
        else:
            self._show_overlay(False)
        for item in self.variables:
            self._show(item)
            if not has_selection:
                self.select(item)
                has_selection = True
        # reapply search query if any
        if self._search_query is not None:
            self.on_search_query(self._search_query)

    def _detail_for(self, variable):
        _editor = self._get_editor(variable)
        if self._editor != _editor:
            # we need to change current editor completely
            if self._editor:
                self._editor.pack_forget()
            self._editor = _editor
        self._editor.set(variable.value)
        self._editor.pack(side="top", fill="x")
        self._editor.on_change(variable.set)

        self.var_name.set(variable.name)
        self.var_name.on_change(variable.set_name)
        self.var_type_lbl["text"] = variable.var_type_name

    def on_session_clear(self):
        self.clear_variables()

    def on_context_switch(self):
        VariableManager.set_context(self.studio.context)
        self.refresh()
