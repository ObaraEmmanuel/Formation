"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
import logging
import os
import pathlib
import re
import sys
import tkinter as tk
from tkinter import BooleanVar, filedialog, StringVar

from hoverset.ui.icons import get_icon_image
from hoverset.ui.panels import FontInput, ColorPicker
from hoverset.ui.pickers import ColorDialog
from hoverset.ui.widgets import (CompoundList, Entry, SpinBox, Spinner, Frame, Application,
                                 Label, ToggleButton, Button, Checkbutton, suppress_change)
from hoverset.ui import widgets
from hoverset.util.color import to_hex
from hoverset.util.validators import numeric_limit, validate_any, is_empty, is_floating_numeric, is_signed, is_numeric
from studio.lib.properties import all_supported_cursors, BUILTIN_BITMAPS
from studio.lib.variables import VariableManager, VariableItem
from studio.preferences import get_active_pref


def get_display_name(style_def, pref):
    if pref and pref.exists("designer::descriptive_names"):
        if pref.get("designer::descriptive_names"):
            return style_def.get("display_name")
    return style_def.get("name")


class Editor(Frame):

    def __init__(self, master, style_def=None):
        super().__init__(master)
        self.style_def = style_def
        self.config(**self.style.surface, width=150, height=25)
        self.pack_propagate(False)
        self.grid_propagate(0)
        self._on_change = None

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda val: func(val, *args, **kwargs)

    def set(self, value):
        raise NotImplementedError()

    def get(self):
        raise NotImplementedError()

    def set_def(self, definition):
        self.style_def = definition


class Choice(Editor):
    # Some subclasses may not need to repopulate when definition changes
    # When extending this class take note of this for the sake of performance
    _setup_once = False

    class ChoiceItem(CompoundList.BaseItem):

        def render(self):
            if not self.value:
                Label(self, **self.style.text, text="select", anchor="w").pack(fill="both")
                return
            Label(self, **self.style.text, text=self._value, anchor="w").pack(fill="both")

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self._spinner = Spinner(self, **self.style.input)
        self._spinner.pack(fill="x")
        self._spinner.on_change(self.spinner_change)
        # initial set up is mandatory for all Choice subclasses
        self.set_up()

    def set_up(self):
        self._spinner.set_item_class(Choice.ChoiceItem)
        # update the values from definition provided
        values = self.style_def.get("options", ())
        if values:
            if not self.style_def.get('allow_empty', True):
                self._spinner.set_values(('', *values))
            else:
                self._spinner.set_values(values)

    def spinner_change(self, value):
        if self._on_change is not None:
            self._on_change(value)

    def set(self, value):
        # Convert to string as values of type _tkinter.Tcl_Obj are common in ttk and may cause unpredictable behaviour
        self._spinner.set(str(value))

    def get(self):
        return self._spinner.get()

    def set_def(self, definition):
        super().set_def(definition)
        if not self._setup_once:
            # repopulate only when needed for the sake of efficiency
            self.set_up()


class Boolean(Editor):
    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.surface, **self.style.highlight_active)
        self._var = BooleanVar()
        self._var.trace('w', self.check_change)
        self._check = Checkbutton(self, text='')
        self._check['variable'] = self._var
        self._check.pack(fill="x")

    def check_change(self, *_):
        self._check.config(text=str(self._var.get()))
        if self._on_change is not None:
            self._on_change(self._var.get())

    @suppress_change
    def set(self, value):
        self._var.set(bool(value))
        self._check.config(text=str(self._var.get()))

    def get(self):
        return bool(self._var.get())


class Relief(Choice):
    _setup_once = True

    class ReliefItem(Choice.ChoiceItem):

        def render(self):
            if not self.value:
                Label(self, width=2, **self.style.text, bd=2).pack(side="left")
                Label(self, text="select", **self.style.text).pack(side="left", padx=4)
            else:
                Label(self, relief=self.value, width=2, **self.style.text, bd=2).pack(side="left")
                Label(self, text=self.value, **self.style.text).pack(side="left", padx=4)

    def set_up(self):
        self._spinner.set_item_class(Relief.ReliefItem)
        self._spinner.set_values((
            '', "flat", "raised", "sunken", "groove", "ridge"
        ))


