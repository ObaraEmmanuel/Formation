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

from PIL import Image, ImageTk

_image_locations = get_resource_path('hoverset.data', "image")


def set_image_resource_path(path):
    """
    Set the path at which to obtain image and icon resources at the start of the application
    :param path: a valid path to a shelve resource without necessarily an extension
    :return:
    """
    global _image_locations
    if os.path.exists(os.path.dirname(path)):
        _image_locations = path
    else:
        raise FileNotFoundError("Image shelve {} path does not exist", path)


# We want to enable memoization to reduce the number of times we read the image database
# An image can be accessed multiple times in the application lifetime hence a cache can improve performance greatly
@functools.lru_cache()
def get_image(identifier: str, width=25, height=25):
    """
    Fetches a PIL image object with a given dimension from the image database. WARNING, if the size required
    is greater than the size of the image in the database, the image will not be scaled upwards.
    :param width: expected image width default is 25 pixels
    :param height: expected image height default is 25 pixels
    :param identifier: A string representing the key of the image in the database
    :return: PIL image
    """
    image: Image
    with shelve.open(_image_locations) as image_base:
        if image_base.get(identifier):
            image = image_base.get(identifier)
        else:
            image = image_base.get("default")
    if image is None:
        raise FileNotFoundError(
            "Incorrect image shelve path specified, use set_image_resource_path function to set the correct path!"
        )
    # Resize the image to required size
    image.thumbnail((width, height), Image.ANTIALIAS)
    return image


def get_tk_image(identifier: str, width=25, height=25):
    """
    Fetch a tkinter compatible image from the image database. It's a wrapper around the get_image function
    :param width: expected image width default is 25 pixels
    :param height: expected image height default is 25 pixels
    :param identifier: A string representing the key of the image in the database
    :return: A tkinter compatible image
    """
    return ImageTk.PhotoImage(image=get_image(identifier, width, height))


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
    if not image.is_animated:
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
