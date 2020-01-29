"""
All commonly used widget sets should be placed here to allow easy reuse.
See to it that the state is easily changeable through a unified set and get.
"""

from PIL import ImageTk

from hoverset.ui.widgets import *
from hoverset.ui.icons import get_icon
from hoverset.util.color import to_hex, to_rgb, to_hsl, from_hsl, to_hsv, from_hsv
from hoverset.util.validators import check_hex_color, numeric_limit
from hoverset.platform.functions import image_grab


class _FloatingColorWindow(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.label = Label(self, **self.style.dark)
        self.label.pack(fill="both", expand=True, padx=1, pady=1)
        self.pixel_access = None
        self.config(borderwidth=1)
        self.color = "#000000"  # The default
        self._on_pick = None

    def set_image_ref(self, image):
        self.pixel_access = image.load()

    def on_pick(self, callback, *args, **kwargs):
        self._on_pick = lambda: callback(self.color, *args, **kwargs)

    def bind_motion(self, element):
        element.bind("<Motion>", self.process)
        element.bind("<Button-1>", self.pick)

    def pick(self, _):
        if self._on_pick:
            self._on_pick()

    def process(self, event):
        displace_x = 10 if self.winfo_screenwidth() - event.x_root > 60 else -50
        displace_y = 0 if self.winfo_screenheight() - event.y_root > 50 else -40
        self.place(x=event.x_root + displace_x, y=event.y_root + displace_y, width=40, height=40)
        color = self.pixel_access[event.x_root, event.y_root]
        self.color = to_hex(color)
        self.label.config(bg=self.color)


class ColorPicker(Button):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf, text=get_icon("color_picker"))
        self.image = None
        self.on_click(self.start)
        self._window = None
        self._on_pick = None
        self._color_win = None
        self._body = None
        self.active = False
        self._grabbed = None

    def start(self, _):
        if self.active:
            return
        self.image = image_grab()
        image_x = ImageTk.PhotoImage(image=self.image)
        self._window = Window(self.window)
        self._grabbed = self.grab_current()  # Store the widget that has event grab if any
        self._window.grab_set()
        self._window.wm_attributes("-fullscreen", True)
        self._body = Label(self._window, image=image_x, cursor="target")
        self._body.place(relwidth=1, relheight=1, x=0, y=0)
        self._body.image = image_x
        self._color_win = _FloatingColorWindow(self._window)
        self._color_win.set_image_ref(self.image)
        self._color_win.bind_motion(self._window)
        self._color_win.on_pick(self.pick)
        self.active = True

    def on_pick(self, callback, *args, **kwargs):
        self._on_pick = lambda color: callback(color, *args, **kwargs)

    def pick(self, color):
        if self._window:
            # Release and return the event grab to the widget that had it initially
            # This is useful when we are using popups which rely heavily on event grabbing to function properly
            self._window.grab_release()
            if self._grabbed:
                self._grabbed.grab_set()
                self._grabbed = None
            self._window.destroy()
            self.active = False
        if self._on_pick:
            self._on_pick(color)