class Cursor(Choice):
    _setup_once = True

    class CursorItem(Choice.ChoiceItem):

        def render(self):
            if not self.value:
                super().render()
                return
            Label(self, **self.style.text, cursor=self.value,
                  text=self.value, anchor='w').pack(fill="both")

    def set_up(self):
        self._spinner.set_item_class(Cursor.CursorItem)
        self._spinner.set_values(('',) + all_supported_cursors())


class Bitmap(Choice):
    _setup_once = True

    class BitmapItem(Choice.ChoiceItem):

        def render(self):
            if not self.value:
                Label(self, **self.style.text, width=2).pack(side="left")
                Label(self, **self.style.text, text="select").pack(side="left")
            else:
                Label(self, **self.style.text, bitmap=self.value).pack(side="left")
                Label(self, **self.style.text, text=self.value).pack(side="left")

    def set_up(self):
        self._spinner.set_item_class(Bitmap.BitmapItem)
        self._spinner.set_values(('',) + BUILTIN_BITMAPS)


class Layout(Choice):
    _setup_once = True

    class LayoutItem(Choice.ChoiceItem):

        def render(self):
            Label(self, **self.style.text, anchor="w", image=get_icon_image(self.value.icon, 14, 14),
                  text=" " + self.value.name, compound='left').pack(fill="x")

    def set_up(self):
        self._spinner.set_item_class(Layout.LayoutItem)
        self._spinner.set_values(self.style_def.get("options"))

    def set(self, value):
        # Override default conversion of value to string by Choice class
        if isinstance(value, str):
            for opt in self.style_def.get("options"):
                if opt.name == value:
                    self._spinner.set(opt)
                    return
        self._spinner.set(value)


class Color(Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.highlight_active)
        self._entry = Entry(self, **self.style.input, **self.style.no_highlight)
        self._color_button = Label(self, relief='groove', bd=1)
        self._color_button.bind('<ButtonRelease-1>', self._chooser)
        self._color_button.place(x=2, y=2, width=20, height=20)
        self._picker = ColorPicker(self, **self.style.button)
        self._picker.place(relx=1, x=-22, y=0, width=20, height=20)
        self._picker.on_pick(self._pick)
        self._entry.place(x=22, y=0, relheight=1, relwidth=1, width=-46)
        self._entry.on_change(self._change)

    def _change(self, value=None):
        value = self._entry.get() if value is None else value
        val = self._parse_color(value)
        if val is not None:
            self._color_button.config(bg=value or self._entry["bg"])
            if self._on_change:
                self._on_change(value)

    def _pick(self, value):
        self.set(value)
        self._change(value)

    def _parse_color(self, value):
        if value == "" and self.style_def.get("allow_transparent", False):
            return value
        try:
            val = self.winfo_rgb(value)
        except Exception:
            return None
        val = tuple(map(lambda x: round((x / 65535) * 255), val))
        return to_hex(val)

    def get(self):
        return self._entry.get()

    @suppress_change
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
            self._color_button.config(bg=self._entry["bg"])

    def _chooser(self, *_):
        if self.get().startswith("#"):
            colour = self.get()
        elif self.get():
            colour = self._parse_color(self.get())
        else:
            colour = "#000000"
        dialog = ColorDialog(self.window, self._color_button, colour)
        dialog.set(colour)
        dialog.update_idletasks()
        self.window.update_idletasks()
        dialog.on_change(self.adjust)


class TextMixin:

    def dnd_init(self):
        self._entry.register_drop_target('*')
        self._entry.bind("<<Drop>>", lambda e: [self._entry.set(e.data), self._change()])

    def _change(self, *_):
        if self._on_change:
            self._on_change(self.get())

    def get(self):
        return self._entry.get()

    @suppress_change
    def set(self, value):
        self._entry.set(value)

    def set_def(self, definition):
        if definition.get("readonly", False):
            self._entry.config(state='disabled')
        else:
            self._entry.config(state="normal")
        super().set_def(definition)


