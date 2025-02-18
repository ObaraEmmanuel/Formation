import tkinter
from dataclasses import dataclass, field

import studio.lib.menu as menu_lib
import studio.lib.canvas as canvas_lib
from studio.debugtools.common import get_studio_equiv, get_root_id


@dataclass
class Message:
    key: str
    payload: dict = field(default=None)


@dataclass
class WidgetMessage:
    id: str
    root: int = 0


def marshal(data, hook=None):
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: marshal(v, hook) for k, v in data.items()}
    if isinstance(data, list):
        return [marshal(v, hook) for v in data]
    if isinstance(data, tuple):
        return tuple(marshal(v, hook) for v in data)
    if isinstance(data, set):
        return {marshal(v, hook) for v in data}
    if isinstance(data, tkinter.Misc):
        return WidgetMessage(data._w, get_root_id(data, hook))
    if isinstance(data, RemoteWidget):
        return WidgetMessage(data._w, data.root)
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


class RemoteCanvasItem:
    DEF_OVERRIDES = dict(canvas_lib.CANVAS_PROPERTIES)
    _item_type_map = {
        "arc": canvas_lib.Arc,
        "bitmap": canvas_lib.Bitmap,
        "image": canvas_lib.Image,
        "line": canvas_lib.Line,
        "oval": canvas_lib.Oval,
        "polygon": canvas_lib.Polygon,
        "rectangle": canvas_lib.Rectangle,
        "text": canvas_lib.Text,
        "window": canvas_lib.Window,
    }

    def __init__(self, canvas, item_id):
        self.canvas = canvas
        self.item_id = item_id
        self._attr_cache = None
        self._name = None
        self._equiv_class = None
        self.deleted = False
        self._dbg_node = None
        self.extra_items = []
        self._class = RemoteCanvasItem

    @property
    def id(self):
        return f"{self.canvas.id}!{self.item_id}"

    @property
    def equiv_class(self):
        if self._equiv_class is None:
            self._equiv_class = self._item_type_map.get(self.type(), canvas_lib.CanvasItem)
        return self._equiv_class

    @property
    def name(self):
        if self._name is None:
            self._name = f"{self.type()}_{self.item_id}"
        return self._name

    def _call(self, meth, *args, **kwargs):
        return self.canvas.debugger.transmit(
            Message(
                "WIDGET",
                payload={
                    "id": self.canvas.id,
                    "root": self.canvas.root,
                    "meth": meth,
                    "args": (self.item_id, *args),
                    "kwargs": kwargs,
                }
            ), response=True
        )

    def configure(self, **kwargs):
        ret = self._call("itemconfigure", **kwargs)
        if not kwargs and isinstance(ret, dict):
            self._attr_cache = {k: v[-1] if isinstance(v, (tuple, list, set)) else v for k, v in ret.items()}
        return ret

    config = configure

    def cget(self, key):
        if self._attr_cache is not None:
            if key in self._attr_cache:
                return self._attr_cache[key]
        return self._call("itemcget", key)

    __getitem__ = cget

    def __setitem__(self, key, value):
        return self._call("itemconfigure", key, value)

    def invalidate_conf(self):
        self._attr_cache = None

    def type(self):
        return self._call("type")

    def winfo_children(self):
        return []

    def winfo_ismapped(self):
        return False


