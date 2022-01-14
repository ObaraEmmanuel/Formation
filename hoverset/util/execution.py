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
import errno
import os
import sys
import importlib.util
import pathlib
from hoverset.platform import platform_is, WINDOWS, MAC

if platform_is(WINDOWS):
    import ctypes
    from ctypes import POINTER, c_ulong, c_char_p, c_int, c_void_p
    from ctypes.wintypes import HANDLE, BOOL, DWORD, HWND, HINSTANCE, HKEY
    from ctypes import windll
    import subprocess
else:
    try:
        from shlex import quote
    except ImportError:
        from pipes import quote


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

    def __init__(self, undo, redo, **kwargs):
        """
        Initialize the action object with the undo and redo callbacks
        :param undo: The undo callback
        :param redo: The redo callback
        """
        self._undo = undo
        self._redo = redo
        self._data = kwargs.get("data", {})
        self.key = kwargs.get("key", None)

    def undo(self):
        self._undo(self._data)

    def redo(self):
        self._redo(self._data)

    def update_redo(self, redo):
        self._redo = redo

    def update(self, data):
        self._data.update(data)


# Copyright (C) 2018 Barney Gale
# Core elevation code adapted from https://github.com/barneygale/elevate

# ----------------------------------------------------------------------

def _elevate_posix():
    if os.getuid() == 0:
        return

    working_dir = os.getcwd()
    args = [sys.executable] + sys.argv
    commands = []

    def quote_shell(a):
        return " ".join(quote(arg) for arg in a)

    def quote_applescript(string):
        charmap = {
            "\n": "\\n",
            "\r": "\\r",
            "\t": "\\t",
            "\"": "\\\"",
            "\\": "\\\\",
        }
        return '"%s"' % "".join(charmap.get(char, char) for char in string)

    if platform_is(MAC):
        commands.append([
            "osascript",
            "-e",
            "do shell script %s "
            "with administrator privileges "
            "without altering line endings"
            % quote_applescript(quote_shell(args))])

    elif os.environ.get("DISPLAY"):
        commands.append(["pkexec"] + args)
        commands.append(["gksudo"] + args)
        commands.append(["kdesudo"] + args)

    commands.append(["sudo"] + args)

    for args in commands:
        try:
            os.execlp(args[0], *args)
            # restore working directory which may be changed in certain systems
            if working_dir != os.getcwd():
                os.chdir(working_dir)
            # we are confident process has been elevated
            break
        except OSError as e:
            if e.errno != errno.ENOENT or args[0] == "sudo":
                sys.exit(1)


def _elevate_win(args=None):
    if windll.shell32.IsUserAnAdmin() and args is None:
        return
    # Constant definitions

    args = args.split(" ") if args is not None else sys.argv

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    SEE_MASK_NO_CONSOLE = 0x00008000

    class ShellExecuteInfo(ctypes.Structure):
        _fields_ = [
            ('cbSize', DWORD),
            ('fMask', c_ulong),
            ('hwnd', HWND),
            ('lpVerb', c_char_p),
            ('lpFile', c_char_p),
            ('lpParameters', c_char_p),
            ('lpDirectory', c_char_p),
            ('nShow', c_int),
            ('hInstApp', HINSTANCE),
            ('lpIDList', c_void_p),
            ('lpClass', c_char_p),
            ('hKeyClass', HKEY),
            ('dwHotKey', DWORD),
            ('hIcon', HANDLE),
            ('hProcess', HANDLE)]

        def __init__(self, **kw):
            super(ShellExecuteInfo, self).__init__()
            self.cbSize = ctypes.sizeof(self)
            for field_name, field_value in kw.items():
                setattr(self, field_name, field_value)

    PShellExecuteInfo = POINTER(ShellExecuteInfo)

    # Function definitions

    ShellExecuteEx = windll.shell32.ShellExecuteExA
    ShellExecuteEx.argtypes = (PShellExecuteInfo,)
    ShellExecuteEx.restype = BOOL

    WaitForSingleObject = windll.kernel32.WaitForSingleObject
    WaitForSingleObject.argtypes = (HANDLE, DWORD)
    WaitForSingleObject.restype = DWORD

    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = (HANDLE,)
    CloseHandle.restype = BOOL

    params = ShellExecuteInfo(
        fMask=SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE,
        hwnd=None,
        lpVerb=b'runas',
        lpFile=args[0].encode('cp1252'),
        lpParameters=subprocess.list2cmdline(args[1:]).encode('cp1252'),
        nShow=0)

    if not ShellExecuteEx(ctypes.byref(params)):
        sys.exit(1)

    handle = params.hProcess
    ret = DWORD()
    WaitForSingleObject(handle, -1)

    if windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(ret)) == 0:
        sys.exit(1)

    CloseHandle(handle)
    sys.exit(ret.value)


def elevate(args=None):
    """
    Runs the current process with root privileges. In posix systems, the current
    process is swapped while in Windows UAC creates a new process and the return
    code of the spawned process is chained back to the process that initiated
    the elevation. In case of elevation failures the process will terminate
    with a non zero exit code

    :param args: A list of commandline arguments to be used in creating the
        command to be run directly in elevated mode. If not provided current
        process is elevated instead. Only available in windows.
    """
    if platform_is(WINDOWS):
        _elevate_win(args)
    else:
        _elevate_posix()


def is_admin():
    """
    Returns ``True`` if current process is running in elevated mode otherwise
    ``False`` is returned
    """
    if platform_is(WINDOWS):
        return windll.shell32.IsUserAnAdmin()
    return os.getuid() == 0

# ----------------------------------------------------------------------


def import_path(path):
    """
    Import/Re-import python module from path
    """
    path = pathlib.Path(path).resolve()
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    if str(path.parent) not in sys.path:
        sys.path.append(str(path.parent))
    spec.loader.exec_module(module)
    return module
