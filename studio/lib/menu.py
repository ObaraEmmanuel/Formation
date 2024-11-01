import abc
import logging
import tkinter as tk
from hoverset.data.images import load_tk_image
from studio.lib.properties import get_resolved, PROPERTY_TABLE, WIDGET_IDENTITY
from studio.lib.variables import VariableManager, VariableItem

__all__ = (
    "MENU_ITEMS",
    "Command",
    "Cascade",
    "CheckButton",
    "RadioButton",
    "Separator",
    "menu_config"
)

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


class MenuItem(abc.ABC):
    OVERRIDES = {}
    icon = "menubutton"
    display_name = "Item"
    _intercepts = {
        "image": _ImageIntercept,
        "selectimage": _ImageIntercept,
        "variable": _VariableIntercept
    }

    def __init__(self, menu, index, create=True, **kw):
        self.menu = menu
        self._index = index
        if create:
            self._create(**kw)
        self.node = None

    def _create(self, *args, **options):
        pass

    @property
    def name(self):
        if not self.menu:
            return ""
        if self.item_type == "separator":
            return "Separator"
        return self.menu.entrycget(self.index, "label")

    @property
    def item_type(self):
        return self.__class__.__name__.lower()

    def create_menu(self):
        return ()

    @property
    def index(self):
        return self._index + int(self.menu["tearoff"])

    @property
    def properties(self):
        conf = self.configure()
        resolved = {}
        for prop in conf:
            definition = get_resolved(
                prop, self.OVERRIDES, MENU_PROPERTY_TABLE,
                PROPERTY_TABLE, WIDGET_IDENTITY
            )
            if definition:
                definition["value"] = self.cget(prop)
                definition["default"] = conf[prop][-2]
                resolved[prop] = definition
        return resolved

    def __setitem__(self, key, value):
        self.configure({key: value})

    def configure(self, cnf=None, **kw):
        return menu_config(self.menu, self.index, None, cnf, **kw)

    def config(self, cnf=None, **kw):
        # This allows un-intercepted configuration
        return self.menu.entryconfigure(self.index, cnf, **kw)

    def __getitem__(self, item):
        return self.menu.entrycget(self.index, item)

    def cget(self, key):
        intercept = self._intercepts.get(key)
        if intercept:
            return intercept.get(self.menu, self.index, key)
        return self.menu.entrycget(self.index, key)

    def get_altered_options(self):
        keys = menu_config(self.menu, self.index)
        return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2]}


class Command(MenuItem):
    icon = "play"
    display_name = "Command"

    def _create(self, **options):
        super()._create(**options)
        self.menu.add_command(**options)


class Cascade(MenuItem):
    icon = "menubutton"
    display_name = "Cascade"

    def __init__(self, menu, index, create=True, **kw):
        super().__init__(menu, index, create, **kw)
        self.sub_menu = None

    def _create(self, **options):
        super()._create(**options)
        self.menu.add_cascade(**options)

    def create_menu(self):
        from studio.i18n import _
        return (
            ("separator",),
            ("cascade", _("Preview"), None, None, {'menu': self.sub_menu}),
        )


class CheckButton(MenuItem):
    icon = "checkbox"
    display_name = "Check Button"

    def _create(self, **options):
        super()._create(**options)
        self.menu.add_checkbutton(**options)


class RadioButton(MenuItem):
    icon = "radiobutton"
    display_name = "Radio Button"

    def _create(self, **options):
        super()._create(**options)
        self.menu.add_radiobutton(**options)


class Separator(MenuItem):
    icon = "line"
    display_name = "Separator"

    def _create(self, **options):
        # ignore options
        super()._create()
        self.menu.add_separator()


MENU_ITEMS = (
    Command, Cascade, CheckButton, RadioButton, Separator
)


def menu_config(parent_menu, index, key=None, cnf=None, **kw):
    cnf = cnf or {}
    kw.update(cnf)
    if not kw:
        if key in _intercepts:
            return _intercepts.get(key).get(parent_menu, index, key)
        if key is not None:
            return parent_menu.entrycget(index, key)

        config = parent_menu.entryconfigure(index)
        for prop in config:
            if prop in _intercepts:
                value = _intercepts.get(prop).get(parent_menu, index, prop)
                config[prop] = (*config[prop][:-1], value)
        return config
    for prop in kw:
        if prop in _intercepts:
            _intercepts.get(prop).set(parent_menu, index, kw[prop], prop)
        else:
            parent_menu.entryconfigure(index, **{prop: kw[prop]})
