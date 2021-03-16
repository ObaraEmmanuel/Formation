"""
An assortment of common input pickers.
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import hoverset.util.color as color
import hoverset.ui.panels as panels
from hoverset.data.utils import get_resource_path
from hoverset.ui.widgets import *


with open(get_resource_path("hoverset.ui", "color.tcl"), encoding='utf-8') as tcl:
    tcl_proc = tcl.read()


# Inspired by python pynche color chooser by Barry A. Warsaw, bwarsaw@python.org
class _Spectrum(Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        if not hasattr(self.window, "__has_color_proc"):
            # Load tcl procedures only once to access fast recolor functions
            self.window.tk.eval(tcl_proc)
            self.window.__has_color_proc = True
        self.config(**self.style.surface)
        self.callback, self.implicit_callback = None, None
        self.pos = 0, 0
        self.bind("<Left>", lambda e: self._adjust(EventWrap(None, None, self.pos[0] - 1, self.pos[1]), 0, 0))
        self.bind("<Right>", lambda e: self._adjust(EventWrap(None, None, self.pos[0] + 1, self.pos[1]), 0, 0))
        self.bind("<Up>", lambda e: self._adjust(EventWrap(None, None, self.pos[0], self.pos[1] - 1), 0, 0))
        self.bind("<Down>", lambda e: self._adjust(EventWrap(None, None, self.pos[0], self.pos[1] + 1), 0, 0))

    def _drag_start(self, event):
        self.focus_set()

    def on_change(self, callback, *args, **kwargs):
        self.callback = lambda c: callback(c, *args, **kwargs)

    def on_implicit_change(self, callback, *args, **kwargs):
        self.implicit_callback = lambda c: callback(c, *args, **kwargs)

    def get(self):
        raise NotImplementedError("Get method is required")

    def set(self, x_frac, y_frac=None):
        raise NotImplementedError("Set method is required")

    def _adjust(self, event=None, x=None, y=None):
        raise NotImplementedError("Adjustment method is required")


class _ColorStrip(_Spectrum):

    def __init__(self, master=None, color_array=None, **cnf):
        super().__init__(master, **cnf)
        self.color_strip = Canvas(self, width=230, height=27, **self.style.surface, highlightthickness=0)
        self.color_strip.pack(pady=5)
        self.color_strip.bind("<ButtonPress-1>", self._drag_start)
        self.color_strip.bind("<ButtonRelease>", self._drag_end)
        self.color_strip.bind("<Motion>", self._adjust)
        self.drag_state = False
        x, y = 5, 0
        self.pos = x, y
        self._width = int(self.color_strip['width'])
        self.step = step = (self._width - 10) / len(color_array)
        self.color_array = color_array
        for c in color_array:
            fill = color.to_hex(c)
            self.color_strip.create_rectangle(
                x, y, x + step, y + 15,
                fill=fill, width=0)
            x = x + step
        self.selector = self.color_strip.create_polygon(5, 15, 0, 25, 10, 25, splinesteps=1, joinstyle="miter",
                                                        fill="#5a5a5a", outline="#f7f7f7", activeoutline="#3d8aff")

    def _drag_start(self, event):
        super()._drag_start(event)
        self.drag_state = event

    def _drag_end(self, event):
        self._adjust(event)
        self.drag_state = None

    def _adjust(self, event=None, x=None, y=None):
        if self.drag_state or x is not None:
            # Ensure the value is always above 5 and below the canvas width
            x = event.x if event else x
            x = min(max(x, 5), self._width - 5)
            if x == self.pos[0]:
                return
            self.pos = x, 0
            self.color_strip.coords(self.selector, x, 15, x - 5, 25, x + 5, 25)
            self.color_strip.update_idletasks()
            # Since we are going to call _adjust implicitly at times we need to avoid firing the callback on implicit
            # changes to avoid unpredictable change loops!
            # During implicit changes event is set to None and an x position provided.
            index = int((x - 5) / (self._width - 10) * (len(self.color_array) - 1))
            if not event:
                if self.implicit_callback:
                    self.implicit_callback(self.color_array[index])
            elif self.callback:
                self.callback(self.color_array[index])

    def get(self):
        return self.color_array[int((self.pos[0] - 5)/(self._width - 10) * (len(self.color_array) - 1))]

    def get_hsv(self):
        return color.to_hsv(self.get())

    def recolor(self, color_array):
        self.color_array = color_array
        color_array = " ".join(list(map(color.to_hex, color_array)))
        self.color_strip.tk.eval('recolor_strip %s {%s}' % (self.color_strip._w, color_array))

    def set(self, x_frac, y_frac=None):
        self._adjust(None, x_frac * (self._width - 5))


class _ColorSpace(_Spectrum):

    def __init__(self, master, hue, **cnf):
        super().__init__(master, **cnf)
        self.hue = hue
        self._color = None
        self.color_space = Canvas(self, width=230, height=100, **self.style.surface, highlightthickness=0)
        self.color_space.pack()
        self.color_space.bind("<ButtonPress-1>", self._drag_start)
        self.color_space.bind("<ButtonRelease>", self._drag_end)
        self.color_space.bind("<Motion>", self._adjust)
        self.drag_state = False
        x, y = 0, 0
        self.pos = x, y
        self._width = w = int(self.color_space['width'])
        self._height = h = int(self.color_space['height'])
        step_x = round(w / 50)
        step_y = round(h / 50)
        for i in range(0, 101, 2):
            for j in range(100, -1, -2):
                fill = color.to_hex(color.from_hsv((hue, i, j)))
                self.color_space.create_rectangle(
                    x, y, x + step_x, y + step_y,
                    fill=fill, width=0)
                y += step_y
            y = 0
            x += step_x
        self.callback, self.implicit_callback = None, None
        self.selector = self.color_space.create_oval(0, 0, 1, 1, outline="#f7f7f7", activeoutline="#3d8aff")

    def _drag_start(self, event):
        super()._drag_start(event)
        self.drag_state = event

    def _drag_end(self, event):
        self._adjust(event)
        self.drag_state = None

    def _adjust(self, event=None, x=None, y=None):
        if self.drag_state or x is not None:
            # Ensure the value is always above 0 and below the canvas width
            x, y = (event.x, event.y) if event else (x, y)
            x = min(max(x, 0), self._width)
            y = min(max(y, 0), self._height)
            self.pos = (x, y)
            self.color_space.coords(self.selector, x - 5, y - 5, x + 5, y + 5)
            self.color_space.update_idletasks()
            # Since we are going to call _adjust implicitly at times we need to avoid firing the callback on implicit
            # changes to avoid unpredictable change loops!
            # During implicit changes event is set to None and an x position provided.
            self._color = (self.hue, round((x/self._width)*100), round(((self._height - y)/self._height)*100))
            if not event:
                if self.implicit_callback:
                    self.implicit_callback(self.get())
            elif self.callback:
                self.callback(self.get())

    def get(self):
        return color.to_hex(color.from_hsv(self._color))

    def get_hsv(self):
        return self._color

    def recolor(self, hue):
        if self.hue == hue:
            return
        self.hue = hue
        self.color_space.tk.eval('recolor_space %s %s' % (self.color_space._w, hue))

    def set(self, x_frac, y_frac=0):
        self._adjust(None, x_frac * self._width, (1 - y_frac) * self._height)


class ColorChooser(Frame):

    def __init__(self, master=None, starting_color=None, **cnf):
        super().__init__(master, **cnf)
        shifts = [
            *[(255, 0, i) for i in range(256)],          # Magenta shift
            *[(255 - i, 0, 255) for i in range(256)],    # Blue shift
            *[(0, i, 255) for i in range(256)],          # Cyan shift
            *[(0, 255, 255 - i) for i in range(256)],    # Green shift
            *[(i, 255, 0) for i in range(256)],          # Yellow shift
            *[(255, 255 - i, 0) for i in range(256)],    # Red shift
        ]
        hsv_start = color.to_hsv(color.to_rgb(starting_color or "#000000"))
        self.configure(**self.style.surface)
        self.col = _ColorSpace(self, hsv_start[0])
        self.col.pack()
        self.hue = hue = _ColorStrip(self, shifts)
        hue.pack()
        hue.on_change(self.adjust_strips)
        hue.on_implicit_change(self.recolor_strips)
        self.col.on_change(self.update_panel)
        self.monitor = monitor = panels.ColorInput(self)
        self.monitor.on_change(self.on_monitor_change)
        monitor.pack()
        self._on_change = None

    def on_monitor_change(self, hex_string):
        self.set_strips(hex_string)
        if self._on_change:
            self._on_change(hex_string)

    def set_strips(self, hex_string):
        h, s, v = color.to_hsv(color.to_rgb(hex_string))
        # Since the hue color strip is using preset color shifts it is reversed with 0 on the right and 360 on the left
        # We therefore need to use the complement of the fraction 1 - f
        self.hue.set(1 - h / 360)
        self.col.set(s / 100, v / 100)

    def recolor_strips(self, rgb):
        h, *_ = color.to_hsv(rgb)
        self.col.recolor(h)

    def adjust_strips(self, rgb):
        self.recolor_strips(rgb)
        self.update_panel()

    def update_panel(self, *_):
        hsv = self.hue.get_hsv()[0], *self.col.get_hsv()[1:]
        hex_string = color.to_hex(color.from_hsv(hsv))
        # We have set panel value implicitly so we update the hex value ourselves
        self.monitor.set(hex_string, True)
        self.monitor.hex_string.set(hex_string)
        if self._on_change:
            self._on_change(self.monitor.get())

    def set_color(self, hex_string):
        self.set_strips(hex_string)
        self.monitor.set(hex_string, True)
        self.monitor.hex_string.set(hex_string)

    def on_change(self, listener, *args, **kwargs):
        self._on_change = lambda val: listener(val, *args, **kwargs)


class ColorDialog(Popup):

    def __init__(self, master, widget=None, starting_color=None, **cnf):
        if widget:
            rec = self.get_pos(widget, side="auto", padding=4, width=234, height=206)
        else:
            rec = (0, 0)
        super().__init__(master, rec, **cnf)
        self.chooser = ColorChooser(self, starting_color, **self.style.surface)
        self.chooser.pack()

    def set(self, value):
        self.chooser.set_color(value)

    def on_change(self, listener, *args, **kwargs):
        self.chooser.on_change(listener, *args, **kwargs)

    def destroy(self):
        if self.chooser.monitor.picker_active:
            return
        else:
            super().destroy()


if __name__ == "__main__":
    import timeit
    root = Application()
    cc = ColorChooser(root, bg="#5a5a5a")
    cc.pack()
    cc.set_color("#5a5a5a")
    hu = 340

    def get_hue():
        global hu
        hu = 350 - hu
        return hu

    def test():
        print("time:")
        print(timeit.timeit("cc.col.recolor(get_hue())", number=5, globals=globals()))

    # root.after(200, test)
    root.mainloop()
