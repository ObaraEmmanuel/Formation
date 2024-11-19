import json

from formation.formats._base import BaseFormat, Node


class ArrayEncoder(json.JSONEncoder):
    def encode(self, obj):
        def hint_arrays(item):
            if isinstance(item, tuple):
                return {'__tuple__': True, 'items': item}
            if isinstance(item, set):
                return {"__set__": True, "items": item}
            if isinstance(item, list):
                return [hint_arrays(e) for e in item]
            if isinstance(item, dict):
                return {key: hint_arrays(value) for key, value in item.items()}
            if not isinstance(item, (str, int, float, bool)):
                return str(item)
            else:
                return item

        return super(ArrayEncoder, self).encode(hint_arrays(obj))


def hinted_array_hook(obj):
    if '__tuple__' in obj:
        return tuple(obj['items'])
    if '__set__' in obj:
        return set(obj['items'])
    else:
        return obj


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

    def can_serialize(self, val):
        try:
            json.dumps(val)
            return True
        except (TypeError, OverflowError):
            return False

    def _normalize(self, attrib, stringify=False):
        for key in attrib:
            if isinstance(attrib[key], dict):
                attrib[key] = self._normalize(attrib[key], stringify)
            else:
                if stringify:
                    if isinstance(attrib[key], (list, tuple, set)):
                        attrib[key] = " ".join(map(str, attrib[key]))
                    else:
                        attrib[key] = str(attrib[key])
                elif isinstance(attrib[key], (list, tuple, set)):
                    attrib[key] = type(attrib[key])(map(lambda x: str(x) if not self.can_serialize(x) else x, attrib[key]))
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
                json_dat = json.load(file, object_hook=hinted_array_hook)
        else:
            json_dat = json.loads(self.data, object_hook=hinted_array_hook)
        self.root = self._load_node(None, json_dat)
        return self.root

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
        if not self._use_strings:
            return ArrayEncoder(**opt).encode(dict_data)
        return json.dumps(dict_data, **opt)
