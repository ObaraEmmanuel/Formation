"""
Provides functions for global image access and processing by hoverset apps
"""

# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import shelve
import functools
from PIL import Image, ImageTk

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
    with shelve.open("../hoverset/data/files/image") as image_base:
        if image_base.get(identifier):
            image = image_base.get(identifier)
        else:
            image = image_base.get("default")
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
