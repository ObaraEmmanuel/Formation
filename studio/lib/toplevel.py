# ======================================================================= #
# Copyright (c) 2022 Hoverset Group.                                      #
# ======================================================================= #

import tkinter as tk

from hoverset.data.images import get_tk_image
from studio.lib.pseudo import Groups, Container, _ImageIntercept
from studio.ui.geometry import parse_geometry

from formation.meth import Meth

WINDOW_DEF = {
    # geometry
    "geometry": {
        "display_name": "geometry",
        "type": "text",
        "handler": "_geometry",
    },
    "iconphoto": {
        "display_name": "icon photo",
        "type": "icon_photo",
        "handler": "_iconphoto",
        "compose": [
            {
                "display_name": "image",
                "name": "image",
                "type": "image",
            },
            {
                "display_name": "default",
                "name": "default",
                "type": "boolean",
            },
        ]
    },
    "iconbitmap": {
        "display_name": "icon bitmap",
        "type": "bitmap",
        "handler": "_iconbitmap"
    },
    "maxsize": {
        "display_name": "maximum size",
        "type": "width_height",
        "handler": "_maxsize",
        "compose": [

            {
                "display_name": "width",
                "name": "width",
                "type": "dimension",
            },
            {
                "display_name": "height",
                "name": "height",
                "type": "dimension",
            }

        ]
    },
    "minsize": {
        "display_name": "minimum size",
        "type": "width_height",
        "handler": "_minsize",
        "compose": [

            {
                "display_name": "width",
                "name": "width",
                "type": "dimension",
            },
            {
                "display_name": "height",
                "name": "height",
                "type": "dimension",
            }

        ]
    },
    "overrideredirect": {
        "display_name": "override redirect",
        "type": "boolean",
        "handler": "_overrideredirect",
    },
    "resizable": {
        "display_name": "resizable",
        "type": "window_resize",
        "handler": "_resizable",
        "compose": [
            [
                {
                    "display_name": "width",
                    "name": "width",
                    "type": "boolean",
                },
                {
                    "display_name": "height",
                    "name": "height",
                    "type": "boolean",
                }
            ]
        ]
    },
    "title": {
        "display_name": "title",
        "type": "text",
        "handler": "_title",
    },
}


def _entangle(master, slave):
    if master == slave:
        return
    widget_conf = master.configure
    widget_set = master.__setitem__

    def _hook_conf(*args, **kw):
        ret = widget_conf(*args, **kw)
        try:
            slave.configure(*args, **kw)
        except:
            pass
        return ret

    def _hook_set(key, value):
        widget_set(key, value)
        try:
            slave[key] = value
        except:
            pass

    setattr(master, "configure", _hook_conf)
    setattr(master, "config", _hook_conf)
    setattr(master, "__setitem__", _hook_set)


def _menu_hook(menu, callback):
    menu_add = menu.add
    menu_delete = menu.delete

    # noinspection PyPep8Naming
    def _add_hook(itemType, cnf=None, **kw):
        menu_add(itemType, cnf or {}, **kw)
        callback()

    def _delete_hook(index1, index2=None):
        menu_delete(index1, index2)
        callback()

    def _clear_hooks():
        setattr(menu, "add", menu_add)
        setattr(menu, "delete", menu_delete)
        delattr(menu, "_clear_hooks")

    setattr(menu, "add", _add_hook)
    setattr(menu, "delete", _delete_hook)
    setattr(menu, "_clear_hooks", _clear_hooks)


