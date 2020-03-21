"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
import re
import sys
from tkinter import IntVar, ttk, filedialog, StringVar

from hoverset.ui.icons import get_icon
from hoverset.ui.pickers import ColorDialog
from hoverset.ui.widgets import (CompoundList, Entry, SpinBox, Spinner, Frame, Application, set_ttk_style,
                                 Label, system_fonts, ToggleButton, FontStyle, Button)
from hoverset.util.color import to_hex
from hoverset.util.validators import numeric_limit
from studio.feature.variable_manager import VariablePane, VariableItem
from studio.lib.properties import all_supported_cursors, BUILTIN_BITMAPS


class Editor(Frame):

    def __init__(self, master, style_def=None):
        super().__init__(master)
        self.config(**self.style.dark, width=150, height=25)
        self.pack_propagate(False)
        self.grid_propagate(0)
        self._on_change = None

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda val: func(val, *args, **kwargs)

    def set(self, value):
        raise NotImplementedError()

    def get(self):
        raise NotImplementedError()


class Choice(Editor):
    class ChoiceItem(CompoundList.BaseItem):

        def render(self):
            if not self.value:
                Label(self, **self.style.dark_text, text="select", anchor="w").pack(fill="both")
                return
            Label(self, **self.style.dark_text, text=self._value, anchor="w").pack(fill="both")

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        if style_def is None:
            style_def = {}
        self.style_def = style_def
        self._spinner = Spinner(self, **self.style.dark_input)
        self._spinner.pack(fill="x")
        self._spinner.on_change(self.spinner_change)
        self.set_up()
        values = style_def.get("options", ())
        if values:
            if not style_def.get('allow_empty', True):
                self._spinner.set_values(('', *values))
            else:
                self._spinner.set_values(values)

    def set_up(self):
        self._spinner.set_item_class(Choice.ChoiceItem)

    def spinner_change(self, value):
        if self._on_change is not None:
            self._on_change(value)

    def set(self, value):
        # Convert to string as values of type _tkinter.Tcl_Obj are common in ttk and may cause unpredictable behaviour
        self._spinner.set(str(value))

    def get(self):
        return self._spinner.get()


class Boolean(Editor):
    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.dark, **self.style.dark_highlight_active)
        self._var = IntVar()
        self._check = ttk.Checkbutton(self, command=self.check_change, text='',
                                      variable=self._var)
        set_ttk_style(self._check, **self.style.dark_checkbutton)
        self._check.pack(fill="x")

    def check_change(self):
        if self._var.get():
            self._check.config(text="True")
        else:
            self._check.config(text="False")
        if self._on_change is not None:
            self._on_change(self._var.get())

    def set(self, value):
        if value:
            self._var.set(1)
            self._check.config(text="True")
        else:
            self._check.config(text="False")
            self._var.set(0)

    def get(self):
        return bool(self._var.get())


class Relief(Choice):
    class ReliefItem(Choice.ChoiceItem):

        def render(self):
            if not self.value:
                Label(self, width=2, **self.style.dark_text, bd=2).pack(side="left")
                Label(self, text="select", **self.style.dark_text).pack(side="left", padx=4)
            else:
                Label(self, relief=self.value, width=2, **self.style.dark_text, bd=2).pack(side="left")
                Label(self, text=self.value, **self.style.dark_text).pack(side="left", padx=4)

    def set_up(self):
        self._spinner.set_item_class(Relief.ReliefItem)
        self._spinner.set_values((
            '', "flat", "raised", "sunken", "groove", "ridge"
        ))


class Cursor(Choice):
    class CursorItem(Choice.ChoiceItem):

        def render(self):
            if not self.value:
                super().render()
                return
            Label(self, **self.style.dark_text, cursor=self.value,
                  text=self.value, anchor='w').pack(fill="both")

    def set_up(self):
        self._spinner.set_item_class(Cursor.CursorItem)
        self._spinner.set_values(('',) + all_supported_cursors())


class Bitmap(Choice):
    class BitmapItem(Choice.ChoiceItem):

        def render(self):
            if not self.value:
                Label(self, **self.style.dark_text, width=2).pack(side="left")
                Label(self, **self.style.dark_text, text="select").pack(side="left")
            else:
                Label(self, **self.style.dark_text, bitmap=self.value).pack(side="left")
                Label(self, **self.style.dark_text, text=self.value).pack(side="left")

    def set_up(self):
        self._spinner.set_item_class(Bitmap.BitmapItem)
        self._spinner.set_values(('',) + BUILTIN_BITMAPS)


class Layout(Choice):
    class LayoutItem(Choice.ChoiceItem):

        def render(self):
            Label(self, **self.style.dark_text, anchor="w",
                  text=f"{get_icon(self.value.icon)}  {self.value.name}").pack(fill="x")

    def set_up(self):
        self._spinner.set_item_class(Layout.LayoutItem)
        self._spinner.set_values(self.style_def.get("options"))

    def set(self, value):
        # Override default conversion of value to string by Choice class
        self._spinner.set(value)


