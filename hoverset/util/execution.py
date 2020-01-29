"""
Contains functions and decorators for execution performance checkers and special execution
function wrappers
"""

# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import threading
import time
import functools


def timed(func):
    """
    Time the execution of a wrapped function and print the output
    :param func: Function to be wrapped
    :return: function to be wrapped
    """

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        start = time.perf_counter()
        func(*args, **kwargs)
        stop = time.perf_counter()
        print(f'{func.__name__} executed in {stop - start}s')

    return wrap


def as_thread(func):
    """
    Run the function in a separate thread
    :param func: the function to be executed in a separate thread
    :return: wrapped function
    """

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        threading.Thread(target=func, args=args, kwargs=kwargs).start()

    return wrap


class Action:
    """
    Action object for use in a undo redo system.
    """

    def __init__(self, undo, redo):
        """
        Initialize the action object with the undo and redo callbacks
        :param undo: The undo callback
        :param redo: The redo callback
        """
        self.undo = undo
        self.redo = redo
