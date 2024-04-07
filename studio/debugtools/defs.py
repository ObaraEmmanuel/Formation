import tkinter
from dataclasses import dataclass, field


@dataclass
class Message:
    key: str
    payload: dict = field(default=None)


@dataclass
class WidgetMessage:
    id: str


def marshal(data):
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: marshal(v) for k, v in data.items()}
    if isinstance(data, list):
        return [marshal(v) for v in data]
    if isinstance(data, tuple):
        return tuple(marshal(v) for v in data)
    if isinstance(data, set):
        return {marshal(v) for v in data}
    if isinstance(data, (tkinter.Misc, RemoteWidget)):
        return WidgetMessage(data._w)
    if not isinstance(data, (str, int, float, bool, type, RemoteEvent, Exception)):
        return str(data)
    return data


def unmarshal(data, debugger):
    if isinstance(data, dict):
        return {k: unmarshal(v, debugger) for k, v in data.items()}
    if isinstance(data, list):
        return [unmarshal(v, debugger) for v in data]
    if isinstance(data, tuple):
        return tuple(unmarshal(v, debugger) for v in data)
    if isinstance(data, set):
        return {unmarshal(v, debugger) for v in data}
    if isinstance(data, WidgetMessage):
        return debugger.widget_from_message(data)
    return data


class RemoteEvent:

    def __init__(self, event):
        self.char = event.char
        self.delta = event.delta
        self.height = event.height
        self.keycode = event.keycode
        self.keysym = event.keysym
        self.keysym_num = event.keysym_num
        self.num = event.num
        self.send_event = event.send_event
        self.serial = event.serial
        self.state = event.state
        self.time = event.time
        self.type = event.type
        self.widget = None
        self.width = event.width
        self.x = event.x
        self.x_root = event.x_root
        self.y = event.y
        self.y_root = event.y_root


class RemoteWidget:

    def __init__(self, id_, debugger):
        self.id = id_
        self._name = self.id.split(".")[-1].strip("!") or "root"
        self.debugger = debugger
        self._dbg_node = None
        self._prop_map = {}
        self.deleted = False

    @property
    def _w(self):
        return self.id

    @_w.setter
    def _w(self, value):
        self.id = value

    @property
    def master(self):
        return self._get("master", cache=True)

    @property
    def _class(self):
        return self.debugger.transmit(
            Message("HOOK", payload={"meth": "extract_base_class", "args": (self,)}), response=True
        )

    @property
    def _dbg_ignore(self):
        return self._get("_dbg_ignore", cache=True)

    def _call(self, meth, *args, **kwargs):
        return self.debugger.transmit(
            Message("WIDGET", payload={"id": self.id, "meth": meth, "args": args, "kwargs": kwargs}), response=True
        )

    def _get(self, prop, cache=True):
        if cache and prop in self._prop_map:
            return self._prop_map[prop]
        result = self.debugger.transmit(
            Message("WIDGET", payload={"id": self.id, "get": prop}), response=True
        )
        if cache:
            self._prop_map[prop] = result
        return result

    def _set(self, prop, value):
        return self.debugger.transmit(
            Message("WIDGET", payload={"id": self.id, "set": prop, "value": value})
        )

    def configure(self, **kwargs):
        return self._call("configure", **kwargs)

    config = configure

    def __getitem__(self, item):
        return self._call("__getitem__", item)

    def __setitem__(self, key, value):
        return self._call("__setitem__", key, value)

    def get_prop(self, prop):
        prop = self[prop]
        if isinstance(prop, (tuple, list)):
            prop = " ".join(map(str, prop))
        return prop

    def keys(self):
        return self._call("keys")

    def winfo_children(self):
        return self._call("winfo_children")

    def winfo_parent(self):
        return self._call("winfo_parent")

    def nametowidget(self, name):
        return self.debugger.widget_from_message(WidgetMessage(name))

    def winfo_ismapped(self):
        return self._call("winfo_ismapped")

    def winfo_manager(self):
        return self._call("winfo_manager")

    def pack_info(self, **kwargs):
        return self._call("pack_info", **kwargs)

    def pack_configure(self, **kwargs):
        return self._call("pack_configure", **kwargs)

    def grid_info(self, **kwargs):
        return self._call("grid_info", **kwargs)

    def grid_configure(self, **kwargs):
        return self._call("grid_configure", **kwargs)

    def place_info(self, **kwargs):
        return self._call("place_info", **kwargs)

    def place_configure(self, **kwargs):
        return self._call("place_configure", **kwargs)

    def tab(self, tab_id, option=None, **kwargs):
        return self._call("tab", tab_id, option, **kwargs)

    def paneconfigure(self, tag, **kwargs):
        return self._call("paneconfigure", tag, **kwargs)

    paneconfig = paneconfigure

    def pane(self, tag, **kwargs):
        return self._call("pane", tag, **kwargs)