class _Toplevel(tk.Frame):
    _images = None

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.title = tk.Frame(self, height=30)
        self.title.grid(row=0, column=0, sticky='ew')

        self._menu = None

        if self._images is None:
            self._images = (
                get_tk_image("close", 15, 15, color="#303030"),
                get_tk_image("minimize", 15, 15, color="#000000"),
                get_tk_image("maximize", 10, 10, color="#303030"),
                get_tk_image("formation", 20, 20)
            )

        self.label = tk.Label(
            self.title, text="  title", image=self._images[3], compound="left")
        self.label.pack(side="left", padx=5, pady=5)

        tk.Label(self.title, image=self._images[0]).pack(side="right", padx=10, pady=5)
        tk.Label(self.title, image=self._images[2]).pack(side="right", padx=10, pady=5)
        tk.Label(self.title, image=self._images[1]).pack(side="right", padx=10, pady=5)

        # body has to be sibling of toplevel for positioning to work
        self._window = window = tk.Frame(self, container=True)
        window.winfo_parent = lambda: str(self)
        window.grid(row=1, column=0, sticky='nswe')

        embed_class = getattr(self, "embed_class", tk.Toplevel)
        self._toplevel = embed_class(master, use=window.winfo_id())

        # get system default maxsize before toplevel is modified
        maxsize = self._toplevel.maxsize()
        self._fixed_maxsize = {"width": maxsize[0], "height": maxsize[1]}

        self._toplevel_state = {}
        self._geom_is_setup = False

        self._title("title")
        self._geometry_pos = 0, 0
        self._shadow = tk.Frame(self._toplevel)
        self._shadow.pack(fill='both', expand=True)
        self._shadow_h = self._shadow.winfo_height()
        embed_frame = getattr(self, "embed_frame_class", tk.Frame)
        self.body = embed_frame(master)
        self.body.place(in_=self, anchor='se', relx=1, rely=1, relwidth=1, relheight=1, height=-30)

        # lock toplevel and body so changes are mirrored to body
        _entangle(self._toplevel, self.body)
        # make body and toplevel appear as child to self
        self._toplevel.winfo_parent = lambda: str(self)
        self.body.winfo_parent = lambda: str(self)

        self.window_props = self._get_props()
        self.setup_widget()

    def _get_props(self):
        props = dict(WINDOW_DEF)

        for key, val in props.items():
            val["func"] = getattr(self, val["handler"])
            val["name"] = key

        return props

    def window_definition(self):
        for key, val in self.window_props.items():
            val["value"] = val["func"]()
        return self.window_props

    def set_win_prop(self, prop, value, *args):
        self.window_props[prop]["func"](value, *args)

    def get_win_prop(self, prop):
        return self.window_props[prop]["func"]()

    def keys(self):
        return self._toplevel.keys()

    def _perturb(self):
        # force slight size change so the toplevel menu can be rendered
        w = self.winfo_width()
        self.master.config_child(self, width=w + 1)
        self.master.config_child(self, width=w)

    def _adjust_for_menu(self, _=None):
        self._perturb()
        # update_idletasks not strong enough to update the nested toplevel
        # let's force things with update
        self._shadow.update()
        if not self._overrideredirect():
            self.body.place_configure(height=-(self._shadow.winfo_rooty() - self.winfo_rooty()))
        else:
            self.body.place_configure(height=0)

    def configure(self, **kwargs):
        tk.Menu().add_cascade()
        conf = self._toplevel.configure(**kwargs)
        if "menu" in kwargs:
            # set up hooks so we can monitor the toplevel menu state and
            # adjust body position accordingly.
            self._adjust_for_menu()
            if kwargs['menu']:
                if hasattr(self._menu, '_clear_hooks'):
                    self._menu._clear_hooks()
                self._menu = kwargs['menu']
                _menu_hook(self._menu, self._adjust_for_menu)
            else:
                if hasattr(self._menu, '_clear_hooks'):
                    self._menu._clear_hooks()
                    self._menu = self._menu_bind = None
        return conf

    config = configure

    def __getitem__(self, item):
        return self._toplevel[item]

    def __setitem__(self, key, value):
        self.configure(**{key: value})

    def cget(self, key):
        return self._toplevel.cget(key)

    def set_name(self, name):
        self.label["text"] = f"  {name}"

    def bind(self, sequence=None, func=None, add=None):
        super(_Toplevel, self).bind(sequence, func, add)
        self.body.bind(sequence, func, add)

    def _geometry(self, val=None):
        if val is None:
            return (
                f"{self._toplevel.winfo_width()}x{self._toplevel.winfo_height()}"
                f"+{self._geometry_pos[0]}+{self._geometry_pos[1]}"
            )

        # ignore the first _geometry call
        if not self._geom_is_setup:
            self._geom_is_setup = True
            return

        geom = parse_geometry(val)
        if geom is None:
            return

        if geom["width"] is not None:
            self.layout.apply("width", geom["width"], self)

        if geom["height"] is not None:
            diff = self.winfo_height() - self._toplevel.winfo_height()
            self.layout.apply(
                "height",
                int(geom["height"]) + diff,
                self
            )

        if None not in (geom["x"], geom["y"]):
            self._geometry_pos = (geom["x"], geom["y"])

    def _overrideredirect(self, val=None):
        if val is None:
            return self._toplevel_state.get("overrideredirect", False)
        self._toplevel_state["overrideredirect"] = val

        if val:
            self.title.grid_forget()
        else:
            self.title.grid(row=0, column=0, sticky='ew')
        self._adjust_for_menu()

    def _iconbitmap(self, val=None):
        if val is None:
            return self._toplevel.wm_iconbitmap()
        self._toplevel.wm_iconbitmap(val)
        self.label["image"] = ""
        self.label["bitmap"] = val

    def _iconphoto(self, val=None, *args):
        if val is None:
            return {
                "image": _ImageIntercept.get(self.label),
                "default": self._toplevel_state.get("iconphoto_default", True)
            }
        if args:
            val = {"default": val, "image": args[0]}

        _ImageIntercept.set(self.label, val["image"], width=20, height=20)
        self._toplevel_state["iconphoto_default"] = val["default"]

    def _title(self, val=None):
        if val is None:
            return self._toplevel_state.get("title", "")
        self.label["text"] = "  " + str(val)
        self._toplevel_state["title"] = val

    def _resizable(self, val=None):
        if val is None:
            w, h = self._toplevel.resizable()
            return {"width": w, "height": h}
        self._toplevel.resizable(val.get("width", False), val.get("height", False))

    def _maxsize(self, val=None):
        if val is None:
            w, h = self._toplevel.maxsize()
            return {"width": w, "height": h}
        w, h = val.get("width", False), val.get("height", False)
        if '' in (w, h):
            return
        self._toplevel.maxsize(w, h)
        self.max_size = list(self._toplevel.maxsize())
        # compensate for title bar
        self.max_size[1] += self.winfo_height() - self._toplevel.winfo_height()

    def _minsize(self, val=None):
        if val is None:
            w, h = self._toplevel.minsize()
            return {"width": w, "height": h}
        w, h = val.get("width", False), val.get("height", False)
        if '' in (w, h):
            return
        self._toplevel.minsize(w, h)
        self.min_size = list(self._toplevel.minsize())
        # compensate for title bar
        self.min_size[1] += self.winfo_height() - self._toplevel.winfo_height()

    def get_window_method_defaults(self):
        return dict(
            title=Meth("title", False, None),
            geometry=Meth("geometry", False, None),
            resizable=Meth("resizable", width=(1, int), height=(1, int)),
            iconbitmap=Meth("iconbitmap", False, ''),
            iconphoto=Meth("iconphoto", False, (1, int), ('', "image")),
            overrideredirect=Meth("overrideredirect", False, (0, int)),
            minsize=Meth("minsize", False, width=1, height=1),
            maxsize=Meth("maxsize", False, **self._fixed_maxsize)
        )

    def get_window_methods(self):
        resizable = self._toplevel.resizable()
        iconphoto = self._iconphoto()
        return [
            Meth("title", False, self._title()),
            Meth("geometry", False, self._geometry()),
            Meth("resizable", False, width=(resizable[0], int), height=(resizable[1], int)),
            Meth("iconbitmap", True, self._iconbitmap()),
            Meth(
                "iconphoto", True,
                (int(iconphoto["default"]), int),
                (iconphoto["image"], "image")
            ),
            Meth("overrideredirect", False, (int(bool(self._overrideredirect())), int)),
            Meth("minsize", False, **self._minsize()),
            Meth("maxsize", False, **self._maxsize())
        ]

    def handle_window_method(self, name, *args, **kwargs):
        if kwargs:
            self.set_win_prop(name, kwargs)
        else:
            self.set_win_prop(name, *args)


class ToplevelContainer(Container):

    # reroute methods to _Toplevel

    def get_methods(self):
        return self.get_window_methods()

    def get_method_defaults(self):
        return self.get_window_method_defaults()

    def handle_method(self, name, *args, **kwargs):
        return self.handle_window_method(name, *args, **kwargs)


class Toplevel(ToplevelContainer, _Toplevel):
    group = Groups.container
    icon = 'window'
    is_toplevel = True
    is_container = True
    display_name = 'Toplevel'
    embed_class = tk.Toplevel
    impl = tk.Toplevel
    initial_dimensions = 200, 230


class Tk(ToplevelContainer, _Toplevel):
    group = Groups.container
    icon = 'window'
    is_toplevel = True
    is_container = True
    display_name = 'Tk'
    embed_class = tk.Toplevel
    impl = tk.Tk
    initial_dimensions = 200, 230
