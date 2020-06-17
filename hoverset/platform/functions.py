"""
Definitions for functions that require additional tweaking to provide cross platform behaviour
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import pyscreenshot
from PIL import ImageGrab

from hoverset.platform import platform_is, WINDOWS, MAC


def image_grab(bbox=None, childprocess=None, backend=None):
    if platform_is(WINDOWS) or platform_is(MAC):
        return ImageGrab.grab(bbox)
    else:
        return pyscreenshot.grab(bbox, childprocess, backend)
