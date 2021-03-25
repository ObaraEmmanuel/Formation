"""
Contains classes that load formation xml design files and generate user interfaces
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #
import logging
import os
from collections import defaultdict
from importlib import import_module

from lxml import etree

from formation import xml
from formation.xml import ttk, tk
from formation.handlers import dispatch_to_handlers

logger = logging.getLogger(__name__)

_preloaded = {"tkinter": tk, "Tkinter": tk, "ttk": ttk, "tkinter.ttk": ttk}

_variable_types = (
    "tkinter.StringVar",
    "Tkinter.StringVar",
    "tkinter.BooleanVar",
    "Tkinter.BooleanVar",
    "tkinter.DoubleVar",
    "Tkinter.DoubleVar",
    "tkinter.IntVar",
    "Tkinter.IntVar",
)

_containers = (
    tk.Frame,
    ttk.Frame,
    tk.PanedWindow,
    ttk.PanedWindow,
    ttk.Notebook,
    tk.LabelFrame,
    ttk.LabelFrame,
    ttk.Sizegrip,
    tk.Toplevel,
)

_menu_item_types = (
    tk.CASCADE,
    tk.COMMAND,
    tk.CHECKBUTTON,
    tk.SEPARATOR,
    tk.RADIOBUTTON,
)


class BaseConverter(xml.BaseConverter):
    required_fields = ["layout"]

    @classmethod
    def _get_class(cls, node):
        tag = node.tag
        match = xml.tag_rgx.search(tag)
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
    def from_xml(cls, node, builder, parent):
        obj_class = cls._get_class(node)
        config = cls.attrib(node)
        if obj_class == ttk.PanedWindow and "orient" in config.get("attr", {}):
            orient = config["attr"].pop("orient")
            obj = obj_class(parent, orient=orient)
        else:
            obj = obj_class(parent)
        parent_node = node.getparent()
        kwargs = {
            "parent_node": parent_node,
            "parent": parent,
            "node": node,
            "builder": builder,
        }
        dispatch_to_handlers(obj, config, **kwargs)
        name = node.attrib.get("name")
        if name:
            # if name attribute is missing calling setattr will raise errors
            setattr(builder, name, obj)
        for sub_node in node:
            if sub_node.tag == "event":
                builder._event_map[obj].append(dict(sub_node.attrib))
            elif sub_node.tag == "grid":
                if sub_node.attrib.get("column"):
                    column = sub_node.attrib.pop("column")
                    obj.columnconfigure(column, **sub_node.attrib)
                elif sub_node.attrib.get("row"):
                    row = sub_node.attrib.pop("row")
                    obj.rowconfigure(row, **sub_node.attrib)
        return obj


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
            if sub_node.tag == "event":
                continue
            attrib = cls.attrib(sub_node)
            kwargs = {
                "parent_node": sub_node.getparent(),
                "node": sub_node,
                "builder": builder,
            }
            if sub_node.tag in MenuConverter._types and menu is not None:
                menu.add(sub_node.tag)
                index = menu.index(tk.END)
                dispatch_to_handlers(menu, attrib, **kwargs, menu=menu, index=index)
            elif cls._get_class(sub_node) == tk.Menu:
                obj_class = cls._get_class(sub_node)
                menu_obj = obj_class(widget)
                if widget:
                    widget.configure(menu=menu_obj)
                    dispatch_to_handlers(menu_obj, attrib, **kwargs)
                elif menu:
                    menu.add(tk.CASCADE, menu=menu_obj)
                    index = menu.index(tk.END)
                    dispatch_to_handlers(
                        menu_obj, attrib, **kwargs, menu=menu, index=index
                    )
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
    """
    Load xml design into a GUI with all components accessible as attributes
    To access a widget use its name as set in the designer

    :param parent: The parent window where the design widgets are to be loaded
    :param path: The path to the xml file containing the design
    """

    _conversion_map = {
        tk.Menubutton: MenuConverter,
        ttk.Menubutton: MenuConverter,
        # Add custom converters here
    }

    _ignore_tags = (
        *_menu_item_types,
        "event",
        "grid"
    )

    def __init__(self, parent, **kwargs):
        self._parent = parent
        self._image_cache = (
            []
        )  # Cache for images to shield them from garbage collection
        # stores event binding for deferred connection to methods
        self._event_map = defaultdict(list)
        # stores command names for deferred connection to methods
        self._command_map = []
        self._root = None
        self._path = None

        if kwargs.get("path"):
            self.load_path(kwargs.get("path"))
        elif kwargs.get("string"):
            self.load_string(kwargs.get("string"))
        elif kwargs.get("node") is not None:
            self.load_node(kwargs.get("node"))

    def _get_converter(self, widget_class):
        return self._conversion_map.get(widget_class, BaseConverter)

    def _load_xml(self, root_node):
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
            if BaseConverter._is_var(sub_node.tag) or sub_node.tag in self._ignore_tags:
                # ignore variables and non widgets
                continue
            self._load_widgets(sub_node, builder, widget)
        return widget

    @property
    def path(self):
        """
        Get absolute path to loaded xml file if available

        :return: path to currently loaded xml file if builder was loaded
            from path else ``None``
        """
        return self._path

    def connect_callbacks(self, object_or_dict):
        """
        Connect bindings and callbacks to user defined functions and
        methods. It connects commands added through the various command
        config options such ``command, yscrollcommand, xscrollcommand`` among
        others. Callbacks added through bindings are connected as well.
        Below are possible ways to connect global functions.

        .. code-block:: python

            ...

            def on_click(event):
                print("button clicked")

            def on_keypress(event):
                print("key pressed")

            # method 1 ---------------------------

            build = Builder(parent, path="my_design.xml")
            build.connect_callbacks({
                "on_click": on_click,
                "on_keypress: on_keypress,
            })

            # method 2 ---------------------------

            build = Builder(path="my_design.xml")
            build.connect_callbacks(globals())

            ...

        To connect to object methods instead the code can be as shown below

        .. code-block:: python

            ...

            class App(tkinter.Tk):

                def __init__(self):
                    self.build = Builder(self, path="my_design.xml")
                    self.build.connect_callbacks(self)

                def on_click(self, event):
                    print("button clicked")

                def on_keypress(self, event):
                    print("key pressed")

            app = App()
            app.mainloop()

            ...

        :param object_or_dict: A dictionary containing function mappings
            or an object defining all the callback methods. The callback
            names have to exactly match what was entered in the studio.
        """
        if isinstance(object_or_dict, dict):
            callback_map = object_or_dict
        else:
            callback_map = {
                attr: getattr(object_or_dict, attr, None)
                for attr in dir(object_or_dict)
            }
        for widget, events in self._event_map.items():
            for event in events:
                handler = callback_map.get(event.get("handler"))
                if handler is not None:
                    widget.bind(
                        event.get("sequence"),
                        handler,
                        event.get("add")
                    )
                else:
                    logger.warning("Callback '%s' not found", event.get("handler"))

        for prop, val, handle_method in self._command_map:
            handler = callback_map.get(val)
            if handle_method is None:
                raise ValueError("Handle method is None, unable to apply binding")
            if handler is not None:
                handle_method(**{prop: handler})
            else:
                logger.warning("Callback '%s' not found", val)

    def load_path(self, path):
        """
        Load xml file

        :param path: Path to xml file to be loaded
        :return: root widget
        """
        with open(path, "rb") as stream:
            self._path = os.path.abspath(path)
            tree = etree.parse(stream)
            node = tree.getroot()
        self._root = self._load_xml(node)
        return self._root

    def load_string(self, xml_string):
        """
        Load the builder from a string

        :param xml_string: string containing xml to be loaded
        :return: root widget
        """
        node = etree.fromstring(xml_string)
        self._root = self._load_xml(node)
        return self._root

    def load_node(self, node: etree._Element):
        """
        Load the builder from :class:lxml._Element node

        :param node: :class:lxml._Element node to be loaded
        :return: root widget
        """
        self._root = self._load_xml(node)
        return self._root


class AppBuilder(Builder):
    """
    Subclass of :class:`formation.loader.Builder` that allow opening of xml designs without
    toplevel root widget. It automatically creates a toplevel window
    and adapts its size to fit the design perfectly. The underlying toplevel window can
    be accesses as _app. The private accessor underscore is to
    free as much as of the builder namespace to your user defined names and prevent
    possible issues

    :param app: optional custom external toplevel to use, if unspecified a toplevel window is created for you
    :param args: Additional arguments to be passed to underlying toplevel window
    :param kwargs: Keyword arguments to be passed to underlying toplevel window. The arguments allowed are:

      * path: Path to the xml file to be loaded
      * string: xml string to be loaded
      * node: :class:`lxml.etree._Element` node to be loaded

      These arguments are mutually exclusive since design can be loaded from only one format at time.

    .. code-block:: python
        :linenos:

        # import the formation library which loads the design for you
        from formation import AppBuilder

        # hello.xml can be any design file created in formation studio
        app = AppBuilder(path="hello.xml")

        app.mainloop()
    """

    def __init__(self, app=None, *args, **kwargs):
        if app is None:
            self._parent = self._app = tk.Tk(*args)
        else:
            self._parent = self._app = app

        super().__init__(self._app, **kwargs)

    def _load_xml(self, root_node):
        layout = BaseConverter.attrib(root_node).get("layout", {})
        # Adjust toplevel window size to that of the root widget
        self._app.geometry(
            "{}x{}".format(layout.get("width", 200), layout.get("height", 200))
        )
        root = super()._load_xml(root_node)
        root.pack(fill="both", expand=True)
        return root

    def mainloop(self, n: int = 0):
        """
        Start the mainloop for the underlying toplevel window

        :param n:
        :return:
        """
        self._app.mainloop(n)
