import tkinter as tk
import tkinter.ttk as ttk

from hoverset.ui.icons import get_icon
from studio.lib.layouts import NPanedLayoutStrategy
from studio.lib.menus import menu_options
from studio.lib.pseudo import PseudoWidget, Groups, Container, LabelFrameCorrection, TabContainer, PanedContainer


class Button(PseudoWidget, ttk.Button):
    display_name = 'Button'
    group = Groups.widget
    icon = get_icon("button")
    impl = ttk.Button

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Checkbutton(PseudoWidget, ttk.Checkbutton):
    display_name = 'Checkbutton'
    group = Groups.widget
    icon = get_icon("checkbutton")
    impl = ttk.Checkbutton

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Combobox(PseudoWidget, ttk.Combobox):
    display_name = 'Combobox'
    group = Groups.input
    icon = get_icon("combobox")
    impl = ttk.Combobox

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['readonly'])

    def set_name(self, name):
        self.set(name)


class Entry(PseudoWidget, ttk.Entry):
    display_name = 'Entry'
    group = Groups.input
    icon = get_icon("entry")
    impl = ttk.Entry

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self._var = tk.StringVar()
        self.state(['disabled'])
        self.config(textvariable=self._var)
        self.setup_widget()

    def set_name(self, name):
        self._var.set(name)


class Frame(Container, ttk.Frame):
    display_name = 'Frame'
    group = Groups.container
    icon = get_icon("frame")
    impl = ttk.Frame

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Label(PseudoWidget, ttk.Label):
    display_name = 'Label'
    group = Groups.widget
    icon = get_icon("text")
    impl = ttk.Label

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Labelframe(LabelFrameCorrection, Container, ttk.Labelframe):
    display_name = 'Labelframe'
    group = Groups.container
    icon = get_icon("labelframe")
    impl = ttk.Labelframe

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class LabeledScale(PseudoWidget, ttk.LabeledScale):
    display_name = 'LabeledScale'
    group = Groups.input
    icon = get_icon("scale")
    impl = ttk.LabeledScale

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])


class Menubutton(PseudoWidget, ttk.Menubutton):
    display_name = 'Menubutton'
    group = Groups.widget
    icon = get_icon("menubutton")
    impl = ttk.Menubutton

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)

    def create_menu(self):
        return super().create_menu() + menu_options(self)


class Notebook(TabContainer, ttk.Notebook):
    display_name = 'Notebook'
    group = Groups.container
    icon = get_icon("notebook")
    impl = ttk.Notebook

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class VerticalPanedWindow(PanedContainer, ttk.PanedWindow):
    display_name = 'VerticalPanedWindow'
    group = Groups.container
    icon = get_icon("flip_vertical")
    impl = ttk.PanedWindow

    def __init__(self, master, id_):
        super().__init__(master, orient=tk.VERTICAL)
        self.id = id_
        self.setup_widget()
        # Needs a modified PanedLayoutStrategy to work
        self.layout_strategy = NPanedLayoutStrategy(self)

    @property
    def properties(self):
        properties = dict(**super().properties)
        properties.pop("orient")
        return properties


class HorizontalPanedWindow(PanedContainer, ttk.PanedWindow):
    display_name = 'HorizontalPanedWindow'
    group = Groups.container
    icon = get_icon("flip_horizontal")
    impl = ttk.PanedWindow

    def __init__(self, master, id_):
        super().__init__(master, orient=tk.HORIZONTAL)
        self.id = id_
        self.setup_widget()
        # Needs a modified PanedLayoutStrategy to work
        self.layout_strategy = NPanedLayoutStrategy(self)

    @property
    def properties(self):
        properties = dict(**super().properties)
        properties.pop("orient")
        return properties


class Progressbar(PseudoWidget, ttk.Progressbar):
    display_name = 'Progressbar'
    group = Groups.widget
    icon = get_icon("progressbar")
    impl = ttk.Progressbar

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self._var = tk.IntVar()
        self.config(variable=self._var)
        self._var.set(40)
        self.setup_widget()


class Radiobutton(PseudoWidget, ttk.Radiobutton):
    display_name = 'Radiobutton'
    group = Groups.input
    icon = get_icon("radiobutton")
    impl = ttk.Radiobutton

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])

    def set_name(self, name):
        self.config(text=name)


class Scale(PseudoWidget, ttk.Scale):
    display_name = 'Scale'
    group = Groups.input
    icon = get_icon("scale")
    impl = ttk.Scale

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['readonly'])
        self.set(40)


class Scrollbar(PseudoWidget, ttk.Scrollbar):
    display_name = 'Scrollbar'
    group = Groups.widget
    icon = get_icon("play")
    impl = ttk.Scrollbar

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])


class Separator(PseudoWidget, ttk.Separator):
    display_name = 'Separator'
    group = Groups.widget
    icon = get_icon("play")
    impl = ttk.Separator

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Sizegrip(PseudoWidget, ttk.Sizegrip):
    display_name = 'Sizegrip'
    group = Groups.container
    icon = get_icon("sizegrip")
    impl = ttk.Sizegrip

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Spinbox(PseudoWidget, ttk.Spinbox):
    display_name = 'Spinbox'
    group = Groups.input
    icon = get_icon("play")
    impl = ttk.Spinbox

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])

    def set_name(self, name):
        self.config(text=name)


class Treeview(PseudoWidget, ttk.Treeview):
    display_name = 'Treeview'
    group = Groups.container
    icon = get_icon("treeview")
    impl = ttk.Treeview

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


widgets = (
    Button, Checkbutton, Combobox, Entry, Frame, HorizontalPanedWindow, Label, LabeledScale, Labelframe, Menubutton,
    Notebook, Progressbar, Radiobutton, Scale, Scrollbar, Separator, Sizegrip, Spinbox, Treeview, VerticalPanedWindow
)
