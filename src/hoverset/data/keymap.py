# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import hoverset.data.actions as actions
from hoverset.data.preferences import SharedPreferences, Component
from hoverset.data.images import get_tk_image
from hoverset.platform import platform_is, LINUX
from hoverset.ui.widgets import Frame, Label, CompoundList
from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.menu import EnableIf


class Key:

    def __init__(self, label, *keycodes):
        self.label = label
        self._keycodes = frozenset(keycodes)

    def __eq__(self, other):
        if isinstance(other, Key):
            return self._keycodes == other._keycodes
        elif isinstance(other, int):
            return other in self._keycodes
        return False

    def __hash__(self):
        return hash(self._keycodes)

    def __add__(self, other):
        if isinstance(other, Key):
            return Key('{}+{}'.format(self.label, other.label), *self._keycodes, *other._keycodes)

    @property
    def keycode(self):
        return self._keycodes

    @classmethod
    def platform(cls, label, windows, linux):
        if platform_is(LINUX):
            return Key(label, linux)
        return Key(label, windows)


BlankKey = Key('')


class CharKey(Key):
    qwerty = "1234567890-=  QWERTYUIOP[]\r ASDFGHJKL;\'   ZXCVBNM,./"

    def __init__(self, alphanumeric: str):
        alphanumeric = alphanumeric.upper()
        if platform_is(LINUX):
            super().__init__(alphanumeric, 10 + self.qwerty.index(alphanumeric))
        else:
            super().__init__(alphanumeric, ord(alphanumeric))


class Symbol(Key):
    if platform_is(LINUX):
        _keycodes = {
            '\'': 48, '[': 34,
            '-': 20, '\\': 51,
            ',': 59, ']': 35,
            '.': 60, '`': 49,
            '/': 61, '=': 21,
            ';': 47,
        }
    else:
        _keycodes = {
            '\'': 222, '[': 219,
            '-': 189, '\\': 220,
            ',': 188, ']': 221,
            '.': 190, '`': 192,
            '/': 192, '=': 187,
            ';': 186,
        }

    def __init__(self, symbol: str):
        if len(symbol):
            symbol = symbol[:1]
            if symbol in self._keycodes:
                super().__init__(symbol, self._keycodes[symbol])
            else:
                raise ValueError('symbol {} not found'.format(symbol))
        else:
            raise ValueError('symbol must not be empty')


class KeyPad(Key):
    if platform_is(LINUX):
        _offset = 79
        _keys = '789-456+1230.'
    else:
        _offset = 96
        _keys = '0123456789*+ -./'

    def __init__(self, key):
        key = str(key)[:1]
        key = key.replace(' ', '')
        if key != '' and key in self._keys:
            super().__init__(key, self._offset + self._keys.index(key))
        else:
            raise ValueError('Invalid keypad key')


class _KeymapDispatch(type):
    """
    We need to ensure only one keymap handler exists for a given window
    """
    _windows = {}

    def __call__(cls, window, *args, **kwargs):
        if window not in cls._windows:
            cls._windows[window] = super(_KeymapDispatch, cls).__call__(window, *args, **kwargs)
        return cls._windows[window]


def function_key(number):
    if number > 12 or number < 1:
        raise ValueError("Function keys should be between 1 and 12 inclusive")
    if platform_is(LINUX):
        return Key('F{}'.format(number), 66 + number)
    return Key('F{}'.format(number), 111 + number)