class Color(Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.dark_highlight_active)
        self._entry = Entry(self, **self.style.dark_input)
        self._color_button = Frame(self, **self.style.dark_highlight_active, width=15, height=15)
        self._color_button.on_click(self._chooser)
        self._color_button.pack(side="left", padx=2)
        self._entry.pack(side="left", fill="x")
        self._entry.on_change(self._change)

    def _change(self, value=None):
        value = self._entry.get() if value is None else value
        val = self._parse_color(value)
        if val:
            self._color_button.config(bg=value)
            if self._on_change:
                self._on_change(value)

    def _parse_color(self, value):
        try:
            val = self.winfo_rgb(value)
        except Exception:
            return ""
        val = tuple(map(lambda x: round((x/65535)*255), val))
        return to_hex(val)

    def get(self):
        return self._entry.get()

    def set(self, value):
        self.adjust(value)

    def on_change(self, func, *args, **kwargs):
        super().on_change(func, *args, **kwargs)

    def adjust(self, value):
        self._entry.update_idletasks()
        self._entry.set(value)
        try:
            self._color_button.config(bg=value)
        except Exception:
            self._color_button.config(bg="#000000")

    def _chooser(self, *_):
        dialog = ColorDialog(self.window)
        dialog.update_idletasks()
        self.window.update_idletasks()
        dialog.post(self._color_button, side="auto", padding=4)
        if self.get().startswith("#"):
            dialog.set(self.get())
        elif self.get():
            dialog.set(self._parse_color(self.get()))
        dialog.on_change(self.adjust)


class TextMixin:

    def _change(self, *_):
        if self._on_change:
            self._on_change(self.get())

    def get(self):
        return self._entry.get()

    def set(self, value):
        self._entry.set(value)