class Text(TextMixin, Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.highlight_active)
        self._entry = Entry(self, **self.style.input)
        self._entry.configure(**self.style.no_highlight)
        self._entry.pack(fill="x")
        self._entry.on_entry(self._change)
        self.dnd_init()
        self.set_def(style_def)


class Textarea(TextMixin, Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.highlight_active, height=60)
        self._entry = widgets.Text(self, **self.style.textarea)
        self._entry.configure(**self.style.no_highlight)
        self._entry.pack(fill="x")
        self._entry.on_change(self._change)
        self.dnd_init()
        self.set_def(style_def)

    def get(self):
        return self._entry.get_all()


class Number(TextMixin, Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.highlight_active)
        self._entry = SpinBox(self, from_=-9999, to=9999, **self.style.spinbox)
        self._entry.config(**self.style.no_highlight)
        # self._entry.set_validator(numeric_limit, -9999, 9999)
        self._entry.pack(fill="x")
        self._entry.on_change(self._change)
        self.set_def(style_def)

    def validator(self):
        return validate_any(is_numeric, is_empty, is_signed)

    def set_def(self, definition):
        super(Number, self).set_def(definition)
        from_ = definition.get("from")
        to = definition.get("to")
        self._entry.config(from_=from_, to=to)
        if from_ is None and to is None:
            # validate without limits
            self._entry.set_validator(self.validator())
        else:
            self._entry.set_validator(numeric_limit, from_, to, self.validator())


class Float(Number):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.set_def(style_def)

    def validator(self):
        return validate_any(is_floating_numeric, is_empty, is_signed)


class Duration(TextMixin, Editor):
    UNITS = ('ns', 'ms', 'sec', 'min', 'hrs')
    MULTIPLIER = {
        'ns': 1e-6, 'ms': 1, 'sec': 1e3, 'min': 6e4, 'hrs': 3.6e5
    }

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.highlight_active)
        self._entry = SpinBox(self, from_=0, to=1e6, **self.style.spinbox)
        self._entry.config(**self.style.no_highlight)
        self._entry.set_validator(numeric_limit, 0, None)
        self._entry.on_change(self._change)
        self._unit = Spinner(self, **self.style.input)
        self._unit.config(**self.style.no_highlight, width=50)
        self._unit.set_item_class(Choice.ChoiceItem)
        self._unit.set_values(Duration.UNITS)
        self._unit.pack(side="right")
        self._unit.on_change(self._change)
        self._entry.pack(side='left', fill="x", expand=True)
        self.set_def(style_def)

    def set_def(self, definition):
        super().set_def(definition)
        self._metric = definition.get("units", "ms")
        self._unit.set(self._metric)

    def get(self):
        if self._entry.get() == '':
            return ''
        m1 = self.MULTIPLIER.get(self._unit.get(), 1)  # Multiplier 1 converts to milliseconds, default is ms
        m2 = self.MULTIPLIER.get(self._metric, 1)  # Multiplier 2 converts to required units, default is ms
        return int((self._entry.get() * m1) / m2)


