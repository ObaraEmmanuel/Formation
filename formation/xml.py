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
tag_rgx = re.compile(r'(.+)\.([^.]+)')
_attr_rgx = re.compile(r'{(?P<namespace>.+)}(?P<attr>.+)')
_var_rgx = re.compile(r'.+Var$')


def _register_namespaces():
    for k in namespaces:
        etree.register_namespace(k, namespaces[k])


_register_namespaces()


class BaseConverter:

    @staticmethod
    def _is_var(tag):
        return _var_rgx.match(tag)

    @staticmethod
    def get_source_line_info(node: etree._Element):
        return "" if node.sourceline is None else "Line {}: ".format(node.sourceline)

    @classmethod
    def _get_class(cls, node):
        raise NotImplementedError("get_class method needs to be implemented")

    @staticmethod
    def create_element(parent, tag):
        if parent is not None:
            return etree.SubElement(parent, tag)
        return etree.Element(tag)

    @classmethod
    def load_attributes(cls, attributes, node, namespace=None):
        for attribute in attributes:
            node.attrib[cls.get_attr_name(namespace, attribute)] = str(attributes[attribute])

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
    def drop_attr(cls, node, attr, namespace=None):
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

    @classmethod
    def get_attr(cls, node, attr, namespace=None):
        return node.attrib.get(cls.get_attr_name(namespace, attr))

    @classmethod
    def is_equal(cls, node1, node2):
        """
        Compare two lxml nodes for equality. It checks for attribute equality,
        children and child order equality and tag name equality. Order of attributes
        does not matter
        :return: True if :param node1 is equal to :param node2
        """
        # if items are not nodes use default behaviour
        if not isinstance(node1, etree._Element) or not isinstance(node2, etree._Element):
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
