# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #
"""
A store and manager for all application functions and routines
"""


class Routine:
    def __init__(self, func, key, desc, group=None, shortcut=None):
        self.key = key
        self.desc = desc
        self.group = group
        self._func = func
        self.shortcut = shortcut

    @property
    def accelerator(self):
        # return the shortcut key combination for display
        if self.shortcut:
            return self.shortcut.label
        return ''

    def invoke(self, *args, **kwargs):
        self._func(*args, **kwargs)


_all_actions = {}


def add(*routines):
    for routine in routines:
        _all_actions[routine.key] = routine


def get_routine(key):
    return _all_actions.get(key)


get = get_routine  # Shorter method get


def remove(*routines):
    for routine in routines:
        _all_actions[routine.key] = routine
