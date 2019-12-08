from .base import BaseComponent
from hoverset.ui.icons import get_icon
import hoverset.ui.widgets as widgets


class ColorComponent(BaseComponent, widgets.Frame):
    ICON = get_icon("paint")
    DESCRIPTION = "Color options"

    def __init__(self, app, **cnf):
        super().__init__(app.control, **cnf)
        self.config(self.style.dark)
        self.selector = None
        self.app = app
