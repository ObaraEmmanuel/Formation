from studio.main import StudioApplication
from hoverset.data.utils import get_resource_path
import hoverset.ui
import tkinter


class TestStudioApp(StudioApplication):
    STYLES_PATH = get_resource_path(hoverset.ui, "themes/default.css")

    @classmethod
    def get_instance(cls, master=None, **cnf):
        if not isinstance(tkinter._default_root, StudioApplication):
            if tkinter._default_root:
                tkinter._default_root.destroy()
            return TestStudioApp(master, **cnf)

        return tkinter._default_root
