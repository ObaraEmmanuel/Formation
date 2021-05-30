"""
Top level widgets and window implementations
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import tkinter.tix as tix
from hoverset.platform import platform_is, MAC


class DragWindow(tix.Toplevel):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        if master:
            self.style = master.window.style
        self.window = self
        # self.transient(master.window)
        self.overrideredirect(True)
        self.attributes("-alpha", 0.6)  # Default transparency
        if platform_is(MAC):
            # needed for macos to make window visible
            self.lift()

    def set_geometry(self, rec):
        self.geometry("{}x{}+{}+{}".format(*rec))
        return self

    def set_position(self, x, y):
        x_offset = self.winfo_width() // 2
        self.geometry(f"+{x - x_offset}+{y}")
        return self

    def set_transparency(self, alpha):
        self.attributes("-alpha", float(alpha))
