"""
An assortment of common input pickers.
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import hoverset.util.color as color
import hoverset.ui.panels as panels
from hoverset.ui.widgets import *


# Inspired by python pynche color chooser by Barry A. Warsaw, bwarsaw@python.org
class _ColorStrip(Frame):
    # Load this script into the Tcl interpreter and call it in
    # _ColorStrip.recolor().  This is about as fast as it can be with the
    # current _tkinter.c interface, which doesn't support Tcl Objects.
    _RECOLOR_PROC = '''\
    proc recolor {canvas colors} {
        set i 1
        foreach c $colors {
            $canvas itemconfigure $i -fill $c
            incr i
        }
    }
    '''

    def __init__(self, master=None, color_array=None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.surface, **self.style.highlight)
        self.color_strip = Canvas(self, width=230, height=27, **self.style.surface, highlightthickness=0)
        self.color_strip.pack(pady=5)
        self.color_strip.tk.eval(_ColorStrip._RECOLOR_PROC)
        setattr(self.color_strip, "pos", 5)
        self.color_strip.bind("<ButtonPress-1>", self._drag_start)
        self.color_strip.bind("<ButtonRelease>", self._drag_end)
        self.color_strip.bind("<Motion>", self._adjust)
        self.drag_state = False
        x, y = 5, 0
        self._width = int(self.color_strip['width'])
        self.step = step = (self._width - 10) / len(color_array)
        self.color_array = color_array
        for c in color_array:
            fill = color.to_hex(c)
            self.color_strip.create_rectangle(
                x, y, x + step, y + 15,
                fill=fill, width=0)
            x = x + step
        self.callback, self.implicit_callback = None, None
        self.selector = self.color_strip.create_polygon(5, 15, 0, 25, 10, 25, splinesteps=1, joinstyle="miter",
                                                        fill="#5a5a5a", outline="#f7f7f7", activeoutline="#3d8aff")
        # First, I apologise for the crappy syntax
        # But this was the quickest way to generate an anonymous event object for use with _adjust
        # Considering we are working inside a lambda function!
        # This should allow the use of arrow keys to adjust the strip
        self.bind("<Left>", lambda e: self._adjust(type("", (), {"x": self.color_strip.pos - 1})(), True))
        self.bind("<Right>", lambda e: self._adjust(type("", (), {"x": self.color_strip.pos + 1})(), True))

    def _drag_start(self, event):
        self.drag_state = event

    def _drag_end(self, event):
        self._adjust(event)
        self.drag_state = None

    def _adjust(self, event=None, x=None):
        if self.drag_state or x is not None:
            # Ensure the value is always above 5 and below the canvas width
            x = event.x if event else x
            x = min(max(x, 5), self._width - 5)
            self.color_strip.pos = x
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

    def on_change(self, callback, *args, **kwargs):
        self.callback = lambda c: callback(c, *args, **kwargs)

    def on_implicit_change(self, callback, *args, **kwargs):
        self.implicit_callback = lambda c: callback(c, *args, **kwargs)

    def get(self):
        return self.color_array[int((self.color_strip.pos - 5)/(self._width - 10) * (len(self.color_array) - 1))]

    def get_hsl(self):
        return color.to_hsl(self.get())

    def recolor(self, color_array):
        self.color_array = color_array
        color_array = " ".join(list(map(color.to_hex, color_array)))
        self.color_strip.tk.eval('recolor %s {%s}' % (self.color_strip._w, color_array))

    def set(self, fraction: float):
        self._adjust(None, fraction * (self._width - 5))


class ColorChooser(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        shifts = [
            *[(255, 0, i) for i in range(256)],          # Magenta shift
            *[(255 - i, 0, 255) for i in range(256)],    # Blue shift
            *[(0, i, 255) for i in range(256)],          # Cyan shift
            *[(0, 255, 255 - i) for i in range(256)],    # Green shift
            *[(i, 255, 0) for i in range(256)],          # Yellow shift
            *[(255, 255 - i, 0) for i in range(256)],    # Red shift
        ]
        self.configure(**self.style.surface)
        self.hue = hue = _ColorStrip(self, shifts)
        hue.pack()
        hue.on_change(self.adjust_strips)
        hue.on_implicit_change(self.recolor_strips)
        self.sat = _ColorStrip(self, self.saturation_list(hue.get()))
        self.sat.pack()
        self.sat.on_change(self.update_panel)
        self.lum = _ColorStrip(self, self.luminosity_list(hue.get()))
        self.lum.pack()
        self.lum.on_change(self.update_panel)
        self.monitor = monitor = panels.ColorInput(self)
        self.monitor.on_change(self.on_monitor_change)
        monitor.pack()
        self._on_change = None

    def on_monitor_change(self, hex_string):
        self.set_strips(hex_string)
        if self._on_change:
            self._on_change(hex_string)

    def set_strips(self, hex_string):
        h, s, l = color.to_hsl(color.to_rgb(hex_string))
        # Since the hue color strip is using preset color shifts it is reversed with 0 on the right and 360 on the left
        # We therefore need to use the complement of the fraction 1 - f
        self.hue.set(1 - h / 360)
        self.sat.set(s / 100)
        self.lum.set(l / 100)

    def recolor_strips(self, rgb):
        self.sat.recolor(self.saturation_list(rgb))
        self.lum.recolor(self.luminosity_list(rgb))

    def adjust_strips(self, rgb):
        self.recolor_strips(rgb)
        self.update_panel()

    def update_panel(self, *_):
        hsl = self.hue.get_hsl()[0], self.sat.get_hsl()[1], self.lum.get_hsl()[2]
        hex_string = color.to_hex(color.from_hsl(hsl))
        # We have set panel value implicitly so we update the hex value ourselves
        self.monitor.set(hex_string, True)
        self.monitor.hex_string.set(hex_string)
        if self._on_change:
            self._on_change(self.monitor.get())

    def saturation_list(self, rgb):
        h, s, l = color.to_hsl(rgb)
        return [color.from_hsl((h, i, l)) for i in range(101)]

    def luminosity_list(self, rgb):
        h, s, l = color.to_hsl(rgb)
        return [color.from_hsl((h, s, i)) for i in range(101)]

    def set_color(self, hex_string):
        self.set_strips(hex_string)
        self.monitor.set(hex_string, True)
        self.monitor.hex_string.set(hex_string)

    def on_change(self, listener, *args, **kwargs):
        self._on_change = lambda val: listener(val, *args, **kwargs)


class ColorDialog(Popup):

    def __init__(self, master, widget=None, **cnf):
        if widget:
            rec = self.get_pos(widget, side="auto", padding=4, width=234, height=206)
        else:
            rec = (0, 0)
        super().__init__(master, rec, **cnf)
        self.chooser = ColorChooser(self, **self.style.surface)
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
    root = Application()
    root.load_styles("themes/default.css")
    c = ColorChooser(root, bg="#5a5a5a")
    c.pack()
    c.on_change(lambda a:print(a))
    c.set_color("#5a5a5a")
    root.mainloop()
