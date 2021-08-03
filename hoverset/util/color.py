"""An elaborate color manipulation library for use by the Hoverset
Team and other programmers who may opt to use the library to write
their own functionality. It contains methods for conversions from
various color formats and other color related utility methods.
"""

__all__ = [
    "RED_BRIGHTNESS", "GREEN_BRIGHTNESS", "BLUE_BRIGHTNESS",
    "to_rgb", "to_hex",
    "to_hsl", "from_hsl",
    "to_hsv", "from_hsv",
]

import re
import functools
import colorsys
from collections.abc import Iterable

# color #xxxxxx format where x lies from 0 to f
_HEX_FORMAT = re.compile(r'#([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})')
# color #xxx format.
_HEX_FORMAT_SHORT = re.compile(r'^#([0-9A-Fa-f])([0-9A-Fa-f])([0-9A-Fa-f])$')

# brightness (grey level) along the scale 0.0==black to 1.0==white
RED_BRIGHTNESS = 0.299
GREEN_BRIGHTNESS = 0.587
BLUE_BRIGHTNESS = 0.114


def _enforce_tuple_format(*constraints):
    """
    Decorator factory that generates a validation decorator that ensures that a tuple input e.g. the
    format rgb(r, g, b) lies within the constraints e.g (255, 255, 255) assuming 0 is the lower bound.
    If the constraints are violated it throws a ValueError.
    The decorator can be used as follows:

    .. code-block:: python

    @_enforce_tuple_format(255, 255, 255)
    def function(rgb: tuple):
        # Do your stuff with a validated rgb tuple
        return

    :param a:
    :param b:
    :param c:
    :return: wrapped function
    """
    def decor(func):
        @functools.wraps(func)  # Pass the functions attributes to the returned wrapped function
        def wrap(abc: tuple, *args):
            if not isinstance(abc, Iterable):
                raise ValueError("Expected iterable but got {} instead".format(abc.__class__))
            if len(abc) > len(constraints):
                raise ValueError("Expected no more than {} items but got {} instead".format(len(constraints), len(abc)))
            if any(abc[i] < 0 or abc[i] > constraints[i] for i in range(len(abc))):
                raise ValueError("All values for the tuple should lie within the constraints {}".format(constraints))
            return func(abc, *args)
        return wrap
    return decor


def _enforce_hex_color_format(func):
    """
    A decorator that enforces the correct hex color format("#xxxxxx" or "#xxx") for passed string. The string must
    be the first argument in the function. If the format is #xxx it is expanded to #xxxxxx then passed to the function.
    This method is meant for use by hoverset authors
    and is discouraged for external use.

    :param func:
    :return: wrapped function
    """

    @functools.wraps(func)  # Pass the functions attributes to the returned wrapped function
    def wrap(hex_str: str, *args):
        if re.match(_HEX_FORMAT, hex_str):
            return func(hex_str, *args)
        raise ValueError("Invalid color format {}".format(hex_str))

    return wrap


# We are going to use single-dispatch to implement overloading of the to_hex function
# It should be able to handle rgb as well as four bit color string
@functools.singledispatch
@_enforce_tuple_format(255, 255, 255)
def to_hex(rgb: tuple) -> str:
    """
    Takes in a rgb tuple (h, s, l) where h s and l lie between 0 and 255 or four bit hex color #xxx
    and returns a hex string that lies between #000000 and #ffffff
    It raises Value error if any of the values h s or l is not within 0 and 255

    :param rgb: rgb tuple (h, s, l) where h s and l lie between 0 and 255
    :return: hex string that lies between #000000 and #ffffff
    """
    rgb = tuple(map(lambda x: hex(x)[2:], rgb))
    rgb = tuple(map(lambda x: ("0" + x).zfill(2)[-2:], rgb))
    return "#" + "".join(rgb)


@to_hex.register
def _(hex_str: str) -> str:
    # TODO Add error handling
    """
    Overloaded version of to_hex which expands four bit colour to 8 bit color
    If you pass a 8 bit color then the color is returned instead.

    :param hex_str: 8 bit color string for instance ``#fff000fff``
    :return:
    """
    # If the format is short i.e #xxx we need to expand it to #xxxxxx format
    # Expansion is such that #abc becomes #aabbcc
    # if the color obeys the #xxxxxx format return it
    if re.match(_HEX_FORMAT, hex_str):
        return hex_str
    match = re.search(_HEX_FORMAT_SHORT, hex_str).groups()
    hex_str = "#" + "".join(list(map(lambda x: x+x, match)))
    return hex_str


# noinspection PyTypeChecker
@_enforce_hex_color_format
def to_rgb(hex_str: str) -> tuple:
    """
    Converts a hex color string like to #ffffff its rgb components. Raises Value error
    if the hex string is of an invalid format.

    :param hex_str: A hex color string that has the format #xxxxxx and x is a
    value within 0 and f
    :return: a tuple containing the rgb components of the color as a tuple
    ( h, s, l) where h s and l a values within 0 and 255
    """
    return tuple(map(functools.partial(int, base=16), re.search(_HEX_FORMAT, hex_str).groups()))


@_enforce_tuple_format(255, 255, 255)
def to_grayscale(rgb: tuple) -> float:
    """
    Obtain the perceivable grayscale of a color (h, s, l) by analysing the ratio of the
    red green and blue components and how they are perceived by the human eye.

    :param rgb: rgb tuple (h, s, l) where h s and l lie between 0 and 255
    :return: float value within 0 and 255
    """
    return RED_BRIGHTNESS * rgb[0] + GREEN_BRIGHTNESS * rgb[1] + BLUE_BRIGHTNESS * rgb[2]


