"""
XML utilities for handling formation design files
"""
# ======================================================================= #
# Copyright (c) 2020 Hoverset Group.                                      #
# ======================================================================= #
import functools
import re
from collections import defaultdict

from lxml import etree

try:
    import Tkinter as tk
    import ttk
except ModuleNotFoundError:
    import tkinter as tk
    import tkinter.ttk as ttk

namespaces = {
    "layout": "http://www.hoversetformationstudio.com/layouts/",
    "attr": "http://www.hoversetformationstudio.com/styles/",
    "menu": "http://www.hoversetformationstudio.com/menu",
}
_reversed_namespaces = dict(zip(namespaces.values(), namespaces.keys()))
tag_rgx = re.compile(r"(.+)\.([^.]+)")
_attr_rgx = re.compile(r"{(?P<namespace>.+)}(?P<attr>.+)")
_var_rgx = re.compile(r".+Var$")


def _register_namespaces():
    for k in namespaces:
        etree.register_namespace(k, namespaces[k])


_register_namespaces()


class BaseConverter:
    """
    Base xml converter class. Contains utility methods useful in
    dealing with xml used in formation design files.
    """
    required_fields = []

    @staticmethod
    def _is_var(tag):
        return _var_rgx.match(tag)

    @staticmethod
    def get_source_line_info(node: etree._Element):
        """
        Returned a formatted message containing the line number in the
        xml file where the node is found

        :param node: Node whose source line is to be determined
        :return: formatted string containing the source line
        """
        return "" if node.sourceline is None else "Line {}: ".format(node.sourceline)

    @classmethod
    def _get_class(cls, node):
        """
        Obtain the class represented by the node for the sake of object creation

        :param node: Node whose class is to be  determined
        :return:
        """
        raise NotImplementedError("get_class method needs to be implemented")

    @staticmethod
    def create_element(parent, tag):
        """
        Create a :class:`lxml.etree._Element` node from a string tag

        :param parent: parent node for the node to be created
        :param tag: a string for the node. To obtain a node `<object></object>`
          tag will be the string "object"
        :return: a :class:`etree.SubElement` sub node if parent is provide else a :class:`lxml.etree.Element`
          root node
        """
        if parent is not None:
            return etree.SubElement(parent, tag)
        return etree.Element(tag)

    @classmethod
    def load_attributes(cls, attributes, node, namespace=None):
        """
        Set namespaced attributes to a node. Given a node `<object></object>`

        .. code-block:: python

            node = lxml.etree.Element('object')
            layout = {"width": "40", "height": "70"}

            # Assuming layout is a registered namespace
            BaseConverter.load_attributes(layout, node, namespace='layout')
            print(lxml.etree.tostring(node))

        This outputs the following xml

        .. code-block:: xml

            <object layout:width=40 layout:height=70></object>

        :param attributes: a dictionary containing the attributes
        :param node: node to be updated with attributes
        :param namespace: namespace to be used if any
        """
        for attribute in attributes:
            node.attrib[cls.get_attr_name(namespace, attribute)] = str(
                attributes[attribute]
            )

    @staticmethod
    def get_attr_name(namespace, attr):
        """
        Get the fully qualified namespaced attribute name. For instance, given xml node:

        .. code-block:: xml

            <object layout:width=40 layout:height=70></object>

        .. code-block:: python

            BaseConverter.get_attr_name("layout", "width")
            # returns {http://www.hoversetformationstudio.com/layouts/}width

        The fully qualified name can be used to directly set the node's attribute

        :param namespace: the attribute namespace
        :param attr: attribute to be determined
        :return: A fully qualified namespaced attribute name
        """
        if namespace is None:
            return attr
        return "{{{}}}{}".format(namespaces.get(namespace), attr)

    @staticmethod
    def extract_attr_name(attr):
        """
        Get the attribute name in a fully qualified namespaced name. A fully qualified name like
        ``{http://www.hoversetformationstudio.com/layouts/}width`` will return ``width``

        :param attr: namespaced attribute from which the attribute is to be extracted
        :return: simple extracted attribute name
        """
        match = _attr_rgx.search(attr)
        if match:
            return match.group("attr")
        return attr

    @classmethod
    def drop_attr(cls, node, attr, namespace=None):
        """
        Remove an attribute from a node.

        :param node: Node in which to drop the attribute
        :param attr: simple name of attribute to be dropped
        :param namespace: attribute's namespace if any
        """
        attr = cls.get_attr_name(namespace, attr)
        if attr in node.attrib:
            node.attrib.pop(attr)

    @classmethod
    @functools.lru_cache(maxsize=4)
    def attrib(cls, node):
        """
        Get all node attributes grouped by namespace. Given the following xml node:

        .. code-block:: xml

            <object
                name=60
                attr:color=red
                attr:text=something
                layout:width=50
                layout:height=70
            ></object>

        .. code-block:: python

            >>> BaseConverter.attrib(node)
            {"attr":{"color":"red", "text": "something"},
            "layout":{"width": "50", "height": "70"}}
            >>> BaseConverter.required_fields.append('color')
            >>> BaseConverter.attrib(node)
            {"attr":{"color":"red", "text": "something"},
            "layout":{"width": "50", "height": "70"},
            "color":{}}

        To ensure that a namespace is always included in the grouped result
        even if it is empty, add it to :py:attr:`BaseConverter.required_fields`

        :param node: Node whose attributes are to be obtained
        :return: a dictionary containing attributes grouped by namespace
        """
        grouped = defaultdict(dict)
        # add required fields
        for field in cls.required_fields:
            grouped[field] = {}
        for attr in node.attrib:
            match = _attr_rgx.search(attr)
            if match:
                group = _reversed_namespaces.get(match.group("namespace"))
                grouped[group][match.group("attr")] = node.attrib.get(attr)
        return grouped

    @classmethod
    def get_attr(cls, node, attr, namespace=None):
        """
        Get an attribute (value) from a node given the attribute name and namespace (if any)

        :param node: Node whose attribute is to be read
        :param attr: simple name of attribute to be read
        :param namespace: namespace of attribute if any
        :return: attribute value
        """
        return node.attrib.get(cls.get_attr_name(namespace, attr))

    @classmethod
    def is_equal(cls, node1, node2):
        """
        Compare two lxml nodes for equality. It checks for attribute equality,
        children and child order equality and tag name equality. Order of attributes
        does not matter

        :param node1: Node to be compared
        :param node2: Node to be compared

        :return: True if node1 is equal to node2
        """
        # if items are not nodes use default behaviour
        if not isinstance(node1, etree._Element) or not isinstance(
                node2, etree._Element
        ):
            return node1 == node2
        tag_eq = node1.tag == node2.tag
        attrib_eq = node1.attrib == node2.attrib
        child_eq = len(list(node1)) == len(list(node2))
        # if any of the above is false no need to even check further
        if child_eq and tag_eq and attrib_eq:
            for sub_node1, sub_node2 in zip(list(node1), list(node2)):
                child_eq = cls.is_equal(sub_node1, sub_node2)
                # if the equality check fails break immediately
                if not child_eq:
                    break
        return tag_eq and attrib_eq and child_eq
