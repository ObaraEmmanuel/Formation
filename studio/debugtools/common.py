import logging
import os
import tkinter
from tkinter import ttk
from studio.lib import native, legacy
from studio.lib.properties import get_properties


def extract_base_class(widget):
    # we'll check the MRO
    # the first class is always itself
    classes = widget.__class__.mro()
    for c in classes:
        if c.__module__ in (ttk.__name__, tkinter.__name__):
            return c
    return None


def get_base_class(widget):
    return widget._class


def get_studio_equiv(widget):
    base = get_base_class(widget)
    if base is None:
        return

    if base.__module__ == tkinter.__name__:
        # we'll look in legacy
        widgets = legacy.widgets
    else:
        # check native
        widgets = native.widgets

    equiv = list(filter(lambda x: x.impl == base, widgets))
    if equiv:
        return equiv[0]
    # its probably a tix widget we cannot resolve
    return None


def run_on_main_thread(root, func, *args, **kwargs):
    # WARNING: Do not call this function on main thread
    # root should be the tk root where mainloop was invoked.
    class Sentinel:
        value = None
        error = None
        pass

    sentinel = Sentinel()
    # sentinel value to confirm if execution is complete on main thread
    sentinel.value = sentinel

    def wrapper():
        try:
            sentinel.value = func(*args, **kwargs)
        except Exception as e:
            sentinel.error = e

    # Run on main thread
    root.after(0, wrapper)
    # wait for value or error from main thread
    while True:
        if sentinel.value is not sentinel:
            return sentinel.value
        if sentinel.error:
            raise sentinel.error


def get_root_id(widget, hook=None):
    if hook and widget in hook.roots:
        return hook.roots.index(widget)
    root = widget.winfo_toplevel()
    while not isinstance(root, tkinter.Tk):
        root = root.master
        root = root.winfo_toplevel()
    if hook is None:
        return 0
    return hook.roots.index(root)


def get_resolved_properties(widget):
    base = get_studio_equiv(widget)
    if base is None:
        base = widget
    overrides = getattr(base, 'DEF_OVERRIDES', {})
    return get_properties(widget, overrides)


def get_logging_level():
    try:
        return int(os.environ.get("FORMATION_LOGLEVEL", logging.INFO))
    except ValueError:
        return logging.INFO
