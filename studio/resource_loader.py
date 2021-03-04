import appdirs
import os
import shelve

from hoverset.data.images import (
    set_image_resource_path,
    get_resource_path,
    load_tk_image,
    _primary_location,
    _recolor
)
from hoverset.data.utils import make_path
from hoverset.util.color import parse_color
from hoverset.ui.widgets import Application, Label, ProgressBar
from hoverset.ui.styles import StyleDelegator
from studio.preferences import Preferences

pref = Preferences.acquire()


class ResourceLoader(Application):
    _default_icon_path = _primary_location
    _cache_icon_path = _primary_location

    def __init__(self):
        super().__init__()
        self.load_styles(pref.get("resource::theme"))
        self.wm_attributes("-type", "splash")
        self.configure(**self.style.surface)
        image = load_tk_image(get_resource_path("studio", "resources/images/logo.png"), 240, 77)
        Label(
            self, image=image, **self.style.surface
        ).pack(side="top", fill="y", padx=20, pady=20)
        self._progress = ProgressBar(self)
        self._progress.pack(side="top", fill="x", padx=20, pady=10)
        self._progress.set(0)
        self._progress_text = Label(
            self, **self.style.text_small, text="Loading icons",
            anchor="w"
        )
        self._progress_text.pack(side="top", fill="x", padx=20, pady=10)
        self.check_resources()
        self.destroy()

    def update_progress(self, value, append=True):
        value = value if not append else self._progress.get() + float(value)
        self._progress.set(value)

    def _message(self, text):
        self._progress_text["text"] = text

    @classmethod
    def load(cls):
        cache_color = pref.get("resource::icon_cache_color")
        style = StyleDelegator(pref.get("resource::theme"))
        cache_path = appdirs.AppDirs("formation", "hoverset").user_cache_dir
        cls.cache_icons_path = os.path.join(cache_path, "image")
        if style.colors["accent"] != cache_color or not os.path.exists(cls.cache_icons_path):
            if not os.path.exists(cache_path):
                make_path(cache_path)
            cls().mainloop()

        set_image_resource_path(cls.cache_icons_path)
        pref.set("resource::icon_cache_color", style.colors["accent"])

    def check_resources(self):

        self._message("Preparing graphic resources...")
        with shelve.open(self.cache_icons_path) as cache:
            with shelve.open(self._default_icon_path) as defaults:
                color = parse_color(self.style.colors["accent"], self)
                step = 1/len(defaults)*1
                for image in defaults:
                    if not image.startswith("_"):
                        cache[image] = _recolor(defaults[image], color)
                    else:
                        cache[image] = defaults[image]
                    self.update_progress(step)


if __name__ == "__main__":
    ResourceLoader().mainloop()
