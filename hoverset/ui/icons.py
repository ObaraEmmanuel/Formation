"""
Common unicode icons used in Hoverset
"""
from hoverset.data.images import get_tk_image
# Not all resources may be rendered on the code editor but
# they sure as hell will be rendered in the interface.
# Trust the name!
_resources = {
    "color_picker": "",  # ==
    "settings": "",  # ==
    "image_dark": "",  # ==
    "image_light": "",  # ==
    "calendar_light": "",  # ==
    "calendar_dark": "",  # ==
    "copy": "",  # ==
    "clipboard": "",  # ==
    "folder": "",  # ==
    "file_explorer_light": "",  # ==
    "file_explorer_dark": "",  # ==
    "emoji": "",  # ==
    "aggregate": "",  # ==
    "arrow_left": "",  # ==
    "equalizer": "",  # ==
    "calculator": "",  # ==
    "developer": "",  # ==
    "math": "∑",  # ==
    "play": "",  # ==
    "network": "",  # ==
    "shield": "",  # ==
    "security": "",  # ==
    "close": "",  # ==
    "separate": "",  # ==
    "gaming": "",  # ==
    "data": "",  # ==
    "info": "",  # ==
    "image_editor": "",  # ==
    "crop_resize": "",  # ==
    "redo": "",  # ==
    "undo": "",  # ==
    "rotate_counterclockwise": "",  # ==
    "rotate_clockwise": "",  # ==
    "paint": "",  # ==
    "heart": "❤",  # ==
    "flip_horizontal": "",  # ==
    "flip_vertical": "",  # ==
    "camera": "",  # ==
    "chevron_up": "",  # ==
    "chevron_down": "",  # ==
    "chevron_left": "",  # ==
    "chevron_right": "",  # ==
    "triangle_up": "⏶",  # ==
    "triangle_down": "⏷",  # ==
    "triangle_right": "⏵",  # ==
    "triangle_left": "⏴",  # ==
    "checkbutton": "",  # ==
    "frame": "",  # ==
    "labelframe": "",  # ==
    "menu": "",  # ==
    "menubutton": "",  # ==
    "grid": "",  #
    "text": "",  #
    "combobox": "",  #
    "listbox": "",  #
    "radiobutton": "",  #
    "button": "",  #
    "multiline_text": "",  #
    "sizegrip": "",
    "treeview": "",
    "notebook": "",
    "progressbar": '',
    "scale": "",
    "entry": "",
    "fullscreen": "",

}


def get_icon(identifier: str) -> str:
    # Fetch icons from the _resource database
    # return an empty string resource if not found
    return _resources.get(identifier, "")


def get_icon_image(identifier: str, width=25, height=25):
    return get_tk_image(identifier, width, height)
