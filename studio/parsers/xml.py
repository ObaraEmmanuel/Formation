"""
Conversions of design to xml and back
"""
import functools
import re
import tkinter as tk
from collections import defaultdict

# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #
from lxml import etree

from studio.feature.variable_manager import VariablePane, VariableItem
from studio.lib import legacy, native
from studio.lib.menus import MenuTree
from studio.lib.pseudo import Container, PseudoWidget

namespaces = {
    "layout": "http://www.hoversetformationstudio.com/layouts/",
    "attr": "http://www.hoversetformationstudio.com/styles/",
    "menu": "http://www.hoversetformationstudio.com/menu",
}
_reversed_namespaces = dict(zip(namespaces.values(), namespaces.keys()))
_tag_rgx = re.compile(r'(.+)\.([^.]+)')
_attr_rgx = re.compile(r'{(?P<namespace>.+)}(?P<attr>.+)')
_var_rgx = re.compile(r'.+Var')


def _get_widget_impl(widget):
    if not hasattr(widget, 'impl'):
        return widget.__class__.__module__ + "." + widget.__class__.__name__
    return widget.impl.__module__ + "." + widget.impl.__name__


def _register_namespaces():
    for k in namespaces:
        etree.register_namespace(k, namespaces[k])


_register_namespaces()


class BaseConverter:
    _designer_alternates = {
        'tkinter': legacy,
        'tkinter.ttk': native,
        'Tkinter': legacy,
        'ttk': native
    }

    @staticmethod
    def _is_var(tag):
        return _var_rgx.match(tag)

    @staticmethod
    def get_source_line_info(node: etree._Element):
        return "" if node.sourceline is None else "Line {}: ".format(node.sourceline)

    @classmethod
    def _get_class(cls, node):
        tag = node.tag
        match = _tag_rgx.search(tag)
        if match:
            module, impl = match.groups()
        else:
            raise SyntaxError("Malformed tag {}".format(tag))
        if module in cls._designer_alternates:
            module = cls._designer_alternates.get(module)
        else:
            raise ModuleNotFoundError("module {} not implemented by designer".format(module))
        if hasattr(module, impl):
            return getattr(module, impl)
        elif impl == 'Panedwindow' and module == native:
            orient = cls.attrib(node).get("attr", {}).get("orient")
            if orient == tk.HORIZONTAL:
                return native.HorizontalPanedWindow
            else:
                return native.VerticalPanedWindow
        raise NotImplementedError("class {} does not have a designer implementation variant in {}".format(impl, module))

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
    def to_xml(cls, widget: PseudoWidget, parent=None):
        node = cls.create_element(parent, _get_widget_impl(widget))
        assert isinstance(widget, PseudoWidget)
        attr = widget.get_altered_options()
        node.attrib['name'] = widget.id
        cls.load_attributes(attr, node, 'attr')
        layout_options = widget.layout.get_altered_options_for(widget)
        cls.load_attributes(layout_options, node, 'layout')
        return node

    @classmethod
    def load_attributes(cls, attributes, node, namespace=None):
        for attribute in attributes:
            node.attrib[cls.get_attr_name(namespace, attribute)] = str(attributes[attribute])

    @classmethod
    def from_xml(cls, node, designer, parent):
        obj_class = cls._get_class(node)
        styles = cls.attrib(node).get("attr", {})
        if obj_class in (native.VerticalPanedWindow, native.HorizontalPanedWindow):
            if 'orient' in styles:
                styles.pop('orient')
        layout = cls.attrib(node).get("layout", {})
        obj = designer.load(obj_class, node.attrib.get("name"), parent, styles, layout)
        return obj

    @staticmethod
    def get_attr_name(namespace, attr):
        if namespace is None:
            return attr
        return f"{{{namespaces.get(namespace)}}}{attr}"

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
    @functools.lru_cache(maxsize=4)
    def attrib(cls, node):
        grouped = defaultdict(dict)
        for attr in node.attrib:
            match = _attr_rgx.search(attr)
            if match:
                group = _reversed_namespaces.get(match.group("namespace"))
                grouped[group][match.group("attr")] = node.attrib.get(attr)
        return grouped


