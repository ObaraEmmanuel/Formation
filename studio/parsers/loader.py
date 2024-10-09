"""
Conversions of design to xml and back
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #

import tkinter as tk

from formation.formats import infer_format, BaseAdapter, Node
from studio.feature.variablepane import VariablePane
from studio.feature.components import ComponentPane
from studio.lib.variables import VariableItem, VariableManager
from studio.lib import legacy, native
from studio.lib.menu import menu_config
from studio.lib.pseudo import Container, PseudoWidget
from studio.lib.events import make_event
from studio.lib.layouts import GridLayoutStrategy
from studio.preferences import Preferences
from studio.i18n import _
from formation.loader import _ignore_tags
from formation.meth import Meth
from formation.handlers import parse_arg
import studio


def get_widget_impl(widget):
    if not hasattr(widget, 'impl'):
        return widget.__class__.__module__ + "." + widget.__class__.__name__
    return widget.impl.__module__ + "." + widget.impl.__name__


class BaseStudioAdapter(BaseAdapter):
    _designer_alternates = {
        'tkinter': legacy,
        'tkinter.ttk': native,
        'Tkinter': legacy,
        'ttk': native
    }

    @classmethod
    def _get_class(cls, node):
        module, impl = node.get_mod_impl()
        if module in cls._designer_alternates:
            module = cls._designer_alternates.get(module)
        else:
            # search custom widgets
            components: ComponentPane = ComponentPane.get_instance()
            component = list(filter(
                lambda comp: comp.impl.__module__ == module and comp.impl.__name__ == impl,
                components.registered_widgets,
            ))
            if component:
                return component[0]
            else:
                raise ModuleNotFoundError(_("Could not resolve studio compatible widget for \"{}\"").format(node.type))
        if hasattr(module, impl):
            return getattr(module, impl)
        if impl == 'Panedwindow' and module == native:
            orient = node.attrib.get("attr", {}).get("orient")
            if orient == tk.HORIZONTAL:
                return native.HorizontalPanedWindow
            return native.VerticalPanedWindow
        raise NotImplementedError(_("class {} does not have a designer implementation variant in {}").format(impl, module))

    @classmethod
    def generate(cls, widget: PseudoWidget, parent=None):
        attr = widget.get_altered_options()
        node = Node(parent, get_widget_impl(widget))
        node.attrib['name'] = widget.id
        node["attr"] = attr
        layout_options = widget.layout.get_altered_options_for(widget)
        node["layout"] = layout_options

        scroll_conf = {}
        if isinstance(getattr(widget, "_cnf_x_scroll", None), PseudoWidget):
            scroll_conf["x"] = widget._cnf_x_scroll.id
        if isinstance(getattr(widget, "_cnf_y_scroll", None), PseudoWidget):
            scroll_conf["y"] = widget._cnf_y_scroll.id
        if scroll_conf:
            node["scroll"] = scroll_conf

        if hasattr(widget, "_event_map_"):
            for binding in widget._event_map_.values():
                bind_dict = binding._asdict()
                # id is not needed and will be recreated on loading
                bind_dict.pop("id")
                # convert field values to string
                bind_dict = {k: str(bind_dict[k]) for k in bind_dict}
                event_node = Node(node, "event")
                event_node.attrib.update(bind_dict)

        if isinstance(widget, Container) and widget.layout_strategy.__class__ == GridLayoutStrategy:
            layout = widget.layout_strategy
            if hasattr(widget, "_row_conf"):
                for row in widget._row_conf:
                    r_info = layout.get_row_def(None, row)
                    modified = {
                        i: str(r_info[i]["value"]) for i in r_info if r_info[i]["value"] != r_info[i]["default"]
                    }
                    row_node = Node(node, "grid")
                    row_node.attrib["row"] = str(row)
                    row_node.attrib.update(modified)
            if hasattr(widget, "_column_conf"):
                for column in widget._column_conf:
                    c_info = layout.get_column_def(None, column)
                    modified = {
                        i: str(c_info[i]["value"]) for i in c_info if c_info[i]["value"] != c_info[i]["default"]
                    }
                    column_node = Node(node, "grid")
                    column_node.attrib["column"] = str(column)
                    column_node.attrib.update(modified)

        for meth in widget.get_resolved_methods():
            meth.to_node(node)

        return node

    @classmethod
    def load(cls, node, designer, parent, bounds=None):
        obj_class = cls._get_class(node)
        attrib = node.attrib
        styles = attrib.get("attr", {})
        if obj_class in (native.VerticalPanedWindow, native.HorizontalPanedWindow):
            # use copy to maintain integrity of XMLForm on pop
            styles = dict(styles)
            if 'orient' in styles:
                styles.pop('orient')
        layout = attrib.get("layout", {})

        old_id = new_id = attrib["name"]
        if not designer._is_unique_id(old_id):
            new_id = designer._get_unique(obj_class)
        obj = designer.load(obj_class, new_id, parent, styles, layout, bounds)

        # store id cross-mapping for post-processing
        if old_id != new_id:
            designer._xlink_map[old_id] = obj

        # load scroll configuration
        scroll_conf = attrib.get("scroll", {})
        if scroll_conf.get("x"):
            obj._cnf_x_scroll = scroll_conf["x"]
        if scroll_conf.get("y"):
            obj._cnf_y_scroll = scroll_conf["y"]

        for sub_node in node:
            if sub_node.type == "event":
                binding = make_event(**sub_node.attrib)
                if not hasattr(obj, "_event_map_"):
                    obj._event_map_ = {}
                obj._event_map_[binding.id] = binding
            elif sub_node.type == "grid":
                # we may pop stuff so use a copy
                sub_attrib = dict(sub_node.attrib)
                if sub_attrib.get("column"):
                    column = sub_attrib.pop("column")
                    obj.body.columnconfigure(column, sub_attrib)
                    if not hasattr(obj, "_column_conf"):
                        obj._column_conf = set()
                    obj._column_conf.add(int(column))
                elif sub_attrib.get("row"):
                    row = sub_attrib.pop("row")
                    obj.body.rowconfigure(row, sub_attrib)
                    if not hasattr(obj, "_row_conf"):
                        obj._row_conf = set()
                    obj._row_conf.add(int(row))
            elif sub_node.type == "meth":
                meth = Meth.from_node(sub_node)
                meth.call(
                    obj.handle_method,
                    with_name=True,
                    context=designer,
                    parser=designer.builder._arg_parser
                )
        return obj

    @staticmethod
    def get_altered_options(widget):
        keys = widget.configure()
        # items with a length of two or less are just alias definitions such as 'bd' and 'borderwidth' so we ignore them
        # compare the last and 2nd last item to see whether options have been altered
        return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2] and len(keys[key]) > 2}


class MenuStudioAdapter(BaseStudioAdapter):
    _types = [tk.COMMAND, tk.CHECKBUTTON, tk.RADIOBUTTON, tk.SEPARATOR, tk.CASCADE]

    @staticmethod
    def get_item_options(menu, index):
        keys = menu_config(menu, index)
        if 'menu' in keys:
            keys.pop('menu')
        return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2]}

    @classmethod
    def generate(cls, widget: PseudoWidget, parent=None):
        node = BaseStudioAdapter.generate(widget, parent)
        node.remove_attrib('menu', 'attr')
        if widget.configure().get('menu')[-1]:
            menu = widget.nametowidget(widget['menu'])
            cls._menu_to_xml(node, menu)
        return node

    @classmethod
    def load(cls, node, designer, parent, bounds=None):
        widget = BaseStudioAdapter.load(node, designer, parent, bounds)
        cls._menu_from_xml(node, None, widget)
        return widget

    @classmethod
    def _menu_from_xml(cls, node, menu=None, widget=None):
        for sub_node in node:
            if sub_node.type in _ignore_tags and sub_node.type not in MenuStudioAdapter._types or sub_node.is_var():
                continue

            attrib = sub_node.attrib
            if sub_node.type in MenuStudioAdapter._types:
                if menu is not None:
                    menu.add(sub_node.type)
                    menu_config(menu, menu.index(tk.END), **attrib.get("menu", {}))
                continue

            obj_class = cls._get_class(sub_node)
            if obj_class == legacy.Menu:
                menu_obj = obj_class(widget, **attrib.get("attr", {}))
                if widget:
                    widget.configure(menu=menu_obj)
                elif menu:
                    menu.add(tk.CASCADE, menu=menu_obj)
                    menu_config(menu, menu.index(tk.END), **attrib.get("menu", {}))
                cls._menu_from_xml(sub_node, menu_obj)

    @classmethod
    def _menu_to_xml(cls, node, menu: legacy.Menu, **item_opt):
        if not menu:
            return
        size = menu.index(tk.END)
        if size is None:
            # menu is empty
            size = -1
        menu_node = Node(node, get_widget_impl(menu))
        menu_node["attr"] = cls.get_altered_options(menu)
        menu_node["menu"] = item_opt
        for i in range(size + 1):
            if menu.type(i) == tk.CASCADE:
                cls._menu_to_xml(menu_node,
                                 menu.nametowidget(menu.entrycget(i, 'menu')), **cls.get_item_options(menu, i))
            elif menu.type(i) != 'tearoff':
                sub_node = Node(menu_node, menu.type(i))
                sub_node["menu"] = cls.get_item_options(menu, i)
        return menu_node


class VariableStudioAdapter(BaseStudioAdapter):

    @classmethod
    def generate(cls, variable: VariableItem, parent=None):
        node = Node(
            parent,
            get_widget_impl(variable.var),
            {"attr":  {'name': variable.name, 'value': variable.value}}
        )
        return node

    @classmethod
    def load(cls, node, *_):
        # we only need the node argument; ignore the rest
        var_manager: VariablePane = VariablePane.get_instance()
        attributes = node.attrib.get("attr", {})
        var_manager.add_var(VariableItem.supported_types.get(node.type, tk.StringVar), **attributes)


class DesignBuilder:

    _adapter_map = {
        legacy.Menubutton: MenuStudioAdapter,
        native.Menubutton: MenuStudioAdapter,
        legacy.Toplevel: MenuStudioAdapter,
        legacy.Tk: MenuStudioAdapter
    }

    def __init__(self, designer):
        self.designer = designer
        self.root = None
        self.metadata = {}
        self._loaded_objs = set()

    @classmethod
    def add_adapter(cls, adapter, *obj_classes):
        """
        Connect an external adapter for a specific set of object types to the builder.
        """
        for obj_class in obj_classes:
            cls._adapter_map[obj_class] = adapter

    def generate(self):
        """
        Serialize the current contents of the designer for saving to file. Note
        that only the root widget and its child widgets are converted to xml. Any
        other widgets at the root level are ignored and cannot be recovered later
        :return:
        """
        adapter = self.get_adapter(self.designer.root_obj.__class__)
        self.root = adapter.generate(self.designer.root_obj, None)
        # load meta and variables first
        self._meta_to_tree(self.root)
        self._variables_to_tree(self.root)
        self.to_tree(self.designer.root_obj, with_node=self.root)

    def get_adapter(self, widget_class):
        return self._adapter_map.get(widget_class, BaseStudioAdapter)

    def load(self, path, designer):
        self.root = infer_format(path)(path=path).load()
        self._load_meta(self.root, designer)
        self._load_variables(self.root)
        self._loaded_objs.clear()
        root = self._load_widgets(self.root, designer, designer)
        self._post_process(designer)
        return root

    def _load_meta(self, node, designer):
        for sub_node in node:
            if sub_node.type == 'meta' and sub_node.attrib.get('name'):
                meta = dict(sub_node.attrib)
                self.metadata[meta.pop('name')] = meta
        theme = self.metadata.get("theme") or {}
        # run on main thread because some themes require thread-safe
        # access to the tcl interpreter
        designer.after(
            0, lambda: designer.set_theme(theme.get("theme"), theme.get("sub_theme"))
        )

    def _load_variables(self, node):
        for sub_node in node:
            if sub_node.is_var():
                VariableStudioAdapter.load(sub_node)

    def load_section(self, node, parent, bounds=None):
        """
        Load lxml node as a widget/group of widgets in the designer under a specific container
        :param parent: Container widget to contain new widget group/section
        :param node: lxml node to be loaded as a widget/group
        :param bounds: tuple of 4 elements describing the intended location of
        the new loaded widget. If left as None, node layout attributes will
        be used instead
        :return:
        """
        self._loaded_objs.clear()
        root = self._load_widgets(node, self.designer, parent, bounds)
        self._post_process(self.designer)
        return root

    def _load_widgets(self, node, designer, parent, bounds=None):
        line_info = node.get_source_line_info()
        try:
            adapter = self.get_adapter(BaseStudioAdapter._get_class(node))
            widget = adapter.load(node, designer, parent, bounds)
            # keep track of loaded objects
            self._loaded_objs.add(widget)
        except Exception as e:
            # Append line number causing error before re-raising for easier debugging by user
            raise e.__class__("{}{}".format(line_info, e)) from e
        if not isinstance(widget, Container):
            # We don't need to load child tags of non-container widgets
            return widget
        for sub_node in node:
            if sub_node.is_var() or sub_node.type in _ignore_tags:
                # ignore variables and non widget nodes
                continue
            if BaseStudioAdapter._get_class(sub_node) == legacy.Menu:
                continue
            self._load_widgets(sub_node, designer, widget)
        return widget

    def _post_process(self, designer):
        # call deferred methods
        Meth.call_deferred(designer)

        lookup = {}
        for obj in designer.objects:
            lookup[obj.id] = obj

        # override lookup with cross-reference map
        lookup.update(designer._xlink_map)
        designer._xlink_map.clear()

        for w in self._loaded_objs:
            if hasattr(w, "_cnf_y_scroll"):
                w._cnf_y_scroll = lookup.get(w._cnf_y_scroll, '')
            if hasattr(w, "_cnf_x_scroll"):
                w._cnf_x_scroll = lookup.get(w._cnf_x_scroll, '')

    def to_tree(self, widget, parent=None, with_node=None):
        """
        Convert a PseudoWidget widget and its children to a node
        :param widget: widget to be converted to an xml node
        :param parent: The intended xml node to act as parent to the created
        :param with_node: This node will be used as starting point and no node
            will be created from widget
        xml node
        :return: the widget converted to a :class:Node instance.
        """
        node = with_node
        if node is None:
            adapter = self.get_adapter(widget.__class__)
            node = adapter.generate(widget, parent)
        if isinstance(widget, Container):
            for child in widget._non_visual_children:
                self.to_tree(child, node)
            for child in widget._children:
                self.to_tree(child, node)
        return node

    def _variables_to_tree(self, parent):
        variables = VariableManager.variables(self.designer.context)
        for var_item in variables:
            VariableStudioAdapter.generate(var_item, parent)

    def _gen_meta_node(self, name, parent, **data):
        node = Node(
            parent,
            'meta',
            dict(data, name=name)
        )
        return node

    def _meta_to_tree(self, parent):
        # load all required meta here
        _, major, minor = studio.__version__.split(".")
        self._gen_meta_node("version", parent, major=major, minor=minor)
        theme, sub_theme = self.designer.theme
        if theme:
            if sub_theme:
                self._gen_meta_node("theme", parent, theme=theme, sub_theme=sub_theme)
            else:
                self._gen_meta_node("theme", parent, theme=theme)

    def _arg_parser(self, arg, typ):
        # bypass image conversion
        if typ == "image":
            return arg
        return parse_arg(arg, typ)

    def write(self, path):
        """
        Writes contents of the designer to a file specified by path
        :param path: Path to file to be written to
        :return: String
        """
        file_loader = infer_format(path)
        pref = Preferences.acquire()
        pref_path = f"designer::{file_loader.name.lower()}"
        pref.set_default(pref_path, {})
        # generate an upto-date tree first
        self.generate()
        content = file_loader(node=self.root).generate(**pref.get(pref_path))
        with open(path, 'w') as dump:
            dump.write(content)

    def __eq__(self, other):
        if isinstance(other, DesignBuilder):
            return self.root == other.root
        return False

    def __ne__(self, other):
        return not (self == other)
