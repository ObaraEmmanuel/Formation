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


def get_resolved_properties(widget):
    base = get_studio_equiv(widget)
    overrides = getattr(base, 'DEF_OVERRIDES', {})
    return get_properties(widget, overrides)


def get_logging_level():
    try:
        return int(os.environ.get("FORMATION_LOGLEVEL", logging.INFO))
    except ValueError:
        return logging.INFO
