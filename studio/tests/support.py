import tkinter

import hoverset.ui
from hoverset.data.i18n import set_locale
from hoverset.data.utils import get_resource_path

from studio.main import StudioApplication
from studio.preferences import Preferences
from studio.resource_loader import ResourceLoader


class TestStudioApp(StudioApplication):
    STYLES_PATH = get_resource_path(hoverset.ui, "themes/default.css")

    @classmethod
    def get_instance(cls, master=None, **cnf):
        if not isinstance(tkinter._default_root, StudioApplication):
            if tkinter._default_root:
                tkinter._default_root.destroy()
            pref = Preferences.acquire()
            set_locale(pref.get("locale::language"))
            ResourceLoader.load(pref, headless=True)
            return TestStudioApp(master, **cnf)

        return tkinter._default_root
