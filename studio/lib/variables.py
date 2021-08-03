# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

"""
Contain variable definitions and runtime management of variable items in
use by the studio
"""
import logging
import tkinter as tk
from typing import Union

from hoverset.ui.widgets import Label
from hoverset.ui.icons import get_icon_image


class VariableItem(Label):
    _types = {
        tk.StringVar: {
            "name": "String",
            "icon": "text",
            "type": "text",
        },
        tk.BooleanVar: {
            "name": "Boolean",
            "icon": "checkbutton",
            "type": "boolean",
        },
        tk.IntVar: {
            "name": "Integer",
            "icon": "entry",
            "type": "number",
        },
        tk.DoubleVar: {
            "name": "Double",
            "icon": "math",
            "type": "number",
        }
    }
    supported_types = {".".join([i.__module__, i.__name__]): i for i in _types}

    def __init__(self, master, var, name=None):
        super().__init__(master)
        self.var = var
        self.var_handle: VariableItem = getattr(var, "handle", None)
        if self.var_handle:
            self.var_handle._slave_items.append(self)
            self._name = self.var_handle.name
        else:
            self.var.handle = self
            self._name = name
        self._slave_items = []
        self.configure(**self.style.text, text=self._with_padding(self._name),
                       image=get_icon_image(self.icon, 15, 15),
                       compound="left",
                       anchor="w")

    def _broadcast(self, func, *args, **kwargs):
        items = list(self._slave_items)
        for slave in items:
            try:
                getattr(slave, func)(*args, **kwargs)
            except AttributeError:
                logging.error(f"slave {slave} has no procedure {func}")
            except Exception as e:
                logging.error(e)

    def _with_padding(self, text):
        return f"   {text}"

    @property
    def value(self):
        return self.var.get()

    @property
    def name(self):
        return self._name

    def set_name(self, value):
        self._name = value
        self.config(text=self._with_padding(value))
        self._broadcast("set_name", value)

    def set(self, value):
        self.var.set(value)
        self._broadcast("set", value)

    @property
    def definition(self):
        return self._types.get(self.var.__class__)

    @property
    def icon(self):
        return self._types.get(self.var.__class__).get("icon")

    @property
    def var_type(self):
        return self.var.__class__

    @property
    def var_type_name(self):
        return self.var.__class__.__name__

    def select(self):
        self.configure(**self.style.hover)

    def deselect(self):
        self.configure(**self.style.surface)

    def destroy(self):
        if self.var_handle:
            self.var_handle._slave_items.remove(self)
        super().destroy()

    def __repr__(self):
        return self._name

    def __str__(self):
        return self._name


class VariableManager:
    variables = []
    editors = []

    @classmethod
    def add(cls, item):
        cls.variables.append(item)
        cls._broadcast("on_var_add", item.var)

    @classmethod
    def clear(cls):
        cls.variables.clear()

    @classmethod
    def remove(cls, item):
        if item in cls.variables:
            cls.variables.remove(item)
            cls._broadcast("on_var_delete", item.var)

    @classmethod
    def remove_editor(cls, editor):
        if editor in cls.editors:
            cls.editors.remove(editor)

    @classmethod
    def _broadcast(cls, func, *args, **kwargs):
        for editor in cls.editors:
            getattr(editor, func)(*args, **kwargs)

    @classmethod
    def lookup(cls, name) -> Union[VariableItem, str]:
        name = str(name)  # Sometimes name is a TclObj and we need it as a string for this to work
        search = list(filter(
            lambda x: name in (x.var._name, x.name),
            cls.variables
        ))
        if search:
            return search[0]
        return ''
