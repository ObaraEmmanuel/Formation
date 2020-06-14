"""
Conversions of design to xml and back
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #
from lxml import etree
from collections import defaultdict
from importlib import import_module
import re
import functools

from formation.preprocessors import preprocess

try:
    import Tkinter as tk
    import ttk
except ModuleNotFoundError:
    import tkinter as tk
    import tkinter.ttk as ttk

_preloaded = {
    "tkinter": tk,
    "Tkinter": tk,
    "ttk": ttk,
    "tkinter.ttk": ttk
}

_variable_types = (
    "tkinter.StringVar", "Tkinter.StringVar",
    "tkinter.BooleanVar", "Tkinter.BooleanVar",
    "tkinter.DoubleVar", "Tkinter.DoubleVar",
    "tkinter.IntVar", "Tkinter.IntVar",
)

_containers = (
    tk.Frame, ttk.Frame, tk.PanedWindow, ttk.PanedWindow, ttk.Notebook, tk.LabelFrame,
    ttk.LabelFrame, ttk.Sizegrip, tk.Toplevel
)

namespaces = {
    "layout": "http://www.hoversetformationstudio.com/layouts/",
    "attr": "http://www.hoversetformationstudio.com/styles/",
    "menu": "http://www.hoversetformationstudio.com/menu",
}
_reversed_namespaces = dict(zip(namespaces.values(), namespaces.keys()))
_tag_rgx = re.compile(r'(.+)\.([^.]+)')
_attr_rgx = re.compile(r'{(?P<namespace>.+)}(?P<attr>.+)')
_var_rgx = re.compile(r'.+Var')


def _register_namespaces():
    for k in namespaces:
        etree.register_namespace(k, namespaces[k])


def set_grid(widget, _=None, **options):
    for opt in list(options):
        if opt in ("width", "height"):
            widget[opt] = options.pop(opt)
    widget.grid(**options)


def set_pack(widget, _=None, **options):
    for opt in list(options):
        if opt in ("width", "height"):
            widget[opt] = options.pop(opt)
    widget.pack(**options)


def set_place(widget, _=None, **options):
    widget.place(**options)


def set_tab(widget, parent, **options):
    parent.add(widget, **options)


def set_pane(widget, parent, **options):
    parent.add(widget, **options)


_layout_handlers = {
    "FrameLayout": set_place,
    "LinearLayout": set_pack,
    "GridLayout": set_grid,
    "TabLayout": set_tab,
    "PanedLayout": set_pane,
    "NativePanedLayout": set_pane
}

_register_namespaces()


class BaseConverter:

    @staticmethod
    def _is_var(tag):
        return _var_rgx.match(tag)

    @classmethod
    def _get_class(cls, node):
        tag = node.tag
        match = _tag_rgx.search(tag)
        if match:
            module, impl = match.groups()
        else:
            raise SyntaxError("Malformed tag {}".format(tag))
        if module in _preloaded:
            module = _preloaded[module]
        else:
            module = import_module(module)

        if hasattr(module, impl):
            return getattr(module, impl)
        raise AttributeError("class {} not found in module {}".format(impl, module))

    @classmethod
    def preprocess(cls, **kwargs):
        return kwargs

    @classmethod
    def get_layout_handler(cls, node, widget):
        layout = cls.attrib(node).get("attr", {}).get("layout")
        if layout is not None:
            return _layout_handlers.get(layout)
        if widget.__class__ == ttk.Notebook:
            return set_tab
        elif widget.__class__ == tk.PanedWindow:
            return set_pane
        elif widget.__class__ == ttk.PanedWindow:
            return set_pane

    @staticmethod
    def get_altered_options(widget):
        keys = widget.configure()
        # items with a length of two or less are just alias definitions such as 'bd' and 'borderwidth' so we ignore them
        # compare the last and 2nd last item to see whether options have been altered
        return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2] and len(keys[key]) > 2}

    @staticmethod
    def create_element(parent, tag):
        if parent is not None:
            return etree.SubElement(parent, tag)
        return etree.Element(tag)

    @classmethod
    def load_attributes(cls, attributes, node, namespace=None):
        for attribute in attributes:
            node.attrib[cls.get_attr_name(namespace, attribute)] = str(attributes[attribute])

    @classmethod
    def from_xml(cls, node, builder, parent):
        obj_class = cls._get_class(node)
        styles = dict(**cls.attrib(node).get("attr", {}))
        if "layout" in styles:
            styles.pop("layout")
        if obj_class == ttk.PanedWindow and 'orient' in styles:
            orient = styles.pop('orient')
            obj = obj_class(parent, orient=orient, **preprocess(builder, styles))
        else:
            obj = obj_class(parent, **preprocess(builder, styles))
        parent_node = node.getparent()
        if parent_node is not None:
            layout_handler = cls.get_layout_handler(parent_node, parent)
            if layout_handler:
                layout = cls.attrib(node).get("layout", {})
                layout_handler(obj, parent, **preprocess(builder, layout))
        setattr(builder, node.attrib.get("name"), obj)
        return obj

    @staticmethod
    def get_attr_name(namespace, attr):
        if namespace is None:
            return attr
        return "{{{}}}{}".format(namespaces.get(namespace), attr)

    @staticmethod
    def extract_attr_name(attr):
        match = _attr_rgx.search(attr)
        if match:
            return match.group('attr')
        return attr

    @classmethod
    def drop_attr(cls, node, attr, namespace):
        attr = cls.get_attr_name(namespace, attr)
        if attr in node.attrib:
            node.attrib.pop(attr)

    @classmethod
    def group_attr(cls, node):
        grouped = defaultdict(dict)
        for attr in node.attrib:
            match = _attr_rgx.search(attr)
            if match:
                group = _reversed_namespaces.get(match.group("namespace"))
                grouped[group][match.group("attr")] = node.attrib.get(attr)

    @classmethod
    @functools.lru_cache(maxsize=4)
    def attrib(cls, node):
        grouped = defaultdict(dict)
        for attr in node.attrib:
            match = _attr_rgx.search(attr)
            if match:
                group = _reversed_namespaces.get(match.group("namespace"))
                grouped[group][match.group("attr")] = node.attrib.get(attr)
        return grouped

    @classmethod
    def get_attr(cls, node, attr, namespace):
        return node.attrib.get(cls.get_attr_name(namespace, attr))


class MenuConverter(BaseConverter):
    _types = [tk.COMMAND, tk.CHECKBUTTON, tk.RADIOBUTTON, tk.SEPARATOR, tk.CASCADE]

    @classmethod
    def from_xml(cls, node, builder, parent):
        widget = BaseConverter.from_xml(node, builder, parent)
        cls._menu_from_xml(node, builder, None, widget)
        return widget

    @classmethod
    def _menu_from_xml(cls, node, builder, menu=None, widget=None):
        for sub_node in node:
            attrib = cls.attrib(sub_node)
            if sub_node.tag in MenuConverter._types and menu is not None:
                menu.add(sub_node.tag)
                menu.entryconfigure(menu.index(tk.END), **preprocess(builder, attrib.get("menu", {})))
            elif cls._get_class(sub_node) == tk.Menu:
                obj_class = cls._get_class(sub_node)
                menu_obj = obj_class(widget, **preprocess(builder, attrib.get("attr", {})))
                if widget:
                    widget.configure(menu=menu_obj)
                elif menu:
                    menu.add(tk.CASCADE, menu=menu_obj)
                    menu.entryconfigure(menu.index(tk.END), **preprocess(builder, attrib.get("menu", {})))
                cls._menu_from_xml(sub_node, builder, menu_obj)


class VariableConverter(BaseConverter):

    @classmethod
    def from_xml(cls, node, builder, __=None):
        # we do not need the designer and parent attributes hence the _ and __
        obj_class = cls._get_class(node)
        attributes = cls.attrib(node).get("attr", {})
        _id = attributes.pop("name")
        obj = obj_class(**attributes)
        setattr(builder, _id, obj)
        return obj


class Builder:
    _conversion_map = {
        tk.Menubutton: MenuConverter,
        ttk.Menubutton: MenuConverter,
        # Add custom converters here
    }

    def __init__(self, parent, path):
        """
        Load xml design into a GUI with all components accessible as attributes
        To access a widget use its name as set in the designer
        :param parent: The parent window where the design widgets are to be loaded
        :param path: The path to the xml file containing the design
        """
        self._parent = parent
        self._image_cache = []  # Cache for images to shield them from garbage collection
        self._root = self._load_xml(path)

    def _get_converter(self, widget_class):
        return self._conversion_map.get(widget_class, BaseConverter)

    def _get_root_node(self, path):
        if isinstance(path, etree._Element):
            return path
        else:
            with open(path, 'rb') as stream:
                tree = etree.parse(stream)
                return tree.getroot()

    def _load_xml(self, path):
        root_node = self._get_root_node(path)
        # load variables first
        self._load_variables(root_node, self)
        return self._load_widgets(root_node, self, self._parent)

    def _load_variables(self, node, builder):
        for var in node.iter(*_variable_types):
            VariableConverter.from_xml(var, builder)

    def _load_widgets(self, node, builder, parent):
        converter = self._get_converter(BaseConverter._get_class(node))
        widget = converter.from_xml(node, builder, parent)
        if widget.__class__ not in _containers:
            # We dont need to load child tags of non-container widgets
            return widget
        for sub_node in node:
            if BaseConverter._is_var(sub_node.tag):
                # ignore variables
                continue
            self._load_widgets(sub_node, builder, widget)
        return widget


class AppBuilder(Builder):
    """
    Subclass of builder that allow opening of xml designs without
    toplevel root widget. It automatically creates a toplevel window
    and adapts its size to fit the design perfectly
    """

    def __init__(self, path, app=None, screenName=None, baseName=None, className: str = 'Tk', useTk=1, sync=0,
                 use=None):
        """
        Create a builder object that automatically adds itself into a toplevel window
        and resizes the window accordingly. The underlying toplevel window can
        be accesses as builder_object._app. The private accessor undrscore is to
        free as much as of the builder namespace to your user defined names and prevent
        possible issues
        :param path: Path to xml file created by the formation designer
        :param app: optional custom external toplevel to use, if unspecified a toplevel window is
        created for you
        The rest of the parameters are specific to the underlying toplevel window
        Return a new Toplevel widget on screen :param screenName. A new Tcl interpreter will
        be created. :param baseName will be used for the identification of the profile file (see
        readprofile).
        It is constructed from sys.argv[0] without extensions if None is given. CLASSNAME
        is the name of the widget class
        """
        if app is None:
            self._parent = self._app = tk.Tk(screenName, baseName, className, useTk, sync, use)
        else:
            self._parent = self._app = app

        super().__init__(self._app, path)
        self._root.pack(fill="both", expand=True)
        # set the xml file name as default
        # but only if the path is a actual string path and not an xml node
        if isinstance(path, str):
            self._app.title(path.split(".")[0])

    def _load_xml(self, path):
        root_node = self._get_root_node(path)
        layout = BaseConverter.attrib(root_node).get("layout", {})
        # Adjust toplevel window size to that of the root widget
        self._app.geometry('{}x{}'.format(layout.get("width", 200), layout.get("height", 200)))
        self._load_variables(root_node, self)
        return self._load_widgets(root_node, self, self._parent)

    def mainloop(self, n: int = 0):
        """
        Start the mainloop for the underlying toplevel window
        :param n:
        :return:
        """
        self._app.mainloop(n)
