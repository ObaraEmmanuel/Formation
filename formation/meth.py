from collections import defaultdict

from formation.formats._base import Node
from formation.handlers import parse_arg


def type_to_str(typ):
    if hasattr(typ, "__name__"):
        return typ.__name__
    return str(typ)


class Meth:
    __slots__ = ("args", "kwargs", "name", "defer")
    _deferred = defaultdict(list)

    def __init__(self, _name_, _deferred_=False, *args, **kwargs):
        self.name = _name_
        self.defer = _deferred_
        self.args = tuple(map(self.init_arg, args))
        self.kwargs = dict(kwargs)

        for k, v in self.kwargs.items():
            self.kwargs[k] = self.init_arg(v)

    def init_arg(self, arg):
        if isinstance(arg, (tuple, list, set)):
            if len(arg) >= 2:
                return arg
            else:
                return arg[0], None
        else:
            return arg, None

    def to_node(self, parent) -> Node:
        node = Node(parent, "meth", {"name": self.name})
        if self.defer:
            node.attrib.update(defer=True)

        for arg in self.args:
            val, typ, *_ = arg
            attr = {"value": val}
            if typ is not None:
                attr["type"] = type_to_str(typ)
            Node(node, "arg", attr)

        for name, arg in self.kwargs.items():
            val, typ, *_ = arg
            attr = {"name": name, "value": val}
            if typ is not None:
                attr["type"] = type_to_str(typ)
            Node(node, "arg", attr)

        return node

    def _call(self, func, with_name=False, parser=None):
        if parser is None:
            parser = parse_arg
        if with_name:
            func(self.name, *map(lambda v: parser(*v), self.args), **{k: parser(*v) for k, v in self.kwargs.items()})
        else:
            func(*map(lambda v: parser(*v), self.args), **{k: parser(*v) for k, v in self.kwargs.items()})

    def call(self, func, with_name=False, parser=None, context=None):
        if self.defer:
            Meth._deferred[context].append(lambda: self._call(func, with_name, parser))
        else:
            self._call(func, with_name, parser)

    def __eq__(self, other):
        return isinstance(other, Meth) and other.args == self.args and other.kwargs == self.kwargs

    def __ne__(self, other):
        return not self == other

    @classmethod
    def from_node(cls, node: Node) -> 'Meth':
        args = []
        kwargs = {}
        for arg_node in node:
            if "name" in arg_node.attrib:
                kwargs[arg_node.attrib["name"]] = (arg_node.attrib["value"], arg_node.attrib.get("type"))
            else:
                args.append((arg_node.attrib["value"], arg_node.attrib.get("type")))
        return cls(node.attrib["name"], node.attrib.get("defer", False), *args, **kwargs)

    @classmethod
    def call_deferred(cls, context=None):
        for meth in cls._deferred.pop(context, []):
            meth()
        cls._deferred.clear()