class ColorInput(Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark)
        self.callback = None
        self.models = {
            "RGB": _RgbModel(self),
            "HSL": _HslModel(self),
            "HSV": _HsvModel(self)
        }
        # Set the value as the first model
        self.current_model = self.models.get(list(self.models.keys())[0])
        # Initialize the hex_string which is needed for model initialization
        self.hex_string = Entry(self, **self.style.dark_input, width=8)
        self.hex_string.grid(row=0, column=1)
        self.hex_string.on_entry(self.on_hex_string_changed)
        self.hex_string.set_validator(check_hex_color)
        self.pad = Label(self, width=8, height=2)
        self.pad.grid(row=0, column=2, columnspan=2, padx=2, pady=2)
        self.model_select = Spinner(self, width=7)
        self.model_select.set_values(list(self.models.keys()))
        self.model_select.set("RGB")
        self.model_select.grid(row=0, column=0, sticky='w')
        self.model_select.config(**self.style.dark)
        self.model_select.on_change(self.on_model_change)
        self.model_select.set(list(self.models.keys())[0])
        self._picker = picker = ColorPicker(self, width=25, height=25, **self.style.dark_button)
        picker.grid(row=1, column=2, padx=2, pady=2, sticky="n")
        picker.on_pick(self.set)
        clipboard = Button(self, width=25, height=25, text="\uee92", **self.style.dark_button)
        clipboard.grid(row=1, column=3, padx=2, pady=2, sticky="n")
        self.current_model = self.models.get(self.model_select.get())
        self.attach(self.current_model)

    @property
    def picker_active(self):
        return self._picker.active

    def change(self, implicit=False):
        if self.callback and not implicit:
            self.callback(self.current_model.get())
        if not implicit:
            self.hex_string.set(self.current_model.get())
        self.pad.config(bg=self.current_model.get())

    def on_hex_string_changed(self):
        # If the color format is incorrect no need to update the panel
        # If the string is 8 bit we need to expand it using to_hex
        if len(self.hex_string.get()) == 4:
            self.current_model.set(to_hex(self.hex_string.get()))
            self.callback(self.current_model.get())
        # if the color is 8 bit then we can update without errors
        elif len(self.hex_string.get()) == 7:
            self.current_model.set(self.hex_string.get())
            self.callback(self.current_model.get())

    def on_model_change(self, *_):
        current_color = self.current_model.get()
        self.current_model.grid_forget()
        self.current_model = self.models.get(self.model_select.get())
        self.current_model.set(current_color)
        self.attach(self.current_model)

    def attach(self, model):
        # Helper function to allow you display a model
        model.grid(row=1, column=0, columnspan=2)

    def set(self, hex_string: str, implicit: bool = False) -> None:
        # Implicit should be set to true if change is generated internally or programmatically
        # otherwise it is explicit and should be imagined as being generated by the user
        # This is very important in preventing infinite loop conditions when the picker is used together
        # with other widgets systems whose change events are interconnected with the color picker
        self.current_model.set(hex_string)
        self.change(implicit)

    def get(self) -> str:
        return self.current_model.get()

    def on_change(self, callback, *args, **kwargs):
        self.callback = lambda color: callback(color, *args, **kwargs)


class _RgbModel(Frame):
    # The RGB model whose render is called when the user switches the model in the color input panel
    # Colors are manipulated by varying the ratios of red green and blue
    def __init__(self, master: ColorInput = None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark)
        self.r = SpinBox(self, **self.style.rgb_spinbox)
        self.r.on_change(master.change, True)
        self.r.on_entry(master.change)
        self.r.set_validator(numeric_limit, 0, 255)
        self.r.grid(row=0, column=0, pady=1, padx=1)
        self.g = SpinBox(self, **self.style.rgb_spinbox)
        self.g.on_change(master.change, True)
        self.g.on_entry(master.change)
        self.g.set_validator(numeric_limit, 0, 255)
        self.g.grid(row=0, column=1, pady=1, padx=1)
        self.b = SpinBox(self, **self.style.rgb_spinbox)
        self.b.on_change(master.change, True)
        self.b.on_entry(master.change)
        self.b.set_validator(numeric_limit, 0, 255)
        self.b.grid(row=0, column=2, pady=1, padx=1)
        Label(self, text="R", **self.style.rgb_label).grid(row=1, column=0)
        Label(self, text="G", **self.style.rgb_label).grid(row=1, column=1)
        Label(self, text="B", **self.style.rgb_label).grid(row=1, column=2)
        self.initial = "#000000"

    def get(self) -> str:
        # return the hex color string
        rgb = self.r.get(), self.g.get(), self.b.get()
        # we shield ourselves from errors raised when trying to parse empty values
        if any([i == "" for i in rgb]):
            return self.initial
        return to_hex(rgb)

    def set(self, hex_str: str) -> None:
        self.initial = hex_str
        r, g, b = to_rgb(hex_str)
        self.r.set(r)
        self.g.set(g)
        self.b.set(b)


