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


def platform_is(*platforms) -> bool:
    """
    Check for the current operating system.
    :param platforms: if any platform provided here is the current
    operating system `True` is returned else `False`

    :return: boolean
    """
    return any(PLATFORM.startswith(p) for p in platforms)