class KeyMap(metaclass=_KeymapDispatch):
    ALT = Key.platform('Alt', 18, 64)
    BACKSPACE = Key.platform('Backspace', 8, 22)
    BREAK = Key.platform('Break', 3, 127)
    CANCEL = Key.platform('Cancel', 3, 127)
    CAPS_LOCK = Key.platform('CapsLock', 20, 66)
    CONTROL = CTRL = Key.platform('Ctrl', 17, 37)
    DELETE = Key.platform('Del', 46, 119)
    END = Key.platform('End', 35, 115)
    ESCAPE = Key.platform('Esc', 27, 9)
    ENTER = RETURN = Key.platform('Enter', 13, 36)
    F = function_key
    HOME = Key.platform('Home', 36, 110)
    INSERT = Key.platform('Insert', 45, 118)
    SHIFT = Key.platform('Shift', 16, 50)
    NUM_LCK = Key.platform('NumLock', 144, 77)
    PAGE_UP = PRIOR = Key.platform('PageUp', 33, 112)
    PAGE_DOWN = NEXT = Key.platform('PageUp', 34, 117)
    PAUSE = Key.platform('Pause', 19, 127)
    SPACE = Key.platform('Space', 32, 65)
    TAB = Key.platform('Tab', 9, 23)
    SCROLL_LCK = Key.platform('Scroll', 145, 78)
    DOWN = Key.platform('Down', 40, 116)
    LEFT = Key.platform('Left', 37, 113)
    RIGHT = Key.platform('Right', 39, 114)
    UP = Key.platform('Up', 38, 111)

    EVENT_MASK = {
        0x0004: CONTROL,
        0x20000: ALT,  # Windows
        0x0008: ALT,  # Linux
        0x0001: SHIFT,
        0x0002: CAPS_LOCK,

    }

    def __init__(self, window, **kwargs):
        self.window = window
        self.bindings = {}
        self.handler_map = {}

    def _bind(self, widget):
        widget.bind('<Key>', self._dispatch)
        # Alt key must be manually bound to work
        widget.bind('<Alt-Key>', self._dispatch)

    def bind_all(self):
        """
        Bind main widget to capture events from all over the application
        :return:
        """
        self.window.bind_all('<Key>', self._dispatch)
        # Alt key must be manually bound to work
        self.window.bind_all('<Alt-Key>', self._dispatch)

    def bind(self):
        """
        Bind main widget to capture only ite events
        :return:
        """
        self._bind(self.window)

    def bind_widget(self, widget):
        self._bind(widget)

    def _invoke(self, routine_key):
        # just call the routine directly since this is a simplified keymap
        routine_key()

    @classmethod
    def get_key(cls, event):
        key = None
        for mod in cls.EVENT_MASK:
            if event.state & mod:
                if key is None:
                    key = cls.EVENT_MASK[mod]
                else:
                    key += cls.EVENT_MASK[mod]
        # key symbols one character long are best displayed in upper case
        sym = event.keysym.upper() if len(event.keysym) == 1 else event.keysym
        main_key = Key(sym, event.keycode)
        key = main_key if key is None else key + main_key
        return key

    def _dispatch(self, event):
        key = self.get_key(event)
        if key in self.bindings:
            routine_key = self.bindings[key]
            self._invoke(routine_key)

    def add_shortcut(self, *handler_shortcut):
        for handler, shortcut in handler_shortcut:
            self.bindings[shortcut] = handler

    def add_routines(self, *routines):
        for routine in routines:
            self.bindings[routine.shortcut] = routine.invoke


class ShortcutManager(KeyMap):
    """
    Extended Keymap that fetches bindings from a config file and
    implicitly handles Routine - shortcut mapping

    :param window: A tkinter Toplevel window
    :param preferences: A SharedPreference object where bindings data is
        to be retrieved from
    """

    instances = []

    def __init__(self, window, preferences: SharedPreferences):
        super().__init__(window)
        ShortcutManager.instances.append(self)
        preferences.set_default('allow_hotkeys', True)
        preferences.set_default('hotkeys', {})
        self.preferences = preferences
        self.update_bindings()

    def add_routines(self, *routines):
        """
        Utility method that adds the routine to action manager for you
        and then binds the shortcut
        :param routines: a Routine object with the shortcut attribute set
        :return: None
        """
        for routine in routines:
            actions.add(routine)
            if routine.shortcut is None:
                continue
            if routine.key in self.reversed_bindings:
                # if shortcut is already set in bindings just ignore
                # setting shortcuts at this point is only important as defaults
                # just in case we have never bound that shortcut
                routine.shortcut = self.reversed_bindings.get(routine.key)
                continue
            self.bindings[routine.shortcut] = routine.key
            self.reversed_bindings[routine.key] = routine.shortcut

    def _dispatch(self, event):
        # allow dispatch if and only if hotkeys are allowed
        if self.preferences.get("allow_hotkeys"):
            super()._dispatch(event)

    def _invoke(self, routine_key):
        # Things get slightly complicated, we need to use the key to
        # access the actual method in the current program context
        # the method as returned by global actions module is a Routine object
        routine = actions.get_routine(routine_key)
        if routine:
            routine.invoke()

    def get_shortcut(self, routine_key):
        return self.reversed_bindings.get(routine_key)

    def update_bindings(self):
        # update binding dictionary with latest info
        # Bindings are stored with actions as keys since action keys are unique
        self.reversed_bindings = self.preferences.get('hotkeys')
        # For faster routing we use shortcut keys as the dict keys so we reverse
        self.bindings = {value: key for key, value in self.reversed_bindings.items()}

    def add_shortcut(self, handler, shortcut):
        # this method doesn't work since shortcuts are fetched from preferences
        raise NotImplementedError('This method does not work, use add_routine instead or use a KeyMap object')


