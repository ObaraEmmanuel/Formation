import tkinter as tk
import tkinter.ttk as ttk

from studio.lib.layouts import NPanedLayoutStrategy
from studio.lib.handles import LinearHandle
from studio.lib.pseudo import (
    PseudoWidget, Groups, Container, TabContainer, PanedContainer,
    _dimension_override
)


class Button(PseudoWidget, ttk.Button):
    display_name = 'Button'
    group = Groups.widget
    icon = "button"
    impl = ttk.Button

    DEF_OVERRIDES = _dimension_override

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Checkbutton(PseudoWidget, ttk.Checkbutton):
    display_name = 'Checkbutton'
    group = Groups.widget
    icon = "checkbox"
    impl = ttk.Checkbutton

    DEF_OVERRIDES = {
        "width": {
            "units": "line",
            "negative": True
        }
    }

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        # The default value of the variable is the checkbutton itself
        # This causes problems when the checkbutton is serialized
        self.configure(variable="")
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Combobox(PseudoWidget, ttk.Combobox):
    display_name = 'Combobox'
    group = Groups.input
    icon = "menubutton"
    impl = ttk.Combobox
    allow_direct_move = False

    DEF_OVERRIDES = {
        "state": {
            "options": ("readonly",)
        },
        **_dimension_override
    }

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.configure(cursor="")
        self.setup_widget()

    def set_name(self, name):
        self.set(name)


class Entry(PseudoWidget, ttk.Entry):
    display_name = 'Entry'
    group = Groups.input
    icon = "entry"
    impl = ttk.Entry
    allow_direct_move = False

    DEF_OVERRIDES = _dimension_override

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.insert(0, str(name))


class Frame(Container, ttk.Frame):
    display_name = 'Frame'
    group = Groups.container
    icon = "frame"
    impl = ttk.Frame

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Label(PseudoWidget, ttk.Label):
    display_name = 'Label'
    group = Groups.widget
    icon = "label"
    impl = ttk.Label

    DEF_OVERRIDES = {
        "width": {
            "units": "line",
            "negative": True
        }
    }

    # TODO handle special compound & image options

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Labelframe(Container, ttk.Labelframe):
    display_name = 'Labelframe'
    group = Groups.container
    icon = "labelframe"
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
    icon = "scale"
    impl = ttk.LabeledScale
    initial_dimensions = 150, 40
    allow_direct_move = False

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])


class Menubutton(PseudoWidget, ttk.Menubutton):
    display_name = 'Menubutton'
    group = Groups.widget
    icon = "menubutton"
    impl = ttk.Menubutton
    allow_direct_move = False

    DEF_OVERRIDES = _dimension_override

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Notebook(TabContainer, ttk.Notebook):
    display_name = 'Notebook'
    group = Groups.container
    icon = "tabs"
    impl = ttk.Notebook

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class VerticalPanedWindow(PanedContainer, ttk.PanedWindow):
    display_name = 'VerticalPanedWindow'
    group = Groups.container
    icon = "dock_vertical"
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

    def get_altered_options(self):
        options = super().get_altered_options()
        options['orient'] = str(self['orient'])
        return options


class HorizontalPanedWindow(PanedContainer, ttk.PanedWindow):
    display_name = 'HorizontalPanedWindow'
    group = Groups.container
    icon = "dock_horizontal"
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

    def get_altered_options(self):
        options = super().get_altered_options()
        options['orient'] = str(self['orient'])
        return options


class Progressbar(PseudoWidget, ttk.Progressbar):
    display_name = 'Progressbar'
    group = Groups.widget
    icon = "progressbar"
    impl = ttk.Progressbar
    initial_dimensions = 200, 20
    _temp_init_var = None

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        if not self._temp_init_var:
            self._temp_init_var = tk.IntVar()
            self._temp_init_var.set(40)
        self.config(variable=self._temp_init_var)
        self.config(variable="")
        self.setup_widget()


class Radiobutton(PseudoWidget, ttk.Radiobutton):
    display_name = 'Radiobutton'
    group = Groups.input
    icon = "radiobutton"
    impl = ttk.Radiobutton

    DEF_OVERRIDES = {
        "width": {
            "units": "line",
            "negative": True
        }
    }

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
    icon = "scale"
    impl = ttk.Scale
    initial_dimensions = 150, 20
    allow_direct_move = False

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['readonly'])
        self.set(40)


class Scrollbar(PseudoWidget, ttk.Scrollbar):
    display_name = 'Scrollbar'
    group = Groups.widget
    icon = "scrollbar"
    impl = ttk.Scrollbar
    initial_dimensions = 20, 100
    allow_direct_move = False

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])


class Separator(PseudoWidget, ttk.Separator):
    display_name = 'Separator'
    group = Groups.widget
    icon = "line"
    impl = ttk.Separator
    initial_dimensions = 150, 1
    handle_class = LinearHandle

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Sizegrip(Container, ttk.Sizegrip):
    display_name = 'Sizegrip'
    group = Groups.container
    icon = "frame"
    impl = ttk.Sizegrip

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Spinbox(PseudoWidget, ttk.Spinbox):
    display_name = 'Spinbox'
    group = Groups.input
    icon = "entry"
    impl = ttk.Spinbox
    allow_direct_move = False

    DEF_OVERRIDES = _dimension_override

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()
        self.state(['disabled'])


class Treeview(PseudoWidget, ttk.Treeview):
    display_name = 'Treeview'
    group = Groups.container
    icon = "treeview"
    impl = ttk.Treeview

    DEF_OVERRIDES = {
        "show": {
            "type": "choice",
            "options": ("tree", "headings", "tree headings")
        }
    }

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.configure(show="tree headings")
        self.setup_widget()


widgets = (
    Button, Checkbutton, Combobox, Entry, Frame, HorizontalPanedWindow, Label, LabeledScale, Labelframe, Menubutton,
    Notebook, Progressbar, Radiobutton, Scale, Scrollbar, Separator, Spinbox, Sizegrip, Treeview, VerticalPanedWindow
)
