import sys

PLATFORM = sys.platform

WINDOWS = 'win32'
LINUX = 'linux'
MAC = 'darwin'
CYGWIN = 'cygwin'
MSYS2 = 'msys'
OS2 = 'os2'
OS2EMX = 'os2emx'
RISCOS = 'riscos'
ATHEOS = 'atheos'
FREEBSD = 'freebsd'
OPENBSD = 'openbsd'

# windowing systems

X11 = 'x11'
AQUA = 'aqua'
WIN32 = 'win32'


def windowing_is(root, *window_sys):
    """
    Check for the current operating system.

    :param root: A tk widget to be used as reference
    :param window_sys: if any windowing system provided here is the current
    windowing  system `True` is returned else `False`

    :return: boolean
    """
    windowing = root.tk.call('tk', 'windowingsystem')
    return windowing in window_sys


def is_threaded_build(root):
    """
    Check whether the tk build in use supports threading.

    :param root: the tk widget to be used as reference

    :return: ``1`` if threading is supported ``0`` otherwise
    """
    return int(root.tk.eval("set tcl_platform(threaded)"))


def platform_is(*platforms) -> bool:
    """
    Check for the current operating system.

    :param platforms: if any platform provided here is the current
    operating system `True` is returned else `False`

    :return: boolean
    """
    return any(PLATFORM.startswith(p) for p in platforms)
