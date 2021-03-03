"""
Common unicode icons used in Hoverset
"""
from hoverset.data.images import get_tk_image


def get_icon_image(identifier: str, width=25, height=25, **kwargs):
    return get_tk_image(identifier, width, height, **kwargs)
