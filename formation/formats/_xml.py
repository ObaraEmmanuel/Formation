# ======================================================================= #
# Copyright (C) 2021 Hoverset Group.                                      #
# ======================================================================= #

import re
from collections import defaultdict

try:
    from lxml import etree
    element_class = etree._Element
except ModuleNotFoundError:
    # use default xml library; features may be limited
    import xml.etree.ElementTree as etree
    element_class = etree.Element

from formation.formats._base import BaseFormat, Node

namespaces = {
    "layout": "http://www.hoversetformationstudio.com/layouts/",
    "attr": "http://www.hoversetformationstudio.com/styles/",
    "menu": "http://www.hoversetformationstudio.com/menu",
}
_reversed_namespaces = dict(zip(namespaces.values(), namespaces.keys()))
_attr_rgx = re.compile(r"{(?P<namespace>.+)}(?P<attr>.+)")


def _register_namespaces():
    for k in namespaces:
        etree.register_namespace(k, namespaces[k])


_register_namespaces()


class XMLFormat(BaseFormat):

    extensions = ("xml", )
    name = "XML"

    def _load_node(self, parent, x_node: element_class):
        grouped = defaultdict(dict)
        # add required fields
        for attr in x_node.attrib:
            match = _attr_rgx.search(attr)
            if match:
                group = _reversed_namespaces.get(match.group("namespace"))
                grouped[group][match.group("attr")] = x_node.attrib.get(attr)
            else:
                grouped[attr] = x_node.attrib.get(attr)

        node = Node(parent, x_node.tag, grouped)
        if hasattr(x_node, "sourceline"):
            node.source_line = x_node.sourceline
        for sub_node in x_node:
            self._load_node(node, sub_node)

        return node

    def _generate_node(self, parent, node: Node):
        if parent is None:
            x_node = etree.Element(node.type)
        else:
            x_node = etree.SubElement(parent, node.type)

        for key in node.attrib:
            if isinstance(node.attrib[key], dict):
                ns = node.attrib[key]
                for attrib in ns:
                    attr = "{{{}}}{}".format(namespaces.get(key), attrib)
                    x_node.attrib[attr] = str(ns[attrib])
            else:
                x_node.attrib[key] = str(node.attrib[key])

        for sub_node in node:
            self._generate_node(x_node, sub_node)

        return x_node

    def load(self):
        if self.path:
            with open(self.path, "rb") as file:
                x_node = etree.parse(file).getroot()
        else:
            x_node = etree.fromstring(self.data)
        self.root = self._load_node(None, x_node)
        return self.root

    def generate(self, **kw):
        x_node = self._generate_node(None, self.root)
        etree.cleanup_namespaces(x_node, top_nsmap=namespaces)
        return etree.tostring(
            x_node, pretty_print=kw.get("pretty_print", True),
            encoding="utf-8", xml_declaration=kw.get("xml_declaration", True)
        ).decode('utf-8')


if __name__ == "__main__":
    x = XMLFormat(path="formation/tests/samples/all_legacy.xml")
    x.load()