class Text(TextMixin, Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        if style_def is None:
            style_def = {}
        self.config(**self.style.dark_highlight_active)
        self._entry = Entry(self, **self.style.dark_input)
        self._entry.pack(fill="x")
        self._entry.on_entry(self._change)
        if style_def.get("readonly", False):
            self._entry.config(state='disabled')


class Number(TextMixin, Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.dark_highlight_active)
        self._entry = SpinBox(self, from_=-9999, to=9999, **self.style.spinbox)
        self._entry.config(**self.style.no_highlight)
        self._entry.set_validator(numeric_limit, -9999, 9999)
        self._entry.pack(fill="x")
        self._entry.on_change(self._change)


class Duration(TextMixin, Editor):
    UNITS = ('ns', 'ms', 'sec', 'min', 'hrs')
    MULTIPLIER = {
        'ns': 1e-6, 'ms': 1, 'sec': 1e3, 'min': 6e4, 'hrs': 3.6e5
    }

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        if style_def is None:
            style_def = {}
        self.config(**self.style.dark_highlight_active)
        self._entry = SpinBox(self, from_=0, to=1e6, **self.style.spinbox)
        self._entry.config(**self.style.no_highlight)
        self._entry.set_validator(numeric_limit, 0, 1e6)
        self._entry.on_change(self._change)
        self._unit = Spinner(self, **self.style.dark_input)
        self._unit.config(**self.style.no_highlight, width=50)
        self._unit.set_item_class(Choice.ChoiceItem)
        self._unit.set_values(Duration.UNITS)
        self._metric = style_def.get("units", "ms")
        self._unit.set(self._metric)
        self._unit.pack(side="right")
        self._unit.on_change(self._change)
        self._entry.pack(side='left', fill="x")

    def get(self):
        if self._entry.get() == '':
            return ''
        else:
            m1 = self.MULTIPLIER.get(self._unit.get(), 1)  # Multiplier 1 converts to milliseconds, default is ms
            m2 = self.MULTIPLIER.get(self._metric, 1)  # Multiplier 2 converts to required units, default is ms
            return int((self._entry.get() * m1) / m2)


class Font(Editor):
    class FontItem(Choice.ChoiceItem):

        def render(self):
            label = Label(self, text=self.value, **self.style.dark_text, anchor="w")
            # label.config(font=(self.value, ))
            label.pack(side="left")

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(height=50, **self.style.dark_highlight_active)
        self._font = Spinner(self, **self.style.dark_input, width=110)
        self._font.config(**self.style.no_highlight)
        self._font.place(x=0, y=0, relwidth=0.7, height=24)
        self._font.set_item_class(Font.FontItem)
        self._font.set_values(system_fonts())
        self._font.on_change(self._change)
        self._size = SpinBox(self, from_=0, to=999, **self.style.spinbox, width=3, justify='right')
        self._size.config(**self.style.no_highlight)
        self._size.place(relx=0.7, y=0, relwidth=0.3, height=24)
        self._size.on_change(self._change)
        frame = Frame(self, **self.style.dark, height=25, width=150)
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

    def get(self):
        font_obj = FontStyle(
            family=self._font.get(), size=self._size.get(),
            weight="bold" if self._bold.get() else "normal",
            slant="italic" if self._italic.get() else "roman",
            overstrike=int(self._strike.get()),
            underline=int(self._underline.get()),
        )
        return font_obj

    def _change(self, *_):
        if self._on_change:
            self._on_change(self.get())

    def set(self, value):
        if not value:
            return
        try:
            font_obj = FontStyle(self, value)
        except Exception:
            return
        self._font.set(font_obj.cget("family"))
        self._size.set(font_obj.cget("size"))
        self._italic.set(True if font_obj.cget("slant") == "italic" else False)
        self._bold.set(True if font_obj.cget("weight") == "bold" else False)
        self._underline.set(font_obj.cget("underline"))
        self._strike.set(font_obj.cget("overstrike"))


class Dimension(Number):
    SHORT_FORMS = {
        "pixels": "px",
    }

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        if style_def is None:
            style_def = {}
        self._entry.config(from_=0, to=1e6)
        self._entry.set_validator(numeric_limit, 0, 1e6)
        self._entry.pack_forget()
        unit = self.SHORT_FORMS.get(style_def.get("units", "pixels"), 'px')
        Label(self, **self.style.dark_text_passive, text=unit).pack(side="right")
        self._entry.pack(side="left", fill="x")


class Anchor(Editor):

    def __init__(self, master, style_def):
        super().__init__(master, style_def)
        style_def = style_def if style_def else {}
        # This flag determines whether multiple anchors are allowed at a time
        self.multiple = style_def.get("multiple", True)  # set to True to obtain a sticky property editor
        self.config(width=150, height=110)
        self.n = ToggleButton(self, text="N", width=20, height=20)
        self.n.grid(row=0, column=0, columnspan=3, sticky='ns')
        self.w = ToggleButton(self, text='W', width=20, height=20)
        self.w.grid(row=1, column=0, sticky='ew')
        self.pad = Frame(self, width=60, height=60, **self.style.dark,  **self.style.dark_highlight_active)
        self.pad.grid(row=1, column=1, padx=1, pady=1)
        self.pad.grid_propagate(0)
        self.pad.grid_columnconfigure(0, minsize=60)
        self.pad.grid_rowconfigure(0, minsize=60)
        self.floating = Frame(self.pad, **self.style.dark_on_hover, width=20, height=20)
        self.floating.grid(row=0, column=0, pady=1, padx=1)
        self.e = ToggleButton(self, text="E", width=20, height=20)
        self.e.grid(row=1, column=2, sticky='ew')
        self.s = ToggleButton(self, text='S', width=20, height=20)
        self.s.grid(row=2, column=0, columnspan=3, sticky='ns')
        self.anchors = {
            "n": self.n, "w": self.w, "e": self.e, "s": self.s
        }
        self._order = ("n", "s", "e", "w")
        self._selected = []
        self._exclusive_pairs = ({"n", "s"}, {"e", "w"})
        self._is_multiple = re.compile(r'(.*[ns].*[ns])|(.*[ew].*[ew])')
        for anchor in self.anchors:
            self.anchors[anchor].on_change(self._change, anchor)

    def _is_exclusive_of(self, anchor1, anchor2):
        return {anchor1, anchor2} in self._exclusive_pairs

    def _change(self, _, anchor):
        if not self.multiple:
            self._sanitize(anchor)
        self._adjust()
        if self._on_change:
            self._on_change(self.get())

    def _sanitize(self, anchor):
        ex_anchor = [i for i in self.get() if self._is_exclusive_of(i, anchor)]
        if len(ex_anchor):
            self.anchors.get(ex_anchor[0]).set(False)

    def _adjust(self):
        sticky = '' if self.get() == 'center' else self.get()
        self.floating.grid(row=0, column=0, pady=1, padx=1, sticky=sticky)

    def get(self):
        anchor = ''.join([i for i in self._order if self.anchors[i].get()])
        # No anchor means center but only when we are acting as an anchor editor
        # if self.multiple is True then we are a stickiness editor and an empty string will suffice
        if anchor == '':
            if not self.multiple:
                return 'center'
        return anchor

    def set(self, value):
        # Ignore invalid values
        if self._is_multiple.match(str(value)) and not self.multiple:
            return
        # Assume no anchor means center
        value = '' if value == 'center' else value
        for anchor in str(value):
            self.anchors.get(anchor).set(False)
            if self.anchors.get(anchor):
                self.anchors.get(anchor).set(True)
        self._adjust()


class Image(Text):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self._picker = Button(self, **self.style.dark_button, width=25, height=25, text="...")
        self._entry.pack_forget()
        self._picker.pack(side="right")
        self._entry.pack(side="left", fill="x")
        self._picker.on_click(self._pick)

    def _pick(self, *_):
        path = filedialog.askopenfilename(parent=self)
        if path:
            self._entry.set(path)
            if self._on_change:
                self._on_change(path)


class Variable(Choice):
    class VariableChoiceItem(Choice.ChoiceItem):

        def render(self):
            if self.value:
                item = VariableItem(self, self.value)
                item.pack(fill="both")
                item.pack_propagate(0)
            else:
                Label(self, text="", **self.style.dark_text).pack(fill="x")

    def set_up(self):
        var_manager: VariablePane = VariablePane.get_instance()
        var_manager.register_editor(self)
        values = [i.var for i in var_manager.variables]
        self._spinner.set_item_class(Variable.VariableChoiceItem)
        self._spinner.set_values((
            '', *values,
        ))

    def set(self, value):
        # Override default conversion of value to string by Choice class
        var_manager: VariablePane = VariablePane.get_instance()
        var = list(filter(lambda x: x.var._name == value, var_manager.variables))
        if len(var):
            value = var[0].var
        self._spinner.set(value)

    def on_var_add(self, var):
        self._spinner.add_values(var)

    def on_var_delete(self, var):
        self._spinner.remove_value(var)

    def destroy(self):
        VariablePane.get_instance().unregister_editor(self)
        super().destroy()


class Stringvariable(Variable):
    # TODO Check for any instances where class is needed otherwise delete

    def set_up(self):
        var_manager: VariablePane = VariablePane.get_instance()
        # filter to obtain only string variables
        var_manager.register_editor(self)
        values = [i.var for i in var_manager.variables if i.var.__class__ == StringVar]
        self._spinner.set_item_class(Variable.VariableChoiceItem)
        self._spinner.set_values((
            '', *values,
        ))


def get_editor(parent, definition):
    type_ = definition.get("type").capitalize()
    editor = getattr(sys.modules[__name__], type_, Text)
    return editor(parent, definition)


class StyleItem(Frame):

    def __init__(self, parent, style_definition, on_change=None):
        super().__init__(parent.body)
        self.definition = style_definition
        self.name = style_definition.get("name")
        self.config(**self.style.dark)
        self._label = Label(self, **parent.style.dark_text_passive, text=style_definition.get("display_name"),
                            anchor="w")
        self._label.grid(row=0, column=0, sticky='ew')
        # self._label.config(**parent.style.dark_highlight_active)
        self._editor = get_editor(self, style_definition)
        self._editor.grid(row=0, column=1, sticky='ew')
        self.grid_columnconfigure(1, weight=1, uniform=1)
        self.grid_columnconfigure(0, weight=1, uniform=1)
        self._on_change = on_change
        self._editor.set(style_definition.get("value"))
        self._editor.on_change(self._change)

    def _change(self, value):
        if self._on_change:
            self._on_change(self.name, value)

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda name, val: callback(name, val, *args, **kwargs)

    def hide(self):
        self.grid_propagate(False)
        self.configure(height=0, width=0)

    def show(self):
        self.grid_propagate(True)

    def set(self, value):
        self._editor.set(value)


if __name__ == '__main__':
    root = Application()
    root.load_styles("../../hoverset/ui/themes/default.css")
    boolean = Boolean(root)
    boolean.pack(side="top")

    relief = Relief(root)
    relief.pack(side="top")
    relief.on_change(lambda x: print(x))
    relief.set("groove")

    cursor = Cursor(root)
    cursor.pack(side="top")
    cursor.set("spider")

    bitmap = Bitmap(root)
    bitmap.pack(side="top")
    bitmap.set("hourglass")

    choice = Choice(root, {'options': ("orange", "red", "yellow")})
    choice.pack(side="top")
    choice.set("oran")

    color = Color(root)
    color.pack(side="top")
    color.on_change(lambda x: print(x))
    color.set("#dfdf45")

    text = Text(root)
    text.pack(side="top")
    text.on_change(lambda x: print(x))
    text.set("This is a sample")

    number = Number(root)
    number.pack(side="top")
    number.on_change(lambda x: print(x))
    number.set(456)

    duration = Duration(root, {"units": "ms"})
    duration.pack(side="top")
    duration.on_change(lambda x: print(x))
    duration.set(456)

    anc = Anchor(root, {"units": "ms"})
    anc.pack(side="top")
    anc.on_change(lambda x: print(x))
    anc.set('nswe')

    font = Font(root)
    font.pack(side="top")
    font.on_change(lambda x: print(x.configure()))
    font.set("TkDefaultFont")
    root.mainloop()
