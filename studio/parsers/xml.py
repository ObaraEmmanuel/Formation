"""
Conversions of design to xml and back
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #

import tkinter as tk

from lxml import etree

from formation import xml
from studio.feature.variablepane import VariablePane
from studio.lib.variables import VariableItem
from studio.lib import legacy, native
from studio.lib.menu import menu_config, MENU_ITEM_TYPES
from studio.lib.pseudo import Container, PseudoWidget
from studio.lib.events import make_event
from studio.lib.layouts import GridLayoutStrategy


def get_widget_impl(widget):
    if not hasattr(widget, 'impl'):
        return widget.__class__.__module__ + "." + widget.__class__.__name__
    return widget.impl.__module__ + "." + widget.impl.__name__


class BaseConverter(xml.BaseConverter):
    _designer_alternates = {
        'tkinter': legacy,
        'tkinter.ttk': native,
        'Tkinter': legacy,
        'ttk': native
    }

    @classmethod
    def _get_class(cls, node):
        tag = node.tag
        match = xml.tag_rgx.search(tag)
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

    @classmethod
    def to_xml(cls, widget: PseudoWidget, parent=None):
        node = cls.create_element(parent, get_widget_impl(widget))
        attr = widget.get_altered_options()
        node.attrib['name'] = widget.id
        cls.load_attributes(attr, node, 'attr')
        layout_options = widget.layout.get_altered_options_for(widget)
        cls.load_attributes(layout_options, node, 'layout')

        if hasattr(widget, "_event_map_"):
            for binding in widget._event_map_.values():
                bind_dict = binding._asdict()
                # id is not needed and will be recreated on loading
                bind_dict.pop("id")
                # convert field values to string
                bind_dict = {k: str(bind_dict[k]) for k in bind_dict}
                event_node = cls.create_element(node, "event")
                event_node.attrib.update(bind_dict)

        if isinstance(widget, Container) and widget.layout_strategy.__class__ == GridLayoutStrategy:
            layout = widget.layout_strategy
            if hasattr(widget, "_row_conf"):
                for row in widget._row_conf:
                    r_info = layout.get_row_def(None, row)
                    modified = {i: str(r_info[i]["value"]) for i in r_info if r_info[i]["value"] != r_info[i]["default"]}
                    row_node = cls.create_element(node, "grid")
                    row_node.attrib["row"] = str(row)
                    row_node.attrib.update(modified)
            if hasattr(widget, "_column_conf"):
                for column in widget._column_conf:
                    c_info = layout.get_column_def(None, column)
                    modified = {i: str(c_info[i]["value"]) for i in c_info if c_info[i]["value"] != c_info[i]["default"]}
                    column_node = cls.create_element(node, "grid")
                    column_node.attrib["column"] = str(column)
                    column_node.attrib.update(modified)

        return node

    @classmethod
    def from_xml(cls, node, designer, parent, bounds=None):
        obj_class = cls._get_class(node)
        attrib = cls.attrib(node)
        styles = attrib.get("attr", {})
        if obj_class in (native.VerticalPanedWindow, native.HorizontalPanedWindow):
            # use copy to maintain integrity of XMLForm on pop
            styles = dict(styles)
            if 'orient' in styles:
                styles.pop('orient')
        layout = attrib.get("layout", {})
        obj = designer.load(obj_class, node.attrib.get("name"), parent, styles, layout, bounds)
        for sub_node in node:
            if sub_node.tag == "event":
                binding = make_event(**sub_node.attrib)
                if not hasattr(obj, "_event_map_"):
                    obj._event_map_ = {}
                obj._event_map_[binding.id] = binding
            elif sub_node.tag == "grid":
                # we may pop stuff so use a copy
                sub_attrib = dict(sub_node.attrib)
                if sub_attrib.get("column"):
                    column = sub_attrib.pop("column")
                    obj.columnconfigure(column, sub_attrib)
                    if not hasattr(obj, "_column_conf"):
                        obj._column_conf = set()
                    obj._column_conf.add(int(column))
                elif sub_attrib.get("row"):
                    row = sub_attrib.pop("row")
                    obj.rowconfigure(row, sub_attrib)
                    if not hasattr(obj, "_row_conf"):
                        obj._row_conf = set()
                    obj._row_conf.add(int(row))
        return obj

    @staticmethod
    def get_altered_options(widget):
        keys = widget.configure()
        # items with a length of two or less are just alias definitions such as 'bd' and 'borderwidth' so we ignore them
        # compare the last and 2nd last item to see whether options have been altered
        return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2] and len(keys[key]) > 2}


class MenuConverter(BaseConverter):
    _types = [tk.COMMAND, tk.CHECKBUTTON, tk.RADIOBUTTON, tk.SEPARATOR, tk.CASCADE]

    @staticmethod
    def get_item_options(menu, index):
        keys = menu_config(menu, index)
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
    def from_xml(cls, node, designer, parent, bounds=None):
        widget = BaseConverter.from_xml(node, designer, parent, bounds)
        cls._menu_from_xml(node, None, widget)
        return widget

    @classmethod
    def _menu_from_xml(cls, node, menu=None, widget=None):
        for sub_node in node:
            if sub_node.tag == "event":
                continue
            attrib = cls.attrib(sub_node)
            if sub_node.tag in MenuConverter._types and menu is not None:
                menu.add(sub_node.tag)
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
        menu_node = cls.create_element(node, get_widget_impl(menu))
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
        node = cls.create_element(parent, get_widget_impl(variable.var))
        attributes = {'name': variable.name, 'value': variable.value}
        cls.load_attributes(attributes, node, 'attr')
        return node

    @classmethod
    def from_xml(cls, node, *_):
        # we only need the node argument; ignore the rest
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
        self._ignore_tags = (
            *MENU_ITEM_TYPES,
            "event",
            "grid"
        )
        self.designer = designer
        self.root = None

    def generate(self):
        """
        Convert the current contents of the designer to xml. Note that only
        the root widget and its child widgets are converted to xml
        :return:
        """
        self.root = self.to_xml_tree(self.designer.root_obj)
        self._variables_to_xml(self.root)

    def get_converter(self, widget_class):
        return self._conversion_map.get(widget_class, BaseConverter)

    def load_xml(self, stream, designer):
        if isinstance(stream, str):
            tree = etree.fromstring(stream)
        else:
            tree = etree.parse(stream)
        self.root = tree.getroot()
        self._load_variables(self.root)
        return self._load_widgets(self.root, designer, designer)

    def _load_variables(self, node):
        for var in node.iter(*VariableItem.supported_types):
            VariableConverter.from_xml(var)

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
        return self._load_widgets(node, self.designer, parent, bounds)

    def _load_widgets(self, node, designer, parent, bounds=None):
        line_info = BaseConverter.get_source_line_info(node)
        try:
            converter = self.get_converter(BaseConverter._get_class(node))
            widget = converter.from_xml(node, designer, parent, bounds)
        except Exception as e:
            # Append line number causing error before re-raising for easier debugging by user
            raise e.__class__("{}{}".format(line_info, e)) from e
        if not isinstance(widget, Container):
            # We dont need to load child tags of non-container widgets
            return widget
        for sub_node in node:
            if BaseConverter._is_var(sub_node.tag) or sub_node.tag in self._ignore_tags:
                # ignore variables and non widget nodes
                continue
            self._load_widgets(sub_node, designer, widget)
        return widget

    def to_xml_tree(self, widget, parent=None):
        """
        Convert a PseudoWidget widget and its children to an xml tree/node
        :param widget: widget to be converted to an xml node
        :param parent: The intended xml node to act as parent to the created
        xml node
        :return: the widget converted to an xml node.
        """
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

    def to_xml_bytes(self, pretty_print=True):
        etree.cleanup_namespaces(self.root, top_nsmap=xml.namespaces)
        return etree.tostring(self.root, pretty_print=pretty_print, encoding='utf-8',
                              xml_declaration=True)

    def to_xml(self, pretty_print=True):
        """
        Gets the xml text representing the contents of the designer
        :param pretty_print: boolean flag indicating whether the text is to be indented and prettified
        :return: String
        """
        return self.to_xml_bytes(pretty_print).decode('utf-8')

    def __eq__(self, other):
        if isinstance(other, XMLForm):
            return BaseConverter.is_equal(self.root, other.root)
        return False

    def __ne__(self, other):
        return not (self == other)
