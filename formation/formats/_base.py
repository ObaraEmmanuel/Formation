"""
Base output and input format abstractions
"""
# ======================================================================= #
# Copyright (c) 2021 Hoverset Group.                                      #
# ======================================================================= #

import abc
import re
from collections import defaultdict


_tag_rgx = re.compile(r"(.+)\.([^.]+)")
_var_rgx = re.compile(r".+Var$")


__all__ = ("Node", "BaseAdapter", "BaseFormat")


class Node:

    __slots__ = ("parent", "attrib", "source_line", "children", "type")

    def __init__(self, parent, node_type, attrib=None):
        self.parent = parent
        self.source_line = None
        self.attrib = defaultdict(dict)
        self.attrib.update(attrib or {})
        self.children = []
        self.type = node_type

        if isinstance(parent, Node):
            parent.append_child(self)

    def is_var(self):
        return _var_rgx.match(self.type)

    def get_source_line_info(self):
        return "" if self.source_line is None else "Line {}: ".format(self.source_line)

    def remove_attrib(self, attrib, namespace):
        if attrib in self.attrib.get(namespace, {}):
            self.attrib[namespace].pop(attrib)

    def append_child(self, child):
        self.children.append(child)

    def get_mod_impl(self):
        match = _tag_rgx.search(self.type)
        if match:
            return match.groups()
        raise SyntaxError("Malformed type {}".format(self.type))

    def __getitem__(self, item):
        return self.attrib[item]

    def __setitem__(self, key, value):
        self.attrib[key] = value

    def __len__(self):
        return len(self.children)

    def __iter__(self):
        return iter(self.children)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False

        tag_eq = self.type == other.type
        attrib_eq = self._flatten(self.attrib) == self._flatten(other.attrib)
        child_eq = len(self) == len(other)
        # if any of the above is false no need to even check further
        if child_eq and tag_eq and attrib_eq:
            for sub_node1, sub_node2 in zip(self, other):
                child_eq = sub_node1 == sub_node2
                # if the equality check fails break immediately
                if sub_node1 != sub_node2:
                    return False
        return tag_eq and attrib_eq and child_eq

    def _flatten(self, dictionary):
        if isinstance(dictionary, dict):
            for k in list(dictionary):
                # skip empty dictionary values
                if isinstance(dictionary[k], dict) and not dictionary[k]:
                    dictionary.pop(k)
                    continue
                dictionary[k] = self._flatten(dictionary[k])
            return dict(dictionary)
        return str(dictionary)


class BaseAdapter(abc.ABC):

    @abc.abstractmethod
    def load(self, node, builder, parent):
        pass

    def generate(self, widget, parent):
        pass


class BaseFormat(abc.ABC):

    extensions = []
    name = None

    def __init__(self, data=None, path=None, node=None):
        self.data = data
        self.path = path
        self.root = node
        if (path, data, node) == (None, None, None):
            raise ValueError("You must provide an input file, string or node")

    def open(self):
        if self.path is not None:
            with open(self.path, "r") as file:
                self.data = file.read()
        return self.data

    @abc.abstractmethod
    def load(self):
        pass

    @abc.abstractmethod
    def generate(self, **kw):
        pass
