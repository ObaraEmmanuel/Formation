from tkinter import Label, Entry, StringVar, Frame, Canvas, ttk, Menu, Toplevel
from functools import wraps
import re

UNICODE_HEXADECIMAL = re.compile(r'[0-9a-f]{1,4}$')


class ActionNotifier(Toplevel):
    DELAY = 50

    def __init__(self, master, event, command=None, **cnf):
        super().__init__(master)
        self.wm_overrideredirect(True)
        self.attributes("-alpha", 0)
        Label(self, cnf).pack()
        self.current_opacity = 1
        self.initialized = False
        self.event = event
        if command:
            command()
        self.after(ActionNotifier.DELAY, self.__fade_up())

    @staticmethod
    def bind_event(sequence: str, widget, command, **cnf):
        widget.bind(sequence, lambda event: ActionNotifier(None, event, command, **cnf))
        return widget

    def __fade_up(self):
        if self.current_opacity == 0:
            self.destroy()
            return
        if not self.initialized:
            self.update_idletasks()
            width, height = self.winfo_width(), self.winfo_height()
            self._set_position(self.event.x_root - width / 2, self.event.y_root - height + 4)
            self.initialized = True
        self.current_opacity -= 0.05
        self.attributes("-alpha", self.current_opacity)
        self.update_idletasks()
        x, y = self.winfo_rootx(), self.winfo_rooty() - 1
        self._set_position(x, y)
        self.after(ActionNotifier.DELAY, self.__fade_up)

    def _set_position(self, x, y):
        self.geometry("+{}+{}".format(*list(map(int, [x, y]))))


class NavControl(Label):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self["bg"] = initial_bg = "#5a5a5a"
        self["fg"] = initial_fg = "#f7f7f7"
        self.config(height=3, width=5, cursor="hand2")
        self.bind('<Enter>', lambda ev: self.config(bg="#f7f7f7", fg="#5a5a5a"))
        self.bind('<Leave>', lambda ev: self.config(bg=initial_bg, fg=initial_fg))
        self.bind('<Button-1>', lambda ev: self.on_click())
        self.run = None

    def on_click(self):
        if self.run:
            self.run()


class HexadecimalIntegerControl(Entry):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self._data = StringVar()
        self["textvariable"] = self._data
        self.config(
            validate='all',
            validatecommand=(
                self.register(self.validator), '%P'
            )
        )

    def get(self) -> int:
        val = self._data.get()
        if val.isdigit():
            return int(val)
        if re.match(UNICODE_HEXADECIMAL, val):
            return int(val, 16)
        return 0

    def set(self, value: str):
        if self.validator(value):
            self._data.set(value)

    def validator(self, value: str) -> bool:
        if value == "":
            return True
        if value.isdigit():
            if int(value) <= 0xffff:
                return True
        if re.match(UNICODE_HEXADECIMAL, value):
            return True
        return False


def text_required(func):
    """
    Decorates Grid class methods that require a actively displaying grid to work.
    :param func:
    :return:
    """

    @wraps(func)
    def wrap(self, *args):
        if not self.text:
            pass
        else:
            return func(self, *args)

    return wrap


class Grid(Label):

    def __init__(self, app, **cnf):
        super().__init__(app.body, **cnf)
        self.app = app
        self.config(bg="#f7f7f7")
        self.bind('<Enter>', lambda ev: self.hover(True))
        self.bind('<Leave>', lambda ev: self.hover(False))
        self.bind('<Button-1>', lambda ev: self.lock())
        self.bind('<Button-3>', lambda ev: self.request_menu(ev))
        self.text = ""
        self.is_locked = False

    @property
    def font(self):
        regex = re.compile(r'{(.+)}')
        if re.match(regex, self['font']):
            return re.search(regex, self['font']).group(1)
        else:
            return self['font'].split()[0]

    @property
    def code_point(self):
        return ord(self['text'])

    def copy(self, flag: int):
        self.clipboard_clear()
        if flag == 0:
            # Copy unicode
            self.clipboard_append(self["text"])
        elif flag == 1:
            # Copy hexadecimal scalar
            self.clipboard_append(self.text.replace("0x", ""))
        elif flag == 2:
            # Copy code point
            self.clipboard_append(str(int(self.text, 16)))

    def set(self, value: int):
        if value is None:
            self["text"] = self.text = ""
            return
        self["text"] = chr(value)
        self.text = str(hex(value))

    @text_required
    def hover(self, flag=True):
        if flag:
            self["bg"] = "#bbb"
            self.app.activate_grid(self)
        elif not self.is_locked:
            self["bg"] = "#f7f7f7"

    def unlock(self):
        self.is_locked = False
        self.app.active_grid = None
        self['bg'] = "#f7f7f7"

    @text_required
    def request_menu(self, event=None):
        self.lock()
        self.app.request_context_menu(event)

    @text_required
    def lock(self):
        if self.app.active_grid:
            self.app.active_grid.unlock()
        self.is_locked = True
        self.app.active_grid = self
        self["bg"] = "#bbb"

    @property
    def data(self):
        return {
            "Font family": self.font,
            "Code point": str(int(self.text, 16)),
            "Hexadecimal scalar": self.text.replace("0x", ""),
            "Surrogate pair": "None",
            "Plane": "Basic Multilingual",
            "Block": "Unknown"
        }


class ContextMenu(Menu):

    def __init__(self):
        super().__init__()
        self.config(bg="#5a5a5a", tearoff=0, fg="#f7f7f7", activebackground="#f7f7f7",
                    activeforeground="#5a5a5a", bd=0, relief='flat', font='calibri 12',
                    disabledforeground="#6a6a6a")

    def load_actions(self, *actions):
        for action in actions:
            if action[0] == 'separator':
                self.add_separator()
            else:
                icon, label, command = action
                self.add_command(label='   '.join([icon, label]), command=command)


class KeyValueLabel(Frame):

    def __init__(self, master, key, value, **cnf):
        super().__init__(master, **cnf)
        self['bg'] = "#f7f7f7"
        self._key = Label(self, bg="#f7f7f7", fg="#5a5a5a", font=('calibri', 11), anchor='w', text=key)
        self._key.pack(side='left')
        self._val = Label(self, bg="#f7f7f7", fg="#bbb", font=('calibri', 11), anchor='w', text=value)
        self._val.pack(side='left')
        self._copy = Label(self, bg="#f7f7f7", fg="#5a5a5a", font=('calibri', 11), anchor='w', text='\ue923')
        self._copy.pack(side='right', padx=3)
        ActionNotifier.bind_event('<Button-1>', self._copy, self.copy,
                                  text="Copied {}".format(key), bg="#5a5a5a", fg="#f7f7f7")

    def copy(self, _=None):
        self.clipboard_clear()
        self.clipboard_append(self._val['text'])


class ScrolledGridHolder(Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.canvas = Canvas(self, highlightthickness=0, **cnf)
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scroll = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.scroll.pack(side='top', fill='x', expand=True)
        self.canvas['xscrollcommand'] = self.scroll.set
        self.body = Frame(self, bg=self['bg'])
        self.window = self.canvas.create_window(0, 0, anchor='nw', window=self.body)
        self.tk = self.body.tk
        self.bind('<Configure>', self.on_configure)
        self.event_generate('<Configure>')

    def on_configure(self, _):
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.canvas.update_idletasks()
