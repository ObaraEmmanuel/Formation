import logging
import tkinter as tk
from hoverset.data.images import load_tk_image
from studio.lib.variables import VariableManager, VariableItem

MENU_PROPERTY_TABLE = {
    "hidemargin": {
        "name": "hidemargin",
        "display_name": "hide margin",
        "type": "boolean",
    },
    "columnbreak": {
        "display_name": "column break",
        "type": "boolean",
    },
    "selectcolor": {
        "display_name": "select color",
        "type": "color",
    },
    "value": {
        "display_name": "value",
        "type": "text",
    },
    "accelerator": {
        "display_name": "accelerator",
        "type": "text",
    }
}

MENU_PROPERTIES = (
    'compound', 'image', 'columnbreak', 'menu', 'label', 'foreground', 'accelerator', 'command', 'variable',
    'selectimage', 'underline', 'onvalue', 'activebackground', 'indicatoron', 'offvalue', 'value', 'background',
    'bitmap', 'activeforeground', 'hidemargin', 'font', 'selectcolor', 'state',
)

MENU_ITEM_TYPES = (
    tk.CASCADE,
    tk.COMMAND,
    tk.CHECKBUTTON,
    tk.SEPARATOR,
    tk.RADIOBUTTON,
)


class _ImageIntercept:
    _image_lookup = {}
    _image_cache = set()
    __slots__ = ()

    @classmethod
    def set(cls, menu, index, value, prop='image'):
        try:
            image = load_tk_image(value)
        except Exception:
            logging.error("could not open image at {}".format(value))
            return
        # store the image string name in the lookup along with its path
        cls._image_lookup[str(image)] = value
        # add to cache to protect image from garbage collection
        cls._image_cache.add(image)
        menu.entryconfigure(index, **{prop: image})

    @classmethod
    def get(cls, menu, index, prop='image'):
        return cls._image_lookup.get(menu.entrycget(index, prop), '')


class _VariableIntercept:
    __slots__ = []

    @staticmethod
    def set(menu, index, value, prop):
        if isinstance(value, tk.Variable):
            menu.entryconfigure(index, **{prop: value})
        else:
            variable = VariableManager.lookup(value)
            if isinstance(variable, VariableItem):
                menu.entryconfigure(index, **{prop: variable.var})
            else:
                logging.debug(f'variable {value} not found')

    @staticmethod
    def get(menu, index, prop):
        return str(VariableManager.lookup(menu.entrycget(index, prop)))


_intercepts = {
    "image": _ImageIntercept,
    "selectimage": _ImageIntercept,
    "variable": _VariableIntercept
}


def menu_config(parent_menu, index, key=None, **kw):
    if not kw:
        if key in _intercepts:
            return _intercepts.get(key).get(parent_menu, index, key)
        elif key is not None:
            return parent_menu.entrycget(index, key)

        config = parent_menu.entryconfigure(index)
        for prop in config:
            if prop in _intercepts:
                value = _intercepts.get(prop).get(parent_menu, index, prop)
                config[prop] = (*config[prop][:-1], value)
        return config
    else:
        for prop in kw:
            if prop in _intercepts:
                _intercepts.get(prop).set(parent_menu, index, kw[prop], prop)
            else:
                parent_menu.entryconfigure(index, **{prop: kw[prop]})