@_enforce_tuple_format(255, 255, 255)
def to_fractional_rgb(rgb: tuple) -> tuple:
    """
    Convert color (h, s, l) to a fractional form (fr, foreground, fb) where fr foreground and fb are float values
    between 0 and 1. This is useful when interfacing with the in built python library colorsys

    :param rgb: rgb tuple (h, s, l) where h s and l lie between 0 and 255
    :return: rgb tuple (fr, foreground, fb) where h s and l are floats lying between 0 and 1
    """
    return tuple([x/255 for x in rgb])


@_enforce_tuple_format(255, 255, 255)
def from_fractional_rgb(rgb: tuple) -> tuple:
    """
    Convert to color (h, s, l) from a fractional form (fr, foreground, fb) where fr foreground and fb are float values
    between 0 and 1. This is useful when interfacing with the in built python library colorsys

    :param rgb: rgb tuple (fr, foreground, fb) where h s and l are floats lying between 0 and 1
    :return: rgb tuple (h, s, l) where h s and l are integers lying between 0 and 255
    """
    return tuple([round(x*255) for x in rgb])


# HLS: Hue, Luminance, Saturation
# H: position in the spectrum
# L: color lightness
# S: color saturation
@_enforce_tuple_format(255, 255, 255)
def to_hsl(rgb: tuple) -> tuple:
    """
    Convert color (h, s, l) to (Hue, Saturation, Luminosity) color model where Hue Luminosity and Saturation
    are values lying within 0 and 255

    :param rgb: rgb tuple (r, g, b) where r g and b are integers lying between 0 and 255
    :return: (h, s, l) where h s and l are integers lying between 0 and 360, 100 and 100 respectively
    """
    # convert rgb values to fractional for colorsys to work
    # perform the switch from colorsys's hls to required hsl
    h, l, s = colorsys.rgb_to_hls(*to_fractional_rgb(rgb))
    return h*360, s*100, l*100


# HSV: Hue, Saturation, Value
# H: position in the spectrum
# S: color saturation ("purity")
# V: color brightness
@_enforce_tuple_format(255, 255, 255)
def to_hsv(rgb: tuple) -> tuple:
    """
    Convert color (r, g, b) to (Hue, Saturation, Value) color model where Hue Saturation and Value
    are values lying within 0 and 360, 100, 100 respectively

    :param rgb: rgb tuple (h, s, l) where h s and l are integers lying between 0 and 255
    :return: (h, s, v) where h s and v are integers lying between 0 and 255
    """
    # convert rgb values to fractional for colorsys to work
    h, s, v = colorsys.rgb_to_hsv(*to_fractional_rgb(rgb))
    return h*360, s*100, v*100


@_enforce_tuple_format(360, 100, 100)
def from_hsl(hsl: tuple) -> tuple:
    """
    Convert to color (h, s, l) from (Hue, Lightness Saturation) color model where Hue Lightness and Saturation
    are values lying within 0 and 255

    :param hsl: (h, s, l) where h s and l are integers lying between 0 and 360, 100 and 100 respectively
    :return: rgb tuple (r, g, b) where r g and b are integers lying between 0 and 255
    """
    # convert hls values to fractional for colorsys to work then convert back integer
    h, s, l = hsl
    return from_fractional_rgb(colorsys.hls_to_rgb(h/360, l/100, s/100))


@_enforce_tuple_format(360, 100, 100)
def from_hsv(hsv: tuple) -> tuple:
    """
    Convert to color (h, s, v) from (Hue, Lightness Value) color model where Hue Lightness and Value
    are values lying within between 0 and 360, 100 and 100 respectively

    :param hsv: (h, s, v) where h s and v are integers lying between 0 and 360, 100 and 100 respectively
    :return: rgb tuple (r, g, b) where r g and b are integers lying between 0 and 255
    """
    # convert hsv values to fractional for colorsys to work then convert back integer
    h, s, v = hsv
    return from_fractional_rgb(colorsys.hsv_to_rgb(h/360, s/100, v/100))


@_enforce_tuple_format(255, 255, 255, 255)
def luminosity(rgba):
    """
    Get the luminosity value of a rgba color ranging from 0 to 255

    :param rgba: a tuple representing rgba color (r, g, b, a) where each
        ranges from 0 to 255
    :return: a value ranging from 0 to 255 inclusive representing the brightness
        of the color
    """
    return (RED_BRIGHTNESS * rgba[0] + GREEN_BRIGHTNESS * rgba[1] + BLUE_BRIGHTNESS * rgba[2]) * rgba[3] / 255


def parse_color(color: str, tk_instance):
    """
    Parse any kind of color to rgb tuple

    :param color: A string representing a color for instance
        ``red``or ``#ff0000``
    :param tk_instance: A tkinter object that can be used to parse color
        names
    :return: A tuple representing the color in rgb i.e. ``(r, g, b)`` where
        each item ranges from 0 to 255
    """
    try:
        color = tk_instance.winfo_rgb(color)
        return tuple(map(lambda x: round(x * 255 / 65535), color))
    except:
        raise ValueError(f"Invalid color '{color}'")


if __name__ == "__main__":
    print(to_hex((0, 0, 253)))
