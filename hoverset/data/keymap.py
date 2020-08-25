# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import hoverset.data.actions as actions
from hoverset.data.preferences import SharedPreferences


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


class CharKey(Key):

    def __init__(self, alphanumeric: str):
        alphanumeric = alphanumeric.upper()
        super().__init__(alphanumeric, ord(alphanumeric))


class Symbol(Key):
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
    _keys = '0123456789*+ -./'

    def __init__(self, key):
        key = str(key)[:1]
        key = key.replace(' ', '')
        if key != '' and key in self._keys:
            super().__init__(key, 96 + self._keys.index(key))
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
    return Key('F{}'.format(number), 111 + number)


class KeyMap(metaclass=_KeymapDispatch):
    ALT = Key('Alt', 18)
    BACKSPACE = Key('Backspace', 8)
    BREAK = Key('Break', 3)
    CANCEL = Key('Cancel', 3)
    CAPS_LOCK = Key('CapsLock', 20)
    CONTROL = CTRL = Key('Ctrl', 17)
    DELETE = Key('Del', 46)
    END = Key('End', 35)
    ESCAPE = Key('Esc', 27)
    ENTER = RETURN = Key('Enter', 13)
    F = function_key
    HOME = Key('Home', 36)
    INSERT = Key('Insert', 45)
    SHIFT = Key('Shift', 16)
    NUM_LCK = Key('NumLock', 144)
    PAGE_UP = Key('PageUp', 33)
    PAGE_DOWN = Key('PageUp', 34)
    PAUSE = Key('Pause', 19)
    SPACE = Key('Space', 32)
    TAB = Key('Tab', 9)
    SCROLL_LCK = Key('Scroll', 145)
    DOWN = Key('Down', 40)
    LEFT = Key('Left', 37)
    RIGHT = Key('Right', 39)
    UP = Key('Up', 38)

    EVENT_MASK = {
        0x0004: CONTROL,
        0x20000: ALT,
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

    def get_key(self, event):
        key = None
        for mod in self.EVENT_MASK:
            if event.state & mod:
                if key is None:
                    key = self.EVENT_MASK[mod]
                else:
                    key += self.EVENT_MASK[mod]
        main_key = Key(chr(event.keycode), event.keycode)
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
    """

    def __init__(self, window, preferences: SharedPreferences):
        """
        Shortcut manager for a given window
        :param window: A tkinter Toplevel window
        :param preferences: A SharedPreference object
        """
        super().__init__(window)
        preferences.set('hotkeys', {})
        self.bindings = preferences.get('hotkeys')
        self.reversed_bindings = {value: key for key, value in self.bindings.items()}

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
            if routine.shortcut in self.bindings:
                # if shortcut is already set in bindings just ignore
                # setting shortcuts at this point is only important as defaults
                # just in case we have never bound that shortcut
                routine.shortcut = self.reversed_bindings.get(routine.key)
                continue
            self.bindings[routine.shortcut] = routine.key
            self.reversed_bindings[routine.key] = routine.shortcut

    def _invoke(self, routine_key):
        # Things get slightly complicated, we need to use the key to
        # access the actual method in the current program context
        # the method as returned by global actions module is a Routine object
        routine = actions.get_routine(routine_key)
        if routine:
            routine.invoke()

    def get_shortcut(self, routine_key):
        return self.reversed_bindings.get(routine_key)

    def add_shortcut(self, handler, shortcut):
        raise NotImplementedError('This method does not work, use add_routine instead or use a KeyMap object')
