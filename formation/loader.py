"""
Contains classes that load formation design files and generate user interfaces
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #
import functools
import logging
import os
import warnings
from collections import defaultdict
from importlib import import_module
import tkinter as tk
import tkinter.ttk as ttk

from formation.formats import Node, BaseAdapter, infer_format
from formation.handlers import dispatch_to_handlers, parse_arg
from formation.meth import Meth
from formation.handlers.image import parse_image
from formation.handlers.scroll import apply_scroll_config
from formation.utils import is_class_toplevel, is_class_root, callback_parse, event_handler
from formation.themes import get_theme
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
    tk.Tk,
)

_menu_containers = (
    tk.Menubutton,
    ttk.Menubutton,
    tk.Toplevel,
    tk.Tk,
)

_menu_item_types = (
    tk.CASCADE,
    tk.COMMAND,
    tk.CHECKBUTTON,
    tk.SEPARATOR,
    tk.RADIOBUTTON,
)

_canvas_item_types = (
    "Arc",
    "Bitmap",
    "Image",
    "Line",
    "Oval",
    "Polygon",
    "Rectangle",
    "Text",
    "Window"
)

_ignore_tags = (
    *_menu_item_types,
    *_canvas_item_types,
    "event",
    "grid",
    "meta",
    "meth"
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
        raise AttributeError("class {}  in module {}".format(impl, module))

    @classmethod
    def load(cls, node, builder, parent):
        obj_class = cls._get_class(node)
        cls._load_required_fields(node)
        config = node.attrib
        if obj_class == ttk.PanedWindow and "orient" in config.get("attr", {}):
            orient = config["attr"].pop("orient")
            obj = obj_class(parent, orient=orient)
        elif is_class_root(obj_class):
            obj = obj_class()
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
            elif sub_node.type == "meth":
                meth = Meth.from_node(sub_node)
                meth.call(
                    getattr(obj, sub_node.attrib["name"]),
                    parser=builder._arg_parser,
                    context=builder
                )
        return obj


class MenuLoaderAdapter(BaseLoaderAdapter):
    _types = [tk.COMMAND, tk.CHECKBUTTON, tk.RADIOBUTTON, tk.SEPARATOR, tk.CASCADE]

    @classmethod
    def load(cls, node, builder, parent):
        cls._load_required_fields(node)
        widget = BaseLoaderAdapter.load(node, builder, parent)
        cls._menu_load(node, builder, widget)
        return widget

    @classmethod
    def _menu_load(cls, node, builder, menu):
        for sub_node in node:
            if sub_node.type in _ignore_tags and sub_node.type not in _menu_item_types or sub_node.is_var():
                continue

            attrib = sub_node.attrib
            kwargs = {
                "parent_node": sub_node.parent,
                "node": sub_node,
                "builder": builder,
            }
            if sub_node.type in MenuLoaderAdapter._types:
                if menu is None:
                    continue
                menu.add(sub_node.type)
                index = menu.index(tk.END)
                dispatch_to_handlers(menu, attrib, **kwargs, menu=menu, index=index)
                continue

            obj_class = cls._get_class(sub_node)
            if issubclass(obj_class, tk.Menu):
                menu_obj = obj_class(menu)
                if menu:
                    menu.add(tk.CASCADE, menu=menu_obj)
                    index = menu.index(tk.END)
                    dispatch_to_handlers(
                        menu_obj, attrib, **kwargs, menu=menu, index=index
                    )
                cls._menu_load(sub_node, builder, menu_obj)


class VariableLoaderAdapter(BaseLoaderAdapter):

    @classmethod
    def load(cls, node, builder, __=None):
        obj_class = cls._get_class(node)
        attributes = node.attrib.get("attr", {})
        _id = attributes.pop("name")
        if not hasattr(builder, "_var_cache"):
            builder._var_cache = {}

        builder._var_cache[_id] = (obj_class, attributes, None)


class CanvasLoaderAdapter(BaseLoaderAdapter):

    @classmethod
    def load(cls, node, builder, parent):
        canvas = BaseLoaderAdapter.load(node, builder, parent)
        for sub_node in node:
            if sub_node.type not in _canvas_item_types:
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
        tk.Menu: MenuLoaderAdapter,
        tk.Canvas: CanvasLoaderAdapter,
        # Add custom adapters here
    }

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
        path = kwargs.get("path")
        self._path = path if path is None else os.path.abspath(path)
        self._meta = {}
        self._deferred_props = []

        if kwargs.get("node"):
            self.load_node(kwargs.get("node"))
        elif kwargs.get("string"):
            format_ = kwargs.get("format")
            if format_ is None:
                raise ValueError("format not provided, cannot infer format from string")
            self.load_string(kwargs.get("string"), format_)
        elif self._path:
            self.load_path(self._path)

        Meth.call_deferred(self)
        self._apply_deferred_props()

    def _apply_deferred_props(self):
        for prop, value, handle_method in self._deferred_props:
            value = getattr(self, value, None)
            if value:
                handle_method(**{prop: value})

    def _arg_parser(self, a, t):
        if t == "image":
            image = parse_image(a, master=self._root, base_path=self._path)
            self._image_cache.append(image)
            return image
        return parse_arg(a, t)

    def _get_adapter(self, widget_class):
        return self._adapter_map.get(widget_class, BaseLoaderAdapter)

    def _load_node(self, root_node):
        # load meta and variables first
        self._load_meta(root_node, self)
        self._verify_version()
        # lazy load variables
        self._load_variables(root_node, self)
        node = self._load_widgets(root_node, self, self._parent)
        theme = self._meta.get("theme")
        if theme:
            theme, sub_theme = theme.get("theme"), theme.get("sub_theme")
            theme = get_theme(theme)
            if theme:
                theme.set(sub_theme)
        self._flush_var_cache()
        if hasattr(self, "_scroll_map"):
            apply_scroll_config(self, self._scroll_map)
            delattr(self, "_scroll_map")
        return node

    def _load_variables(self, node, builder):
        for sub_node in node:
            if sub_node.is_var():
                VariableLoaderAdapter.load(sub_node, builder)

    def _get_var(self, name):
        if not hasattr(self, "_var_cache"):
            return None
        if name not in self._var_cache:
            return None
        obj_class, attributes, obj = self._var_cache[name]
        if obj is None:
            obj = obj_class(**attributes)
            self._var_cache[name] = (obj_class, attributes, obj)
            setattr(self, name, obj)
        return obj

    def _flush_var_cache(self):
        if not hasattr(self, "_var_cache"):
            return
        for name in self._var_cache:
            self._get_var(name)
        delattr(self, "_var_cache")

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
        if isinstance(widget, tk.Menu):
            # old-style menu format, so assign it to parent "menu" attribute
            if node.attrib.get("name") is None:
                # old-style menu format, so assign it to parent "menu" attribute
                if isinstance(parent, _menu_containers):
                    parent.configure(menu=widget)
            return widget
        for sub_node in node:
            if sub_node.is_var() or sub_node.type in _ignore_tags:
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
                handler_string = event.get("handler")
                parsed = list(callback_parse(handler_string))
                if parsed is None:
                    logger.warning("Callback string '%s' is malformed", handler_string)
                    continue

                # parsed[0] is the function name.
                # starting with "::" means the widget is the first argument
                if handler_string.startswith("::"):
                    parsed[1] = (widget, *parsed[1])

                handler = callback_map.get(parsed[0])
                if handler is not None:
                    # parsed[1] is function args/ parsed[2] is function kwargs.
                    partial_handler = functools.partial(event_handler, func=handler, args=parsed[1], kwargs=parsed[2])
                    widget.bind(
                        event.get("sequence"),
                        partial_handler,
                        event.get("add")
                    )
                else:
                    logger.warning("Callback '%s' not found", parsed[0])

        for prop, val, handle_method, widget in self._command_map:
            parsed = list(callback_parse(val))
            if parsed is None:
                logger.warning("Callback string '%s' is malformed", val)
                continue
            # starting with "::" means the widget is the first argument after the event object
            if val.startswith("::"):
                parsed[1] = (widget, *parsed[1])

            handler = callback_map.get(parsed[0])
            if handle_method is None:
                raise ValueError("Handle method is None, unable to apply binding")
            if handler is not None:
                partial_handler = functools.partial(handler, *parsed[1], **parsed[2])
                handle_method(**{prop: partial_handler})
            else:
                logger.warning("Callback '%s' not found", parsed[0])

    def load_path(self, path):
        """
        Load design file

        :param path: Path to design file to be loaded
        :return: root widget
        """
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
        self._app = app
        self._toplevel_args = args
        super().__init__(self._app, **kwargs)

    def _load_node(self, root_node):
        if self._app is None:
            # no external parent app provided
            obj_class = BaseLoaderAdapter._get_class(root_node)
            if not is_class_toplevel(obj_class):
                # widget is not toplevel, so we spin up a toplevel parent for it
                self._parent = self._app = tk.Tk(*self._toplevel_args)
        else:
            # use external app as parent
            self._parent = self._app

        layout = root_node.attrib.get("layout", {})
        root = super()._load_node(root_node)
        if not isinstance(root, (tk.Tk, tk.Toplevel)):
            # Adjust toplevel window size to that of the root widget
            self._app.geometry(
                "{}x{}".format(layout.get("width", 200), layout.get("height", 200))
            )
            root.pack(fill="both", expand=True)
        elif not self._app:
            # this means root is a toplevel so set it as the app and parent
            self._app = root
        return root

    def mainloop(self, n: int = 0):
        """
        Start the mainloop for the underlying toplevel window

        :param n:
        :return:
        """
        self._app.mainloop(n)
