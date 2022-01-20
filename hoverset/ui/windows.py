"""
Top level widgets and window implementations
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import tkinter as tk
from hoverset.platform import platform_is, MAC


class DragWindow(tk.Toplevel):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        if master:
            self.style = master.window.style
        self.window = self
        self.pos = (0, 0)
        self.overrideredirect(True)
        self.attributes("-alpha", 0.6)  # Default transparency
        if platform_is(MAC):
            # needed for macos to make window visible
            self.lift()

    def get_center(self):
        w, h, = self.winfo_width(), self.winfo_height()
        return self.pos[0] + int(w / 2), self.pos[1] + int(h / 2)

    def set_geometry(self, rec):
        self.geometry("{}x{}+{}+{}".format(*rec))
        return self

    def set_position(self, x, y):
        self.geometry(f"+{x}+{y}")
        self.pos = x, y
        return self

    def move(self, delta_x, delta_y):
        self.pos = (self.pos[0] + delta_x, self.pos[1] + delta_y)
        self.set_position(*self.pos)

    def set_transparency(self, alpha):
        self.attributes("-alpha", float(alpha))
