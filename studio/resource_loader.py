import os
import shelve
from hashlib import md5
import shutil

from hoverset.data.images import (
    set_image_resource_path,
    get_resource_path,
    load_tk_image,
    _primary_location,
    _recolor
)
from hoverset.data.utils import make_path, get_theme_path
from hoverset.util.color import parse_color
from hoverset.ui.widgets import Application, Label, ProgressBar
from hoverset.ui.styles import StyleDelegator
from hoverset.platform import windowing_is, X11


class ResourceLoader(Application):
    _default_icon_path = _primary_location
    _cache_icon_path = _primary_location

    def __init__(self, pref):
        super().__init__()
        self.pref = pref
        self.load_styles(pref.get("resource::theme"))
        if windowing_is(self, X11):
            self.wm_attributes("-type", "splash")
        else:
            self.enable_centering()
            self.overrideredirect(1)

        self.configure(**self.style.surface)
        image = load_tk_image(get_resource_path("studio", "resources/images/logo.png"), 240, 77)
        Label(
            self, image=image, **self.style.surface
        ).pack(side="top", fill="y", padx=20, pady=20)
        self._progress = ProgressBar(self)
        self._progress.pack(side="top", fill="x", padx=20, pady=10)
        self._progress.set(0)
        self._progress_text = Label(
            self, **self.style.text_small, text="Waiting for resource loader...",
            anchor="w"
        )
        self._progress_text.pack(side="top", fill="x", padx=20, pady=10)
        self.update_idletasks()
        # give the loader some time to render before starting load
        self.after(200, self.start_load)

    def start_load(self):
        self.check_resources()
        self.destroy()

    def update_progress(self, value, append=True):
        value = value if not append else self._progress.get() + float(value)
        self._progress.set(value)

    def _message(self, text):
        self._progress_text["text"] = text

    @classmethod
    def _actual_cache_icon_path(cls, path):
        if os.path.exists(path):
            return path
        # for windows, we may need the extension
        if os.path.exists(path + ".dat"):
            return path + ".dat"
            # for mac, we need ".db" extension
        if os.path.exists(path + ".db"):
            return path + ".db"
        return None

    @classmethod
    def _cache_exists(cls, path):
        if os.path.exists(path):
            return True
        # for windows, we may need the extension
        if os.path.exists(path + ".dat"):
            return True
            # for mac, we need ".db" extension
        return os.path.exists(path + ".db")

    @classmethod
    def _cache_is_stale(cls, cache_path):
        # check whether cache is outdated
        default = cls._default_icon_checksum()
        current = cls._icon_cache_checksum(cache_path)

        if default is None:
            # the cache is all we got so don't mark it as stale
            return False
        return default != current

    @classmethod
    def _default_icon_checksum(cls):
        path = cls._default_icon_path + ".dat"
        if not os.path.exists(path):
            return None
        with open(path, "rb") as dat:
            return md5(dat.read()).hexdigest()

    @classmethod
    def _icon_cache_checksum(cls, cache_path):
        path = os.path.join(cache_path, "ic_checksum")
        if not os.path.exists(path):
            return None
        with open(path, "r") as checksum:
            return checksum.read()

    @classmethod
    def load(cls, pref):
        cache_color = pref.get("resource::icon_cache_color")
        style = StyleDelegator(get_theme_path(pref.get("resource::theme")))
        cache_path = pref.get_cache_dir()
        cls._cache_icon_path = os.path.join(cache_path, "image")
        if style.colors["accent"] != cache_color \
                or not cls._actual_cache_icon_path(cls._cache_icon_path)\
                or cls._cache_is_stale(cache_path):
            # delete cache to ensure hard refresh
            shutil.rmtree(cache_path, ignore_errors=True)
            make_path(cache_path)
            cls(pref).mainloop()

        set_image_resource_path(cls._cache_icon_path)
        pref.set("resource::icon_cache_color", style.colors["accent"])

    def check_resources(self):

        self._message("Preparing graphic resources...")
        with shelve.open(self._cache_icon_path) as cache:
            with shelve.open(self._default_icon_path) as defaults:
                color = parse_color(self.style.colors["accent"], self)
                step = 1 / len(defaults) * 1
                for image in defaults:
                    if not image.startswith("_"):
                        cache[image] = _recolor(defaults[image], color)
                    else:
                        cache[image] = defaults[image]
                    self.update_progress(step)

        # save default icon checksum
        with open(self._default_icon_path + ".dat", "rb") as cache:
            with open(os.path.join(self.pref.get_cache_dir(), "ic_checksum"), "w") as checksum:
                checksum.write(md5(cache.read()).hexdigest())


if __name__ == "__main__":

    from studio.preferences import Preferences
    ResourceLoader(Preferences.acquire()).mainloop()