class Font(Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(height=50, **self.style.highlight_active)
        self._input = FontInput(self)
        self._input.pack(fill='both', expand=True)
        self.set_def(style_def)

    def on_change(self, func, *args, **kwargs):
        self._input.on_change(lambda v: func(self.get(), *args, **kwargs))

    def get(self):
        if self.style_def.get("string_output", True):
            return self._input.get_str()
        return self._input.get_tuple()

    def set(self, value):
        self._input.set(value)


class Dimension(TextMixin, Editor):
    SHORT_FORMS = {
        "px": "",
        "cm": "c",
        "in": "i",
        "mm": "m",
        "pts": "p"
    }

    # a reverse of the short forms above to simplify lookup
    # to be computed later
    REVERSE_SF = None

    parse_expr = re.compile(r'^([-+]?\d+(?:.\d+)?) *([cimp]?)$')

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self.config(**self.style.highlight_active)
        self._entry = SpinBox(self, from_=0, to=1e6, **self.style.spinbox)
        self._entry.config(**self.style.no_highlight)
        self._entry.on_change(self._change)
        self._unit = Spinner(self, **self.style.input)
        self._unit.config(**self.style.no_highlight, width=50)
        self._unit.set_item_class(Choice.ChoiceItem)
        self._unit.set_values(list(Dimension.SHORT_FORMS.keys()))
        self._unit.pack(side="right")
        self._unit.on_change(self._change)
        self.set_def(style_def)
        self._entry.pack(side="left", fill="x", expand=True)

    def set_def(self, definition):
        super().set_def(definition)
        self._metric = definition.get("units", "px")
        if self._metric in ("char", "line"):
            self._unit.set_values((self._metric,))
            self._unit.set(self._metric)
            self._unit.disabled(True)
        else:
            self._unit.set_values(list(Dimension.SHORT_FORMS.keys()))
            self._unit.disabled(False)
            self._unit.set(self._metric)

        if definition.get("negative", False):
            self._entry.set_validator(self._validator())
        else:
            self._entry.set_validator(numeric_limit, 0, None, self._validator())

    def _validator(self):
        return validate_any(
            is_numeric if self.style_def.get("float", False) else is_floating_numeric,
            is_empty,
            is_signed
        )

    def get(self):
        if self._entry.get() == '':
            return ''
        return f"{self._entry.get()}{Dimension.SHORT_FORMS.get(self._unit.get(), '')}"

    @suppress_change
    def set(self, value):
        match = Dimension.parse_expr.match(str(value))
        if match:
            if self.style_def.get("units") in ('char', 'line'):
                self._entry.set(match.group(1))
                return
            num, metric = match.groups()
            self._entry.set(num)
            self._unit.set(self._reverse_lookup(metric))
        elif not value:
            self._entry.set(value)
        else:
            logging.error("%: malformed dimension '%s'", self.style_def['name'], value)

    @classmethod
    def _reverse_lookup(cls, metric):
        if not cls.REVERSE_SF:
            cls.REVERSE_SF = {cls.SHORT_FORMS[k]: k for k in cls.SHORT_FORMS}
        return cls.REVERSE_SF.get(metric, '')


class Anchor(Editor):

    def __init__(self, master, style_def):
        super().__init__(master, style_def)
        self.set_def(style_def)
        self.config(width=150, height=110)
        self.n = ToggleButton(self, text="N", width=20, height=20)
        self.n.grid(row=0, column=0, columnspan=3, sticky='ns')
        self.w = ToggleButton(self, text='W', width=20, height=20)
        self.w.grid(row=1, column=0, sticky='ew')
        self.pad = Frame(self, width=60, height=60, **self.style.surface, **self.style.highlight_active)
        self.pad.grid(row=1, column=1, padx=1, pady=1)
        self.pad.grid_propagate(0)
        self.pad.grid_columnconfigure(0, minsize=60)
        self.pad.grid_rowconfigure(0, minsize=60)
        self.floating = Frame(self.pad, **self.style.accent, width=20, height=20)
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
        if ex_anchor:
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
        # bypass the special value 'center' before subjecting to validity check
        value = '' if value == 'center' else str(value)
        # Ignore invalid values
        if self._is_multiple.match(str(value)) and not self.multiple:
            return
        # Assume no anchor means center
        for anchor in self.anchors:
            self.anchors.get(anchor).set(anchor in value)

        self._adjust()

    def set_def(self, definition):
        # This flag determines whether multiple anchors are allowed at a time
        # set to True to obtain a sticky property editor
        self.multiple = definition.get("multiple", True)
        super().set_def(definition)


class Image(Text):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        self._picker = Button(self, **self.style.button, width=25, height=25, text="...")
        self._entry.pack_forget()
        self._picker.pack(side="right")
        self._entry.pack(side="left", fill="x")
        self._picker.on_click(self._pick)

    def _change(self, *_):
        # TODO Add indicator for invalid paths
        super()._change()

    def _pick(self, *_):
        path = filedialog.askopenfilename(parent=self)
        if path:
            try:
                path_opt = get_active_pref(self).get("designer::image_path")
            except:
                path_opt = "absolute"

            if path_opt == "absolute":
                # use path as is (absolute)
                pass
            else:
                path = pathlib.Path(path)
                current = pathlib.Path(os.getcwd())
                if (current in path.parents and path_opt == "mixed") or path_opt == "relative":
                    # use relative path
                    try:
                        # use relative path if possible
                        path = os.path.relpath(path, current)
                    except ValueError:
                        pass
                path = str(path)
            self._entry.set(path)
            if self._on_change:
                self._on_change(path)


class Variable(Choice):
    _setup_once = True

    class VariableChoiceItem(Choice.ChoiceItem):

        def render(self):
            if self.value:
                item = VariableItem(self, self.value)
                item.pack(fill="both")
                item.pack_propagate(0)
            else:
                Label(self, text="", **self.style.text).pack(fill="x")

    def set_up(self):
        VariableManager.editors.append(self)
        values = [i.var for i in VariableManager.variables()]
        self._spinner.set_item_class(Variable.VariableChoiceItem)
        self._spinner.set_values((
            '', *values,
        ))

    def set(self, value):
        # Override default conversion of value to string by Choice class
        var = list(filter(lambda x: x.name == value, VariableManager.variables()))
        # if variable does not match anything in the variable manager presume as empty
        value = var[0].var if var else ''
        self._spinner.set(value)

    def on_var_add(self, var):
        self._spinner.add_values(var)

    def on_var_delete(self, var):
        self._spinner.remove_value(var)

    def on_var_context_change(self):
        values = [i.var for i in VariableManager.variables()]
        self._spinner.set_values((
            '', *values,
        ))

    def destroy(self):
        VariableManager.remove_editor(self)
        super().destroy()


class Stringvariable(Variable):
    # TODO Check for any instances where class is needed otherwise delete

    def set_up(self):
        # filter to obtain only string variables
        VariableManager.editors.append(self)
        values = [i.var for i in VariableManager.variables() if i.var.__class__ == StringVar]
        self._spinner.set_item_class(Variable.VariableChoiceItem)
        self._spinner.set_values((
            '', *values,
        ))

    def on_var_context_change(self):
        values = [i.var for i in VariableManager.variables() if i.var.__class__ == StringVar]
        self._spinner.set_values((
            '', *values,
        ))


class Widget(Choice):
    _setup_once = False

    class WidgetChoiceItem(Choice.ChoiceItem):

        def render(self):
            if self.value:
                item = Label(
                    self, text=f" {self.value.id}", **self.style.text,
                    image=get_icon_image(self.value.icon, 15, 15),
                    compound="left", anchor="w"
                )
                item.pack(fill="x")
            else:
                Label(self, text="", **self.style.text).pack(fill="x")

    def _get_objs(self):
        master = tk._default_root
        if not hasattr(master, "get_widgets"):
            master = self.winfo_toplevel()

        if hasattr(master, "get_widgets"):
            include = self.style_def.get("include", ())
            exclude = self.style_def.get("exclude", ())
            objs = master.get_widgets(criteria=self.style_def.get("criteria"))
            if include:
                objs = list(filter(lambda x: isinstance(x, tuple(include)), objs))
            if exclude:
                objs = list(filter(lambda x: not isinstance(x, tuple(exclude)), objs))
            return objs
        return []

    def set_up(self):
        objs = self._get_objs()
        self._spinner.set_item_class(Widget.WidgetChoiceItem)
        self._spinner.set_values((
            '', *objs,
        ))

    def set(self, value):
        if isinstance(value, tk.Widget):
            self._spinner.set(value)
            return

        # Override default conversion of value to string by Choice class
        widget = list(filter(lambda x: x.id == value, self._get_objs()))
        # if widget does not match anything in the obj list presume as empty
        value = widget[0] if widget else ''
        self._spinner.set(value)


def get_editor(parent, definition):
    if "compose" in definition:
        type_ = "Compose"
    else:
        type_ = definition.get("type").capitalize()

    editor = getattr(sys.modules[__name__], type_, Text)
    return editor(parent, definition)


class Compose(Editor):

    def __init__(self, master, style_def=None):
        super().__init__(master, style_def)
        items = style_def.get("compose", [])
        self.as_dict = style_def.get("as_dict", True)
        row = 0
        self.pref = get_active_pref(self)
        height = 25 * len(items)
        max_columns = 1
        self.columnconfigure(0, weight=1)
        self.editors = {}

        for item in filter(lambda x: isinstance(x, list), items):
            column = 0
            for row_item in item:
                self.columnconfigure(column, weight=1)
                self._create_editor(row_item, row, column, 1)
                column += 1
            height += 25
            max_columns = max(max_columns, column)
            row += 2

        for item in filter(lambda x: isinstance(x, dict), items):
            self._create_editor(item, row, 0, max_columns)
            height += 25
            row += 2

        self.config(height=height)

    def _create_editor(self, definition, row, column, columnspan):
        Label(
            self,
            **self.style.text_passive,
            anchor="w", text=get_display_name(definition, self.pref)
        ).grid(row=row, column=column, columnspan=columnspan)
        editor = get_editor(self, definition)
        self.editors[definition["name"]] = editor
        editor.grid(row=row + 1, column=column, columnspan=columnspan, sticky='ew')
        editor.on_change(self._change)

    def _change(self, _):
        if self._on_change:
            self._on_change(self.get())

    def set(self, value):
        if not value:
            return
        if self.as_dict:
            for k, v in value.items():
                if k in self.editors:
                    self.editors[k].set(v)
        else:
            if isinstance(value, str):
                value = value.split(' ')
            if not value:
                value = [''] * len(self.editors)

            for editor, v in zip(self.editors.values(), value):
                editor.set(v)

    def get(self):
        if self.as_dict:
            return {k: e.get() for k, e in self.editors.items()}
        return [e.get() for e in self.editors.values()]


class StyleItem(Frame):

    def __init__(self, parent, style_definition, on_change=None):
        super().__init__(parent.body)
        self.pref = get_active_pref(self)
        self.definition = style_definition
        self.name = style_definition.get("name")
        self.config(**self.style.surface)
        display = get_display_name(style_definition, self.pref)
        self._label = Label(self, **parent.style.text_passive, text=display,
                            anchor="w")
        self._label.grid(row=0, column=0, sticky='new')
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

    def set_label(self, name):
        self._label.configure(text=name)

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda name, val: callback(name, val, *args, **kwargs)

    def hide(self):
        self.grid_propagate(False)
        self.configure(height=0, width=0)

    def show(self):
        self.grid_propagate(True)

    def set(self, value):
        self._editor.set(value)

    def set_silently(self, value):
        # disable ability to trigger on change before setting value
        prev_callback = self._on_change
        self._on_change = None
        self.set(value)
        self._on_change = prev_callback


if __name__ == '__main__':
    root = Application()
    root.load_styles("../../hoverset/ui/themes/default.css")
    boolean = Boolean(root)
    boolean.pack(side="top")
    boolean.on_change(print)
    boolean.set(True)

    relief = Relief(root)
    relief.pack(side="top")
    relief.on_change(print)
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
    color.on_change(print)
    color.set("#dfdf45")

    text = Textarea(root, {})
    text.pack(side="top")
    text.on_change(print)
    text.set("This is a sample")

    number = Number(root, {})
    number.pack(side="top")
    number.on_change(print)
    number.set(456)

    duration = Duration(root, {"units": "ms"})
    duration.pack(side="top")
    duration.on_change(print)
    duration.set(456)

    anc = Anchor(root, {"units": "ms"})
    anc.pack(side="top")
    anc.on_change(print)
    anc.set('nswe')

    dim = Dimension(root, {})
    dim.pack(side="top")
    dim.on_change(print)
    dim.set('40c')

    font = Font(root)
    font.pack(side="top")
    font.on_change(print)
    font.set("TkDefaultFont")
    root.mainloop()
