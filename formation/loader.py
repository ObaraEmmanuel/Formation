"""
Contains classes that load formation design files and generate user interfaces
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #
import logging
import os
import warnings
from collections import defaultdict
from importlib import import_module
import tkinter as tk
import tkinter.ttk as ttk

from formation.formats import Node, BaseAdapter, infer_format
from formation.handlers import dispatch_to_handlers
import formation

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


class BaseLoaderAdapter(BaseAdapter):
    required_fields = ["layout"]

    @classmethod
    def _load_required_fields(cls, node):
        for key in cls.required_fields:
            if key not in node.attrib:
                node.attrib[key] = {}

    @classmethod
    def _get_class(cls, node):
        module, impl = node.get_mod_impl()
        if module in _preloaded:
            module = _preloaded[module]
        else:
            module = import_module(module)

        if hasattr(module, impl):
            return getattr(module, impl)
        raise AttributeError("class {} not found in module {}".format(impl, module))

    @classmethod
    def load(cls, node, builder, parent):
        obj_class = cls._get_class(node)
        cls._load_required_fields(node)
        config = node.attrib
        if obj_class == ttk.PanedWindow and "orient" in config.get("attr", {}):
            orient = config["attr"].pop("orient")
            obj = obj_class(parent, orient=orient)
        else:
            obj = obj_class(parent)
        parent_node = node.parent
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
            if sub_node.type == "event":
                builder._event_map[obj].append(dict(sub_node.attrib))
            elif sub_node.type == "grid":
                if sub_node.attrib.get("column"):
                    column = sub_node.attrib.pop("column")
                    obj.columnconfigure(column, **sub_node.attrib)
                elif sub_node.attrib.get("row"):
                    row = sub_node.attrib.pop("row")
                    obj.rowconfigure(row, **sub_node.attrib)
        return obj


class MenuLoaderAdapter(BaseLoaderAdapter):
    _types = [tk.COMMAND, tk.CHECKBUTTON, tk.RADIOBUTTON, tk.SEPARATOR, tk.CASCADE]

    @classmethod
    def load(cls, node, builder, parent):
        cls._load_required_fields(node)
        widget = BaseLoaderAdapter.load(node, builder, parent)
        cls._menu_load(node, builder, None, widget)
        return widget

    @classmethod
    def _menu_load(cls, node, builder, menu=None, widget=None):
        for sub_node in node:
            if sub_node.type == "event":
                continue
            attrib = sub_node.attrib
            kwargs = {
                "parent_node": sub_node.parent,
                "node": sub_node,
                "builder": builder,
            }
            if sub_node.type in MenuLoaderAdapter._types and menu is not None:
                menu.add(sub_node.type)
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
                cls._menu_load(sub_node, builder, menu_obj)


class VariableLoaderAdapter(BaseLoaderAdapter):

    @classmethod
    def load(cls, node, builder, __=None):
        # we do not need the designer and parent attributes hence the _ and __
        obj_class = cls._get_class(node)
        attributes = node.attrib.get("attr", {})
        _id = attributes.pop("name")
        obj = obj_class(**attributes)
        setattr(builder, _id, obj)
        return obj


class CanvasLoaderAdapter(BaseLoaderAdapter):

    @classmethod
    def load(cls, node, builder, parent):
        canvas = BaseLoaderAdapter.load(node, builder, parent)
        for sub_node in node:
            if sub_node.type in builder._ignore_tags:
                continue
            # just additional options that may be needed down the line
            kwargs = {
                "parent_node": sub_node.parent,
                "node": sub_node,
                "builder": builder,
            }

            _id = sub_node.attrib.pop("name", None)
            coords = sub_node.attrib.pop("coords", "").split(",")
            item_id = canvas._create(sub_node.type.lower(), coords, {})

            def handle(**config):
                canvas.itemconfig(item_id, config)

            dispatch_to_handlers(canvas, sub_node.attrib, **kwargs, handle_method=handle)
            if _id:
                setattr(builder, _id, item_id)

        return canvas


class Builder:
    """
    Load design file into a GUI with all components accessible as attributes
    To access a widget use its name as set in the designer

    :param parent: The parent window where the design widgets are to be loaded
    :param kwargs: Options used in loading
        * **path**: Path to file of supported format from which to load the design
        * **string**: String of supported format to be used in loading the design
        * **node**: an instance of :py:class:`~formation.formats.Node` from which to load the design directly
        * **format**: an instance of :py:class:`~formation.formats.BaseFormat` to be used in loading the string
        contents provided by the **string** option

    .. note::
        if the **string** option is used, not providing the **format** option will
        raise a :class:ValueError

    """

    _adapter_map = {
        tk.Menubutton: MenuLoaderAdapter,
        ttk.Menubutton: MenuLoaderAdapter,
        tk.Canvas: CanvasLoaderAdapter,
        # Add custom adapters here
    }

    _ignore_tags = (
        *_menu_item_types,
        "event",
        "grid",
        "meta"
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
        self._meta = {}

        if kwargs.get("path"):
            self.load_path(kwargs.get("path"))
        elif kwargs.get("string"):
            format_ = kwargs.get("format")
            if format_ is None:
                raise ValueError("format not provided, cannot infer format from string")
            self.load_string(kwargs.get("string"), format_)
        elif kwargs.get("node") is not None:
            self.load_node(kwargs.get("node"))

    def _get_adapter(self, widget_class):
        return self._adapter_map.get(widget_class, BaseLoaderAdapter)

    def _load_node(self, root_node):
        # load meta and variables first
        self._load_meta(root_node, self)
        self._verify_version()
        self._load_variables(root_node, self)
        return self._load_widgets(root_node, self, self._parent)

    def _load_variables(self, node, builder):
        for sub_node in node:
            if sub_node.is_var():
                VariableLoaderAdapter.load(sub_node, builder)

    def _verify_version(self):
        if self._meta.get("version"):
            _, major, __ = formation.__version__.split(".")
            if major < self._meta["version"].get("major", 0):
                warnings.warn(
                    "You are loading a design from a higher version of formation "
                    "and some features may not be supported. Update your formation loader"
                )

    def _load_meta(self, node, builder):
        for sub_node in node:
            if sub_node.type == 'meta' and sub_node.attrib.get('name'):
                meta = dict(sub_node.attrib)
                builder._meta[meta.pop('name')] = meta

    def _load_widgets(self, node, builder, parent):
        adapter = self._get_adapter(BaseLoaderAdapter._get_class(node))
        widget = adapter.load(node, builder, parent)
        if widget.__class__ not in _containers:
            # We dont need to load child tags of non-container widgets
            return widget
        for sub_node in node:
            if sub_node.is_var() or sub_node.type in self._ignore_tags:
                # ignore variables and non widgets
                continue
            self._load_widgets(sub_node, builder, widget)
        return widget

    @property
    def path(self):
        """
        Get absolute path to loaded design file if available

        :return: path to currently loaded design file if builder was loaded
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
        Load design file

        :param path: Path to design file to be loaded
        :return: root widget
        """
        self._path = os.path.abspath(path)
        tree = infer_format(path)(path=path)
        tree.load()
        self._root = self._load_node(tree.root)
        return self._root

    def load_string(self, content_string, format_):
        """
        Load the builder from a string

        :param content_string: string containing serialized design to be loaded
        :param format_: the format class sub-classing :py:class:`~formation.formats.BaseFormat` to be used
        :return: root widget
        """
        tree = format_(content_string)
        tree.load()
        self._root = self._load_node(tree.root)
        return self._root

    def load_node(self, node: Node):
        """
        Load the builder from a :py:class:`~formation.formats.Node` instance

        :param node: :py:class:`~formation.formats.Node` to be loaded
        :return: root widget
        """
        self._root = self._load_node(node)
        return self._root


class AppBuilder(Builder):
    """
    Subclass of :class:`formation.loader.Builder` that allow opening of designs files without
    toplevel root widget. It automatically creates a toplevel window
    and adapts its size to fit the design perfectly. The underlying toplevel window can
    be accesses as _app. The private accessor underscore is to
    free as much as of the builder namespace to your user defined names and prevent
    possible issues

    :param app: optional custom external toplevel to use, if unspecified a toplevel window is created for you
    :param args: Additional arguments to be passed to underlying toplevel window
    :param kwargs: Keyword arguments to be passed to underlying toplevel window. The arguments allowed are:

      * path: Path to the design file to be loaded
      * string: serialized design as string to be loaded
      * node: :py:class:`~formation.formats.Node` node to be loaded

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

    def _load_node(self, root_node):
        layout = root_node.attrib.get("layout", {})
        # Adjust toplevel window size to that of the root widget
        self._app.geometry(
            "{}x{}".format(layout.get("width", 200), layout.get("height", 200))
        )
        root = super()._load_node(root_node)
        root.pack(fill="both", expand=True)
        return root

    def mainloop(self, n: int = 0):
        """
        Start the mainloop for the underlying toplevel window

        :param n:
        :return:
        """
        self._app.mainloop(n)
