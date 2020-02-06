import tkinter as tk
from tkinter import *

from hoverset.ui.icons import get_icon
from studio.lib.pseudo import PseudoWidget, Groups, Container, LabelFrameCorrection


class Button(PseudoWidget, tk.Button):
    display_name = 'Button'
    group = Groups.widget
    icon = get_icon("button")
    impl = tk.Button

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Canvas(PseudoWidget, tk.Canvas):
    display_name = 'Canvas'
    group = Groups.container
    icon = get_icon("paint")
    impl = tk.Canvas

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def lift(self, above_this=None):
        tk.Misc.lift(self, above_this)


class Checkbutton(PseudoWidget, tk.Checkbutton):
    display_name = 'Checkbutton'
    group = Groups.widget
    icon = get_icon("checkbutton")
    impl = tk.Checkbutton

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Entry(PseudoWidget, tk.Entry):
    display_name = 'Entry'
    group = Groups.input
    icon = get_icon("entry")
    impl = tk.Entry

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self._var = tk.StringVar()
        self.config(textvariable=self._var, state="disabled")
        self.setup_widget()

    def set_name(self, name):
        self._var.set(name)


class Frame(Container, tk.Frame):
    display_name = 'Frame'
    group = Groups.container
    icon = get_icon("frame")
    impl = tk.Frame

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Label(PseudoWidget, tk.Label):
    display_name = 'Label'
    group = Groups.input
    icon = get_icon("text")
    impl = tk.Label

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class LabelFrame(LabelFrameCorrection, Container, tk.LabelFrame):
    display_name = 'LabelFrame'
    group = Groups.container
    icon = get_icon("labelframe")
    impl = tk.LabelFrame

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Listbox(PseudoWidget, tk.Listbox):
    display_name = 'Listbox'
    group = Groups.container
    icon = get_icon("listbox")
    impl = tk.Listbox

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Menu(PseudoWidget, tk.Menu):
    display_name = 'Menu'
    group = Groups.container
    icon = get_icon("menu")
    impl = tk.Menu

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Menubutton(PseudoWidget, tk.Menubutton):
    display_name = 'Menubutton'
    group = Groups.widget
    icon = get_icon("menubutton")
    impl = tk.Menubutton

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Message(PseudoWidget, tk.Message):
    display_name = 'Message'
    group = Groups.input
    icon = get_icon("multiline_text")
    impl = tk.Message

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class PanedWindow(PseudoWidget, tk.PanedWindow):
    display_name = 'PanedWindow'
    group = Groups.container
    icon = get_icon("flip_horizontal")
    impl = tk.PanedWindow

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Radiobutton(PseudoWidget, tk.Radiobutton):
    display_name = 'Radiobutton'
    group = Groups.widget
    icon = get_icon("radiobutton")
    impl = tk.Radiobutton

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Scale(PseudoWidget, tk.Scale):
    display_name = 'Scale'
    group = Groups.input
    icon = get_icon("scale")
    impl = tk.Scale

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.config(from_=0, to=100)
        self.set(40)
        self.setup_widget()


class Scrollbar(PseudoWidget, tk.Scrollbar):
    display_name = 'Scrollbar'
    group = Groups.widget
    icon = get_icon("play")
    impl = tk.Scrollbar

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Spinbox(PseudoWidget, tk.Spinbox):
    display_name = 'Spinbox'
    group = Groups.input
    icon = get_icon("entry")
    impl = tk.Spinbox

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self._var = StringVar()
        self.config(textvariable=self._var)
        self.setup_widget()

    def set_name(self, name):
        self._var.set(name)


class Text(PseudoWidget, tk.Text):
    display_name = 'Text'
    group = Groups.input
    icon = get_icon("text")
    impl = tk.Text

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.insert(tk.FIRST, name)


class Toplevel(PseudoWidget, tk.Toplevel):
    display_name = 'Toplevel'
    group = Groups.container
    icon = get_icon("labelframe")
    impl = tk.Toplevel

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.title(name)


widgets = (
    Button, Canvas, Checkbutton, Entry, Frame, Label, LabelFrame, Listbox, Menu, Menubutton, Message, PanedWindow,
    Radiobutton, Scale, Scrollbar, Spinbox, Text, Toplevel
)
