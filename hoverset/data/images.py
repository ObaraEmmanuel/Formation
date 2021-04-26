"""
Provides functions for global image access and processing by hoverset apps
"""

# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import functools
import itertools
import os
import shelve
import math

from hoverset.data.utils import get_resource_path
from hoverset.util.color import to_rgb, luminosity

from PIL import Image, ImageTk

# raw default image resources
_primary_location = get_resource_path('hoverset.data', "image")
# path to theme recolored and cached image resources
_secondary_location = _primary_location


def set_image_resource_path(path):
    """
    Set the path at which to obtain image and icon resources at the start of the application

    :param path: a valid path to a shelve resource without necessarily an extension
    :return: None
    """
    global _secondary_location
    if os.path.exists(os.path.dirname(path)):
        _secondary_location = path
    else:
        raise FileNotFoundError("Image shelve {} path does not exist", path)


def _recolor(image, color):
    color = to_rgb(color) if isinstance(color, str) else color
    # expand to RGBA color
    color = (*color, 255)
    pix = image.load()

    for x in range(image.size[0]):
        for y in range(image.size[1]):
            if luminosity(pix[x, y]) > 65:
                pix[x, y] = color
            else:
                pix[x, y] = (0, 0, 0, 0)

    return image


# We want to enable memoization to reduce the number of times we read the image database
# An image can be accessed multiple times in the application lifetime hence a cache can improve performance greatly
@functools.lru_cache()
def get_image(identifier: str, width=25, height=25, **kwargs):
    """
    Fetches a PIL image object with a given dimension from the image database.
    WARNING, if the size required is greater than the size of the image
    in the database, the image will not be scaled upwards.

    :param width: expected image width default is 25 pixels
    :param height: expected image height default is 25 pixels
    :param identifier: A string representing the key of the image in the database
    :return: PIL image
    """
    color = kwargs.get("color")
    image: Image
    loc = _secondary_location
    if color:
        loc = _primary_location
    with shelve.open(loc) as image_base:
        if image_base.get(identifier):
            image = image_base.get(identifier)
        elif image_base.get("_" + identifier):
            # these are transformation free images
            image = image_base.get("_" + identifier)
        else:
            image = image_base.get("default")
    if image is None:
        raise FileNotFoundError(
            "Incorrect image shelve path specified, use set_image_resource_path function to set the correct path!"
        )
    # Resize the image to required size
    if color:
        image = _recolor(image, color)
    image.thumbnail((width, height), Image.ANTIALIAS)
    return image


def get_tk_image(identifier: str, width=25, height=25, **kwargs):
    """
    Fetch a tkinter compatible image from the image database.
    It's a wrapper around the get_image function

    :param width: expected image width default is 25 pixels
    :param height: expected image height default is 25 pixels
    :param identifier: A string representing the key of the image in the database
    :return: A tkinter compatible image
    """
    return ImageTk.PhotoImage(image=get_image(identifier, width, height, **kwargs))


def load_image(path, **kwargs):
    image = Image.open(path)
    width = kwargs.get("width", image.width)
    height = kwargs.get("height", image.height)
    if (width, height) != image.size:
        image.thumbnail((width, height))
    return image


def get_frames(image):
    # Get all frames present in an image
    frames = [to_tk_image(image)]
    try:
        while True:
            image.seek(image.tell() + 1)
            frames.append(to_tk_image(image))
    except EOFError:
        pass
    return frames


def load_image_to_widget(widget, image, prop):
    # cancel any animate cycles present
    if hasattr(widget, '_animate_cycle'):
        widget.after_cancel(widget._animate_cycle)
    if not isinstance(image, Image.Image):
        # load non PIL image values
        widget.config(**{prop: image})
        # store a reference to shield from garbage collection
        setattr(widget, prop, image)
        return
    if not hasattr(image, "is_animated") or not image.is_animated:
        image = to_tk_image(image)
        widget.config(**{prop: image})
        # store a reference to shield from garbage collection
        setattr(widget, prop, image)
        return
    # Animate the image
    frames = get_frames(image)
    frame_count = len(frames)
    if len(frames) == 1:
        widget.config(**{prop: frames[0]})
        return

    # an infinite iterator to loop through the frames continuously
    cycle = itertools.cycle(frames)
    loop = image.info.get("loop", 0)
    loop = math.inf if loop == 0 else loop
    loop_count = 0

    def cycle_frames():
        nonlocal loop_count
        widget.config(**{prop: next(cycle)})
        loop_count += 1
        if loop_count // frame_count >= loop:
            return
        widget._animate_cycle = widget.after(image.info.get("duration", 100), cycle_frames)

    # begin animation
    cycle_frames()


def to_tk_image(image):
    return ImageTk.PhotoImage(image)


def load_tk_image(path, width=None, height=None):
    """
    Load image from file described by path and convert to a tkinter image
    :param height: integer representing height of image to be returned
    :param width: integer representing width of image to be returned
    :param path: Image file path
    :return: tkinter PhotoImage
    """
    image = Image.open(path)
    if width is not None and height is not None:
        image.thumbnail((width, height))
    return ImageTk.PhotoImage(image=image)
