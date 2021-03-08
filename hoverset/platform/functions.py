"""
Definitions for functions that require additional tweaking to provide cross platform behaviour
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.platform import platform_is, WINDOWS, MAC


def image_grab(bbox=None, childprocess=None, backend=None):
    if platform_is(WINDOWS, MAC):
        from PIL import ImageGrab
        return ImageGrab.grab(bbox)
    else:
        # only import pyscreenshot if not on windows
        import pyscreenshot  # noqa
        return pyscreenshot.grab(bbox, childprocess, backend)
