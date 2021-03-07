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


def platform_is(platform) -> bool:
    """
    Check for the current operating system.
    :param platform: if platform is the current operating system or belongs to operating system belongs
    to the same family as platform True is returned and vice versa
    :return: boolean
    """
    return PLATFORM.startswith(platform)