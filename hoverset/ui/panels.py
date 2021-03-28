"""
All commonly used widget sets should be placed here to allow easy reuse.
See to it that the state is easily changeable through a unified set and get.
"""

from PIL import ImageTk
import logging

from hoverset.ui.widgets import *
from hoverset.ui.icons import get_icon_image
from hoverset.util.color import to_hex, to_rgb, to_hsl, from_hsl, to_hsv, from_hsv
from hoverset.util.validators import check_hex_color, numeric_limit
from hoverset.platform.functions import image_grab


class _FloatingColorWindow(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.label = Label(self, **self.style.surface)
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
        super().__init__(master, **cnf, image=get_icon_image("colorpicker", 15, 15))
        self.tooltip('Pick color from anywhere')
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
        self._window.bind("<Visibility>", lambda _: self._window.grab_set())
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
        self.config(**self.style.surface)
        self.callback = None
        self.models = {
            "RGB": _RgbModel(self),
            "HSL": _HslModel(self),
            "HSV": _HsvModel(self)
        }
        # Set the value as the first model
        self.current_model = self.models.get(list(self.models.keys())[0])
        # Initialize the hex_string which is needed for model initialization
        self.hex_string = Entry(self, **self.style.input, **self.style.highlight_active, width=8)
        self.hex_string.grid(row=0, column=1)
        self.hex_string.on_entry(self.on_hex_string_changed)
        self.hex_string.set_validator(check_hex_color)
        self.pad = Label(self, width=8, height=2)
        self.pad.grid(row=0, column=2, columnspan=2, padx=2, pady=2)
        self.model_select = Spinner(self, width=7)
        self.model_select.set_values(list(self.models.keys()))
        self.model_select.set("RGB")
        self.model_select.grid(row=0, column=0, sticky='w')
        self.model_select.config(**self.style.surface)
        self.model_select.on_change(self.on_model_change)
        self.model_select.set(list(self.models.keys())[0])
        self._picker = picker = ColorPicker(self, width=25, height=25, **self.style.button)
        picker.grid(row=1, column=2, padx=2, pady=2, sticky="n")
        picker.on_pick(self.set)
        clipboard = Button(self, width=25, height=25,
                           image=get_icon_image("clipboard", 15, 15), **self.style.button)
        clipboard.grid(row=1, column=3, padx=2, pady=2, sticky="n")
        clipboard.on_click(self.pick_from_clipboard)
        clipboard.tooltip('Pick color from clipboard')
        self.current_model = self.models.get(self.model_select.get())
        self.attach(self.current_model)

    @property
    def picker_active(self):
        return self._picker.active

    def pick_from_clipboard(self, *_):
        value = self.clipboard_get()
        try:
            # convert color from clipboard to general rgb format first
            # if the color is valid this should not throw any errors
            # this means if the clipboard contains "red" what is set finally is "#ff0000"
            r, g, b = self.winfo_rgb(value)  # returns 12-bit color
            # scale down from 12-bit color to 8-bit color that the color-chooser understands
            color = to_hex(tuple(map(lambda x: round(x * (255 / 65535)), (r, g, b))))
            self.set(color)
        except Exception:
            # Not a valid color so ignore
            # TODO Show a message
            pass

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
        self.config(**self.style.surface)
        rgb_spinbox = {**self.style.spinbox, "from": 0, "to": 255, "width": 4}
        self.r = SpinBox(self, **rgb_spinbox)
        self.r.on_change(master.change, True)
        self.r.on_entry(master.change)
        self.r.set_validator(numeric_limit, 0, 255)
        self.r.grid(row=0, column=0, pady=1, padx=1)
        self.g = SpinBox(self, **rgb_spinbox)
        self.g.on_change(master.change, True)
        self.g.on_entry(master.change)
        self.g.set_validator(numeric_limit, 0, 255)
        self.g.grid(row=0, column=1, pady=1, padx=1)
        self.b = SpinBox(self, **rgb_spinbox)
        self.b.on_change(master.change, True)
        self.b.on_entry(master.change)
        self.b.set_validator(numeric_limit, 0, 255)
        self.b.grid(row=0, column=2, pady=1, padx=1)
        Label(self, text="R", **self.style.text).grid(row=1, column=0, sticky="ew")
        Label(self, text="G", **self.style.text).grid(row=1, column=1, sticky="ew")
        Label(self, text="B", **self.style.text).grid(row=1, column=2, sticky="ew")
        self.initial = "#000000"

    def get(self) -> str:
        # return the hex color string
        rgb = self.r.get(), self.g.get(), self.b.get()
        # we shield ourselves from errors raised when trying to parse empty values
        if any(i == "" for i in rgb):
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
        self.config(**self.style.surface)
        # ======== hue is a angular value ranging from 0 to 360 =========

        self.h = SpinBox(self, **self.style.spinbox, width=4, from_=0, to=360)
        self.h.on_change(master.change, True)
        self.h.on_entry(master.change)
        self.h.set_validator(numeric_limit, 0, 360)
        self.h.grid(row=0, column=0, pady=1, padx=1)

        # ========= saturation and luminosity are percentages ===========

        percent_spinbox = {**self.style.spinbox, "from": 0, "to": 100, "width": 4}
        self.s = SpinBox(self, **percent_spinbox)
        self.s.on_change(master.change, True)
        self.s.on_entry(master.change)
        self.s.set_validator(numeric_limit, 0, 100)
        self.s.grid(row=0, column=1, pady=1, padx=1)
        self.l = SpinBox(self, **percent_spinbox)
        self.l.on_change(master.change, True)
        self.l.on_entry(master.change)
        self.l.set_validator(numeric_limit, 0, 100)
        self.l.grid(row=0, column=2, pady=1, padx=1)

        # ===============================================================

        Label(self, text="H", **self.style.text).grid(row=1, column=0, sticky="ew")
        Label(self, text="S", **self.style.text).grid(row=1, column=1, sticky="ew")
        Label(self, text="L", **self.style.text).grid(row=1, column=2, sticky="ew")
        self.initial = "#000000"

    def get(self) -> str:
        # return the hex color string
        hsl = self.h.get(), self.s.get(), self.l.get()
        if any(i == "" for i in hsl):
            return self.initial
        return to_hex(from_hsl(hsl))

    def set(self, hex_str: str) -> None:
        h, s, l = to_hsl(to_rgb(hex_str))
        self.h.set(round(h))
        self.s.set(round(s))
        self.l.set(round(l))
        self.initial = hex_str


class _HsvModel(Frame):
    # The HSV model whose render is called when the user switches the model in the color input panel
    # Colors are manipulated by varying the ratios of hue saturation and value
    def __init__(self, master: ColorInput = None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.surface)
        # ======== hue is a angular value ranging from 0 to 360 =========

        self.h = SpinBox(self, **self.style.spinbox, from_=0, to=360, width=4)
        self.h.on_change(master.change, True)
        self.h.on_entry(master.change)
        self.h.set_validator(numeric_limit, 0, 360)
        self.h.grid(row=0, column=0, pady=1, padx=1)

        # ========= saturation and value are percentages ===========

        percent_spinbox = {**self.style.spinbox, "from": 0, "to": 100, "width": 4}
        self.s = SpinBox(self, **percent_spinbox)
        self.s.on_change(master.change, True)
        self.s.on_entry(master.change)
        self.s.set_validator(numeric_limit, 0, 100)
        self.s.grid(row=0, column=1, pady=1, padx=1)
        self.v = SpinBox(self, **percent_spinbox)
        self.v.on_change(master.change, True)
        self.v.on_entry(master.change)
        self.v.set_validator(numeric_limit, 0, 100)
        self.v.grid(row=0, column=2, pady=1, padx=1)

        # ===============================================================

        Label(self, text="H", **self.style.text).grid(row=1, column=0, sticky="ew")
        Label(self, text="S", **self.style.text).grid(row=1, column=1, sticky="ew")
        Label(self, text="V", **self.style.text).grid(row=1, column=2, sticky="ew")
        self.initial = "#000000"

    def get(self) -> str:
        # return the hex color string
        # remember s and v are percentages and underlying hsv converter works with values from 0 to 255
        hsv = self.h.get(), self.s.get(), self.v.get()
        if any(i == "" for i in hsv):
            return self.initial
        return to_hex(from_hsv(hsv))

    def set(self, hex_str: str) -> None:
        h, s, v = to_hsv(to_rgb(hex_str))
        self.h.set(round(h))
        self.s.set(round(s))
        self.v.set(round(v))
        self.initial = hex_str


class FontPicker(Button):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf, image=get_icon_image("eye", 15, 15))
        self.tooltip("Pick Font")
        self.bind_all('<Button-1>', self.pick, add='+')
        self.bind_all('<Motion>', self._render, add='+')
        self.active = False
        self._grabbed = None
        self._window = None
        self._indicator = None

    def start(self, _):
        if self.active:
            return
        self._grabbed = self.grab_current()  # Store the widget that has event grab if any
        self.active = True
        self._window = Window(self.window)
        self._window.geometry('0x0')
        self._window.overrideredirect(True)
        self._window.config(**self.style.surface, **self.style.highlight_passive)
        self._indicator = Label(self._window, **self.style.text_accent)
        self._indicator.pack(fill="both", expand=True)
        self._window.pack_propagate(False)
        self._window.bind("<Visibility>", lambda _: self.grab_set())

    def on_pick(self, callback, *args, **kwargs):
        self._on_pick = lambda color: callback(color, *args, **kwargs)

    def _get_font(self, x, y):
        widget = self.winfo_containing(x, y)
        if widget is not None and 'font' in widget.keys():
            return widget['font']

    def _render(self, event):
        if not self.active:
            return
        displace_x = 10 if self.winfo_screenwidth() - event.x_root > 160 else -160
        displace_y = 0 if self.winfo_screenheight() - event.y_root > 40 else -30
        font_value = self._get_font(event.x_root, event.y_root)
        try:
            _font = FontStyle(self, font_value)
            self._indicator['text'] = _font.cget('family') or 'No font to extract'
            if font_value:
                self._indicator['font'] = _font.cget('family')
            else:
                self._indicator['font'] = 'TkDefaultFont'
        except Exception:
            self._indicator['font'] = 'TkDefaultFont'
            self._indicator['text'] = 'No font to extract'

        self._window.geometry(
            '{width}x{height}+{x}+{y}'.format(
                x=event.x_root + displace_x, y=event.y_root + displace_y, width=150, height=30
            ))

    def pick(self, event):
        if self.active:
            if self._window:
                self._window.destroy()
                self._window = None
            self.grab_release()
            if self._grabbed:
                self._grabbed.grab_set()
                self._grabbed = None
            self.active = False
            value = self._get_font(event.x_root, event.y_root)
            if value and self._on_pick:
                self._on_pick(value)
        else:
            # if picker is not active then start it
            self.start(event)