class RemoteMenuItem:

    _pool = []
    DEF_OVERRIDES = dict(menu_lib.MENU_PROPERTY_TABLE)
    _item_type_map = {
        "command": menu_lib.Command,
        "cascade": menu_lib.Cascade,
        "checkbutton": menu_lib.CheckButton,
        "radiobutton": menu_lib.RadioButton,
        "separator": menu_lib.Separator,
    }

    def __init__(self, menu, index):
        self.menu = menu
        self.index = index
        self.deleted = False
        self._dbg_node = None
        self._name = None
        self._equiv_class = None
        self._attr_cache = None
        self._class = RemoteMenuItem
        self.menu_items = []
        self.extra_items = []

    @property
    def id(self):
        return f"{self.menu.id}!{self.index}"

    @property
    def equiv_class(self):
        if self._equiv_class is None:
            self._equiv_class = self._item_type_map.get(self.type(), menu_lib.MenuItem)
        return self._equiv_class

    @property
    def name(self):
        if self._name is None:
            if self.type() == "separator":
                self._name = "Separator"
            elif self.type() == "cascade":
                menu = self.cget("menu")
                if menu:
                    menu = self.menu.debugger.widget_from_message(WidgetMessage(menu))
                    self._name = f"{self.cget('label')} > [{menu._name}]"
                else:
                    self._name = self.cget("label")
            else:
                self._name = self.cget("label")
        return self._name

    def _call(self, meth, *args, **kwargs):
        return self.menu.debugger.transmit(
            Message(
                "WIDGET",
                payload={
                    "id": self.menu.id,
                    "root": self.menu.root,
                    "meth": meth,
                    "args": args,
                    "kwargs": kwargs,
                    "index": self.index,  # special for menu items to allow tear-off compensation on hook side
                }
            ), response=True
        )

    def configure(self, **kwargs):
        ret = self._call("entryconfigure", **kwargs)
        if not kwargs and isinstance(ret, dict):
            self._attr_cache = {k: v[-1] if isinstance(v, (tuple, list, set)) else v for k, v in ret.items()}
        return ret

    config = configure

    def cget(self, key):
        if self._attr_cache is not None:
            if key in self._attr_cache:
                return self._attr_cache[key]
        return self._call("entrycget", key)

    __getitem__ = cget

    def __setitem__(self, key, value):
        return self._call("entryconfigure", key, value)

    def invalidate_conf(self):
        self._attr_cache = None

    def type(self):
        return self._call("type")

    def winfo_children(self):
        return []

    def winfo_ismapped(self):
        return False

    def release(self):
        self.menu = None
        self.index = None
        self.deleted = True
        self._name = None
        self._equiv_class = None
        self._pool.append(self)

    @classmethod
    def acquire(cls, menu, index):
        if cls._pool:
            item = cls._pool.pop()
            item.menu = menu
            item.index = index
            item.deleted = False
            return item
        return cls(menu, index)


