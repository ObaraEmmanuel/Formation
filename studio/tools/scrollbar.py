# ======================================================================= #
# Copyright (C) 2021 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.ui.icons import get_icon_image as icon
from hoverset.ui.widgets import Frame, Checkbutton, Spinner, Label

from studio.tools._base import BaseTool, BaseToolWindow


class ScrollWindow(BaseToolWindow):
    _tool_map = {}

    class ScrollConfigFrame(Frame):

        def __init__(self, master, **cnf):
            label = cnf.pop("text", "")
            super().__init__(master, **cnf)
            self._label = Label(
                self, text=label,
                **self.style.text_accent, anchor='w'
            )
            self._label.grid(sticky="ew", row=0, column=0, columnspan=2, pady=5, padx=10)
            self._scroll = Spinner(self)
            self._scroll.set_values(("select", "scroll 2", "scroll 3"))
            self._scroll.grid(row=1, column=0, pady=5, padx=10, sticky='ew')
            self._auto = Checkbutton(self, text="Auto hide")
            self._auto.grid(row=1, column=1, pady=5, padx=10)
            self.columnconfigure(0, weight=1)

        def disabled(self, flag: bool) -> None:
            super().disabled(flag)
            self._scroll.disabled(True)
            self._auto.disabled(True)
            self._label.disabled(flag)

    def __init__(self, tool, widget):
        super().__init__(tool, widget)
        self.title(f'Configure Scrollbar for {widget.id}')
        self.minsize(400, 300)
        self._x_frame = ScrollWindow.ScrollConfigFrame(
            self, **self.style.surface, text="Horizontal Scrollbar"
        )
        self._x_frame.pack(fill="x", side="top", pady=10)
        self._y_frame = ScrollWindow.ScrollConfigFrame(
            self, **self.style.surface, text="Vertical Scrollbar"
        )
        self._y_frame.pack(fill="x", side="top", pady=10)
        self._y_frame.disabled(True)


class ScrollbarTool(BaseTool):

    def __init__(self, studio, manager):
        super(ScrollbarTool, self).__init__(studio, manager)

    def get_menu(self, studio):
        return ("command", "Scrollbar", icon("play", 14, 14), self.open_editor, {}),

    def open_editor(self):
        ScrollWindow.acquire(self, self.studio.selected)

    def supports(self, widget):
        if widget is None:
            return False
        keys = widget.keys()
        return any(i in keys for i in ("yscrollcommand", "xscrollcommand"))