class FontInput(Frame):
    class FontItem(CompoundList.BaseItem):

        def render(self):
            label = Label(self, text=self.value, **self.style.text, anchor="w")
            # label.config(font=(self.value, ))
            label.pack(side="left")

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.surface)
        self._on_change = None
        self._font = Spinner(self, **self.style.input, width=110)
        self._font.config(**self.style.no_highlight)
        self._font.place(x=0, y=0, relwidth=0.7, height=24)
        self._font.set_item_class(FontInput.FontItem)
        self._font.set_values(system_fonts())
        self._font.on_change(self._change)
        self._size = SpinBox(self, from_=0, to=999, **self.style.spinbox, width=3, justify='right')
        self._size.config(**self.style.no_highlight)
        self._size.place(relx=0.7, y=0, relwidth=0.3, height=24)
        self._size.on_change(self._change)
        frame = Frame(self, **self.style.surface, height=25, width=150)
        frame.place(x=0, y=25, relwidth=1, height=24)
        self._bold = ToggleButton(frame, text="B", font=FontStyle(family="Times", size=12, weight='bold'),
                                  width=24, height=24)
        self._bold.pack(side='left')
        self._bold.on_change(self._change)
        self._italic = ToggleButton(frame, text="I", font=FontStyle(family="Times", size=12, slant='italic'),
                                    width=24, height=24)
        self._italic.pack(side='left')
        self._italic.on_change(self._change)
        self._underline = ToggleButton(frame, text="U", font=FontStyle(family="Times", size=12, underline=1),
                                       width=24, height=24)
        self._underline.pack(side='left')
        self._underline.on_change(self._change)
        self._strike = ToggleButton(frame, text="abc", font=FontStyle(family="Times", size=12, overstrike=1),
                                    width=30, height=24)
        self._strike.pack(side='left')
        self._strike.on_change(self._change)

        self._picker = picker = FontPicker(frame, width=24, height=24, **self.style.button)
        picker.pack(side="right")
        picker.on_pick(self.pick)

    def _change(self, *_):
        if self._on_change:
            self._on_change(self.get())

    def pick(self, value):
        self.set(value)
        self._change()

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda val: func(val, *args, **kwargs)

    def get(self):
        extra = []
        if self._bold.get():
            extra.append('bold')
        if self._italic.get():
            extra.append('italic')
        if self._strike.get():
            extra.append('overstrike')
        if self._underline.get():
            extra.append('underline')
        extra = ' '.join(extra)
        return f"{{{self._font.get()}}} {abs(self._size.get() or 0)} {{{extra}}}"

    @suppress_change
    def set(self, value):
        if not value:
            for i in (self._italic, self._bold, self._underline, self._strike):
                i.set(False)
            return
        try:
            font_obj = FontStyle(self, value)
        except Exception:
            logging.error("Font exception")
            return
        self._font.set(font_obj.cget("family"))
        self._size.set(font_obj.cget("size"))
        self._italic.set(True if font_obj.cget("slant") == "italic" else False)
        self._bold.set(True if font_obj.cget("weight") == "bold" else False)
        self._underline.set(font_obj.cget("underline"))
        self._strike.set(font_obj.cget("overstrike"))


if __name__ == "__main__":
    root = Application()
    root.load_styles("themes/default.css")
    c_input = ColorInput(root)
    c_input.set("#5a5a5a")
    c_input.pack()
    root.mainloop()
