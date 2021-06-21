import json

from formation.formats._base import BaseFormat, Node


class JSONFormat(BaseFormat):
    extensions = ["json"]
    name = "JSON"

    def __init__(self, data=None, path=None, node=None):
        super(JSONFormat, self).__init__(data, path, node)
        self._use_strings = True

    def _load_node(self, parent, data: dict) -> Node:
        node = Node(parent, data["type"], data.get("attrib"))
        for child in data.get("children", {}):
            self._load_node(node, child)
        return node

    def _normalize(self, attrib, stringify=False):
        for key in attrib:
            if isinstance(attrib[key], dict):
                attrib[key] = self._normalize(attrib[key], stringify)
            else:
                if stringify or not isinstance(attrib[key], (int, float, bool, type(None))):
                    attrib[key] = str(attrib[key])
        return attrib

    def _to_dict(self, node: Node) -> dict:
        attrib = self._normalize(node.attrib, self._use_strings)
        obj = {
            "type": node.type,
            "attrib": attrib,
        }
        if node.children:
            obj["children"] = list(map(self._to_dict, node.children))
        return obj

    def load(self):
        if self.path:
            with open(self.path, "rb") as file:
                json_dat = json.load(file)
        else:
            json_dat = json.loads(self.data)
        self._root = self._load_node(None, json_dat)
        return self._root

    def generate(self, **kw):
        self._use_strings = kw.get("stringify_values", True)
        dict_data = self._to_dict(self.root)
        compact = kw.get("compact", False)
        opt = {
            "separators": (",", ":") if compact else (", ", ": "),
            "sort_keys": kw.get("sort_keys", True)
        }
        if kw.get("pretty_print"):
            indent = kw.get("indent", "")
            opt["indent"] = kw.get("indent_count", 4) if indent == "" else indent
        return json.dumps(dict_data, **opt)
