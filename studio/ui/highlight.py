# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import tkinter as tk


class WidgetHighlighter:
    OUTLINE = 2

    def __init__(self, master, style=None):
        style = master.winfo_toplevel().style if style is None else style
        color = style.colors.get("accent")
        h_force_visible = dict(relief="groove", bd=1)
        self.l = tk.Frame(master, bg=color, width=self.OUTLINE, **h_force_visible)
        self.r = tk.Frame(master, bg=color, width=self.OUTLINE, **h_force_visible)
        self.t = tk.Frame(master, bg=color, height=self.OUTLINE, **h_force_visible)
        self.b = tk.Frame(master, bg=color, height=self.OUTLINE, **h_force_visible)
        self.master = master
        self.elements = (self.l, self.r, self.t, self.b)

    def highlight(self, widget):
        x, y = widget.winfo_rootx() - self.master.winfo_rootx(), widget.winfo_rooty() - self.master.winfo_rooty()
        w, h = widget.winfo_width(), widget.winfo_height()
        self._draw(x, y, w, h)

    def _draw(self, x, y, w, h):
        self.l.place(x=x, y=y, height=h)
        self.r.place(x=x + w, y=y, height=h + self.OUTLINE)
        self.t.place(x=x, y=y, width=w)
        self.b.place(x=x, y=y + h, width=w + self.OUTLINE)
        for element in self.elements:
            element.lift()

    def highlight_bounds(self, bounds):
        x, y, w, h = bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]
        self._draw(x, y, w, h)

    def clear(self):
        for element in self.elements:
            element.place_forget()


class EdgeIndicator(tk.Frame):
    """
    Generates a conspicuous line at the edges of a widget for various indication purposes
    """

    def __init__(self, master, style=None):
        super().__init__(master)
        style = self.winfo_toplevel().style if style is None else style
        self.config(**style.bright_background, height=1, relief="groove", bd=1)

    def bottom(self, bounds):
        x, y = bounds[0], bounds[3]
        self.lift()
        self.place(x=x, y=y, height=1.5, width=bounds[2] - bounds[0])

    def top(self, bounds):
        x, y = bounds[:2]
        self.lift()
        self.place(x=x, y=y, height=1.5, width=bounds[2] - bounds[0])

    def right(self, bounds):
        x, y = bounds[2], bounds[3]
        self.lift()
        self.place(x=x, y=y, height=bounds[3] - bounds[1], width=1.5)

    def left(self, bounds):
        x, y = bounds[:2]
        self.place(x=x, y=y, height=bounds[3] - bounds[1], width=1.5)

    def clear(self):
        self.place_forget()