class RemoteWidget:

    def __init__(self, id_, debugger, root=0):
        self.id = id_
        self.debugger = debugger
        self._dbg_node = None
        self._prop_map = {}
        self._attr_cache = None
        self._menu_items = None
        self._canvas_items = None
        self.deleted = False
        self.root = root
        self._equiv_class = None
        if self.id == '.':
            self._name = self._true_class_name
        else:
            self._name = self.id.split(".")[-1].strip("!") or "<unnamed>"

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
    def equiv_class(self):
        if self._equiv_class is None:
            self._equiv_class = get_studio_equiv(self)
        return self._equiv_class

    @property
    def _true_class_name(self):
        return self.debugger.transmit(
            Message("HOOK", payload={"meth": "extract_true_class_name", "args": (self,)}), response=True
        )

    @property
    def _dbg_ignore(self):
        return self._get("_dbg_ignore", cache=True)

    def _call(self, meth, *args, **kwargs):
        return self.debugger.transmit(
            Message(
                "WIDGET",
                payload={"id": self.id, "root": self.root, "meth": meth, "args": args, "kwargs": kwargs}
            ), response=True
        )

    def _get(self, prop, cache=True):
        if cache and prop in self._prop_map:
            return self._prop_map[prop]
        result = self.debugger.transmit(
            Message("WIDGET", payload={"id": self.id, "root": self.root, "get": prop}), response=True
        )
        if cache:
            self._prop_map[prop] = result
        return result

    def _set(self, prop, value):
        return self.debugger.transmit(
            Message("WIDGET", payload={"id": self.id, "root": self.root, "set": prop, "value": value})
        )

    def configure(self, **kwargs):
        ret = self._call("configure", **kwargs)
        if ret is None and not kwargs:
            # fallback if configure behaviour is not implemented correctly
            ret = self._configure()
        if not kwargs and isinstance(ret, dict):
            self._attr_cache = {k: v[-1] if isinstance(v, (tuple, list, set)) else v for k, v in ret.items()}
        return ret

    def invalidate_conf(self):
        self._attr_cache = None

    def _configure(self, cmd="configure", cnf=None, kw=None):
        return self._call("_configure", cmd, cnf, kw)

    config = configure

    def __getitem__(self, item):
        if self._attr_cache is not None:
            if item in self._attr_cache:
                return self._attr_cache[item]
        return self._call("__getitem__", item)

    def __setitem__(self, key, value):
        return self._call("__setitem__", key, value)

    def get_prop(self, prop):
        prop = self[prop]
        if isinstance(prop, (tuple, list)):
            prop = " ".join(map(str, prop))
        return prop

    def _init_menu_items(self):
        index = self.index(tkinter.END)
        if index is None:
            index = -1
        if not self["tearoff"] and index >= 0:
            index += 1
        index = max(0, index)
        self._menu_items = [RemoteMenuItem.acquire(self, i) for i in range(index)]

    def _add_menu_item(self, index):
        if self._menu_items is None:
            return
        item = RemoteMenuItem.acquire(self, index)
        self._menu_items.insert(index, item)
        # adjust index for all following items
        for i in range(index + 1, len(self._menu_items)):
            self._menu_items[i].index = i
        return item

    def _remove_menu_items(self, start, end):
        if self._menu_items is None:
            return
        removed = []
        for i in range(start, min(end+1, len(self._menu_items))):
            removed.append(self._menu_items[i])

        for item in removed:
            self._menu_items.remove(item)
            item.release()

        # adjust index for all following items
        for i in range(end + 1, len(self._menu_items)):
            self._menu_items[i].index = i

        return removed

    @property
    def menu_items(self):
        if self._class != tkinter.Menu:
            return []
        if self._menu_items is None:
            self._init_menu_items()
        return self._menu_items

    def _init_canvas_items(self):
        self._canvas_items = {i: RemoteCanvasItem(self, i) for i in self.find_all()}

    def get_canvas_item_from_id(self, item_id):
        if self._canvas_items is None:
            self._init_canvas_items()
        return self._canvas_items.get(item_id)

    def delete_canvas_ids(self, *ids):
        if self._canvas_items is None:
            return []
        removed = []
        for id in ids:
            item = self._canvas_items.pop(int(id), None)
            if item:
                item.deleted = True
                removed.append(item)
        return removed

    def add_canvas_item(self, id):
        if not self._canvas_items:
            self._canvas_items = {}
        if id in self._canvas_items:
            return self._canvas_items[id]
        item = RemoteCanvasItem(self, id)
        self._canvas_items[id] = item
        return item

    @property
    def canvas_items(self):
        if self._class != tkinter.Canvas:
            return []
        if self._canvas_items is None:
            self._init_canvas_items()
        return list(self._canvas_items.values())

    @property
    def extra_items(self):
        if self._class == tkinter.Menu:
            return self.menu_items
        if self._class == tkinter.Canvas:
            return self.canvas_items
        return []

    def find_all(self):
        return self._call("find_all")

    def keys(self):
        return self._call("keys")

    def winfo_children(self):
        return self._call("winfo_children")

    def winfo_parent(self):
        return self._call("winfo_parent")

    def nametowidget(self, name):
        return self.debugger.widget_from_message(WidgetMessage(name, root=self.root))

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

    def index(self, index):
        return self._call("index", index)

    paneconfig = paneconfigure

    def pane(self, tag, **kwargs):
        return self._call("pane", tag, **kwargs)
