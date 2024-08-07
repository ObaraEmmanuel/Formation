import importlib
from tkinter import ttk


from hoverset.platform import windowing_is, WIN32, AQUA

builtin_themes = (
    "clam",
    "alt",
    "default",
    "classic",
    "vista",
    "xpnative",
    "aqua",
    "winnative",
)


class Theme:
    def __init__(self, name):
        self.name = name
        self.sub_theme = None
        self.sub_themes = []

    def set(self, sub_theme=None):
        raise NotImplementedError()

    @classmethod
    def is_available(cls):
        raise NotImplementedError()

    @classmethod
    def init(cls):
        raise NotImplementedError()

    @classmethod
    def theme_names(cls):
        raise NotImplementedError()

    def __iter__(self):
        return iter(self.sub_themes)

    def __str__(self):
        return self.name


class BuiltInTheme(Theme):
    _style = None

    def set(self, sub_theme=None):
        self._style.theme_use(self.name)

    @classmethod
    def is_available(cls):
        return True

    @classmethod
    def init(cls):
        cls._style = ttk.Style()

    @classmethod
    def theme_names(cls):
        if not cls._style:
            cls.init()
        return cls._style.theme_names()


class TTKTheme(Theme):
    _style = None

    def __init__(self, name):
        super().__init__(name)

    def load(self):
        try:
            ttkthemes = importlib.import_module('ttkthemes')
            self._style = ttkthemes.ThemedStyle()
        except ModuleNotFoundError:
            return

    def set(self, sub_theme=None):
        self._style.theme_use(self.name)

    @classmethod
    def is_available(cls):
        return bool(cls._style)

    @classmethod
    def init(cls):
        try:
            ttkthemes = importlib.import_module('ttkthemes')
            cls._style = ttkthemes.ThemedStyle()
        except ModuleNotFoundError:
            return

    @classmethod
    def theme_names(cls):
        if not cls._style:
            return
        return [x for x in cls._style.theme_names() if x not in builtin_themes]


class SunValleyTheme(Theme):
    _style = None

    def __init__(self, name="Sun Valley"):
        super().__init__(name)
        self.sub_themes = (
            "light",
            "dark",
        )
        self.sub_theme = "light"

    def set(self, sub_theme=None):
        if sub_theme in self.sub_themes:
            self.sub_theme = sub_theme
            self._style.set_theme(self.sub_theme)

    @classmethod
    def is_available(cls):
        return bool(cls._style)

    @classmethod
    def init(cls):
        try:
            cls._style = importlib.import_module('sv_ttk')
        except ModuleNotFoundError:
            return

    @classmethod
    def theme_names(cls):
        return ["sun-valley"]


_theme_cache = {}
_theme_classes = (BuiltInTheme, TTKTheme, SunValleyTheme)


def _load_cache():
    all_themes = []
    for theme_class in _theme_classes:
        theme_class.init()
        if not theme_class.is_available():
            continue
        all_themes.extend([theme_class(x) for x in theme_class.theme_names()])

    for theme in sorted(all_themes, key=lambda x: x.name):
        _theme_cache[theme.name] = theme


def get_default_theme(root):
    if windowing_is(root, WIN32):
        return "vista"
    elif windowing_is(root, AQUA):
        return "aqua"
    return "default"


def get_theme(name):
    if not _theme_cache:
        _load_cache()
    return _theme_cache.get(name)


def get_themes():
    if not _theme_cache:
        _load_cache()
    return _theme_cache