class MenuConverter(BaseConverter):
    _types = [tk.COMMAND, tk.CHECKBUTTON, tk.RADIOBUTTON, tk.SEPARATOR, tk.CASCADE]

    @staticmethod
    def get_item_options(menu, index):
        keys = MenuTree.menu_config(menu, index)
        if 'menu' in keys:
            keys.pop('menu')
        return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2]}

    @classmethod
    def to_xml(cls, widget: PseudoWidget, parent=None):
        node = BaseConverter.to_xml(widget, parent)
        cls.drop_attr(node, 'menu', 'attr')
        if widget.configure().get('menu')[-1]:
            menu = widget.nametowidget(widget['menu'])
            cls._menu_to_xml(node, menu)
        return node

    @classmethod
    def from_xml(cls, node, designer, parent):
        widget = BaseConverter.from_xml(node, designer, parent)
        cls._menu_from_xml(node, None, widget)
        return widget

    @classmethod
    def _menu_from_xml(cls, node, menu=None, widget=None):
        for sub_node in node:
            attrib = cls.attrib(sub_node)
            if sub_node.tag in MenuConverter._types and menu is not None:
                menu.add(sub_node.tag)
                MenuTree.menu_config(menu, menu.index(tk.END), **attrib.get("menu", {}))
                return

            obj_class = cls._get_class(sub_node)
            if obj_class == legacy.Menu:
                menu_obj = obj_class(widget, **attrib.get("attr", {}))
                if widget:
                    widget.configure(menu=menu_obj)
                elif menu:
                    menu.add(tk.CASCADE, menu=menu_obj)
                    MenuTree.menu_config(menu, menu.index(tk.END), **attrib.get("menu", {}))
                cls._menu_from_xml(sub_node, menu_obj)

    @classmethod
    def _menu_to_xml(cls, node, menu: legacy.Menu, **item_opt):
        if not menu:
            return
        size = menu.index(tk.END)
        if size is None:
            # menu is empty
            return
        menu_node = cls.create_element(node, _get_widget_impl(menu))
        cls.load_attributes(cls.get_altered_options(menu), menu_node, 'attr')
        cls.load_attributes(item_opt, menu_node, 'menu')
        for i in range(size + 1):
            if menu.type(i) == tk.CASCADE:
                cls._menu_to_xml(menu_node,
                                 menu.nametowidget(menu.entrycget(i, 'menu')), **cls.get_item_options(menu, i))
            elif menu.type(i) != 'tearoff':
                sub_node = cls.create_element(menu_node, menu.type(i))
                cls.load_attributes(cls.get_item_options(menu, i), sub_node, 'menu')
        return menu_node


class VariableConverter(BaseConverter):

    @classmethod
    def to_xml(cls, variable: VariableItem, parent=None):
        node = cls.create_element(parent, _get_widget_impl(variable.var))
        attributes = {'name': variable.name, 'value': variable.value}
        cls.load_attributes(attributes, node, 'attr')
        return node

    @classmethod
    def from_xml(cls, node, _=None, __=None):
        # we do not need the designer and parent attributes hence the _ and __
        var_manager: VariablePane = VariablePane.get_instance()
        attributes = cls.attrib(node).get("attr", {})
        var_manager.add_var(VariableItem.supported_types.get(node.tag, tk.StringVar), **attributes)


class XMLForm:

    def __init__(self, designer):
        self._conversion_map = {
            legacy.Menubutton: MenuConverter,
            native.Menubutton: MenuConverter,
            # Add custom converters here
        }
        self.designer = designer

    def generate(self):
        self.root = self.to_xml_tree(self.designer.root_obj)
        self._variables_to_xml(self.root)

    def get_converter(self, widget_class):
        return self._conversion_map.get(widget_class, BaseConverter)

    def load_xml(self, byte_stream, designer):
        tree = etree.parse(byte_stream)
        self.root = tree.getroot()
        self._load_variables(self.root)
        return self._load_widgets(self.root, designer, designer)

    def _load_variables(self, node):
        for var in node.iter(*VariableItem.supported_types):
            VariableConverter.from_xml(var)

    def _load_widgets(self, node, designer, parent):
        line_info = BaseConverter.get_source_line_info(node)
        try:
            converter = self.get_converter(BaseConverter._get_class(node))
            widget = converter.from_xml(node, designer, parent)
        except Exception as e:
            # Append line number causing error before re-raising for easier debugging by user
            raise e.__class__("{}{}".format(line_info, e)) from e
        if not isinstance(widget, Container):
            # We dont need to load child tags of non-container widgets
            return widget
        for sub_node in node:
            if BaseConverter._is_var(sub_node.tag):
                # ignore variables
                continue
            self._load_widgets(sub_node, designer, widget)
        return widget

    def to_xml_tree(self, widget, parent=None):
        converter = self.get_converter(widget.__class__)
        node = converter.to_xml(widget, parent)
        if isinstance(widget, Container):
            for child in widget._children:
                self.to_xml_tree(child, node)
        return node

    def _variables_to_xml(self, parent):
        variables = VariablePane.get_instance().variables
        for var_item in variables:
            VariableConverter.to_xml(var_item, parent)

    def to_xml(self, pretty_print=True):
        return etree.tostring(self.root, pretty_print=pretty_print).decode('utf-8')

    def to_xml_bytes(self, pretty_print=True):
        return etree.tostring(self.root, pretty_print=pretty_print)
