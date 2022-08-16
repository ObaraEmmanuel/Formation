# ======================================================================= #
# Copyright (c) 2022 Hoverset Group.                                      #
# ======================================================================= #

import tkinter as tk

from hoverset.data.images import get_tk_image
from studio.lib.pseudo import Groups, Container


class _Toplevel(tk.Frame):
    impl = tk.Toplevel
    _images = None

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.title = tk.Frame(self, height=30)
        self.title.grid(row=0, column=0, sticky='ew')

        if self._images is None:
            self._images = (
                get_tk_image("close", 15, 15, color="#303030"),
                get_tk_image("minimize", 15, 15, color="#000000"),
                get_tk_image("rectangle", 10, 10, color="#000000"),
                get_tk_image("formation", 15, 15)
            )

        self.label = tk.Label(
            self.title, text="  title", image=self._images[3], compound="left")
        self.label.pack(side="left", padx=5, pady=5)

        tk.Label(self.title, image=self._images[0]).pack(side="right", padx=10, pady=5)
        tk.Label(self.title, image=self._images[2]).pack(side="right", padx=10, pady=5)
        tk.Label(self.title, image=self._images[1]).pack(side="right", padx=10, pady=5)

        # body has to be sibling of toplevel for positioning to work
        body = tk.Frame(master, bg="#bbbbbb", container=True)
        body.winfo_parent = lambda: str(self)
        body.grid(in_=self, row=1, column=0, sticky='nswe')

        # embed an actual toplevel widget
        if issubclass(self.impl, tk.Toplevel):
            self._toplevel = self.impl(master, use=body.winfo_id())
        else:
            self._toplevel = self.impl(use=str(body.winfo_id()))
        # make body appear as child to toplevel
        self._toplevel.winfo_parent = lambda: str(self)
        self._toplevel.configure(bg="#bbbbbb")

        self.setup_widget()
        self.body = self._toplevel

    def keys(self):
        return self._toplevel.keys()

    def configure(self, **kwargs):
        conf = self._toplevel.configure(**kwargs)
        if "menu" in kwargs:
            self.update_idletasks()
        return conf

    config = configure

    def __getitem__(self, item):
        return self._toplevel[item]

    def __setitem__(self, key, value):
        self._toplevel[key] = value

    def cget(self, key):
        return self._toplevel.cget(key)

    def set_name(self, name):
        self.label["text"] = f"  {name}"

    def bind(self, sequence=None, func=None, add=None):
        super(_Toplevel, self).bind(sequence, func, add)
        self._toplevel.bind(sequence, func, add)


class Toplevel(Container, _Toplevel):
    group = Groups.container
    icon = 'window'
    is_toplevel = True
    display_name = 'Toplevel'
    impl = tk.Toplevel


class Tk(Container, _Toplevel):
    group = Groups.container
    icon = 'window'
    is_toplevel = True
    display_name = 'Tk'
    impl = tk.Tk