class _HslModel(Frame):
    # The HSL model whose render is called when the user switches the model in the color input panel
    # Colors are manipulated by varying the ratios of hue saturation and luminosity
    def __init__(self, master: ColorInput = None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark)
        # ======== hue is a angular value ranging from 0 to 360 =========

        self.h = SpinBox(self, **self.style.degree_spinbox)
        self.h.on_change(master.change, True)
        self.h.on_entry(master.change)
        self.h.set_validator(numeric_limit, 0, 360)
        self.h.grid(row=0, column=0, pady=1, padx=1)

        # ========= saturation and luminosity are percentages ===========

        self.s = SpinBox(self, **self.style.percent_spinbox)
        self.s.on_change(master.change, True)
        self.s.on_entry(master.change)
        self.s.set_validator(numeric_limit, 0, 100)
        self.s.grid(row=0, column=1, pady=1, padx=1)
        self.l = SpinBox(self, **self.style.percent_spinbox)
        self.l.on_change(master.change, True)
        self.l.on_entry(master.change)
        self.l.set_validator(numeric_limit, 0, 100)
        self.l.grid(row=0, column=2, pady=1, padx=1)

        # ===============================================================

        Label(self, text="H", **self.style.rgb_label).grid(row=1, column=0)
        Label(self, text="S", **self.style.rgb_label).grid(row=1, column=1)
        Label(self, text="L", **self.style.rgb_label).grid(row=1, column=2)

    def get(self) -> str:
        # return the hex color string
        return to_hex(from_hsl((self.h.get(), self.s.get(), self.l.get())))

    def set(self, hex_str: str) -> None:
        h, s, l = to_hsl(to_rgb(hex_str))
        self.h.set(round(h))
        self.s.set(round(s))
        self.l.set(round(l))


class _HsvModel(Frame):
    # The HSV model whose render is called when the user switches the model in the color input panel
    # Colors are manipulated by varying the ratios of hue saturation and value
    def __init__(self, master: ColorInput = None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark)
        # ======== hue is a angular value ranging from 0 to 360 =========

        self.h = SpinBox(self, **self.style.degree_spinbox)
        self.h.on_change(master.change, True)
        self.h.on_entry(master.change)
        self.h.set_validator(numeric_limit, 0, 360)
        self.h.grid(row=0, column=0, pady=1, padx=1)

        # ========= saturation and value are percentages ===========

        self.s = SpinBox(self, **self.style.percent_spinbox)
        self.s.on_change(master.change, True)
        self.s.on_entry(master.change)
        self.s.set_validator(numeric_limit, 0, 100)
        self.s.grid(row=0, column=1, pady=1, padx=1)
        self.v = SpinBox(self, **self.style.percent_spinbox)
        self.v.on_change(master.change, True)
        self.v.on_entry(master.change)
        self.v.set_validator(numeric_limit, 0, 100)
        self.v.grid(row=0, column=2, pady=1, padx=1)

        # ===============================================================

        Label(self, text="H", **self.style.rgb_label).grid(row=1, column=0)
        Label(self, text="S", **self.style.rgb_label).grid(row=1, column=1)
        Label(self, text="V", **self.style.rgb_label).grid(row=1, column=2)

    def get(self) -> str:
        # return the hex color string
        # remember s and v are percentages and underlying hsv converter works with values from 0 to 255
        return to_hex(from_hsv((self.h.get(), self.s.get(), self.v.get())))

    def set(self, hex_str: str) -> None:
        h, s, v = to_hsv(to_rgb(hex_str))
        self.h.set(round(h))
        self.s.set(round(s))
        self.v.set(round(v))


if __name__ == "__main__":
    root = Application()
    root.load_styles("themes/default.css")
    input = ColorInput(root)
    input.set("#5a5a5a")
    input.pack()
    root.mainloop()
