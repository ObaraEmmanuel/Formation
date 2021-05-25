# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #
"""
A store and manager for all application functions and routines
"""


class Routine:
    """
    Representation of an action available throughout the lifetime
    of a hoverset application

    * **key**: A uniques string value used to access the action
    * **desc**: Long description of what the action does
    * **group**: group to which the action belongs. Can be ``None``
    * **shortcut**: A :py:class:`hoverset.data.keymap.Key` representing
      shortcut that can invoke the action
    * **func**: The actual function the action invokes

    """
    def __init__(self, func, key, desc, group=None, shortcut=None):
        self.key = key
        self.desc = desc
        self.group = group
        self._func = func
        self.shortcut = shortcut

    @property
    def accelerator(self):
        """
        Label for the shortcut key that invokes the action

        :return: String representing the shortcut combination that invokes
          routine
        """
        # return the shortcut key combination for display
        if self.shortcut:
            return self.shortcut.label
        return ''

    def invoke(self, *args, **kwargs):
        return self._func(*args, **kwargs)


_all_actions = {}


def add(*routines):
    """
    Add routines

    :param routines: :py:class:`Routine` objects to be added
    """
    for routine in routines:
        _all_actions[routine.key] = routine


def get_routine(key):
    """
    Get a routine with given key

    :param key: String key for routine to be obtained
    :return: :py:class:`Routine` object with given key
    """
    return _all_actions.get(key)


get = get_routine  # Shorter method get


def remove(*routines):
    """
    Remove routines from global map

    :param routines: routines to be removed
    """
    for routine in routines:
        _all_actions[routine.key] = routine


def all_routines():
    """
    Get dictionary of all routines

    :return: A dictionary with string keys and :py:class`Routine` values
    """
    return _all_actions


def routine_from_shortcut(shortcut):
    """
    Get routine object with given shortcut

    :param shortcut: :py:class:`hoverset.data.keymap.Key` object
    :return: Routine object with given shortcut otherwise None
    """
    search = list(filter(lambda r: r.shortcut == shortcut, _all_actions.values()))
    if len(search) > 0:
        return search[0]
    return None