class ShortcutPicker(MessageDialog):

    def __init__(self, master, message, shortcut_pane=None):
        self.message = message
        super().__init__(master, self.render)
        self.title("Shortcut Picker")
        self.resizable(0, 0)
        self.minsize(350, 200)
        self.value = None
        self.key = None
        self.shortcut_pane = shortcut_pane

    def on_key_change(self, event):
        self.key = KeyMap.get_key(event)
        if self.shortcut_pane is not None:
            routine = self.shortcut_pane.routine_from_shortcut(self.key)
            if routine is not None and self.shortcut_pane:
                self._warning['text'] = f"Key already assigned to {routine.desc}"
                self._warning.pack(fill="x")
            else:
                self._warning.pack_forget()
        self.event_pad.config(text=self.key.label)
        # returning break ensures this event does not propagate
        # preventing the event from invoking currently set bindings
        return "break"

    def render(self, _):
        self.detail = Label(self, **self.style.text, text=self.message)
        self.detail.pack(fill="x")
        warn_frame = Frame(self, **self.style.surface)
        self._warning = Label(
            warn_frame,
            **self.style.text_passive,
            padx=5,
            anchor='w',
            compound="left",
            image=get_tk_image("dialog_warning", 15, 15),
        )
        self.event_pad = Label(
            self, **self.style.text_accent)
        self._add_button(text="Cancel", value=None)
        self._add_button(text="Okay", command=self.exit_with_key, focus=True)
        warn_frame.pack(side="bottom", fill="x")
        self.event_pad.config(
            **self.style.bright, takefocus=True,
            text="Tap here to begin capturing shortcuts."
        )
        self.event_pad.bind("<Any-KeyPress>", self.on_key_change)
        # for some reason alt needs to be bound separately
        self.event_pad.bind("<Alt-KeyPress>", self.on_key_change)
        self.event_pad.bind("<Button-1>", lambda e: self.event_pad.focus_set())
        self.event_pad.pack(fill="both", expand=True)

    def exit_with_key(self, _):
        self.value = self.key
        self.destroy()

    @classmethod
    def pick(cls, master, message, shortcut_pane=None):
        picker = cls(master, message, shortcut_pane)
        picker.wait_window()
        return picker.value


class ShortcutPane(Component, Frame):
    class ShortcutItem(CompoundList.BaseItem):

        def __init__(self, master, value, index, isolated=False):
            super().__init__(master, value, index, isolated)
            initial_key = value[1]
            self.key = initial_key

        def set_key(self, key):
            self.key_label.config(text=key.label)
            self.key = key
            self._value = (self.value[0], key)

        def render(self):
            self.key_label = Label(
                self, text=self.value[1].label, **self.style.text_accent
            )
            self.key_label.pack(side="right")
            routine = actions.get_routine(self.value[0])
            self.desc = Label(
                self, text=routine.desc, **self.style.text
            )
            self.desc.pack(side="left")

        def on_hover_ended(self, *_):
            self.config_all(**self.style.surface)

        def on_hover(self, *_):
            self.config_all(**self.style.bright)

        def disable(self, flag):
            self.disabled(flag)
            if flag:
                self.desc.config(**self.style.text_passive)
                self.key_label.config(**self.style.text_passive)
            else:
                self.desc.config(**self.style.text)
                self.key_label.config(**self.style.text_accent)

    def __init__(self, master, pref: SharedPreferences, path, _, **__):
        super().__init__(master)
        self.config(**self.style.surface)
        self.bindings = {}
        self.is_disabled = False
        self.load(pref, path)
        self.shortcut_list = CompoundList(self)
        self.shortcut_list.set_item_class(ShortcutPane.ShortcutItem)
        self.shortcut_list.set_values(list(self.bindings.items()))
        self.shortcut_list.pack(fill="both", expand=True)
        self.shortcut_list.body.set_up_context((
            EnableIf(
                lambda: (not self.is_disabled) and self.shortcut_list.get(),
                ("command", "Change Shortcut", get_tk_image('edit', 14, 14), self.pick_key, {}),
                EnableIf(
                    lambda: self.shortcut_list.get() and self.shortcut_list.get().value[1] != BlankKey,
                    ("command", "Remove", get_tk_image('delete', 14, 14), self.remove_key, {})
                ),
            ),
        ))

    def remove_key(self):
        if self.shortcut_list.get():
            item = self.shortcut_list.get()
            routine = actions.get_routine(item.value[0])
            self.bindings[routine.key] = BlankKey
            item.set_key(BlankKey)

    def get_item(self, key):
        items = list(filter(
            lambda i: i.value[1] == key,
            self.shortcut_list.items
        ))
        if len(items):
            return items[0]
        return None

    def routine_from_shortcut(self, shortcut):
        search = list(filter(
            lambda r: self.bindings[r] == shortcut,
            self.bindings))
        if len(search) > 0:
            return actions.get_routine(search[0])
        return None

    def pick_key(self):
        if self.shortcut_list.get():
            item = self.shortcut_list.get()
            routine = actions.get_routine(item.value[0])
            key = ShortcutPicker.pick(
                self.window,
                routine.desc,
                self
            )
            if key:
                # overwrite any present bindings by replacing with blank key
                overwritten = self.routine_from_shortcut(key)
                overwritten_item = self.get_item(key)
                if overwritten:
                    self.bindings[overwritten.key] = BlankKey
                    if overwritten_item:
                        overwritten_item.set_key(BlankKey)
                self.bindings[routine.key] = key
                item.set_key(key)

    def _add_key(self, key: Key):
        pass

    def disable(self, flag):
        self.is_disabled = flag
        for item in self.shortcut_list.items:
            item.disable(flag)

    def get(self):
        return self.bindings

    def set(self, value):
        if isinstance(value, dict):
            self.bindings = dict(value.items())
        else:
            raise ValueError("Value must be a dictionary")

    def commit(self):
        super().commit()
        for action, key in self.bindings.items():
            routine = actions.get_routine(action)
            if routine:
                routine.shortcut = key
        for instance in ShortcutManager.instances:
            instance.update_bindings()
