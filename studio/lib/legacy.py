import tkinter as tk

from studio.lib.pseudo import PseudoWidget, Groups, Container, PanedContainer


class Button(PseudoWidget, tk.Button):
    display_name = 'Button'
    group = Groups.widget
    icon = "button"
    impl = tk.Button

    DEF_OVERRIDES = {
        "state": {
            "options": ("normal", "active", "disabled")
        }
    }

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class Canvas(PseudoWidget, tk.Canvas):
    display_name = 'Canvas'
    group = Groups.container
    icon = "paint"
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
    icon = "checkbutton"
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
    icon = "entry"
    impl = tk.Entry

    DEF_OVERRIDES = {
        "state": {
            "options": ("normal", "readonly", "disabled")
        }
    }

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.insert(0, str(name))


class Frame(Container, tk.Frame):
    display_name = 'Frame'
    group = Groups.container
    icon = "frame"
    impl = tk.Frame

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Label(PseudoWidget, tk.Label):
    display_name = 'Label'
    group = Groups.widget
    icon = "text"
    impl = tk.Label

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class LabelFrame(Container, tk.LabelFrame):
    display_name = 'LabelFrame'
    group = Groups.container
    icon = "labelframe"
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
    icon = "listbox"
    impl = tk.Listbox

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Menu(PseudoWidget, tk.Menu):
    display_name = 'Menu'
    group = Groups.container
    icon = "menu"
    impl = tk.Menu

    def __init__(self, master, id_=None, **kw):
        super().__init__(master, **kw)
        if id_ is None:
            id_ = 'menu' + str(self.winfo_id())
        self.id = id_
        self.setup_widget()


class Menubutton(PseudoWidget, tk.Menubutton):
    display_name = 'Menubutton'
    group = Groups.widget
    icon = "menubutton"
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
    icon = "multiline_text"
    impl = tk.Message

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.config(text=name)


class PanedWindow(PanedContainer, tk.PanedWindow):
    display_name = 'PanedWindow'
    group = Groups.container
    icon = "flip_horizontal"
    impl = tk.PanedWindow

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Radiobutton(PseudoWidget, tk.Radiobutton):
    display_name = 'Radiobutton'
    group = Groups.input
    icon = "radiobutton"
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
    icon = "scale"
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
    icon = "play"
    impl = tk.Scrollbar

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()


class Spinbox(PseudoWidget, tk.Spinbox):
    display_name = 'Spinbox'
    group = Groups.input
    icon = "entry"
    impl = tk.Spinbox

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.insert(0, str(name))


class Text(PseudoWidget, tk.Text):
    display_name = 'Text'
    group = Groups.input
    icon = "text"
    impl = tk.Text

    DEF_OVERRIDES = {
        "wrap": {
            "type": "choice",
            "options": ("char", "word", "none")
        }
    }

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.insert(tk.END, name)


class Toplevel(PseudoWidget, tk.Toplevel):
    display_name = 'Toplevel'
    group = Groups.container
    icon = "labelframe"
    impl = tk.Toplevel

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

    def set_name(self, name):
        self.title(name)


widgets = (
    Button, Canvas, Checkbutton, Entry, Frame, Label, LabelFrame, Listbox, Menubutton, Message, PanedWindow,
    Radiobutton, Scale, Scrollbar, Spinbox, Text
)
